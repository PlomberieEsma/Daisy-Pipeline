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
import os, argparse, json
from time import perf_counter
from typing import Any
from pxr import Usd, UsdGeom # type: ignore

print("execute create_asset.py\n\n")

# title
try:
    from Scripts.DaisyTools.core.ascii_art import print_title
    print_title()
except:
    print("\nDaisy Pipeline\n\nby Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio\n\n")

# needs to be launched in hython by using prism, otherwise it will not work


class Error(Exception):
    # use to raise errors in the script
    pass

##########################################################################################################################################
#=========================================================== SET VARIABLES ===============================================================
##########################################################################################################################################

# customization of the command line to pass the name of the asset to be processed and its info
try:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assetName", type=str, help="name of the asset to be processed")
    parser.add_argument("--path", type=str, help="path of the asset to be processed")
    parser.add_argument("--assetPath", type=str, help="path of the asset to be processed from 'Assets' to the asset name")
    parser.add_argument("--projectPath", type=str, help="project path of the asset to be processed")
    parser.add_argument("--packed", type=bool, help="whether the asset is packed or not")
    args = parser.parse_args()
except:
    raise Error("An argument is missing in the command line, please check the command line arguments\n\nThe command line should be : hython create_asset.py --assetName <asset_name> --path <asset_path> --projectPath <project_path> --packed <True/False>")

try:
    asset_name = args.assetName
    print(f"asset to process : {asset_name}")
except:
    raise Error("No asset name passed in the hython command line, please check the command line arguments")


path = args.path
asset_path = args.assetPath
project_path = args.projectPath
env_var_path = f"$PRISM_JOB/03_Production/Assets/{asset_path}"
packed = args.packed

print(f"{path = }")
print(f"{asset_path = }")
print(f"{project_path = }")
print(f"{env_var_path = }")
print(f"{packed = }")

tasks = os.listdir(f"{path}/Export")
tasks_save = list(tasks)

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

usd_file_format = config_file["global"]["usd_file_format"]
autoproxy_polygone_number = config_file["create_usd_asset"]["autoproxy_polygone_number"]
variant_digit_number = config_file["create_usd_asset"]["variant_digit_number"]

print("\n\n--------------------------------------------------------------------------------------------------\n\n")
print(f"tasks : {tasks}")

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def mod_detect(tasks: list[str]) -> dict[str,Any]:

    #-------------------------------------------------------#
    # Detect if there is a ModH and/or a ModL,              #
    # returns a dictionary with :                           #
    # - the department name                                 #
    # - whether there is a ModL                             #
    # - whether there is a ModH                             #
    # - the string to detect for identifying the mode tasks #
    #-------------------------------------------------------#


    is_ModH = False
    is_ModL = False
    if "ModH" in tasks:
        string_to_detect = "ModH"
        is_ModH = True
        if "ModL" in tasks:
            is_ModL = True
    elif "ModL" in tasks:
        string_to_detect = "ModL"
        is_ModL = True
    else:
        raise Error("No modL or ModH found in the tasks list, you need at least one of them to create the USD asset")

    print(f"is ModH = {is_ModH}")
    print(f"is ModL = {is_ModL}")

    is_mod_level = {"departement" : "geo",
                    "ModL" : is_ModL,
                    "ModH" : is_ModH,
                    "str_to_detect" : string_to_detect}
    return is_mod_level

def grm_detect(tasks: list[str]) -> dict[str,Any]:

    #-----------------------------------------------------------#
    # Detect if there is a groom and a groom proxy,             #
    # returns a dictionary with :                               #
    # - the department name                                     #
    # - whether there is a GrmL                                 #
    # - whether there is a GrmH                                 #
    # - the string to detect for identifying the groom tasks    #
    #-----------------------------------------------------------#


    is_GrmH = False
    is_GrmL = False
    if "Groom" in tasks:
        string_to_detect = "Groom"
        files = os.listdir(f"{path}/Export/Groom/master")
        for file in files:
            if "Groom_master" in file:
                is_GrmH = True
                if "proxy" in file:
                    is_GrmL = True
            else:
                if "proxy" in file:
                    is_GrmL = True
    else:
        string_to_detect = "Groom"

    print(f"is GrmH = {is_GrmH}")
    print(f"is GrmL = {is_GrmL}")

    is_grm_level = {"departement" : "grm",
                    "GrmL" : is_GrmL,
                    "GrmH" : is_GrmH,
                    "str_to_detect" : string_to_detect}
    return is_grm_level

def mtl_detect(tasks: list[str]) -> dict[str,Any]:

    #-----------------------------------------------------------#
    # Detect if there is a material (of geo),                   #
    # returns a dictionary with :                               #
    # - the department name                                     #
    # - whether there is a Shader                               #
    # - the string to detect for identifying the material tasks #
    #-----------------------------------------------------------#


    is_Shading = False
    if "Shading" in tasks:
        string_to_detect = "Shading"
        is_Shading = True
    else:
        string_to_detect = "Shading"

    print(f"is Shading = {is_Shading}")

    is_mtl_level = {"departement" : "mtl",
                    "Shading" : is_Shading,
                    "str_to_detect" : string_to_detect}
    return is_mtl_level

def mtl_groom_detect(tasks: list[str]) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # Detect if there is a material (of groom),                         #
    # returns a dictionary with :                                       #
    # - the department name                                             #
    # - whether there is a Shader of groom                              #
    # - the string to detect for identifying the groom material tasks   #
    #-------------------------------------------------------------------#


    is_ShadingGroom = False
    if "ShadingGroom" in tasks:
        string_to_detect = "ShadingGroom"
        is_ShadingGroom = True
    else:
        string_to_detect = "ShadingGroom"

    print(f"is ShadingGroom = {is_ShadingGroom}")

    is_mtl_groom_level = {"departement" : "mtl_groom",
                    "ShadingGroom" : is_ShadingGroom,
                    "str_to_detect" : string_to_detect}
    return is_mtl_groom_level

def variant_list(departement: str, string_to_detect: str, tasks: list[str]) -> dict[str,Any]:

    #---------------------------------------------------------------#
    # Detect if there are variants for the associated department,   #
    # returns a dictionary with :                                   #
    # - whether there are variants                                  #
    # - the list of variant names                                   #
    #---------------------------------------------------------------#


    is_variant = False

    previews_deleted = False
    contrecompte = 0

    # lists all the tasks and checks if they are part of the department
    # if not, it deletes the department from the list
    # then, for the tasks that are kept, it renames them

    for i in range(len(tasks)):
        if previews_deleted:
            # if a task has been popped previously
            contrecompte += 1
            previews_deleted = False

        if string_to_detect not in tasks[i-contrecompte]:
            # delete the task from the list if it is not part of the targeted department
            tasks.pop(i-contrecompte)
            previews_deleted = True
        else:
            # what's not in the targeted department
            dont_change_name = False
            if departement == "grm" or departement == "mtl":
                if "ShadingGroom" in tasks[i-contrecompte]:
                    # special case for ShadingGroom, we don't want to rename it
                    tasks.pop(i-contrecompte)
                    previews_deleted = True
                    dont_change_name = True

            try:
                if string_to_detect in tasks[i-contrecompte] and dont_change_name == False:
                    # rename the task to the department name, so that it can be used in the nodes creation
                    tasks[i-contrecompte] = tasks[i-contrecompte].replace(string_to_detect, departement)
                    dont_change_name = False
            except:
                pass

    variants = tasks

    variant_index = 0

    # rename the variants to have a uniform naming convention, and check if there are any variants
    for variant in variants:
        if "_var" in variant:
            is_variant = True
        else:
            variants[variant_index] = variant + "_var01"
        variant_index += 1

    print(f"{departement} variants : {variants}")
    variant_list = {"is_variant" : is_variant, "variants" : variants}
    return variant_list

