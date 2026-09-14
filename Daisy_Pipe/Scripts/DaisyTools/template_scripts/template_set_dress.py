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

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]


##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def nodes_import_assets(imported_assets: list[dict[str,str]], input: Any) -> dict[str,Any]:

    #-------------------------------------------------------------------------------#
    # Creates a bunch of nodes to import and assemble assets                        #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    node_list = {}

    #-------------------------------- create nodes ---------------------------------#
    lopnet = hou.node("/stage")

    graft_set_dress1 = lopnet.createNode("graftstages")
    graft_set_dress1.setName("graft_set_dress1")
    graft_set_dress1.setInput(0, input)
    graft_set_dress1.parm("primpath").set(f"/{seq_and_sht_name}/scene/set_dress")
    graft_set_dress1.parm("destpath").set("/")

    # Iterate through each imported asset
    for asset in imported_assets:
        asset_name = asset["name"]
        asset_path = asset["asset_path"]
        asset_env_var_path = f"$PRISM_JOB/03_Production/Assets/{asset_path}"

        asset_stage = Usd.Stage.Open(f"{project_path}/03_Production/Assets/{asset_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(asset_stage)
        print(f"meters per unit for {asset_name} : {meters_per_unit}")

        reference1 = lopnet.createNode("reference")
        reference1.setName(f"ref_{asset_name}")
        reference1.parm("enable").set(0)
        reference1.parm("num_files").set(2)
        reference1.parm("primpath1").set("""/`pythonexprs("__import__('pxr').Sdf.Layer.FindOrOpen(hou.pwd().evalParm('filepath1')).defaultPrim")`""")
        reference1.parm("filepath1").set(f"{asset_env_var_path}/Export/USD/master/{asset_name}_USD_master.usda")
        reference1.parm("filerefprim1").set("") #reference specific primitive
        reference1.parm("filerefprimpath1").set("`chs(\"primpath1\")`")
        reference1.parm("primpath2").set("/__class__")
        reference1.parm("filepath2").set("`chs(\"filepath1\")`")
        reference1.parm("filerefprim2").set("") #reference specific primitive
        reference1.parm("filerefprimpath2").set("/__class__")

        set_variant1 = lopnet.createNode("setvariant")
        set_variant1.setName(f"set_variant_{asset_name}")
        set_variant1.setInput(0, reference1)
        set_variant1.move(node_position)
        set_variant1.parm("num_variants").set(3)
        set_variant1.parm("variantset1").set("geo")
        set_variant1.parm("variantname1").set("geo_var01")
        set_variant1.parm("variantset2").set("grm")
        set_variant1.parm("variantname2").set("grm_var01")
        set_variant1.parm("variantset3").set("mtl")
        set_variant1.parm("variantname3").set("mtl_var01")

        scale_down1 = lopnet.createNode("xform")
        scale_down1.setName(f"scale_down_{asset_name}")
        scale_down1.setInput(0, set_variant1)
        scale_down1.parm("primpattern").set("%kind:component")
        scale_down1.parm("scale").set(meters_per_unit)

        restructure_scene_graph1 = lopnet.createNode("restructurescenegraph")
        restructure_scene_graph1.setName(f"restructure_scene_graph_{asset_name}")
        restructure_scene_graph1.setInput(0, scale_down1)
        restructure_scene_graph1.setColor(hou.Color(color_input_box))
        restructure_scene_graph1.parm("primpattern").set("`lopinputprims('.', 0)` /__class__")
        restructure_scene_graph1.parm("primnewparent").set(f"/{asset_name}")
        restructure_scene_graph1.parm("createparentprim").set(1)
        restructure_scene_graph1.parm("parentprimtype").set("UsdGeomXform") #xform

        configure_prim1 = lopnet.createNode("configureprimitive")
        configure_prim1.setName(f"configure_prim_{asset_name}")
        configure_prim1.setInput(0, restructure_scene_graph1)
        configure_prim1.setColor(hou.Color(color_input_box))
        configure_prim1.parm("primpattern").set(f"/{asset_name}")
        configure_prim1.parm("setkind").set(1)
        configure_prim1.parm("kind").set("component")

        null1 = lopnet.createNode("null")
        null1.setName(f"OUT_{asset_name}")
        null1.setInput(0, configure_prim1)
        null1.setColor(hou.Color(color_input_box))

        node_list.update({f"ref_{asset_name}": reference1,
                          f"set_variant_{asset_name}": set_variant1,
                          f"scale_down_{asset_name}": scale_down1,
                          f"restructure_scene_graph_{asset_name}": restructure_scene_graph1,
                          f"configure_prim_{asset_name}": configure_prim1,
                          f"OUT_import_{asset_name}": null1})

        graft_set_dress1.setInput(1000, null1)

    node_list.update({"graft_set_dress1": graft_set_dress1})

    #-------------------------------- arange nodes ---------------------------------#
    
    lopnet.layoutChildren()
    node_list["graft_set_dress1"].setPosition([0,node_list["graft_set_dress1"].position()[1]])
    
    # set input network box
    input_box = lopnet.createNetworkBox()
    nodes_in_input_box = dict(node_list)
    del nodes_in_input_box["graft_set_dress1"]
    for node in nodes_in_input_box:
        input_box.addItem(node_list[node])
    input_box.setColor(hou.Color(color_input_box))
    input_box.setComment("Inputs")
    input_box.fitAroundContents()
    node_list.update({"input_box" : input_box})

    return node_list

def nodes_template_set_dress(imported_assets: list[dict[str,Any]]) -> dict[str,Any]:

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

    create_assembly1 = lopnet.createNode("primitive")
    create_assembly1.setName("create_assembly1")
    create_assembly1.parm("primpath").set(f"/{seq_and_sht_name}")
    create_assembly1.parm("primkind").set("assembly")

    create_set_dress1 = lopnet.createNode("primitive")
    create_set_dress1.setName("create_set_dress1")
    create_set_dress1.setInput(0, create_assembly1)
    create_set_dress1.parm("primpath").set("`lopinputprims('.', 0)`/scene\n`lopinputprims('.', 0)`/scene/set_dress")
    create_set_dress1.parm("primkind").set("group")
    create_set_dress1.parm("parentprimtype").set("") #none

    node_list.update(nodes_import_assets(imported_assets, create_set_dress1))

    scale_up1 = lopnet.createNode("xform")
    scale_up1.setName("scale_up1")
    scale_up1.setInput(0, node_list["graft_set_dress1"])
    scale_up1.parm("primpattern").set(f"/{seq_and_sht_name}/scene/set_dress/*")
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

    node_list.update({"create_assembly1" : create_assembly1, 
                      "create_set_dress1" : create_set_dress1,
                      "scale_up1" : scale_up1,
                      "config_layer1" : config_layer1,
                      "usd_rop1" : usd_rop1})

    #-------------------------------- arange nodes ---------------------------------#
    lopnet.layoutChildren()

    node_list["create_assembly1"].move([0,node_list["input_box"].size()[1]-2])
    node_list["create_set_dress1"].move([0,node_list["input_box"].size()[1]-2])

    node_list["scale_up1"].setPosition([0,node_list["scale_up1"].position()[1]])
    node_list["config_layer1"].setPosition([0,node_list["config_layer1"].position()[1]])
    node_list["usd_rop1"].setPosition([0,node_list["usd_rop1"].position()[1]])

    node_list["scale_up1"].move([0, -15])
    node_list["config_layer1"].move([0, -15])
    node_list["usd_rop1"].move([0, -15])

    # set output network box
    nodes_in_output_box = ["scale_up1", "config_layer1", "usd_rop1"]
    output_box = lopnet.createNetworkBox()
    for node in nodes_in_output_box:
        output_box.addItem(node_list[node])
    output_box.setColor(hou.Color(color_output_box))
    output_box.setComment("Outputs")
    output_box.fitAroundContents()
    node_list.update({"output_box" : output_box})

    # set display flag
    node_list["graft_set_dress1"].setDisplayFlag(True)

    #-------------------------------- create toolbox ---------------------------------#
    node_list.update(create_toolbox(["primitive",
                                     "prune",
                                     "graftbranches",
                                     "stagemanager",
                                     "restructurescenegraph",
                                     "instancer",
                                     "matchsize",
                                     "xform",
                                     "edit"], [-15,0]))


    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")

    return node_list
