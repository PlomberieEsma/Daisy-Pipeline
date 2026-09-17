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

print("execute template_shading.py\n\n")

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
color_material_box = [0.7, 0.79, 0.72]
color_output_box = [0.86, 0.85, 0.72]

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]
print(f"{usd_file_format = }")

asset_stage = Usd.Stage.Open(f"{project_path}/03_Production/Assets/{asset_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
meters_per_unit = UsdGeom.GetStageMetersPerUnit(asset_stage)
print(f"meters per unit : {meters_per_unit}")

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def template_shading() -> Any:

    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for the Shading department    #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    start_counter = perf_counter()

    # delete the HDA node to avoid it to influence the layout
    node_template = hou.node("/stage/create_template1")
    node_template.destroy()

    #-------------------------------- create nodes ---------------------------------#
    lopnet=hou.node("/stage")

    ref_geo1 = lopnet.createNode("reference")
    ref_geo1.setName("ref_geo1")
    ref_geo1.setPosition(node_position)
    ref_geo1.parm("enable").set(0) #disable multi-input
    ref_geo1.parm("primpath1").set("/`pythonexprs(\"__import__('pxr').Sdf.Layer.FindOrOpen(hou.pwd().evalParm('filepath1')).defaultPrim\")`") #re1ferenced file's default primitive
    ref_geo1.parm("filepath1").set(f"{env_var_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
    ref_geo1.parm("filerefprim1").set("") #reference specific primitive
    ref_geo1.parm("filerefprimpath1").set("`chs(\"primpath1\")`")

    set_variant1 = lopnet.createNode("setvariant")
    set_variant1.setName("set_variant1")
    set_variant1.setInput(0, ref_geo1)
    node_position[1] -= 1
    set_variant1.move(node_position)
    set_variant1.parm("num_variants").set(2)
    set_variant1.parm("variantset1").set("geo")
    set_variant1.parm("variantname1").set("geo_var01")
    set_variant1.parm("variantset2").set("grm")
    set_variant1.parm("variantname2").set("grm_var01")

    layer_break1 = lopnet.createNode("layerbreak")
    layer_break1.setName("layer_break1")
    layer_break1.setInput(0, set_variant1)
    layer_break1.setColor(hou.Color(color_input_box))
    node_position[1] -= 1
    layer_break1.move(node_position)

    scale_down1 = lopnet.createNode("xform")
    scale_down1.setName("scale_down1")
    scale_down1.setInput(0, layer_break1)
    node_position[1] -= 1
    scale_down1.move(node_position)
    scale_down1.parm("scale").set(meters_per_unit)

    create_component1 = lopnet.createNode("primitive")
    create_component1.setName("create_component1")
    create_component1.setInput(0, scale_down1)
    create_component1.setColor(hou.Color(color_input_box))
    node_position[1] -= 1
    create_component1.move(node_position)
    create_component1.parm("primpath").set("/`lopinputprims('.', 0)`")
    create_component1.parm("primkind").set("component") #component

    create_mtl1 = lopnet.createNode("primitive")
    create_mtl1.setName("create_mtl1")
    create_mtl1.setInput(0, create_component1)
    create_mtl1.setColor(hou.Color(color_input_box))
    node_position[1] -= 1
    create_mtl1.move(node_position)
    create_mtl1.parm("primpath").set("/`chs(\"../create_component1/primpath\")`/mtl")
    create_mtl1.parm("parentprimtype").set("UsdGeomScope") #scope
    create_mtl1.parm("primtype").set("UsdGeomScope") #scope

    create_shader1 = lopnet.createNode("materiallibrary")
    create_shader1.setName("create_shader1")
    create_shader1.setInput(0, create_mtl1)
    node_position[1] -= 5
    create_shader1.move(node_position)
    create_shader1.parm("matpathprefix").set("/`chs(\"../create_component1/primpath\")`/mtl/")

    configure_mtl_primitives1 = lopnet.createNode("configureprimitive")
    configure_mtl_primitives1.setName("configure_mtl_primitives1")
    configure_mtl_primitives1.setInput(0, create_shader1)
    node_position[1] -= 2
    configure_mtl_primitives1.move(node_position)
    configure_mtl_primitives1.setColor(hou.Color(list(map(lambda x: x - 0.2 ,color_material_box))))
    configure_mtl_primitives1.parm("primpattern").set("/`chs(\"../create_component1/primpath\")`/mtl/*")
    configure_mtl_primitives1.parm("settype").set(1)
    configure_mtl_primitives1.parm("type").set("UsdShadeMaterial") #material
    configure_mtl_primitives1.parm("setspecifier").set(1)

    assign_shader1 = lopnet.createNode("assignmaterial")
    assign_shader1.setName("assign_shader1")
    assign_shader1.setInput(0, configure_mtl_primitives1)
    node_position[1] -= 2
    assign_shader1.move(node_position)

    scale_up1 = lopnet.createNode("xform")
    scale_up1.setName("scale_up1")
    scale_up1.setInput(0, assign_shader1)
    node_position[1] -= 5
    scale_up1.move(node_position)
    scale_up1.parm("primpattern").set("`chs(\"../create_component1/primpath\")`")
    scale_up1.parm("scale").set(1/meters_per_unit)

    config_mtl_layer1 = lopnet.createNode("configurelayer")
    config_mtl_layer1.setName("config_mtl_layer1")
    config_mtl_layer1.setInput(0, scale_up1)
    node_position[1] -= 1
    config_mtl_layer1.move(node_position)
    config_mtl_layer1.parm("setsavepath").set(1)
    config_mtl_layer1.parm("savepath").set(f"{env_var_path}/Export/{asset_task}/{asset_version}/{asset_name}_{asset_task}_{asset_version}.{usd_file_format}")
    config_mtl_layer1.parm("setdefaultprim").set(1)
    config_mtl_layer1.parm("defaultprim").set("/`chs(\"../create_component1/primpath\")`")

    usd_rop1 = lopnet.createNode("usd_rop")
    usd_rop1.setName("usd_rop1")
    usd_rop1.setInput(0, config_mtl_layer1)
    node_position[1] -= 1
    usd_rop1.move(node_position)
    usd_rop1.parm("lopoutput").set("")
    usd_rop1.parm("postrender").set("$PRISMJOB/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/saveas/create_version_info.py")
    usd_rop1.parm("lpostrender").set("python")

    node_list = {"ref_geo1" : ref_geo1,
              "set_variant1" : set_variant1,
              "layer_break1" : layer_break1,
              "scale_down1" : scale_down1,
              "create_component1" : create_component1,
              "create_mtl1" : create_mtl1,
              "create_shader1" : create_shader1,
              "configure_mtl_primitives1" : configure_mtl_primitives1,
              "assign_shader1" : assign_shader1,
              "scale_up1" : scale_up1,
              "config_mtl_layer1" : config_mtl_layer1,
              "usd_rop1" : usd_rop1}
    
    #-------------------------------- arange nodes ---------------------------------#
    # set input network box
    nodes_in_input_box = ["ref_geo1", "set_variant1", "layer_break1", "scale_down1", "create_component1", "create_mtl1"]
    input_box = lopnet.createNetworkBox()
    for node in nodes_in_input_box:
        input_box.addItem(node_list[node])
    input_box.setColor(hou.Color(color_input_box))
    input_box.setComment("Inputs")
    input_box.fitAroundContents()
    input_box.setBounds(hou.BoundingRect(input_box.position()[0]-1, input_box.position()[1], input_box.position()[0]+input_box.size()[0]+3, input_box.position()[1]+input_box.size()[1]))

    # set mtl network box
    nodes_in_material_box = ["create_shader1", "configure_mtl_primitives1", "assign_shader1"]
    material_box = lopnet.createNetworkBox()
    for node in nodes_in_material_box:
        material_box.addItem(node_list[node])
    material_box.setColor(hou.Color(color_material_box))
    material_box.setComment("Material")
    material_box.fitAroundContents()
    material_box.setBounds(hou.BoundingRect(material_box.position()[0]-1, material_box.position()[1], material_box.position()[0]+material_box.size()[0]+3, material_box.position()[1]+material_box.size()[1]))

    # set output network box
    nodes_in_output_box = ["scale_up1", "config_mtl_layer1", "usd_rop1"]
    output_box = lopnet.createNetworkBox()
    for node in nodes_in_output_box:
        output_box.addItem(node_list[node])
    output_box.setColor(hou.Color(color_output_box))
    output_box.setComment("Outputs")
    output_box.fitAroundContents()
    output_box.setBounds(hou.BoundingRect(output_box.position()[0]-1, output_box.position()[1], output_box.position()[0]+output_box.size()[0]+3, output_box.position()[1]+output_box.size()[1]))

    node_list.update({"input_box" : input_box,
                      "material_box" : material_box,
                      "output_box" : output_box})

    # set display flag
    node_list["assign_shader1"].setDisplayFlag(True)

    #-------------------------------- crete toolbox ---------------------------------#
    node_list.update(create_toolbox(["assignmaterial",
                                     "materiallinker",
                                     "unassignmaterial",
                                     "editmaterial"], [-10,0]))


    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")

    return node_list
