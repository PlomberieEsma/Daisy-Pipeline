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

asset_stage = Usd.Stage.Open(f"{project_path}/03_Production/Assets/{asset_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
meters_per_unit = UsdGeom.GetStageMetersPerUnit(asset_stage)
print(f"meters per unit : {meters_per_unit}")

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def texture_detect() -> dict[str, str]:
    #-----------------------------------------------------------#
    # detect the textures latest version of the asset           #
    #                                                           #
    # return a dict of the filenames and paths of each texture  #
    #-----------------------------------------------------------#

    # get the last version of textures
    texture_version_dir = f"{project_path}/03_Production/Assets/{asset_path}/Textures/Texturing"
    try:
        texture_version_list = os.listdir(texture_version_dir)
    except:
        print("No texture found")
        return
    int_greater_version = 0
    greater_version = ""
    for tex_version in texture_version_list:
        int_tex_version = int(tex_version.replace("v", ""))
        if int_tex_version > int_greater_version:
            int_greater_version = int_tex_version
            greater_version = tex_version
    texture_last_version_dir = greater_version

    # get textures in a list
    texture_dir = f"{texture_version_dir}/{texture_last_version_dir}"
    texture_dir_content = os.listdir(texture_dir)
    texture_list = {}
    # keep only texture in the directory and create the output
    for content in texture_dir_content:
        if os.path.isfile(f"{texture_dir}/{content}"):
            texture_list.update({content : f"{texture_dir}/{content}"})

    return texture_list

def auto_material(parent_node: object) -> None:
    #-----------------------------------------------------------------------------------#
    # create a pxrSurface node with pxrTexture nodes set and connected automatically    #
    #                                                                                   #
    # parent_node : the node containing the shader                                      #
    #-----------------------------------------------------------------------------------#

    #--------------------------------- detections ----------------------------------#
    # create a dict with shader name, texture name and path
    texture_dict = texture_detect()
    if texture_dict == None:
        return
    material_dict: dict[str, dict[str, str]] = {}
    shader_name_list = []
    for texture in texture_dict:
        map_type = texture.split("_")[-3]
        shader_name = texture.split(f"_{map_type}")[0]

        if shader_name not in shader_name_list:
            shader_name_list.append(shader_name)
            material_dict.update({shader_name: {texture: texture_dict[texture]}})
        else:
            material_dict[shader_name].update({texture: texture_dict[texture]})

    #-------------------------------- create nodes ---------------------------------#
    # create shader nodes
    for shader in material_dict:
        mat_builder = parent_node.createNode("pxrmaterialbuilder")
        mat_builder.setName(shader)

        pxr_surface = mat_builder.createNode("pxrsurface::3.0")
        pxr_surface.setName(f"pxr_{shader}")

        output_collect = hou.node(f"/stage/{parent_node.name()}/{mat_builder.name()}/output_collect")
        output_collect.setInput(0, pxr_surface)

        # create texture nodes
        for tex in material_dict[shader]:
            map_type = tex.split("_")[-3]

            pxr_texture = mat_builder.createNode("pxrtexture::3.0")
            pxr_texture.setName(map_type)
            pxr_texture.parm("filename").set(material_dict[shader][tex].replace(project_path, "$PRISM_JOB"))

            # connect the pxrTexture nodes with the pxrSurface node
            try:
                if map_type == "Diffuse" or map_type == "BaseColor" or map_type == "Albedo":
                    pxr_surface.setInput(2, pxr_texture)
                elif map_type == "Specular":
                    pxr_surface.setInput(10, pxr_texture)
                    pxr_surface.parm("specularFresnelMode").set(1)
                    pxr_surface.parm("specularEdgeColorr").set(1)
                    pxr_surface.parm("specularEdgeColorg").set(1)
                    pxr_surface.parm("specularEdgeColorb").set(1)
                elif map_type == "Roughness":
                    pxr_surface.setInput(14, pxr_texture)
                    pxr_surface.parm("specularFresnelMode").set(1)
                    pxr_surface.parm("specularEdgeColorr").set(1)
                    pxr_surface.parm("specularEdgeColorg").set(1)
                    pxr_surface.parm("specularEdgeColorb").set(1)
                elif map_type == "Subsurface" or map_type == "SSS":
                    pxr_surface.setInput(54, pxr_texture)
                elif map_type == "SubsurfaceColor":
                    pxr_surface.setInput(55, pxr_texture)
                elif map_type == "Emissive" or map_type == "Glow":
                    pxr_surface.setInput(113, pxr_texture)
                elif map_type == "GlowColor":
                    pxr_surface.setInput(114, pxr_texture)
                elif map_type == "Opacity" or map_type == "Translucency" or map_type == "Presence":
                    pxr_surface.setInput(118, pxr_texture)
                else:
                    print(f"Unrecognized map type for {map_type}")
            except:
                print(f"Unrecognized map type for {map_type}")

        #-------------------------------- arange nodes ---------------------------------#
        mat_builder.layoutChildren()
    parent_node.layoutChildren()

def template_shading() -> dict[str, Any]:
    #-------------------------------------------------------------------------------#
    # This function creates the houdini node template for the Shading department    #
    #                                                                               #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    start_counter = perf_counter()

    # delete the HDA node to avoid it to influence the layout
    node_template = hou.node("/stage/create_template1")
    node_template.destroy()

    #-------------------------------- create nodes ---------------------------------#
    lopnet=hou.node("/stage")

    ref_geo1 = lopnet.createNode("Daisy::daisy_import")
    ref_geo1.setName("ref_geo1")
    ref_geo1.setPosition(node_position)
    ref_geo1.parm("importAs").set(1) #reference
    ref_geo1.parm("path").set(f"{env_var_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
    ref_geo1.parm("scale").set(meters_per_unit)

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

    create_component1 = lopnet.createNode("primitive")
    create_component1.setName("create_component1")
    create_component1.setInput(0, set_variant1)
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

    daisy_export1 = lopnet.createNode("Daisy::daisy_export::1.0")
    daisy_export1.setName("daisy_export1")
    daisy_export1.setInput(0, assign_shader1)
    node_position[1] -= 5
    daisy_export1.move(node_position)
    daisy_export1.parm("defaultprim").set("`chs(\"../create_component1/primpath\")`")
    daisy_export1.parm("metersperunit").set(meters_per_unit)

    auto_material(create_shader1)

    node_list = {"ref_geo1" : ref_geo1,
              "set_variant1" : set_variant1,
              "create_component1" : create_component1,
              "create_mtl1" : create_mtl1,
              "create_shader1" : create_shader1,
              "configure_mtl_primitives1" : configure_mtl_primitives1,
              "assign_shader1" : assign_shader1,
              "daisy_export1" : daisy_export1}
    
    #-------------------------------- arange nodes ---------------------------------#
    # set input network box
    nodes_in_input_box = ["ref_geo1", "set_variant1", "create_component1", "create_mtl1"]
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
    nodes_in_output_box = ["daisy_export1"]
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
