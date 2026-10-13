import math
import os
import re
import maya.cmds as cmds
import maya.api.OpenMaya as om

from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.framerange_convert import FramerangeFile
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

USD_EXTENSIONS = (".usd", ".usda", ".usdc", ".usdz")
MAYA_EXTENSIONS = (".ma", ".mb")

LAYOUT_PRODUCT = "layout"
MASTER_SHOT = "MASTER"
RIG_PRODUCT = "ModL"

DAISY_CAM_PATH = ("Integration", "otls", "DaisyCam.mb")
CAM_SEQUENCE_TOKEN = re.compile("sqX", re.IGNORECASE)
CAM_SHOT_TOKEN = re.compile("shX", re.IGNORECASE)
CAM_GLOBAL_CTRL_SUFFIX = "_{sequence}_{shot}_global_ctrl"
CAM_PAN_CTRL_SUFFIX = "_{sequence}_{shot}_pan_ctrl"
CAM_TILT_CTRL_SUFFIX = "_{sequence}_{shot}_tilt_ctrl"
CAM_CTRL_SUFFIXES = (CAM_GLOBAL_CTRL_SUFFIX, CAM_PAN_CTRL_SUFFIX, CAM_TILT_CTRL_SUFFIX)
USD_CAM_NAME = "cam_{sequence}_{shot}"
USD_CAM_KEYFRAMES = "daisy:cameraKeyframes"
USD_LENS_SCALE = 100.0
MM_PER_INCH = 25.4
FILM_FIT_HORIZONTAL = 1
LENS_ATTRS = (
    "focalLength",
    "horizontalFilmAperture",
    "verticalFilmAperture",
    "horizontalFilmOffset",
    "verticalFilmOffset",
)


# ------------------------------------------------------------------------------ #
#                                 Prism products                                 #
# ------------------------------------------------------------------------------ #

def get_master_path(core, entity, product):
    versions = core.products.getVersionsFromProduct(entity, product)
    master = next((v for v in versions if v.get("version") == "master"), None)
    if not master:
        return None
    return core.products.getPreferredFileFromVersion(master)


def get_source_scene(core, product_path):
    data = core.paths.getCachePathData(product_path) or {}
    src = data.get("sourceScene")
    if src:
        return src

    info_path = core.products.getVersionInfoPathFromProductFilepath(product_path)
    if info_path and os.path.exists(info_path):
        return core.getConfig("sourceScene", configPath=info_path)
    return None


def get_master_shot_entity(shot_entity):
    entity = {
        "type": "shot",
        "sequence": shot_entity["sequence"],
        "shot": MASTER_SHOT,
    }
    if "episode" in shot_entity:
        entity["episode"] = shot_entity["episode"]
    return entity


def get_daisy_cam_path(core):
    plugin = core.getPlugin("Daisy_Pipe")
    if not plugin:
        cmds.warning("Plugin Prism 'Daisy_Pipe' introuvable")
        return None

    cam_path = os.path.join(plugin.pluginDirectory, *DAISY_CAM_PATH)
    if not os.path.isfile(cam_path):
        cmds.warning("DaisyCam introuvable : %s" % cam_path)
        return None

    return cam_path.replace("\\", "/")


# ------------------------------------------------------------------------------ #
#                                  Maya loaders                                  #
# ------------------------------------------------------------------------------ #

def load_usd_stage(path, name, scale=100.0):
    cmds.loadPlugin("mayaUsdPlugin", quiet=True)
    xform = cmds.createNode("transform", name=name)
    shape = cmds.createNode("mayaUsdProxyShape", name=name + "Shape", parent=xform)
    cmds.setAttr(shape + ".filePath", path, type="string")
    cmds.connectAttr("time1.outTime", shape + ".time")
    cmds.setAttr(xform + ".scale", scale, scale, scale, type="double3")
    return shape


def import_maya_scene(path, namespace=":"):
    if not path or not os.path.exists(path):
        cmds.warning("Scène introuvable : %s" % path)
        return None

    if not path.lower().endswith(MAYA_EXTENSIONS):
        cmds.warning("La scène source n'est pas un fichier Maya : %s" % path)
        return None

    path = path.replace("\\", "/")
    file_type = "mayaAscii" if path.lower().endswith(".ma") else "mayaBinary"
    nodes = cmds.file(
        path,
        i=True,
        type=file_type,
        ignoreVersion=True,
        namespace=namespace,
        mergeNamespacesOnClash=True,
        preserveReferences=True,
        returnNewNodes=True,
    )
    print("Importé : %s (%d nodes)" % (path, len(nodes or [])))
    return nodes


# ------------------------------------------------------------------------------ #
#                                    Imports                                     #
# ------------------------------------------------------------------------------ #

