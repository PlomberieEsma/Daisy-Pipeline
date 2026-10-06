import os
import glob

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QPushButton, QHeaderView
)

# Compatibilité Qt5 / Qt6 pour la case tri-état
_AUTO_TRISTATE = getattr(Qt, "ItemIsAutoTristate", None) or getattr(Qt, "ItemIsTristate")

THUMB_SIZE = QSize(100, 56)


# Ordre croissant d'avancement : du premier niveau au dernier.
# Chaque niveau = (label, [motifs glob relatifs au dossier du shot])
# À ADAPTER à ton arborescence réelle.
TASK_LEVELS = [
    ("Animatic",    ["Scenefiles/Animatic/*/*.*"]),
    ("Layout",      ["Renders/2dRender/@department@/*.usd"]),
    ("Anim",        ["Renders/2dRenderAnimation/*/*.ma"]),
    ("Render",      ["Renders/2dRender/*.hip*"]),
    ("Compo",       ["Renders/2dRender/*.*"]),
    ("Etalonnage",  ["Renders/2dRender/*.nk"]),
]

NO_LEVEL = "-"


class ShotBrowserUI(object):
    def __init__(self, core, plugin=None):
        self.core = core
        self.plugin = plugin
        self.toImportShot = []

    def onShotBrowserTriggered(self, task=""):
        self.toImportShot = []

        try:
            self.dlg = QDialog()
            self.core.parentWindow(self.dlg)
            self.dlg.setWindowTitle("Shot Browser")
            self.dlg.resize(650, 650)

            layout = QVBoxLayout(self.dlg)

            if task:
                lo_ctx = QHBoxLayout()
                lbl = QLabel("Current Task :")
                lbl.setStyleSheet("font-weight: bold;")
                lo_ctx.addWidget(lbl)
                lo_ctx.addWidget(QLabel(str(task)))
                lo_ctx.addStretch()
                layout.addLayout(lo_ctx)

            # Recherche + cocher/décocher tout
            lo_top = QHBoxLayout()
            self.e_search = QLineEdit()
            self.e_search.setPlaceholderText("Filtrer les shots...")
            self.e_search.textChanged.connect(self.filterTree)
            lo_top.addWidget(self.e_search)

            b_all = QPushButton("Tout cocher")
            b_all.clicked.connect(lambda: self.setAllChecked(Qt.Checked))
            b_none = QPushButton("Tout décocher")
            b_none.clicked.connect(lambda: self.setAllChecked(Qt.Unchecked))
            lo_top.addWidget(b_all)
            lo_top.addWidget(b_none)
            layout.addLayout(lo_top)

            # Arbre Séquence > Shots, avec colonnes d'infos
            self.tw_shots = QTreeWidget()
            self.tw_shots.setColumnCount(3)
            self.tw_shots.setHeaderLabels(["Shot", "Thumbnail", "Task Level"])
            self.tw_shots.setIconSize(THUMB_SIZE)
            self.tw_shots.setUniformRowHeights(False)
            header = self.tw_shots.header()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            layout.addWidget(self.tw_shots)

            self.populateTree()

            self.btn_validate = QPushButton("Validate")
            self.btn_validate.clicked.connect(self.onValidate)
            layout.addWidget(self.btn_validate)

            result = self.dlg.exec_()
            return self.toImportShot if result == QDialog.Accepted else []

        except Exception as e:
            self.core.popup("Erreur ShotBrowser: %s" % e)
            return []

    # ------------------------------------------------------------------ #
    def getShotFolder(self, entity):
        """Dossier racine du shot sur le disque."""
        try:
            return self.core.getEntityPath(entity=entity)
        except Exception:
            return None

    def getTaskLevel(self, entity):
        """
        Renvoie le label du dernier niveau (dans l'ordre de TASK_LEVELS)
        pour lequel au moins un fichier existe, sinon NO_LEVEL.
        """
        shotFolder = self.getShotFolder(entity)
        print(shotFolder)
        if not shotFolder or not os.path.isdir(shotFolder):
            return NO_LEVEL

        # On parcourt à l'envers : le premier niveau trouvé est le plus avancé,
        # ce qui évite de scanner tous les niveaux inférieurs.
        for label, patterns in reversed(TASK_LEVELS):
            for pattern in patterns:
                fullPattern = os.path.join(shotFolder, pattern)
                print(fullPattern)
                # iglob + next : on s'arrête dès le premier fichier trouvé
                if next(glob.iglob(fullPattern), None) is not None:
                    return label

        return NO_LEVEL


    def getShotInfos(self, entity):
        """Renvoie les infos affichées dans les colonnes. À adapter."""
        taskLevel = self.getTaskLevel(entity)

        pm = None
        try:
            pm = self.core.entities.getEntityPreview(entity)
        except Exception:
            pass
        if not pm:
            pm = self.core.media.emptyPrvPixmap
        pm = pm.scaled(THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return {"taskLevel": str(taskLevel), "pixmap": pm}

    def populateTree(self):
        self.tw_shots.clear()

        shots = self.core.entities.getShots() or []

        sequences = {}
        for entity in shots:
            sequences.setdefault(entity.get("sequence", ""), []).append(entity)

        for seq in sorted(sequences):
            seqItem = QTreeWidgetItem(self.tw_shots, [seq or "(sans séquence)"])
            seqItem.setFlags(seqItem.flags() | Qt.ItemIsUserCheckable | _AUTO_TRISTATE)
            font = seqItem.font(0)
            font.setBold(True)
            seqItem.setFont(0, font)

            for entity in sorted(sequences[seq], key=lambda e: e.get("shot", "")):
                infos = self.getShotInfos(entity)

                shotItem = QTreeWidgetItem(seqItem, [entity.get("shot", ""), "", infos["taskLevel"]])
                shotItem.setFlags(shotItem.flags() | Qt.ItemIsUserCheckable)
                shotItem.setCheckState(0, Qt.Checked)
                shotItem.setIcon(1, QIcon(infos["pixmap"]))
                shotItem.setSizeHint(1, THUMB_SIZE)
                shotItem.setData(0, Qt.UserRole, entity)

            # Le tri-état se met à jour à partir des enfants (tous cochés)
            seqItem.setCheckState(0, Qt.Checked)

        self.tw_shots.expandAll()

    # ------------------------------------------------------------------ #
    def setAllChecked(self, state):
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            if not seqItem.isHidden():
                seqItem.setCheckState(0, state)

    def filterTree(self, text):
        text = text.lower()
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            seqMatch = text in seqItem.text(0).lower()
            visible = 0
            for j in range(seqItem.childCount()):
                child = seqItem.child(j)
                match = seqMatch or text in child.text(0).lower()
                child.setHidden(not match)
                visible += match
            seqItem.setHidden(visible == 0)

    def onValidate(self):
        result = []
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            for j in range(seqItem.childCount()):
                child = seqItem.child(j)
                if child.isHidden() or child.checkState(0) != Qt.Checked:
                    continue
                entity = child.data(0, Qt.UserRole)
                seq = entity.get("sequence", "")
                shot = entity.get("shot", "")
                result.append({
                    "name": shot,
                    "sequence": seq,
                    "shot_path": "%s/%s" % (seq, shot) if seq else shot,
                    "taskLevel": child.text(2),
                })

        self.toImportShot = result
        self.dlg.accept()

    