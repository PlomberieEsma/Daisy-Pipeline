import os
import sys
import platform
import shutil
import logging
logger = logging.getLogger(__name__)

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_SubstancePainter_Integration(object):
    """SubstancePainter integration management.
    
    Handles installation and removal of Prism integration files in
    SubstancePainter preferences folders, including package files and initialization
    scripts.
    
    Attributes:
        core: PrismCore instance.
        plugin: SubstancePainter plugin instance.
        examplePath: Example installation path for reference.
    """

    def __init__(self, core, plugin):
        """Initialize SubstancePainter integration manager.
        
        Sets example paths based on available SubstancePainter installations.
        
        Args:
            core: PrismCore instance.
            plugin: SubstancePainter plugin instance.
        """
        self.core = core
        self.plugin = plugin



        if platform.system() == "Windows":
            # Dossier "Integration" livre avec le plugin, qui contient
            # les fichiers a copier chez l'utilisateur (PrismInit.py, icones...)
            self.examplePath = os.path.join(
                self.plugin.pluginDirectory, "Integration"
            )
        else:
            return
        
    ######################################################################
    # Chemin pour trouver le dossier d'installation de SubstancePainter
    ######################################################################
    @err_catcher(name=__name__)
    def getExecutable(self):
        # get executable path to the SubstancePainter executable file
        execPath = ""
        if platform.system() == "Windows":
            programFiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")
            defaultpath = os.path.join(
                programFiles, "Adobe", "Adobe Substance 3D Painter",
                "Adobe Substance 3D Painter.exe"
            )
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getSubstancePainterPath(self):
        # Path to the SubstancePainter Plugin folder
        userProfile = os.environ.get("USERPROFILE", "")
        installPath = os.path.join(
                userProfile,
                "Documents",
                "Adobe",
                "Adobe Substance 3D Painter",
            )
        return installPath

    ######################################################################
    # Installation
    ######################################################################
    def addIntegration(self, installPath):
        """Install Prism integration into SubstancePainter.
        
        Copies integration files and creates package configuration.
        
        Args:
            installPath: Path to SubstancePainter installation folder.
        
        Returns:
            True if installation succeeded, False otherwise.
        """
        try:
            # confirmed = False
            #     # Check if InstallPath exists, if not, ask user to confirm installation
            #     if not os.path.exists(installPath):
            #         msg = "SubstancePainter path doesn't exist:\n\n%s\n\nThe path has to be the SubstancePainter installation folder, which usually looks like this: (with your SubstancePainter version):\n\n%s" % (installPath, self.examplePath)
            #         result = self.core.popupQuestion(msg, buttons=["Continue", "Cancel"], icon=QMessageBox.Warning, default="Continue")
            #         if result != "Continue":
            #             return False
    
            #         confirmed = True


            pluginsFolder = os.path.join(installPath, "python", "plugins")
            if not os.path.exists(pluginsFolder):
                os.makedirs(pluginsFolder)

            initpath = os.path.join(pluginsFolder, "PrismInit.py")

            if os.path.exists(initpath):
                os.remove(initpath)

            if os.path.exists(initpath + "c"):
                os.remove(initpath + "c")

            integrationBase = os.path.realpath(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
            )
            origInitFile = os.path.join(integrationBase, "PrismInit.py")
            shutil.copy2(origInitFile, initpath)

            with open(initpath, "r") as init:
                initStr = init.read()

            initStr = initStr.replace(
                "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
            )

            with open(initpath, "w") as init:
                init.write(initStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the SubstancePainter integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        """Remove Prism integration from SubstancePainter.
        
        Removes integration files and cleans up modified scripts.
        
        Args:
            installPath: Path to SubstancePainter installation folder.
        
        Returns:
            True if removal succeeded, False otherwise.
        """
        try:
            initPy = os.path.join(installPath, "python", "plugins", "scripts", "PrismInit.py")
            initPyc = initPy + "c"

            for i in [initPy, initPyc]:
                if os.path.exists(i):
                    os.remove(i)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the SubstancePainter integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    # ------------------------------------------------------------------ #
    # Verification que le chemin choisi par l'utilisateur est valide
    # ------------------------------------------------------------------ #
    def integrationAdded(self, installPath):
        targetFile = os.path.join(
            installPath, "python", "plugins", "scripts", "PrismInit.py"
        )
        return os.path.exists(targetFile)
