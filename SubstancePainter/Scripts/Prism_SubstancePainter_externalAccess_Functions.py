import os
import json
import platform
import re

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

MESH_EXTENSIONS = (".obj", ".fbx", ".abc", ".usd", ".usda", ".usdc")
MOD_FOLDER_PATTERN = re.compile(r"^Mod[HL](_var\d+)?$", re.IGNORECASE)

class Prism_SubstancePainter_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.core.registerCallback(
            "openPBFileContextMenu", self.openPBFileContextMenu, plugin=self
        )

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin):
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(
                self.core.getWindowsDocumentsPath(), "SubstancePainter"
            )

        fileStr = "SubstancePainter Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def copySceneFile(self, origin, origFile, targetPath, mode="copy"):
        pass

    ##############################################################################################################
    ###########################     EmptyScene - Creation depuis Project Browser     ###########################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def getPendingFilePath(self):

        #-----------------------------------------------------------------------------------#
        # Get the Substance Json pending file path
        # Return - Path to the file
        #-----------------------------------------------------------------------------------#

        return os.path.join(
            self.core.projectPath,
            "00_Pipeline", "Plugins", "SubstancePainter", "tmp",
            "SubstancePainterPending.json",
        )

    def openPBFileContextMenu(self, origin, rcMenu, widget):

        #-----------------------------------------------------------------------------------#
        # Add a EmptyScene SubstancePainter to the Presets scenes in the RC Contextual Menu in the Files
        # Return - Launch onEmptySceneRequested function
        #-----------------------------------------------------------------------------------#

        entity = origin.getCurrentEntity()
        widgetType = "department" if widget == origin.lw_departments else "task"

        if entity and entity["type"] in ["asset"] and widgetType == "task":
            deptItem = origin.lw_departments.currentItem()
            if not deptItem:
                return
            department = deptItem.data(Qt.UserRole)

            emptySceneAction = QAction("EmptyScene SubstancePainter", origin)
            emptySceneAction.triggered.connect(
                lambda: self.onEmptySceneRequested(origin, entity, department)
            )

            presetMenu = None
            for act in rcMenu.actions():
                if act.menu() and act.text() == self.core.tr("Create new version from preset"):
                    presetMenu = act.menu()
                    break

            if presetMenu:
                presetMenu.addAction(emptySceneAction)
            else:
                rcMenu.addAction(emptySceneAction)

    @err_catcher(name=__name__)
    def onEmptySceneRequested(self, origin, entity, department):

        #-----------------------------------------------------------------------------------#
        # Open SubstancePainter and create a pending file Json to keep the scene info for the first save
        # Return - Open the Geometry Path window
        #-----------------------------------------------------------------------------------#

        taskItem = origin.lw_tasks.currentItem()
        taskName = taskItem.text() if taskItem else ""

        version = self.core.entities.getHighestVersion(entity, department, taskName)
        ext = self.sceneFormats[0]

        filepath = self.core.generateScenePath(
            entity,
            department,
            task=taskName,
            extension=ext,
            comment="",
            version=version,
            user=self.core.user,
        )

        if self.core.useLocalFiles:
            filepath = self.core.convertPath(filepath, "local")

        filepath = filepath.replace("\\", "/")

        if os.path.exists(filepath):
            self.core.popup("There already is a scene here:\n\n%s" % filepath)
            return

        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except Exception as e:
                self.core.popup("Folder couldn't be created:\n\n%s" % e)
                return

        pendingData = {
            "project_path": self.core.projectPath,
            "asset_path": entity.get("asset_path", ""),
            "asset": entity.get("asset", ""),
            "type": entity.get("type", "asset"),
            "department": department,
            "task": taskName,
            "version": version,
            "comment": "",
            "extension": ext,
            "user": self.core.user,
            "filepath": filepath,
        }

        pendingFile = self.getPendingFilePath()
        os.makedirs(os.path.dirname(pendingFile), exist_ok=True)
        with open(pendingFile, "w") as f:
            json.dump(pendingData, f, indent=4)

        meshData = self.findMeshCandidates(entity)

        self.core.meshDlg = MeshPathsDialog(
            meshData, assetName=entity.get("asset", ""), parent=self.core.messageParent, source="new"
        )
        self.core.meshDlg.destroyed.connect(lambda: setattr(self.core, "meshDlg", None))
        self.core.meshDlg.setAttribute(Qt.WA_DeleteOnClose)
        self.core.meshDlg.show()

    @err_catcher(name=__name__)
    def findMeshCandidates(self, entity):

        #-----------------------------------------------------------------------------------#
        # Find the all meshes in all format from the same asset as where the user clicked.
        # Return - mashData dict with
        #   variant - name of the variant
        #   definition - ModH or ModL
        #   format - format of the files found
        #   path - path to the folder of the files found
        #-----------------------------------------------------------------------------------#

        meshData = []
        assetName = entity.get("asset", "")

        # Get the Project path through the Z Disk
        networkProjectPath = self.core.projectPath
        project_name = os.path.basename(networkProjectPath.rstrip("/\\"))
        localProjectPath = os.path.join("Z:\\", project_name)

        exportPath = os.path.join(
            localProjectPath, "03_Production", "Assets",
            entity["asset_path"].replace("\\", os.sep), "Export"
        )
        if not os.path.isdir(exportPath):
            return meshData

        for modFolder in sorted(os.listdir(exportPath)):
            match = MOD_FOLDER_PATTERN.match(modFolder)
            if not match:
                continue

            definition = modFolder[:4]  # "ModH" ou "ModL" (les 4 premiers caracteres)
            variantSuffix = match.group(1)
            variantLabel = variantSuffix[1:] if variantSuffix else "Base"

            masterPath = os.path.join(exportPath, modFolder, "master")
            if not os.path.isdir(masterPath):
                continue

            filenamePattern = re.compile(
                r"^%s_%s_master\.\w+$" % (re.escape(assetName), re.escape(modFolder)),
                re.IGNORECASE,
            )

            foundFormats = set()
            for f in os.listdir(masterPath):
                fullPath = os.path.join(masterPath, f)
                if not os.path.isfile(fullPath):
                    continue

                ext = os.path.splitext(f)[1].lower()
                if ext not in MESH_EXTENSIONS:
                    continue
                if not filenamePattern.match(f):
                    continue

                foundFormats.add(ext[1:].upper())

            if not foundFormats:
                continue

            meshData.append({
                "variant": variantLabel,
                "definition": definition,
                "format": ", ".join(sorted(foundFormats)),
                "path": masterPath.replace("\\", "/"),
            })

        return meshData

