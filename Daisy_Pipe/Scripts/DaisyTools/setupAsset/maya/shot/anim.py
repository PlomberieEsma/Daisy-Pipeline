import maya.cmds as cmds

from Scripts.DaisyTools.setupAsset.maya.shot.camera import create_camera_sequence, get_usd_camera_ranges, get_usd_camera_shots, group_daisy_cam, import_daisy_cam, match_daisy_cam_to_usd
from Scripts.DaisyTools.setupAsset.maya.shot.layout import MASTER_SHOT, deactivate_usd_cameras, get_default_prim_name, get_shot_ranges, load_shot_layout
from Scripts.DaisyTools.setupAsset.maya.shot.rig_references import reference_rig_scenes

# Departments where the MASTER shot gets a Camera Sequencer with its DaisyCams
CAMERA_SEQUENCE_DEPARTMENTS = ("02_layout", "03_anim")


# ------------------------------------------------------------------------------ #
#                                      Anim                                      #
# ------------------------------------------------------------------------------ #

def setup_daisy_cam(core, layout, group_name, sequence, shot, shot_range, master_range):
    #-----------------------------------------------------------------------------#
    # Import a DaisyCam for a shot, group it and match it to the USD camera       #
    #                                                                             #
    # core = Prism core                                                           #
    # layout = mayaUsdProxyShape of the layout (or None)                          #
    # group_name = name of the top group (layout defaultPrim, or None)            #
    # sequence = sequence name (e.g.: sq0010)                                     #
    # shot = shot name (e.g.: sh0010)                                             #
    # shot_range = shot frame range in the scene time (or None)                   #
    # master_range = shot frame range in the MASTER time (or None)                #
    #                                                                             #
    # return the DaisyCam transform, or None if the import failed                 #
    #-----------------------------------------------------------------------------#

    camera = import_daisy_cam(core, sequence, shot)
    if camera and group_name:
        # Group named as the layout defaultPrim, above the DaisyCam_sqX_shX group
        camera = group_daisy_cam(camera, group_name)
    if layout and camera:
        match_daisy_cam_to_usd(camera, layout, sequence, shot, shot_range, master_range)
    return camera


def setup_anim(core, info):
    #-----------------------------------------------------------------------------#
    # Set up an anim scene: load the layout and match the DaisyCam to it          #
    # Load the shot layout master, or the MASTER shot layout master if none       #
    # In the MASTER shot, one DaisyCam is imported per shot camera of the USD     #
    # (and a Camera Sequencer is created with them in layout and anim)            #
    #                                                                             #
    # core = Prism core                                                           #
    # info = dict returned by get_entity_info()                                   #
    #                                                                             #
    # return a dict with the layout stage and the camera transforms               #
    #-----------------------------------------------------------------------------#

    entity = info["entity"]
    sequence, shot = entity["sequence"], entity["shot"]

    layout, shot_range, master_range = load_shot_layout(core, entity)
    default_prim = get_default_prim_name(layout) if layout else None

    if shot == MASTER_SHOT and layout:
        # The MASTER scene is in the MASTER time: each camera uses its MASTER range
        # Ranges from the camera keys, the frame range file is only a fallback
        cam_shot_names = get_usd_camera_shots(layout, sequence)
        cam_ranges = get_usd_camera_ranges(layout, sequence, cam_shot_names)
        cam_shots = []
        for cam_shot in cam_shot_names:
            cam_range = cam_ranges.get(cam_shot) or get_shot_ranges(sequence, cam_shot)[1]
            camera = setup_daisy_cam(core, layout, default_prim, sequence, cam_shot, cam_range, cam_range)
            if camera:
                cam_shots.append((cam_shot, camera, cam_range))
        cameras = [camera for _, camera, _ in cam_shots]

        # MASTER layout/anim: Camera Sequencer switching between the DaisyCams over the sequence
        if info["department"] in CAMERA_SEQUENCE_DEPARTMENTS:
            create_camera_sequence(cam_shots, sequence)
    else:
        camera = setup_daisy_cam(core, layout, default_prim, sequence, shot, shot_range, master_range)
        cameras = [camera] if camera else []

    # Rigs of the assets selected in the Asset Browser, under the shot group|scene
    if cameras and default_prim:
        shot_group = "|" + cameras[0].split("|")[1]
    else:
        shot_group = None
    rigs = reference_rig_scenes(core, info, shot_group or default_prim or "%s_%s" % (sequence, shot))

    # Deactivate the USD cameras only once Maya is idle, after the DaisyCam keys are evaluated
    if layout:
        cmds.evalDeferred(lambda: deactivate_usd_cameras(layout), lowestPriority=True)

    return {"layout": layout, "camera": cameras[0] if cameras else None, "cameras": cameras, "rigs": rigs}
