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
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.template_scripts.create_toolbox import create_toolbox

print("execute template_MASTER_layout.py\n\n")

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
color_light_box = [0.86, 0.85, 0.5]
color_output_box = [0.86, 0.85, 0.72]

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def nodes_template_MASTER_lighting() -> dict[str,Any]:
    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for the Lighting department   #
    # works only for the MASTER shot                                                #
    #                                                                               #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    start_counter = perf_counter()

    # delete the HDA node to avoid it to influence the layout
    node_template = hou.node("/stage/create_template1")
    node_template.destroy()

    node_list = {}

    #-------------------------------- create nodes ---------------------------------#
    lopnet = hou.node("/stage")

    ref_set_dress1 = lopnet.createNode("Daisy::daisy_import")
    ref_set_dress1.setName("ref_set_dress1")
    ref_set_dress1.parm("path").set(f"{env_var_path}/Export/SetDress/master/{seq_and_sht_name}_setDress_master.{usd_file_format}")
    ref_set_dress1.parm("importAs").set(1)# Reference
    ref_set_dress1.parm("mayascale").set(0)

    create_lights1 = lopnet.createNode("primitive")
    create_lights1.setName("create_lights1")
    create_lights1.setInput(0, ref_set_dress1)
    create_lights1.parm("primpath").set(f"{seq_and_sht_name}/lights")
    create_lights1.parm("primkind").set("group")
    create_lights1.parm("parentprimtype").set("") #none

    create_lightFilters1 = lopnet.createNode("primitive")
    create_lightFilters1.setName("create_lightFilters1")
    create_lightFilters1.setInput(0, create_lights1)
    create_lightFilters1.parm("primpath").set(f"{seq_and_sht_name}/lights/lightFilters")
    create_lightFilters1.parm("primkind").set("group")
    create_lightFilters1.parm("primtype").set("UsdGeomScope")# scope

    null_light1 = lopnet.createNode("null")
    null_light1.setName("LIGHTS")
    null_light1.setInput(0, create_lightFilters1)
    null_light1.setColor(hou.Color(color_light_box))

    daisy_export1 = lopnet.createNode("Daisy::daisy_export::1.0")
    daisy_export1.setName("daisy_export1")
    daisy_export1.setInput(0, null_light1)
    daisy_export1.parm("versions").set(1)
    daisy_export1.parm("trange").set(1)# Render Specific Frame Range
    daisy_export1.parm("mayascale").set(0)
    def_prim = seq_and_sht_name.replace("-", "_")
    daisy_export1.parm("defaultprim").set(f"/{def_prim}")

    node_list.update({"ref_set_dress1": ref_set_dress1,
                    "create_lights1" : create_lights1,
                    "create_lightFilters1" : create_lightFilters1,
                    "null_light1" : null_light1,
                    "daisy_export1" : daisy_export1})

    #-------------------------------- arange nodes ---------------------------------#
    lopnet.layoutChildren()

    node_list["null_light1"].move([0, -5])
    node_list["daisy_export1"].move([0, -10])

    # set input network box
    nodes_in_input_box = ["ref_set_dress1", "create_lights1", "create_lightFilters1"]
    input_box = lopnet.createNetworkBox()
    for node in nodes_in_input_box:
        input_box.addItem(node_list[node])
    input_box.setColor(hou.Color(color_input_box))
    input_box.setComment("Inputs")
    input_box.fitAroundContents()
    node_list.update({"input_box" : input_box})

    # set light network box
    nodes_in_light_box = ["null_light1"]
    light_box = lopnet.createNetworkBox()
    light_box.setName("light_box")
    for node in nodes_in_light_box:
        light_box.addItem(node_list[node])
    light_box.setColor(hou.Color(color_light_box))
    light_box.setComment("Lights")
    light_box.fitAroundContents()
    light_box.resize(hou.Vector2(0, 1.5))
    for node_in_box in light_box.nodes():
        node_in_box.move([0, 1.5])
    node_list.update({"light_box" : light_box})

    # set output network box
    nodes_in_output_box = ["daisy_export1"]
    output_box = lopnet.createNetworkBox()
    output_box.setName("output_box")
    for node in nodes_in_output_box:
        output_box.addItem(node_list[node])
    output_box.setColor(hou.Color(color_output_box))
    output_box.setComment("Outputs")
    output_box.fitAroundContents()
    node_list.update({"output_box" : output_box})

    # set display flag
    node_list["null_light1"].setDisplayFlag(True)

    #-------------------------------- create toolbox ---------------------------------#
    node_list.update(create_toolbox(["light::2.0",
                                     "domelight::3.0",
                                     "portallight",
                                     "lightlinker",
                                     "lightmixer",
                                     "pxrbarnlightfilter",
                                     "pxrcookielightfilter",
                                     "pxrramplightfilter",
                                     "pxrrodlightfilter"], [-15,0]))


    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")

    return node_list
