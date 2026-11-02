import math
import os
import re
import maya.cmds as cmds
import maya.api.OpenMaya as om

from Scripts.DaisyTools.core.core import CAMERA_RIG_PREFIX, USD_CAM_KEYFRAMES, get_camera_file
from Scripts.DaisyTools.setupAsset.maya.shot.layout import set_playback_range

DAISY_CAM_PATH = ("Integration", "otls", "DaisyCam.mb")
CAM_GROUP_NAME = "cam"
CAM_SEQUENCE_TOKEN =re.compile("sqX", re.IGNORECASE)
CAM_SHOT_TOKEN = re.compile("shX", re.IGNORECASE)
CAM_GLOBAL_CTRL_SUFFIX = "_{sequence}_{shot}_global_ctrl"
CAM_PAN_CTRL_SUFFIX = "_{sequence}_{shot}_pan_ctrl"
CAM_TILT_CTRL_SUFFIX = "_{sequence}_{shot}_tilt_ctrl"
CAM_CTRL_SUFFIXES = (CAM_GLOBAL_CTRL_SUFFIX, CAM_PAN_CTRL_SUFFIX, CAM_TILT_CTRL_SUFFIX)
USD_CAM_NAME = "DaisyCam_{sequence}_{shot}_camShape"
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
#                                DaisyCam import                                 #
# ------------------------------------------------------------------------------ #

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


def offset_camera_keys(nodes, shot_range, master_range):
    #-----------------------------------------------------------------------------#
    # Move the keys of an imported camera from the MASTER time to the shot time   #
    # The camera is always published from the MASTER scene, so its keys are in    #
    # the MASTER time whatever the layout the shot loads                          #
    #                                                                             #
    # nodes = nodes of the imported camera                                        #
    # shot_range = shot frame range in the shot time (or None)                    #
    # master_range = same range in the MASTER time (or None)                      #
    #-----------------------------------------------------------------------------#

    if not shot_range or not master_range:
        return

    offset = int(master_range[0]) - int(shot_range[0])
    if not offset:
        return

    # Only the curves driven by time: a driven key (animCurveU*) has no time input
    # and shifting it would break the rig
    curves = cmds.listConnections(nodes, type="animCurve", source=True, destination=False) or []
    curves = sorted({curve for curve in curves if cmds.nodeType(curve).startswith("animCurveT")})
    if curves:
        cmds.keyframe(curves, edit=True, relative=True, timeChange=-offset)


def get_rig_of_camera(cam_transform):
    #-----------------------------------------------------------------------------#
    # Top DaisyCam group above a camera transform, i.e. the rig itself            #
    #                                                                             #
    # cam_transform = long name of the camera transform                           #
    #                                                                             #
    # return the long name of the rig, or None if the camera is not in one        #
    #-----------------------------------------------------------------------------#

    parts = cmds.ls(cam_transform, long=True)[0].split("|")
    for index, name in enumerate(parts):
        if name.split(":")[-1].startswith(CAMERA_RIG_PREFIX):
            return "|".join(parts[:index + 1])
    return None


def drop_imported_groups(uuids, rig):
    #-----------------------------------------------------------------------------#
    # Move an imported rig to the world and remove the groups that came with it   #
    # A published camera is written with exportSelected, which keeps the ancestors#
    # of the selection: the file carries the groups of the MASTER scene. They are #
    # dropped here, group_daisy_cam puts the rig under the groups of this scene   #
    #                                                                             #
    # uuids = uuids of the imported nodes, valid across the reparenting           #
    # rig = long name of the imported rig                                         #
    #                                                                             #
    # return the long name of the rig once it is at the world                     #
    #-----------------------------------------------------------------------------#

    if cmds.listRelatives(rig, parent=True):
        # relative: the groups of the MASTER are empty groups left at the origin,
        # so keeping the local values keeps the camera where it was
        rig = cmds.ls(cmds.parent(rig, world=True, relative=True), long=True)[0]

    # Only the imported transforms, never the anim curves, and only those left
    # outside the rig: they are the groups it was exported under
    leftovers = []
    for uuid in uuids:
        nodes = cmds.ls(uuid, long=True, type="transform") or []
        if nodes and nodes[0] != rig and not nodes[0].startswith(rig + "|"):
            leftovers.append(nodes[0])

    # Deepest first, and never a group that still holds something
    for node in sorted(leftovers, key=lambda path: path.count("|"), reverse=True):
        if cmds.objExists(node) and not cmds.listRelatives(node, children=True):
            cmds.delete(node)

    return rig


