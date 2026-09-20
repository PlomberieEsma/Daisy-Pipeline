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
from typing import Any
import qtpy.QtWidgets as qt # type: ignore
import qtpy.QtCore as qc # type: ignore
import qtpy.QtGui as qg # type: ignore
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.framerange_convert import FramerangeFile

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
assert core is not None

project_path = core.sequencePath.replace("\\", "/")
project_path = project_path.removesuffix("/03_Production/Shots")

#get variables from config.json
config_file_path = f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Scripts/DaisyTools/lib/config.json"
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

digit_number = config_file["global"]["sh_name_digit_number"] # number of digits in the seq and sht names

##########################################################################################################################################
#============================================================ SET CLASSES ================================================================
##########################################################################################################################################

class PaddedSpinBox(qt.QSpinBox):
    #-----------------------------------------------------------------------------------#
    # Create a custom Qt SpinBox to keep the potential leading 0 before the shot number #
    #                                                                                   #
    # return the object                                                                 #
    #-----------------------------------------------------------------------------------#
    def __init__(self, parent=None, digits=3):
        super().__init__(parent)
        self._digits = digits

    def textFromValue(self, value: int) -> str:
        # Format integer with leading zeros (e.g., 001, 042)
        return f"{value:0{self._digits}d}"

##########################################################################################################################################
#=========================================================== SET FUNCTIONS ===============================================================
##########################################################################################################################################

def rename_shot(kwargs: dict[str,str]):
    #-------------------------------------------------------------------------------------------#
    # Launch the window creation to rename the selected shot and place it next to the cursor    #
    #                                                                                           #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"                             #
    #-------------------------------------------------------------------------------------------#

    current_shot_name = kwargs["node"].parm("sh_name"+kwargs["script_multiparm_index"]).eval()

    window = renaming_window(
        kwargs,
        current_shot_name = current_shot_name
        )

    # move to mouse cursor
    cursor_position = qg.QCursor.pos()
    window.move(
        cursor_position.x()-(window.width()*0.75),
        cursor_position.y()+30
        )

    # show window
    window.show()

