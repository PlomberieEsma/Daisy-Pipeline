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

SEQ_TOOL, SEQ_INPUT = "SeqCounter", "Number"      # à adapter
SHOT_TOOL, SHOT_INPUT = "ShotCounter", "Number"   # à adapter


# Ordre croissant d'avancement : du premier niveau au dernier.
# Chaque niveau = (label, [motifs glob relatifs au dossier du shot])
# À ADAPTER à ton arborescence réelle.
TASK_LEVELS = [
    ("Layout",      ["Playblasts/02_layout/Layout/*/*"]),
    ("Anim",        ["Playblasts/03_anim/Animation/*/*"]),
    ("Lighting",    ["Renders/3dRender/07_lighting/Lighting/*/*_beauty.*"]),
    ("Compositing", ["Renders/2dRender/08_compositing/Compositing/*/*"]),
]

NO_LEVEL = "-"

# Association personnalisée des lettres pour chaque TaskLevel
TASK_LETTERS = {
    "Layout": "Ly",
    "Anim": "A",
    "Lighting": "Lg",       # Par exemple 'G' pour Lighting ou 'L'
    "Compositing": "C",
}

def naturalKey(s):
    # sh2 avant sh10
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def tcToFrames(tc, fps):
    # Timecode "HH:MM:SS:FF" -> frame absolu (drop-frame non géré)
    h, m, s, f = [int(x) for x in re.split(r"[:;]", tc)]
    return (h * 3600 + m * 60 + s) * int(round(fps)) + f

def levelIndex(label):
    labels = [l for l, _ in TASK_LEVELS]
    return labels.index(label) if label in labels else -1

def versionNumber(path):
    # .../Layout/v0003/fichier -> 3
    if not path:
        return 0
    m = re.match(r"^v(\d+)$", os.path.basename(os.path.dirname(path)), re.I)
    return int(m.group(1)) if m else 0

def rank(label, path):
    return (levelIndex(label), versionNumber(path))

def rankText(label, path):
    return "%s v%04d" % (label, versionNumber(path))

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

def counterExpression(rows, mode):
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
    return seq        # "sq010" -> "sq010"

def shLabel(shotPath):
    # "sq010/sh020" -> "Sh0020"  (format à confirmer)
    shot = shotPath.split("/")[-1]
    digits = re.sub(r"\D", "", shot)
    return "Sh%04d" % int(digits) if digits else "Sh----"

def getInput(tool, inputId):
    for _, inp in tool.GetInputList().items():
        if inp.GetAttrs().get("INPS_ID") == inputId:
            return inp
    return None

SHOTINFO_REL = os.path.join("00_Pipeline", "Shotinfo", "shotInfo.json")

def loadShotRanges(core):
    """{"sq010": {"sh010": [1001, 1100], ...}, ...}"""
    path = os.path.join(core.projectPath, SHOTINFO_REL)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("shotRanges", {})
    except Exception as e:
        print("[ShotBrowser] shotInfo.json illisible (%s) : %s" % (path, e))
        return {}

def luaStr(s):
    # Chaîne Lua sûre (guillemets et antislashs échappés)
    return '"%s"' % str(s).replace("\\", "\\\\").replace('"', '\\"')

def constantExpression(text):
    return "(function() return %s end)()" % luaStr(text)

def fileDateText(path):
    """Date de modification du fichier au format AA/MM/JJ (ex : 26/10/13)."""
    try:
        return time.strftime("%y/%m/%d", time.localtime(os.path.getmtime(path)))
    except Exception:
        return ""

def getFilmName(core):
    """Nom du projet Prism sans préfixe du type '12_'."""
    name = getattr(core, "projectName", None) or os.path.basename(os.path.normpath(core.projectPath))
    return re.sub(r"^\d+_", "", str(name))