def import_shot_camera(core, entity, shot_range=None, master_range=None):
    #-----------------------------------------------------------------------------#
    # Import the camera published for the shot by the MASTER scene                #
    # The file holds the DaisyCam rig already animated and already named for the  #
    # shot: nothing to rename, and nothing to match on the USD camera             #
    #                                                                             #
    # core = Prism core                                                           #
    # entity = Prism entity dict of the shot                                      #
    # shot_range = shot frame range in the shot time (or None)                    #
    # master_range = same range in the MASTER time (or None)                      #
    #                                                                             #
    # return the camera transform, or None if no camera is published              #
    #-----------------------------------------------------------------------------#

    cam_path = get_camera_file(core, entity)
    if not cam_path:
        return None

    new_nodes = cmds.file(
        cam_path,
        i=True,
        type="mayaBinary",
        namespace=":",
        returnNewNodes=True,
        ignoreVersion=True,
    )
    # UUIDs stay valid once the rig is moved under another parent
    uuids = cmds.ls(new_nodes, uuid=True) or []

    offset_camera_keys(new_nodes, shot_range, master_range)

    cameras = cmds.ls(new_nodes, type="camera", long=True) or []
    cam_transforms = cmds.listRelatives(cameras, parent=True, fullPath=True) or []
    if not cam_transforms:
        cmds.warning("No camera in the published file: %s" % cam_path)
        return None

    camera_uuid = cmds.ls(cam_transforms[0], uuid=True)[0]
    rig = get_rig_of_camera(cam_transforms[0])
    if rig:
        drop_imported_groups(uuids, rig)
    else:
        cmds.warning("No %s group above %s: the camera is imported as is" % (CAMERA_RIG_PREFIX, cam_transforms[0]))

    print("Camera imported: %s" % cam_path)
    return cmds.ls(camera_uuid, long=True)[0]


def group_daisy_cam(cam_transform, group_name):
    #-------------------------------------------------------------------------#
    # Put the DaisyCam root group (DaisyCam_sqX_shX) under the groups:        #
    # group_name|cam|DaisyCam_sqX_shX                                         #
    # The groups are reused if they exist (several DaisyCams in the MASTER)   #
    #                                                                         #
    # cam_transform = DaisyCam transform                                      #
    # group_name = name of the top group (name of the layout defaultPrim)     #
    #                                                                         #
    # return the DaisyCam transform long name after the parenting             #
    #-------------------------------------------------------------------------#

    uuid = cmds.ls(cam_transform, uuid=True)[0]
    root = "|" + cmds.ls(cam_transform, long=True)[0].split("|")[1]

    group = "|" + group_name
    if not cmds.objExists(group):
        group = cmds.ls(cmds.group(empty=True, world=True, name=group_name), long=True)[0]
    cam_group = group + "|" + CAM_GROUP_NAME
    if not cmds.objExists(cam_group):
        cam_group = cmds.group(empty=True, parent=group, name=CAM_GROUP_NAME)

    cmds.parent(root, cam_group, relative=True)
    return cmds.ls(uuid, long=True)[0]


def create_camera_sequence(cam_shots, sequence):
    #-----------------------------------------------------------------------------#
    # Create one Camera Sequencer shot per DaisyCam, to play the whole sequence   #
    # and switch from one camera to the next                                      #
    # Each shot is cut on the MASTER range of the frame range file, and the       #
    # playback range is set to the whole sequence                                 #
    #                                                                             #
    # cam_shots = list of tuples (shot name, DaisyCam transform, MASTER range)    #
    # sequence = sequence name (e.g.: sq0010)                                     #
    #                                                                             #
    # return the list of created shot nodes                                       #
    #-----------------------------------------------------------------------------#

    shots = []
    for shot, cam_transform, cam_range in sorted(cam_shots, key=lambda s: s[2][0] if s[2] else 0):
        if not cam_range:
            cmds.warning("Pas de frame range pour %s_%s : pas de shot dans le Camera Sequencer" % (sequence, shot))
            continue
        start, end = float(cam_range[0]), float(cam_range[1])
        node = cmds.shot("%s_%s" % (sequence, shot), shotName=shot, currentCamera=cam_transform)
        # The ranges given at the creation are replaced by the playback range: set them afterwards
        cmds.shot(node, edit=True, startTime=start, endTime=end)
        cmds.shot(node, edit=True, sequenceStartTime=start, sequenceEndTime=end)
        print("Shot %s : %s -> %s (%s)" % (node, start, end, cam_transform))
        shots.append(node)

    if shots:
        start = min(cmds.shot(s, query=True, startTime=True) for s in shots)
        end = max(cmds.shot(s, query=True, endTime=True) for s in shots)
        set_playback_range([start, end])
        print("Camera Sequencer : %d shot(s) de %s à %s" % (len(shots), start, end))
        start_camera_switch(shots)
    return shots


