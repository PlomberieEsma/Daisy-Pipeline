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
CAM_GROUP_NAME = "cam"
CAM_SEQUENCE_TOKEN =re.compile("sqX", re.IGNORECASE)
CAM_SHOT_TOKEN = re.compile("shX", re.IGNORECASE)
CAM_GLOBAL_CTRL_SUFFIX = "_{sequence}_{shot}_global_ctrl"
CAM_PAN_CTRL_SUFFIX = "_{sequence}_{shot}_pan_ctrl"
CAM_TILT_CTRL_SUFFIX = "_{sequence}_{shot}_tilt_ctrl"
CAM_CTRL_SUFFIXES = (CAM_GLOBAL_CTRL_SUFFIX, CAM_PAN_CTRL_SUFFIX, CAM_TILT_CTRL_SUFFIX)
USD_CAM_NAME = "cam_{sequence}_{shot}"
USD_CAM_KEYFRAMES = "daisy:cameraKeyframes"
LOADED_PRIM_COLLECTION = "loaded_prim"
USD_LENS_SCALE = 100.0
MM_PER_INCH = 25.4
FILM_FIT_HORIZONTAL = 1
STATIC_TOLERANCE = 1e-5
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
    #-----------------------------------------------------------------#
    # Get the preferred file of the master version of a Prism product #
    #                                                                 #
    # core = Prism core                                               #
    # entity = Prism entity dict (asset or shot)                      #
    # product = product name (e.g.: layout)                           #
    #                                                                 #
    # return the file path, or None if the product has no master      #
    #-----------------------------------------------------------------#

    versions = core.products.getVersionsFromProduct(entity, product)
    master = next((v for v in versions if v.get("version") == "master"), None)
    if not master:
        return None
    return core.products.getPreferredFileFromVersion(master)


def get_source_scene(core, product_path):
    #------------------------------------------------------------#
    # Get the source scene used to publish a product             #
    # Look in the cache path data first, then in the versioninfo #
    #                                                            #
    # core = Prism core                                          #
    # product_path = path of a published product file            #
    #                                                            #
    # return the source scene path, or None if not found         #
    #------------------------------------------------------------#

    data = core.paths.getCachePathData(product_path) or {}
    src = data.get("sourceScene")
    if src:
        return src

    info_path = core.products.getVersionInfoPathFromProductFilepath(product_path)
    if info_path and os.path.exists(info_path):
        return core.getConfig("sourceScene", configPath=info_path)
    return None


def get_master_shot_entity(shot_entity):
    #------------------------------------------------------------------------#
    # Build the entity of the MASTER shot of a shot's sequence               #
    #                                                                        #
    # shot_entity = Prism entity dict of the shot                            #
    #                                                                        #
    # return the MASTER shot entity dict (keeps the episode if there is one) #
    #------------------------------------------------------------------------#

    entity = {
        "type": "shot",
        "sequence": shot_entity["sequence"],
        "shot": MASTER_SHOT,
    }
    if "episode" in shot_entity:
        entity["episode"] = shot_entity["episode"]
    return entity


def get_daisy_cam_path(core):
    #---------------------------------------------------------------------------#
    # Get the DaisyCam path in the Daisy_Pipe plugin folder                     #
    #                                                                           #
    # core = Prism core                                                         #
    #                                                                           #
    # return the DaisyCam.mb path, or None if the plugin or the file is missing #
    #---------------------------------------------------------------------------#

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
    #------------------------------------------------------------------#
    # Load a USD file in the Maya scene through a mayaUsdProxyShape    #
    # The stage follows the scene time and is scaled (Houdini -> Maya) #
    #                                                                  #
    # path = USD file path                                             #
    # name = name of the created transform                             #
    # scale = scale applied to the stage transform                     #
    #                                                                  #
    # return the name of the created mayaUsdProxyShape                 #
    #------------------------------------------------------------------#

    cmds.loadPlugin("mayaUsdPlugin", quiet=True)
    xform = cmds.createNode("transform", name=name)
    shape = cmds.createNode("mayaUsdProxyShape", name=name + "Shape", parent=xform)
    # Open the stage without payloads, they are loaded afterwards by load_stage_payloads()
    cmds.setAttr(shape + ".loadPayloads", False)
    cmds.setAttr(shape + ".filePath", path, type="string")
    cmds.connectAttr("time1.outTime", shape + ".time")
    cmds.setAttr(xform + ".scale", scale, scale, scale, type="double3")
    load_stage_payloads(shape)
    return shape


