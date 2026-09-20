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
from typing import Any
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

print("execute create_cam.py\n\n")

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

seq_and_sht_name = info["name"]
shot_entity = info["entity"]
project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")

sequence_name = shot_entity["sequence"]
shot_name = shot_entity["shot"]

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def create_cam(input_node: Any, input_network_box: Any, digit_number: int) -> Any:
    #-----------------------------------------------------------------------------------------------#
    # detect all cameras, get the last one well named and create a new one                          #
    # set name and path of the new camera                                                           #
    #                                                                                               #
    # input_node = the node just before the camera section                                          #
    # input_network_box = the network box containing the cameras                                    #
    # digit_number = number of digits after the sequence and shot (e.g.: sq0020_sh0120 => 4 digits) #
    #                                                                                               #
    # return the camera created                                                                     #
    #-----------------------------------------------------------------------------------------------#

    # detect all cameras and get the last one well named
    cameras_in_scene = hou.lopNodeTypeCategory().nodeTypes()["camera"].instances()
    last_cam_shot_number = 0
    new_shot_name = "sh010"
    last_cam_object = None

    if cameras_in_scene != ():
        for camera in cameras_in_scene:
            cam_name = camera.name()
            cam_name_first_part = cam_name[:6]
            cam_name_second_part = cam_name[6+digit_number:-digit_number]

            if cam_name_first_part == "cam_sq" and cam_name_second_part == "_sh":
                shot_number = int(cam_name[-3:])
                if shot_number > last_cam_shot_number:
                    last_cam_shot_number = shot_number
                    last_cam_object = camera

        if last_cam_shot_number + 10 < 100:
            new_shot_name = f"sh0{last_cam_shot_number+10}"
        else:
            new_shot_name = f"sh{last_cam_shot_number+10}"
    
    # create the cam with the new shot name
    lopnet = hou.node("/stage")

    cam1 = lopnet.createNode("camera")
    cam1.setName(f"cam_{sequence_name}_{new_shot_name}")
    cam1.parm("primpath").set(f"/{seq_and_sht_name}/cam/cam_{sequence_name}_{new_shot_name}")

    #-------------------------------- rearange nodes ---------------------------------#
    if last_cam_object != None:
        outputs_last_cam_object = last_cam_object.outputs()
        for output in outputs_last_cam_object:
            output.setInput(0, None)
        cam1.setInput(0, last_cam_object)
        for output in outputs_last_cam_object:
            output.setInput(0, cam1)

        cam1.setPosition([last_cam_object.position()[0],last_cam_object.position()[1]-1])
    else:
        outputs_input_node = input_node.outputs()
        for output in outputs_input_node:
            output.setInput(0, None)
        cam1.setInput(0, input_node)
        for output in outputs_input_node:
            output.setInput(0, cam1)

        cam1.setPosition([input_node.position()[0],input_node.position()[1]-2])

    cam1.setSelected(1, clear_all_selected=True)

    input_network_box.addItem(cam1)
    input_network_box.fitAroundContents()

    # set display flag
    cam1.setDisplayFlag(True)

    return cam1