def get_shot_cameras():
    #-------------------------------------------------------------------#
    # List the Camera Sequencer shots with their range and camera       #
    #                                                                   #
    # return a list of tuples (start, end, camera long name) by start   #
    #-------------------------------------------------------------------#

    shot_cameras = []
    for shot in cmds.ls(type="shot") or []:
        camera = cmds.shot(shot, query=True, currentCamera=True)
        if not camera or not cmds.objExists(camera):
            continue
        start = cmds.shot(shot, query=True, startTime=True)
        end = cmds.shot(shot, query=True, endTime=True)
        shot_cameras.append((start, end, get_camera_transform(camera)))
    return sorted(shot_cameras)


def get_camera_transform(camera):
    #-------------------------------------------------------#
    # Get the transform long name of a camera (or its shape) #
    #                                                       #
    # camera = camera transform or shape                    #
    #                                                       #
    # return the camera transform long name                 #
    #-------------------------------------------------------#

    if cmds.nodeType(camera) == "camera":
        camera = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
    return cmds.ls(camera, long=True)[0]


def switch_to_shot_camera(*_):
    #-------------------------------------------------------------------------#
    # Look through the camera of the Camera Sequencer shot at the current     #
    # frame, in the visible viewports already looking through a shot camera   #
    # (a viewport in persp or another camera is left as it is)                #
    #-------------------------------------------------------------------------#

    shot_cameras = get_shot_cameras()
    if not shot_cameras:
        return

    # Last shot starting before the frame: on a shared frame, the next shot wins
    frame = cmds.currentTime(query=True)
    camera = next((c for s, e, c in reversed(shot_cameras) if s <= frame <= e), None)
    if camera is None:
        return

    shot_camera_set = {c for _, _, c in shot_cameras}
    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) != "modelPanel":
            continue
        panel_camera = get_camera_transform(cmds.modelPanel(panel, query=True, camera=True))
        if panel_camera in shot_camera_set and panel_camera != camera:
            cmds.lookThru(panel, camera)


def start_camera_switch(shots):
    #-------------------------------------------------------------------------#
    # Start the scriptJob switching the viewport camera on every time change  #
    # The main viewport looks through the first shot camera to start with     #
    # The job is replaced if it already exists and is killed with the scene   #
    #                                                                         #
    # shots = list of the Camera Sequencer shot nodes                         #
    #                                                                         #
    # return the scriptJob id                                                 #
    #-------------------------------------------------------------------------#

    # The job of a previous import (or of an old version of this module) is replaced
    for job in cmds.scriptJob(listJobs=True) or []:
        if "switch_to_shot_camera" in job:
            cmds.scriptJob(kill=int(job.split(":")[0]), force=True)

    # Main viewport (biggest visible modelPanel) starts on the first shot camera
    panels = [p for p in cmds.getPanel(visiblePanels=True) or [] if cmds.getPanel(typeOf=p) == "modelPanel"]
    if panels:
        main_panel = max(panels, key=lambda p: cmds.control(p, query=True, width=True) * cmds.control(p, query=True, height=True))
        first = min(shots, key=lambda s: cmds.shot(s, query=True, startTime=True))
        cmds.lookThru(main_panel, cmds.shot(first, query=True, currentCamera=True))

    job = cmds.scriptJob(event=["timeChanged", switch_to_shot_camera], killWithScene=True)
    switch_to_shot_camera()
    print("Changement de caméra automatique actif (scriptJob %d)" % job)
    return job