def get_loaded_prim_collection(stage):
    #-------------------------------------------------------------------#
    # Find the collection listing the prims to load in the USD stage    #
    #                                                                   #
    # stage = USD stage                                                 #
    #                                                                   #
    # return the Usd.CollectionAPI, or None if there is no collection   #
    #-------------------------------------------------------------------#

    from pxr import Usd

    for prim in stage.Traverse():
        for collection in Usd.CollectionAPI.GetAllCollections(prim):
            if collection.GetName() == LOADED_PRIM_COLLECTION:
                return collection
    return None


def load_stage_payloads(stage_shape):
    #------------------------------------------------------------------------#
    # Load the payloads of the prims listed in the loaded_prim collection    #
    # If the stage has no loaded_prim collection, everything is loaded       #
    #                                                                        #
    # stage_shape = mayaUsdProxyShape of the stage                           #
    #                                                                        #
    # return the list of loaded prim paths                                   #
    #------------------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import Sdf

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    collection = get_loaded_prim_collection(stage)
    if collection is None or collection.GetIncludeRootAttr().Get():
        stage.Load(Sdf.Path.absoluteRootPath)
        print("Pas de collection %s : tout le stage est chargé" % LOADED_PRIM_COLLECTION)
        return [Sdf.Path.absoluteRootPath]

    # The targets are used as they are: the prims under an unloaded payload
    # do not exist yet, so the collection membership can not be computed
    paths = collection.GetIncludesRel().GetTargets()
    for path in paths:
        stage.Load(path)
    for path in collection.GetExcludesRel().GetTargets():
        stage.Unload(path)

    print("%d prim(s) chargée(s) depuis la collection %s" % (len(paths), collection.GetPath()))
    return paths


def import_maya_scene(path, namespace=":"):
    #-------------------------------------------------------------------#
    # Import a Maya scene (.ma or .mb) in the current scene             #
    #                                                                   #
    # path = path of the scene to import                                #
    # namespace = namespace to import the nodes in (":" = root)         #
    #                                                                   #
    # return the list of imported nodes, or None if the file is invalid #
    #-------------------------------------------------------------------#

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
    #-------------------------------------------------------------------------------------#
    # Load the master USD of a product as a stage in the Maya scene                       #
    #                                                                                     #
    # core = Prism core                                                                   #
    # entity = Prism entity dict of the shot                                              #
    # product = name of the product to load (e.g.: layout)                                #
    #                                                                                     #
    # return the name of the created mayaUsdProxyShape, or None if there is no USD master #
    #-------------------------------------------------------------------------------------#

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
    #-----------------------------------------------------------------------------------#
    # Rename the DaisyCam nodes by replacing sqX and shX with the sequence and the shot #
    #                                                                                   #
    # nodes = list of the imported DaisyCam nodes                                       #
    # sequence = sequence name (e.g.: sq0010)                                           #
    # shot = shot name (e.g.: sh0010)                                                   #
    #                                                                                   #
    # return the list of renamed nodes (long names)                                     #
    #-----------------------------------------------------------------------------------#

    # UUIDs stay valid even after a parent is renamed
    uuids = cmds.ls(nodes, uuid=True) or []
    for uuid in uuids:
        node = cmds.ls(uuid, long=True)[0]
        short_name = node.split("|")[-1]
        new_name = CAM_SHOT_TOKEN.sub(shot, CAM_SEQUENCE_TOKEN.sub(sequence, short_name))
        if new_name != short_name:
            cmds.rename(node, new_name)

    return cmds.ls(uuids, long=True) or []


