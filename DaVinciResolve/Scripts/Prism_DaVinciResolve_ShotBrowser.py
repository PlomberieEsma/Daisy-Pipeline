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
import re
import os

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

class ShotBrowserUI(object):
    def __init__(self, core, plugin = None):
        self.core = core
        self.plugin = plugin

    def onShotBrowserTriggered(self, task):
        
        #-----------------------------------------------------------------------------------#
        # Window Shot Browser to select Shots to load into a scene during layout          #
        # If opened from Task SetDress, simple double column view                           #
        # If opened from Task RLO, the SetDress USD file is already being selected          #
        #       only need to select Char and Props
        # Entity imported for shot and sequence 
        #-----------------------------------------------------------------------------------#

        # self.core.popup("Current entity: %s" % entity)

        self.toImportShot = []  # valeur par défaut si l'utilisateur ferme sans valider

        try:
            allShotPaths = self.core.entities.getShots()
            self.shotRoot = os.path.commonpath(allShotPaths) if allShotPaths else ""
            
            self.shotBrowserDlg = QDialog()
            self.core.parentWindow(self.shotBrowserDlg)
            self.shotBrowserDlg.setWindowTitle("Shot Browser")
            self.shotBrowserDlg.resize(700, 600)

            # Set Window Icon
            iconPath = os.path.join(
                self.core.projectPath,
                "00_Pipeline", "Plugins", "Daisy_Pipe", "Integration", "ui", "daisy_logo.png"
            )
            iconPath = os.path.normpath(iconPath)

            if os.path.isfile(iconPath):
                self.shotBrowserDlg.setWindowIcon(QIcon(iconPath))
            else:
                self.core.popup("Icône introuvable: %s" % iconPath)

            mainLayout = QVBoxLayout(self.shotBrowserDlg)

            # NOUVELLE LIGNE TOUT EN HAUT : rappel Séquence / Shot
            
            lo_context = QHBoxLayout()
            lbl_context = QLabel("Sequence / Shot :")
            lbl_context.setStyleSheet("font-weight: bold;")

            self.lbl_contextValue = QLabel(f"Current Task {task}")

            lo_context.addWidget(lbl_context)
            lo_context.addWidget(self.lbl_contextValue)
            lo_context.addStretch()
            mainLayout.addLayout(lo_context)

            columnsLayout = QHBoxLayout()
            mainLayout.addLayout(columnsLayout)

            # LEFT COLUMN : Prism Shot List
            import EntityWidget
            self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
            # Keep only necessary and hide shots
            self.w_entities.tb_entities.setVisible(False)
            self.w_entities.getPage("Shots").tw_tree.setDragEnabled(True)
            self.selectedShotsData = {}  # clé = shot_path (unique), valeur = entity dict
            columnsLayout.addWidget(self.w_entities)

            # RIGHT COLUMN : conteneur vertical (SetDress + Selected Shots)
            rightColumnLayout = QVBoxLayout()
            columnsLayout.addLayout(rightColumnLayout)

            # BOTTOM RIGHT (ou seul élément si pas RLO) : Selected Shots
            self.gb_selectedShots = QGroupBox("Selected Shots")
            lo_selectedShots = QVBoxLayout()
            self.gb_selectedShots.setLayout(lo_selectedShots)
            self.lw_selectedShots = SelectedShotsList(self)
            lo_selectedShots.addWidget(self.lw_selectedShots)
            rightColumnLayout.addWidget(self.gb_selectedShots)
            rightColumnLayout.setStretch(0, 0)  # gb_setDress : ne stretch pas
            rightColumnLayout.setStretch(1, 1)

            # BOTTOM : Validate Button
            self.btn_validate = QPushButton("Validate")
            self.btn_validate.clicked.connect(self.onValidateShotsBrowser)
            mainLayout.addWidget(self.btn_validate)

            result = self.shotBrowserDlg.exec_()  # bloquant, remplace .show()
            return self.toImportShot if result == QDialog.Accepted else []

        except Exception as e:
            self.core.popup("Erreur ShotBrowser: %s" % e)
            return []

    def onShotsDropped(self):
        
        #-----------------------------------------------------------------------------------#
        # Add Shot to the 'Selected Shots' list then refresh list                         #
        #-----------------------------------------------------------------------------------#

        entities = self.w_entities.getCurrentData(returnOne=False)
        entities = [e for e in entities if e["type"] == "shot"]

        for entity in entities:
            key = entity.get("shot_path")
            if key and key not in self.selectedShotsData:
                self.selectedShotsData[key] = entity

        self.refreshSelectedShotsList()

    def refreshSelectedShotsList(self):
         
        #-----------------------------------------------------------------------------------#
        # Refresh the 'Selected Shots' list                                                #
        #-----------------------------------------------------------------------------------#

        self.lw_selectedShots.clear()
        self.lw_selectedShots.setIconSize(QSize(50, 50))

        shots = list(self.selectedShotsData.values())
        if not shots:
            return

        nodes = {}
        for entity in shots:
            relPath = entity.get("shot_path", "")
            parts = relPath.replace("\\", "/").split("/")

            parent = self.lw_selectedShots
            currentPath = ""
            for i, part in enumerate(parts):
                currentPath = os.path.join(currentPath, part)
                if currentPath not in nodes:
                    if parent is self.lw_selectedShots:
                        node = QTreeWidgetItem(self.lw_selectedShots, [part])
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

        self.lw_selectedShots.expandAll()

    def onRemoveSelectedShots(self, items):
         
        #-----------------------------------------------------------------------------------#
        # Delete Shot to the 'Selected Shots' list then refresh list                      #
        #-----------------------------------------------------------------------------------#

        for item in items:
            entity = item.data(0, Qt.UserRole)
            if not entity:
                continue  # c'est un dossier, pas un shot - on ignore
            key = entity.get("shot_path")
            if key in self.selectedShotsData:
                del self.selectedShotsData[key]
        self.refreshSelectedShotsList()

    def onValidateShotsBrowser(self):
         
        #-----------------------------------------------------------------------------------------#
        # toImportShot is the output list of selected Shot in the Shot Browser                 #
        #       with their Sshot_path as a dictionary                                             #
        # Return toImportShot                                                                    #
        #-----------------------------------------------------------------------------------------#

        toImportShot = []
        for entity in self.selectedShotsData.values():
            name = entity.get("shot", "")
            shotPath = entity.get("shot_path", "")
            # path = entity.get("paths", "")
            toImportShot.append({"name": name, "shot_path": shotPath})

        # Check the toImportShot before creating the scene
        # self.core.popup(f"Selected shots: {toImportShot}")
        self.toImportShot = toImportShot          # stocké pour la fonction appelante
        self.shotBrowserDlg.accept()               # ferme le dialogue proprement (au lieu de .hide())