##########################################################################################################################################
#============================================================== HOUDINI ==================================================================
##########################################################################################################################################

def nodes_var_geo(tasks: list[str], asset_name: str, node_input: Any, detections: dict[str,dict[str,Any]]) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # Create nodes for each geo variant                                 #
    # makes a loop to create the nodes for each variant                 #
    # creates an automatic proxy if it doesn't exist                    #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"
    proxy_path = f"{env_var_path}/Export/ModL/master/{asset_name}_ModL_master.{usd_file_format}"
    render_path = f"{env_var_path}/Export/ModH/master/{asset_name}_ModH_master.{usd_file_format}"

    detect_geo = detections["geo"]
    var_list = variant_list(detect_geo["departement"], detect_geo["str_to_detect"], tasks)
    is_geo_variant = var_list["is_variant"]
    geo_variants = var_list["variants"]

    # create two lists for ModL and ModH, and check if they have the same number of variants
    modL_list = []
    modH_list = []
    tasks = list(tasks_save)
    for task in tasks:
        if "ModL" in task:
            modL_list.append(task.replace("ModL", "ModL_var01") if task == "ModL" else task)
        if "ModH" in task:
            modH_list.append(task.replace("ModH", "ModH_var01") if task == "ModH" else task)

    compteur = len(modL_list) if len(modL_list)>len(modH_list) else len(modH_list)
    
    # check if the two lists have the same number of variants, if not, add None to the list with less variants
    for i in range(compteur):
        try:
            if int(modH_list[i][-variant_digit_number:]) < int(modL_list[i][-variant_digit_number:]):
                modL_list.insert(i, None)
            elif int(modH_list[i][-variant_digit_number:]) > int(modL_list[i][-variant_digit_number:]):
                modH_list.insert(i, None)
            else:
                pass
        except IndexError:
            if len(modH_list) > len(modL_list):
                modL_list.append(None)
            else:
                modH_list.append(None)


    lopnet=hou.node("/stage")

    if is_geo_variant:
        var_output = []
        for variant in geo_variants:

            # modifies the variant paths
            proxy_var_path = proxy_path
            if variant != "geo_var01":
                proxy_var_path = proxy_path.replace("ModL", "ModL" + variant.replace("geo", ""))
            render_var_path = render_path
            if variant != "geo_var01":
                render_var_path = render_path.replace("ModH", "ModH" + variant.replace("geo", ""))

            if modL_list[int(variant[-variant_digit_number:])-1] is not None:
                ref_geo_prox = lopnet.createNode("reference")
                ref_geo_prox.setName("ref_geo_prox" + variant[-variant_digit_number:])
                ref_geo_prox.setInput(0, node_input)
                ref_geo_prox.parm("primpath1").set(f"{root_name}/geo/proxy")
                ref_geo_prox.parm("filepath1").set(proxy_var_path)
            else:
                # if there is no modL aviable, we create it with a polyreduce node
                print("create geometry proxy for : " + variant)
                ref_geo_prox = lopnet.createNode("subnet")
                ref_geo_prox.setName("create_geo_prox" + variant[-variant_digit_number:])
                ref_geo_prox.setInput(0, node_input)

                subnet_input = ref_geo_prox.indirectInputs()[0]

                sop_geo_prox1 = ref_geo_prox.createNode("sopnet")
                sop_geo_prox1.setName("sop_geo_prox1")

                usd_import1 = sop_geo_prox1.createNode("usdimport")
                usd_import1.setName("usd_import" + variant[-variant_digit_number:])
                usd_import1.parm("filepath1").set(render_var_path)
                usd_import1.parm("importtime").set(1.0)
                usd_import1.parm("input_unpack").set(1)
                usd_import1.parm("unpack_geomtype").set(1) #polygons

                polyreduce1 = sop_geo_prox1.createNode("polyreduce")
                polyreduce1.setName("polyreduce" + variant[-variant_digit_number:])
                polyreduce1.setInput(0, usd_import1)
                polyreduce1.parm("target").set(2) #output polygone coun
                polyreduce1.parm("finalcount").set(autoproxy_polygone_number)

                import_sop1 = ref_geo_prox.createNode("sopimport")
                import_sop1.setName("import_sop" + variant[-variant_digit_number:])
                import_sop1.setInput(0, subnet_input)
                import_sop1.parm("soppath").set(polyreduce1.path()) #path to polyreduce
                import_sop1.parm("asreference").set(1)
                import_sop1.parm("reftype").set("referencestrong") #stronger reference
                import_sop1.parm("primpath").set(f"{root_name}/geo/proxy")
                import_sop1.parm("parentprimkind").set("") #none
                import_sop1.parm("parentprimtype").set("UsdGeomScope") #scope
                import_sop1.parm("enable_savepath").set(1)
                import_sop1.parm("savepath").set(f"{env_var_path}/Export/ModL_var{variant[-variant_digit_number:]}/master/{asset_name}_ModL_var{variant[-variant_digit_number:]}_master.{usd_file_format}")

                subnet_output = subnet_input.outputs()[0]
                subnet_output.setInput(0, import_sop1)

            config_geo_prox = lopnet.createNode("configureprimitive")
            config_geo_prox.setName(f"config_geo_prox{variant[-variant_digit_number:]}")
            config_geo_prox.setInput(0, ref_geo_prox)
            config_geo_prox.parm("primpattern").set(f"{root_name}/geo/proxy")
            config_geo_prox.parm("setpurpose").set(1)
            config_geo_prox.parm("purpose").set("proxy")
            config_geo_prox.parm("setkind").set(1)

            ref_geo_render = lopnet.createNode("reference")
            ref_geo_render.setName(f"ref_geo_render{variant[-variant_digit_number:]}")
            ref_geo_render.setInput(0, node_input)
            ref_geo_render.parm("primpath1").set(f"{root_name}/geo/render")
            ref_geo_render.parm("filepath1").set(render_var_path)

            config_geo_render = lopnet.createNode("configureprimitive")
            config_geo_render.setName(f"config_geo_render{variant[-variant_digit_number:]}")
            config_geo_render.setInput(0, ref_geo_render)
            config_geo_render.parm("primpattern").set(f"{root_name}/geo/render")
            config_geo_render.parm("setpurpose").set(1)
            config_geo_render.parm("purpose").set("render")
            config_geo_render.parm("setproxy").set(1)
            config_geo_render.parm("proxy").set(f"{root_name}/geo/proxy")
            config_geo_render.parm("setkind").set(1)

            graft_geo_purpose = lopnet.createNode("graftbranches")
            graft_geo_purpose.setName(f"graft_geo_purpose{variant[-variant_digit_number:]}")
            graft_geo_purpose.setInput(0, config_geo_prox)
            graft_geo_purpose.setInput(1, config_geo_render)
            graft_geo_purpose.parm("primpath").set(f"{root_name}/geo/render")
            graft_geo_purpose.parm("parentprimtype").set("None")
            graft_geo_purpose.parm("destasparent").set(0)
            graft_geo_purpose.parm("srcprimpath1").set(f"{root_name}/geo/render")

            geo_var = lopnet.createNode("null")
            geo_var.setName(variant)
            geo_var.setInput(0, graft_geo_purpose)

            var_output.append(geo_var)

        add_geo_var = lopnet.createNode("addvariant")
        add_geo_var.setName("add_geo_var1")
        for output in var_output:
            add_geo_var.setInput(100, output)
        add_geo_var.parm("primpath").set(root_name)
        add_geo_var.parm("primkind").set("component")
        add_geo_var.parm("parentprimtype").set("none")
        add_geo_var.parm("variantset").set("geo")
        add_geo_var.parm("variantprimpath").set(root_name)

        set_geo_extents = lopnet.createNode("setextents")
        set_geo_extents.setName("set_geo_extents1")
        set_geo_extents.setInput(0, add_geo_var)
        set_geo_extents.parm("primitives").set(f"{root_name}/* &(%kind:subcomponent + */geo)")

    else:
        if detect_geo["ModL"]:
            ref_geo_prox = lopnet.createNode("reference")
            ref_geo_prox.setName("ref_geo_prox")
            ref_geo_prox.setInput(0, node_input)
            ref_geo_prox.parm("primpath1").set(f"{root_name}/geo/proxy")
            ref_geo_prox.parm("filepath1").set(proxy_path)
        else:
            # if there is no modL aviable, we create it with a polyreduce node
            print("create geometry proxy")
            ref_geo_prox = lopnet.createNode("subnet")
            ref_geo_prox.setName("create_geo_prox1")
            ref_geo_prox.setInput(0, node_input)

            subnet_input = ref_geo_prox.indirectInputs()[0]

            sop_geo_prox1 = ref_geo_prox.createNode("sopnet")
            sop_geo_prox1.setName("sop_geo_prox1")

            usd_import1 = sop_geo_prox1.createNode("usdimport")
            usd_import1.setName("usd_import1")
            usd_import1.parm("filepath1").set(render_path)
            usd_import1.parm("importtime").set(1.0)
            usd_import1.parm("input_unpack").set(1)
            usd_import1.parm("unpack_geomtype").set(1) #polygons

            polyreduce1 = sop_geo_prox1.createNode("polyreduce")
            polyreduce1.setName("polyreduce1")
            polyreduce1.setInput(0, usd_import1)
            polyreduce1.parm("target").set(2) #output polygone coun
            polyreduce1.parm("finalcount").set(3000)

            import_sop1 = ref_geo_prox.createNode("sopimport")
            import_sop1.setName("import_sop1")
            import_sop1.setInput(0, subnet_input)
            import_sop1.parm("soppath").set(polyreduce1.path()) #path to polyreduce
            import_sop1.parm("asreference").set(1)
            import_sop1.parm("reftype").set("referencestrong") #stronger reference
            import_sop1.parm("primpath").set(f"{root_name}/geo/proxy")
            import_sop1.parm("parentprimkind").set("") #none
            import_sop1.parm("parentprimtype").set("UsdGeomScope") #scope
            import_sop1.parm("enable_savepath").set(1)
            import_sop1.parm("savepath").set(f"{env_var_path}/Export/ModL/master/{asset_name}_ModL_master.{usd_file_format}")

            subnet_output = subnet_input.outputs()[0]
            subnet_output.setInput(0, import_sop1)

        config_geo_prox = lopnet.createNode("configureprimitive")
        config_geo_prox.setName("config_geo_prox1")
        config_geo_prox.setInput(0, ref_geo_prox)
        config_geo_prox.parm("primpattern").set(f"{root_name}/geo/proxy")
        config_geo_prox.parm("setpurpose").set(1)
        config_geo_prox.parm("purpose").set("proxy")
        config_geo_prox.parm("setkind").set(1)

        ref_geo_render = lopnet.createNode("reference")
        ref_geo_render.setName("ref_geo_render1")
        ref_geo_render.setInput(0, node_input)
        ref_geo_render.parm("primpath1").set(f"{root_name}/geo/render")
        ref_geo_render.parm("filepath1").set(render_path)

        config_geo_render = lopnet.createNode("configureprimitive")
        config_geo_render.setName("config_geo_render1")
        config_geo_render.setInput(0, ref_geo_render)
        config_geo_render.parm("primpattern").set(f"{root_name}/geo/render")
        config_geo_render.parm("setpurpose").set(1)
        config_geo_render.parm("purpose").set("render")
        config_geo_render.parm("setproxy").set(1)
        config_geo_render.parm("proxy").set(f"{root_name}/geo/proxy")
        config_geo_render.parm("setkind").set(1)

        graft_geo_purpose = lopnet.createNode("graftbranches")
        graft_geo_purpose.setName("graft_geo_purpose1")
        graft_geo_purpose.setInput(0, config_geo_prox)
        graft_geo_purpose.setInput(1, config_geo_render)
        graft_geo_purpose.parm("primpath").set(f"{root_name}/geo/render")
        graft_geo_purpose.parm("parentprimtype").set("None")
        graft_geo_purpose.parm("destasparent").set(0)
        graft_geo_purpose.parm("srcprimpath1").set(f"{root_name}/geo/render")

        set_geo_extents = lopnet.createNode("setextents")
        set_geo_extents.setName("set_geo_extents1")
        set_geo_extents.setInput(0, graft_geo_purpose)
        set_geo_extents.parm("primitives").set(f"{root_name}/* &(%kind:subcomponent + */geo)")

    outputs = {"ref_geo_prox" : ref_geo_prox,
               "config_geo_prox" : config_geo_prox,
               "ref_geo_render" : ref_geo_render,
               "config_geo_render" : config_geo_render,
               "graft_geo_purpose" : graft_geo_purpose,
               "set_geo_extents" : set_geo_extents}
    return outputs

