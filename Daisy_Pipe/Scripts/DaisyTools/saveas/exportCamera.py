#------------------------------------------------------------------------------#
# Publish of the shot cameras as Maya files, one .mb per DaisyCam              #
#                                                                              #
# The MASTER shot holds one DaisyCam per shot of the sequence, animated by     #
# the layout/anim artist. Each one is exported on its own so that a shot can   #
# import its camera already animated and already named, instead of rebuilding  #
# it from the USD overlay (see setupAsset/maya/shot/camera.py)                 #
#                                                                              #
# The files live side by side in a single version of the Camera product:       #
#   <shot>/Export/Camera/v0001/<seq>-MASTER_Camera_v0001_<shot>.mb             #
# and the master version is a plain copy of them, as the geo master is         #
#------------------------------------------------------------------------------#

import os
import shutil

from DaisyTools.core.core import CAMERA_PRODUCT, CAMERA_RIG_PREFIX
from DaisyTools.saveas.exportShotAnim import get_cameras_to_export

CAMERA_EXTENSION = ".mb"


def shot_of_camera(rig, sequence):
    #-------------------------------------------------------------------------#
    # Shot a DaisyCam rig belongs to, read from its name DaisyCam_<seq>_<shot>#
    #                                                                         #
    # rig = long name of the DaisyCam rig top node                            #
    # sequence = sequence name (e.g.: sq0010)                                 #
    #                                                                         #
    # return the shot name, or None if the rig is not named for the sequence  #
    #-------------------------------------------------------------------------#

    # Strip the prefix instead of splitting on "_": a shot name may hold one
    prefix = "%s_%s_" % (CAMERA_RIG_PREFIX, sequence)
    name = rig.split("|")[-1].split(":")[-1]
    if not name.startswith(prefix) or len(name) == len(prefix):
        return None
    return name[len(prefix):]


def camera_file_path(base_path, shot):
    #-------------------------------------------------------------------------#
    # Path of the camera file of a shot, next to the other cameras of the     #
    # version: the Prism file name of the product, suffixed with the shot     #
    #-------------------------------------------------------------------------#

    base, extension = os.path.splitext(base_path)
    return "%s_%s%s" % (base, shot, extension)


def write_camera(file_path, rig):
    #-------------------------------------------------------------------------#
    # Export one DaisyCam rig and its animation to a Maya file               #
    #                                                                         #
    # file_path = path of the .mb to write                                    #
    # rig = long name of the DaisyCam rig top node                            #
    #-------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    cmds.select(rig, replace=True)
    # exportSelected takes the whole hierarchy under the rig and its anim curves,
    # preserveReferences=False so the published camera stands on its own
    cmds.file(
        file_path,
        force=True,
        options="v=0;",
        type="mayaBinary",
        exportSelected=True,
        preserveReferences=False,
    )


def export_cameras(core, entity, nodes=None, update_master=True):
    #-------------------------------------------------------------------------------#
    # Publish one .mb per DaisyCam of the scene in the Camera product               #
    # Registering the files in Prism is left to the caller (saveas/exportUSD.py)    #
    #                                                                               #
    # core = Prism core                                                             #
    # entity = Prism entity dict of the shot                                        #
    # nodes = Maya Objects list of the export state, None = every DaisyCam          #
    # update_master = also copy the files to the master version                     #
    #                                                                               #
    # return the list of the written files, empty if the scene has no DaisyCam      #
    #-------------------------------------------------------------------------------#

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    cameras = get_cameras_to_export(nodes)
    if not cameras:
        return []

    sequence = entity.get("sequence", "")
    base_path = core.products.generateProductPath(
        entity=entity, task=CAMERA_PRODUCT, extension=CAMERA_EXTENSION, version=None, location="global"
    )
    os.makedirs(os.path.dirname(base_path), exist_ok=True)

    master_base_path = None
    if update_master:
        master_base_path = core.products.generateProductPath(
            entity=entity, task=CAMERA_PRODUCT, extension=CAMERA_EXTENSION, version="master", location="global"
        )
        os.makedirs(os.path.dirname(master_base_path), exist_ok=True)

    # The export selects each rig in turn: give the artist their selection back
    selection = cmds.ls(selection=True, long=True) or []

    paths = []
    try:
        for camera in cameras:
            rig = camera["rig"]
            shot = shot_of_camera(rig, sequence)
            if shot is None:
                cmds.warning("%s is not named %s_%s_<shot>: camera not published" % (rig, CAMERA_RIG_PREFIX, sequence))
                continue

            path = camera_file_path(base_path, shot)
            write_camera(path, rig)
            paths.append(path)
            print("Camera published: %s -> %s" % (rig, path))

            if master_base_path:
                master_path = camera_file_path(master_base_path, shot)
                shutil.copy2(path, master_path)
                print("Master copied: %s" % master_path)
    finally:
        if selection:
            cmds.select(selection, replace=True)
        else:
            cmds.select(clear=True)

    return paths


def camera_master_path(core, entity):
    #-------------------------------------------------------------------------#
    # Path Prism gives the master version of the Camera product, used to      #
    # write its version info - the files themselves are suffixed per shot     #
    #-------------------------------------------------------------------------#

    return core.products.generateProductPath(
        entity=entity, task=CAMERA_PRODUCT, extension=CAMERA_EXTENSION, version="master", location="global"
    )