class MeshPathsDialog(QDialog):
    def __init__(self, meshData, assetName="", parent=None, source=None):

        #-----------------------------------------------------------------------------------#
        # Window with the different meshes of the same asset textured for path selection
        #-----------------------------------------------------------------------------------#

        super(MeshPathsDialog, self).__init__(parent)
        self.setWindowTitle("Prism - Geometry Path")
        self.resize(650, 350)
        self.meshData = meshData

        self.variants = sorted(set(m["variant"] for m in meshData))

        self.mainLayout = QVBoxLayout(self)

        titleLabel = QLabel("Mesh for the asset : %s" % assetName)
        titleFont = titleLabel.font()
        titleFont.setPointSize(titleFont.pointSize() + 2)
        titleFont.setBold(True)
        titleLabel.setFont(titleFont)
        self.mainLayout.addWidget(titleLabel)

        if source == "new":
            helpLabel = QLabel("Guide : \nCopy the path of the mesh you want to use " \
                "\nGo to Files > New project... > Select and paste the path in the os window." \
                "\nChoose which format you prefer if there are several.\n")
            helpFont = helpLabel.font()
            helpFont.setPointSize(helpFont.pointSize() + 2)
            helpLabel.setFont(helpFont)
            self.mainLayout.addWidget(helpLabel)


        if len(self.variants) > 1:
            comboRow = QHBoxLayout()
            comboRow.addWidget(QLabel("Variant :"))
            self.variantCombo = QComboBox()
            self.variantCombo.addItems(self.variants)
            self.variantCombo.currentTextChanged.connect(self.refreshTable)
            comboRow.addWidget(self.variantCombo)
            comboRow.addStretch()
            self.mainLayout.addLayout(comboRow)
        else:
            self.variantCombo = None

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Definition", "Format", "Path", ""])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mainLayout.addWidget(self.table)

        closeBtn = QPushButton("Close")
        closeBtn.clicked.connect(self.close)
        self.mainLayout.addWidget(closeBtn)

        initialVariant = self.variants[0] if self.variants else None
        self.refreshTable(initialVariant)

    def refreshTable(self, variant):

        #-----------------------------------------------------------------------------------#
        # Refresh the Path selection UI
        #-----------------------------------------------------------------------------------#

        filtered = [m for m in self.meshData if m["variant"] == variant] if variant else self.meshData

        self.table.setRowCount(len(filtered))

        for row, m in enumerate(filtered):
            defItem = QTableWidgetItem(m["definition"])
            self.table.setItem(row, 0, defItem)

            formatItem = QTableWidgetItem(m["format"])
            self.table.setItem(row, 1, formatItem)

            pathItem = QTableWidgetItem(m["path"])
            self.table.setItem(row, 2, pathItem)

            copyBtn = QPushButton("Copy")
            copyBtn.clicked.connect(lambda checked, p=m["path"]: self.copyToClipboard(p))
            self.table.setCellWidget(row, 3, copyBtn)

        if not filtered:
            self.table.setRowCount(1)
            emptyItem = QTableWidgetItem("No mesh found.")
            self.table.setItem(0, 0, emptyItem)
            self.table.setSpan(0, 0, 1, 4)

    def copyToClipboard(self, path):

        #-----------------------------------------------------------------------------------#
        # Copy the path link to clipboard for later Paste
        #-----------------------------------------------------------------------------------#

        QApplication.clipboard().setText(path)