def renaming_window(kwargs: dict[str,str], current_shot_name: str) -> Any:
    #-----------------------------------------------------------------------#
    # Create the GUI window to help the user to set the new shot name       #
    #                                                                       #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"         #
    # current_shot_name = current shot name comming from the HDA shot name  #
    #                                                                       #
    # return the window                                                     #
    #-----------------------------------------------------------------------#

    current_shot_number = int(current_shot_name[-digit_number:])

    #-------------------------------- create window ---------------------------------#
    # get existing QApplication instance to prevent crashes
    app = qt.QApplication.instance()
    if app is None:
        qt.QApplication([])

    # create the widget window
    window = qt.QWidget()
    window.setWindowTitle("shot rename")
    window.resize(200, 100)

    # change window icon
    core = get_core()
    project_path = core.sequencePath.replace("\\", "/")
    project_path = project_path.removesuffix("/03_Production/Shots")
    window.setWindowIcon(qg.QIcon(f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Integration/ui/daisy_logo.png"))

    # parent the houdini's main Qt window to ensure the window stays open and managed by houdini
    main_window = hou.ui.mainQtWindow()
    window.setParent(main_window, qc.Qt.Window)

    #-------------------------------- create elements ---------------------------------#
    layout = qt.QGridLayout(window)

    # label
    label = qt.QLabel()
    label.setText(current_shot_name[:-digit_number])
    label.setStyleSheet("""
    font-size: 20px;
    """)
    label.setAlignment(qc.Qt.AlignRight | qc.Qt.AlignVCenter)
    layout.addWidget(label, 0, 0)

    # spin box
    spin_box = PaddedSpinBox(digits = digit_number)
    spin_box.setStyleSheet("""
    font-size: 20px;
    """)
    spin_box.setMinimum(1)
    spin_box.setMaximum((10**digit_number)-1)
    spin_box.setValue(current_shot_number)
    layout.addWidget(spin_box, 0, 1)

    # button
    button = qt.QPushButton("Apply")
    button.setStyleSheet("""
    font-size: 20px;
    """)
    button.clicked.connect(lambda : button_action(
        kwargs,
        spin_box.value(),
        renaming_window = window
    ))
    layout.addWidget(button, 1, 0, 1, 2)

    return window

def button_action(kwargs: dict[str,str], new_shot_name: str, renaming_window: Any = None):
    #-----------------------------------------------------------------------------------#
    # Set and applies the new values for the shot name                                  #
    # (the HDA shot name, the camera primpath, the HDA camera path and the camera name) #
    #                                                                                   #
    # kwargs = dict taken from the HDA multiParmBlock "shot_number"                     #
    # new_shot_name = number set in the window                                          #
    #-----------------------------------------------------------------------------------#

    if kwargs["parm_name"][:11] == "rename_shot":
        new_shot_name = f"{new_shot_name:0{digit_number}d}"

    if renaming_window != None:
        renaming_window.close()

    #-------------------------------- set new values ---------------------------------#
    node = kwargs["node"]
    new_shot_HDA_number = kwargs["script_multiparm_index"]
    camera_path = node.parm(f"cam_selection_{new_shot_HDA_number}")
    camera_path_content = camera_path.eval()

    # get camera name
    splited_camera_path = camera_path_content.split("/")
    camera_name = splited_camera_path[-1]

    sq_and_sh_name = camera_name.replace("cam_", "").replace("_", " ")

    splited_name = camera_name.split("_")
    sq_name = splited_name[1]
    sh_name = splited_name[2]
    new_sh_name = new_shot_name

    if kwargs["parm_name"][:11] == "rename_shot":
        new_sq_and_sh_name = sq_and_sh_name[:-digit_number] + new_sh_name
        new_camera_name = "cam_" + new_sq_and_sh_name.replace(" ", "_")
    else:
        new_sq_and_sh_name = sq_and_sh_name[:-digit_number-2] + new_sh_name
        new_camera_name = "cam_" + new_sq_and_sh_name.replace(" ", "_")

    new_camera_path = camera_path_content.replace(camera_name, new_camera_name)

    #-------------------------------- apply new values ---------------------------------#
    # apply to shot name in the HDA
    node.parm(f"sh_name{new_shot_HDA_number}").set(new_sq_and_sh_name)
    node.parm(f"sh_name_FLO_{new_shot_HDA_number}").set(new_sq_and_sh_name)
    node.parm(f"sh_name_TLO_{new_shot_HDA_number}").set(new_sq_and_sh_name)

    # get all well named cameras in the scene
    cameras_in_scene = hou.lopNodeTypeCategory().nodeTypes()["camera"].instances()
    if cameras_in_scene != ():
        cameras_in_scene = list(cameras_in_scene)
        loop_count = 0
        for camera in cameras_in_scene:
            if camera.parm("primpath").eval() == camera_path_content:

                # apply to camera name
                camera.setName(new_camera_name)

            loop_count += 1

    # apply to camera selection in the HDA and camera primpath
    camera_path.set(new_camera_path)

    # change shot name in Prism
    new_sh_name = new_sq_and_sh_name[-digit_number-2:]
    try:
        selected_shot = core.entities.getShot(sq_name, sh_name)
        new_selected_shot = dict(selected_shot)
        if selected_shot["shot"] != new_sh_name:
            new_selected_shot.update({"shot": new_sh_name})
            core.entities.renameShot(selected_shot, new_selected_shot)
    except Exception as e:
        # if the shot doesn't exist in Prism
        print("Unable to rename this shot in the pipeline because it deosn't exist in Prism")
    else:
        # change shot name in json framerange file
        framerange_file = FramerangeFile()
        old_master_framerange = framerange_file.get_master_range(sq_name, sh_name)
        framerange_file.set_shot(sq_name, new_sh_name, old_master_framerange)
    finally:
        print(f"rename shot : \n{sq_and_sh_name} to\n{new_sq_and_sh_name}")