def import_daisy_cam(core, sequence, shot, reference=False):
    #--------------------------------------------------------------------------------#
    # Import (or reference) the DaisyCam and rename it for the shot                  #
    #                                                                                #
    # core = Prism core                                                              #
    # sequence = sequence name (e.g.: sq0010)                                        #
    # shot = shot name (e.g.: sh0010)                                                #
    # reference = True to reference the camera instead of importing it (no renaming) #
    #                                                                                #
    # return the camera transform, or None if the import failed                      #
    #--------------------------------------------------------------------------------#

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


def group_daisy_cam(cam_transform, group_name):
    #-------------------------------------------------------------------------#
    # Put the DaisyCam root group (DaisyCam_sqX_shX) under new groups:        #
    # group_name|cam|DaisyCam_sqX_shX                                         #
    #                                                                         #
    # cam_transform = DaisyCam transform                                      #
    # group_name = name of the top group (name of the layout defaultPrim)     #
    #                                                                         #
    # return the DaisyCam transform long name after the parenting             #
    #-------------------------------------------------------------------------#

    uuid = cmds.ls(cam_transform, uuid=True)[0]
    root = "|" + cmds.ls(cam_transform, long=True)[0].split("|")[1]
    group = cmds.group(empty=True, world=True, name=group_name)
    cam_group = cmds.group(empty=True, parent=group, name=CAM_GROUP_NAME)
    cmds.parent(root, cam_group, relative=True)
    return cmds.ls(uuid, long=True)[0]


def get_shot_ranges(sequence, shot):
    #-------------------------------------------------------------------------#
    # Get the shot frame range in the shot time and in the MASTER time        #
    #                                                                         #
    # sequence = sequence name (e.g.: sq0010)                                 #
    # shot = shot name (e.g.: sh0010)                                         #
    #                                                                         #
    # return a tuple (shot_range, master_range), or (None, None) if not found #
    #-------------------------------------------------------------------------#

    # Shot frame range in the shot time and in the MASTER time
    try:
        framerange = FramerangeFile()
        return framerange.get_shot_range(sequence, shot), framerange.get_master_range(sequence, shot)
    except Exception as e:
        cmds.warning("Frame range introuvable pour %s_%s (%s)" % (sequence, shot, e))
        return None, None


def offset_stage_time(stage_shape, shot_range, master_range):
    #--------------------------------------------------------------------------#
    # Offset the USD stage time so the shot reads the right part of the MASTER #
    #                                                                          #
    # stage_shape = mayaUsdProxyShape of the layout                            #
    # shot_range = shot frame range in the shot time                           #
    # master_range = shot frame range in the MASTER time                       #
    #                                                                          #
    # return the animCurveTT connected to the stage time                       #
    #--------------------------------------------------------------------------#

    # Time -> time curve: the shot start frame reads the shot start frame in the MASTER
    curve = cmds.createNode("animCurveTT", name=stage_shape.split("|")[-1] + "_timeOffset")
    cmds.setKeyframe(curve, time=shot_range[0], value=master_range[0])
    cmds.setKeyframe(curve, time=shot_range[1], value=master_range[0] + shot_range[1] - shot_range[0])
    cmds.keyTangent(curve, inTangentType="linear", outTangentType="linear")
    cmds.setInfinity(curve, preInfinite="linear", postInfinite="linear")
    cmds.connectAttr(curve + ".output", stage_shape + ".time", force=True)
    return curve


def get_default_prim_name(stage_shape):
    #------------------------------------------------------------------#
    # Get the name of the defaultPrim of the USD stage                 #
    #                                                                  #
    # stage_shape = mayaUsdProxyShape of the stage                     #
    #                                                                  #
    # return the defaultPrim name, or None if the stage has none       #
    #------------------------------------------------------------------#

    import mayaUsd.ufe

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    default_prim = stage.GetDefaultPrim()
    if not default_prim:
        cmds.warning("Pas de defaultPrim dans le stage %s" % stage_shape)
        return None
    return default_prim.GetName()


def get_usd_camera(stage_shape, camera_name):
    #-----------------------------------------------------------------#
    # Find a USD camera by its name in the stage                      #
    #                                                                 #
    # stage_shape = mayaUsdProxyShape of the layout                   #
    # camera_name = name of the camera prim (e.g.: cam_sq0010_sh0010) #
    #                                                                 #
    # return the camera prim, or None if not found                    #
    #-----------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import UsdGeom

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    camera = next((p for p in stage.Traverse() if p.IsA(UsdGeom.Camera) and p.GetName() == camera_name), None)
    if camera is None:
        cmds.warning("Caméra %s introuvable dans le stage %s" % (camera_name, stage_shape))
    return camera