def nodes_var_grm(tasks: list[str], asset_name: str, node_input: Any, detections: dict[str,dict[str,Any]]) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # Create nodes for each groom variant                               #
    # makes a loop to create the nodes for each variant                 #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"
    proxy_path = f"{env_var_path}/Export/Groom/master/{asset_name}_Groom_proxy_master.{usd_file_format}"
    render_path = f"{env_var_path}/Export/Groom/master/{asset_name}_Groom_master.{usd_file_format}"

    detect_grm = detections["grm"]
    var_list = variant_list(detect_grm["departement"], detect_grm["str_to_detect"], tasks)
    is_grm_variant = var_list["is_variant"]
    grm_variants = var_list["variants"]

    lopnet=hou.node("/stage")

    begin_var_grm = None
    add_grm_var = None

    if is_grm_variant:
        var_output = []

        begin_var_grm = lopnet.createNode("begincontextoptionsblock")
        begin_var_grm.setName("begin_var_grm1")
        begin_var_grm.setInput(0, node_input)
        begin_var_grm.parm("layerbreak").set(1)
        begin_var_grm.setColor(hou.Color((1,0.5,0.2)))

        for variant in grm_variants:

            # modifies the variant paths
            proxy_var_path = proxy_path
            if variant != "grm_var01":
                proxy_var_path = proxy_path.replace("Groom", "Groom" + variant.replace("grm", ""))
            render_var_path = render_path
            if variant != "grm_var01":
                render_var_path = render_path.replace("Groom", "Groom" + variant.replace("grm", ""))


            ref_grm_prox = lopnet.createNode("reference")
            ref_grm_prox.setName(f"ref_grm_prox{variant[-variant_digit_number:]}")
            ref_grm_prox.setInput(0, begin_var_grm)
            ref_grm_prox.parm("primpath1").set(f"{root_name}/grm/proxy")
            ref_grm_prox.parm("filepath1").set(proxy_var_path)

            config_grm_prox = lopnet.createNode("configureprimitive")
            config_grm_prox.setName(f"config_grm_prox{variant[-variant_digit_number:]}")
            config_grm_prox.setInput(0, ref_grm_prox)
            config_grm_prox.parm("primpattern").set(f"{root_name}/grm/proxy")
            config_grm_prox.parm("setpurpose").set(1)
            config_grm_prox.parm("purpose").set("proxy")
            config_grm_prox.parm("setkind").set(1)

            ref_grm_render = lopnet.createNode("reference")
            ref_grm_render.setName(f"ref_grm_render{variant[-variant_digit_number:]}")
            ref_grm_render.setInput(0, begin_var_grm)
            ref_grm_render.parm("primpath1").set(f"{root_name}/grm/render")
            ref_grm_render.parm("filepath1").set(render_var_path)

            config_grm_render = lopnet.createNode("configureprimitive")
            config_grm_render.setName(f"config_grm_render{variant[-variant_digit_number:]}")
            config_grm_render.setInput(0, ref_grm_render)
            config_grm_render.parm("primpattern").set(f"{root_name}/grm/render")
            config_grm_render.parm("setpurpose").set(1)
            config_grm_render.parm("purpose").set("render")
            config_grm_render.parm("setproxy").set(1)
            config_grm_render.parm("proxy").set(f"{root_name}/grm/proxy")
            config_grm_render.parm("setkind").set(1)

            graft_grm_purpose = lopnet.createNode("graftbranches")
            graft_grm_purpose.setName(f"graft_grm_purpose{variant[-variant_digit_number:]}")
            graft_grm_purpose.setInput(0, config_grm_prox)
            graft_grm_purpose.setInput(1, config_grm_render)
            graft_grm_purpose.parm("primpath").set(f"{root_name}/grm/render")
            graft_grm_purpose.parm("parentprimtype").set("None")
            graft_grm_purpose.parm("destasparent").set(0)
            graft_grm_purpose.parm("srcprimpath1").set(f"{root_name}/grm/render")

            grm_var = lopnet.createNode("null")
            grm_var.setName(variant)
            grm_var.setInput(0, graft_grm_purpose)

            var_output.append(grm_var)

        add_grm_var = lopnet.createNode("addvariant")
        add_grm_var.setName("add_grm_var")
        add_grm_var.setInput(0, begin_var_grm)
        for output in var_output:
            add_grm_var.setInput(100, output)
        add_grm_var.parm("primpath").set(root_name)
        add_grm_var.parm("primkind").set("component")
        add_grm_var.parm("parentprimtype").set("none")
        add_grm_var.parm("createoptionsblock").set(1)
        add_grm_var.parm("variantset").set("grm")
        add_grm_var.parm("variantprimpath").set(root_name)

        set_grm_extents = lopnet.createNode("setextents")
        set_grm_extents.setName("set_grm_extents1")
        set_grm_extents.setInput(0, add_grm_var)
        set_grm_extents.parm("primitives").set(f"{root_name}/* &(%kind:subcomponent + */grm)")
    
    else:
        ref_grm_prox = lopnet.createNode("reference")
        ref_grm_prox.setName("ref_grm_prox1")
        ref_grm_prox.setInput(0, node_input)
        ref_grm_prox.parm("primpath1").set(f"{root_name}/grm/proxy")
        ref_grm_prox.parm("filepath1").set(proxy_path)

        config_grm_prox = lopnet.createNode("configureprimitive")
        config_grm_prox.setName("config_grm_prox1")
        config_grm_prox.setInput(0, ref_grm_prox)
        config_grm_prox.parm("primpattern").set(f"{root_name}/grm/proxy")
        config_grm_prox.parm("setpurpose").set(1)
        config_grm_prox.parm("purpose").set("proxy")
        config_grm_prox.parm("setkind").set(1)

        ref_grm_render = lopnet.createNode("reference")
        ref_grm_render.setName("ref_grm_render1")
        ref_grm_render.setInput(0, node_input)
        ref_grm_render.parm("primpath1").set(f"{root_name}/grm/render")
        ref_grm_render.parm("filepath1").set(render_path)

        config_grm_render = lopnet.createNode("configureprimitive")
        config_grm_render.setName("config_grm_render1")
        config_grm_render.setInput(0, ref_grm_render)
        config_grm_render.parm("primpattern").set(f"{root_name}/grm/render")
        config_grm_render.parm("setpurpose").set(1)
        config_grm_render.parm("purpose").set("render")
        config_grm_render.parm("setproxy").set(1)
        config_grm_render.parm("proxy").set(f"{root_name}/grm/proxy")
        config_grm_render.parm("setkind").set(1)

        graft_grm_purpose = lopnet.createNode("graftbranches")
        graft_grm_purpose.setName("graft_grm_purpose1")
        graft_grm_purpose.setInput(0, config_grm_prox)
        graft_grm_purpose.setInput(1, config_grm_render)
        graft_grm_purpose.parm("primpath").set(f"{root_name}/grm/render")
        graft_grm_purpose.parm("parentprimtype").set("None")
        graft_grm_purpose.parm("destasparent").set(0)
        graft_grm_purpose.parm("srcprimpath1").set(f"{root_name}/grm/render")

        set_grm_extents = lopnet.createNode("setextents")
        set_grm_extents.setName("set_grm_extents1")
        set_grm_extents.setInput(0, graft_grm_purpose)
        set_grm_extents.parm("primitives").set(f"{root_name}/* &(%kind:subcomponent + */grm)")

    outputs = {"ref_grm_prox" : ref_grm_prox,
               "config_grm_prox" : config_grm_prox,
               "ref_grm_render" : ref_grm_render,
               "config_grm_render" : config_grm_render,
               "graft_grm_purpose" : graft_grm_purpose,
               "set_grm_extents" : set_grm_extents}
    
    if is_grm_variant:
        outputs.update({"begin_var_grm" : begin_var_grm, "add_grm_var" : add_grm_var})
    return outputs

