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
from Scripts.DaisyTools.core.framerange_convert import FramerangeFile
from Scripts.DaisyTools.template_scripts.create_toolbox import create_toolbox

print("execute template_RLO.py\n\n")

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

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def python_command() -> str:
    #-----------------------------------------------------------------------#
    ################################ OUTDATED ###############################
    # Create a python script to place into a python lop node                #
    # works only for the shot                                               #
    #                                                                       #
    # return a string containing all the cameras which are not the shot one #
    #-----------------------------------------------------------------------#

    return f"""
cam_path_to_keep = f"/{seq_and_sht_name}/cam/cam_{seq_and_sht_name}"

node = hou.pwd()
stage = node.editableStage()
parent_prim = stage.GetPrimAtPath(f"/{seq_and_sht_name}/cam")
output = ""

# check all /cam children to add them to the output string
if parent_prim:
    for child in parent_prim.GetChildren():
        if str(child.GetPath()) == cam_path_to_keep:
            continue
        output += str(child.GetPath()) + " "
else:
    raise Exception("no parent primitive named cam, check if it exists an placed as a child of the assembly prim (with sequence and shot name)")

# put the output value in a custom parameter
node_ptg = node.parmTemplateGroup()
output_param = hou.StringParmTemplate("output_param", "Output", 1, default_value=output)
node_ptg.append(output_param)
node.setParmTemplateGroup(node_ptg)
node.parm("output_param").set(output)
"""

def cam_to_delete(last_node) -> str:
    #-----------------------------------------------------------------------#
    ################################ OUTDATED ###############################
    # Create a python lop node to get the list of cameras to delete         #
    # works only for the shot                                               #
    #                                                                       #
    # last_node: the last node in the network                               #
    #                                                                       #
    # return a string containing all the cameras which are not the shot one #
    #-----------------------------------------------------------------------#

    lopnet = hou.node("/stage")
    tmp_node = lopnet.createNode('pythonscript')
    tmp_node.setInput(0, last_node)
    tmp_node.parm("python").set(python_command())
    tmp_node.cook(force=True)

    cam_to_delete = tmp_node.parm("output_param").eval()
    # print(f"{cam_to_delete = }")

    tmp_node.destroy()
    return cam_to_delete

def define_time_offset() -> int:
    #-----------------------------------------------------------------------#
    # get the difference between the start frame of the MASTER and the shot #
    # works only for the shot                                               #
    #                                                                       #
    # return an int containing the number of frames to offset               #
    #-----------------------------------------------------------------------#

    framerange_file = FramerangeFile()
    start_MASTER_frame = framerange_file.get_master_range(sequence_name, shot_name)[0]
    start_shot_frame = framerange_file.get_shot_range(sequence_name, shot_name)[0]
    time_offset = start_shot_frame - start_MASTER_frame
    return time_offset