def deactivate_usd_cameras(stage_shape):
    #--------------------------------------------------------------------#
    # Deactivate all the cameras of the USD stage so they do not appear  #
    # in the Maya camera list                                            #
    # The edit is done in the session layer, the USD file is not changed #
    #                                                                    #
    # stage_shape = mayaUsdProxyShape of the layout                      #
    #                                                                    #
    # return the number of deactivated cameras                           #
    #--------------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import Usd, UsdGeom

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    # Get the list first: deactivating a prim during the traversal breaks it
    cameras = [p for p in stage.Traverse() if p.IsA(UsdGeom.Camera)]
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        for camera in cameras:
            camera.SetActive(False)

    print("%d caméra(s) USD désactivée(s) dans %s" % (len(cameras), stage_shape))
    return len(cameras)


def get_usd_camera_matrix(stage_shape, camera, frame):
    #--------------------------------------------------------------------------#
    # Compute the world matrix of a USD camera in Maya space at a given frame  #
    # The stage scale is removed to only keep the position and the orientation #
    #                                                                          #
    # stage_shape = mayaUsdProxyShape of the layout                            #
    # camera = USD camera prim                                                 #
    # frame = frame in the stage time (MASTER)                                 #
    #                                                                          #
    # return the camera matrix (MMatrix)                                       #
    #--------------------------------------------------------------------------#

    from pxr import Usd, UsdGeom

    usd_matrix = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(Usd.TimeCode(frame))

    # USD matrix -> Maya space, through the stage transform (scale 100)
    stage_xform = cmds.listRelatives(stage_shape, parent=True, fullPath=True)[0]
    matrix = om.MMatrix([usd_matrix[i][j] for i in range(4) for j in range(4)])
    matrix *= om.MMatrix(cmds.xform(stage_xform, query=True, worldSpace=True, matrix=True))

    # Only the position and the orientation matter, not the stage scale
    transform = om.MTransformationMatrix(matrix)
    transform.setScale([1.0, 1.0, 1.0], om.MSpace.kWorld)
    return transform.asMatrix()


def match_lens(cam_transform, camera, frame):
    #---------------------------------------------------------------------------#
    # Copy the focal length and the film back of the USD camera to the DaisyCam #
    #                                                                           #
    # cam_transform = DaisyCam transform                                        #
    # camera = USD camera prim                                                  #
    # frame = frame in the stage time (MASTER)                                  #
    #---------------------------------------------------------------------------#

    from pxr import Usd, UsdGeom

    lens = UsdGeom.Camera(camera)
    time = Usd.TimeCode(frame)
    shape = cmds.listRelatives(cam_transform, shapes=True, type="camera", fullPath=True)[0]

    # USD values x100 -> mm, then mm -> inches for the Maya film back
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
    # Houdini aperture is horizontal
    cmds.setAttr(shape + ".filmFit", FILM_FIT_HORIZONTAL)

    # The rig also exposes the focal length on the camera transform
    if cmds.attributeQuery("focalLength", node=cam_transform, exists=True):
        cmds.setAttr(cam_transform + ".focalLength", focal_length)


def get_cam_ctrl(cam_transform, suffix, sequence, shot):
    #--------------------------------------------------------------------------------------------------#
    # Find a controller of the DaisyCam rig from its suffix                                            #
    #                                                                                                  #
    # cam_transform = DaisyCam transform                                                               #
    # suffix = controller suffix (CAM_GLOBAL_CTRL_SUFFIX, CAM_PAN_CTRL_SUFFIX or CAM_TILT_CTRL_SUFFIX) #
    # sequence = sequence name (e.g.: sq0010)                                                          #
    # shot = shot name (e.g.: sh0010)                                                                  #
    #                                                                                                  #
    # return the controller long name, or None if not found                                            #
    #--------------------------------------------------------------------------------------------------#

    root = cmds.ls(cam_transform, long=True)[0].split("|")[1]
    nodes = cmds.listRelatives(root, allDescendents=True, type="transform", fullPath=True) or []
    # The full suffix avoids mixing up global_ctrl with sub_global_ctrl or gimbal_global_ctrl
    suffix = suffix.format(sequence=sequence, shot=shot)
    ctrls = [n for n in nodes if n.endswith(suffix)]
    if not ctrls:
        cmds.warning("Contrôleur %s introuvable sous %s" % (suffix, root))
        return None
    return ctrls[0]