def nodes_var_mtl(tasks: list[str], asset_name: str, node_input: Any, detections: dict[str,dict[str,Any]]) -> dict[str,Any]:

    #-----------------------------------------------------------------------------------------------------------#
    # create nodes for each material variant (for geo and groom)                                                #
    # create 2 loops to create the nodes for each variant (one for geo and one for groom)                       #
    # merge the 2 node groups                                                                                   #
    # return the list of all created nodes                                                                      #
    #-----------------------------------------------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"
    mtl_path = f"{env_var_path}/Export/Shading/master/{asset_name}_Shading_master.{usd_file_format}"
    mtl_groom_path = f"{env_var_path}/Export/ShadingGroom/master/{asset_name}_ShadingGroom_master.{usd_file_format}"

    var_mtl_list = variant_list(detections["mtl"]["departement"], detections["mtl"]["str_to_detect"], tasks)
    is_mtl_variant = var_mtl_list["is_variant"]
    mtl_variants = var_mtl_list["variants"]

    tasks = list(tasks_save)

    var_mtl_groom_list = variant_list(detections["mtl_groom"]["departement"], detections["mtl_groom"]["str_to_detect"], tasks)
    is_mtl_groom_variant = var_mtl_groom_list["is_variant"]
    mtl_groom_variants = var_mtl_groom_list["variants"]


    lopnet=hou.node("/stage")

    begin_var_mtl = None
    outputs = {}

    if is_mtl_variant:
        # for the shading of the geo
        var_output = []

        begin_var_mtl = lopnet.createNode("begincontextoptionsblock")
        begin_var_mtl.setName("begin_var_mtl1")
        begin_var_mtl.setInput(0, node_input)
        begin_var_mtl.parm("layerbreak").set(1)
        begin_var_mtl.setColor(hou.Color((1,0.5,0.2)))

        for variant in mtl_variants:

            # modifies the variant paths
            mtl_var_path = mtl_path
            if variant != "mtl_var01":
                mtl_var_path = mtl_path.replace("Shading", "Shading" + variant.replace("mtl", ""))

            ref_mtl = lopnet.createNode("sublayer")
            ref_mtl.setName(f"ref_mtl{variant[-variant_digit_number:]}")
            ref_mtl.setInput(0, begin_var_mtl)
            ref_mtl.parm("editrootlayer").set(0)
            ref_mtl.parm("filepath1").set(mtl_var_path)

            mtl_var = lopnet.createNode("null")
            mtl_var.setName(variant)
            mtl_var.setInput(0, ref_mtl)

            var_output.append(mtl_var)

        add_mtl_var1 = lopnet.createNode("addvariant")
        add_mtl_var1.setName("add_mtl_var1")
        add_mtl_var1.setInput(0, begin_var_mtl)
        for output in var_output:
            add_mtl_var1.setInput(100, output)
        add_mtl_var1.parm("primpath").set(root_name)
        add_mtl_var1.parm("primkind").set("component")
        add_mtl_var1.parm("parentprimtype").set("none")
        add_mtl_var1.parm("createoptionsblock").set(1)
        add_mtl_var1.parm("variantset").set("mtl")
        add_mtl_var1.parm("variantprimpath").set(root_name)
    
    else:
        if detections["mtl"]["Shading"]:
            ref_mtl1 = lopnet.createNode("sublayer")
            ref_mtl1.setName("ref_mtl1")
            ref_mtl1.setInput(0, node_input)
            ref_mtl1.parm("editrootlayer").set(0)
            ref_mtl1.parm("filepath1").set(mtl_path)

            outputs.update({"ref_mtl1" : ref_mtl1})


    if is_mtl_groom_variant:
        # for the shading of the groom
        var_output = []

        begin_var_mtl_groom = lopnet.createNode("begincontextoptionsblock")
        begin_var_mtl_groom.setName("begin_var_mtl_groom1")
        begin_var_mtl_groom.setInput(0, node_input)
        begin_var_mtl_groom.parm("layerbreak").set(1)
        begin_var_mtl_groom.setColor(hou.Color((1,0.5,0.2)))

        for variant in mtl_groom_variants:

            # modifies the variant paths
            mtl_groom_var_path = mtl_groom_path
            if variant != "mtl_groom_var01":
                mtl_groom_var_path = mtl_groom_path.replace("Shading", "Shading" + variant.replace("mtl_groom", ""))


            ref_mtl_groom = lopnet.createNode("reference")
            ref_mtl_groom.setName(f"ref_mtl_groom{variant[-variant_digit_number:]}")
            ref_mtl_groom.setInput(0, begin_var_mtl_groom)
            ref_mtl_groom.parm("primpath1").set(root_name)
            ref_mtl_groom.parm("filepath1").set(mtl_groom_var_path)

            mtl_groom_var = lopnet.createNode("null")
            mtl_groom_var.setName(variant)
            mtl_groom_var.setInput(0, ref_mtl_groom)

            var_output.append(mtl_groom_var)

        add_mtl_groom_var1 = lopnet.createNode("addvariant")
        add_mtl_groom_var1.setName("add_mtl_groom_var1")
        add_mtl_groom_var1.setInput(0, begin_var_mtl_groom)
        for output in var_output:
            add_mtl_groom_var1.setInput(100, output)
        add_mtl_groom_var1.parm("primpath").set(root_name)
        add_mtl_groom_var1.parm("primkind").set("component")
        add_mtl_groom_var1.parm("parentprimtype").set("none")
        add_mtl_groom_var1.parm("createoptionsblock").set(1)
        add_mtl_groom_var1.parm("variantset").set("mtl_groom")
        add_mtl_groom_var1.parm("variantprimpath").set(root_name)
    
    else:
        if detections["mtl_groom"]["ShadingGroom"]:
            ref_mtl_groom1 = lopnet.createNode("reference")
            ref_mtl_groom1.setName("ref_mtl_groom1")
            ref_mtl_groom1.setInput(0, node_input)
            ref_mtl_groom1.parm("primpath1").set(root_name)
            ref_mtl_groom1.parm("filepath1").set(mtl_groom_path)

            outputs.update({"ref_mtl_groom1" : ref_mtl_groom1})


    if detections["mtl"]["Shading"] and detections["mtl_groom"]["ShadingGroom"]:
        merge_mtl_mtl_groom1 = lopnet.createNode("merge")
        merge_mtl_mtl_groom1.setName("merge_mtl_mtl_groom1")
        if var_mtl_list["is_variant"]:
            merge_mtl_mtl_groom1.setInput(0, add_mtl_var1)
        else:
            merge_mtl_mtl_groom1.setInput(0, ref_mtl1)
        if var_mtl_groom_list["is_variant"]:
            merge_mtl_mtl_groom1.setInput(1, add_mtl_groom_var1)
        else:
            merge_mtl_mtl_groom1.setInput(1, ref_mtl_groom1)

        outputs.update({"merge_mtl_mtl_groom1" : merge_mtl_mtl_groom1})

    if is_mtl_variant:
        outputs.update({"begin_var_mtl" : begin_var_mtl, "add_mtl_var1" : add_mtl_var1})
    if is_mtl_groom_variant:
        outputs.update({"begin_var_mtl_groom" : begin_var_mtl_groom, "add_mtl_groom_var1" : add_mtl_groom_var1})
    return {"outputs" : outputs, "var_mtl_list" : var_mtl_list, "var_mtl_groom_list" : var_mtl_groom_list}