def import_master_usd(core, entity, product):
    path = get_master_path(core, entity, product)
    if not path:
        cmds.warning("Pas de master trouvé pour %s sur %s" % (product, entity))
        return None

    if not path.lower().endswith(USD_EXTENSIONS):
        cmds.warning("Le fichier préféré du master n'est pas un USD : %s" % path)
        return None

    name = "%s_%s_%s" % (entity["sequence"], entity["shot"], product)
    shape = load_usd_stage(path.replace("\\", "/"), name)
    print("Stage chargé : %s -> %s" % (shape, path))
    return shape


def rename_cam_nodes(nodes, sequence, shot):
    # Les UUID restent valides même après le renommage d'un parent
    uuids = cmds.ls(nodes, uuid=True) or []
    for uuid in uuids:
        node = cmds.ls(uuid, long=True)[0]
        short_name = node.split("|")[-1]
        new_name = CAM_SHOT_TOKEN.sub(shot, CAM_SEQUENCE_TOKEN.sub(sequence, short_name))
        if new_name != short_name:
            cmds.rename(node, new_name)

    return cmds.ls(uuids, long=True) or []


def import_daisy_cam(core, sequence, shot, reference=False):
    cam_path = get_daisy_cam_path(core)
    if not cam_path:
        return None

    if reference:
        new_nodes = cmds.file(
            cam_path,
            reference=True,
            namespace=":",
            returnNewNodes=True,
        )
        cmds.warning("Caméra référencée : les nodes ne peuvent pas être renommés")
    else:
        new_nodes = cmds.file(
            cam_path,
            i=True,
            type="mayaBinary",
            namespace=":",
            returnNewNodes=True,
            ignoreVersion=True,
        )
        new_nodes = rename_cam_nodes(new_nodes, sequence, shot)

    cameras = cmds.ls(new_nodes, type="camera", long=True) or []
    cam_transforms = cmds.listRelatives(cameras, parent=True, fullPath=True) or []
    return cam_transforms[0] if cam_transforms else None


def get_shot_ranges(sequence, shot):
    # Frame range du shot dans le temps du shot et dans le temps du MASTER
    try:
        framerange = FramerangeFile()
        return framerange.get_shot_range(sequence, shot), framerange.get_master_range(sequence, shot)
    except Exception as e:
        cmds.warning("Frame range introuvable pour %s_%s (%s)" % (sequence, shot, e))
        return None, None


def offset_stage_time(stage_shape, shot_range, master_range):
    # Courbe temps -> temps : la frame de début du shot lit la frame de début du shot dans le MASTER
    curve = cmds.createNode("animCurveTT", name=stage_shape.split("|")[-1] + "_timeOffset")
    cmds.setKeyframe(curve, time=shot_range[0], value=master_range[0])
    cmds.setKeyframe(curve, time=shot_range[1], value=master_range[0] + shot_range[1] - shot_range[0])
    cmds.keyTangent(curve, inTangentType="linear", outTangentType="linear")
    cmds.setInfinity(curve, preInfinite="linear", postInfinite="linear")
    cmds.connectAttr(curve + ".output", stage_shape + ".time", force=True)
    return curve


def get_usd_camera(stage_shape, camera_name):
    import mayaUsd.ufe
    from pxr import UsdGeom

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    camera = next((p for p in stage.Traverse() if p.IsA(UsdGeom.Camera) and p.GetName() == camera_name), None)
    if camera is None:
        cmds.warning("Caméra %s introuvable dans le stage %s" % (camera_name, stage_shape))
    return camera


def get_usd_camera_matrix(stage_shape, camera, frame):
    from pxr import Usd, UsdGeom

    usd_matrix = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(Usd.TimeCode(frame))

    # Matrice USD -> espace Maya, en passant par le transform du stage (scale 100)
    stage_xform = cmds.listRelatives(stage_shape, parent=True, fullPath=True)[0]
    matrix = om.MMatrix([usd_matrix[i][j] for i in range(4) for j in range(4)])
    matrix *= om.MMatrix(cmds.xform(stage_xform, query=True, worldSpace=True, matrix=True))

    # Seule la position et l'orientation nous intéressent, pas le scale du stage
    transform = om.MTransformationMatrix(matrix)
    transform.setScale([1.0, 1.0, 1.0], om.MSpace.kWorld)
    return transform.asMatrix()


