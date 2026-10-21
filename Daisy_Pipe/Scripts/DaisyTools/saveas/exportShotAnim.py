#------------------------------------------------------------------------------#
# USD export of the animation of a shot (02_layout, 03_anim) from Maya          #
#                                                                              #
# The file is an overlay of the layout assembly: each rig's <asset>_geo group  #
# is written at the path of the same geo in the assembly                       #
#   /<shot>/scene/<asset>/<asset>/geo/<proxy|render>/<asset>_geo/<mesh>        #
# and each DaisyCam at the path of the same camera                             #
#   /<shot>/cam/DaisyCam_<seq>_<shot>/.../DaisyCam_<seq>_<shot>_camShape       #
# so that sublayering it over the layout puts the animation on the static USD  #
# The transforms are computed relatively to the assembly: the asset stays      #
# where the animator put it, whatever the placement made in the layout         #
#                                                                              #
# The MASTER shot works the same way, with the camera of each shot of the      #
# sequence under its cam group (see shot/anim.py)                              #
#------------------------------------------------------------------------------#

import os
import tempfile

from Scripts.DaisyTools.core.core import usdExportParams

LAYOUT_PRODUCT = "layout"
MASTER_SHOT = "MASTER"
SCENE_GROUP_NAME = "scene"
CAM_GROUP_NAME = "cam"
GEO_GROUP_SUFFIX = "_geo"
CAM_SHAPE_SUFFIX = "_camShape"
# defaultPrim of the asset USD, between <asset> and geo in the assembly:
# only used when the assembly cannot be read, it is looked up in it otherwise
ASSET_PRIM_SUFFIX = "_asset"
# Maya scene in cm, assembly in m
MAYA_TO_ASSEMBLY_SCALE = 0.01
# Lens: USD values x100 -> mm, Maya film back in inches (see shot/camera.py)
USD_LENS_SCALE = 100.0
MM_PER_INCH = 25.4
# Maya camera attribute -> USD camera attribute of the film back
FILM_BACK_ATTRS = {
    "horizontalFilmAperture": "horizontalAperture",
    "verticalFilmAperture": "verticalAperture",
    "horizontalFilmOffset": "horizontalApertureOffset",
    "verticalFilmOffset": "verticalApertureOffset",
}

# Rig task -> purpose of the asset geo it deforms (RigL rigs the ModL, RigH the ModH)
RIG_TASK_PURPOSES = {
    "RigL": "proxy",
    "RigH": "render",
}
DEFAULT_PURPOSE = "render"


# ------------------------------------------------------------------------------ #
#                                 Maya hierarchy                                 #
# ------------------------------------------------------------------------------ #

def find_shot_root():
    #-------------------------------------------------------------------------#
    # Find the top group of the shot: the assembly holding the scene and cam  #
    # groups of the Daisy import, named as the layout defaultPrim             #
    # (e.g.: sq0010_sh0010, sq0010_MASTER)                                    #
    #                                                                         #
    # return the group long name, or None if the Daisy import was not run     #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    for top in cmds.ls(assemblies=True, long=True) or []:
        if any(cmds.objExists(top + "|" + name) for name in (SCENE_GROUP_NAME, CAM_GROUP_NAME)):
            return top
    return None


def find_shot_group(name):
    #-------------------------------------------------------------------#
    # Find a group of the shot under its top group: |<shot>|<name>      #
    #                                                                   #
    # name = name of the group to find (scene or cam)                   #
    #                                                                   #
    # return the group long name, or None if there is none              #
    #-------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    root = find_shot_root()
    group = root + "|" + name if root else None
    return group if group and cmds.objExists(group) else None


def find_scene_group():
    #-------------------------------------------------------------------#
    # Find the group receiving the rigs in the shot: |<shot>|scene      #
    #                                                                   #
    # return the scene group long name, or None if there is none        #
    #-------------------------------------------------------------------#

    return find_shot_group(SCENE_GROUP_NAME)


def get_rig_asset(core, rig):
    #--------------------------------------------------------------------#
    # Get the asset name and the geo purpose of a rig in the scene group #
    # Read from the referenced rig scene, the node name if not found     #
    #                                                                    #
    # core = Prism core                                                  #
    # rig = long name of the rig top node                                #
    #                                                                    #
    # return a tuple (asset name, purpose)                               #
    #--------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    asset, task = None, None
    if cmds.referenceQuery(rig, isNodeReferenced=True):
        scene = cmds.referenceQuery(rig, filename=True, withoutCopyNumber=True)
        data = core.getScenefileData(scene) or {}
        asset, task = data.get("asset"), data.get("task")

    if not asset:
        asset = rig.split("|")[-1].split(":")[-1]
    return asset, RIG_TASK_PURPOSES.get(task, DEFAULT_PURPOSE)


