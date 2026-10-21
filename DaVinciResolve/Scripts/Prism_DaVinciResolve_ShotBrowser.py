"""Shot Browser Prism pour DaVinci Resolve.

Permet de choisir des shots Prism, de les poser sur la timeline (modes "add",
"bake" et "modify") et de piloter par expressions Fusion les compteurs
affichés par-dessus (séquence, shot, task level, date, nom du film).

Chaque clip posé reçoit un marqueur dont le customData JSON décrit le shot
(sequence, shot, taskLevel, mediaPath, length) : getTimelineShots relit ces
marqueurs pour retrouver les shots déjà présents sur la timeline.
"""

import os
import glob
import re
import json
import time

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QPushButton, QHeaderView, QComboBox
)

# Compatibilité Qt5 / Qt6 pour la case tri-état
_AUTO_TRISTATE = getattr(Qt, "ItemIsAutoTristate", None) or getattr(Qt, "ItemIsTristate")

THUMB_SIZE = QSize(100, 56)


##############################################################################################################
###########################     Sequence and Shots     #######################################################
##############################################################################################################

SEQ_TOOL, SEQ_INPUT = "SeqCounter", "Number"
SHOT_TOOL, SHOT_INPUT = "ShotCounter", "Number"


# Ordre croissant d'avancement : du premier niveau au dernier.
# Chaque niveau = (label, [motifs glob relatifs au dossier du shot])
TASK_LEVELS = [
    ("Layout",      ["Playblasts/02_layout/Layout/*/*"]),
    ("Anim",        ["Playblasts/03_anim/Animation/*/*"]),
    ("Lighting",    ["Renders/3dRender/07_lighting/Lighting/*/*_beauty.*"]),
    ("Compositing", ["Renders/2dRender/08_compositing/Compositing/*/*"]),
]
# Si le nom du projet Resolve contient ce mot, on ne cherche que ces niveaux
LAYOUT_PROJECT_KEYWORD = "layout"
LAYOUT_PROJECT_LEVELS = ("Layout", "Anim")

MASTER_ONLY_LEVEL = "Layout" 
NO_LEVEL = "-"
TASK_LETTERS = {
    "Layout": "Ly",
    "Anim": "A",
    "Lighting": "Lg",
    "Compositing": "C",
}

def naturalKey(s):
    # sh2 avant sh10
    """Clé de tri naturel : "sh2" passe avant "sh10".

    Args:
        s: chaîne à trier.

    Returns:
        list: morceaux de texte (minuscules) et d'entiers, utilisable dans sorted(key=...).
    """
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def tcToFrames(tc, fps):
    # Timecode "HH:MM:SS:FF" -> frame absolu (drop-frame non géré)
    """Convertit un timecode en numéro d'image absolu (drop-frame non géré).

    Args:
        tc: timecode "HH:MM:SS:FF" (ou avec ";" comme séparateur).
        fps: cadence de la timeline (arrondie à l'entier).

    Returns:
        int: numéro d'image.
    """
    h, m, s, f = [int(x) for x in re.split(r"[:;]", tc)]
    return (h * 3600 + m * 60 + s) * int(round(fps)) + f

def levelIndex(label):
    """Position d'un niveau d'avancement dans TASK_LEVELS (0 = Layout, le moins avancé).

    Args:
        label: nom du niveau ("Layout", "Anim", "Lighting", "Compositing").

    Returns:
        int: index dans TASK_LEVELS, ou -1 si le niveau est inconnu.
    """
    labels = [l for l, _ in TASK_LEVELS]
    return labels.index(label) if label in labels else -1

def versionNumber(path):
    # .../Layout/v0003/fichier -> 3
    """Numéro de version déduit du dossier parent du fichier.
    Ex. ".../Layout/v0003/fichier.png" -> 3.

    Args:
        path: chemin d'un fichier de média.

    Returns:
        int: numéro de version, ou 0 si le chemin est vide ou le dossier parent
        n'est pas de la forme vNNNN.
    """
    if not path:
        return 0
    m = re.match(r"^v(\d+)$", os.path.basename(os.path.dirname(path)), re.I)
    return int(m.group(1)) if m else 0

def rank(label, path):
    """Rang d'une version, pour comparer deux versions (niveau d'abord, puis numéro).

    Args:
        label: niveau d'avancement ("Layout", "Anim"...).
        path: chemin du média (sert à lire le numéro de version).

    Returns:
        tuple[int, int]: (levelIndex(label), versionNumber(path)).
    """
    return (levelIndex(label), versionNumber(path))

def rankText(label, path):
    """Texte affiché pour une version, ex. "Anim v0003".

    Args:
        label: niveau d'avancement.
        path: chemin du média (sert à lire le numéro de version).

    Returns:
        str: "<label> v<numéro sur 4 chiffres>".
    """
    return "%s v%04d" % (label, versionNumber(path))



##############################################################################################################
###########################     DaVinci Fusion Composition Visual Template     ###############################
##############################################################################################################

COUNTER_BASE = 1    # 1 : la 1re frame s'affiche " - 0001" ; 0 : " - 0000"
COUNTERS = [
    ("SqName",     "name",     "seq"),
    ("SqFrame",    "frame",    "seq"),
    ("ShName",     "name",     "shot"),
    ("ShFrame",    "frame",    "shot"),
    ("TaskLevel",  "task",     "shot"),
    ("TaskDate",   "date",     "shot"),       # date du fichier
    ("FilmName",   "project",  "project"),    # nom du projet, constant
]

# Texte affiché par défaut sur chaque node après réinitialisation
COUNTER_DEFAULTS = {
    "SqName":    "Sq----",
    "SqFrame":   " - 0000",
    "ShName":    "Sh----",
    "ShFrame":   " - 0000",
    "TaskLevel": "-",
    "TaskDate":  "--/--/--",
    "FilmName":  "Film",
}

def counterExpression(rows, mode):
    """Construit l'expression Lua (Fusion) d'un compteur texte : selon la frame
    courante, renvoie le texte de la ligne dont la plage contient cette frame, ou
    "" hors de toute plage.

    Args:
        rows: liste de tuples (début, fin, ref, label), en frames relatives au
            clip Fusion ; fin exclue. ref sert au mode compteur, label aux modes
            texte.
        mode: "name" ou "date" -> affiche label tel quel ; "task" -> affiche la
            lettre de TASK_LETTERS pour label ; "duration" -> durée "N f"
            (non utilisé par COUNTERS) ; toute autre valeur (ex. "frame") ->
            compteur " - 0001" depuis ref (voir COUNTER_BASE).

    Returns:
        str: expression Lua à passer à SetExpression.
    """
    if mode in ("name", "date"):
        table = ",".join("{%d,%d,%s}" % (s, e, luaStr(label)) for s, e, ref, label in rows)
        result = "r[3]"
    elif mode == "duration":
        table = ",".join("{%d,%d,%d}" % (s, e, e - s) for s, e, ref, label in rows)
        result = 'string.format("%d f", r[3])'
    elif mode == "task":
        table = ",".join("{%d,%d,%s}" % (s, e, luaStr(TASK_LETTERS.get(label, label[:1].upper())))
                         for s, e, ref, label in rows)
        result = "r[3]"
    else:
        table = ",".join("{%d,%d,%d}" % (s, e, ref) for s, e, ref, label in rows)
        result = 'string.format(" - %%04d", t - r[3] + %d)' % COUNTER_BASE
    return ("(function() local t = math.floor(time + 0.5) "
            "for _, r in ipairs({" + table + "}) do "
            "if t >= r[1] and t < r[2] then return " + result + " end end "
            "return '' end)()")

def sqLabel(seq):
    # "sq010" -> "Sq010"
    """Texte affiché pour une séquence : première lettre en majuscule.
    Ex. "sq010" -> "Sq010".

    Args:
        seq: nom de la séquence Prism.

    Returns:
        str: libellé de la séquence.
    """
    return seq[:1].upper() + seq[1:]

def shLabel(shotPath):
    # "sq010/sh020" -> "Sh0020"  (format à confirmer)
    """Texte affiché pour un shot : "Sh" + numéro sur 4 chiffres.
    Ex. "sq010/sh020" -> "Sh0020".

    Args:
        shotPath: chemin "sequence/shot" ; seul le dernier élément est lu.

    Returns:
        str: libellé du shot, "Sh----" si le nom ne contient aucun chiffre.
    """
    shot = shotPath.split("/")[-1]
    digits = re.sub(r"\D", "", shot)
    return "Sh%04d" % int(digits) if digits else "Sh----"

def getInput(tool, inputId):
    """Retrouve une entrée (input) d'un node Fusion par son identifiant.

    Args:
        tool: node Fusion.
        inputId: identifiant de l'input (INPS_ID), ex. "StyledText", "TopLeftRed".

    Returns:
        L'input Fusion, ou None s'il n'existe pas.
    """
    for _, inp in tool.GetInputList().items():
        if inp.GetAttrs().get("INPS_ID") == inputId:
            return inp
    return None

SHOTINFO_REL = os.path.join("00_Pipeline", "Shotinfo", "shotInfo.json")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".dpx", ".tga", ".bmp", ".webp"}