# ------------------------------------------------------------------------------ #
#                                   USD camera                                   #
# ------------------------------------------------------------------------------ #

def get_usd_camera(stage_shape, camera_name):
    #-----------------------------------------------------------------#
    # Find a USD camera by its name in the stage                      #
    #                                                                 #
    # stage_shape = mayaUsdProxyShape of the layout                   #
    # camera_name = name of the camera prim                           #
    #               (e.g.: DaisyCam_sq0010_sh0010_camShape)           #
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


def get_usd_camera_shots(stage_shape, sequence):
    #-----------------------------------------------------------------------#
    # List the shots that have a camera (DaisyCam_sqX_shX_camShape) in USD  #
    # Used in the MASTER shot, which holds the cameras of every shot        #
    #                                                                       #
    # stage_shape = mayaUsdProxyShape of the layout                         #
    # sequence = sequence name (e.g.: sq0010)                               #
    #                                                                       #
    # return the sorted list of shot names (e.g.: ["sh0010", "sh0020"])     #
    #-----------------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import UsdGeom

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    # Text before and after the shot name (e.g.: "DaisyCam_sq0010_" and "_camShape")
    prefix, suffix = USD_CAM_NAME.format(sequence=sequence, shot="\0").split("\0")
    shots, ignored = set(), []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Camera):
            continue
        name = prim.GetName()
        if name.startswith(prefix) and name.endswith(suffix) and len(name) > len(prefix) + len(suffix):
            shots.add(name[len(prefix):len(name) - len(suffix)])
        else:
            ignored.append(name)

    if ignored:
        cmds.warning("Caméra(s) USD ignorée(s), nom différent de %sshX%s : %s" % (prefix, suffix, ", ".join(ignored)))
    print("%d caméra(s) de shot trouvée(s) dans %s" % (len(shots), stage_shape))
    return sorted(shots)


def get_camera_first_frame(camera):
    #-----------------------------------------------------------------------#
    # Get the first keyed frame of a USD camera (in the stage time)         #
    # Use the Houdini keys of the customData, otherwise the time samples    #
    # of the transform and of the lens                                      #
    #                                                                       #
    # camera = USD camera prim                                              #
    #                                                                       #
    # return the first frame, or None if the camera has no key              #
    #-----------------------------------------------------------------------#

    from pxr import UsdGeom

    frames = camera.GetCustomData().get(USD_CAM_KEYFRAMES)
    if not frames:
        lens = UsdGeom.Camera(camera)
        frames = list(UsdGeom.Xformable(camera).GetTimeSamples())
        for attr in (lens.GetFocalLengthAttr(), lens.GetHorizontalApertureAttr(), lens.GetVerticalApertureAttr()):
            frames += attr.GetTimeSamples()
    return int(min(frames)) if frames else None


def get_usd_camera_ranges(stage_shape, sequence, shots):
    #-------------------------------------------------------------------------------#
    # Compute the range of each shot camera of the MASTER from the camera keys      #
    # A shot starts on the first key of its camera and ends one frame before the    #
    # next shot, the last shot ends at the end of the stage                         #
    #                                                                               #
    # stage_shape = mayaUsdProxyShape of the layout                                 #
    # sequence = sequence name (e.g.: sq0010)                                       #
    # shots = list of shot names with a camera (see get_usd_camera_shots)           #
    #                                                                               #
    # return a dict {shot: [start, end]}, without the shots whose camera has no key #
    #-------------------------------------------------------------------------------#

    starts = {}
    for shot in shots:
        camera = get_usd_camera(stage_shape, USD_CAM_NAME.format(sequence=sequence, shot=shot))
        start = get_camera_first_frame(camera) if camera else None
        if start is None:
            cmds.warning("Pas de clé sur la caméra de %s_%s : range introuvable" % (sequence, shot))
            continue
        starts[shot] = start

    import mayaUsd.ufe

    stage_end = int(mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0]).GetEndTimeCode())
    ordered = sorted(starts.items(), key=lambda s: s[1])
    ranges = {}
    for i, (shot, start) in enumerate(ordered):
        end = ordered[i + 1][1] - 1 if i + 1 < len(ordered) else stage_end
        ranges[shot] = [start, max(start, end)]
    return ranges


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


# ------------------------------------------------------------------------------ #
#                               DaisyCam matching                                #
# ------------------------------------------------------------------------------ #

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