# ---------------------------------------- departements ------------------------------------------------

def nodes_geo(tasks: list[str], asset_name: str, detetcions: dict[str,dict[str,Any]], meters_per_unit: float) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # create geo nodes                                                  #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"

    lopnet=hou.node("/stage")

    create_component1 = lopnet.createNode("primitive")
    create_component1.setName("create_component1")
    create_component1.parm("primpath").set(root_name)
    create_component1.parm("primkind").set("component") #component

    create_geo1 = lopnet.createNode("primitive")
    create_geo1.setName("create_geo1")
    create_geo1.setInput(0, create_component1)
    create_geo1.parm("primpath").set(f"{root_name}/geo/proxy\n{root_name}/geo/render")
    create_geo1.parm("parentprimtype").set("UsdGeomScope") #scope
    create_geo1.parm("primtype").set("UsdGeomScope") #scope

    set_geo_purpose1 = lopnet.createNode("configureprimitive")
    set_geo_purpose1.setName("set_geo_purpose1")
    set_geo_purpose1.setInput(0, create_geo1)
    set_geo_purpose1.parm("primpattern").set(f"{root_name}/geo")
    set_geo_purpose1.parm("setpurpose").set(1)

    nodes_var_geo_list = nodes_var_geo(tasks, asset_name, set_geo_purpose1, detetcions)

    config_geo_layer1 = lopnet.createNode("configurelayer")
    config_geo_layer1.setName("config_geo_layer1")
    config_geo_layer1.setInput(0, nodes_var_geo_list["set_geo_extents"])
    config_geo_layer1.parm("setsavepath").set(1)
    config_geo_layer1.parm("savepath").set(f"{env_var_path}/Export/USD/layers/geo.{usd_file_format}")
    config_geo_layer1.parm("setdefaultprim").set(1)
    config_geo_layer1.parm("defaultprim").set(root_name)
    config_geo_layer1.parm("flattenop").set("layer")# flatten input layers
    config_geo_layer1.parm("setmetersperunit").set(1)
    config_geo_layer1.parm("metersperunit").set(meters_per_unit)

    outputs = {"create_component1" : create_component1,
               "create_geo1" : create_geo1,
               "set_geo_purpose1" : set_geo_purpose1,
               "config_geo_layer1" : config_geo_layer1}
    outputs.update(nodes_var_geo_list)
    return outputs

