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
assert core is not None

project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

digit_number = config_file["global"]["sh_name_digit_number"] # number of digits in the seq and sht names

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
        for camera in cameras_in_scene:
            cam_name = camera.name()
            cam_name_first_part = cam_name[:6]
            cam_name_second_part = cam_name[6+digit_number:-digit_number]

            if cam_name_first_part != "cam_sq" or cam_name_second_part != "_sh":
                del cameras_in_scene[loop_count]

            loop_count += 1

        cam_count_scene = len(cameras_in_scene)

    return {"cameras_in_scene" : cameras_in_scene,
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
        for camera in cameras_in_scene:
            # destroy camera node
            camera.destroy()

        # set FLO and TLO number to 0
        kwargs["node"].parm("shots_FLO").set(0)
        kwargs["node"].parm("shots_TLO").set(0)
        return

    # check the difference btw the cam number and the HDA shot number
    # to detect which function needs to be called
    count_difference = int(kwargs["script_value"]) - cam_count_scene

    current_framerange = list(core.getFrameRange())
    for i in range (len(current_framerange)):
        current_framerange[i] = int(current_framerange[i])

    if count_difference == 1:
        # new shot
        create_shot(kwargs, digit_number, current_framerange)
    elif count_difference == -1:
        # delete shot
        delete_shot(kwargs, cameras_in_scene)
    else:
        # issuecdetected
        issue_correction(kwargs)





def create_shot(kwargs: dict[str,str], digit_number: int, framerange: list[int]):
    #-----------------------------------------------------------------------------------------------#
    # Create new shot by creating a camera and naming the HDA multiParmBlock instance               #
    # modifies the FLO and TLO multiParmBlock instances too                                         #
    #                                                                                               #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"                                 #
    # digit_number = number of digits after the sequence and shot (e.g.: sq0020_sh0120 => 4 digits) #
    #-----------------------------------------------------------------------------------------------#

    from Scripts.DaisyTools.hda_scripts.create_cam import create_cam

    node = kwargs["node"]
    # shot_number = kwargs["script_value"]
    shot_number = node.parm("shot_number").eval()

    # mofifie script value to get the correct parameters if we create the shot automatically from get from Prism buton
    # if kwargs["parm_name"] == "get_from_prism":
    #     shot_number = str(kwargs["node"].parm("shot_number").eval())

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
    new_shot_name = new_cam.name().replace("cam_", "").replace("_", " ")

    # modifie the HDA
    # RLO part
    node.parm(f"sh_name{shot_number}").set(new_shot_name)
    node.parm(f"cam_selection_{shot_number}").set(new_cam.parm("primpath"))
    node.parm(f"sh_framerange_{shot_number}x").set(framerange[0])
    node.parm(f"sh_framerange_{shot_number}y").set(framerange[1])

    # copy shot number and name from RLO to FLO and TLO
    # FLO part
    node.parm("shots_FLO").set(shot_number)
    node.parm(f"sh_name_FLO_{shot_number}").set(new_shot_name)
    # TLO part
    node.parm("shots_TLO").set(shot_number)
    node.parm(f"sh_name_TLO_{shot_number}").set(new_shot_name)

    print("add "+new_cam.name().replace("cam_", ""))

def delete_shot(kwargs: dict[str,str], cameras_in_scene: Any):
    #-------------------------------------------------------------------#
    # Delete a camera by getting the shot deleted in the multiParmBlock #
    # modifies the FLO and TLO multiParmBlock instances too             #
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
            print("del "+cameras_in_scene[i].name().replace("cam_", ""))
            # delete the corresponding camera node
            cameras_in_scene[i].destroy()

            # delete shot for RLO, FLO and TLO
            block.parm("shot_number").removeMultiParmInstance(i)
            block.parm("shots_FLO").removeMultiParmInstance(i)
            block.parm("shots_TLO").removeMultiParmInstance(i)
            break

        # when it comes from delete button
        try:
            if cameras_in_scene[i].parm("primpath").eval() == block.parm(f"cam_selection_{i+1}").eval():
                # it's ok
                pass
            else:
                # the shot has been deleted
                print("del "+cameras_in_scene[i].name().replace("cam_", ""))
                # delete the corresponding camera node
                cameras_in_scene[i].destroy()

                # delete shot for FLO and TLO
                block.parm("shots_FLO").removeMultiParmInstance(i)
                block.parm("shots_TLO").removeMultiParmInstance(i)
                break

        except AttributeError as e:
            # if the user deletes the last shot
            print("del "+cameras_in_scene[i].name().replace("cam_", ""))
            cameras_in_scene[i].destroy()

            # delete shot for FLO and TLO
            block.parm("shots_FLO").removeMultiParmInstance(i)
            block.parm("shots_TLO").removeMultiParmInstance(i)
            break

def issue_correction(kwargs: dict[str,str]):
    #---------------------------------------------------------------------------#
    # In case of node deletion without deleting the shot in multiParmBlock :    #
    # delete multiParmBlock instances which have empty "cam_selection_#" field  #
    # modifies the FLO and TLO multiParmBlock instances too                     #
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

                # delete shot for FLO and TLO
                block.parm("shots_FLO").removeMultiParmInstance(i)
                block.parm("shots_TLO").removeMultiParmInstance(i)
                removed = True
        except Exception as e:
            print(f"Error : {e}")