def luaStr(s):
    # Chaîne Lua sûre (guillemets et antislashs échappés)
    """Transforme un texte en chaîne Lua sûre (guillemets et antislashs échappés).

    Args:
        s: texte quelconque.

    Returns:
        str: littéral Lua entre guillemets.
    """
    return '"%s"' % str(s).replace("\\", "\\\\").replace('"', '\\"')

def constantExpression(text):
    """Expression Lua Fusion qui renvoie toujours le même texte.

    Args:
        text: texte à afficher.

    Returns:
        str: expression à passer à SetExpression.
    """
    return "(function() return %s end)()" % luaStr(text)

# TaskLevel BackGround
TASK_BG_NODE = "Bg_TaskLevel"
TASK_COLORS = {
    "Layout":       (0.65, 0.15, 0.00),
    "Anim":         (0.65, 0.55, 0.00),
    "Lighting":     (0.05, 0.65, 0.00),
    "Compositing":  (0.00, 0.50, 0.65),
}
NO_LEVEL_COLOR = (0.40, 0.40, 0.40) 
BG_CHANNELS = (("TopLeftRed", 0), ("TopLeftGreen", 1), ("TopLeftBlue", 2))

def numberExpression(table, default):
    """Comme counterExpression, mais pour un nombre (ex. un canal de couleur).

    Args:
        table: liste de tuples (début, fin, valeur), en frames relatives au clip
            de la comp ; fin exclue ; la première plage qui correspond gagne.
        default: valeur renvoyée hors de toute plage.

    Returns:
        str: expression Lua à passer à SetExpression.
    """
    rows = ",".join("{%d,%d,%.4f}" % (s, e, v) for s, e, v in table)
    return ("(function() local t = math.floor(time + 0.5) "
            "for _, r in ipairs({" + rows + "}) do "
            "if t >= r[1] and t < r[2] then return r[3] end end "
            "return %.4f end)()" % default)

# TaskLevel Date
def fileDateText(path):
    """Date de modification d'un fichier, au format AA/MM/JJ (ex. "26/10/13").

    Args:
        path: chemin du fichier.

    Returns:
        str: la date, ou "" si le fichier est illisible.
    """
    try:
        return time.strftime("%y/%m/%d", time.localtime(os.path.getmtime(path)))
    except Exception:
        return ""

# Film Name
def getFilmName(core):
    """Nom du film : nom du projet Prism sans préfixe numérique du type "12_".

    Args:
        core: core Prism (projectName, sinon dernier dossier de projectPath).

    Returns:
        str: nom du film.
    """
    name = getattr(core, "projectName", None) or os.path.basename(os.path.normpath(core.projectPath))
    return re.sub(r"^\d+_", "", str(name))

MASTER_TRACK_NAME = "Sequence Master"