def nodes_groom(tasks: list[str], asset_name: str, input_nodes: dict[str,Any], detections: dict[str,dict[str,Any]], meters_per_unit: float) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # create groom nodes                                                #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"

    lopnet=hou.node("/stage")

    layer_grm_break1 = lopnet.createNode("layerbreak")
    layer_grm_break1.setName("layer_grm_break1")
    layer_grm_break1.setInput(0, input_nodes["config_geo_layer1"])

    create_grm1 = lopnet.createNode("primitive")
    create_grm1.setName("create_grm1")
    create_grm1.setInput(0, layer_grm_break1)
    create_grm1.parm("primpath").set(f"{root_name}/grm/proxy\n" + f"{root_name}/grm/render")
    create_grm1.parm("parentprimtype").set("UsdGeomScope") #scope
    create_grm1.parm("primtype").set("UsdGeomScope") #scope

    set_grm_purpose1 = lopnet.createNode("configureprimitive")
    set_grm_purpose1.setName("set_grm_purpose1")
    set_grm_purpose1.setInput(0, create_grm1)
    set_grm_purpose1.parm("primpattern").set(f"{root_name}/grm")
    set_grm_purpose1.parm("setpurpose").set(1)

    nodes_var_grm_list = nodes_var_grm(tasks, asset_name, set_grm_purpose1, detections)

    config_grm_layer1 = lopnet.createNode("configurelayer")
    config_grm_layer1.setName("config_grm_layer1")
    config_grm_layer1.setInput(0, nodes_var_grm_list["set_grm_extents"])
    config_grm_layer1.parm("setsavepath").set(1)
    config_grm_layer1.parm("savepath").set(f"{env_var_path}/Export/USD/layers/grm.{usd_file_format}")
    config_grm_layer1.parm("setdefaultprim").set(1)
    config_grm_layer1.parm("defaultprim").set(root_name)
    config_grm_layer1.parm("setmetersperunit").set(1)
    config_grm_layer1.parm("metersperunit").set(meters_per_unit)

    outputs = {"layer_grm_break1" : layer_grm_break1,
               "create_grm1" : create_grm1,
               "set_grm_purpose1" : set_grm_purpose1,
               "config_grm_layer1" : config_grm_layer1}
    outputs.update(nodes_var_grm_list)
    return outputs

def nodes_mtl(tasks: list[str], asset_name: str, input_nodes: dict[str,Any], detections: dict[str,dict[str,Any]], meters_per_unit: float) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # create material nodes                                             #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"

    is_grm = detections["grm"]
    is_grm = is_grm["GrmL"] or is_grm["GrmH"]

    lopnet=hou.node("/stage")

    layer_mtl_break1 = lopnet.createNode("layerbreak")
    layer_mtl_break1.setName("layer_mtl_break1")
    if is_grm:
        layer_mtl_break1.setInput(0, input_nodes["config_grm_layer1"])
    else:
        layer_mtl_break1.setInput(0, input_nodes["config_geo_layer1"])
    
    create_mtl1 = lopnet.createNode("primitive")
    create_mtl1.setName("create_mtl1")
    create_mtl1.setInput(0, layer_mtl_break1)
    create_mtl1.parm("primpath").set(f"{root_name}/mtl")
    create_mtl1.parm("parentprimtype").set("UsdGeomScope") #scope
    create_mtl1.parm("primtype").set("UsdGeomScope") #scope

    nodes_var_mtl_list = nodes_var_mtl(tasks, asset_name, create_mtl1, detections)

    config_mtl_layer1 = lopnet.createNode("configurelayer")
    config_mtl_layer1.setName("config_mtl_layer1")
    if detections["mtl"]["Shading"] and detections["mtl_groom"]["ShadingGroom"]:
        config_mtl_layer1.setInput(0, nodes_var_mtl_list["outputs"]["merge_mtl_mtl_groom1"])
    elif detections["mtl"]["Shading"]:
        if nodes_var_mtl_list["var_mtl_list"]["is_variant"]:
            config_mtl_layer1.setInput(0, nodes_var_mtl_list["outputs"]["add_mtl_var1"])
        else:
            config_mtl_layer1.setInput(0, nodes_var_mtl_list["outputs"]["ref_mtl1"])
    else:
        if nodes_var_mtl_list["var_mtl_groom_list"]["is_variant"]:
            config_mtl_layer1.setInput(0, nodes_var_mtl_list["outputs"]["add_mtl_groom_var1"])
        else:
            config_mtl_layer1.setInput(0, nodes_var_mtl_list["outputs"]["ref_mtl_groom1"])
    config_mtl_layer1.parm("setsavepath").set(1)
    config_mtl_layer1.parm("savepath").set(f"{env_var_path}/Export/USD/layers/mtl.{usd_file_format}")
    config_mtl_layer1.parm("setdefaultprim").set(1)
    config_mtl_layer1.parm("defaultprim").set(root_name)
    config_mtl_layer1.parm("setmetersperunit").set(1)
    config_mtl_layer1.parm("metersperunit").set(meters_per_unit)

    outputs = {"layer_mtl_break1" : layer_mtl_break1,
               "create_mtl1" : create_mtl1,
               "config_mtl_layer1" : config_mtl_layer1}
    outputs.update(nodes_var_mtl_list["outputs"])
    return outputs