def match_lens(cam_transform, camera, frame):
    from pxr import Usd, UsdGeom

    lens = UsdGeom.Camera(camera)
    time = Usd.TimeCode(frame)
    shape = cmds.listRelatives(cam_transform, shapes=True, type="camera", fullPath=True)[0]

    # Valeurs USD x100 -> mm, puis mm -> pouces pour le film back Maya
    focal_length = lens.GetFocalLengthAttr().Get(time) * USD_LENS_SCALE
    film_values = {
        "horizontalFilmAperture": lens.GetHorizontalApertureAttr().Get(time),
        "verticalFilmAperture": lens.GetVerticalApertureAttr().Get(time),
        "horizontalFilmOffset": lens.GetHorizontalApertureOffsetAttr().Get(time),
        "verticalFilmOffset": lens.GetVerticalApertureOffsetAttr().Get(time),
    }

    cmds.setAttr(shape + ".focalLength", focal_length)
    for attr, value in film_values.items():
        cmds.setAttr(shape + "." + attr, value * USD_LENS_SCALE / MM_PER_INCH)
    # L'aperture Houdini est horizontale
    cmds.setAttr(shape + ".filmFit", FILM_FIT_HORIZONTAL)

    # Le rig expose aussi la focale sur le transform de la caméra
    if cmds.attributeQuery("focalLength", node=cam_transform, exists=True):
        cmds.setAttr(cam_transform + ".focalLength", focal_length)


def get_cam_ctrl(cam_transform, suffix, sequence, shot):
    root = cmds.ls(cam_transform, long=True)[0].split("|")[1]
    nodes = cmds.listRelatives(root, allDescendents=True, type="transform", fullPath=True) or []
    # Le suffixe complet évite de confondre global_ctrl avec sub_global_ctrl ou gimbal_global_ctrl
    suffix = suffix.format(sequence=sequence, shot=shot)
    ctrls = [n for n in nodes if n.endswith(suffix)]
    if not ctrls:
        cmds.warning("Contrôleur %s introuvable sous %s" % (suffix, root))
        return None
    return ctrls[0]


def get_yaw_pitch(matrix):
    # La caméra regarde vers -Z, normal() ignore le scale du rig
    forward = om.MVector(-matrix[8], -matrix[9], -matrix[10]).normal()
    yaw = math.degrees(math.atan2(-forward.x, -forward.z))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, forward.y))))
    return yaw, pitch


def get_cam_yaw_pitch(cam_transform):
    return get_yaw_pitch(cmds.xform(cam_transform, query=True, worldSpace=True, matrix=True))


def match_position(cam_transform, global_ctrl, target):
    cam_position = cmds.xform(cam_transform, query=True, worldSpace=True, translation=True)
    offset = [target[12 + i] - cam_position[i] for i in range(3)]
    cmds.move(offset[0], offset[1], offset[2], global_ctrl, relative=True, worldSpace=True)


def match_pan(cam_transform, pan_ctrl, target_yaw):
    yaw = get_cam_yaw_pitch(cam_transform)[0]
    delta = (target_yaw - yaw + 180.0) % 360.0 - 180.0
    cmds.setAttr(pan_ctrl + ".rotateY", cmds.getAttr(pan_ctrl + ".rotateY") + delta)


def match_tilt(cam_transform, tilt_ctrl, target_pitch):
    # Un rotateX positif sur le tilt fait baisser la caméra
    pitch = get_cam_yaw_pitch(cam_transform)[1]
    cmds.setAttr(tilt_ctrl + ".rotateX", cmds.getAttr(tilt_ctrl + ".rotateX") - (target_pitch - pitch))


def is_camera_animated(camera):
    from pxr import UsdGeom

    lens = UsdGeom.Camera(camera)
    lens_attrs = (
        lens.GetFocalLengthAttr(),
        lens.GetHorizontalApertureAttr(),
        lens.GetVerticalApertureAttr(),
        lens.GetHorizontalApertureOffsetAttr(),
        lens.GetVerticalApertureOffsetAttr(),
    )
    return UsdGeom.Xformable(camera).TransformMightBeTimeVarying() or any(a.ValueMightBeTimeVarying() for a in lens_attrs)


def get_camera_key_frames(camera, shot_range, time_offset):
    # Frames des clés Houdini, écrites en customData à l'export du layout
    master_frames = camera.GetCustomData().get(USD_CAM_KEYFRAMES)
    if master_frames is None:
        return None

    start, end = int(shot_range[0]), int(shot_range[1])
    all_frames = {int(frame) - time_offset for frame in master_frames}
    frames = {frame for frame in all_frames if start <= frame <= end}
    # Une clé hors shot influence le shot : sa borne garde la valeur interpolée
    if any(frame < start for frame in all_frames):
        frames.add(start)
    if any(frame > end for frame in all_frames):
        frames.add(end)
    return sorted(frames)


def match_frame(cam_transform, ctrls, stage_shape, camera, master_frame):
    global_ctrl, pan_ctrl, tilt_ctrl = ctrls
    target = get_usd_camera_matrix(stage_shape, camera, master_frame)

    # Position d'abord : l'orientation de la caméra dépend de sa position (aim)
    match_position(cam_transform, global_ctrl, target)

    # Rotation : pan pour le yaw, tilt pour le pitch
    target_yaw, target_pitch = get_yaw_pitch(list(target))
    match_pan(cam_transform, pan_ctrl, target_yaw)
    match_tilt(cam_transform, tilt_ctrl, target_pitch)

    match_position(cam_transform, global_ctrl, target)
    match_lens(cam_transform, camera, master_frame)


