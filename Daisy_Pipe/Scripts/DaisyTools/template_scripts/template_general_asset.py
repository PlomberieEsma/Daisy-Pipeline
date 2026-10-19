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
import json, os
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

asset_name = info["name"]
asset_entity = info["entity"]
asset_path = asset_entity['asset_path'].replace("\\", "/")
asset_task = info["task"]
asset_version = core.products.getNextAvailableVersion(entity=asset_entity, product=asset_task)
project_path = info["entity"]["project_path"].replace("\\", "/")

env_var_path = f"$PRISM_JOB/03_Production/Assets/{asset_path}"

node_position = [0,0]
color_input_box = [0.33, 0.18, 0.44]
color_output_box = [0.86, 0.85, 0.72]

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def check_usd() -> bool:
    export_path = f"{project_path}/03_Production/Assets/{asset_path}/Export"
    tasks = os.listdir(export_path)
    if "USD" not in tasks:
        return False
    if asset_task not in tasks:
        return False
    return True

def nodes_general():
    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for a general purpose         #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    start_counter = perf_counter()

    # delete the HDA node to avoid it to influence the layout
    node_template = hou.node("/stage/create_template1")
    node_template.destroy()

    node_list = {}

    # if a USD asset is already created -> create Daisy import node
    # else create a primitive node with the name of the asset as root
    is_usd = check_usd()


    #-------------------------------- create nodes ---------------------------------#
    lopnet = hou.node("/stage")

    if is_usd:
        asset_stage = Usd.Stage.Open(f"{project_path}/03_Production/Assets/{asset_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(asset_stage)
        print(f"meters per unit : {meters_per_unit}")

        ref_asset1 = lopnet.createNode("Daisy::daisy_import")
        ref_asset1.setName("ref_asset1")
        ref_asset1.parm("importAs").set(1) #reference
        ref_asset1.parm("path").set(f"{env_var_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
        ref_asset1.parm("scale").set(meters_per_unit)
        node_list.update({"ref_asset1": ref_asset1})
    else:
        create_root1 = lopnet.createNode("primitive")
        create_root1.setName("create_root1")
        create_root1.parm("primpath").set(f"/{asset_name}")
        create_root1.parm("primkind").set("component")
        node_list.update({"create_root1": create_root1})

    sop_create1 = lopnet.createNode("sopcreate")
    sop_create1.setName("sop_create1")
    if is_usd:
        sop_create1.setInput(0, ref_asset1)
    else:
        sop_create1.setInput(0, create_root1)
        if "ModL" in asset_task or "ModH" in asset_task:
            sop_create1.parm("enable_pathprefix").set(1)
            sop_create1.parm("pathprefix").set(f"/{asset_name}/{asset_name}_geo")
            sop_create1.parm("enable_kindschema").set(1)
            sop_create1.parm("kindschema").set("none")

    daisy_export1 = lopnet.createNode("Daisy::daisy_export::1.0")
    daisy_export1.setName("daisy_export1")
    daisy_export1.setInput(0, sop_create1)
    daisy_export1.parm("mayascale").set(0)
    daisy_export1.parm("defaultprim").set(f"/{asset_name}")
    # daisy_export1.parm("setmetersperunit").set(0)
    if is_usd:
        daisy_export1.parm("metersperunit").set(meters_per_unit)
    else:
        daisy_export1.parm("metersperunit").set(1)

    node_list.update({
        "sop_create1": sop_create1,
        "daisy_export1": daisy_export1
    })

    #-------------------------------- arange nodes ---------------------------------#
    lopnet.layoutChildren()

    node_list["sop_create1"].move([0, -3])
    node_list["daisy_export1"].move([0, -6])

    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")

    return node_list
