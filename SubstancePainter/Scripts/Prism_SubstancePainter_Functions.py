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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from functools import partial
import json
import subprocess
import os, sys

from PrismUtils.Decorators import err_catcher
from PrismUtils import PrismWidgets


import substance_painter.project as sp_project

from Prism_SubstancePainter_externalAccess_Functions import MeshPathsDialog


class Prism_SubstancePainter_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.state = {
                        "states": [
                            {
                                "statename": "publish",
                                "comment": "dummy publish state",
                                "description": ""
                            }
                        ]
                    }
        self.state = json.dumps(self.state)  # convert dict to JSON string


    @err_catcher(name=__name__)
    def startup(self, origin):

        origin.timer.stop()

        origin.messageParent = QWidget()
        # 	origin.messageParent.setParent(QtParent, Qt.Window)
        if self.core.useOnTop:
            origin.messageParent.setWindowFlags(
                origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
            )

        origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        # get autosave enabled
        return False

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        if not sp_project.is_open():
            return ""
        return sp_project.file_path() or ""

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        try:
            sp_project.save_as(filepath)
            return True
        except Exception as e:
            self.core.popup("Impossible de sauvegarder la scene:\n%s" % e)
            return False

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return []

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return "1.0"

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if sp_project.is_open():
            if sp_project.needs_saving() and not force:
                # Prism gere normalement la confirmation de sauvegarde en amont,
                # mais on securise ici si la fonction est appelee directement.
                pass
            sp_project.close()

        try:
            sp_project.open(filepath)
            return True
        except Exception as e:
            self.core.popup("Impossible d'ouvrir la scene:\n%s" % e)
            return False

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin, objects=None):
        if not objects:
            objects = []  # get selected objects from scene

        for i in objects:
            if not i in origin.nodes:
                origin.nodes.append(i)

        origin.updateUi()
        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getNodeName(self, origin, node):
        if self.isNodeValid(origin, node):
            try:
                return node.name
            except:
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Cannot get name from %s" % node
                )
                return node
        else:
            return "invalid"

    @err_catcher(name=__name__)
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            nodes = []
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.isNodeValid(origin, node):
                    nodes.append(node)
            # select(nodes)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, handle):
        return True

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        sceneCams = []  # get cams from scene
        if cur:
            sceneCams = ["Current View"] + sceneCams

        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        if handle == "Current View":
            return handle

        return str(nodes[0])

    @err_catcher(name=__name__)
    def selectCam(self, origin):
        if self.isNodeValid(origin, origin.curCam):
            select(origin.curCam)

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        pass

    # 	@err_catcher(name=__name__)
    # 	def sm_export_setTaskText(self, origin, prevTaskName, newTaskName):
    # 		origin.l_taskName.setText(newTaskName)

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        pass

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin,
        startFrame,
        endFrame,
        outputName,
        scaledExport=False,
        nodes=None,
        expType=None,
    ):
        pass

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_unColorObjList(self, origin):
        origin.lw_objects.setStyleSheet(
            "QListWidget { border: 3px solid rgb(50,50,50); }"
        )

    @err_catcher(name=__name__)
    def sm_export_typeChanged(self, origin, idx):
        pass

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_export_loadData(self, origin, data):
        pass

    @err_catcher(name=__name__)
    def sm_export_getStateProps(self, origin, stateProps):
        stateProps.update()

        return stateProps

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_render_getRenderLayer(self, origin):
        rlayerNames = []

        return rlayerNames

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin, item=None):
        pass

    @err_catcher(name=__name__)
    def removeAOV(self, aovName):
        pass

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        pass

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        pass

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin, rSettings):
        pass

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        pass

    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin):
        return "Renderer"

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        curFileName = self.core.getCurrentFileName()
        scenefiles = [curFileName]
        return scenefiles

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin):
        return []

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin, passName, steps):
        pass

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def getProgramVersion(self, origin):
        return "1.0"

    @err_catcher(name=__name__)
    def sm_render_getDeadlineSubmissionParams(self, origin, dlParams, jobOutputFile):
        dlParams["Build"] = dlParams["build"]
        dlParams["OutputFilePath"] = os.path.split(jobOutputFile)[0]
        dlParams["OutputFilePrefix"] = os.path.splitext(
            os.path.basename(jobOutputFile)
        )[0]
        dlParams["Renderer"] = self.getCurrentRenderer(origin)

        if origin.chb_resOverride.isChecked() and "resolution" in dlParams:
            resString = "Image"
            dlParams[resString + "Width"] = str(origin.sp_resWidth.value())
            dlParams[resString + "Height"] = str(origin.sp_resHeight.value())

        return dlParams

    @err_catcher(name=__name__)
    def deleteNodes(self, origin, handles, num=0):
        pass

    @err_catcher(name=__name__)
    def sm_import_disableObjectTracking(self, origin):
        self.deleteNodes(origin, [origin.setName])

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        pass

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        pass

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        return self.state

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        extFiles = []
        return [extFiles, []]

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin):
        origin.createPressed("Render")

    @err_catcher(name=__name__)
    def SaveComment(self, origin=None):
        oldFilePath = self.getCurrentFileName(origin)
        if oldFilePath == "":
            self.core.popup(
                "Merci d'utiliser le Project Browser pour créer un nouveau "
                "fichier avant d'utiliser 'Save Comment'."
            )
            return False

        # empeche d'ouvrir plusieurs fois la meme fenetre
        if hasattr(self.core, "savec") and self.core.savec is not None:
            self.core.savec.show()
            self.core.savec.raise_()
            self.core.savec.activateWindow()
            return False

        if not self.core.projects.ensureProject():
            return False

        if not self.core.users.ensureUser():
            return False

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning()
            return False

        self.core.savec = PrismWidgets.SaveComment(core=self.core)
        self.core.savec.accepted.connect(
            lambda: self.core.saveWithCommentAccepted(self.core.savec)
        )
        self.core.savec.destroyed.connect(lambda: setattr(self.core, "savec", None))
        self.core.savec.show()
        self.core.savec.activateWindow()
        self.core.savec.setAttribute(Qt.WA_DeleteOnClose)
        return True

    @err_catcher(name=__name__)
    def GeometryPath(self, origin=None):

        #-----------------------------------------------------------------------------------#
        # Open the GeomatryPath Window from the Substance Prism Menu
        #-----------------------------------------------------------------------------------#

        filepath = self.getCurrentFileName(origin)
        if not filepath:
            self.core.popup("Aucune scene ouverte.")
            return

        versionInfoPath = os.path.splitext(filepath)[0] + "versioninfo.json"
        if not os.path.isfile(versionInfoPath):
            self.core.popup(
                "Impossible de trouver les informations de la scene:\n%s" % versionInfoPath
            )
            return

        try:
            with open(versionInfoPath, "r") as f:
                data = json.load(f)
        except Exception as e:
            self.core.popup("Impossible de lire les informations de la scene:\n%s" % e)
            return

        entity = {
            "type": data.get("type", "asset"),
            "asset": data.get("asset", ""),
            "asset_path": data.get("asset_path", ""),
        }

        meshData = self.findMeshCandidates(entity)

        self.core.meshDlg = MeshPathsDialog(
            meshData, assetName=entity.get("asset", ""), parent=self.core.messageParent
        )
        self.core.meshDlg.destroyed.connect(lambda: setattr(self.core, "meshDlg", None))
        self.core.meshDlg.setAttribute(Qt.WA_DeleteOnClose)
        self.core.meshDlg.show()

    @err_catcher(name=__name__)
    def ExportTextures(self, origin=None):

        #-----------------------------------------------------------------------------------#
        # From the currentFileName, find the path and asset informations for the ExportTexturesWindow
        # Open the ExportTexturesDialog Window
        #-----------------------------------------------------------------------------------#
        filepath = self.getCurrentFileName(origin)
        versionInfoPath = os.path.splitext(filepath)[0] + "versioninfo.json"

        with open(versionInfoPath, 'r') as file:
            jsonPath = json.load(file)

        # Get the Project path through the Z Disk
        networkProjectPath = jsonPath["project_path"]
        project_name = networkProjectPath.split("\\")[-1]
        localProjectPath = f"Z:\{project_name}"

        exportPath = os.path.join(localProjectPath, "03_Production", "Assets", jsonPath["asset_path"], "Textures", jsonPath["task"])