class ShotBrowserUI(object):
    def __init__(self, core, plugin=None):
        self.core = core
        self.plugin = plugin
        self.toImportShot = []

    def onShotBrowserTriggered(self, task="", action="add"):
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
        self.shotRanges = loadShotRanges(self.core)

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
        """03_Production/Shots/<sq>/<sh>"""
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
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return NO_LEVEL

        # Parcours inversé : le premier niveau trouvé est le plus avancé
        for label, patterns in reversed(TASK_LEVELS):
            for pattern in patterns:
                fullPattern = os.path.join(shotFolder, *pattern.split("/"))
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
        """Remplit l'arbre, renvoie le nombre de shots affichés."""
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
        """
        Parcourt les pistes vidéo et renvoie
        {shot_path: [{"item", "track", "start", "duration", "taskLevel", "mediaPath"}, ...]}
        d'après le marqueur (customData JSON) posé à l'ajout.
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
                        "duration": item.GetDuration(),
                        "taskLevel": info.get("taskLevel", NO_LEVEL),
                        "mediaPath": info.get("mediaPath"),
                    })
                    break
        return found

    # ------------------------------------------------------------------ #
    def placeShot(self, shot, pool, timeline, trackIndex, recordFrame):
        """Importe et pose un shot. Renvoie (tlItem ou None, avertissement ou None)."""
        path = shot.get("mediaPath")
        if not path:
            return None, "%s : aucun média trouvé" % shot["shot_path"]

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

        # Durée de référence côté Prism
        target = self.getShotLength(shot["sequence"], shot["name"])
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

        # Transmission des infos
        mp = tlItem.GetMediaPoolItem()
        mp.SetMetadata("Scene", shot["sequence"])
        mp.SetMetadata("Shot", shot["name"])
        tlItem.AddMarker(
            0, "Blue", shot["shot_path"],
            "taskLevel: %s" % shot["taskLevel"], 1,
            json.dumps({
                "sequence": shot["sequence"],
                "shot": shot["name"],
                "taskLevel": shot["taskLevel"],
                "mediaPath": shot["mediaPath"],
            }),
        )
        return tlItem, warning

    # ------------------------------------------------------------------ #
    def getTimelineContext(self):
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
        ctx = self.getTimelineContext()
        if not ctx:
            return []
        project, timeline, pool = ctx

        fps = float(timeline.GetSetting("timelineFrameRate"))
        cursor = tcToFrames(timeline.GetCurrentTimecode(), fps)    # curseur rouge

        # Nouvelle piste vidéo pour cet import
        if not timeline.AddTrack("video"):
            self.core.popup("Impossible de créer une nouvelle piste vidéo.")
            return []
        newTrack = timeline.GetTrackCount("video")
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
                cursor += tlItem.GetDuration()       # le shot suivant démarre à la fin du précédent

        if warnings:
            self.core.popup("Shots non ajoutés ou incomplets :\n" + "\n".join(warnings))

        print("[ShotBrowser] ajout terminé, mise à jour des compteurs")
        self.updateFrameCounters()
        return tlItems

    def bakeShotsOnTimeline(self, shots):
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

                timeline.DeleteClips([oldItem], False)      # sans ripple : pas de décalage
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

                if newItem.GetDuration() != ref["duration"]:
                    warnings.append("%s : durée changée (%s → %s frames)"
                                    % (shot["shot_path"], ref["duration"], newItem.GetDuration()))
                baked.append(newItem)

        msg = "%d clip(s) mis à jour." % len(baked)
        if warnings:
            msg += "\n\n" + "\n".join(warnings)
        self.core.popup(msg)
        return baked


    # ------------------------------------------------------------------ #
    def setAllChecked(self, state):
        for i in range(self.tw_shots.topLevelItemCount()):
            seqItem = self.tw_shots.topLevelItem(i)
            if not seqItem.isHidden():
                seqItem.setCheckState(0, state)

    def isMaster(self, item):
        entity = item.data(0, Qt.UserRole) or {}
        return str(entity.get("shot", "")).upper() == "MASTER"

    def filterTree(self, *args):
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
        """(taskLevel, chemin du 1er fichier de la dernière version) du niveau le plus avancé."""
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return NO_LEVEL, None

        for label, patterns in reversed(TASK_LEVELS):
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
        try:
            import DaVinciResolveScript as dvr
            return dvr.scriptapp("Resolve")
        except ImportError:
            import __main__
            return getattr(__main__, "resolve", None)

    def getShotVersions(self, entity):
        """Toutes les versions existantes du shot, de la plus avancée à la plus ancienne.
        [{"label": niveau, "version": n, "path": 1er fichier, "rank": (niveau, version)}]"""
        shotFolder = self.getShotFolder(entity)
        if not shotFolder or not os.path.isdir(shotFolder):
            return []

        versions = []
        for label, patterns in TASK_LEVELS:
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
        """
        Renvoie (élément pour ImportMedia, nb de frames attendu).
        - fichier unique (mov, etc.)  -> (path, None)
        - séquence name.0001.exr      -> ({"FilePath": ".../name.%04d.exr", "StartIndex": 1, "EndIndex": 100}, 100)
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
        """Plages (frames relatives au début du clip comp) par plan et par séquence."""
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
        """Clip portant la comp qui contient les nodes de compteur."""
        for t in range(1, timeline.GetTrackCount("video") + 1):
            for item in timeline.GetItemListInTrack("video", t) or []:
                for idx in range(1, (item.GetFusionCompCount() or 0) + 1):
                    comp = item.GetFusionCompByIndex(idx)
                    if comp and comp.FindTool(COUNTERS[0][0]):
                        return item, comp
        return None, None

    def buildCounterRows(self, timeline, overlay, scope):
        perShot, perSeq = self.getCounterRanges(timeline, overlay.GetStart())
        
        # Récupérer les infos détaillées depuis getTimelineShots pour avoir le taskLevel
        timelineShots = self.getTimelineShots(timeline)
        
        rows = []
        for r in perShot:
            shotPath = r["shot"]
            if scope == "seq":
                ref, label = perSeq[r["seq"]][0], sqLabel(r["seq"])
            else:
                # Mode plan (shot)
                ref = r["start"]
                # Déterminer quel label passer selon le nœud traité (si on est sur TaskLevel ou ShName)
                # On peut récupérer le taskLevel stocké dans la timeline
                t_level = NO_LEVEL
                if shotPath in timelineShots and timelineShots[shotPath]:
                    t_level = timelineShots[shotPath][0].get("taskLevel", NO_LEVEL)
                
                # Astuce : on gère dynamiquement selon le besoin, ou on enrichit perShot
                label = shLabel(shotPath) # par défaut pour ShName
            
            rows.append((r["start"], r["end"], ref, label))
        return rows

    def updateFrameCounters(self):
        ctx = self.getTimelineContext()
        if not ctx:
            return
        project, timeline, pool = ctx

        overlay, comp = self.findCounterComp(timeline)
        if not comp:
            print("[ShotBrowser] comp des compteurs introuvable")
            return

        perShot, perSeq = self.getCounterRanges(timeline, overlay.GetStart())
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

            inp.SetExpression(counterExpression(rows, mode))

    def printToolInputs(self, toolName):
        overlay, comp = self.findCounterComp(self.getTimelineContext()[1])
        print("[ShotBrowser] comp trouvée : %s | clip : %s" % (bool(comp), overlay.GetName() if overlay else None))
        tool = comp.FindTool(toolName)
        for i, inp in tool.GetInputList().items():
            attrs = inp.GetAttrs()
            print(attrs.get("INPS_ID"), "|", attrs.get("INPS_Name"), "|", attrs.get("INPS_DataType"))

    def getShotLength(self, sequence, shotName):
        """Renvoie la durée en frames d'après shotInfo.json avec tolérance sur la casse."""
        if not sequence or not shotName:
            return None
        
        seq_data = self.shotRanges.get(sequence, {})
        if not seq_data:
            # Essai sans tenir compte de la casse de la séquence
            for sq_key, sq_val in self.shotRanges.items():
                if sq_key.lower() == sequence.lower():
                    seq_data = sq_val
                    break
                    
        shot_range = None
        for k, v in seq_data.items():
            if k.lower() == shotName.lower() or naturalKey(k) == naturalKey(shotName):
                shot_range = v
                break
        
        if shot_range and isinstance(shot_range, list) and len(shot_range) >= 2:
            return shot_range[1] - shot_range[0] + 1
        return None

    # ------------------------------------------------------------------ #
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
    