class ShotBrowserUI(object):
    """Fenêtre Shot Browser et logique de pose des shots sur la timeline Resolve.

    Trois modes (self.action) :
    - "add"    : ajoute les shots cochés sur une nouvelle piste, à la position du curseur ;
    - "bake"   : remplace les shots de la timeline par une version plus avancée ;
    - "modify" : remplace les shots de la timeline par la version choisie à la main.

    Sections de la classe : interface (onShotBrowserTriggered, populateTree,
    filterTree...), disque et versions (getShotMedia, getShotVersions...), pose des
    clips (placeShot, placeHeldShot...), piste Master (syncMasterTrack...) et
    compteurs Fusion (updateFrameCounters...).
    """
    def __init__(self, core, plugin=None):
        """Args:
            core: core Prism (projectPath, entities, popup, parentWindow...).
            plugin: plugin Prism, optionnel (conservé mais non utilisé).
        """
        self.core = core
        self.plugin = plugin
        self.toImportShot = []

    def onShotBrowserTriggered(self, task="", action="add"):
        """Point d'entrée : prépare et affiche la fenêtre Shot Browser (en mode modal).

        La pose ou la mise à jour des clips est exécutée dans onValidate, avant le
        retour de cette méthode. Affiche aussi dans la console la ligne de définition
        de quelques méthodes (diagnostic de version du fichier chargé).

        Args:
            task: task de montage affichée en en-tête ("Current Task"), optionnel.
            action: "add", "bake" ou "modify" ; toute autre valeur équivaut à "add".
                Les modes "bake" et "modify" lisent la timeline et n'affichent que
                les shots déjà posés.

        Returns:
            list[dict]: les shots validés, chacun de la forme {"name", "sequence",
            "shot_path", "taskLevel", "mediaPath"} ; [] si annulé, si la timeline est
            vide, s'il n'y a rien à faire ou en cas d'erreur (affichée dans un popup).
        """
        import inspect
        for name in ("addShotsToTimeline", "placeShot", "updateFrameCounters", "bakeShotsOnTimeline"):
            try:
                fn = getattr(self, name)
                print("[ShotBrowser] %s -> %s : ligne %d"
                      % (name, inspect.getsourcefile(fn), inspect.getsourcelines(fn)[1]))
            except Exception as e:
                print("[ShotBrowser] %s -> ABSENTE (%s)" % (name, e))
        self.toImportShot = []
        self.action = action if action in ("add", "bake", "modify") else "add"
        self.timelineMode = self.action in ("bake", "modify")   # modes qui lisent la timeline
        self.onTimeline = {}

        try:
            if self.timelineMode:
                resolve = self.getResolve()
                project = resolve.GetProjectManager().GetCurrentProject() if resolve else None
                timeline = project.GetCurrentTimeline() if project else None
                if not timeline:
                    self.core.popup("Aucune timeline active.")
                    return []
                self.onTimeline = self.getTimelineShots(timeline)
                if not self.onTimeline:
                    self.core.popup("Aucun shot du Shot Browser trouvé sur la timeline.")
                    return []

            titles = {"add": "Add", "bake": "Bake", "modify": "Modify"}
            self.dlg = QDialog()
            self.core.parentWindow(self.dlg)
            self.dlg.setWindowTitle("Shot Browser - %s" % titles[self.action])
            self.dlg.resize(750, 650)

            iconPath = os.path.join(
                self.core.projectPath,
                "00_Pipeline", "Plugins", "DaVinciResolve", "Resources", "daisy_logo.png"
            )
            iconPath = os.path.normpath(iconPath)
            if os.path.isfile(iconPath):
                self.dlg.setWindowIcon(QIcon(iconPath))
            else:
                print("Prism: icône introuvable : %s" % iconPath)

            layout = QVBoxLayout(self.dlg)

            if task:
                lo_ctx = QHBoxLayout()
                lbl = QLabel("Current Task :")
                lbl.setStyleSheet("font-weight: bold;")
                lo_ctx.addWidget(lbl)
                lo_ctx.addWidget(QLabel(str(task)))
                lo_ctx.addStretch()
                layout.addLayout(lo_ctx)

            self.cb_masters = QCheckBox("Afficher les MASTER")
            self.cb_masters.setChecked(False)                  # décoché par défaut
            self.cb_masters.toggled.connect(self.filterTree)
            layout.addWidget(self.cb_masters)

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

            self.tw_shots = QTreeWidget()
            if self.timelineMode:
                lastCol = "Nouveau" if self.action == "bake" else "Version à poser"
                headers = ["Shot", "Thumbnail", "Actuel (timeline)", lastCol]
            else:
                headers = ["Shot", "Thumbnail", "Task Level"]
            self.tw_shots.setColumnCount(len(headers))
            self.tw_shots.setHeaderLabels(headers)
            self.tw_shots.setIconSize(THUMB_SIZE)
            self.tw_shots.setUniformRowHeights(False)
            header = self.tw_shots.header()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, len(headers)):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            if self.timelineMode:
                header.setSectionResizeMode(3, QHeaderView.Interactive)
                self.tw_shots.setColumnWidth(3, 200)
            layout.addWidget(self.tw_shots)

            count = self.populateTree()
            self.filterTree()
            if self.timelineMode and count == 0:
                if self.action == "bake":
                    self.core.popup("Tous les shots de la timeline sont à jour.")
                else:
                    self.core.popup("Aucun shot de la timeline n'a été retrouvé dans le projet.")
                return []

            labels = {"add": "Add to new track", "bake": "Bake", "modify": "Apply"}
            self.btn_validate = QPushButton(labels[self.action])
            self.btn_validate.clicked.connect(self.onValidate)
            layout.addWidget(self.btn_validate)
            

            result = self.dlg.exec_()
            return self.toImportShot if result == QDialog.Accepted else []

        except Exception as e:
            self.core.popup("Erreur ShotBrowser: %s" % e)
            return []

    # ------------------------------------------------------------------ #
    def getShotFolder(self, entity):
        """Dossier d'un shot : <projet>/03_Production/Shots/<séquence>/<shot>.

        Args:
            entity: entité Prism du shot, dict avec les clés "sequence" et "shot".

        Returns:
            str | None: le dossier ; à défaut, le chemin résolu par
            core.getEntityPath ; None si le shot n'a pas de nom ou si rien n'est trouvé.
        """
        seq = entity.get("sequence", "")
        shot = entity.get("shot", "")
        if not shot:
            return None

        folder = os.path.join(self.core.projectPath, "03_Production", "Shots", seq, shot)
        if os.path.isdir(folder):
            return folder

        # Plan B : laisser Prism résoudre le chemin
        try:
            return self.core.getEntityPath(entity=entity)
        except Exception:
            return None

    def getTaskLevel(self, entity):
        """Niveau d'avancement le plus avancé existant sur disque pour un shot,
        parmi les niveaux de getActiveTaskLevels().

        Args:
            entity: entité Prism du shot.

        Returns:
            str: "Layout", "Anim", "Lighting" ou "Compositing" ; NO_LEVEL ("-") si
            aucun média n'est trouvé ou si le dossier du shot n'existe pas.
        """
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return NO_LEVEL

        # Parcours inversé : le premier niveau trouvé est le plus avancé
        for label, patterns in reversed(self.getActiveTaskLevels()):
            for pattern in patterns:
                fullPattern = os.path.join(shotFolder, *pattern.split("/"))
                if next(glob.iglob(fullPattern), None) is not None:
                    return label

        return NO_LEVEL

    def getShotInfos(self, entity):
        """Informations affichées dans les colonnes de l'arbre pour un shot.

        Args:
            entity: entité Prism du shot.

        Returns:
            dict: {"taskLevel": str (voir getTaskLevel), "pixmap": QPixmap miniature
            à la taille THUMB_SIZE (image vide si le shot n'a pas d'aperçu)}.
        """
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

    def updateTaskLevelColors(self, comp, perShot, masterRanges=()):
        """Pilote par expressions la couleur de fond du node Bg_TaskLevel selon le
        niveau d'avancement du shot affiché. Les lignes des shots passent avant celles
        du master (la première plage qui correspond gagne) ; hors plage, couleur
        NO_LEVEL_COLOR.

        Args:
            comp: composition Fusion contenant le node Bg_TaskLevel.
            perShot: liste de dicts de getCounterRanges (clés "start", "end",
                "taskLevel"), frames relatives au clip de la comp.
            masterRanges: liste de tuples (début, fin) des clips de la piste Master,
                colorés avec la couleur de MASTER_ONLY_LEVEL.
        """
        tool = comp.FindTool(TASK_BG_NODE)
        if not tool:
            print("[ShotBrowser] node '%s' introuvable" % TASK_BG_NODE)
            return
    
        masterColor = TASK_COLORS.get(MASTER_ONLY_LEVEL, NO_LEVEL_COLOR)
    
        for inputId, idx in BG_CHANNELS:
            inp = getInput(tool, inputId)
            if not inp:
                print("[ShotBrowser] %s : input '%s' introuvable (voir printToolInputs)"
                    % (TASK_BG_NODE, inputId))
                continue
            table = [(r["start"], r["end"], TASK_COLORS.get(r["taskLevel"], NO_LEVEL_COLOR)[idx])
                    for r in perShot]
            table += [(s, e, masterColor[idx]) for s, e in masterRanges]
            inp.SetExpression(numberExpression(table, NO_LEVEL_COLOR[idx]))
    
        print("[ShotBrowser] %s -> couleurs mises à jour" % TASK_BG_NODE)

    def getMasterRanges(self, timeline, origin):
        """Plages occupées par les clips de la piste Master.

        Args:
            timeline: timeline Resolve.
            origin: première frame du clip Fusion des compteurs ; sert de zéro.

        Returns:
            list[tuple[int, int]]: [(début, fin)] triées, en frames relatives à origin.
        """
        ranges = []
        for t in range(1, timeline.GetTrackCount("video") + 1):
            if timeline.GetTrackName("video", t) != MASTER_TRACK_NAME:
                continue
            for item in timeline.GetItemListInTrack("video", t) or []:
                ranges.append((item.GetStart() - origin, item.GetEnd() - origin))
        return sorted(ranges)

    def listSequenceFiles(self, path):
        """Liste les images d'une séquence numérotée à partir d'un de ses fichiers.

        Args:
            path: chemin d'une image au format "<nom>.<numéro>.<ext>".

        Returns:
            list[tuple[int | None, str]]: [(numéro, chemin)] triés par numéro ;
            [(None, path)] si le nom n'est pas numéroté.
        """
        folder, name = os.path.split(path)
        m = re.match(r"^(?P<pre>.+\.)(?P<frame>\d+)(?P<ext>\.[A-Za-z0-9]+)$", name)
        if not m:
            return [(None, path)]
        pre, width, ext = m.group("pre"), len(m.group("frame")), m.group("ext")
        rx = re.compile(r"^%s(\d{%d})%s$" % (re.escape(pre), width, re.escape(ext)))
        out = []
        for f in os.listdir(folder):
            mm = rx.match(f)
            if mm:
                out.append((int(mm.group(1)), os.path.join(folder, f)))
        return sorted(out)
    
    def isHeldMedia(self, files):
        """Indique si un shot doit être "tenu" (blocs de durée fixe sur la timeline)
        au lieu d'être posé comme séquence continue.

        Args:
            files: résultat de listSequenceFiles.

        Returns:
            bool: True pour une image fixe unique (extension de IMAGE_EXTS) ou une
            séquence dont l'écart entre numéros dépasse 1 ; False pour une vidéo
            ou une séquence continue.
        """
        if len(files) == 1:
            # fichier unique : tenu seulement si c'est une image (pas un mov/mp4)
            return os.path.splitext(files[0][1])[1].lower() in IMAGE_EXTS
        nums = [n for n, _ in files]
        return any(b - a > 1 for a, b in zip(nums, nums[1:]))
    
    def clearRange(self, timeline, track, start, end):
        """Supprime, sans ripple, les clips d'une piste qui touchent l'intervalle
        [start, end).

        Args:
            timeline: timeline Resolve.
            track: index de la piste vidéo (à partir de 1).
            start: première frame de l'intervalle.
            end: frame de fin, exclue.
        """
        olds = [it for it in (timeline.GetItemListInTrack("video", track) or [])
                if it.GetStart() < end and it.GetEnd() > start]
        if olds:
            timeline.DeleteClips(olds, False)
    
    def getTrackItemAt(self, timeline, track, startFrame):
        """Retrouve le clip qui démarre exactement à une frame (la piste est relue).

        Args:
            timeline: timeline Resolve.
            track: index de la piste vidéo.
            startFrame: frame de départ recherchée.

        Returns:
            Le clip, ou None.
        """
        for it in (timeline.GetItemListInTrack("video", track) or []):
            try:
                if it.GetStart() == startFrame:
                    return it
            except Exception:
                pass
        return None
    
    def buildSingleFrameImportItem(self, path, number):
        """Prépare l'import d'UNE seule image d'une séquence (plan B quand Resolve
        regroupe les images en séquence).

        Args:
            path: chemin de l'image.
            number: numéro de l'image dans la séquence (None si non numérotée).

        Returns:
            dict | None: {"FilePath": motif "%0Nd", "StartIndex": number,
            "EndIndex": number} pour ImportMedia ; None si le nom n'est pas numéroté.
        """
        if number is None:
            return None
        folder, name = os.path.split(path)
        m = re.match(r"^(?P<pre>.+\.)(?P<frame>\d+)(?P<ext>\.[A-Za-z0-9]+)$", name)
        if not m:
            return None
        pattern = os.path.join(folder, "%s%%0%dd%s" % (m.group("pre"), len(m.group("frame")), m.group("ext")))
        return {"FilePath": pattern, "StartIndex": number, "EndIndex": number}

    def importSingleImage(self, pool, path, number):
        """Importe une seule image dans le Media Pool : d'abord comme fichier simple ;
        si Resolve en a fait une séquence de plusieurs frames, retente avec un motif
        Start = End.

        Args:
            pool: Media Pool Resolve.
            path: chemin de l'image.
            number: numéro de l'image (utile au plan B).

        Returns:
            L'item du Media Pool, ou None si l'import échoue.
        """
        imported = pool.ImportMedia([path])
        mp = imported[0] if imported else None
        if mp:
            try:
                ctype = mp.GetClipProperty("Type")
                frames = mp.GetClipProperty("Frames")
            except Exception:
                ctype, frames = None, None
            print("[ShotBrowser] import %s -> Type=%s Frames=%s" % (os.path.basename(path), ctype, frames))
            if ctype in ("Still", "Image"):
                return mp
            try:
                if int(float(frames)) <= 1:
                    return mp
            except (TypeError, ValueError):
                return mp
    
        alt = self.buildSingleFrameImportItem(path, number)
        if alt:
            imported = pool.ImportMedia([alt])
            if imported:
                print("[ShotBrowser] plan B (Start=End) utilisé pour %s" % os.path.basename(path))
                return imported[0]
        return mp
    
    ##########################
    # MASTER
    ##########################

    def getMasterEntity(self, seq):
        """Entité Prism du shot "MASTER" d'une séquence.

        Args:
            seq: nom de la séquence.

        Returns:
            dict | None: l'entité, ou None si seq est vide ou s'il n'y a pas de MASTER.
        """
        if not seq:
            return None
        for entity in self.core.entities.getShots(sequence=seq) or []:
            if str(entity.get("shot", "")).upper() == "MASTER":
                return entity
        return None
    
    def getMasterItems(self, timeline, track):
        """Retrouve les masters déjà posés sur la piste Master, d'après leurs marqueurs.

        Args:
            timeline: timeline Resolve.
            track: index de la piste Master.

        Returns:
            dict: {séquence: [(clip, infos du marqueur)]}.
        """
        found = {}
        for item in timeline.GetItemListInTrack("video", track) or []:
            for marker in (item.GetMarkers() or {}).values():
                try:
                    info = json.loads(marker.get("customData") or "")
                except ValueError:
                    continue
                if "masterOf" in info:
                    found.setdefault(info["masterOf"], []).append((item, info))
                    break
        return found
    
    def ensureMasterTrack(self, timeline, lowestShotTrack):
        """Renvoie la piste Master, en la créant juste sous la piste de shots la plus
        basse si elle n'existe pas, et en la nommant MASTER_TRACK_NAME.

        Args:
            timeline: timeline Resolve.
            lowestShotTrack: index de la piste de shots la plus basse.

        Returns:
            int | None: index de la piste Master ; None si la création échoue ou si
            Resolve ignore l'index d'insertion.
        """
        for t in range(1, timeline.GetTrackCount("video") + 1):
            if timeline.GetTrackName("video", t) == MASTER_TRACK_NAME:
                return t
    
        before = timeline.GetTrackCount("video")
        try:
            timeline.AddTrack("video", {"index": lowestShotTrack})
        except Exception as e:
            print("[ShotBrowser] AddTrack (Master) refusé : %s" % e)
        if timeline.GetTrackCount("video") != before + 1:
            return None
    
        # Les pistes de shots doivent avoir monté d'un cran, sinon l'index a été ignoré
        shotTracks = [r["track"] for refs in self.getTimelineShots(timeline).values() for r in refs]
        if shotTracks and min(shotTracks) != lowestShotTrack + 1:
            print("[ShotBrowser] l'index d'insertion a été ignoré : piste Master non placée sous les shots")
            return None
    
        timeline.SetTrackName("video", lowestShotTrack, MASTER_TRACK_NAME)
        return lowestShotTrack
    
    def syncMasterTrack(self, timeline, pool):
        """Pour chaque séquence présente sur la timeline, pose (ou met à jour) son
        MASTER au début de la séquence, sur la piste Master. Un master déjà à jour
        (même média, même position) est laissé tel quel.

        Args:
            timeline: timeline Resolve.
            pool: Media Pool Resolve.

        Returns:
            list[str]: avertissements (vide si tout s'est bien passé).
        """
        warnings = []
        shots = self.getTimelineShots(timeline)
        refs = [r for refList in shots.values() for r in refList]
        if not refs:
            return warnings
    
        # Étendue de chaque séquence sur la timeline (début du 1er shot -> fin du dernier)
        spans = {}
        for shotPath, refList in shots.items():
            seq = shotPath.split("/")[0] if "/" in shotPath else ""
            for r in refList:
                s, e = r["start"], r["start"] + r["duration"]
                lo, hi = spans.get(seq, (s, e))
                spans[seq] = (min(lo, s), max(hi, e))
    
        track = self.ensureMasterTrack(timeline, min(r["track"] for r in refs))
        if not track:
            return ["Master : impossible de créer la piste sous les shots"]
    
        existing = self.getMasterItems(timeline, track)
    
        for seq in sorted(spans, key=naturalKey):
            if not seq:
                continue
            start, end = spans[seq]
    
            entity = self.getMasterEntity(seq)
            if not entity:
                print("[ShotBrowser] Master %s : aucun shot MASTER dans Prism" % seq)
                continue
            level, mediaPath = self.getShotMedia(entity)
            if not mediaPath:
                print("[ShotBrowser] Master %s : aucun média trouvé" % seq)
                continue
    
            cur = existing.get(seq)
            if cur and cur[0][1].get("mediaPath") == mediaPath and cur[0][0].GetStart() == start:
                print("[ShotBrowser] Master %s : déjà à jour (%s)" % (seq, rankText(level, mediaPath)))
                continue
            for item, _info in cur or []:
                self.clearRange(timeline, track, item.GetStart(), item.GetEnd())
    
            master = {
                "name": entity["shot"],
                "sequence": seq,
                "shot_path": "%s/%s" % (seq, entity["shot"]),
                "taskLevel": level,
                "mediaPath": mediaPath,
                "isMaster": True,
            }
            item, warn = self.placeShot(master, pool, timeline, track, start)
            if warn:
                warnings.append(warn)
            if item:
                print("[ShotBrowser] Master %s : %s posé à %d (%d f ; séquence sur la timeline : %d f)"
                    % (seq, rankText(level, mediaPath), start, self.lastPlacedLength, end - start))
        return warnings


    
    def addShotMarker(self, tlItem, shot, length=None):
        """Écrit les métadonnées Scene / Shot sur le média et pose sur le clip un
        marqueur (frame 0) dont le customData JSON est relu par getTimelineShots.
        Marqueur bleu pour un shot, violet pour un master.

        Args:
            tlItem: clip de la timeline.
            shot: dict {"name", "sequence", "shot_path", "taskLevel", "mediaPath"},
                plus "isMaster": True pour un master.
            length: durée réelle du shot en frames, mémorisée dans le marqueur
                (utile quand le shot est posé en plusieurs blocs) ; ignoré pour un master.
        """
        mp = tlItem.GetMediaPoolItem()
        if mp:
            mp.SetMetadata("Scene", shot["sequence"])
            mp.SetMetadata("Shot", shot["name"])
    
        if shot.get("isMaster"):
            data = {
                "masterOf": shot["sequence"],
                "taskLevel": shot["taskLevel"],
                "mediaPath": shot["mediaPath"],
            }
            color = "Purple"
        else:
            data = {
                "sequence": shot["sequence"],
                "shot": shot["name"],
                "taskLevel": shot["taskLevel"],
                "mediaPath": shot["mediaPath"],
            }
            if length:
                data["length"] = int(length)     # durée réelle du shot (multi-blocs)
            color = "Blue"
    
        tlItem.AddMarker(
            0, color, shot["shot_path"],
            "taskLevel: %s" % shot["taskLevel"], 1,
            json.dumps(data),
        )


    def setHeldMarks(self, mp, n):
        """Règle la plage In/Out d'un média sur n frames (de 0 à n-1). Si Resolve
        refuse, réessaie avec la moitié, jusqu'à 1.

        Args:
            mp: item du Media Pool.
            n: nombre de frames souhaité.

        Returns:
            int: nombre de frames réellement acceptées ; 0 si Resolve refuse tout.
        """
        while n >= 1:
            try:
                mp.ClearMarkInOut("all")
            except Exception:
                pass
            try:
                ok = mp.SetMarkInOut(0, n - 1, "all")
            except Exception as e:
                print("[ShotBrowser] SetMarkInOut a levé : %s" % e)
                ok = False
            try:
                mo = mp.GetMarkInOut() or {}
            except Exception:
                mo = {}
            outs = [v.get("out") for v in mo.values() if isinstance(v, dict)]
            print("[ShotBrowser] marques demandées 0-%d -> ok=%s relu=%s" % (n - 1, ok, mo))
            if ok and (not outs or any(o == n - 1 for o in outs)):
                return n
            n //= 2
        return 0
    
    def clearHeldMarks(self, mp):
        """Efface la plage In/Out d'un média (erreurs ignorées).

        Args:
            mp: item du Media Pool.
        """
        try:
            mp.ClearMarkInOut("all")
        except Exception:
            pass
    
    def placeHeldShot(self, shot, files, pool, timeline, trackIndex, recordFrame, target):
        """Pose un shot "tenu" (image fixe, ou séquence à pas > 1) en blocs bout à
        bout dont la somme vaut exactement `target` frames. En cas d'échec, les clips
        ajoutés par ce shot sont supprimés.

        Args:
            shot: dict du shot (voir addShotMarker).
            files: résultat de listSequenceFiles ; chaque image démarre un bloc.
            pool: Media Pool Resolve.
            timeline: timeline Resolve.
            trackIndex: piste vidéo de destination.
            recordFrame: frame de départ sur la timeline.
            target: durée totale voulue, en frames.

        Returns:
            tuple: (premier clip posé ou None, avertissement ou None). L'avertissement
            signale une erreur, un trou, un chevauchement ou une durée obtenue
            différente de target.
        """
        recordFrame, target = int(recordFrame), int(target)
        shotEnd = recordFrame + target
        name = shot["shot_path"]
    
        self.clearRange(timeline, trackIndex, recordFrame, shotEnd)
    
        def snapshot():
            return {(it.GetStart(), it.GetEnd())
                    for it in (timeline.GetItemListInTrack("video", trackIndex) or [])}
    
        before = snapshot()
    
        def abort(msg):
            # Supprime uniquement ce que ce shot a ajouté (y compris un clip posé ailleurs par erreur)
            extra = [it for it in (timeline.GetItemListInTrack("video", trackIndex) or [])
                    if (it.GetStart(), it.GetEnd()) not in before]
            if extra:
                timeline.DeleteClips(extra, False)
            return None, msg
    
        base = files[0][0]
        offsets = [0 if n is None else n - base for n, _ in files]
        offsets = [o for o in offsets if o < target]
    
        for i, off in enumerate(offsets):
            end = offsets[i + 1] if i + 1 < len(offsets) else target
            number, filePath = files[i]
            label = "%s bloc %d" % (name, i)
    
            mp = self.importSingleImage(pool, filePath, number)
            if not mp:
                return abort("%s : import échoué (%s)" % (label, filePath))
    
            pos, remaining = recordFrame + off, end - off
            while remaining > 0:
                n = self.setHeldMarks(mp, remaining)
                if n < 1:
                    self.clearHeldMarks(mp)
                    return abort("%s : Resolve refuse la plage In/Out sur cette image fixe" % label)
    
                pool.AppendToTimeline([{
                    "mediaPoolItem": mp,
                    "mediaType": 1,
                    "trackIndex": trackIndex,
                    "recordFrame": pos,
                }])
                item = self.getTrackItemAt(timeline, trackIndex, pos)
                d = item.GetDuration() if item else None
                print("[ShotBrowser] %s : pose à %d, marques %d f -> clip obtenu %s f" % (label, pos, n, d))
    
                if not item or not d:
                    self.clearHeldMarks(mp)
                    return abort("%s : aucun clip posé à la frame %d" % (label, pos))
                if d > n:
                    # Les marques ont été ignorées : on retire le clip trop long
                    timeline.DeleteClips([item], False)
                    self.clearHeldMarks(mp)
                    return abort("%s : Resolve a ignoré la plage In/Out (clip de %d f au lieu de %d)"
                                % (label, d, n))
                pos += d
                remaining -= d
    
            self.clearHeldMarks(mp)
    
        # Vérification : la piste doit être continue de recordFrame à shotEnd
        items = sorted((it for it in (timeline.GetItemListInTrack("video", trackIndex) or [])
                        if it.GetStart() < shotEnd and it.GetEnd() > recordFrame),
                    key=lambda it: it.GetStart())
        warning, cur = None, recordFrame
        for it in items:
            s, e = it.GetStart(), it.GetEnd()
            print("[ShotBrowser]   V%d : start=%d end=%d dur=%d" % (trackIndex, s, e, e - s))
            if s != cur and not warning:
                warning = "%s : trou ou chevauchement à la frame %d" % (name, s)
            cur = e
        if cur != shotEnd:
            warning = "%s : durée obtenue %d f au lieu de %d" % (name, cur - recordFrame, target)
    
        return self.getTrackItemAt(timeline, trackIndex, recordFrame), warning

    def findCounterTrack(self, timeline):
        """Piste vidéo qui porte le clip Fusion des compteurs (celui dont une comp
        contient le node COUNTERS[0], "SqName").

        Args:
            timeline: timeline Resolve.

        Returns:
            int | None: index de la piste, ou None si le clip est introuvable.
        """
        for t in range(1, timeline.GetTrackCount("video") + 1):
            for item in timeline.GetItemListInTrack("video", t) or []:
                for idx in range(1, (item.GetFusionCompCount() or 0) + 1):
                    comp = item.GetFusionCompByIndex(idx)
                    if comp and comp.FindTool(COUNTERS[0][0]):
                        return t
        return None
    
    def addShotsTrack(self, timeline):
        """Crée la piste des shots juste SOUS la piste des compteurs Fusion.
        Si l'insertion à un index est impossible, ajoute la piste tout en haut ; sans
        clip de compteurs, ajoute simplement une piste.

        Args:
            timeline: timeline Resolve.

        Returns:
            int | None: index de la nouvelle piste, ou None si la création échoue.
        """
        overlayTrack = self.findCounterTrack(timeline)
        before = timeline.GetTrackCount("video")
    
        if overlayTrack:
            try:
                timeline.AddTrack("video", {"index": overlayTrack})
            except Exception as e:
                print("[ShotBrowser] AddTrack avec index refusé : %s" % e)
    
            if timeline.GetTrackCount("video") == before + 1:
                # La piste Fusion est-elle montée d'un cran ? Alors notre piste est juste dessous.
                if self.findCounterTrack(timeline) == overlayTrack + 1:
                    return overlayTrack
                print("[ShotBrowser] l'index d'insertion a été ignoré : piste ajoutée tout en haut")
                return before + 1
    
        # Pas de comp Fusion trouvée, ou AddTrack n'a rien créé : méthode d'origine
        if not timeline.AddTrack("video"):
            return None
        return timeline.GetTrackCount("video")




    def populateTree(self):
        """Remplit l'arbre des shots, groupés par séquence, selon self.action.

        En "add", tous les shots Prism sont listés (cochés par défaut). En "bake" et
        "modify", seuls les shots déjà sur la timeline sont listés, avec une liste
        déroulante des versions ; "bake" ne garde que ceux dont une version plus
        avancée existe ; "modify" laisse tout décoché et coche un shot dès que sa
        version change.

        Returns:
            int: nombre de shots affichés.
        """
        self.tw_shots.clear()
        shots = self.core.entities.getShots() or []

        sequences = {}
        for entity in shots:
            sequences.setdefault(entity.get("sequence", ""), []).append(entity)

        defaultState = Qt.Unchecked if self.action == "modify" else Qt.Checked

        count = 0
        for seq in sorted(sequences, key=naturalKey):
            seqItem = None

            for entity in sorted(sequences[seq], key=lambda e: naturalKey(e.get("shot", ""))):
                shotName = entity.get("shot", "")
                shotPath = "%s/%s" % (seq, shotName) if seq else shotName

                versions, curRank = None, None
                if self.timelineMode:
                    refs = self.onTimeline.get(shotPath)
                    if not refs:
                        continue                         # pas sur la timeline
                    cur = refs[0]
                    curRank = rank(cur["taskLevel"], cur["mediaPath"])
                    versions = list(self.getShotVersions(entity))

                    if self.action == "bake":
                        if not versions or versions[0]["rank"] <= curRank:
                            continue                     # déjà à jour
                    elif not any(v["rank"] == curRank for v in versions):
                        # Version actuelle absente du disque : on la garde dans le menu
                        versions.append({
                            "label": cur["taskLevel"],
                            "version": versionNumber(cur["mediaPath"]),
                            "path": cur["mediaPath"],
                            "rank": curRank,
                        })
                        versions.sort(key=lambda v: v["rank"], reverse=True)

                    infos = self.getShotInfos(entity)
                    columns = [shotName, "", rankText(cur["taskLevel"], cur["mediaPath"]), ""]
                else:
                    infos = self.getShotInfos(entity)
                    columns = [shotName, "", infos["taskLevel"]]

                if seqItem is None:
                    seqItem = QTreeWidgetItem(self.tw_shots, [seq or "(sans séquence)"])
                    seqItem.setFlags(seqItem.flags() | Qt.ItemIsUserCheckable | _AUTO_TRISTATE)
                    font = seqItem.font(0)
                    font.setBold(True)
                    seqItem.setFont(0, font)

                shotItem = QTreeWidgetItem(seqItem, columns)
                shotItem.setFlags(shotItem.flags() | Qt.ItemIsUserCheckable)
                shotItem.setCheckState(0, defaultState)
                shotItem.setIcon(1, QIcon(infos["pixmap"]))
                shotItem.setSizeHint(1, THUMB_SIZE)
                shotItem.setData(0, Qt.UserRole, entity)

                if self.timelineMode:
                    combo = QComboBox()
                    for v in versions:
                        text = "%s v%04d" % (v["label"], v["version"])
                        if v["rank"] == curRank:
                            text += "  (actuel)"
                        combo.addItem(text, v)

                    if self.action == "modify":
                        # Présélection = version actuelle ; tout changement coche le shot
                        combo.setCurrentIndex(next(i for i, v in enumerate(versions) if v["rank"] == curRank))
                        combo.currentIndexChanged.connect(
                            lambda _i, it=shotItem: it.setCheckState(0, Qt.Checked))

                    self.tw_shots.setItemWidget(shotItem, 3, combo)
                count += 1

            if seqItem is not None:
                seqItem.setCheckState(0, defaultState)

        self.tw_shots.expandAll()
        return count
    
    # ------------------------------------------------------------------ #
    def getTimelineShots(self, timeline):
        """Parcourt les pistes vidéo et relit le marqueur (customData JSON) posé par
        addShotMarker sur chaque clip de shot.

        Args:
            timeline: timeline Resolve.

        Returns:
            dict: {shot_path: [{"item": clip, "track": index de piste, "start":
            frame de début, "duration": durée en frames (celle du marqueur si
            présente), "taskLevel": str, "mediaPath": str}]}.
        """
        found = {}
        for t in range(1, timeline.GetTrackCount("video") + 1):
            for item in timeline.GetItemListInTrack("video", t) or []:
                for marker in (item.GetMarkers() or {}).values():
                    cd = marker.get("customData")
                    if not cd:
                        continue
                    try:
                        info = json.loads(cd)
                    except ValueError:
                        continue
                    if "shot" not in info or "mediaPath" not in info:
                        continue
                    seq, shot = info.get("sequence", ""), info["shot"]
                    shotPath = "%s/%s" % (seq, shot) if seq else shot
                    found.setdefault(shotPath, []).append({
                        "item": item,
                        "track": t,
                        "start": item.GetStart(),
                        "duration": info.get("length") or item.GetDuration(),
                        "taskLevel": info.get("taskLevel", NO_LEVEL),
                        "mediaPath": info.get("mediaPath"),
                    })
                    break
        return found

    # ------------------------------------------------------------------ #
    def placeShot(self, shot, pool, timeline, trackIndex, recordFrame):
        """Importe et pose un shot sur la timeline, puis y ajoute son marqueur.

        Deux chemins : shot "tenu" (image fixe ou séquence à pas > 1) -> placeHeldShot
        avec la durée du shot dans Prism ; sinon séquence ou vidéo posée telle quelle
        (plusieurs essais de plage si la durée obtenue est trop courte). Met à jour
        self.lastPlacedLength (durée occupée sur la timeline).

        Args:
            shot: dict {"name", "sequence", "shot_path", "taskLevel", "mediaPath"},
                plus "isMaster" pour un master.
            pool: Media Pool Resolve.
            timeline: timeline Resolve.
            trackIndex: piste vidéo de destination.
            recordFrame: frame de départ sur la timeline.

        Returns:
            tuple: (clip posé ou None, avertissement ou None).
        """
        self.lastPlacedLength = 0
    
        path = shot.get("mediaPath")
        if not path:
            return None, "%s : aucun média trouvé" % shot["shot_path"]
    
        # Durée de référence côté Prism
        target = self.getShotLength(shot["sequence"], shot["name"])
        files = self.listSequenceFiles(path)
    
        # Diagnostic (une seule fois par import) : pourquoi Prism ne donne aucune durée ?
        if not target and not getattr(self, "_diagDone", False):
            self._diagDone = True
            try:
                ents = self.core.entities
                ent = ents.getShot(shot["sequence"], shot["name"])
                ranges = self.core.getConfig("shotRanges", config="shotinfo") or {}
                print("[ShotBrowser] diag %s : entité=%s | getShotRange=%s | épisodes=%s | clés shotRanges=%s"
                    % (shot["shot_path"], ent, ents.getShotRange(ent) if ent else None,
                        self.core.projects.getUseEpisodes(), list(ranges.keys())))
            except Exception as e:
                print("[ShotBrowser] diag impossible : %s" % e)
    
        # Plan B : pas de durée Prism, mais une séquence à step -> durée déduite des numéros d'images
        # (ex. 1001, 1011, ..., 1041 : 1041 - 1001 + dernier step de 10 = 50 frames)
        if not target and len(files) > 1 and self.isHeldMedia(files):
            nums = [n for n, _ in files]
            target = nums[-1] - nums[0] + (nums[-1] - nums[-2])
            print("[ShotBrowser] %s : pas de durée Prism, durée déduite du step : %d f"
                % (shot["shot_path"], target))
    
        # ---- Chemin 1 : image fixe / step > 1 -> durée garantie ----
        if target and self.isHeldMedia(files):
            tlItem, warning = self.placeHeldShot(
                shot, files, pool, timeline, trackIndex, recordFrame, target)
            if tlItem:
                self.lastPlacedLength = target
                self.addShotMarker(tlItem, shot, length=target)
            return tlItem, warning
    
        # ---- Chemin 2 : séquence complète / vidéo (fonctionnement d'origine) ----
        importItem, expectedFrames = self.buildImportItem(path)
        imported = pool.ImportMedia([importItem])
        if not imported:
            return None, "%s : ImportMedia a échoué (%s)" % (shot["shot_path"], importItem)
    
        mpItem = imported[0]
        try:
            nFrames = int(float(mpItem.GetClipProperty("Frames")))
        except (TypeError, ValueError):
            nFrames = 0
        if expectedFrames and nFrames < 2:
            nFrames = expectedFrames
        if nFrames < 1:
            return None, "%s : durée illisible" % shot["shot_path"]
    
        isStill = isinstance(importItem, str)       # fichier unique, pas une séquence
        try:
            isStill = isStill and mpItem.GetClipProperty("Type") in ("Still", "Image")
        except Exception:
            pass
        exact = bool(isStill and target)
    
        if exact:
            expectedFrames = target
            variants = [(0, target - 1), None]
        else:
            variants = [None]
            if isinstance(importItem, dict):
                variants.append((importItem["StartIndex"], importItem["EndIndex"]))
            variants.append((0, nFrames - 1))
    
        def append(frameRange):
            info = {
                "mediaPoolItem": mpItem,
                "mediaType": 1,
                "trackIndex": trackIndex,
                "recordFrame": int(recordFrame),
            }
            if frameRange:
                info["startFrame"], info["endFrame"] = frameRange
            res = pool.AppendToTimeline([info])
            return res[0] if res and res[0] else None
    
        tlItem, warning = None, None
        for frameRange in variants:
            item = append(frameRange)
            if not item:
                continue
            dur = item.GetDuration()
            tooShort = expectedFrames and dur < expectedFrames
            wrongStill = exact and dur != expectedFrames
            if tooShort or wrongStill:
                timeline.DeleteClips([item])
                continue
            tlItem = item
            break
    
        if not tlItem:
            tlItem = append(None)
            if not tlItem:
                return None, "%s : AppendToTimeline refusé" % shot["shot_path"]
            warning = "%s : durée %s au lieu de %s" % (shot["shot_path"], tlItem.GetDuration(), expectedFrames)
    
        self.lastPlacedLength = tlItem.GetDuration()
        self.addShotMarker(tlItem, shot)            # pas de "length" : la durée du clip fait foi
        return tlItem, warning


    # ------------------------------------------------------------------ #
    def getTimelineContext(self):
        """Récupère les objets Resolve nécessaires aux opérations sur la timeline.
        Affiche un popup si Resolve est injoignable ou s'il n'y a pas de timeline active.

        Returns:
            tuple | None: (projet, timeline, Media Pool), ou None en cas de problème.
        """
        resolve = self.getResolve()
        if not resolve:
            self.core.popup("Impossible de joindre DaVinci Resolve.")
            return None
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        if not timeline:
            self.core.popup("Aucune timeline active.")
            return None
        return project, timeline, project.GetMediaPool()

    def addShotsToTimeline(self, shots):
        """Mode "add" : crée une piste "ShotBrowser" sous les compteurs et y pose les
        shots les uns après les autres, à partir du curseur de lecture. Met ensuite à
        jour la piste Master et les compteurs Fusion, puis affiche les avertissements.

        Args:
            shots: liste de dicts de shots, voir placeShot.

        Returns:
            list: clips posés ; [] si Resolve ou la piste est indisponible.
        """
        ctx = self.getTimelineContext()
        if not ctx:
            return []
        project, timeline, pool = ctx

        fps = float(timeline.GetSetting("timelineFrameRate"))
        cursor = tcToFrames(timeline.GetCurrentTimecode(), fps)    # curseur rouge

        # Nouvelle piste vidéo pour cet import
        newTrack = self.addShotsTrack(timeline)
        if not newTrack:
            self.core.popup("Impossible de créer une nouvelle piste vidéo.")
            return []

        try:
            timeline.SetTrackName("video", newTrack, "ShotBrowser")
        except Exception:
            pass
        print("[ShotBrowser] nouvelle piste vidéo : V%d" % newTrack)

        tlItems, warnings = [], []
        for shot in shots:
            tlItem, warn = self.placeShot(shot, pool, timeline, newTrack, cursor)
            if warn:
                warnings.append(warn)
            if tlItem:
                tlItems.append(tlItem)
                cursor += self.lastPlacedLength or tlItem.GetDuration()

        warnings += self.syncMasterTrack(timeline, pool)

        if warnings:
            self.core.popup("Shots non ajoutés ou incomplets :\n" + "\n".join(warnings))

        print("[ShotBrowser] ajout terminé, mise à jour des compteurs")
        self.updateFrameCounters()
        return tlItems

    def bakeShotsOnTimeline(self, shots):
        """Modes "bake" / "modify" : remplace chaque occurrence des shots donnés sur
        la timeline par le nouveau média, à la même position. Si la pose échoue,
        l'ancien média est remis. Met ensuite à jour la piste Master et les
        compteurs, puis affiche un popup (nombre de clips mis à jour et avertissements,
        dont les changements de durée).

        Args:
            shots: liste de dicts de shots avec le nouveau "taskLevel" / "mediaPath".

        Returns:
            list: nouveaux clips posés.
        """
        ctx = self.getTimelineContext()
        if not ctx:
            return []
        project, timeline, pool = ctx

        onTimeline = self.getTimelineShots(timeline)
        baked, warnings = [], []

        for shot in shots:
            for ref in onTimeline.get(shot["shot_path"], []):
                oldItem = ref["item"]
                oldMp = oldItem.GetMediaPoolItem()

                self.clearRange(timeline, ref["track"], ref["start"], ref["start"] + ref["duration"])
                newItem, warn = self.placeShot(shot, pool, timeline, ref["track"], ref["start"])
                if warn:
                    warnings.append(warn)

                if not newItem:
                    # Restauration de l'ancien média (plage complète du clip)
                    pool.AppendToTimeline([{
                        "mediaPoolItem": oldMp, "mediaType": 1,
                        "trackIndex": ref["track"], "recordFrame": int(ref["start"]),
                    }])
                    warnings.append("%s : mise à jour impossible, ancien média remis" % shot["shot_path"])
                    continue

                newLen = self.lastPlacedLength or newItem.GetDuration()
                if newLen != ref["duration"]:
                    warnings.append("%s : durée changée (%s → %s frames)"
                                    % (shot["shot_path"], ref["duration"], newLen))

                baked.append(newItem)

        if baked:
            warnings += self.syncMasterTrack(timeline, pool)


        if baked:
            try:
                self.updateFrameCounters()
            except Exception as e:
                print("[ShotBrowser] mise à jour des compteurs impossible : %s" % e)

        msg = "%d clip(s) mis à jour." % len(baked)
        if warnings:
            msg += "\n\n" + "\n".join(warnings)
        self.core.popup(msg)
        return baked


    # ------------------------------------------------------------------ #
    def setAllChecked(self, state):
        """Coche ou décoche toutes les séquences visibles (donc leurs shots).

        Args:
            state: Qt.Checked ou Qt.Unchecked.
        """
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            if not seqItem.isHidden():
                seqItem.setCheckState(0, state)

    def isMaster(self, item):
        """Indique si un item de l'arbre est un shot MASTER.

        Args:
            item: QTreeWidgetItem dont la colonne 0 porte l'entité Prism (UserRole).

        Returns:
            bool: True si le nom du shot est "MASTER" (insensible à la casse).
        """
        entity = item.data(0, Qt.UserRole) or {}
        return str(entity.get("shot", "")).upper() == "MASTER"

    def filterTree(self, *args):
        """Affiche ou masque séquences et shots selon le texte de recherche et la
        case "Afficher les MASTER" ; une séquence sans shot visible est masquée.

        Args:
            *args: arguments du signal Qt (texte, état de la case), ignorés.
        """
        text = self.e_search.text().lower()
        showMasters = self.cb_masters.isChecked()
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            seqMatch = text in seqItem.text(0).lower()
            visible = 0
            for j in range(seqItem.childCount()):
                child = seqItem.child(j)
                match = (seqMatch or text in child.text(0).lower()) \
                        and (showMasters or not self.isMaster(child))
                child.setHidden(not match)
                visible += match
            seqItem.setHidden(visible == 0)

    # ------------------------------------------------------------------ #
    def getShotMedia(self, entity):
        """Média à poser pour un shot : première image de la dernière version du
        niveau le plus avancé parmi getActiveTaskLevels().

        Args:
            entity: entité Prism du shot.

        Returns:
            tuple[str, str | None]: (niveau, chemin du premier fichier) ;
            (NO_LEVEL, None) si le dossier du shot ou le média est introuvable.
        """
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return NO_LEVEL, None

        for label, patterns in reversed(self.getActiveTaskLevels()):
            files = []
            for pattern in patterns:
                files += glob.glob(os.path.join(shotFolder, *pattern.split("/")))
            files = [f for f in files if os.path.isfile(f)]
            if not files:
                continue
            latestDir = max(os.path.dirname(f) for f in files)  # v0001 < v0002 (zéro-padding)
            inLatest = sorted(f for f in files if os.path.dirname(f) == latestDir)
            return label, inLatest[0]   # 1re image pour une séquence

        return NO_LEVEL, None

    def getResolve(self):
        # Adapte si ton plugin expose déjà l'objet resolve
        """Objet racine de l'API de script de DaVinci Resolve.

        Returns:
            L'objet Resolve (via DaVinciResolveScript, sinon la variable `resolve` de
            __main__), ou None.
        """
        try:
            import DaVinciResolveScript as dvr
            return dvr.scriptapp("Resolve")
        except ImportError:
            import __main__
            return getattr(__main__, "resolve", None)

    def getResolveProjectName(self):
        """Nom du projet Resolve courant.

        Returns:
            str: le nom, ou "" si Resolve ou le projet est injoignable.
        """
        try:
            resolve = self.getResolve()
            project = resolve.GetProjectManager().GetCurrentProject() if resolve else None
            return project.GetName() if project else ""
        except Exception:
            return ""

    def getActiveTaskLevels(self):
        """Niveaux d'avancement à chercher sur disque. Si le nom du projet Resolve
        contient LAYOUT_PROJECT_KEYWORD ("layout"), seuls les niveaux de
        LAYOUT_PROJECT_LEVELS (Layout et Anim) sont gardés ; sinon, tous.

        Returns:
            list: sous-liste de TASK_LEVELS, de la forme [(label, [motifs glob])].
        """
        name = self.getResolveProjectName()
        if LAYOUT_PROJECT_KEYWORD in name.lower():
            return [lvl for lvl in TASK_LEVELS if lvl[0] in LAYOUT_PROJECT_LEVELS]
        return TASK_LEVELS

    def getShotVersions(self, entity):
        """Toutes les versions existantes d'un shot sur disque, parmi les niveaux de
        getActiveTaskLevels().

        Args:
            entity: entité Prism du shot.

        Returns:
            list[dict]: [{"label": niveau, "version": numéro, "path": premier fichier,
            "rank": rang comparable}], de la plus avancée à la plus ancienne ; []
            si le dossier du shot n'existe pas.
        """
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return []

        versions = []
        for label, patterns in self.getActiveTaskLevels():
            byDir = {}
            for pattern in patterns:
                for f in glob.glob(os.path.join(shotFolder, *pattern.split("/"))):
                    if os.path.isfile(f):
                        byDir.setdefault(os.path.dirname(f), []).append(f)
            for folder, files in byDir.items():
                first = sorted(files)[0]          # 1re image pour une séquence
                versions.append({
                    "label": label,
                    "version": versionNumber(first),
                    "path": first,
                    "rank": rank(label, first),
                })

        versions.sort(key=lambda v: v["rank"], reverse=True)
        return versions

    # ------------------------------------------------------------------ #

    def buildImportItem(self, path):
        """Prépare l'élément à donner à ImportMedia pour un média.

        Args:
            path: chemin d'un fichier ; si son nom est "<nom>.<numéro>.<ext>" et que
                le dossier contient au moins 2 images de la séquence, la séquence
                entière est importée.

        Returns:
            tuple: (élément, nombre de frames attendu). Fichier unique ou vidéo ->
            (path, None). Séquence -> ({"FilePath": motif "%0Nd", "StartIndex",
            "EndIndex"}, nombre d'images).
        """
        folder, name = os.path.split(path)
        m = re.match(r"^(?P<pre>.+\.)(?P<frame>\d+)(?P<ext>\.[A-Za-z0-9]+)$", name)
        if not m:
            return path, None

        pre, width, ext = m.group("pre"), len(m.group("frame")), m.group("ext")
        rx = re.compile(r"^%s(\d{%d})%s$" % (re.escape(pre), width, re.escape(ext)))

        frames = sorted(int(rx.match(f).group(1)) for f in os.listdir(folder) if rx.match(f))
        if len(frames) < 2:
            return path, None

        pattern = os.path.join(folder, "%s%%0%dd%s" % (pre, width, ext))
        item = {
            "FilePath": pattern,
            "StartIndex": frames[0],
            "EndIndex": frames[-1],
        }
        return item, frames[-1] - frames[0] + 1

    def getCounterRanges(self, timeline, origin):
        """Plages des shots sur la timeline, relatives au clip des compteurs.

        Args:
            timeline: timeline Resolve.
            origin: première frame du clip Fusion des compteurs ; sert de zéro.

        Returns:
            tuple: (perShot, perSeq). perShot : liste de dicts {"shot", "seq",
            "start", "end", "taskLevel", "mediaPath"} triée par début. perSeq :
            {séquence: (début, fin)} couvrant tous ses shots.
        """
        shots = self.getTimelineShots(timeline)
        perShot, perSeq = [], {}
        for shotPath, refs in shots.items():
            seq = shotPath.split("/")[0] if "/" in shotPath else ""
            for ref in refs:
                s = ref["start"] - origin
                e = s + ref["duration"]
                perShot.append({"shot": shotPath, "seq": seq, "start": s, "end": e,
                                "taskLevel": ref["taskLevel"], "mediaPath": ref["mediaPath"]})
                lo, hi = perSeq.get(seq, (s, e))
                perSeq[seq] = (min(lo, s), max(hi, e))
        perShot.sort(key=lambda r: r["start"])
        return perShot, perSeq
    
    def findCounterComp(self, timeline):
        """Trouve le clip et la composition Fusion qui contiennent les nodes de compteur.

        Args:
            timeline: timeline Resolve.

        Returns:
            tuple: (clip, composition), ou (None, None) s'ils sont introuvables.
        """
        for t in range(1, timeline.GetTrackCount("video") + 1):
            for item in timeline.GetItemListInTrack("video", t) or []:
                for idx in range(1, (item.GetFusionCompCount() or 0) + 1):
                    comp = item.GetFusionCompByIndex(idx)
                    if comp and comp.FindTool(COUNTERS[0][0]):
                        return item, comp
        return None, None

    def updateFrameCounters(self):
        """Met à jour tous les compteurs Fusion de la timeline : pose sur chaque node
        de COUNTERS une expression qui affiche, selon la frame, le nom de la séquence
        ou du shot, le compteur d'images, le niveau, la date du fichier ou le nom du
        film, puis recolore le fond du niveau (updateTaskLevelColors). Les plages
        du master sont ajoutées au niveau d'avancement MASTER_ONLY_LEVEL.

        Ne fait rien (message dans la console) si la comp des compteurs est
        introuvable.
        """
        ctx = self.getTimelineContext()
        if not ctx:
            return
        project, timeline, pool = ctx

        overlay, comp = self.findCounterComp(timeline)
        if not comp:
            print("[ShotBrowser] comp des compteurs introuvable")
            return

        perShot, perSeq = self.getCounterRanges(timeline, overlay.GetStart())
        masterRanges = self.getMasterRanges(timeline, overlay.GetStart())
        filmName = getFilmName(self.core)

        for nodeName, mode, scope in COUNTERS:
            tool = comp.FindTool(nodeName)
            if not tool:
                print("[ShotBrowser] node '%s' introuvable" % nodeName)
                continue
            inp = getInput(tool, "StyledText")
            if not inp:
                continue

            if scope == "project":
                inp.SetExpression(constantExpression(filmName))
                print("[ShotBrowser] %s -> %s" % (nodeName, filmName))
                continue

            rows = []
            for r in perShot:
                if scope == "seq":
                    ref, label = perSeq[r["seq"]][0], sqLabel(r["seq"])
                else:
                    ref = r["start"]
                    if mode == "task":
                        label = r["taskLevel"]
                    elif mode == "date":
                        label = fileDateText(r["mediaPath"])
                    else:
                        label = shLabel(r["shot"])
                rows.append((r["start"], r["end"], ref, label))

            if mode == "task":
                rows += [(s, e, s, MASTER_ONLY_LEVEL) for s, e in masterRanges]

            inp.SetExpression(counterExpression(rows, mode))
        self.updateTaskLevelColors(comp, perShot, masterRanges)

    def printToolInputs(self, toolName):
        """Outil de debug : affiche dans la console l'identifiant, le nom et le type
        de chaque input d'un node de la comp des compteurs (utile pour trouver les
        INPS_ID à passer à getInput).

        Args:
            toolName: nom du node Fusion (ex. "Bg_TaskLevel").
        """
        overlay, comp = self.findCounterComp(self.getTimelineContext()[1])
        print("[ShotBrowser] comp trouvée : %s | clip : %s" % (bool(comp), overlay.GetName() if overlay else None))
        tool = comp.FindTool(toolName)
        for i, inp in tool.GetInputList().items():
            attrs = inp.GetAttrs()
            print(attrs.get("INPS_ID"), "|", attrs.get("INPS_Name"), "|", attrs.get("INPS_DataType"))

    def getShotLength(self, sequence, shotName):
        """Durée d'un shot d'après sa plage d'images dans Prism.

        Args:
            sequence: nom de la séquence.
            shotName: nom du shot.

        Returns:
            int | None: fin - début + 1 (plage inclusive) ; None si la plage est
            inconnue.
        """
        if not sequence or not shotName:
            return None
    
        ents = self.core.entities
        entity = ents.getShot(sequence, shotName) or {
            "type": "shot", "sequence": sequence, "shot": shotName}
    
        shotRange = ents.getShotRange(entity)
        source = "getShotRange"
        if not shotRange:
            ranges = self.core.getConfig("shotRanges", config="shotinfo", allowCache=False) or {}
            shotRange = (ranges.get(sequence) or {}).get(shotName)
            source = "relecture sans cache"
    
        print("[ShotBrowser] plage Prism %s/%s = %s (%s) | projet : %s"
            % (sequence, shotName, shotRange, source, self.core.projectPath))
    
        if shotRange and len(shotRange) >= 2:
            return shotRange[1] - shotRange[0] + 1
        return None



    # ------------------------------------------------------------------ #
    def onValidate(self):
        """Bouton de validation : collecte les shots cochés et visibles, ferme la
        fenêtre puis lance la pose (addShotsToTimeline) ou la mise à jour
        (bakeShotsOnTimeline). En "bake" / "modify", un shot dont la version choisie
        est celle déjà posée est ignoré ; sans changement, affiche "Aucune
        modification à appliquer.".

        Stocke la liste des shots dans self.toImportShot (renvoyée par
        onShotBrowserTriggered), chaque élément étant {"name", "sequence",
        "shot_path", "taskLevel", "mediaPath"}.
        """
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
                shotPath = "%s/%s" % (seq, shot) if seq else shot

                if self.timelineMode:
                    # Version choisie dans le menu déroulant
                    combo = self.tw_shots.itemWidget(child, 3)
                    chosen = combo.itemData(combo.currentIndex())
                    level, mediaPath = chosen["label"], chosen["path"]

                    # Rien à faire si c'est déjà la version posée sur la timeline
                    cur = self.onTimeline[shotPath][0]
                    if rank(level, mediaPath) == rank(cur["taskLevel"], cur["mediaPath"]):
                        continue
                else:
                    level, mediaPath = self.getShotMedia(entity)

                result.append({
                    "name": shot,
                    "sequence": seq,
                    "shot_path": shotPath,
                    "taskLevel": level,
                    "mediaPath": mediaPath,
                })

        self.toImportShot = result
        self.dlg.accept()

        if self.timelineMode:
            if not result:
                self.core.popup("Aucune modification à appliquer.")
                return
            self.bakeShotsOnTimeline(result)
        else:
            self.addShotsToTimeline(result)

    def prepareDeliver(self, folder, name, openDeliverPage=True):
        """Remplit les champs "Location" et "File name" de la page Deliver.

        Args:
            folder: dossier de sortie (TargetDir).
            name: nom de fichier sans extension (CustomName).
            openDeliverPage: True pour ouvrir la page Deliver ensuite.

        Returns:
            bool: True si Resolve a accepté les réglages ; False sinon (projet
            injoignable ou réglages refusés).
        """
        resolve = self.getResolve()
        project = resolve.GetProjectManager().GetCurrentProject() if resolve else None
        if not project:
            self.core.popup("Impossible de joindre le projet DaVinci Resolve.")
            return False
    
        ok = project.SetRenderSettings({
            "TargetDir": folder,      # champ Location
            "CustomName": name,       # champ File name (sans extension)
        })
        print("[ShotBrowser] Deliver : TargetDir=%s CustomName=%s -> %s" % (folder, name, ok))
    
        if ok and openDeliverPage:
            resolve.OpenPage("deliver")     # rafraîchit l'affichage des champs
        return bool(ok)

    


    # ------------------------------------------------------------------ #
    def resetFrameCounters(self):
        """Réinitialise les compteurs Fusion : retire les expressions posées par le
        Shot Browser, remet les textes de COUNTER_DEFAULTS et la couleur de fond
        NO_LEVEL_COLOR. Les nodes restent en place, updateFrameCounters pourra les
        piloter de nouveau.

        Ne fait rien (message dans la console) si la comp des compteurs est
        introuvable.
        """
        ctx = self.getTimelineContext()
        if not ctx:
            return
        project, timeline, pool = ctx

        overlay, comp = self.findCounterComp(timeline)
        if not comp:
            print("[ShotBrowser] comp des compteurs introuvable")
            return

        def clearExpression(inp):
            try:
                inp.SetExpression(None)
            except Exception:
                inp.SetExpression("")      # repli si None est refusé

        comp.Lock()
        try:
            # Textes
            for nodeName, mode, scope in COUNTERS:
                tool = comp.FindTool(nodeName)
                inp = getInput(tool, "StyledText") if tool else None
                if not inp:
                    print("[ShotBrowser] reset : node/input '%s' introuvable" % nodeName)
                    continue
                clearExpression(inp)
                tool.SetInput("StyledText", COUNTER_DEFAULTS.get(nodeName, ""), comp.CurrentTime)

            # Couleur du fond TaskLevel
            bg = comp.FindTool(TASK_BG_NODE)
            if bg:
                for inputId, idx in BG_CHANNELS:
                    inp = getInput(bg, inputId)
                    if not inp:
                        continue
                    clearExpression(inp)
                    bg.SetInput(inputId, NO_LEVEL_COLOR[idx], comp.CurrentTime)
        finally:
            comp.Unlock()

        print("[ShotBrowser] compteurs réinitialisés")