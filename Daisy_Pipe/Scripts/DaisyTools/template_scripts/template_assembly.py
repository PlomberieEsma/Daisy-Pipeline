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
from time import perf_counter
from typing import Any
from pxr import Usd, UsdGeom # type: ignore
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.template_scripts.create_toolbox import create_toolbox

print("execute template_set_dress.py\n\n")

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

env_var_path = f"$PRISM_JOB/03_Production/Shots/{sequence_name}/{shot_name}"

node_position = [0,0]
color_input_box = [0.33, 0.18, 0.44]
color_output_box = [0.86, 0.85, 0.72]
color_animation_box = [0.41, 0.4, 0.64]
color_cfx_box = [0.52, 0.66, 0.75]
color_fx_box = [0.7, 0.8, 0.72]

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]


##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def nodes_template_assembly() -> dict[str,Any]:

    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for the Set Dress department  #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    start_counter = perf_counter()

    # delete the HDA node to avoid it to influence the layout
    node_template = hou.node("/stage/create_template1")
    node_template.destroy()

    node_list = {}

    #-------------------------------- create nodes ---------------------------------#
    lopnet = hou.node("/stage")

    ref_layout1 = lopnet.createNode("Daisy::daisy_import")
    ref_layout1.setName("ref_layout1")
    ref_layout1.parm("path").set(f"{env_var_path}/Export/Layout/master/{seq_and_sht_name}_Layout_master.{usd_file_format}")
    ref_layout1.parm("layerbreak").set(0)
    ref_layout1.parm("mayascale").set(0)
    ref_layout1.parm("loadpayloads").set(0)

    load_payloads1 = lopnet.createNode("Daisy::load_saved_payloads::1.0")
    load_payloads1.setName("load_payloads1")
    load_payloads1.setInput(0, ref_layout1)

    null_anim1 = lopnet.createNode("null")
    null_anim1.setName("ANIMATION")
    null_anim1.setInput(0, load_payloads1)
    null_anim1.setColor(hou.Color(color_animation_box))

    null_cfx1 = lopnet.createNode("null")
    null_cfx1.setName("CFX")
    null_cfx1.setInput(0, null_anim1)
    null_cfx1.setColor(hou.Color(color_cfx_box))
    
    null_fx1 = lopnet.createNode("null")
    null_fx1.setName("FX")
    null_fx1.setInput(0, null_cfx1)
    null_fx1.setColor(hou.Color(color_fx_box))

    daisy_export1 = lopnet.createNode("Daisy::daisy_export::1.0")
    daisy_export1.setName("daisy_export1")
    daisy_export1.setInput(0, null_fx1)
    daisy_export1.parm("versions").set(1)
    daisy_export1.parm("trange").set(1)# Render Specific Frame Range
    daisy_export1.parm("mayascale").set(0)
    def_prim = seq_and_sht_name.replace("-", "_")
    daisy_export1.parm("defaultprim").set(f"/{def_prim}")
    daisy_export1.parm("striplayerbreaks").set(0)

    node_list.update({"ref_layout1" : ref_layout1,
                      "load_payloads1" : load_payloads1,
                      "null_anim1" : null_anim1,
                      "null_cfx1" : null_cfx1,
                      "null_fx1" : null_fx1,
                      "daisy_export1" : daisy_export1})

    #-------------------------------- arange nodes ---------------------------------#
    lopnet.layoutChildren()
    
    node_list["null_anim1"].move([0,-5])
    node_list["null_cfx1"].move([0,-7])
    node_list["null_fx1"].move([0,-9])

    node_list["daisy_export1"].move([0, -14])

    # set input network box
    nodes_in_input_box = ["ref_layout1", "load_payloads1"]
    input_box = lopnet.createNetworkBox()
    for node in nodes_in_input_box:
        input_box.addItem(node_list[node])
    input_box.setColor(hou.Color(color_input_box))
    input_box.setComment("Inputs")
    input_box.fitAroundContents()
    node_list.update({"input_box" : input_box})

    # set animation network box
    nodes_in_animation_box = ["null_anim1"]
    animation_box = lopnet.createNetworkBox()
    for node in nodes_in_animation_box:
        animation_box.addItem(node_list[node])
    animation_box.setColor(hou.Color(color_animation_box))
    animation_box.setComment("Animation")
    animation_box.fitAroundContents()
    animation_box.resize(hou.Vector2(0, 1.5))
    for node_in_box in animation_box.nodes():
        node_in_box.move([0, 1.5])
    node_list.update({"animation_box" : animation_box})

    # set cfx network box
    nodes_in_cfx_box = ["null_cfx1"]
    cfx_box = lopnet.createNetworkBox()
    for node in nodes_in_cfx_box:
        cfx_box.addItem(node_list[node])
    cfx_box.setColor(hou.Color(color_cfx_box))
    cfx_box.setComment("CFX")
    cfx_box.fitAroundContents()
    cfx_box.resize(hou.Vector2(0, 1.5))
    for node_in_box in cfx_box.nodes():
        node_in_box.move([0, 1.5])
    node_list.update({"cfx_box" : cfx_box})

    # set fx network box
    nodes_in_fx_box = ["null_fx1"]
    fx_box = lopnet.createNetworkBox()
    for node in nodes_in_fx_box:
        fx_box.addItem(node_list[node])
    fx_box.setColor(hou.Color(color_fx_box))
    fx_box.setComment("FX")
    fx_box.fitAroundContents()
    fx_box.resize(hou.Vector2(0, 1.5))
    for node_in_box in fx_box.nodes():
        node_in_box.move([0, 1.5])
    node_list.update({"fx_box" : fx_box})

    # set output network box
    nodes_in_output_box = ["daisy_export1"]
    output_box = lopnet.createNetworkBox()
    for node in nodes_in_output_box:
        output_box.addItem(node_list[node])
    output_box.setColor(hou.Color(color_output_box))
    output_box.setComment("Outputs")
    output_box.fitAroundContents()
    node_list.update({"output_box" : output_box})

    # set display flag
    node_list["daisy_export1"].setDisplayFlag(True)

    #-------------------------------- create toolbox ---------------------------------#
    node_list.update(create_toolbox(["primitive",
                                     "prune",
                                     "graftbranches",
                                     "stagemanager",
                                     "restructurescenegraph",
                                     "Daisy::daisy_import",
                                     "Daisy::load_saved_payloads::1.0"], [-15,0]))


    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")

    return node_list
