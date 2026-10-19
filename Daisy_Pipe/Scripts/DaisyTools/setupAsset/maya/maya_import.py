#------------------------------------------------------------------------------#
# Entry point of the Daisy import in Maya                                      #
# The setup of each department lives in its own module:                        #
#   scene_loaders.py        find Prism files, load USD stages and Maya scenes  #
#   shot/layout.py          layout USD stage and frame range                   #
#   shot/camera.py          DaisyCam import and matching on the USD camera     #
#   shot/rig_references.py  rigs of the assets chosen in the Asset Browser     #
#   shot/anim.py            02_layout and 03_anim setup                        #
#   asset/rig.py            04_rig setup                                       #
#------------------------------------------------------------------------------#

import importlib

from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.setupAsset.maya import scene_loaders
from Scripts.DaisyTools.setupAsset.maya.shot import layout, camera, rig_references, anim
from Scripts.DaisyTools.setupAsset.maya.asset import rig

# The shelf button reloads this module only: reload the others too, dependencies
# first, so that script changes are used without restarting Maya
for module in (scene_loaders, layout, camera, rig_references, anim, rig):
    importlib.reload(module)


SHOT_DEPARTMENTS = {
    # Same setup as the anim, only the referenced rig differs (see rig_references.py)
    "02_layout": anim.setup_anim,
    "03_anim": anim.setup_anim,
}

ASSET_DEPARTMENTS = {
    "04_rig": rig.setup_rig,
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