def get_yaw_pitch(matrix):
    #-----------------------------------------------------------------#
    # Compute the yaw and the pitch of a camera from its world matrix #
    #                                                                 #
    # matrix = camera world matrix (list of 16 values)                #
    #                                                                 #
    # return a tuple (yaw, pitch) in degrees                          #
    #-----------------------------------------------------------------#

    # The camera looks down -Z, normal() ignores the rig scale
    forward = om.MVector(-matrix[8], -matrix[9], -matrix[10]).normal()
    yaw = math.degrees(math.atan2(-forward.x, -forward.z))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, forward.y))))
    return yaw, pitch


def get_cam_yaw_pitch(cam_transform):
    #---------------------------------------------------#
    # Compute the current yaw and pitch of the DaisyCam #
    #                                                   #
    # cam_transform = DaisyCam transform                #
    #                                                   #
    # return a tuple (yaw, pitch) in degrees            #
    #---------------------------------------------------#

    return get_yaw_pitch(cmds.xform(cam_transform, query=True, worldSpace=True, matrix=True))


def match_position(cam_transform, global_ctrl, target):
    #------------------------------------------------------------------------------#
    # Move the global_ctrl so the DaisyCam is at the position of the target matrix #
    #                                                                              #
    # cam_transform = DaisyCam transform                                           #
    # global_ctrl = global controller of the DaisyCam rig                          #
    # target = target world matrix (position at indices 12, 13 and 14)             #
    #------------------------------------------------------------------------------#

    cam_position = cmds.xform(cam_transform, query=True, worldSpace=True, translation=True)
    offset = [target[12 + i] - cam_position[i] for i in range(3)]
    cmds.move(offset[0], offset[1], offset[2], global_ctrl, relative=True, worldSpace=True)


def match_pan(cam_transform, pan_ctrl, target_yaw):
    #--------------------------------------------------------#
    # Rotate the pan_ctrl so the DaisyCam has the target yaw #
    #                                                        #
    # cam_transform = DaisyCam transform                     #
    # pan_ctrl = pan controller of the DaisyCam rig          #
    # target_yaw = target yaw in degrees                     #
    #--------------------------------------------------------#

    yaw = get_cam_yaw_pitch(cam_transform)[0]
    delta = (target_yaw - yaw + 180.0) % 360.0 - 180.0
    cmds.setAttr(pan_ctrl + ".rotateY", cmds.getAttr(pan_ctrl + ".rotateY") + delta)


def match_tilt(cam_transform, tilt_ctrl, target_pitch):
    #-----------------------------------------------------------#
    # Rotate the tilt_ctrl so the DaisyCam has the target pitch #
    #                                                           #
    # cam_transform = DaisyCam transform                        #
    # tilt_ctrl = tilt controller of the DaisyCam rig           #
    # target_pitch = target pitch in degrees                    #
    #-----------------------------------------------------------#

    # A positive rotateX on the tilt makes the camera look down
    pitch = get_cam_yaw_pitch(cam_transform)[1]
    cmds.setAttr(tilt_ctrl + ".rotateX", cmds.getAttr(tilt_ctrl + ".rotateX") - (target_pitch - pitch))


