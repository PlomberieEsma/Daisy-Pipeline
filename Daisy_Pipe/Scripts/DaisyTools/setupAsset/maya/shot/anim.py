import maya.cmds as cmds

from Scripts.DaisyTools.setupAsset.maya.scene_loaders import get_master_path
from Scripts.DaisyTools.setupAsset.maya.shot.camera import group_daisy_cam, import_daisy_cam, match_daisy_cam_to_usd
from Scripts.DaisyTools.setupAsset.maya.shot.layout import LAYOUT_PRODUCT, MASTER_SHOT, deactivate_usd_cameras, get_default_prim_name, get_master_shot_entity, get_shot_ranges, import_master_usd, offset_stage_time
from Scripts.DaisyTools.setupAsset.maya.shot.rig_references import reference_rig_scenes


# ------------------------------------------------------------------------------ #
#                                      Anim                                      #
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

    # Rigs of the assets selected in the Asset Browser, under the shot group|scene
    if camera and default_prim:
        shot_group = "|" + camera.split("|")[1]
    else:
        shot_group = None
    rigs = reference_rig_scenes(core, info, shot_group or default_prim or "%s_%s" % (sequence, shot))

    # Deactivate the USD cameras only once Maya is idle, after the DaisyCam keys are evaluated
    if layout:
        cmds.evalDeferred(lambda: deactivate_usd_cameras(layout), lowestPriority=True)

    return {"layout": layout, "camera": camera, "rigs": rigs}
