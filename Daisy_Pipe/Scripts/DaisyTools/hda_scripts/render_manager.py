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
import json, re
from typing import Any
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info


print("execute rename_shot.py\n\n")

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

seq_and_sht_name = info["name"]
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

def create_layer(kwargs: dict[str, Any]) -> None:
    #-------------------------------------------------------------------------------#
    # Create a layer rendersettings and set the current node to unhide parameters   #
    #                                                                               #
    # kwargs = dict taken from the callbgack of the HDA                             #
    #-------------------------------------------------------------------------------#

    #get variables from pipeline.json
    config_file_path = f"{project_path}/00_Pipeline/pipeline.json"
    with open(config_file_path, mode="r", encoding="utf-8") as read_file:
        pipeline_file = json.load(read_file)
    project_resolution = pipeline_file["globals"]["resolution"]

    # set HDA parameters
    node = kwargs["node"]
    multiparm_index = int(kwargs["script_multiparm_index"])
    node.parm(f"is_layer{multiparm_index}").set(1)
    node.parm(f"deadline_is_layer{multiparm_index+1}").set(1)

    # get the input null for render settings
    nulls_in_scene = hou.lopNodeTypeCategory().nodeTypes()["null"].instances()
    null_render_input = None
    for null in nulls_in_scene:
        if null.name() == "RENDER":
            null_render_input = null
            break

    layer_name = node.parm(f"layer_name{multiparm_index}").eval()
    
    # create renderman render settings, configure primitive, restructure scenegraph and null
    lopnet = hou.node("/stage")
    box_render = hou.node("/stage").findNetworkBox("/stage/render_box")
    box_render_color = box_render.color()

    rendersettings_node1 = lopnet.createNode("rendermanrendersettings")
    rendersettings_node1.setName(f"{layer_name}_settings")
    rendersettings_node1.setInput(0, null_render_input)
    rendersettings_node1.parm("resolution1").set(project_resolution[0])
    rendersettings_node1.parm("resolution2").set(project_resolution[1])
    rendersettings_node1.parm("disableMotionBlur").set(1)
    rendersettings_node1.parm("disableDepthOfField").set(1)

    configure_prim_node1 = lopnet.createNode("configureprimitive")
    configure_prim_node1.setName(f"{layer_name}_config")
    configure_prim_node1.setInput(0, rendersettings_node1)
    configure_prim_node1.setColor(box_render_color)
    configure_prim_node1.parm("primpattern").set("/Render")
    configure_prim_node1.parm("setkind").set(1)
    configure_prim_node1.parm("kind").set("group")
    configure_prim_node1.parm("settype").set(1)
    configure_prim_node1.parm("type").set("UsdGeomScope")# scope

    restructure_scene_node1 = lopnet.createNode("restructurescenegraph")
    restructure_scene_node1.setName(f"{layer_name}_reparent")
    restructure_scene_node1.setInput(0, configure_prim_node1)
    restructure_scene_node1.setColor(box_render_color)
    restructure_scene_node1.parm("primpattern").set("/Render")
    restructure_scene_node1.parm("primnewparent").set(f"/{seq_and_sht_name}")

    null_layer1 = lopnet.createNode("null")
    null_layer1.setName(f"{layer_name}_OUT")
    null_layer1.setInput(0, restructure_scene_node1)
    null_layer1.setColor(box_render_color)

    #-------------------------------- rearange nodes ---------------------------------#
    rendersettings_in_scene = hou.lopNodeTypeCategory().nodeTypes()["rendermanrendersettings"].instances()
    x_offset = (len(rendersettings_in_scene)-1)*3

    rendersettings_node1.move([null_render_input.position()[0]+x_offset,null_render_input.position()[1]-3])
    configure_prim_node1.move([rendersettings_node1.position()[0],rendersettings_node1.position()[1]-1])
    restructure_scene_node1.move([rendersettings_node1.position()[0],rendersettings_node1.position()[1]-2])
    null_layer1.move([rendersettings_node1.position()[0],rendersettings_node1.position()[1]-3])

    box_render.addItem(rendersettings_node1)
    box_render.addItem(configure_prim_node1)
    box_render.addItem(restructure_scene_node1)
    box_render.addItem(null_layer1)
    box_render.fitAroundContents()

    # create usd render in the ROP of the HDA

def change_layer_name(kwargs: dict[str, Any]) -> None:
    #-----------------------------------------------------------------------#
    # Modify the name of a layer                                            #
    # Triggered when the name field is modified in the HDA                  #
    #                                                                       #
    # kwargs = dict taken from the callbgack of the HDA                     #
    #-----------------------------------------------------------------------#

    # set HDA parameters
    node = kwargs["node"]

    multiparm_index = int(kwargs["script_multiparm_index"])
    script_value = kwargs["script_value"]
    render_layers = node.parm("render_layers").eval()
    new_name = script_value

    # add number at the end of the layer name
    for layer_number in range(render_layers):
        name = node.parm(f"layer_old_name{layer_number}").eval()
        if new_name in name:
            final_digits = re.search(r'\d+$', name)
            if final_digits != None:
                final_digits = final_digits.group()
            if bool(final_digits) == False:
                new_name = f"{new_name}1"
            else:
                new_name = new_name.replace(final_digits, "")
                new_name = f"{new_name}{int(final_digits)+1}"
    new_name = new_name.replace(" ", "_")

    # apply name
    kwargs["parm"].set(new_name)
    node.parm(f"deadline_layer_name{multiparm_index+1}").set(new_name)

    # rename nodes
    layer_old_name = node.parm(f"layer_old_name{multiparm_index}").eval()

    try:
        rendersettings_node1 = hou.node(f"/stage/{layer_old_name}_settings")
        rendersettings_node1.setName(f"{new_name}_settings")

        configure_prim_node1 = hou.node(f"/stage/{layer_old_name}_config")
        configure_prim_node1.setName(f"{new_name}_OUT")

        restructure_scene_node1 = hou.node(f"/stage/{layer_old_name}_reparent")
        restructure_scene_node1.setName(f"{new_name}_OUT")

        null_layer1 = hou.node(f"/stage/{layer_old_name}_OUT")
        null_layer1.setName(f"{new_name}_OUT")
    except Exception as e:
        print(f"Error : {e}")

    node.parm(f"layer_old_name{multiparm_index}").set(new_name)