def find_geo_group(rig, asset):
    #-----------------------------------------------------------#
    # Find the <asset>_geo group of the modeling inside a rig   #
    #                                                           #
    # rig = long name of the rig top node                       #
    # asset = asset name                                        #
    #                                                           #
    # return the geo group long name, or None if not found      #
    #-----------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    name = asset + GEO_GROUP_SUFFIX
    transforms = [rig] + (cmds.listRelatives(rig, allDescendents=True, type="transform", fullPath=True) or [])
    for transform in transforms:
        if transform.split("|")[-1].split(":")[-1] == name:
            return transform
    return None


def is_in_nodes(rig, nodes):
    #-----------------------------------------------------------------------#
    # Check if a rig is part of the Maya Objects list of the export state   #
    # A node above the rig (shot or scene group) selects all the rigs below #
    #                                                                       #
    # rig = long name of the rig top node                                   #
    # nodes = long names of the Maya Objects list                           #
    #-----------------------------------------------------------------------#

    return any(rig == n or rig.startswith(n + "|") or n.startswith(rig + "|") for n in nodes)


def get_rigs_to_export(core, nodes=None):
    #-------------------------------------------------------------------------#
    # List the rigs of the scene group and the geo group to export for each   #
    #                                                                         #
    # core = Prism core                                                       #
    # nodes = Maya Objects list of the export state, None = every rig         #
    #                                                                         #
    # return a list of dicts {asset, purpose, geo}, empty if there is no rig  #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    scene_group = find_scene_group()
    if scene_group is None:
        return []

    if nodes:
        nodes = cmds.ls(nodes, long=True) or []

    rigs, assets = [], set()
    for rig in cmds.listRelatives(scene_group, children=True, type="transform", fullPath=True) or []:
        if nodes and not is_in_nodes(rig, nodes):
            continue

        asset, purpose = get_rig_asset(core, rig)
        geo = find_geo_group(rig, asset)
        if geo is None:
            cmds.warning("Pas de groupe %s%s dans %s : rig non exporté" % (asset, GEO_GROUP_SUFFIX, rig))
            continue
        if asset in assets:
            cmds.warning("%s est présent plusieurs fois dans %s : seul le premier est exporté" % (asset, scene_group))
            continue

        assets.add(asset)
        rigs.append({"asset": asset, "purpose": purpose, "geo": geo})

    return rigs


# ------------------------------------------------------------------------------ #
#                                    Cameras                                     #
# ------------------------------------------------------------------------------ #

def find_camera_shape(rig):
    #------------------------------------------------------------------------#
    # Find the camera shape of a DaisyCam rig: <DaisyCam_sq_sh>_camShape     #
    #                                                                        #
    # rig = long name of the DaisyCam rig top node                           #
    #                                                                        #
    # return the camera shape long name, or None if the rig has no camera    #
    #------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    shapes = cmds.listRelatives(rig, allDescendents=True, type="camera", fullPath=True) or []
    name = rig.split("|")[-1].split(":")[-1] + CAM_SHAPE_SUFFIX
    for shape in shapes:
        if shape.split("|")[-1].split(":")[-1] == name:
            return shape
    # A renamed camera is still exported, as long as the rig holds only one
    return shapes[0] if len(shapes) == 1 else None


def get_cameras_to_export(nodes=None):
    #-------------------------------------------------------------------------#
    # List the DaisyCams of the cam group and the camera shape of each one    #
    # The MASTER holds one DaisyCam per shot of the sequence                  #
    #                                                                         #
    # nodes = Maya Objects list of the export state, None = every DaisyCam    #
    #                                                                         #
    # return a list of dicts {rig, shape}, empty if there is no DaisyCam      #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    cam_group = find_shot_group(CAM_GROUP_NAME)
    if cam_group is None:
        return []

    if nodes:
        nodes = cmds.ls(nodes, long=True) or []

    cameras = []
    for rig in cmds.listRelatives(cam_group, children=True, type="transform", fullPath=True) or []:
        if nodes and not is_in_nodes(rig, nodes):
            continue

        shape = find_camera_shape(rig)
        if shape is None:
            cmds.warning("Pas de caméra %s dans %s : caméra non exportée" % (CAM_SHAPE_SUFFIX, rig))
            continue
        cameras.append({"rig": rig, "shape": shape})

    return cameras