def nodes_payload(asset_name: str, input_nodes: dict[str,Any], detections: dict[str,dict[str,Any]], meters_per_unit: float) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # create payload nodes                                              #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"

    lopnet=hou.node("/stage")

    create_root_prim1 = lopnet.createNode("primitive")
    create_root_prim1.setName("create_root_prim1")
    create_root_prim1.parm("primpath").set(root_name)
    create_root_prim1.parm("primkind").set("component") #component
    create_root_prim1.parm("parentprimtype").set("") #none
    create_root_prim1.parm("primtype").set("") #none

    ref_geo_grm_mtl1 = lopnet.createNode("reference")
    ref_geo_grm_mtl1.setName("ref_geo_grm_mtl1")
    try:
        ref_geo_grm_mtl1.setInput(0, create_root_prim1)
    except :
        try:
            ref_geo_grm_mtl1.setInput(0, input_nodes["config_grm_layer1"])
        except:
            ref_geo_grm_mtl1.setInput(0, input_nodes["config_geo_layer1"])
    ref_geo_grm_mtl1.parm("primpath").set(root_name)
    ref_geo_grm_mtl1.parm("createprims").set(0) # Edit Existing Primitives
    ref_geo_grm_mtl1.parm("num_files").set(0)
    if detections["geo"]["ModH"] or detections["geo"]["ModL"]:
        ref_geo_grm_mtl1.setInput(100, input_nodes["config_geo_layer1"])
    if detections["grm"]["GrmH"] or detections["grm"]["GrmL"]:
        ref_geo_grm_mtl1.setInput(100, input_nodes["config_grm_layer1"])
    if detections["mtl"]["Shading"]:
        ref_geo_grm_mtl1.setInput(100, input_nodes["config_mtl_layer1"])

    config_prims_type1 = lopnet.createNode("configureprimitive")
    config_prims_type1.setName("config_prims_type1")
    config_prims_type1.setInput(0, ref_geo_grm_mtl1)
    config_prims_type1.parm("primpattern").set(f"{root_name}/geo {root_name}/geo/* {root_name}/grm {root_name}/grm/* {root_name}/mtl")
    config_prims_type1.parm("settype").set(1)
    config_prims_type1.parm("type").set("UsdGeomScope") #scope

    config_prims_specifier1 = lopnet.createNode("configureprimitive")
    config_prims_specifier1.setName("config_prims_specifier1")
    config_prims_specifier1.setInput(0, config_prims_type1)
    config_prims_specifier1.parm("primpattern").set(f"{root_name}/geo {root_name}/geo/* {root_name}/grm {root_name}/grm/* {root_name}/mtl {root_name}/mtl/*")
    config_prims_specifier1.parm("setspecifier").set(1)
    config_prims_specifier1.parm("specifier").set("def") #define

    config_payload_layer1 = lopnet.createNode("configurelayer")
    config_payload_layer1.setName("config_payload_layer1")
    config_payload_layer1.setInput(0, config_prims_specifier1)
    config_payload_layer1.parm("setsavepath").set(1)
    config_payload_layer1.parm("savepath").set(f"{env_var_path}/Export/USD/layers/payload.{usd_file_format}")
    config_payload_layer1.parm("setdefaultprim").set(1)
    config_payload_layer1.parm("defaultprim").set(root_name)
    config_payload_layer1.parm("setmetersperunit").set(1)
    config_payload_layer1.parm("metersperunit").set(meters_per_unit)
    if packed:
        config_payload_layer1.parm("flattenop").set("stage")# flatten input stage

    ref_payload1 = lopnet.createNode("reference")
    ref_payload1.setName("ref_payload1")
    ref_payload1.setInput(0, create_root_prim1)
    ref_payload1.setInput(1, config_payload_layer1)
    ref_payload1.parm("primpath").set(root_name)
    ref_payload1.parm("reftype").set("payload") #payload inputs
    ref_payload1.parm("num_files").set(0)
    ref_payload1.parm("primkind").set("commponent") #component
    ref_payload1.parm("parentprimtype").set("") #none

    loft_payload_info1 = lopnet.createNode("loftpayloadinfo")
    loft_payload_info1.setName("loft_payload_info1")
    loft_payload_info1.setInput(0, ref_payload1)

    outputs = {"create_root_prim1" : create_root_prim1,
               "ref_geo_grm_mtl1" : ref_geo_grm_mtl1,
               "config_payload_layer1" : config_payload_layer1,
               "ref_payload1" : ref_payload1,
               "loft_payload_info1" : loft_payload_info1}
    return outputs

def nodes_class(asset_name: str, input_nodes: dict[str,Any]) -> dict[str,Any]:

    #-------------------------------------------------------------------#
    # create class nodes                                                #
    # return the list of all created nodes                              #
    #-------------------------------------------------------------------#


    root_name = f"/{asset_name}_asset"

    lopnet=hou.node("/stage")

    create_class1 = lopnet.createNode("primitive")
    create_class1.setName("create_class1")
    create_class1.setInput(0, input_nodes["loft_payload_info1"])
    create_class1.parm("primpath").set("""/__class__`chs("../create_root_prim1/primpath")`""")
    create_class1.parm("parentprimtype").set("") #none
    create_class1.parm("primtype").set("") #none

    inherit_class1 = lopnet.createNode("reference")
    inherit_class1.setName("inherit_class1")
    inherit_class1.setInput(0, create_class1)
    inherit_class1.parm("enable").set(0)
    inherit_class1.parm("primpath1").set(root_name)
    inherit_class1.parm("reftype1").set("inherit") # inherit from first input
    inherit_class1.parm("filerefprimpath1").set("""`chs("../create_class1/primpath")`""")

    outputs = {"create_class1" : create_class1,
               "inherit_class1" : inherit_class1}
    return outputs

