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
import json, re, os
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
shot_entity = info["entity"]
project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")
department = info["department"]
task = info["task"]

sequence_name = shot_entity["sequence"]
shot_name = shot_entity["shot"]

#get variables from pipeline.json
config_file_path = f"{project_path}/00_Pipeline/pipeline.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    pipeline_file = json.load(read_file)

version_padding = pipeline_file["globals"]["versionPadding"] # number of digits to compose a version

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def create_render_folders(kwargs: dict[str, Any], identifier_name: str) -> None:
    #-----------------------------------------------------------------------#
    # Create the folders for render files                                   #
    #                                                                       #
    # identifier_name = name of the identifier in Prism for this render     #
    #-----------------------------------------------------------------------#

    node = kwargs["node"]
    multiparm_index = int(kwargs["script_multiparm_index"])
    version = node.parm(f"version{multiparm_index}").eval()
    version = f"v{version:0{version_padding}d}"

    # create the folders to put the exr files
    updated_entity = shot_entity
    updated_entity.update({"department": "Render", "task": task})
    render_folder = core.mediaProducts.createIdentifier(entity=updated_entity, identifier=identifier_name)

    # create the version folder if it doesn't exist and the aov one
    if render_folder != None and len(os.listdir(render_folder)) == 0:
        core.mediaProducts.createVersion(entity=updated_entity, identifier=identifier_name, version=version)
        core.mediaProducts.createAov(entity=updated_entity, identifier=identifier_name, version=version, aov="rgb")

    # put idnetifiers in a group named "Render"
    identifiers = core.mediaProducts.getIdentifiersByType(entity=shot_entity)
    identifiers_3d = identifiers["3d"]

    render_idents = []
    for ident in identifiers_3d:
        if ident["department"] == "Render":
            render_idents.append(ident)
    core.mediaProducts.setIdentifiersGroup(identifiers=render_idents, group="Render")

def render_single_layer(kwargs: dict[str, Any]) -> None:
    #-----------------------------------------------------------------------#
    # Launch a render with Deadline for a single layer                      #
    #                                                                       #
    # kwargs = dict taken from the callbgack of the HDA                     #
    #-----------------------------------------------------------------------#

    node = kwargs["node"]
    multiparm_index = int(kwargs["script_multiparm_index"])
    layer_name = node.parm(f"deadline_layer_name{multiparm_index}").eval()

    create_render_folders(kwargs, layer_name)