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
import re
import os, sys

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

class SelectedAssetsList(QTreeWidget):

    #-----------------------------------------------------------------------------------#
    # Class used in the Asset Browser to handle the asset movement between lists        #
    # Actions to Drag and Drop the Asset from the left list to the selected list        #
    # Action to Delete the Asset from the selected list                                 #
    #-----------------------------------------------------------------------------------#

    
    def __init__(self, parentDlg):
        super(SelectedAssetsList, self).__init__()
        self.parentDlg = parentDlg
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        try:
            self.parentDlg.onAssetsDropped()
        except Exception as e:
            self.parentDlg.core.popup("Erreur drop: %s" % e)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.parentDlg.onRemoveSelectedAssets(self.selectedItems())
        else:
            super(SelectedAssetsList, self).keyPressEvent(event)

class AssetBrowserUI(object):
    def __init__(self, core, plugin = None):
        self.core = core
        self.plugin = plugin

    def onAssetBrowserTriggered(self, entity, task, checked=False):
        
        #-----------------------------------------------------------------------------------#
        # Window Asset Browser to select assets to load into a scene during layout          #
        # If opened from Task SetDress, simple double column view                           #
        # If opened from Task RLO, the SetDress USD file is already being selected          #
        #       only need to select Char and Props
        # Entity imported for shot and sequence 
        #-----------------------------------------------------------------------------------#

        # self.core.popup("Current entity: %s" % entity)

        self.toImportAsset = []  # valeur par défaut si l'utilisateur ferme sans valider

        try:
            allAssetPaths = self.core.entities.getAssetPaths()
            self.assetRoot = os.path.commonpath(allAssetPaths) if allAssetPaths else ""
            
            self.assetBrowserDlg = QDialog()
            self.core.parentWindow(self.assetBrowserDlg)
            self.assetBrowserDlg.setWindowTitle("Asset Browser")
            self.assetBrowserDlg.resize(700, 600)

            # Set Window Icon
            iconPath = os.path.join(
                self.core.projectPath,
                "00_Pipeline", "Plugins", "Daisy_Pipe", "Integration", "ui", "daisy_logo.png"
            )
            iconPath = os.path.normpath(iconPath)

            if os.path.isfile(iconPath):
                self.assetBrowserDlg.setWindowIcon(QIcon(iconPath))
            else:
                self.core.popup("Icône introuvable: %s" % iconPath)

            mainLayout = QVBoxLayout(self.assetBrowserDlg)

            # NOUVELLE LIGNE TOUT EN HAUT : rappel Séquence / Shot
            
            lo_context = QHBoxLayout()
            lbl_context = QLabel("Sequence / Shot :")
            lbl_context.setStyleSheet("font-weight: bold;")

            sequenceName = entity.get("sequence", "") if entity else ""
            shotName = entity.get("shot", "") if entity else ""
            self.lbl_contextValue = QLabel(f"{sequenceName} / {shotName}")

            lo_context.addWidget(lbl_context)
            lo_context.addWidget(self.lbl_contextValue)
            lo_context.addStretch()
            mainLayout.addLayout(lo_context)

            columnsLayout = QHBoxLayout()
            mainLayout.addLayout(columnsLayout)

            # LEFT COLUMN : Prism Asset List
            import EntityWidget
            self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
            # Keep only necessary and hide shots
            self.w_entities.tb_entities.setVisible(False)
            self.w_entities.getPage("Assets").tw_tree.setDragEnabled(True)
            self.selectedAssetsData = {}  # clé = asset_path (unique), valeur = entity dict
            columnsLayout.addWidget(self.w_entities)

            # RIGHT COLUMN : conteneur vertical (SetDress + Selected Assets)
            rightColumnLayout = QVBoxLayout()
            columnsLayout.addLayout(rightColumnLayout)

            if task == "RLO":
                # Check if the Asset Browser will be in SetDress View or RLO View
                # self.core.popup("RLO task detected.")

                # TOP RIGHT COLUMN : Shot SetDress
                self.gb_setDress = QGroupBox("Shot SetDress")
                lo_setDress = QHBoxLayout()
                self.gb_setDress.setLayout(lo_setDress)

                # Ligne titre "Selected SetDress"
                lo_selectedSetDress = QHBoxLayout()
                lbl_selectedSetDress = QLabel("Selected SetDress")
                lo_selectedSetDress.addWidget(lbl_selectedSetDress)
                lo_selectedSetDress.addStretch()
                lo_setDress.addLayout(lo_selectedSetDress)

                # NOUVELLE LIGNE : icône preview + chemin cible
                lo_masterSetDress = QHBoxLayout()

                self.lbl_setDressThumbnail = QLabel()
                self.lbl_setDressThumbnail.setFixedSize(64, 64)
                self.lbl_setDressThumbnail.setScaledContents(True)

                self.lbl_setDressPath = QLabel("")
                self.lbl_setDressPath.setWordWrap(True)

                lo_masterSetDress.addWidget(self.lbl_setDressThumbnail)
                lo_masterSetDress.addWidget(self.lbl_setDressPath)
                lo_masterSetDress.addStretch()
                lo_setDress.addLayout(lo_masterSetDress)

                # # Remplissage avec les vraies données
                thumbnailPath = self.getMasterSetDressThumbnail(entity)
                targetPath = self.getMasterSetDress(entity)

                if targetPath:
                    self.lbl_setDressPath.setText("SetDress found")
                    self.lbl_setDressPath.setToolTip(f"<span>{targetPath}</span>")
                else:
                    self.lbl_setDressPath.setText("No SetDress USD file found")
                    self.lbl_setDressPath.setToolTip("")

                if thumbnailPath and os.path.isfile(thumbnailPath):
                    pixmap = QPixmap(thumbnailPath)
                    self.lbl_setDressThumbnail.setPixmap(pixmap)
                else:
                    self.lbl_setDressThumbnail.setText("N/A")
                    self.lbl_setDressThumbnail.setAlignment(Qt.AlignCenter)

                rightColumnLayout.addWidget(self.gb_setDress)
                self.gb_setDress.setFixedHeight(100)

            # BOTTOM RIGHT (ou seul élément si pas RLO) : Selected Assets
            self.gb_selectedAssets = QGroupBox("Selected Assets")
            lo_selectedAssets = QVBoxLayout()
            self.gb_selectedAssets.setLayout(lo_selectedAssets)
            self.lw_selectedAssets = SelectedAssetsList(self)
            lo_selectedAssets.addWidget(self.lw_selectedAssets)
            rightColumnLayout.addWidget(self.gb_selectedAssets)
            rightColumnLayout.setStretch(0, 0)  # gb_setDress : ne stretch pas
            rightColumnLayout.setStretch(1, 1)

            # BOTTOM : Validate Button
            self.btn_validate = QPushButton("Validate")
            self.btn_validate.clicked.connect(self.onValidateAssetsBrowser)
            mainLayout.addWidget(self.btn_validate)

            result = self.assetBrowserDlg.exec_()  # bloquant, remplace .show()
            return self.toImportAsset if result == QDialog.Accepted else []

        except Exception as e:
            self.core.popup("Erreur AssetBrowser: %s" % e)
            return []

    def onAssetsDropped(self):
        
        #-----------------------------------------------------------------------------------#
        # Add asset to the 'Selected Assets' list then refresh list                         #
        #-----------------------------------------------------------------------------------#

        entities = self.w_entities.getCurrentData(returnOne=False)
        entities = [e for e in entities if e["type"] == "asset"]

        for entity in entities:
            key = entity.get("asset_path")
            if key and key not in self.selectedAssetsData:
                self.selectedAssetsData[key] = entity

        self.refreshSelectedAssetsList()

    def refreshSelectedAssetsList(self):
         
        #-----------------------------------------------------------------------------------#
        # Refresh the 'Selected Assets' list                                                #
        #-----------------------------------------------------------------------------------#

        self.lw_selectedAssets.clear()
        self.lw_selectedAssets.setIconSize(QSize(50, 50))

        assets = list(self.selectedAssetsData.values())
        if not assets:
            return

        nodes = {}
        for entity in assets:
            relPath = entity.get("asset_path", "")
            parts = relPath.replace("\\", "/").split("/")

            parent = self.lw_selectedAssets
            currentPath = ""
            for i, part in enumerate(parts):
                currentPath = os.path.join(currentPath, part)
                if currentPath not in nodes:
                    if parent is self.lw_selectedAssets:
                        node = QTreeWidgetItem(self.lw_selectedAssets, [part])
                    else:
                        node = QTreeWidgetItem(parent, [part])
                    nodes[currentPath] = node
                else:
                    node = nodes[currentPath]

                if i == len(parts) - 1:
                    node.setData(0, Qt.UserRole, entity)
                    pm = self.core.entities.getEntityPreview(entity)
                    if not pm:
                        pm = self.core.media.emptyPrvPixmap
                    node.setIcon(0, QIcon(pm))

                parent = node

        self.lw_selectedAssets.expandAll()

    def onRemoveSelectedAssets(self, items):
         
        #-----------------------------------------------------------------------------------#
        # Delete asset to the 'Selected Assets' list then refresh list                      #
        #-----------------------------------------------------------------------------------#

        for item in items:
            entity = item.data(0, Qt.UserRole)
            if not entity:
                continue  # c'est un dossier, pas un asset - on ignore
            key = entity.get("asset_path")
            if key in self.selectedAssetsData:
                del self.selectedAssetsData[key]
        self.refreshSelectedAssetsList()

    def onValidateAssetsBrowser(self):
         
        #-----------------------------------------------------------------------------------------#
        # toImportAsset is the output list of selected asset in the Asset Browser                 #
        #       with their asset_path as a dictionary                                             #
        # Return toImportAsset                                                                    #
        #-----------------------------------------------------------------------------------------#

        toImportAsset = []
        for entity in self.selectedAssetsData.values():
            name = entity.get("asset", "")
            assetPath = entity.get("asset_path", "")
            # path = entity.get("paths", "")
            toImportAsset.append({"name": name, "asset_path": assetPath})

        # Check the toImportAsset before creating the scene
        # self.core.popup(f"Selected assets: {toImportAsset}")
        self.toImportAsset = toImportAsset          # stocké pour la fonction appelante
        self.assetBrowserDlg.accept()               # ferme le dialogue proprement (au lieu de .hide())
    
    def getMasterSetDress(self, entity):
        #-----------------------------------------------------------------------------------#
        # Get the SetDress USD for the current shot                                         #
        # Import entity to find the right shot                                              #
        #-----------------------------------------------------------------------------------#

        # Redirecting toward the master SetDress file
        sequence = entity.get("sequence", "") if entity else ""
        targetFile = f"{sequence}_SetDress_master.usda"
        shotPath = self.core.getEntityPath(entity)

        seqFolder = os.path.dirname(shotPath)
        targetPath = os.path.join(seqFolder, "MASTER/Export/SetDress/master", targetFile)
        targetPath = os.path.normpath(targetPath)

        return targetPath if os.path.isfile(targetPath) else None
    
    def getMasterSetDressThumbnail(self, entity):
        #-----------------------------------------------------------------------------------#
        # Get the thumbnail for the SetDress USD for the current shot                       #
        # Import entity to find the right shot                                              #
        # CURRENTLY NOT WORKING                                                             #
        #-----------------------------------------------------------------------------------#
        sequence = entity.get("sequence", "") if entity else ""
        shotPath = self.core.getEntityPath(entity)
        seqFolder = os.path.dirname(shotPath)

        setDressFolder = os.path.normpath(
            os.path.join(shotPath, "Scenefiles/01_setDress/SetDress/")
        )

    

        if not os.path.isdir(setDressFolder):
            return None

        # Scan manuel du dossier pour trouver la dernière version
        pattern = re.compile(rf"{re.escape(sequence)}_SetDress_v(\d+)preview\.jpg", re.IGNORECASE)

        matches = []
        for fname in os.listdir(setDressFolder):
            m = pattern.match(fname)
            if m:
                versionNum = int(m.group(1))
                matches.append((versionNum, fname))

        if not matches:
            return None
        self.core.popup("working here")
        matches.sort(key=lambda x: x[0])
        latestVersion, latestFile = matches[-1]
        previewPath = os.path.join(setDressFolder, latestFile)
        previewPath = os.path.normpath(previewPath)

        self.core.popup(previewPath)

        return previewPath if os.path.isfile(previewPath) else None
