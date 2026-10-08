import os
import glob
import re
import json

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QPushButton, QHeaderView, QComboBox
)

# Compatibilité Qt5 / Qt6 pour la case tri-état
_AUTO_TRISTATE = getattr(Qt, "ItemIsAutoTristate", None) or getattr(Qt, "ItemIsTristate")

THUMB_SIZE = QSize(100, 56)


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



class ShotBrowserUI(object):
    def __init__(self, core, plugin=None):
        self.core = core
        self.plugin = plugin
        self.toImportShot = []

    def onShotBrowserTriggered(self, task="", action="add"):
        self.toImportShot = []
        self.action = action if action in ("add", "bake") else "add"

        try:
            # Mode bake : on a besoin de la timeline pour savoir ce qui est déjà posé
            self.onTimeline = {}
            if self.action == "bake":
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

            self.dlg = QDialog()
            self.core.parentWindow(self.dlg)
            self.dlg.setWindowTitle("Shot Browser - %s" % ("Bake" if self.action == "bake" else "Add"))
            self.dlg.resize(700, 650)

            layout = QVBoxLayout(self.dlg)

            if task:
                lo_ctx = QHBoxLayout()
                lbl = QLabel("Current Task :")
                lbl.setStyleSheet("font-weight: bold;")
                lo_ctx.addWidget(lbl)
                lo_ctx.addWidget(QLabel(str(task)))
                lo_ctx.addStretch()
                layout.addLayout(lo_ctx)

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
            if self.action == "bake":
                headers = ["Shot", "Thumbnail", "Actuel (timeline)", "Nouveau"]
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
            if self.action == "bake":
                header.setSectionResizeMode(3, QHeaderView.Interactive)
                self.tw_shots.setColumnWidth(3, 200)
            layout.addWidget(self.tw_shots)

            count = self.populateTree()
            if self.action == "bake" and count == 0:
                self.core.popup("Tous les shots de la timeline sont à jour.")
                return []

            self.btn_validate = QPushButton("Bake" if self.action == "bake" else "Add to new track")
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

        count = 0
        for seq in sorted(sequences, key=naturalKey):
            seqItem = None

            for entity in sorted(sequences[seq], key=lambda e: naturalKey(e.get("shot", ""))):
                shotName = entity.get("shot", "")
                shotPath = "%s/%s" % (seq, shotName) if seq else shotName

                if self.action == "bake":
                    refs = self.onTimeline.get(shotPath)
                    if not refs:
                        continue                     # pas sur la timeline
                    versions = self.getShotVersions(entity)
                    if not versions:
                        continue
                    cur = refs[0]
                    curRank = rank(cur["taskLevel"], cur["mediaPath"])
                    if versions[0]["rank"] <= curRank:
                        continue                     # déjà à jour
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
                shotItem.setCheckState(0, Qt.Checked)
                shotItem.setIcon(1, QIcon(infos["pixmap"]))
                shotItem.setSizeHint(1, THUMB_SIZE)
                shotItem.setData(0, Qt.UserRole, entity)
                if self.action == "bake":
                    combo = QComboBox()
                    for v in versions:
                        text = "%s v%04d" % (v["label"], v["version"])
                        if v["rank"] == curRank:
                            text += "  (actuel)"
                        combo.addItem(text, v)       # le dict de la version est stocké dans le menu
                    self.tw_shots.setItemWidget(shotItem, 3, combo)   # index 0 = la plus avancée
                count += 1

            if seqItem is not None:
                seqItem.setCheckState(0, Qt.Checked)

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
            if expectedFrames and item.GetDuration() < expectedFrames:
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
        cursor = tcToFrames(timeline.GetCurrentTimecode(), fps)

        if not timeline.AddTrack("video"):
            self.core.popup("Impossible de créer une nouvelle piste vidéo.")
            return []
        newTrack = timeline.GetTrackCount("video")
        try:
            timeline.SetTrackName("video", newTrack, "ShotBrowser")
        except Exception:
            pass

        tlItems, warnings = [], []
        for shot in shots:
            tlItem, warn = self.placeShot(shot, pool, timeline, newTrack, cursor)
            if warn:
                warnings.append(warn)
            if tlItem:
                tlItems.append(tlItem)
                cursor += tlItem.GetDuration()

        if warnings:
            self.core.popup("Shots non ajoutés ou incomplets :\n" + "\n".join(warnings))
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

    def addShotsToTimeline(self, shots):
        resolve = self.getResolve()
        if not resolve:
            self.core.popup("Impossible de joindre DaVinci Resolve.")
            return []

        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        if not timeline:
            self.core.popup("Aucune timeline active.")
            return []

        pool = project.GetMediaPool()
        fps = float(timeline.GetSetting("timelineFrameRate"))
        cursor = tcToFrames(timeline.GetCurrentTimecode(), fps)

        # Nouvelle piste vidéo dédiée à cet import
        if not timeline.AddTrack("video"):
            self.core.popup("Impossible de créer une nouvelle piste vidéo.")
            return []
        newTrack = timeline.GetTrackCount("video")   # la nouvelle piste est la dernière
        try:
            timeline.SetTrackName("video", newTrack, "ShotBrowser")
        except Exception:
            pass
        print("[ShotBrowser] nouvelle piste vidéo : V%d" % newTrack)

        tlItems, failed = [], []

        for shot in shots:
            path = shot.get("mediaPath")
            if not path:
                failed.append("%s : aucun média trouvé" % shot["shot_path"])
                continue

            importItem, expectedFrames = self.buildImportItem(path)
            imported = pool.ImportMedia([importItem])
            if not imported:
                failed.append("%s : ImportMedia a échoué (%s)" % (shot["shot_path"], importItem))
                continue

            mpItem = imported[0]
            print("[ShotBrowser] props %s : Frames=%s Start=%s End=%s Type=%s" % (
                shot["shot_path"],
                mpItem.GetClipProperty("Frames"), mpItem.GetClipProperty("Start"),
                mpItem.GetClipProperty("End"), mpItem.GetClipProperty("Type")))

            try:
                nFrames = int(float(mpItem.GetClipProperty("Frames")))
            except (TypeError, ValueError):
                nFrames = 0
            if expectedFrames and nFrames < 2:
                nFrames = expectedFrames
            if nFrames < 1:
                failed.append("%s : durée illisible" % shot["shot_path"])
                continue

            # Variantes de startFrame/endFrame : aucune, numérotation réelle, 0-based
            variants = [None]
            if isinstance(importItem, dict):
                variants.append((importItem["StartIndex"], importItem["EndIndex"]))
            variants.append((0, nFrames - 1))

            def append(frameRange):
                info = {
                    "mediaPoolItem": mpItem,
                    "mediaType": 1,
                    "trackIndex": newTrack,
                    "recordFrame": int(cursor),
                }
                if frameRange:
                    info["startFrame"], info["endFrame"] = frameRange
                res = pool.AppendToTimeline([info])
                if not res or not res[0]:
                    print("[ShotBrowser] append refusé, frameRange=%s" % (frameRange,))
                    return None
                return res[0]

            tlItem = None
            for frameRange in variants:
                item = append(frameRange)
                if not item:
                    continue
                dur = item.GetDuration()
                print("[ShotBrowser] %s frameRange=%s -> durée timeline=%s (attendu %s)"
                      % (shot["shot_path"], frameRange, dur, expectedFrames))
                if expectedFrames and dur < expectedFrames:
                    timeline.DeleteClips([item])   # trop court : on retire et on essaie la suivante
                    continue
                tlItem = item
                break

            # Dernier recours : on garde quand même le clip, en le signalant
            if not tlItem:
                tlItem = append(None)
                if not tlItem:
                    failed.append("%s : AppendToTimeline refusé" % shot["shot_path"])
                    continue
                failed.append("%s : durée %s au lieu de %s"
                              % (shot["shot_path"], tlItem.GetDuration(), expectedFrames))

            tlItems.append(tlItem)
            cursor += tlItem.GetDuration()   # durée réelle posée sur la timeline

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

        if failed:
            self.core.popup("Shots non ajoutés ou incomplets :\n" + "\n".join(failed))

        return tlItems

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

                if self.action == "bake":
                    # Version choisie dans le menu déroulant
                    combo = self.tw_shots.itemWidget(child, 3)
                    chosen = combo.itemData(combo.currentIndex())
                    level, mediaPath = chosen["label"], chosen["path"]

                    # Rien à faire si la version choisie est déjà celle de la timeline
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

        if self.action == "bake":
            self.bakeShotsOnTimeline(result)
        else:
            self.addShotsToTimeline(result)
    