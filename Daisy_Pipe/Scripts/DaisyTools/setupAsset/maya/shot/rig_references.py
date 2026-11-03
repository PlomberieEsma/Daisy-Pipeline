import maya.cmds as cmds

from DaisyTools.core.asset_browser_import import AssetBrowserUI
from DaisyTools.setupAsset.maya.scene_loaders import get_latest_scene, reference_maya_scene
from DaisyTools.setupAsset.maya.shot.layout import MASTER_SHOT

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


def get_usd_asset_names(layout, shot_group):
    #---------------------------------------------------------------------------#
    # List the assets of the USD layout: the children of <defaultPrim>/scene    #
    # (e.g.: pufferfish, pufferfish02)                                          #
    #                                                                           #
    # layout = mayaUsdProxyShape of the layout (or None)                        #
    # shot_group = unused if the stage has a defaultPrim                        #
    #                                                                           #
    # return the list of the prim names, empty if there are none                #
    #---------------------------------------------------------------------------#

    if not layout:
        return []

    import mayaUsd.ufe

    stage = mayaUsd.ufe.getStage(cmds.ls(layout, long=True)[0])
    root = stage.GetDefaultPrim() if stage else None
    if not root:
        return []
    scene = root.GetChild(SCENE_GROUP_NAME)
    if not scene:
        return []
    return [prim.GetName() for prim in scene.GetAllChildren()]


def get_used_rig_names(scene_group):
    #---------------------------------------------------------------------#
    # Get the names already taken by the rigs of the scene group          #
    # (the namespace of the rig, or its node name without namespace)      #
    #                                                                     #
    # scene_group = scene group long name                                 #
    #                                                                     #
    # return a set of names                                               #
    #---------------------------------------------------------------------#

    used = set()
    for child in cmds.listRelatives(scene_group, children=True, fullPath=True) or []:
        short = child.split("|")[-1]
        used.add(short.split(":")[0])
    return used


def pick_usd_name(asset, usd_names, used):
    #--------------------------------------------------------------------------#
    # Pick the USD name the next reference of an asset must take               #
    # pufferfish matches pufferfish, pufferfish02, ... : the first one that    #
    # is not used yet                                                          #
    #                                                                          #
    # asset = asset name (e.g.: pufferfish)                                    #
    # usd_names = names of the assets of the USD layout                        #
    # used = names already taken in the Maya scene group                       #
    #                                                                          #
    # return the name, or None if every USD instance is already referenced     #
    #--------------------------------------------------------------------------#

    for name in usd_names:
        if name in used or cmds.namespace(exists=name):
            continue
        if name == asset or (name.startswith(asset) and name[len(asset):].isdigit()):
            return name
    return None


def reference_rig_scenes(core, info, shot_group, layout=None, ask=False):
    #------------------------------------------------------------------------#
    # Open the Asset Browser and reference the latest rig scene of every     #
    # selected asset, then put it under shot_group|scene                     #
    # The rig task depends on the department (RigL in layout, RigH else),    #
    # and is always RigL in the MASTER shot                                  #
    # The rig takes the name of its asset in the USD layout as namespace     #
    # (pufferfish, then pufferfish02 when it is referenced a second time)    #
    #                                                                        #
    # core = Prism core                                                      #
    # info = dict returned by get_entity_info()                              #
    # shot_group = top group of the shot (e.g.: sq0010_sh0010)               #
    # layout = mayaUsdProxyShape of the layout, gives the names (or None)    #
    # ask = True on a new click of the import button: ask before opening     #
    #       the Asset Browser instead of opening it directly                 #
    #                                                                        #
    # return the list of referenced scene paths                              #
    #------------------------------------------------------------------------#

    if ask:
        answer = core.popup(
            "The USD has been reloaded.\nDo you want to add a rig?",
            title="Daisy import",
            severity="question",
            buttons=["Yes", "No"],
            default="No",
        )
        if answer != "Yes":
            return []

    asset_browser = AssetBrowserUI(core=core, plugin=None)
    items = asset_browser.onAssetBrowserTriggered(info["entity"], info["task"], multiSelect=True)

    if info["entity"].get("shot") == MASTER_SHOT:
        rig_task = MASTER_RIG_SCENE_TASK
    else:
        rig_task = RIG_SCENE_TASKS.get(info["department"], DEFAULT_RIG_SCENE_TASK)
    referenced, missing = [], []
    scene_group = get_scene_group(shot_group) if items else None
    usd_names = get_usd_asset_names(layout, shot_group) if items else []
    used = get_used_rig_names(scene_group) if items else set()
    for item in items:
        if item.get("type") != "asset":
            continue

        entity = {"type": "asset", "asset_path": item["asset_path"], "asset": item["name"]}
        scene = get_latest_scene(core, entity, RIG_DEPARTMENT, rig_task)
        if not scene:
            cmds.warning("Aucune scène %s/%s pour %s" % (RIG_DEPARTMENT, rig_task, item["name"]))
            missing.append(item["name"])
            continue

        # Same name as the asset in the USD, ":" (no namespace) if the USD has none left
        usd_name = pick_usd_name(item["name"], usd_names, used)
        nodes = reference_maya_scene(scene, namespace=usd_name or ":")
        if nodes is not None:
            if usd_name:
                used.add(usd_name)
            group_rig_nodes(nodes, scene_group)
            referenced.append(scene)

    if missing:
        core.popup(
            "No %s/%s scene found for:\n%s" % (RIG_DEPARTMENT, rig_task, "\n".join(missing)),
            title="Daisy import",
            severity="warning",
        )

    return referenced