# # C:\Users\3D5\Documents\Daisy_Pipe\03_Production\Assets\Char\<assetname>\Textures\<task>\<asset_name>_<task>_v<version>.<ext>


        self.core.exportDlg = ExportTexturesDialog(core=self.core,
            assetName=jsonPath["asset"], exportPath=exportPath, parent=self.core.messageParent)
        self.core.exportDlg.destroyed.connect(lambda: setattr(self.core, "exportDlg", None))
        self.core.exportDlg.setAttribute(Qt.WA_DeleteOnClose)
        self.core.exportDlg.show()

class ExportTexturesDialog(QDialog):
    def __init__(self, core, assetName="", exportPath="", parent=None):

        #-----------------------------------------------------------------------------------#
        # Window with the export options with presets
        #   core : Prism core, needed for popups and path helpers
        #   assetName : Name of the asset
        #   exportPath : Folder path where the textures will be exported
        #-----------------------------------------------------------------------------------#

        super(ExportTexturesDialog, self).__init__(parent)
        self.core = core
        self.setWindowTitle("Prism - Export Textures")
        self.resize(650, 350)

        self.mainLayout = QVBoxLayout(self)

        titleLabel = QLabel("Export Textures for the asset : %s" % assetName)
        titleFont = titleLabel.font()
        titleFont.setPointSize(titleFont.pointSize() + 2)
        titleFont.setBold(True)
        titleLabel.setFont(titleFont)
        self.mainLayout.addWidget(titleLabel)

        ### General Parameters

        self.formLayout = QFormLayout()
        self.formLayout.setLabelAlignment(Qt.AlignRight)
        self.mainLayout.addLayout(self.formLayout)

        # Export path (QLineEdit + Browse + Reset)
        pathRow = QHBoxLayout()
        self.pathEdit = QLineEdit(exportPath)
        self.browseBtn = QPushButton("Browse")
        self.browseBtn.setMaximumWidth(30)
        self.browseBtn.clicked.connect(self.onBrowseClicked)
        self.resetBtn = QPushButton("Reset")
        self.resetBtn.setMaximumWidth(50)
        self.resetBtn.clicked.connect(lambda: self.onResetClicked(exportPath))
        pathRow.addWidget(self.pathEdit)
        pathRow.addWidget(self.browseBtn)
        pathRow.addWidget(self.resetBtn)
        self.formLayout.addRow("Export Path", pathRow)

        # Export preset
        self.presetCombo = QComboBox()
        self.presetCombo.addItems([
            "PBR Metallic Roughness",
            "Unity HDRP (Lit)",
            "Arnold (AiStandard)",
            "USD PBR Metal Roughness",
        ])
        self.formLayout.addRow("Output template", self.presetCombo)

        # File type (Type + Bit depth)
        fileRow = QHBoxLayout()
        self.formatCombo = QComboBox()
        fileType = self.formatCombo.addItems(["Based on output template", "png", "tiff", "exr"])
        self.formatCombo.currentTextChanged.connect(self.onFileTypeChanged)
        bitDepthList = self.onFileTypeChanged(text=fileType)
        self.bitDepthCombo = QComboBox()
        self.bitDepthCombo.addItems(bitDepthList)
        fileRow.addWidget(self.formatCombo)
        fileRow.addWidget(self.bitDepthCombo)
        self.formLayout.addRow("File type", fileRow)

        # Etat initial du bouton de dilation selon le choix par défaut du combo
        self.onFileTypeChanged(self.formatCombo.currentText())

        # Resolution
        self.sizeCombo = QComboBox()
        self.sizeCombo.addItems(["Based on each Texture Set's size", "128", "256", "512", "1024", "2048", "4096", "8192"])
        self.sizeCombo.setCurrentText("Based on each Texture Set's size")
        self.formLayout.addRow("Resolution", self.sizeCombo)

        # Padding (algorithm + dilation button revealing a slider popup)
        paddingRow = QHBoxLayout()
        self.paddingCombo = QComboBox()
        self.paddingCombo.addItems([
            "No padding (Passthrough)",
            "Dilation Infinite",
            "Dilation + transparent",
            "Dilation + default background color",
            "Dilation + diffusion",
        ])
        self.paddingCombo.currentTextChanged.connect(self.onPaddingChanged)

        self.dilationValue = 5
        self.dilationBtn = QPushButton(str(self.dilationValue))
        self.dilationBtn.setMaximumWidth(50)
        self.dilationBtn.clicked.connect(self.onDilationClicked)

        paddingRow.addWidget(self.paddingCombo)
        paddingRow.addWidget(self.dilationBtn)
        self.formLayout.addRow("Padding", paddingRow)

        # Popup contenant le slider, caché par défaut, affiché au clic sur dilationBtn
        self.dilationPopup = QFrame(self, Qt.Popup)
        popupLayout = QVBoxLayout(self.dilationPopup)
        popupLayout.setContentsMargins(6, 6, 6, 6)

        self.dilationSlider = QSlider(Qt.Horizontal, self.dilationPopup)
        self.dilationSlider.setRange(0, 255)
        self.dilationSlider.setValue(self.dilationValue)
        self.dilationSlider.setMinimumWidth(150)
        self.dilationSlider.valueChanged.connect(self.onDilationSliderChanged)
        popupLayout.addWidget(self.dilationSlider)

        # Etat initial du bouton de dilation selon le choix par défaut du combo
        self.onPaddingChanged(self.paddingCombo.currentText())

        # Checkboxes
        self.ditheringCheck = QCheckBox()
        self.ditheringCheck.setChecked(True)
        self.formLayout.addRow("Dithering", self.ditheringCheck)

        self.shaderParamsCheck = QCheckBox()
        self.formLayout.addRow("Export Shader Params", self.shaderParamsCheck)

        ### Bouton export

        exportBtn = QPushButton("Export")
        exportBtn.clicked.connect(self.onExportClicked)
        self.mainLayout.addWidget(exportBtn)

    def onBrowseClicked(self):

        #-----------------------------------------------------------------------------------#
        # Open a folder browser and update the export path field
        #-----------------------------------------------------------------------------------#

        folder = QFileDialog.getExistingDirectory(self, "Choose export directory", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def availableBitDepth(self, fileType):

        #-----------------------------------------------------------------------------------#
        # List the available Bit Depth by fileType
        #-----------------------------------------------------------------------------------#

        bitDepthList=[]
        if fileType =="png" or fileType =="tiff":
            bitDepthList=["8 bits", "8 bits + dithering", "16 bits"]
            if fileType =="tiff":
                bitDepthList.append("32f bits")
        elif fileType == "exr":
            bitDepthList=["16f bits", "32f bits"]
        else:
            bitDepthList=[""]
        return bitDepthList


    def onDilationClicked(self):

        #-----------------------------------------------------------------------------------#
        # Show the dilation slider popup, positioned right under the button
        #-----------------------------------------------------------------------------------#

        pos = self.dilationBtn.mapToGlobal(self.dilationBtn.rect().bottomLeft())
        self.dilationPopup.move(pos)
        self.dilationPopup.show()

    def onDilationSliderChanged(self, value):

        #-----------------------------------------------------------------------------------#
        # Update the stored dilation value and reflect it on the button label
        #-----------------------------------------------------------------------------------#

        self.dilationValue = value
        self.dilationBtn.setText(str(value))

    def onResetClicked(self, exportPath):

        #-----------------------------------------------------------------------------------#
        # Reset the export path field to its original value
        #-----------------------------------------------------------------------------------#

        self.pathEdit.setText(exportPath)

    def onPaddingChanged(self, text):

        #-----------------------------------------------------------------------------------#
        # Enable/disable the dilation button depending on the selected padding algorithm
        # Dilation distance is only relevant for transparent, color and diffusion padding
        #-----------------------------------------------------------------------------------#

        needsDilation = text in [
            "Dilation + transparent",
            "Dilation + default background color",
            "Dilation + diffusion",
        ]
        self.dilationBtn.setEnabled(needsDilation)

        

    def onFileTypeChanged(self, text):
    
            #-----------------------------------------------------------------------------------#
            # Enable/disable the dilation button depending on the selected padding algorithm
            # Dilation distance is only relevant for transparent, color and diffusion padding
            #-----------------------------------------------------------------------------------#
    
            needsBitDepth = text not in [
                "Based on output template",
            ]
            self.bitDepthCombo.setEnabled(needsBitDepth)

            bitDepthList=[]
            if text =="png" or text =="tiff":
                bitDepthList=["8 bits", "8 bits + dithering", "16 bits"]
                if text =="tiff":
                    bitDepthList.append("32f bits")
            elif text == "exr":
                bitDepthList=["16f bits", "32f bits"]
            else:
                bitDepthList=[""]
            return bitDepthList


    def getExportConfig(self):

        #-----------------------------------------------------------------------------------#
        # Build the substance_painter.export JSON config from the UI fields
        # Return - dict ready to be passed to export_project_textures
        #-----------------------------------------------------------------------------------#

        sizeLog2 = int(self.sizeCombo.currentText()).bit_length() - 1

        return {
            "exportPath": self.pathEdit.text(),
            "exportShaderParams": self.shaderParamsCheck.isChecked(),
            "defaultExportPreset": self.presetCombo.currentText(),
            "exportList": [{"rootPath": ""}],  # à compléter avec le/les texture sets réels
            "exportParameters": [{
                "parameters": {
                    "fileFormat": self.formatCombo.currentText(),
                    "bitDepth": self.bitDepthCombo.currentText(),
                    "dithering": self.ditheringCheck.isChecked(),
                    "paddingAlgorithm": self.paddingCombo.currentText(),
                    "dilationDistance": self.dilationValue,
                    "sizeLog2": sizeLog2,
                }
            }],
        }

    def onExportClicked(self):

        #-----------------------------------------------------------------------------------#
        # Trigger the actual texture export using the built config
        #-----------------------------------------------------------------------------------#

        config = self.getExportConfig()

        import substance_painter.export
        try:
            result = substance_painter.export.export_project_textures(config)
            if result.status != substance_painter.export.ExportStatus.Success:
                self.core.popup(result.message)
            else:
                self.close()
        except Exception as e:
            self.core.popup("Export failed:\n\n%s" % e)

