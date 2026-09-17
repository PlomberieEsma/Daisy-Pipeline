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
import os
import re

import substance_painter.project as sp_project

import substance_painter.textureset as sp_ts

VERSION_PATTERN = re.compile(r"^v(\d{4})$", re.IGNORECASE)
VARIANT_PATTERN = re.compile(r"^var(\d{2})$", re.IGNORECASE)


class ExportTexturesDialog(QDialog):
    MAP_TYPE_KEYWORDS = [
        "BaseColor", "Diffuse", "Albedo", "Normal", "Roughness", "Metallic", "Metalness",
        "Height", "Displacement", "AmbientOcclusion", "AO", "Emissive", "Alpha", "Reflection",
        "Opacity", "Specular", "Glossiness", "SSS", "Translucency", "ID", "Glow", "GlowColor",
        "Curvature", "Thickness", "Anisotropy", "AnisotropyAngle", "Presence", "Transmission",
        "Sheen", "SheenTint", "Clearcoat", "ClearcoatGloss", "Subsurface", "SubsurfaceColor"
    ]
    COLOR_SPACE_KEYWORDS = ["Utility - Raw", "Utility", "ACES", "ACEScg"]

    def __init__(self, core, assetName="", exportPath="", parent=None):

        #-----------------------------------------------------------------------------------#
        # Window with the export options with presets
        #   core : Prism core, needed for popups and path helpers
        #   assetName : Name of the asset
        #   exportPath : Folder path where the textures will be exported
        #-----------------------------------------------------------------------------------#

        super(ExportTexturesDialog, self).__init__(parent)
        self.core = core
        self.assetName=assetName
        self.exportPath=exportPath

        if "var" in exportPath:
            variant=exportPath.split("var")[-1]
            variant=f"_var{variant}"
        else:
            variant=""
        self.variant=variant



        
        self.setWindowTitle("Prism - Export Textures")
        self.resize(650, 350)

        self.mainLayout = QVBoxLayout(self)

        titleLabel = QLabel("Export Textures for the asset : %s" % assetName)
        titleFont = titleLabel.font()
        titleFont.setPointSize(titleFont.pointSize() + 2)
        titleFont.setBold(True)
        titleLabel.setFont(titleFont)
        self.mainLayout.addWidget(titleLabel)

        # --- Onglets ---
        self.tabWidget = QTabWidget()
        self.mainLayout.addWidget(self.tabWidget)

        settingsTab = QWidget()
        self.settingsTabLayout = QVBoxLayout(settingsTab)
        self.tabWidget.addTab(settingsTab, "Export Settings")

        summaryTab = QWidget()
        self.summaryTabLayout = QVBoxLayout(summaryTab)
        self.tabWidget.addTab(summaryTab, "Export Summary")

        ### General Parameters

        sTitle1Label = QLabel("Export path parameters")
        sTitle1Font = sTitle1Label.font()
        sTitle1Font.setPointSize(sTitle1Font.pointSize() + 2)
        sTitle1Font.setBold(True)
        sTitle1Label.setFont(sTitle1Font)
        sTitle1Label.setContentsMargins(0, 20, 5, 0)
        self.settingsTabLayout.addWidget(sTitle1Label)

        self.formPathLayout = QFormLayout()
        self.formPathLayout.setLabelAlignment(Qt.AlignRight)
        self.settingsTabLayout.addLayout(self.formPathLayout)

        
        self.pathEdit = QLineEdit(exportPath)
        self.baseExportPath = exportPath

        # Export version CheckBoxe
        versionRow = QHBoxLayout()
        self.newVersionCheck = QCheckBox()
        self.versionCombo = QComboBox()

        existingVersions = self.availableVersions(exportPath)
        self.versionCombo.addItems(existingVersions)
        if existingVersions == ["No existing version yet"]:
            self.newVersionCheck.setChecked(True)

        # Connexions posées APRES l'état initial, pour éviter un déclenchement prématuré
        self.newVersionCheck.toggled.connect(self.onVersionChecked)
        self.newVersionCheck.toggled.connect(self.refreshExportPath)
        self.versionCombo.currentTextChanged.connect(self.refreshExportPath)

        # Etat initial, maintenant que pathEdit/baseExportPath/versionCombo existent tous
        self.onVersionChecked(self.newVersionCheck.isChecked())
        self.refreshExportPath()

        versionRow.addWidget(self.newVersionCheck)
        versionRow.addWidget(self.versionCombo, stretch=1)
        self.formPathLayout.addRow("Export as new version", versionRow)

        # Etat initial du combo version selon l'état par défaut de la checkbox
        self.onVersionChecked(self.newVersionCheck.isChecked())

        # Export path (QLineEdit + Browse + Reset)
        pathRow = QHBoxLayout()
        self.browseBtn = QPushButton("Browse")
        self.browseBtn.setMaximumWidth(30)
        self.browseBtn.clicked.connect(self.onBrowseClicked)
        self.resetBtn = QPushButton("Reset")
        self.resetBtn.setMaximumWidth(30)
        self.resetBtn.clicked.connect(lambda: self.refreshExportPath())
        pathRow.addWidget(self.pathEdit)
        pathRow.addWidget(self.browseBtn)
        pathRow.addWidget(self.resetBtn)
        self.formPathLayout.addRow("Export Path", pathRow)

        ### Texture Parameters

        sTitle2Label = QLabel("Texture parameters")
        sTitle2Font = sTitle2Label.font()
        sTitle2Font.setPointSize(sTitle2Font.pointSize() + 2)
        sTitle2Font.setBold(True)
        sTitle2Label.setFont(sTitle2Font)
        sTitle2Label.setContentsMargins(0, 20, 5, 0)
        self.settingsTabLayout.addWidget(sTitle2Label)

        self.formTextureLayout = QFormLayout()
        self.formTextureLayout.setLabelAlignment(Qt.AlignRight)
        self.settingsTabLayout.addLayout(self.formTextureLayout)

        # Export preset (récupérés dynamiquement depuis les shelves du projet)
        self.presetResources = self.availablePresets()
        self.presetCombo = QComboBox()
        self.presetCombo.addItems(sorted(self.presetResources.keys()) or ["No preset found"])
        self.formTextureLayout.addRow("Output template", self.presetCombo)

        # File type (Type + Bit depth)
        fileRow = QHBoxLayout()
        self.formatCombo = QComboBox()
        self.formatCombo.addItems(["Based on output template", "png", "tiff", "exr"])
        self.bitDepthCombo = QComboBox()
        self.formatCombo.currentTextChanged.connect(self.onFileTypeChanged)
        fileRow.addWidget(self.formatCombo)
        fileRow.addWidget(self.bitDepthCombo)
        self.formTextureLayout.addRow("File type", fileRow)

        # Etat initial du combo bit depth selon le choix par défaut du format
        self.onFileTypeChanged(self.formatCombo.currentText())

        # Resolution
        self.sizeCombo = QComboBox()
        self.sizeCombo.addItems(["Based on each Texture Set's size", "128", "256", "512", "1024", "2048", "4096", "8192"])
        self.sizeCombo.setCurrentText("Based on each Texture Set's size")
        self.formTextureLayout.addRow("Resolution", self.sizeCombo)

        # Padding (algorithm + dilation button revealing a slider popup)
        paddingRow = QHBoxLayout()
        self.paddingCombo = QComboBox()
        paddingOptions = [
            ("No padding (Passthrough)", "passthrough"),
            ("Dilation Infinite", "infinite"),
            ("Dilation + transparent", "transparent"),
            ("Dilation + default background color", "color"),
            ("Dilation + diffusion", "diffusion"),
        ]
        for label, key in paddingOptions:
            self.paddingCombo.addItem(label, key)
        self.paddingCombo.currentTextChanged.connect(self.onPaddingChanged)

        self.dilationValue = 5
        self.dilationBtn = QPushButton(str(self.dilationValue))
        self.dilationBtn.setMaximumWidth(50)
        self.dilationBtn.clicked.connect(self.onDilationClicked)

        paddingRow.addWidget(self.paddingCombo)
        paddingRow.addWidget(self.dilationBtn)
        self.formTextureLayout.addRow("Padding", paddingRow)

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
        self.shaderParamsCheck = QCheckBox()
        self.formTextureLayout.addRow("Export Shader Params", self.shaderParamsCheck)


        #### TEXTURE SETS AND TEXTURES PREVIEW

        self.textureTree = QTreeWidget()
        self.textureTree.setHeaderHidden(True)
        self.textureTree.setMinimumHeight(220)
        self.textureTree.setMaximumHeight(220)

        for tsName in self.availableTextureSets():
            tsItem = QTreeWidgetItem([tsName])
            tsItem.setFlags(tsItem.flags() | Qt.ItemIsUserCheckable)
            tsItem.setCheckState(0, Qt.Checked)
            self.textureTree.addTopLevelItem(tsItem)
        

        self.textureTree.itemChanged.connect(self.onTreeItemChanged)
        self.formTextureLayout.addRow("Textures to export", self.textureTree)

        # --- Onglet Summary ---
        self.exportSummaryList = QListWidget()
        self.summaryTabLayout.addWidget(self.exportSummaryList)

        # Preset et Texture Sets déclenchent tous les deux un recalcul de la preview
        self.presetCombo.currentTextChanged.connect(self.refreshTexturePreview)

        # Etat initial de la preview
        self.refreshTexturePreview()


        ### EXPORT

        ### Bouton export
        exportBtn = QPushButton("Export")
        exportBtn.clicked.connect(self.onExportClicked)
        self.mainLayout.addWidget(exportBtn)


    #########################################################################################
    #   Export Path Functions
    #########################################################################################

    def onVersionChecked(self, checked):

        #-----------------------------------------------------------------------------------#
        # Grey out and disable the version combo when "new version" is checked,
        # keep it active otherwise
        #-----------------------------------------------------------------------------------#

        self.versionCombo.setEnabled(not checked)

    def availableVersions(self, exportPath):

        #-----------------------------------------------------------------------------------#
        # List all existing version folders (vXXXX) found in exportPath
        #   exportPath : Folder path where the version folders are located
        # Return - list of version folder names (e.g. ["v0001", "v0003"]),
        #          or ["No existing version yet"] if none found
        #-----------------------------------------------------------------------------------#

        if not os.path.isdir(exportPath):
            return ["No existing version yet"]

        foundVersions = []
        for f in os.listdir(exportPath):
            fullPath = os.path.join(exportPath, f)
            if not os.path.isdir(fullPath):
                continue
            if not VERSION_PATTERN.match(f):
                continue
            foundVersions.append(f)

        if not foundVersions:
            return ["No existing version yet"]

        foundVersions.sort(key=lambda v: int(VERSION_PATTERN.match(v).group(1)), reverse=True)
        return foundVersions

    def onVersionChanged(self, exportPath, selectedVersion, versionChecked):

        #-----------------------------------------------------------------------------------#
        # Recompute the version folder to use and update the export path field accordingly
        #   exportPath : base export path, without any version folder appended
        #   selectedVersion : currently selected item in versionCombo
        #   versionChecked : state of the "Export as new version" checkbox
        #-----------------------------------------------------------------------------------#

        if selectedVersion == "No existing version yet":
            version = "v0001"
        elif versionChecked:
            existingVersions = self.availableVersions(exportPath)
            if existingVersions == ["No existing version yet"]:
                version = "v0001"
            else:
                highest = max(int(VERSION_PATTERN.match(v).group(1)) for v in existingVersions)
                version = "v%04d" % (highest + 1)
        else:
            version = selectedVersion

        newExportPath = self.defaultExportPath(exportPath, version)
        self.pathEdit.setText(newExportPath)

        return version
    
    def defaultExportPath(self, exportPath, version):

        #-----------------------------------------------------------------------------------#
        # Update the export path field accordingly
        #   exportPath : base export path, without any version folder appended
        #   version : v\d{4} name of the version folder
        # Return
        #   exportPath : export path with folder appened
        #-----------------------------------------------------------------------------------#

        exportPath = os.path.join(exportPath, version)
        return exportPath

    def refreshExportPath(self, *args):

        #-----------------------------------------------------------------------------------#
        # Wrapper called by both the checkbox and the combo signals (different payloads),
        # re-reads the current UI state and updates the export path field
        #-----------------------------------------------------------------------------------#

        self.onVersionChanged(
            self.baseExportPath,
            self.versionCombo.currentText(),
            self.newVersionCheck.isChecked(),
        )

    def onBrowseClicked(self):

        #-----------------------------------------------------------------------------------#
        # Open a folder browser and update the export path field
        #-----------------------------------------------------------------------------------#

        folder = QFileDialog.getExistingDirectory(self, "Choose export directory", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def onResetClicked(self, exportPath):

        #-----------------------------------------------------------------------------------#
        # Reset the export path field to its original value
        #-----------------------------------------------------------------------------------#

        self.pathEdit.setText(exportPath)

    #########################################################################################
    #   Texture Paramaters Functions
    #########################################################################################

    def availableBitDepth(self, fileType):

        #-----------------------------------------------------------------------------------#
        # List the available Bit Depth by fileType
        #-----------------------------------------------------------------------------------#

        if fileType == "png" or fileType == "tiff":
            bitDepthList = [("8 bits", "8"), ("8 bits + dithering", "8"), ("16 bits", "16")]
            if fileType == "tiff":
                bitDepthList.append(("32f bits", "32"))
        elif fileType == "exr":
            bitDepthList = [("16f bits", "16f"), ("32f bits", "32f")]
        else:
            bitDepthList = []
        return bitDepthList

    def onFileTypeChanged(self, text):

        #-----------------------------------------------------------------------------------#
        # Refresh the available bit depth options based on the selected file format
        # "Based on output template" disables the choice entirely
        #-----------------------------------------------------------------------------------#

        needsBitDepth = text != "Based on output template"
        self.bitDepthCombo.setEnabled(needsBitDepth)

        self.bitDepthCombo.clear()
        bitDepthList=self.availableBitDepth(text)
        for label, key in bitDepthList:
            self.bitDepthCombo.addItem(label, key)

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

    def onPaddingChanged(self, text):

        #-----------------------------------------------------------------------------------#
        # Enable/disable the dilation button depending on the selected padding algorithm
        # Dilation distance is only relevant for transparent, color and diffusion padding
        #-----------------------------------------------------------------------------------#

        needsDilation = self.paddingCombo.currentData() in ["transparent", "color", "diffusion"]
        self.dilationBtn.setEnabled(needsDilation)



    #########################################################################################
    #   Textures to Export Functions
    #########################################################################################

    def availableTextureSets(self):
        import substance_painter.textureset
        try:
            return [ts.name() for ts in substance_painter.textureset.all_texture_sets()]
        except Exception as e:
            self.core.popup("Couldn't list Texture Sets:\n\n%s" % e)
            return []

    def selectedTextureSets(self):

        #-----------------------------------------------------------------------------------#
        # Read the currently checked Texture Sets from the top-level items of textureTree
        # Return - list of checked Texture Set names
        #-----------------------------------------------------------------------------------#

        selected = []
        for i in range(self.textureTree.topLevelItemCount()):
            tsItem = self.textureTree.topLevelItem(i)
            if tsItem.checkState(0) == Qt.Checked:
                selected.append(tsItem.text(0))
        return selected

    def availablePresets(self):
        import substance_painter.resource

        presets = {}
        try:
            for shelf in substance_painter.resource.Shelves.all():
                presetsDir = os.path.join(shelf.path(), "export-presets")
                if not os.path.isdir(presetsDir):
                    continue

                for filename in os.listdir(presetsDir):
                    if not filename.endswith(".spexp"):
                        continue

                    name = os.path.splitext(filename)[0]
                    resId = substance_painter.resource.ResourceID(context=shelf.name(), name=name)
                    resList = substance_painter.resource.Resource.retrieve(resId)
                    if not resList:
                        continue

                    presets[resList[0].gui_name()] = {
                        "resourceId": resId,
                        "path": os.path.join(presetsDir, filename),
                    }
        except Exception as e:
            self.core.popup("Couldn't list export presets:\n\n%s" % e)

        return presets

    def refreshTexturePreview(self, *args):

        #-----------------------------------------------------------------------------------#
        # Simulate an export with the current settings and list the resulting textures,
        # without writing anything to disk. Populates each checked Texture Set's children
        # in textureTree with the predicted texture files, as checkable items.
        #-----------------------------------------------------------------------------------#

        selectedTextureSets = self.selectedTextureSets()

        presetResource = self.presetResources.get(self.presetCombo.currentText())

        # On garde les cases déjà décochées par l'utilisateur avant de tout reconstruire
        previouslyUnchecked = getattr(self, "excludedTextures", set())

        # On bloque les signaux pendant la reconstruction pour éviter tout rebouclage
        # sur onTreeItemChanged pendant qu'on coche/décoche les enfants nous-mêmes
        self.textureTree.blockSignals(True)

        for i in range(self.textureTree.topLevelItemCount()):
            self.textureTree.topLevelItem(i).takeChildren()

        if selectedTextureSets and presetResource:
            previewConfig = self.getExportConfig()

            import substance_painter.export
            try:
                result = substance_painter.export.list_project_textures(previewConfig)
                textureRenamed=self.mapNaming(self.assetName, self.variant, result)
            except Exception as e:
                self.textureTree.blockSignals(False)
                errorItem = QTreeWidgetItem(["Preview unavailable: %s" % e])
                errorItem.setFlags(Qt.NoItemFlags)
                self.textureTree.addTopLevelItem(errorItem)
                return

            # Index les Texture Set items par nom pour y rattacher les bons enfants
            tsItemsByName = {}
            for i in range(self.textureTree.topLevelItemCount()):
                tsItem = self.textureTree.topLevelItem(i)
                tsItemsByName[tsItem.text(0)] = tsItem

            for textureSetName, filenames in textureRenamed.items():
                tsItem = tsItemsByName.get(textureSetName)
                if not tsItem:
                    continue

                for filename in filenames:
                    mapLabel = self.guessMapType(filename) or os.path.splitext(os.path.basename(filename))[0]
                    texItem = QTreeWidgetItem([mapLabel])
                    texItem.setFlags(texItem.flags() | Qt.ItemIsUserCheckable)
                    texItem.setCheckState(
                        0, Qt.Unchecked if filename in previouslyUnchecked else Qt.Checked
                    )
                    texItem.setData(0, Qt.UserRole, filename)
                    texItem.setToolTip(0, filename)  # nom complet visible au survol
                    tsItem.addChild(texItem)

            self.textureTree.expandAll()

        self.textureTree.blockSignals(False)
        self.refreshExportSummary()


    def refreshExportSummary(self):

        #-----------------------------------------------------------------------------------#
        # List the full filenames of every texture currently checked for export,
        # across all checked Texture Sets in textureTree
        #-----------------------------------------------------------------------------------#

        self.exportSummaryList.clear()
        for i in range(self.textureTree.topLevelItemCount()):
            tsItem = self.textureTree.topLevelItem(i)
            if tsItem.checkState(0) != Qt.Checked:
                continue

            for j in range(tsItem.childCount()):
                texItem = tsItem.child(j)
                if texItem.checkState(0) == Qt.Checked:
                    filename = texItem.data(0, Qt.UserRole)
                    self.exportSummaryList.addItem(os.path.basename(filename))

    def onTreeItemChanged(self, item, column):

        #-----------------------------------------------------------------------------------#
        # Toggling a Texture Set (top-level item) changes exportList -> full preview refresh
        # Toggling a single texture (child item) only affects the summary -> lightweight update
        #-----------------------------------------------------------------------------------#

        if item.parent() is None:
            self.refreshTexturePreview()
        else:
            self.refreshExportSummary()

    def _resolve(self, value):
        if callable(value):
            return value()
        return value

    def guessMapType(self, filename):

        #-----------------------------------------------------------------------------------#
        # Try to extract a short, readable map type (BaseColor, Normal, ...) from a filename
        #   filename : full path or filename of the exported texture
        # Return - the matched keyword, or the filename stem if nothing matched
        #-----------------------------------------------------------------------------------#

        stem = os.path.splitext(os.path.basename(filename))[0]
        for keyword in self.MAP_TYPE_KEYWORDS:
            if keyword.lower() in stem.lower():
                return keyword
        return None  # plus de fallback ici, géré par l'appelant
    
    def guessColorSpace(self, filename):

        #-----------------------------------------------------------------------------------#
        # Try to extract the color space token (Raw, Utility, Aces) from a filename
        #   filename : full path or filename of the exported texture
        # Return - the matched keyword, or None if nothing matched
        #-----------------------------------------------------------------------------------#

        stem = os.path.splitext(os.path.basename(filename))[0]
        for token in stem.split("_"):
            if " - " in token:
                return token
        return None

    def extractMapLabel(self, filepath, matName, colorSpace):

        #-----------------------------------------------------------------------------------#
        # Extract the map type label by taking the substring between matName and the
        # colorSpace token (or the extension, if no colorSpace was found)
        #   filepath : full path or filename of the exported texture
        #   matName : texture set / material name, as found in mapNaming()
        #   colorSpace : color space token returned by guessColorSpace(), or None
        # Return - the isolated map label, or the file stem if matName wasn't found
        #-----------------------------------------------------------------------------------#

        stem = os.path.splitext(os.path.basename(filepath))[0]

        idx = stem.find(matName)
        if idx == -1:
            return stem

        after = stem[idx + len(matName):]

        if colorSpace and after.endswith(colorSpace):
            after = after[: -len(colorSpace)]

        return after.strip("_")

    def mapNaming(self, assetName, variant, textureFileDict):

        #-----------------------------------------------------------------------------------#
        # Build the custom naming string used to replace $mesh in the export preset
        #   assetName : Name of the asset
        #   variant : "var{2}" if the curent scene is a variant
        #   textureFile : Dictionnary with tuple as key with lists of all maps and paths to export
        # Return
        #   materialDict : Dictionnary with texture set as key and texture maps names for each texture set
        #-----------------------------------------------------------------------------------#

        materialDict = {}
        for key, filepaths in textureFileDict.items():
            matName = key[0]
            texturePath = []
            for filepath in filepaths:
                colorSpace = self.guessColorSpace(filepath)

                mapLabel = self.guessMapType(filepath)
                if mapLabel is None:
                    mapLabel = self.extractMapLabel(filepath, matName, colorSpace)

                ext = os.path.splitext(filepath)[1]
            
                if colorSpace:
                    colorSpaceClean = colorSpace.replace(" - ", "_").replace(" ", "")
                    newName = f"{assetName}{variant}_{matName}_{mapLabel}_{colorSpaceClean}{ext}"
                else:
                    newName = f"{assetName}{variant}_{matName}_{mapLabel}{ext}"

                texturePath.append(newName)
            materialDict[matName] = texturePath
        return materialDict


    def stackHasChannel(self, textureSetName, channelType):
        stack = sp_ts.Stack.from_name(textureSetName)
        return stack.has_channel(channelType)



    #########################################################################################
    #   Textures to Export Functions
    #########################################################################################

    def isConfigExportable(self, config):

        #-----------------------------------------------------------------------------------#
        # Try list_project_textures with the current config: if it raises, or returns
        # nothing, the preset is incompatible with the selected stacks' channels
        #-----------------------------------------------------------------------------------#

        import substance_painter.export
        try:
            result = substance_painter.export.list_project_textures(config)
        except Exception:
            return False
        return any(filenames for filenames in result.values())

    def getExportConfig(self):

        #-----------------------------------------------------------------------------------#
        # Build the substance_painter.export JSON config from the UI fields
        # Return - dict ready to be passed to export_project_textures
        #-----------------------------------------------------------------------------------#

        presetResource = self.presetResources.get(self.presetCombo.currentText())
        selectedTextureSets = self.selectedTextureSets()

        parameters = {
            "paddingAlgorithm": self.paddingCombo.currentData(),
            "dilationDistance": self.dilationValue,
        }

        if self.formatCombo.currentText() != "Based on output template":
            parameters["fileFormat"] = self.formatCombo.currentText()
            if self.bitDepthCombo.currentData():
                parameters["bitDepth"] = self.bitDepthCombo.currentData()

        if self.sizeCombo.currentText() != "Based on each Texture Set's size":
            parameters["sizeLog2"] = int(self.sizeCombo.currentText()).bit_length() - 1

        presetUrl = None
        if presetResource:
            presetUrl = self._resolve(presetResource["resourceId"].url)

        selectedLabel = self.presetCombo.currentText()
        presetInfo = self.presetResources.get(selectedLabel)

        presetUrl = presetInfo["resourceId"].url()

        return {
            "exportPath": self.pathEdit.text(),
            "exportShaderParams": self.shaderParamsCheck.isChecked(),
            "defaultExportPreset": presetUrl,
            "exportList": [{"rootPath": ts} for ts in selectedTextureSets],
            "exportParameters": [{"parameters": parameters}],
        }

    def onExportClicked(self):

        #-----------------------------------------------------------------------------------#
        # Trigger the actual texture export, then remove any file the user unchecked
        # in the texture tree
        #-----------------------------------------------------------------------------------#

        self.excludedTextures = set()
        for i in range(self.textureTree.topLevelItemCount()):
            tsItem = self.textureTree.topLevelItem(i)
            for j in range(tsItem.childCount()):
                texItem = tsItem.child(j)
                if texItem.checkState(0) == Qt.Unchecked:
                    self.excludedTextures.add(texItem.data(0, Qt.UserRole))

        config = self.getExportConfig()

        if not self.isConfigExportable(config):
            self.core.popup(
                "Ce preset ne correspond à aucun channel disponible sur les Texture Sets "
                "sélectionnés (ex: workflow Spec/Gloss vs Metal/Rough). Choisissez un autre preset."
            )
            return

        import substance_painter.export
        try:
            result = substance_painter.export.export_project_textures(config)
            if result.status != substance_painter.export.ExportStatus.Success:
                self.core.popup(result.message)
                return
            
            # Renomme les fichiers réels pour qu'ils matchent exactement le summary
            renamedTextures = self.mapNaming(self.assetName, self.variant, result.textures)

            for key, filepaths in result.textures.items():
                matName = key[0]
                desiredNames = renamedTextures.get(matName, [])
                for filepath, desiredName in zip(filepaths, desiredNames):
                    if not os.path.isfile(filepath):
                        continue
                    newPath = os.path.join(os.path.dirname(filepath), desiredName)
                    if filepath != newPath:
                        if os.path.isfile(newPath):
                            os.remove(newPath)
                        os.rename(filepath, newPath)

                    if desiredName in self.excludedTextures and os.path.isfile(newPath):
                        os.remove(newPath)

            self.close()
        except Exception as e:
            self.core.popup("Export failed:\n\n%s" % e)

