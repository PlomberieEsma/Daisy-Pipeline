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
import json
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.framerange_convert import FramerangeFile

print("execute syncronize_layout_prism.py\n\n")

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

shot_path = info["path"]
seq_and_sht_name = info["name"]
shot_entity = info["entity"]
shot_task = info["task"]
shot_version = core.products.getNextAvailableVersion(entity=shot_entity, product=shot_task)
project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")

sequence_name = shot_entity["sequence"]
shot_name = shot_entity["shot"]

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]
digit_number = config_file["global"]["sh_name_digit_number"] # number of digits in the seq and sht names

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

#============================================================ get from prism ============================================================#

def get_from_prism(kwargs: dict[str,str]):
    #---------------------------------------------------------------#
    # Check what to do when Get from Prism is clicked               #
    # launch the correct function to add or omit a shot in Prism    #
    #                                                               #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number" #
    #---------------------------------------------------------------#

    sequence_entities = core.entities.getShotsFromSequence(sequence_name)
    hou_node = kwargs["node"]

    # set prism shot names in a list
    prism_shots = []
    for entity in range (len(sequence_entities)):
        prism_shots.append(sequence_entities[entity]["shot"])

    # get HDA shot names and keep only the last part to get the same layout as prism shot names
    hou_shots = []
    for i in range(hou_node.parm("shot_number").eval()):
        hou_shots.append(hou_node.parm(f"sh_name{i+1}").eval())
        hou_shots[i] = hou_shots[i][-digit_number-2:]


    # check if a shot is missing in both list
    for hou_shot in hou_shots:
        # if a shot doesn't exist in the pipe but exists in the HDA => delete shot in houdini
        if hou_shot not in prism_shots:
            from Scripts.DaisyTools.hda_scripts.layout_manager import delete_shot, get_cameras_in_scene

            cameras_in_scene = get_cameras_in_scene()["cameras_in_scene"]
            kwargs.update({"shot_to_delete" : f"{sequence_name} {hou_shot}"})

            delete_shot(kwargs, cameras_in_scene)

    shot_counter = 0
    for prism_shot in prism_shots:
        if prism_shot == "MASTER":
            continue
        # if a shot exists in the pipe but doesn't in the HDA => create shot in houdini
        if prism_shot not in hou_shots:
            from Scripts.DaisyTools.hda_scripts.layout_manager import create_shot
            from Scripts.DaisyTools.hda_scripts.rename_shot import button_action

            # get framerange from a json file
            framerange = FramerangeFile().get_master_range(sequence_name, prism_shot)

            shot_number = hou_node.parm("shot_number")
            shot_number.set(hou_node.parm("shot_number").eval()+1)
            kwargs["script_multiparm_index"] = str(kwargs["node"].parm("shot_number").eval())

            create_shot(kwargs, digit_number, framerange)
            button_action(kwargs, new_shot_name=prism_shot)
        shot_counter += 1

def update_from_prism(kwargs: dict[str,str]):
    #---------------------------------------------------------------------------#
    # Syncronize a single houdini shot with Prism when Update shot is clicked   #
    # update the framerange                                                     #
    #                                                                           #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"             #
    #---------------------------------------------------------------------------#

    parm_number = kwargs["parm_name"][12:]
    hou_node = kwargs["node"]
    shot_name = hou_node.parm(f"sh_name{parm_number}").eval()
    shot_name = shot_name[-digit_number-2:]

    # get framerange from a json file
    framerange = FramerangeFile().get_master_range(sequence_name, shot_name)

    # set new framerange in HDA
    hou_node.parm(f"sh_framerange_{parm_number}x").set(framerange[0])
    hou_node.parm(f"sh_framerange_{parm_number}y").set(framerange[1])

    # get prism shot
    # selected_shot = core.entities.getShot(sequence_name, shot_name)
    # print(f"{selected_shot=}")

#============================================================= push to prism ============================================================#

def push_to_prism(kwargs: dict[str,str]):
    #---------------------------------------------------------------#
    # Check what to do when Push to Prism is clicked                #
    # launch the correct function to add or omit a shot in Prism    #
    #                                                               #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number" #
    #---------------------------------------------------------------#

    sequence_entities = core.entities.getShotsFromSequence(sequence_name)
    hou_node = kwargs["node"]

    # set prism shot names in a list
    prism_shots = []
    for entity in range (len(sequence_entities)):
        prism_shots.append(sequence_entities[entity]["shot"])

    # get HDA shot names and keep only the last part to get the same layout as prism shot names
    hou_shots = []
    for i in range(hou_node.parm("shot_number").eval()):
        hou_shots.append(hou_node.parm(f"sh_name{i+1}").eval())
        hou_shots[i] = hou_shots[i][-digit_number-2:]


    # check if a shot is missing in both list
    hou_shot_counter = 1
    for hou_shot in hou_shots:
        # if a shot doesn't exist in the pipe but exists in the HDA => create shot in the pipe
        if hou_shot not in prism_shots:
            hou_framerange = []
            hou_framerange.append(hou_node.parm(f"sh_framerange_{hou_shot_counter}x").eval())
            hou_framerange.append(hou_node.parm(f"sh_framerange_{hou_shot_counter}y").eval())

            hou_complete_shot_name = hou_node.parm(f"sh_name{hou_shot_counter}").eval()
            hou_splited_name = hou_complete_shot_name.split(" ")
            hou_sequence_name = hou_splited_name[0]
            hou_shot_name = hou_splited_name[1]

            # convert framerange and get it from a json file
            framerange_file = FramerangeFile()
            framerange_file.set_shot(hou_sequence_name, hou_shot_name, hou_framerange)
            framerange = framerange_file.get_shot_range(hou_sequence_name, hou_shot_name)

            create_prism_shot(framerange, hou_shot)
        hou_shot_counter += 1

    prism_shot_counter = 0
    for prism_shot in prism_shots:
        if prism_shot == "MASTER":
            continue
        # if a shot exists in the pipe but doesn't in the HDA => omit (hide) shot in the pipe
        if prism_shot not in hou_shots:
            omit_prism_shot(prism_shot)
        prism_shot_counter += 1



def create_prism_shot(framerange: list[int], shot_name: str):
    #-----------------------------------------------#
    # Create new shot in Prism and in the pipe      #
    # create it from HDA node informations          #
    #                                               #
    # shot_name : name of the shot (e.g.: sh053)    #
    #-----------------------------------------------#

    # make sure the shot is not omited
    current_shot = core.entities.getShot(sequence_name, shot_name)
    if current_shot != None:
    # if the shot is omited, unomit it
        is_omitted = core.entities.isShotOmitted(current_shot)
        if is_omitted:
            core.entities.omitEntity(current_shot, omit=False)
            print(f"unomit {shot_name} in Prism")
            core.entities.refreshOmittedEntities()
    else:
        # if the shot is not omited, create the shot
        entity={"type": "shot", "sequence": str(sequence_name), "shot": str(shot_name)}

        core.entities.createShot(
            entity = entity,
            frameRange=framerange)

        print(f"create {shot_name} in Prism")

def omit_prism_shot(shot_name: str):
    #-----------------------------------------------#
    # Omit the shot in Prism                        #
    #                                               #
    # shot_name : name of the shot (e.g.: sh053)    #
    #-----------------------------------------------#
    
    sequence_entities = core.entities.getShotsFromSequence(sequence_name)

    for entity in sequence_entities:
        entity_name = core.entities.getShotName(entity)
        if entity_name[-digit_number-2:] == shot_name:
            core.entities.omitEntity(entity)
            print(f"omit {shot_name} in Prism")
            core.entities.refreshOmittedEntities()