def nodes_metadata_write(asset_name: str, input_nodes: dict[str,Any], detections: dict[str,dict[str,Any]], meters_per_unit: float) -> dict[str,Any]:

    #---------------------------------------------------------------------------#
    # create metadata and export nodes                                          #
    # return the list of all created nodes                                      #
    #---------------------------------------------------------------------------#


    lopnet=hou.node("/stage")

    asset_info_metadata1 = lopnet.createNode("configureprimitive")
    asset_info_metadata1.setName("asset_info_metadata1")
    asset_info_metadata1.setInput(0, input_nodes["inherit_class1"])
    asset_info_metadata1.parm("primpattern").set("""`chs("../create_component1/primpath")`""")
    asset_info_metadata1.parm("setassetidentifier").set(1)
    asset_info_metadata1.parm("assetidentifier").set(f"{env_var_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
    asset_info_metadata1.parm("setassetname").set(1)
    asset_info_metadata1.parm("assetname").set(asset_name)

    layer_metadata1 = lopnet.createNode("configurelayer")
    layer_metadata1.setName("layer_metadata1")
    layer_metadata1.setInput(0, asset_info_metadata1)
    layer_metadata1.parm("setdefaultprim").set(1)
    layer_metadata1.parm("defaultprim").set("""`chs("../create_component1/primpath")`""")
    layer_metadata1.parm("setupaxis").set(1)
    layer_metadata1.parm("upaxis").set("y")# Y axis
    layer_metadata1.parm("setmetersperunit").set(1)
    layer_metadata1.parm("metersperunit").set(meters_per_unit)

    set_default_variants1 = lopnet.createNode("setvariant")
    set_default_variants1.setName("set_default_variants1")
    set_default_variants1.setInput(0, layer_metadata1)
    set_default_variants1.parm("num_variants").set(4)
    if detections["geo"]["ModL"] or detections["geo"]["ModH"]:
        set_default_variants1.parm("variantset1").set("geo")
        set_default_variants1.parm("variantname1").set("geo_var01")
    if detections["grm"]["GrmL"] or detections["grm"]["GrmH"]:
        set_default_variants1.parm("variantset2").set("grm")
        set_default_variants1.parm("variantname2").set("grm_var01")
    if detections["mtl"]["Shading"]:
        set_default_variants1.parm("variantset3").set("mtl")
        set_default_variants1.parm("variantname3").set("mtl_var01")
    if detections["mtl_groom"]["ShadingGroom"]:
        set_default_variants1.parm("variantset4").set("mtl_groom")
        set_default_variants1.parm("variantname4").set("mtl_groom_var01")
    
    usd_rop1 = lopnet.createNode("usd_rop")
    usd_rop1.setName("usd_rop1")
    usd_rop1.setInput(0,set_default_variants1)
    usd_rop1.parm("lopoutput").set(f"{env_var_path}/Export/USD/master/{asset_name}_USD_master.{usd_file_format}")
    usd_rop1.parm("filtertimesamples").set("never")# never
    usd_rop1.parm("flattensoplayers").set(1)

    outputs = {"asset_info_metadata1" : asset_info_metadata1,
               "layer_metadata1" : layer_metadata1,
               "set_default_variants1" : set_default_variants1,
               "usd_rop1" : usd_rop1}
    return outputs


def nodes_create_asset(tasks: list[str], asset_name: str):

    #-------------------------------------------------------#
    # create the global asset creation tree                 #
    #-------------------------------------------------------#


    start_counter = perf_counter()

    # set framerange to 1 to avoid writing the set extents on multiple frames
    hou.playbar.setFrameRange(1,1)

    # detection and listing of the present departments

    is_mod_detect = mod_detect(tasks)

    is_grm_detect = grm_detect(tasks)
    is_grm = is_grm_detect["GrmL"] or is_grm_detect["GrmH"]

    is_mtl_detect = mtl_detect(tasks)
    is_mtl = is_mtl_detect["Shading"]

    is_mtl_groom_detect = mtl_groom_detect(tasks)
    is_mtl_groom = is_mtl_groom_detect["ShadingGroom"]

    detections = {}
    detections.update({is_mod_detect["departement"] : is_mod_detect})
    detections.update({is_grm_detect["departement"] : is_grm_detect})
    detections.update({is_mtl_detect["departement"] : is_mtl_detect})
    detections.update({is_mtl_groom_detect["departement"] : is_mtl_groom_detect})

    mod_to_detect = is_mod_detect["str_to_detect"]
    mod_stage = Usd.Stage.Open(f"{path}/Export/{mod_to_detect}/master/{asset_name}_{mod_to_detect}_master.{usd_file_format}")
    meters_per_unit = UsdGeom.GetStageMetersPerUnit(mod_stage)
    print(f"meters per unit : {meters_per_unit}")

    nodes_list = {} # liste de tt les nodes

    # call the functions to create nodes for each department and update the nodes_list with the created nodes

    nodes_geo_list = nodes_geo(tasks, asset_name, detections, meters_per_unit)
    nodes_list.update(nodes_geo_list)

    tasks = list(tasks_save)
    nodes_grm_list = nodes_geo_list
    if is_grm:
        nodes_grm_list = nodes_groom(tasks, asset_name, nodes_list, detections, meters_per_unit)
        nodes_list.update(nodes_grm_list)
    
    tasks = list(tasks_save)
    nodes_mtl_list = nodes_grm_list
    if is_mtl or is_mtl_groom:
        nodes_mtl_list = nodes_mtl(tasks, asset_name, nodes_list, detections, meters_per_unit)
        nodes_list.update(nodes_mtl_list)

    nodes_payload_list = nodes_payload(asset_name, nodes_list, detections, meters_per_unit)
    nodes_list.update(nodes_payload_list)

    nodes_class_list = nodes_class(asset_name, nodes_list)
    nodes_list.update(nodes_class_list)

    nodes_metadata_write_list = nodes_metadata_write(asset_name, nodes_list, detections, meters_per_unit)
    nodes_list.update(nodes_metadata_write_list)

    # export the master USD file
    print("\n\n\nVeuillez patienter ...")
    nodes_list["usd_rop1"].parm("execute").pressButton()
    print("Fin du processus")

    os.makedirs(f"{path}/Scenefiles/USD/usd", exist_ok=True)
    hou.hipFile.save(f"{path}/Scenefiles/USD/usd/{asset_name}_create_USD_master.hip")
    print(f"\n\nHoudini file saved in : {path}/Scenefiles/USD/usd/{asset_name}_create_USD_master.hip")

    elapsed_counter = perf_counter() - start_counter
    print(f"\n\nTotal time: {elapsed_counter:.2f} seconds")


# ---------------------------------------- appels ------------------------------------------------

nodes_create_asset(tasks, asset_name)
