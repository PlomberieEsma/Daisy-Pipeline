#                           .=     ,        =.
#                   _  _   /'/    )\,/,/(_   \ \
#                    `//-.|  (  ,\\)\//\)\/_  ) |
#                    //___\   `\\\/\\/\/\\///'  /
#                 ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
#                 \       `-.  '_`.      .'_` \ ,-"~`/
#                  `.__.-'`/  ( -\        /- )|-.__,'
#                    ||   |    \ O)  /^\ (O / |
#                    `\\  |         /   `\    /
#                      \\  \       /      `\ /
#                       `\\ `-.  /' .---.--.\
#                         `\\/`~(, '()      ('
#                          /(O) \\   _,.-.,_)
#                         //  \\ `\'`      /
#                        / |  ||   `""'"~"`
#                      /'  |__||
#                            `o
#      ___       _                    _          ___               
#     / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___       
#    / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)      
#   /____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/       
#                   /___/    /_/    /_/                            
#
#   by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio
#   art by Joan G. Stark (Spunk)

#import modules
import hou # type: ignore
import json
from typing import Any
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.framerange_convert import FramerangeFile

print("execute layout_manager.py\n\n")

# title
try:
    from Scripts.DaisyTools.core.ascii_art import print_title
    print_title()
except:
    print("\nDaisy Pipeline\n\nby Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio\n\n")



class Error(Exception):
    # use to raise errors in the script
    pass

##########################################################################################################################################
#=========================================================== SET VARIABLES ===============================================================
##########################################################################################################################################

core = get_core()
info = get_entity_info()
assert core is not None
assert info is not None

project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")
shot_entity = info["entity"]
seq_and_sht_name = info["name"]

sequence_name = shot_entity["sequence"]
shot_name = shot_entity["shot"]

env_var_path = f"$PRISM_JOB/03_Production/Shots/{sequence_name}/{shot_name}"

cam_layout_name = "cam_layout"

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

digit_number = config_file["global"]["sh_name_digit_number"] # number of digits in the seq and sht names
usd_file_format = config_file["global"]["usd_file_format"]

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def get_cameras_in_scene() -> dict[str,Any]:
    #-----------------------------------------------------------------------------------#
    # Get well named cameras in the houdini scene                                       #
    #                                                                                   #
    # return the list of cameras objects and the number of well named cameras in a dict #
    #-----------------------------------------------------------------------------------#

    cameras_in_scene = hou.lopNodeTypeCategory().nodeTypes()["camera"].instances()
    cam_count_scene = 0

    # get all well named cameras in the scene
    if cameras_in_scene != ():
        cameras_in_scene = list(cameras_in_scene)
        loop_count = 0
        sorted_cameras_in_scene = list(cameras_in_scene)

        for camera in cameras_in_scene:
            cam_name = camera.name()

            if cam_name.startswith("DaisyCam") == False:
                del sorted_cameras_in_scene[loop_count]
                loop_count -= 1

            loop_count += 1

        cam_count_scene = len(sorted_cameras_in_scene)

    return {"cameras_in_scene" : sorted_cameras_in_scene,
            "cam_count_scene" : cam_count_scene}

def command_check(kwargs: dict[str,str]):
    #-----------------------------------------------------------------------------------------------#
    # Check what command has been used (add, delete or clear all shots) and call the right function #
    #                                                                                               #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"                                 #
    #-----------------------------------------------------------------------------------------------#

    cameras_in_scene = get_cameras_in_scene()["cameras_in_scene"]
    cam_count_scene = get_cameras_in_scene()["cam_count_scene"]

    if int(kwargs["script_value"]) == 0:
        # if there is no shot in the HDA
        # CLEAR button
        print("clear shots")

        # delete sequence in framerange.json
        framerange_file = FramerangeFile()
        framerange_file.delete_sequence(sequence_name)

        for camera in cameras_in_scene:
            if camera.name() == cam_layout_name:
                continue
            # destroy camera node
            print(f"delete {camera.name()}")
            camera.destroy()

        return

    # check the difference btw the cam number and the HDA shot number
    # to detect which function needs to be called
    count_difference = int(kwargs["script_value"]) - cam_count_scene

    current_framerange = list(core.getFrameRange())
    for i in range (len(current_framerange)):
        current_framerange[i] = int(current_framerange[i])

    if count_difference == 0 or count_difference == 1 or cameras_in_scene == []:
        # new shot
        create_shot(kwargs, digit_number, current_framerange)
    elif count_difference < 0 and cameras_in_scene != []:
        # delete shot
        delete_shot(kwargs, cameras_in_scene)
    else:
        # issue detected
        issue_correction(kwargs)