def get_shot_anim_nodes(core):
    #-------------------------------------------------------------------------#
    # Nodes to fill the Maya Objects list of the export state with: the geo   #
    # group of every rig of |<shot>|scene and of every DaisyCam of |<shot>|cam#
    # (a node inside a rig exports that whole rig, see is_in_nodes)           #
    #                                                                         #
    # core = Prism core                                                       #
    #                                                                         #
    # return a list of long names, empty if the Daisy import was not run      #
    #-------------------------------------------------------------------------#

    nodes = [rig["geo"] for rig in get_rigs_to_export(core)]
    for camera in get_cameras_to_export():
        rig = camera["rig"]
        # The DaisyCam rig has its own geo group: DaisyCam_<seq>_<shot>_geo
        nodes.append(find_geo_group(rig, rig.split("|")[-1].split(":")[-1]) or rig)
    return nodes


# ------------------------------------------------------------------------------ #
#                                    Assembly                                    #
# ------------------------------------------------------------------------------ #

def get_layout(core, entity):
    #-------------------------------------------------------------------------------#
    # Get the layout the anim is put on, as the Daisy import loads it in Maya       #
    # The shot layout master, or the MASTER shot layout master with a time offset   #
    #                                                                               #
    # core = Prism core                                                             #
    # entity = Prism entity dict of the shot                                        #
    #                                                                               #
    # return a tuple (layout path or None, time offset shot -> layout,              #
    #                 True if it is the shot layout, False if the MASTER one)       #
    #-------------------------------------------------------------------------------#

    # From core.core and not from the Maya scene_loaders: the Houdini import
    # reuses this function to load the layout the overlay was exported on
    from Scripts.DaisyTools.core.core import get_master_path

    path = get_master_path(core, entity, LAYOUT_PRODUCT)
    if path:
        return path, 0, True

    master_entity = {"type": "shot", "sequence": entity["sequence"], "shot": MASTER_SHOT}
    if "episode" in entity:
        master_entity["episode"] = entity["episode"]
    path = get_master_path(core, master_entity, LAYOUT_PRODUCT)
    if not path:
        return None, 0, False

    try:
        from Scripts.DaisyTools.core.framerange_convert import FramerangeFile
        framerange = FramerangeFile()
        offset = framerange.get_master_range(entity["sequence"], entity["shot"])[0] - framerange.get_shot_range(entity["sequence"], entity["shot"])[0]
    except Exception as e:
        print("Frame range introuvable pour %s_%s, pas de décalage de temps (%s)" % (entity["sequence"], entity["shot"], e))
        offset = 0
    return path, offset, False


def get_shot_prim_name(entity, layout_root, is_shot_layout):
    #------------------------------------------------------------------------#
    # Get the root prim of the shot assembly the anim must be written under  #
    # The root of the shot layout, or the shot name if it is not published   #
    # (the MASTER layout root is renamed to the shot name in the shot layout)#
    #                                                                        #
    # entity = Prism entity dict of the shot                                 #
    # layout_root = defaultPrim name of the loaded layout (or None)          #
    # is_shot_layout = True if the loaded layout is the shot one             #
    #------------------------------------------------------------------------#

    from pxr import Tf

    if is_shot_layout and layout_root:
        return layout_root
    return Tf.MakeValidIdentifier("%s-%s" % (entity["sequence"], entity["shot"]))