def key_daisy_cam(cam_transform, ctrls):
    global_ctrl, pan_ctrl, tilt_ctrl = ctrls
    shape = cmds.listRelatives(cam_transform, shapes=True, type="camera", fullPath=True)[0]

    cmds.setKeyframe(global_ctrl, attribute=["translateX", "translateY", "translateZ"])
    cmds.setKeyframe(pan_ctrl, attribute="rotateY")
    cmds.setKeyframe(tilt_ctrl, attribute="rotateX")
    cmds.setKeyframe(shape, attribute=list(LENS_ATTRS))
    if cmds.attributeQuery("focalLength", node=cam_transform, exists=True):
        cmds.setKeyframe(cam_transform, attribute="focalLength")


def match_daisy_cam_to_usd(cam_transform, stage_shape, sequence, shot, shot_range, master_range):
    camera_name = USD_CAM_NAME.format(sequence=sequence, shot=shot)
    camera = get_usd_camera(stage_shape, camera_name)
    if camera is None:
        return None

    ctrls = tuple(get_cam_ctrl(cam_transform, suffix, sequence, shot) for suffix in CAM_CTRL_SUFFIXES)
    if None in ctrls:
        return None

    if shot_range is None:
        # Sans frame range, on reste dans le temps du master sur toute la durée du stage
        stage = camera.GetStage()
        shot_range = master_range = [int(stage.GetStartTimeCode()), int(stage.GetEndTimeCode())]
        cmds.warning("Pas de frame range : DaisyCam calée sur le temps du master %s" % shot_range)

    time_offset = master_range[0] - shot_range[0]
    if not is_camera_animated(camera):
        match_frame(cam_transform, ctrls, stage_shape, camera, master_range[0])
        print("DaisyCam placée sur %s" % camera_name)
        return ctrls[0]

    # Caméra animée : clés aux frames des clés Houdini, sinon à chaque frame du shot
    frames = get_camera_key_frames(camera, shot_range, time_offset)
    if frames is None:
        frames = range(int(shot_range[0]), int(shot_range[1]) + 1)
    elif not frames:
        # Aucune clé utile sur ce shot : la caméra est fixe
        match_frame(cam_transform, ctrls, stage_shape, camera, master_range[0])
        print("DaisyCam placée sur %s (fixe sur le shot)" % camera_name)
        return ctrls[0]

    cmds.refresh(suspend=True)
    try:
        for frame in frames:
            cmds.currentTime(frame)
            match_frame(cam_transform, ctrls, stage_shape, camera, frame + time_offset)
            key_daisy_cam(cam_transform, ctrls)
    finally:
        cmds.currentTime(shot_range[0])
        cmds.refresh(suspend=False)

    print("DaisyCam animée sur %s (%d clés)" % (camera_name, len(frames)))
    return ctrls[0]


def import_rig_source_scene(core, entity):
    product_path = core.products.getLatestVersionpathFromProduct(RIG_PRODUCT, entity=entity)
    if not product_path:
        cmds.warning("Aucune version trouvée pour %s sur %s" % (RIG_PRODUCT, entity))
        return None

    source_scene = get_source_scene(core, product_path)
    print("Product :", product_path)
    print("Source scene :", source_scene)
    return import_maya_scene(source_scene)


# ------------------------------------------------------------------------------ #
#                                   Departments                                  #
# ------------------------------------------------------------------------------ #

def setup_anim(core, info):
    entity = info["entity"]
    sequence, shot = entity["sequence"], entity["shot"]

    shot_range, master_range = get_shot_ranges(sequence, shot)

    layout = import_master_usd(core, get_master_shot_entity(entity), LAYOUT_PRODUCT)
    if layout and shot_range:
        offset_stage_time(layout, shot_range, master_range)

    camera = import_daisy_cam(core, sequence, shot)
    if layout and camera:
        match_daisy_cam_to_usd(camera, layout, sequence, shot, shot_range, master_range)

    return {"layout": layout, "camera": camera}


def setup_rig(core, info):
    if info["task"] != "RigL":
        return None
    return import_rig_source_scene(core, info["entity"])


SHOT_DEPARTMENTS = {
    "03_anim": setup_anim,
}

ASSET_DEPARTMENTS = {
    "04_rig": setup_rig,
}


def import_asset():
    info = get_entity_info()
    if info is None:
        return None

    if info["entity"].get("type") == "shot":
        departments = SHOT_DEPARTMENTS
    else:
        departments = ASSET_DEPARTMENTS

    setup = departments.get(info["department"])
    if setup is None:
        return None

    return setup(get_core(), info)


import_asset()
