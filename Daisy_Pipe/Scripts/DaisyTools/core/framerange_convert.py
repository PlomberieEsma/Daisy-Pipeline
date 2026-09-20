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
import json
from Scripts.DaisyTools.core.core import get_core

print("execute framerange_convert.py\n\n")

class Error(Exception):
    # use to raise errors in the script
    pass

##########################################################################################################################################
#=========================================================== SET VARIABLES ===============================================================
##########################################################################################################################################

core = get_core()
assert core is not None

project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")

##########################################################################################################################################
#============================================================ SET CLASSES ================================================================
##########################################################################################################################################

class FramerangeFile():
    def __init__(self):
        self.file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/framerange.json"
        with open(self.file_path, mode="r", encoding="utf-8") as read_file:
            try:
                self.file = json.load(read_file)
            except json.decoder.JSONDecodeError:
                # if file is empty
                self.file = {}

    def get_sequence(self, sq_name: str) -> dict[str,dict]:
        #---------------------------------------------------------------------------#
        # Get a sequence from the json file                                         #
        #                                                                           #
        # sq_name = name of the sequence (e.g.: sq032)                              #
        #                                                                           #
        # return the sequence name and the shots inside it (with each framerange)   #
        #---------------------------------------------------------------------------#

        if sq_name not in self.file:
            raise Error("This sequence doesn't exist in this json file")
        return {sq_name: self.file[sq_name]}

    def get_shot(self, sq_name: str, sh_name: str) -> dict[str,dict]:
        #-----------------------------------------------#
        # Get a shot from the json file                 #
        #                                               #
        # sq_name = name of the sequence (e.g.: sq032)  #
        # sh_name = name of the shot (e.g.: sh028)      #
        #                                               #
        # return the shot name with its framerange      #
        #-----------------------------------------------#

        if sq_name not in self.file:
            raise Error("This sequence doesn't exist in this json file")
        if sh_name not in self.file[sq_name]:
            raise Error("This shot doesn't exist in this json file")
        return {sh_name: self.file[sq_name][sh_name]}

    def get_master_range(self, sq_name: str, sh_name: str) -> list[int]:
        #---------------------------------------------------#
        # Get a shot master framerange from the json file   #
        #                                                   #
        # sq_name = name of the sequence (e.g.: sq032)      #
        # sh_name = name of the shot (e.g.: sh028)          #
        #                                                   #
        # return the shot master framerange                 #
        #---------------------------------------------------#

        if sq_name not in self.file:
            raise Error("This sequence doesn't exist in this json file")
        if sh_name not in self.file[sq_name]:
            raise Error("This shot doesn't exist in this json file")
        if "master_range" not in self.file[sq_name][sh_name]:
            raise Error("There is no master range in this json file")
        return self.file[sq_name][sh_name]["master_range"]

    def get_shot_range(self, sq_name: str, sh_name: str) -> list[int]:
        #---------------------------------------------------#
        # Get a shot shot framerange from the json file     #
        #                                                   #
        # sq_name = name of the sequence (e.g.: sq032)      #
        # sh_name = name of the shot (e.g.: sh028)          #
        #                                                   #
        # return the shot shot framerange                   #
        #---------------------------------------------------#

        if sq_name not in self.file:
            raise Error("This sequence doesn't exist in this json file")
        if sh_name not in self.file[sq_name]:
            raise Error("This shot doesn't exist in this json file")
        if "shot_range" not in self.file[sq_name][sh_name]:
            raise Error("There is no shot range in this json file")
        return self.file[sq_name][sh_name]["shot_range"]

    def write(self, dict_to_write: dict) -> dict:
        #---------------------------------------------------------------#
        # Write a dict in json file                                     #
        #                                                               #
        # dict_to_write = final dict which will replace the curent dict #
        #                                                               #
        # return dict_to_write                                          #
        #---------------------------------------------------------------#

        with open(self.file_path, mode="w", encoding="utf-8") as write_file:
            json.dump(dict_to_write, write_file, indent=4, sort_keys=True)
        return dict_to_write

    def add_sequence(self, sq_name: str) -> dict:
        #-----------------------------------------------------------------------------------#
        # Add a sequence in json file, if the sequence doesn't exist, create an empty one   #
        #                                                                                   #
        # sq_name = name of the sequence (e.g.: sq032)                                      #
        #                                                                                   #
        # return the new file content                                                       #
        #-----------------------------------------------------------------------------------#

        if sq_name in self.file:
            sequence_content = self.file[sq_name]
            self.file.update({sq_name: sequence_content})
        else:
            self.file.update({sq_name: {}})
        return self.file

    def add_shot(self, sq_name: str, sh_name: str, range: list[int]) -> dict:
        #---------------------------------------------------------------------------#
        # Add a shot in json file, if the sequence doesn't exist, create an new one #
        #                                                                           #
        # sq_name = name of the sequence (e.g.: sq032)                              #
        # sh_name = name of the shot (e.g.: sh028)                                  #
        # range = start and end frame of the shot in the layout                     #
        #                                                                           #
        # return the new file content                                               #
        #---------------------------------------------------------------------------#

        f_start = range[0]
        f_end = range[1]
        shot_duration = f_end - f_start
        shot_to_update = {
            sh_name: {
                "master_range": [range[0], range[1]],
                "shot_range": [1001, 1001+shot_duration]
            }}

        for sequence in self.file:
            if sequence != sq_name:
                continue
            self.file[sequence].update(shot_to_update)
        return self.file

    def set_shot(self, sq_name: str, sh_name: str, range: list[int]) -> dict:  
        #-------------------------------------------------------#
        # Set new sequence and shot in json file                #
        #                                                       #
        # sq_name = name of the sequence (e.g.: sq032)          #
        # sh_name = name of the shot (e.g.: sh028)              #
        # range = start and end frame of the shot in the layout #
        #                                                       #
        # return the new file content                           #
        #-------------------------------------------------------#

        self.add_sequence(sq_name)
        self.add_shot(sq_name, sh_name, range)

        self.write(self.file)
        return self.file