def find_layout_geo_path(layout_stage, layout_root, asset, purpose):
    #-------------------------------------------------------------------------------#
    # Path of the static geo of an asset in the layout assembly, relative to the    #
    # root prim of the assembly:                                                    #
    #   scene/<asset>/<asset prim>/geo/<proxy|render>/<asset>_geo                   #
    # <asset prim> is the defaultPrim of the asset USD referenced by the layout     #
    # (e.g.: <asset>_asset): it is read in the assembly, never guessed              #
    #                                                                               #
    # layout_stage = stage of the layout assembly (or None)                         #
    # layout_root = defaultPrim name of the layout (or None)                        #
    # asset = asset name                                                            #
    # purpose = geo purpose of the rig (proxy for RigL, render for RigH)            #
    #                                                                               #
    # return the path relative to the root prim, as a string                        #
    #-------------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from pxr import Sdf, Usd

    geo_name = asset + GEO_GROUP_SUFFIX
    default = "%s/%s/%s%s/geo/%s/%s" % (SCENE_GROUP_NAME, asset, asset, ASSET_PRIM_SUFFIX, purpose, geo_name)

    root = Sdf.Path("/" + layout_root) if layout_root else None
    asset_prim = layout_stage.GetPrimAtPath(root.AppendPath("%s/%s" % (SCENE_GROUP_NAME, asset))) if layout_stage and root else None
    if not asset_prim:
        cmds.warning("%s introuvable dans le layout : l'anim est écrite sous %s" % (asset, default))
        return default

    # <asset>_geo of every purpose published for this asset
    geos = {}
    for prim in Usd.PrimRange(asset_prim):
        path = prim.GetPath()
        if prim.GetName() == geo_name and path.GetParentPath().GetParentPath().name == "geo":
            geos[path.GetParentPath().name] = path

    path = geos.get(purpose)
    if path is None:
        # The rig deforms a geo that the layout does not have: the other purpose is better than nothing
        path = next(iter(sorted(geos.values())), None)
        if path is None:
            cmds.warning("Pas de %s sous %s dans le layout : l'anim est écrite sous %s" % (geo_name, asset_prim.GetPath(), default))
            return default
        cmds.warning("Pas de geo %s pour %s dans le layout : l'anim est écrite sur %s" % (purpose, asset, path))

    return str(path.MakeRelativePath(root))


# ------------------------------------------------------------------------------ #
#                                     Export                                     #
# ------------------------------------------------------------------------------ #

def export_geo_groups(file_path, geo_groups, frame_range=None, overrides=None):
    #-------------------------------------------------------------------------#
    # Export the geo groups in world space, each one as a root prim           #
    # Same mesh settings as the modeling export so the mesh paths match       #
    #                                                                         #
    # file_path = path of the USD file to write                               #
    # geo_groups = long names of the geo groups                               #
    # frame_range = (start, end) or None for the current frame                #
    # overrides = extra mayaUSDExport flags (state UI)                        #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    if not cmds.pluginInfo("mayaUsdPlugin", q=True, loaded=True):
        cmds.loadPlugin("mayaUsdPlugin")

    config = dict(usdExportParams["common"])
    config.update(usdExportParams["presets"]["mod"])
    if overrides:
        config.update(overrides)

    config["file"] = file_path
    config["exportRoots"] = list(geo_groups)
    config["selection"] = False
    config["worldspace"] = True
    config["stripNamespaces"] = True
    if frame_range:
        config["frameRange"] = list(frame_range)

    cmds.mayaUSDExport(**config)


def get_assembly_matrix(layout_stage, prim_path, time):
    #------------------------------------------------------------------------#
    # Get the world matrix of a prim of the assembly (identity if not found) #
    #------------------------------------------------------------------------#

    from pxr import Gf, Usd, UsdGeom

    prim = layout_stage.GetPrimAtPath(prim_path) if layout_stage else None
    if not prim:
        return Gf.Matrix4d(1.0)
    return UsdGeom.XformCache(Usd.TimeCode(time)).GetLocalToWorldTransform(prim)


def get_camera_prim_path(shape, root_prim):
    #-------------------------------------------------------------------------------#
    # Path of a DaisyCam camera in the assembly, under a root prim                  #
    # The layout camera is created with the hierarchy of the Maya rig               #
    # (see hda_scripts/create_cam.py):                                              #
    #   /<root>/cam/DaisyCam_sq_sh/.../DaisyCam_sq_sh_cam/DaisyCam_sq_sh_camShape   #
    #                                                                               #
    # shape = long name of the Maya camera shape                                    #
    # root_prim = root prim of the assembly the path is written under               #
    #-------------------------------------------------------------------------------#

    from pxr import Sdf

    # Maya path without the shot group, namespaces stripped as in the geo export
    parts = [part.split(":")[-1] for part in shape.split("|") if part][1:]
    return Sdf.Path("/" + "/".join([root_prim] + parts))


def get_camera_matrix(transform, frame):
    #-------------------------------------------------------------------------#
    # World matrix of a Maya camera at a frame, in the assembly units         #
    # Only the position and the orientation are kept, not the rig scale       #
    #                                                                         #
    # transform = long name of the Maya camera transform                      #
    # frame = frame in the scene time                                         #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from pxr import Gf

    # getAttr evaluates the frame without moving the time slider
    matrix = Gf.Matrix4d(*cmds.getAttr(transform + ".worldMatrix[0]", time=frame)).RemoveScaleShear()
    return matrix.SetTranslateOnly(matrix.ExtractTranslation() * MAYA_TO_ASSEMBLY_SCALE)