def nodes_template_RLO() -> dict[str,Any]:
    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for the RLO department        #
    # works only for the shot                                                       #
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

    ref_MASTER_RLO1 = lopnet.createNode("sublayer")
    ref_MASTER_RLO1.setName("ref_MASTER_RLO1")
    ref_MASTER_RLO1.parm("loadpayloads").set(0)
    ref_MASTER_RLO1.parm("filepath1").set(f"$PRISM_JOB/03_production/shots/{sequence_name}/MASTER/Export/RLO/master/{sequence_name}_MASTER_RLO_master.{usd_file_format}")
    ref_MASTER_RLO1.parm("timeoffset1").set(define_time_offset())

    scale_down_RLO1 = lopnet.createNode("xform")
    scale_down_RLO1.setName("scale_down_RLO1")
    scale_down_RLO1.setInput(0, ref_MASTER_RLO1)
    scale_down_RLO1.setColor(hou.Color(color_input_box))
    scale_down_RLO1.parm("scale").set(0.01)
    scale_down_RLO1.parm("primpattern").set("/*")

    rename_assembly1 = lopnet.createNode("restructurescenegraph")
    rename_assembly1.setName("rename_assembly1")
    rename_assembly1.setInput(0, scale_down_RLO1)
    rename_assembly1.setColor(hou.Color(color_input_box))
    rename_assembly1.parm("op").set(1)# rename primitives
    rename_assembly1.parm("primnewname").set(seq_and_sht_name)

    cameras_to_delete = f"%type:Camera ^{seq_and_sht_name}/cam/cam_{seq_and_sht_name}"

    unload_cam1 = lopnet.createNode("prune")
    unload_cam1.setName("unload_cam1")
    unload_cam1.setInput(0, rename_assembly1)
    unload_cam1.setColor(hou.Color(color_input_box))
    unload_cam1.parm("primpattern1").set(cameras_to_delete)
    unload_cam1.parm("method").set("deactivate")

    hide_cam1 = lopnet.createNode("configureprimitive")
    hide_cam1.setName("hide_cam1")
    hide_cam1.setInput(0, unload_cam1)
    hide_cam1.setColor(hou.Color(color_input_box))
    hide_cam1.parm("primpattern").set(cameras_to_delete)
    hide_cam1.parm("seteditable").set(1)
    hide_cam1.parm("editable").set(0)
    hide_cam1.parm("setselectable").set(1)
    hide_cam1.parm("selectable").set(0)
    hide_cam1.parm("sethideinui").set(1)
    hide_cam1.parm("hideinui").set(1)

    camera_edit1 = lopnet.createNode("camera")
    camera_edit1.setName("camera_edit1")
    camera_edit1.setInput(0, hide_cam1)
    camera_edit1.parm("primpattern").set(f"/{seq_and_sht_name}/cam/cam_{seq_and_sht_name}")
    camera_edit1.parm("createprims").set(0)# edit

    scale_up1 = lopnet.createNode("xform")
    scale_up1.setName("scale_up1")
    scale_up1.setInput(0, camera_edit1)
    scale_up1.parm("primpattern").set("/*")
    scale_up1.parm("scale").set(100)

    config_layer1 = lopnet.createNode("configurelayer")
    config_layer1.setName("config_layer1")
    config_layer1.setInput(0, scale_up1)
    config_layer1.parm("setsavepath").set(1)
    config_layer1.parm("savepath").set(f"{env_var_path}/Export/{shot_task}/{shot_version}/{seq_and_sht_name}_{shot_task}_{shot_version}.{usd_file_format}")
    config_layer1.parm("setdefaultprim").set(1)
    config_layer1.parm("defaultprim").set(f"{seq_and_sht_name}")

    usd_rop1 = lopnet.createNode("usd_rop")
    usd_rop1.setName("usd_rop1")
    usd_rop1.setInput(0, config_layer1)
    usd_rop1.parm("lopoutput").set("")
    usd_rop1.parm("postrender").set("$PRISMJOB/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/saveas/create_version_info.py")
    usd_rop1.parm("lpostrender").set("python")

    node_list.update({
        "ref_MASTER_RLO1": ref_MASTER_RLO1,
        "scale_down_RLO1": scale_down_RLO1,
        "rename_assembly1": rename_assembly1,
        "unload_cam1": unload_cam1,
        "hide_cam1": hide_cam1,
        "camera_edit1": camera_edit1,
        "scale_up1": scale_up1,
        "config_layer1": config_layer1,
        "usd_rop1": usd_rop1
    })

    #-------------------------------- arange nodes ---------------------------------#
    lopnet.layoutChildren()

    node_list["camera_edit1"].move([0, -3])

    node_list["scale_up1"].move([0, -6])
    node_list["config_layer1"].move([0, -6])
    node_list["usd_rop1"].move([0, -6])

    # set input network box
    nodes_in_input_box = ["ref_MASTER_RLO1", "scale_down_RLO1", "rename_assembly1", "unload_cam1", "hide_cam1"]
    input_box = lopnet.createNetworkBox()
    input_box.setName("input_box")
    for node in nodes_in_input_box:
        input_box.addItem(node_list[node])
    input_box.setColor(hou.Color(color_input_box))
    input_box.setComment("Input")
    input_box.fitAroundContents()
    node_list.update({"input_box" : input_box})

    # set output network box
    nodes_in_output_box = ["scale_up1", "config_layer1", "usd_rop1"]
    output_box = lopnet.createNetworkBox()
    output_box.setName("output_box")
    for node in nodes_in_output_box:
        output_box.addItem(node_list[node])
    output_box.setColor(hou.Color(color_output_box))
    output_box.setComment("Outputs")
    output_box.fitAroundContents()
    node_list.update({"output_box" : output_box})

    # set display flag
    node_list["hide_cam1"].setDisplayFlag(True)
    node_list["hide_cam1"].setSelected(1, clear_all_selected=True)

    #-------------------------------- create toolbox ---------------------------------#
    node_list.update(create_toolbox(["primitive",
                                     "prune",
                                     "graftbranches",
                                     "stagemanager",
                                     "restructurescenegraph",
                                     "matchsize",
                                     "xform",
                                     "edit",
                                     "followpathconstraint"], [-15,0]))
    
    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")
    
    return node_list