def is_camera_animated(camera):
    #---------------------------------------------------------#
    # Check if the USD camera is animated (transform or lens) #
    #                                                         #
    # camera = USD camera prim                                #
    #                                                         #
    # return True if the camera might vary over time          #
    #---------------------------------------------------------#

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
    #-------------------------------------------------------------------------------#
    # Get the frames of the Houdini camera keys, converted to the shot time         #
    #                                                                               #
    # camera = USD camera prim                                                      #
    # shot_range = shot frame range in the shot time                                #
    # time_offset = offset between the MASTER time and the shot time                #
    #                                                                               #
    # return the sorted list of keyed frames, or None if the keys were not exported #
    #-------------------------------------------------------------------------------#

    # Houdini key frames, written in customData when the layout is exported
    master_frames = camera.GetCustomData().get(USD_CAM_KEYFRAMES)
    if master_frames is None:
        return None

    start, end = int(shot_range[0]), int(shot_range[1])
    all_frames = {int(frame) - time_offset for frame in master_frames}
    frames = {frame for frame in all_frames if start <= frame <= end}
    # A key outside the shot affects the shot: its bound keeps the interpolated value
    if any(frame < start for frame in all_frames):
        frames.add(start)
    if any(frame > end for frame in all_frames):
        frames.add(end)
    return sorted(frames)


def get_camera_state(camera, frame):
    #----------------------------------------------------------------#
    # Get the transform and lens values of the USD camera at a frame #
    #                                                                #
    # camera = USD camera prim                                       #
    # frame = frame in the stage time (MASTER)                       #
    #                                                                #
    # return a tuple of floats (matrix values then lens values)      #
    #----------------------------------------------------------------#

    from pxr import Usd, UsdGeom

    time = Usd.TimeCode(frame)
    matrix = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(time)
    lens = UsdGeom.Camera(camera)
    lens_values = (
        lens.GetFocalLengthAttr().Get(time),
        lens.GetHorizontalApertureAttr().Get(time),
        lens.GetVerticalApertureAttr().Get(time),
        lens.GetHorizontalApertureOffsetAttr().Get(time),
        lens.GetVerticalApertureOffsetAttr().Get(time),
    )
    return tuple(matrix[i][j] for i in range(4) for j in range(4)) + tuple(v or 0.0 for v in lens_values)


def is_camera_static_between(camera, first, last, time_offset):
    #-----------------------------------------------------------------#
    # Check if the USD camera does not move on every frame of a range #
    #                                                                 #
    # camera = USD camera prim                                        #
    # first = first frame of the range in the shot time               #
    # last = last frame of the range in the shot time                 #
    # time_offset = offset between the MASTER time and the shot time  #
    #                                                                 #
    # return True if the camera has the same state on the whole range #
    #-----------------------------------------------------------------#

    reference = get_camera_state(camera, first + time_offset)
    for frame in range(int(first) + 1, int(last) + 1):
        state = get_camera_state(camera, frame + time_offset)
        if any(abs(a - b) > STATIC_TOLERANCE for a, b in zip(reference, state)):
            return False
    return True


def trim_static_frames(camera, frames, time_offset):
    #------------------------------------------------------------------------#
    # Remove the keys at the start and at the end of the shot where the      #
    # camera does not move, so the keys start on the first animated frame    #
    #                                                                        #
    # camera = USD camera prim                                               #
    # frames = sorted list of frames to key in the shot time                 #
    # time_offset = offset between the MASTER time and the shot time         #
    #                                                                        #
    # return the list of frames without the static keys at the start and end #
    #------------------------------------------------------------------------#

    frames = list(frames)
    # Maya holds the first and last key values outside of the keys
    while len(frames) > 1 and is_camera_static_between(camera, frames[0], frames[1], time_offset):
        del frames[0]
    while len(frames) > 1 and is_camera_static_between(camera, frames[-2], frames[-1], time_offset):
        del frames[-1]
    return frames


def match_frame(cam_transform, ctrls, stage_shape, camera, master_frame):
    #----------------------------------------------------------------------------------#
    # Match the DaisyCam to the USD camera at a given frame (position, rotation, lens) #
    #                                                                                  #
    # cam_transform = DaisyCam transform                                               #
    # ctrls = tuple (global_ctrl, pan_ctrl, tilt_ctrl) of the DaisyCam rig             #
    # stage_shape = mayaUsdProxyShape of the layout                                    #
    # camera = USD camera prim                                                         #
    # master_frame = frame in the MASTER time                                          #
    #----------------------------------------------------------------------------------#

    global_ctrl, pan_ctrl, tilt_ctrl = ctrls
    target = get_usd_camera_matrix(stage_shape, camera, master_frame)

    # Position first: the camera orientation depends on its position (aim)
    match_position(cam_transform, global_ctrl, target)

    # Rotation: pan for the yaw, tilt for the pitch
    target_yaw, target_pitch = get_yaw_pitch(list(target))
    match_pan(cam_transform, pan_ctrl, target_yaw)
    match_tilt(cam_transform, tilt_ctrl, target_pitch)

    match_position(cam_transform, global_ctrl, target)
    match_lens(cam_transform, camera, master_frame)