def get_camera_lens(shape, frame):
    #-------------------------------------------------------------------------#
    # Lens values of a Maya camera at a frame, converted to the USD units     #
    # Inverse of the conversion made at the import (see shot/camera.py)       #
    #                                                                         #
    # shape = long name of the Maya camera shape                              #
    # frame = frame in the scene time                                         #
    #                                                                         #
    # return a dict {USD camera attribute name: value}                        #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    lens = {"focalLength": cmds.getAttr(shape + ".focalLength", time=frame) / USD_LENS_SCALE}
    for attr, usd_attr in FILM_BACK_ATTRS.items():
        # Maya film back in inches -> mm, then mm -> USD units
        lens[usd_attr] = cmds.getAttr(shape + "." + attr, time=frame) * MM_PER_INCH / USD_LENS_SCALE
    return lens


def write_camera_anim(stage, layer, camera, dst_path, layout_parent, layout_stage, frames, frame_range, time_offset):
    #-------------------------------------------------------------------------------#
    # Write the anim of a DaisyCam at the path of the camera of the assembly        #
    # The transform and the lens override the ones published in the layout          #
    #                                                                               #
    # stage = stage of the overlay being written                                    #
    # layer = root layer of that stage                                              #
    # camera = dict {rig, shape} of the DaisyCam (see get_cameras_to_export)        #
    # dst_path = path of the camera in the overlay                                  #
    # layout_parent = path of the camera parent in the assembly (or None)           #
    # layout_stage = stage of the layout assembly (or None)                         #
    # frames = frames to write                                                      #
    # frame_range = (start, end) or None to write a single value                    #
    # time_offset = time offset between the shot time and the assembly time         #
    #-------------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from pxr import Sdf, Usd, UsdGeom

    shape = camera["shape"]
    transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]

    # Ancestors as "over": they keep the assembly type and placement
    Sdf.CreatePrimInLayer(layer, dst_path.GetParentPath())
    spec = Sdf.CreatePrimInLayer(layer, dst_path)
    spec.specifier = Sdf.SpecifierDef
    spec.typeName = "Camera"

    usd_camera = UsdGeom.Camera(stage.GetPrimAtPath(dst_path))
    op = usd_camera.MakeMatrixXform()
    lens_attrs = {
        "focalLength": usd_camera.CreateFocalLengthAttr(),
        "horizontalAperture": usd_camera.CreateHorizontalApertureAttr(),
        "verticalAperture": usd_camera.CreateVerticalApertureAttr(),
        "horizontalApertureOffset": usd_camera.CreateHorizontalApertureOffsetAttr(),
        "verticalApertureOffset": usd_camera.CreateVerticalApertureOffsetAttr(),
    }

    for frame in frames:
        time = Usd.TimeCode(frame) if frame_range else Usd.TimeCode.Default()
        # Local matrix so that the camera ends up at its Maya position, whatever the
        # placement of its parents in the assembly: local * parent world = Maya world
        parent_matrix = get_assembly_matrix(layout_stage, layout_parent, frame + time_offset)
        op.Set(get_camera_matrix(transform, frame) * parent_matrix.GetInverse(), time)
        for name, value in get_camera_lens(shape, frame).items():
            lens_attrs[name].Set(value, time)