def create_shot(kwargs: dict[str,str], digit_number: int, framerange: list[int]):
    #-----------------------------------------------------------------------------------------------#
    # Create new shot by creating a camera and naming the HDA multiParmBlock instance               #
    #                                                                                               #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"                                 #
    # digit_number = number of digits after the sequence and shot (e.g.: sq0020_sh0120 => 4 digits) #
    #-----------------------------------------------------------------------------------------------#
    from Scripts.DaisyTools.hda_scripts.create_cam import create_cam

    node = kwargs["node"]
    shot_number = node.parm("shot_number").eval()

    # get the input node for create_cam()
    nulls_in_scene = hou.lopNodeTypeCategory().nodeTypes()["null"].instances()
    null_input = None
    for null in nulls_in_scene:
        if null.name() == "cameras":
            null_input = null
            break

    # get the networkbox for create_cam()
    box_input = hou.node("/stage").findNetworkBox("/stage/camera_box")

    new_cam = create_cam(null_input, box_input, digit_number)
    new_shot_name = new_cam.name().replace("DaisyCam_", "").replace("_", " ")

    # modifie the HDA
    node.parm(f"sh_name{shot_number}").set(new_shot_name)
    node.parm(f"cam_selection_{shot_number}").set(new_cam.parm("primpath"))
    node.parm(f"sh_framerange_{shot_number}x").set(framerange[0])
    node.parm(f"sh_framerange_{shot_number}y").set(framerange[1])

    framerange_file = FramerangeFile()
    framerange_file.set_shot(new_shot_name.split(" ")[0], new_shot_name.split(" ")[1], framerange)

    print("add "+new_cam.name().replace("DaisyCam_", ""))

def delete_shot(kwargs: dict[str,str], cameras_in_scene: Any):
    #-------------------------------------------------------------------#
    # Delete a camera by getting the shot deleted in the multiParmBlock #
    #                                                                   #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"     #
    # cameras_in_scene = list of all well named cameras in the scene    #
    #-------------------------------------------------------------------#

    block = kwargs["node"]
    block_number = block.parm("shot_number").eval()
    add_to_block_number = 1 if kwargs["parm_name"] != "get_from_prism" else 0

    for i in range(block_number+add_to_block_number):
        # loop into all shots in the HDA
        # when it comes from get from prism button
        if kwargs["parm_name"] == "get_from_prism" and kwargs["shot_to_delete"] == block.parm(f"sh_name{i+1}").eval():
            # the shot has been deleted
            print("del "+cameras_in_scene[i].name().replace("DaisyCam_", ""))
            # delete the corresponding camera node
            cameras_in_scene[i].destroy()

            # delete shot for RLO
            block.parm("shot_number").removeMultiParmInstance(i)
            break

        # when it comes from delete button
        try:
            if cameras_in_scene[i].parm("primpath").eval() == block.parm(f"cam_selection_{i+1}").eval():
                # it's ok
                pass
            else:
                sq_and_sh_name = cameras_in_scene[i].name().replace("DaisyCam_", "").replace("_", " ")
                # the shot has been deleted
                print(f"del {sq_and_sh_name}")
                # delete the corresponding camera node
                cameras_in_scene[i].destroy()
                # delete shot in framerange.json
                framerange_file = FramerangeFile()
                framerange_file.delete_shot(sq_and_sh_name.split(" ")[0], sq_and_sh_name.split(" ")[1])
                break

        except AttributeError as e:
            # if the user deletes the last shot
            print("del "+cameras_in_scene[i].name().replace("DaisyCam_", ""))
            cameras_in_scene[i].destroy()
            break

def issue_correction(kwargs: dict[str,str]):
    #---------------------------------------------------------------------------#
    # In case of node deletion without deleting the shot in multiParmBlock :    #
    # delete multiParmBlock instances which have empty "cam_selection_#" field  #
    #                                                                           #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"             #
    #---------------------------------------------------------------------------#

    block = kwargs["node"]
    block_number = block.parm("shot_number").eval()
    removed = False

    for i in range(block_number-1):
        # loop into all shots in the HDA
        if removed == True:
            i -= 1
            removed = False
        try:
            if block.parm(f"cam_selection_{i+1}").eval() == "":
                # if there is no camera in the camera selection field
                # remove the corresponding shot in the HDA
                block.parm("shot_number").removeMultiParmInstance(i)

                removed = True
        except Exception as e:
            print(f"Error : {e}")

def get_rlo_from_maya():
    cameras_in_scene = get_cameras_in_scene()
    last_cam_object = None
    last_cam_shot_number = 0

    if cameras_in_scene["cameras_in_scene"] != []:
        # check every camera to find the last one
        for camera in cameras_in_scene["cameras_in_scene"]:
            cam_name = camera.name()
            
            shot_number = int(cam_name[-digit_number:])
            if shot_number > last_cam_shot_number:
                last_cam_shot_number = shot_number
                last_cam_object = camera

    lopnet = hou.node("/stage")

    ref_rlo_maya = lopnet.createNode("Daisy::daisy_import")
    ref_rlo_maya.setName("ref_rlo_maya")
    ref_rlo_maya.parm("path").set(f"{env_var_path}/Export/Animation/master/{seq_and_sht_name}_Animation_master.{usd_file_format}")
    ref_rlo_maya.parm("layerbreak").set(0)
    ref_rlo_maya.parm("mayascale").set(0)

    #-------------------------------- rearange nodes ---------------------------------#
    if last_cam_object != None:
        outputs_last_cam_object = last_cam_object.outputs()
        for output in outputs_last_cam_object:
            output.setInput(0, None)
        ref_rlo_maya.setInput(0, last_cam_object)
        for output in outputs_last_cam_object:
            output.setInput(0, ref_rlo_maya)

        ref_rlo_maya.setPosition([last_cam_object.position()[0],last_cam_object.position()[1]-4])
    else:
        input_node = last_cam_object
        outputs_input_node = input_node.outputs()
        for output in outputs_input_node:
            output.setInput(0, None)
        ref_rlo_maya.setInput(0, input_node)
        for output in outputs_input_node:
            output.setInput(0, ref_rlo_maya)

        ref_rlo_maya.setPosition([input_node.position()[0],input_node.position()[1]-4])