#------------------------------------------------------------------------------#
# USD export of the animation of a shot (02_layout, 03_anim) from Maya          #
#                                                                              #
# The file is an overlay of the layout assembly: each rig's <asset>_geo group  #
# is written at the path of the same geo in the assembly                       #
#   /<shot>/scene/<asset>/<asset>/geo/<proxy|render>/<asset>_geo/<mesh>        #
# so that sublayering it over the layout puts the animation on the static USD  #
# The geo transform is computed relatively to the assembly: the asset stays    #
# where the animator put it, whatever the placement made in the layout         #
#------------------------------------------------------------------------------#

import os
import tempfile

from Scripts.DaisyTools.core.core import usdExportParams

LAYOUT_PRODUCT = "layout"
MASTER_SHOT = "MASTER"
SCENE_GROUP_NAME = "scene"
GEO_GROUP_SUFFIX = "_geo"
# Maya scene in cm, assembly in m
MAYA_TO_ASSEMBLY_SCALE = 0.01

# Rig task -> purpose of the asset geo it deforms (RigL rigs the ModL, RigH the ModH)
RIG_TASK_PURPOSES = {
    "RigL": "proxy",
    "RigH": "render",
}
DEFAULT_PURPOSE = "render"


# ------------------------------------------------------------------------------ #
#                                 Maya hierarchy                                 #
# ------------------------------------------------------------------------------ #

def find_scene_group():
    #-------------------------------------------------------------------#
    # Find the group receiving the rigs in the shot: |<shot>|scene      #
    #                                                                   #
    # return the scene group long name, or None if there is none        #
    #-------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    for top in cmds.ls(assemblies=True, long=True) or []:
        group = top + "|" + SCENE_GROUP_NAME
        if cmds.objExists(group):
            return group
    return None


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
    # return a list of dicts {asset, purpose, geo}                            #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    scene_group = find_scene_group()
    if scene_group is None:
        raise RuntimeError("Pas de groupe |<shot>|%s dans la scène : lance le Daisy import avant l'export." % SCENE_GROUP_NAME)

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

    if not rigs:
        raise RuntimeError("Aucun rig avec un groupe <asset>%s à exporter sous %s." % (GEO_GROUP_SUFFIX, scene_group))
    return rigs


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

    from Scripts.DaisyTools.setupAsset.maya.scene_loaders import get_master_path

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


def write_shot_anim_usd(core, entity, file_path, frame_range=None, overrides=None, nodes=None, shot_prim=None):
    #-------------------------------------------------------------------------------#
    # Write the anim of the shot rigs as an overlay of the layout assembly          #
    #                                                                               #
    # core = Prism core                                                             #
    # entity = Prism entity dict of the shot                                        #
    # file_path = path of the USD file to write                                     #
    # frame_range = (start, end) or None for the current frame                      #
    # overrides = extra mayaUSDExport flags (state UI)                              #
    # nodes = Maya Objects list of the export state, None = every rig               #
    # shot_prim = root prim name override (default: the shot assembly root)         #
    #                                                                               #
    # return the root prim name of the written file                                 #
    #-------------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from pxr import Gf, Sdf, Usd, UsdGeom

    rigs = get_rigs_to_export(core, nodes)

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
        parent = "%s/%s/%s/geo/%s" % (SCENE_GROUP_NAME, asset, asset, purpose)
        dst_path = Sdf.Path("/%s/%s/%s" % (shot_prim, parent, geo_name))

        # Ancestors as "over": they keep the assembly type and placement
        Sdf.CreatePrimInLayer(layer, dst_path.GetParentPath())
        Sdf.CopySpec(tmp_stage.GetRootLayer(), src_path, layer, dst_path)

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
        layout_parent = Sdf.Path("/%s/%s" % (layout_root, parent)) if layout_root else None
        op = xformable.AddTransformOp()
        for frame, maya_matrix in zip(frames, maya_matrices):
            parent_matrix = get_assembly_matrix(layout_stage, layout_parent, frame + time_offset)
            local = maya_matrix * unit * parent_matrix.GetInverse()
            op.Set(local, Usd.TimeCode(frame) if frame_range else Usd.TimeCode.Default())

        print("Anim exportée : %s -> %s" % (rig["geo"], dst_path))

    layer.defaultPrim = shot_prim
    if frame_range:
        layer.startTimeCode, layer.endTimeCode = frame_range
    layer.Export(file_path)

    tmp_stage = None
    try:
        os.remove(tmp_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    return shot_prim