def write_shot_anim_usd(core, entity, file_path, frame_range=None, overrides=None, nodes=None, shot_prim=None):
    #-------------------------------------------------------------------------------#
    # Write the anim of the shot rigs and DaisyCams as an overlay of the layout     #
    #                                                                               #
    # core = Prism core                                                             #
    # entity = Prism entity dict of the shot                                        #
    # file_path = path of the USD file to write                                     #
    # frame_range = (start, end) or None for the current frame                      #
    # overrides = extra mayaUSDExport flags (state UI)                              #
    # nodes = Maya Objects list of the export state, None = every rig and camera    #
    # shot_prim = root prim name override (default: the shot assembly root)         #
    #                                                                               #
    # return the root prim name of the written file                                 #
    #-------------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from pxr import Gf, Sdf, Usd, UsdGeom

    rigs = get_rigs_to_export(core, nodes)
    cameras = get_cameras_to_export(nodes)
    if not rigs and not cameras:
        raise RuntimeError(
            "Rien à exporter : pas de rig sous |<shot>|%s ni de DaisyCam sous |<shot>|%s.\n"
            "Lance le Daisy import avant l'export." % (SCENE_GROUP_NAME, CAM_GROUP_NAME)
        )

    layout_path, time_offset, is_shot_layout = get_layout(core, entity)
    if layout_path:
        layout_stage = Usd.Stage.Open(layout_path)
        layout_root = layout_stage.GetDefaultPrim().GetName() if layout_stage.GetDefaultPrim() else None
    else:
        cmds.warning("Pas de layout publié pour %s : l'anim est exportée sans compenser l'assembly" % entity)
        layout_stage, layout_root = None, None
    shot_prim = shot_prim or get_shot_prim_name(entity, layout_root, is_shot_layout)

    if frame_range:
        frames = list(range(int(frame_range[0]), int(frame_range[1]) + 1))
    else:
        frames = [cmds.currentTime(query=True)]

    # The rigs go through a Maya USD export, the cameras are written directly
    tmp_dir, tmp_path, tmp_stage = None, None, None
    if rigs:
        tmp_dir = tempfile.mkdtemp(prefix="daisy_anim_")
        tmp_path = os.path.join(tmp_dir, "anim.usdc")
        export_geo_groups(tmp_path, [rig["geo"] for rig in rigs], frame_range, overrides)
        tmp_stage = Usd.Stage.Open(tmp_path)

    layer = Sdf.Layer.CreateAnonymous(".usda")
    stage = Usd.Stage.Open(layer)
    unit = Gf.Matrix4d(1.0).SetScale(MAYA_TO_ASSEMBLY_SCALE)

    for rig in rigs:
        asset, purpose = rig["asset"], rig["purpose"]
        geo_name = asset + GEO_GROUP_SUFFIX
        src_path = Sdf.Path("/" + geo_name)
        if not tmp_stage.GetPrimAtPath(src_path):
            cmds.warning("%s absent de l'export Maya : %s ignoré" % (src_path, asset))
            continue

        # Path of the static geo in the assembly
        geo_path = find_layout_geo_path(layout_stage, layout_root, asset, purpose)
        dst_path = Sdf.Path("/%s/%s" % (shot_prim, geo_path))

        # Ancestors as "over": they keep the assembly type and placement
        Sdf.CreatePrimInLayer(layer, dst_path.GetParentPath())
        Sdf.CopySpec(tmp_stage.GetRootLayer(), src_path, layer, dst_path)

        # The kind of the assembly wins: the geo group of a Maya export is a component,
        # the layout has none there (its components are the asset prims above)
        geo_spec = layer.GetPrimAtPath(dst_path)
        if geo_spec.HasInfo("kind"):
            geo_spec.ClearInfo("kind")

        # world matrices of the Maya geo, before its xformOps are replaced
        src_xform = UsdGeom.Xformable(tmp_stage.GetPrimAtPath(src_path))
        maya_matrices = [src_xform.ComputeLocalToWorldTransform(Usd.TimeCode(f)) for f in frames]

        prim = stage.GetPrimAtPath(dst_path)
        xformable = UsdGeom.Xformable(prim)
        xformable.ClearXformOpOrder()
        for attr in prim.GetAuthoredAttributes():
            if attr.GetName().startswith("xformOp:"):
                prim.RemoveProperty(attr.GetName())

        # Local matrix so that the geo ends up at its Maya position, whatever the
        # placement of its parents in the assembly: local * parent world = Maya world
        layout_parent = Sdf.Path("/%s/%s" % (layout_root, geo_path)).GetParentPath() if layout_root else None
        op = xformable.AddTransformOp()
        for frame, maya_matrix in zip(frames, maya_matrices):
            parent_matrix = get_assembly_matrix(layout_stage, layout_parent, frame + time_offset)
            local = maya_matrix * unit * parent_matrix.GetInverse()
            op.Set(local, Usd.TimeCode(frame) if frame_range else Usd.TimeCode.Default())

        print("Anim exportée : %s -> %s" % (rig["geo"], dst_path))

    for camera in cameras:
        # The camera keeps the path of the layout camera: same rig hierarchy
        dst_path = get_camera_prim_path(camera["shape"], shot_prim)
        layout_parent = get_camera_prim_path(camera["shape"], layout_root).GetParentPath() if layout_root else None
        write_camera_anim(stage, layer, camera, dst_path, layout_parent, layout_stage, frames, frame_range, time_offset)
        print("Caméra exportée : %s -> %s" % (camera["shape"], dst_path))

    layer.defaultPrim = shot_prim
    if frame_range:
        layer.startTimeCode, layer.endTimeCode = frame_range
    layer.Export(file_path)

    tmp_stage = None
    if tmp_path:
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return shot_prim
