import maya.cmds as cmds

from Scripts.DaisyTools.core.asset_browser_import import AssetBrowserUI
from Scripts.DaisyTools.setupAsset.maya.scene_loaders import get_latest_scene, reference_maya_scene
from Scripts.DaisyTools.setupAsset.maya.shot.layout import MASTER_SHOT

RIG_DEPARTMENT = "04_rig"
# Rig task referenced in each shot department, RigH if the department is not listed
RIG_SCENE_TASKS = {
    "02_layout": "RigL",
}
DEFAULT_RIG_SCENE_TASK = "RigH"
# Everything in the MASTER shot stays low: it is the whole sequence in one scene
MASTER_RIG_SCENE_TASK = "RigL"
SCENE_GROUP_NAME = "scene"

# ------------------------------------------------------------------------------ #
#                                 Rig references                                 #
# ------------------------------------------------------------------------------ #

def get_scene_group(shot_group):
    #---------------------------------------------------------------------------#
    # Get (or create) the group receiving the rigs: shot_group|scene            #
    #                                                                           #
    # shot_group = top group of the shot (name or long name), created if absent #
    #                                                                           #
    # return the scene group long name                                          #
    #---------------------------------------------------------------------------#

    if not cmds.objExists(shot_group):
        shot_group = cmds.group(empty=True, world=True, name=shot_group.lstrip("|"))
    shot_group = cmds.ls(shot_group, long=True)[0]

    scene_group = shot_group + "|" + SCENE_GROUP_NAME
    if not cmds.objExists(scene_group):
        scene_group = cmds.group(empty=True, parent=shot_group, name=SCENE_GROUP_NAME)
    return cmds.ls(scene_group, long=True)[0]


def group_rig_nodes(nodes, group):
    #-----------------------------------------------------------------#
    # Put the top level transforms of a referenced rig under a group  #
    #                                                                 #
    # nodes = list of the referenced nodes                            #
    # group = group to parent the rig under                           #
    #-----------------------------------------------------------------#

    roots = cmds.ls(nodes, assemblies=True, long=True) or []
    if roots:
        cmds.parent(roots, group)


def reference_rig_scenes(core, info, shot_group):
    #------------------------------------------------------------------------#
    # Open the Asset Browser and reference the latest rig scene of every     #
    # selected asset, then put it under shot_group|scene                     #
    # The rig task depends on the department (RigL in layout, RigH else),    #
    # and is always RigL in the MASTER shot                                  #
    #                                                                        #
    # core = Prism core                                                      #
    # info = dict returned by get_entity_info()                              #
    # shot_group = top group of the shot (e.g.: sq0010_sh0010)               #
    #                                                                        #
    # return the list of referenced scene paths                              #
    #------------------------------------------------------------------------#

    asset_browser = AssetBrowserUI(core=core, plugin=None)
    items = asset_browser.onAssetBrowserTriggered(info["entity"], info["task"], multiSelect=True)

    if info["entity"].get("shot") == MASTER_SHOT:
        rig_task = MASTER_RIG_SCENE_TASK
    else:
        rig_task = RIG_SCENE_TASKS.get(info["department"], DEFAULT_RIG_SCENE_TASK)
    referenced, missing = [], []
    scene_group = get_scene_group(shot_group) if items else None
    for item in items:
        if item.get("type") != "asset":
            continue

        entity = {"type": "asset", "asset_path": item["asset_path"], "asset": item["name"]}
        scene = get_latest_scene(core, entity, RIG_DEPARTMENT, rig_task)
        if not scene:
            cmds.warning("Aucune scène %s/%s pour %s" % (RIG_DEPARTMENT, rig_task, item["name"]))
            missing.append(item["name"])
            continue

        nodes = reference_maya_scene(scene)
        if nodes is not None:
            group_rig_nodes(nodes, scene_group)
            referenced.append(scene)

    if missing:
        core.popup(
            "No %s/%s scene found for:\n%s" % (RIG_DEPARTMENT, rig_task, "\n".join(missing)),
            title="Daisy import",
            severity="warning",
        )

    return referenced
