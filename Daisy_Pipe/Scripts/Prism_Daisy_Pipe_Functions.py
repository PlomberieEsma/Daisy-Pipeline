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
#   by Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio
#   art by Joan G. Stark (Spunk)

name = "CustomExportSettings"
classname = "CustomExportSettings"
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from functools import partial

import os, sys

from DaisyTools.core.command_launcher import Command_launcher
from DaisyTools.core.asset_browser import AssetBrowserUI
from DaisyTools.ui.maya_state_manager import EsmaUsdExportClass

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Daisy_Pipe_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if self.isMaya():
            self.mayastate = EsmaUsdExportClass()

        if self.isStandalone():
            self.importUsdPackages()

        self.Command_launcher = Command_launcher(core, plugin)
        self.AssetBrowserUI = AssetBrowserUI(core, plugin)
        self.core.registerCallback("onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self)
        self.core.registerCallback("openPBAssetContextMenu", self.openPBAssetContextMenu, plugin=self)
        self.core.registerCallback("openPBAssetTaskContextMenu", self.openPBAssetTaskContextMenu, plugin=self)
        self.core.registerCallback("productSelectorContextMenuRequested", self.productSelectorContextMenu, plugin=self)

        if self.isMaya():
            self.core.registerCallback("onStateManagerOpen", self.onStateManagerOpen, plugin=self)

        if self.isMaya() or self.isHoudini():
            self.core.registerCallback("sceneSaved", self.onSceneSaved, plugin=self)

    @err_catcher(name=__name__)
    def onSceneSaved(self, *args, **kwargs):

        #-----------------------------------------------------------------------------------#
        # A work scene was just saved: once the task piles up too many versions,            #
        # offer to clean them up - same deal as the product check after an export           #
        #-----------------------------------------------------------------------------------#

        from DaisyTools.ui.version_cleanup import checkSceneVersionLimit

        checkSceneVersionLimit(self.core)


    def onStateManagerOpen(self, origin):
        import importlib
        from DaisyTools.ui import maya_state_manager
        importlib.reload(maya_state_manager)
        origin.loadState(maya_state_manager.EsmaUsdExportClass)

        menu = QMenu(origin.b_createExport)
        menu.addAction("Export", lambda: origin.createState("Export", setActive=True))
        menu.addAction("EsmaUsdExport", lambda: origin.createState("EsmaUsdExport", setActive=True))
        origin.b_createExport.setMenu(menu)


    def onProjectBrowserStartup(self, origin):
        
        #-----------------------------------------------------------------------------------#
        # Create a general menu 'DaisyMenu'
        #-----------------------------------------------------------------------------------#

        origin.daisyMenu = QMenu("DaisyMenu")
        origin.menubar.addMenu(origin.daisyMenu)


    ##############################################################################################################
    ###########################     ASSET Contextual Menu - CreateUsdAsset and PackUsdAsset      #################
    ##############################################################################################################

    def openPBAssetContextMenu(self, origin, rcMenu, asset):
        
        #-----------------------------------------------------------------------------------#
        # Add USD options to the context menu for assets (CreateUsdAsset and PackUsdAsset)
        # When clicked, launch the functions with the asset as argument
        #-----------------------------------------------------------------------------------#
        
        # Get the item
        item = asset.data(Qt.UserRole)
        if item is None:
            return
        
        if item["type"] != "asset":
            return
        
        # Create an action named "Create USD Asset" and add it to the context menu
        createUsdAssetAction = QAction(QIcon(self.daisyIcon("CreateUSD.png")), "Create USD Asset", origin)
        createUsdAssetAction.triggered.connect(lambda: self.onCreateUsdAsset(item))
        rcMenu.addAction(createUsdAssetAction)

        # Create an action named "Pack USD Asset" and add it to the context menu
        packUsdAssetAction = QAction(QIcon(self.daisyIcon("PackUSD.png")), "Pack USD Asset", origin)
        packUsdAssetAction.triggered.connect(lambda: self.onPackUsdAsset(item))
        rcMenu.addAction(packUsdAssetAction)

    def onCreateUsdAsset(self, item):
        
        #-----------------------------------------------------------------------------------#
        # Get the selected asset from the Create USD Asset option
        # Launch the create asset function
        #-----------------------------------------------------------------------------------#

        self.Command_launcher.create_asset(item["asset"], item)

    def onPackUsdAsset(self, item):
        
        #-----------------------------------------------------------------------------------#
        # Get the selected asset from the Pack USD Asset option
        # Launch the pack asset function with the "packed=True" attribute
        #-----------------------------------------------------------------------------------#

        self.Command_launcher.create_asset(item["asset"], item, packed=True)


    ##############################################################################################################
    ###########################     ASSET TASK Contextual Menu - Variant     #####################################
    ##############################################################################################################

    def openPBAssetTaskContextMenu(self, origin, rcMenu, widget):
        
        #-----------------------------------------------------------------------------------#
        # Create a submenu "Add Variants" to the context menu for assets' task
        # Add as options every current existing task
        # When clicked, launch the function onCreateVariant with the task as argument
        #
        # Return - Launch the onCreateVariant function
        #-----------------------------------------------------------------------------------#
        
        # Check where the cursor is to launch at the right spot
        entity = origin.getCurrentEntity()
        widgetType = "department" if widget == origin.lw_departments else "task"

        if entity or entity["type"] in ["asset"] and widgetType == "task":
            # Check the department
            deptItem = origin.lw_departments.currentItem()
            if not deptItem:
                return
            department = deptItem.data(Qt.UserRole)

            # Check existing tasks and their names
            existingTasks = self.core.entities.getCategories(entity, step=department)
            existingBaseTasks = [t for t in existingTasks if not any(c.isdigit() for c in t)]
            # CHECK - self.core.popup("Tasks trouvées: %s" % existingBaseTasks)

            # Create the contextual menu and actions
            addVarMenu = QMenu("Add Variants", origin)
            addVarMenu.setIcon(QIcon(self.daisyIcon("AddVariant.png")))

            if not existingBaseTasks:
                emptyAction = QAction("No existing tasks", addVarMenu)
                emptyAction.setEnabled(False)
                addVarMenu.addAction(emptyAction)
            else:
                for taskName in existingBaseTasks:
                    taskAction = QAction("Add Variant : %s" % taskName, addVarMenu)
                    taskAction.triggered.connect(partial(self.onCreateVariant, origin, entity, department, taskName, existingTasks))
                    addVarMenu.addAction(taskAction)

            rcMenu.addMenu(addVarMenu)

    def onCreateVariant(self, origin, entity, department, taskName, existingTasks):
        
        #-----------------------------------------------------------------------------------#
        # Get the chosen task from the Create Variant option
        #-----------------------------------------------------------------------------------#
        
        # Check existing tasks and determine the right name
        if f"{taskName}_var02" not in existingTasks:
            varTaskName = f"{taskName}_var02"
        else:
            varTaskName = None
            for i in range(3, 99):
                candidate = f"{taskName}_var{i:02d}"
                if candidate not in existingTasks:
                    varTaskName = candidate
                    break

            if varTaskName is None:
                self.core.popup("Impossible de trouver un nom de variante disponible pour %s" % taskName)
                return
        
        path = self.core.entities.createCategory(entity, department, varTaskName)
        if not path:
            return
        origin.refreshTasks()
        return path


    ##############################################################################################################
    ###########################     PRODUCT VERSION Contextual Menu - USD Convert     ############################
    ##############################################################################################################

    def productSelectorContextMenu(self, origin, widget, pos, rcMenu):
        
        #-----------------------------------------------------------------------------------#
        # Create option to Duplicate and Convert Usd versions in the verisons RC Contextual Menu in Products
        #
        # Return - launch onConvertUsd function
        #-----------------------------------------------------------------------------------#

        # On ne veut agir que sur la liste des versions, pas sur la liste des produits
        if widget != origin.tw_versions:
            return

        row = widget.rowAt(pos.y())
        if row == -1:
            return

        # Récupère l'objet "version" complet (colonne 0, data stockée en UserRole)
        version = widget.model().index(row, 0).data(Qt.UserRole)
        if not version:
            return

        version = origin.getCurrentVersion()
        path = version["path"]
        listDir = os.listdir(path)

        for link in listDir:
            ext=link.split(".")[-1]
            if ext == "usda":
                usd_in = "usda"
                usd_out = "usdc"
                filename = link
                iconName = "ConvertAtoC"
                break
            elif ext == "usdc":
                usd_in = "usdc"
                usd_out = "usda"
                filename = link
                iconName = "ConvertCtoA"
                break
            elif ext == "usd":
                usd_in = "usd"
                usd_out = "usda"
                filename = link
                iconName = "ConvertCtoA"
                break
            else:
                return

        path = f"{path}\\{filename}"
        convertUsdAction = QAction(QIcon(self.daisyIcon(iconName)),f"Duplicate and Convert to {usd_out}", origin)
        convertUsdAction.triggered.connect(lambda: self.onConvertUsd(path, usd_in, usd_out))
        rcMenu.addAction(convertUsdAction)

    def onConvertUsd(self, path, usd_in, usd_out):
        
        #-----------------------------------------------------------------------------------#
        # Get the selected product version from the Create USD option
        # Launch the duplicate and convert USD script
        #
        #   path: path to the usd version folder
        #   usd_in: format of the original file
        #   usd_out: format of the converted file
        #-----------------------------------------------------------------------------------#

        self.Command_launcher.convert_usd_format(path, usd_in, usd_out)
        origin.core.refreshUI()







    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    
    def daisyIcon(self,iconName):
        iconPath = os.path.join(self.pluginDirectory, "Integration", "ui", iconName)
        return iconPath








    def importUsdPackages(self):

        try:
            extModPath = os.path.join(self.pluginDirectory, "ExternalModules")
            extModPath = extModPath.replace("\\", "/")

            os.environ["PATH"] += os.pathsep + extModPath + "/USD/bin"
            os.environ["PATH"] += os.pathsep + extModPath + "/USD/lib"
            os.environ["PYTHONPATH"] = extModPath + "/USD/lib/python"
            os.environ["PYTHONPATH"] += extModPath + "/USD/bin"

            sys.path.append(extModPath)
            sys.path.insert(0, extModPath + "/USD/lib/python")
            sys.path.insert(0, extModPath + "/USD/lib/python/pxr")


        except Exception as e:
            self.console.showMessageBoxError("USD packages could not be imported", str(e))

        try:
            from pxr import Usd, UsdGeom, Sdf, Gf, Kind, UsdShade, UsdSkel, Vt, Tf, Ar
            print("Successfully imported USD packages")
        except Exception as e:
            print("USD packages could not be imported", str(e))
            return

    def isMaya(self):

        return self.core.appPlugin.pluginName == "Maya"
    
    def isStandalone(self):

        return self.core.appPlugin.pluginName == "Standalone"

    def isHoudini(self):

        return self.core.appPlugin.pluginName == "Houdni"