def key_daisy_cam(cam_transform, ctrls):
    #----------------------------------------------------------------------#
    # Set a key on the DaisyCam controllers and lens at the current frame  #
    #                                                                      #
    # cam_transform = DaisyCam transform                                   #
    # ctrls = tuple (global_ctrl, pan_ctrl, tilt_ctrl) of the DaisyCam rig #
    #----------------------------------------------------------------------#

    global_ctrl, pan_ctrl, tilt_ctrl = ctrls
    shape = cmds.listRelatives(cam_transform, shapes=True, type="camera", fullPath=True)[0]

    cmds.setKeyframe(global_ctrl, attribute=["translateX", "translateY", "translateZ"])
    cmds.setKeyframe(pan_ctrl, attribute="rotateY")
    cmds.setKeyframe(tilt_ctrl, attribute="rotateX")
    cmds.setKeyframe(shape, attribute=list(LENS_ATTRS))
    if cmds.attributeQuery("focalLength", node=cam_transform, exists=True):
        cmds.setKeyframe(cam_transform, attribute="focalLength")


def delete_static_keys(cam_transform, ctrls):
    #----------------------------------------------------------------------#
    # Remove the keys of the DaisyCam attributes that never change value,  #
    # the attribute keeps its constant value without animation curve       #
    #                                                                      #
    # cam_transform = DaisyCam transform                                   #
    # ctrls = tuple (global_ctrl, pan_ctrl, tilt_ctrl) of the DaisyCam rig #
    #----------------------------------------------------------------------#

    shape = cmds.listRelatives(cam_transform, shapes=True, type="camera", fullPath=True)[0]
    cmds.delete(list(ctrls) + [shape, cam_transform], staticChannels=True, hierarchy="none")


def match_daisy_cam_to_usd(cam_transform, stage_shape, sequence, shot, shot_range, master_range):
    #-------------------------------------------------------------------------------------#
    # Match the DaisyCam to the layout USD camera for the whole shot                      #
    # Static camera: placed once, animated camera: one key per Houdini key (or per frame) #
    #                                                                                     #
    # cam_transform = DaisyCam transform                                                  #
    # stage_shape = mayaUsdProxyShape of the layout                                       #
    # sequence = sequence name (e.g.: sq0010)                                             #
    # shot = shot name (e.g.: sh0010)                                                     #
    # shot_range = shot frame range in the shot time (or None)                            #
    # master_range = shot frame range in the MASTER time (or None)                        #
    #                                                                                     #
    # return the DaisyCam global_ctrl, or None if the camera or a controller is missing   #
    #-------------------------------------------------------------------------------------#

    camera_name = USD_CAM_NAME.format(sequence=sequence, shot=shot)
    camera = get_usd_camera(stage_shape, camera_name)
    if camera is None:
        return None

    ctrls = tuple(get_cam_ctrl(cam_transform, suffix, sequence, shot) for suffix in CAM_CTRL_SUFFIXES)
    if None in ctrls:
        return None

    if shot_range is None:
        # Without a frame range, stay in the master time over the whole stage duration
        stage = camera.GetStage()
        shot_range = master_range = [int(stage.GetStartTimeCode()), int(stage.GetEndTimeCode())]
        cmds.warning("Pas de frame range : DaisyCam calée sur le temps du master %s" % shot_range)

    time_offset = master_range[0] - shot_range[0]
    if not is_camera_animated(camera):
        match_frame(cam_transform, ctrls, stage_shape, camera, master_range[0])
        print("DaisyCam placée sur %s" % camera_name)
        return ctrls[0]

    # Animated camera: keys on the Houdini key frames, otherwise on every frame of the shot
    frames = get_camera_key_frames(camera, shot_range, time_offset)
    if frames is None:
        frames = list(range(int(shot_range[0]), int(shot_range[1]) + 1))
    frames = trim_static_frames(camera, frames, time_offset)
    if len(frames) <= 1:
        # No movement on this shot: the camera is static
        match_frame(cam_transform, ctrls, stage_shape, camera, (frames[0] if frames else shot_range[0]) + time_offset)
        print("DaisyCam placée sur %s (fixe sur le shot)" % camera_name)
        return ctrls[0]

    cmds.refresh(suspend=True)
    try:
        for frame in frames:
            cmds.currentTime(frame)
            match_frame(cam_transform, ctrls, stage_shape, camera, frame + time_offset)
            key_daisy_cam(cam_transform, ctrls)
        delete_static_keys(cam_transform, ctrls)
    finally:
        cmds.currentTime(shot_range[0])
        cmds.refresh(suspend=False)

    print("DaisyCam animée sur %s (%d clés)" % (camera_name, len(frames)))
    return ctrls[0]


