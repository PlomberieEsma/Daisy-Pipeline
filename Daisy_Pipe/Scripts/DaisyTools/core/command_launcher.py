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

# import modules
import subprocess
import json
from typing import Any


class Command_launcher(object):
    def __init__(self, core: Any, plugin: Any = None) -> None:
        self.core = core
        self.plugin = plugin
        self.project_path = self.core.projectPath
        self.project_path = self.project_path.replace("\\", "/")

        # importe config.json
        with open(f'{self.project_path}00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json', 'r') as file:
            self.jsonPath = json.load(file)
        
    ######################################################################################################################################
    ########################################################### SET METHODS ##############################################################
    ######################################################################################################################################

    def create_asset(self, asset_name: str, current_entity: Any, packed: bool = False) -> None:

        #---------------------------------------------------------------------------------------------------#
        # launch the create_asset.py script with hython in powershell                                       #
        #                                                                                                   #
        # asset name : name of the asset to be processed, it is passed in the command line to hython        #
        # path : path of the asset to be processed, it is passed in the command line to hython              #
        # project path : path of the project, it is passed in the command line to hython                    #
        #---------------------------------------------------------------------------------------------------#

        hython_path = self.jsonPath["software"]["hython"]

        # path to the create_asset.py script to be launched with hython
        python_file_path = f"{self.project_path}00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/core/create_asset.py"

        asset_name = str(asset_name)
        to_hython_path = "cd \'" + hython_path.replace("/hython.exe", "") + "\'"

        asset_path = current_entity["asset_path"]
        asset_path = asset_path.replace("\\", "/")

        path_to_asset = self.core.paths.getEntityPath(entity=current_entity)

        # create command line to launch hython with the create_asset.py script and pass the asset name and info as arguments
        command_line = f"powershell.exe \"{to_hython_path}\" ; ./hython.exe \"{python_file_path}\" --assetName \'{asset_name}\' --path '{path_to_asset}' --assetPath '{asset_path}' --projectPath '{self.project_path}' --packed '{packed}'"

        # launch command line in powershell
        subprocess.Popen(command_line)

    def convert_usd_format(self, path: Any, usd_in: str = "usdc", usd_out: str = "usda") -> None:
        #---------------------------------------------------------------------------------------------------#
        # launch usdcat in powershell to convert USD format                                                 #
        #                                                                                                   #       
        # path : the path for which to convert USD format                                                   #
        # usd_in : the input USD format                                                                     #
        # usd_out : the output USD format                                                                   #
        #---------------------------------------------------------------------------------------------------#

        usdcat_path = self.jsonPath["software"]["usdcat"]
        usdcat_path_to_del = usdcat_path.split("/")[-1]
        usdcat_path = usdcat_path.replace(f"/{usdcat_path_to_del}", "")

        input_path = path
        output_path = path.replace(usd_in, usd_out)
        to_usdcat_path = f"cd \'{usdcat_path}\'"

        # create command line to convert USD format using usdcat
        if usd_out == "usd":
            command_line = f"powershell.exe \"{to_usdcat_path}\" ; ./usdcat --out \"{output_path}\" --usdFormat \"{usd_out}\" \"{input_path}.{usd_out}\""
        else:
            command_line = f"powershell.exe \"{to_usdcat_path}\" ; ./usdcat --out \"{output_path}\" \"{input_path}\""

        # launch command line in powershell
        subprocess.Popen(command_line)