def import_rig_source_scene(core, entity):
    #-----------------------------------------------------------------------#
    # Import the source scene of the latest version of the modeling product #
    #                                                                       #
    # core = Prism core                                                     #
    # entity = Prism entity dict of the asset                               #
    #                                                                       #
    # return the list of imported nodes, or None if the import failed       #
    #-----------------------------------------------------------------------#

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
    #-----------------------------------------------------------------------------#
    # Set up an anim scene: load the layout and match the DaisyCam to it          #
    # Load the shot layout master, or the MASTER shot layout master if none       #
    #                                                                             #
    # core = Prism core                                                           #
    # info = dict returned by get_entity_info()                                   #
    #                                                                             #
    # return a dict with the layout stage and the camera transform                #
    #-----------------------------------------------------------------------------#

    entity = info["entity"]
    sequence, shot = entity["sequence"], entity["shot"]

    shot_range, master_range = get_shot_ranges(sequence, shot)

    if get_master_path(core, entity, LAYOUT_PRODUCT):
        # The shot layout is already in the shot time: no time offset
        layout = import_master_usd(core, entity, LAYOUT_PRODUCT)
        master_range = shot_range
    else:
        core.popup(
            "No layout published on %s_%s.\nThe %s shot layout is imported instead." % (sequence, shot, MASTER_SHOT),
            title="Daisy import",
            severity="warning",
        )
        layout = import_master_usd(core, get_master_shot_entity(entity), LAYOUT_PRODUCT)
        if layout and shot_range:
            offset_stage_time(layout, shot_range, master_range)

    camera = import_daisy_cam(core, sequence, shot)
    default_prim = get_default_prim_name(layout) if layout else None
    if camera and default_prim:
        # Group named as the layout defaultPrim, above the DaisyCam_sqX_shX group
        camera = group_daisy_cam(camera, default_prim)
    if layout and camera:
        match_daisy_cam_to_usd(camera, layout, sequence, shot, shot_range, master_range)

    # Deactivate the USD cameras only once Maya is idle, after the DaisyCam keys are evaluated
    if layout:
        cmds.evalDeferred(lambda: deactivate_usd_cameras(layout), lowestPriority=True)

    return {"layout": layout, "camera": camera}


def setup_rig(core, info):
    #-----------------------------------------------------------------------#
    # Set up a rig scene: import the modeling source scene (RigL task only) #
    #                                                                       #
    # core = Prism core                                                     #
    # info = dict returned by get_entity_info()                             #
    #                                                                       #
    # return the list of imported nodes, or None                            #
    #-----------------------------------------------------------------------#

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
    #-----------------------------------------------------------------#
    # Entry point: run the setup of the current scene's department    #
    # Use SHOT_DEPARTMENTS for shots and ASSET_DEPARTMENTS for assets #
    #                                                                 #
    # return the setup result, or None if the department has no setup #
    #-----------------------------------------------------------------#

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


# Run from the script editor; the Prism shelf button calls import_asset() itself
if __name__ == "__main__":
    import_asset()
