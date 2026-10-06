# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import os, re, shutil, tempfile, datetime, json

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher

from Prism_DaVinciResolve_ShotBrowser import ShotBrowserUI

# ShotBrowserUI.onShotBrowserTriggered()

TASK_FOLDER_PATTERN = re.compile(r"^\d{2}_(.+)$")   # "01_animatic_2D" -> "animatic_2D"

class Prism_DaVinciResolve_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def startup(self, origin):
        # 	for obj in QApplication.topLevelWidgets():
        # 		if obj.objectName() == 'DaVinciResolveWindow':
        # 			QtParent = obj
        # 			break
        # 	else:
        # 		return False

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
        return ""

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        # save scenefile
        return True

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return []

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = 0
        endframe = 100

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        pass

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return 24

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        pass

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return "1.0"

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        # load scenefile
        return True

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
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        result = self.sm_export_exportAppObjects(
            origin,
            startFrame,
            endFrame,
            (outputName + ".abc"),
            nodes=[origin.curCam],
            expType=".abc",
        )
        result = self.sm_export_exportAppObjects(
            origin,
            startFrame,
            endFrame,
            (outputName + ".fbx"),
            nodes=[origin.curCam],
            expType=".fbx",
        )
        return result

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
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        pass

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_playblast_postExecute(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        pass

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        pass

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        return []

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



    ##############################################################################################################
    # Specific functions scripting
    ##############################################################################################################

    def getScenefilesRoot(self):
        return os.path.join(self.core.projectPath, "04_Editing", "Scenefiles")

    def getTask(self):
        # "animatic_2D_master" -> "animatic_2D"
        return re.sub(r"_master$", "", self._projectName())

    def getTaskFolder(self):
        task = self.getTask()
        root = self.getScenefilesRoot()
        if not os.path.isdir(root):
            raise RuntimeError("Dossier introuvable : %s" % root)

        for folder in sorted(os.listdir(root)):
            m = TASK_FOLDER_PATTERN.match(folder)
            if m and m.group(1).lower() == task.lower() and os.path.isdir(os.path.join(root, folder)):
                return folder

        raise RuntimeError("Le projet Resolve '%s' ne correspond à aucun dossier de task dans :\n%s"
                        % (self._projectName(), root))

    def getEditingScenefilePath(self):
        task=self.getTaskFolder()
        path=os.path.join(self.core.projectPath,"04_Editing", "Scenefiles", task)
        return path

    def getEditingRenderPath(self):
        task=self.getTaskFolder()
        path=os.path.join(self.core.projectPath,"04_Editing", "Output", task)
        return path

    def _projectName(self):
        return self.resolve.GetProjectManager().GetCurrentProject().GetName()

    def _masterFile(self):
        return os.path.join(self.getEditingScenefilePath(), "%s.drp" % self._projectName())

    # --- état local : "quelle version du master ai-je vue en dernier ?" ---

    def _stateFile(self):
        base = os.path.join(os.getenv("LOCALAPPDATA", tempfile.gettempdir()), "PrismResolve")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "master_state.json")

    def _loadState(self):
        try:
            with open(self._stateFile(), "r") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _recordMaster(self):
        master = self._masterFile()
        if os.path.exists(master):
            state = self._loadState()
            state[master] = os.path.getmtime(master)
            with open(self._stateFile(), "w") as f:
                json.dump(state, f)

    def _exportDrp(self, destFile):
        pm = self.resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        name = project.GetName()

        tmpDir = tempfile.mkdtemp(prefix="prism_resolve_")
        tmpFile = os.path.join(tmpDir, os.path.basename(destFile))
        try:
            ok = pm.ExportProject(name, tmpFile, True)   # True = avec stills et LUTs
            if not ok or not os.path.exists(tmpFile):
                raise RuntimeError("ExportProject a échoué pour '%s'" % name)
            os.makedirs(os.path.dirname(destFile), exist_ok=True)
            shutil.copy2(tmpFile, destFile)
        finally:
            shutil.rmtree(tmpDir, ignore_errors=True)
        return name

    @err_catcher(name=__name__)
    def SaveVersion(self):
        master = self._masterFile()

        if os.path.exists(master):
            known = self._loadState().get(master)
            current = os.path.getmtime(master)
            if known is None or abs(current - known) > 1:
                answer = self.core.popupQuestion(
                    "Le master a été modifié depuis votre dernière ouverture ou sauvegarde.\n"
                    "L'écraser avec votre version ?",
                    title="Master modifié",
                    buttons=["Écraser", "Annuler"],
                )
                if answer != "Écraser":
                    return

        self._exportDrp(master)
        self._recordMaster()
        self.core.popup("Master mis à jour.")

    @err_catcher(name=__name__)
    def SaveBackUpVersion(self):
        name = self._projectName()
        backupsDir = os.path.join(self.getEditingScenefilePath(), "Backups")

        pattern = re.compile(r"^%s_v(\d+)\.drp$" % re.escape(name))
        files = os.listdir(backupsDir) if os.path.isdir(backupsDir) else []
        numbers = [int(m.group(1)) for m in map(pattern.match, files) if m]
        version = max(numbers, default=0) + 1

        backupFile = os.path.join(backupsDir, "%s_v%04d.drp" % (name, version))
        self._exportDrp(backupFile)
        self.core.popup("Backup v%04d enregistré." % version)

    @err_catcher(name=__name__)
    def AddShot(self):
        task = self.getTask()
        shotBrowser = ShotBrowserUI(self.core)
        shots = shotBrowser.onShotBrowserTriggered(task)
        if not shots:
            return
        for s in shots:
            print(s["shot_path"])

    def _projectNameFromFile(self, filePath):
        base = os.path.splitext(os.path.basename(filePath))[0]
        return re.sub(r"_v\d+$", "", base)

    def _safetyExport(self, projectName):
        folder = os.path.join(os.getenv("LOCALAPPDATA", tempfile.gettempdir()),
                            "PrismResolve", "SafetyBackups")
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(folder, "%s_%s.drp" % (projectName, stamp))
        pm = self.resolve.GetProjectManager()
        if not pm.ExportProject(projectName, dest, True):
            raise RuntimeError("Export de sécurité impossible pour '%s'" % projectName)
        return dest

    @err_catcher(name=__name__)
    def OpenScene(self):
        filePath, _ = QFileDialog.getOpenFileName(
            None, "Open scene", self.getScenefilesRoot(), "DaVinci Resolve project (*.drp)")
        if not filePath:
            return

        pm = self.resolve.GetProjectManager()
        projectName = self._projectNameFromFile(filePath)

        if projectName in (pm.GetProjectListInCurrentFolder() or []):
            answer = self.core.popupQuestion(
                "Un projet nommé '%s' existe déjà sur ce PC.\n\n"
                "Il va être supprimé et remplacé par le fichier choisi.\n"
                "Si vous n'avez pas fait de Save Version, votre travail local ne sera conservé "
                "que dans une copie de sécurité exportée automatiquement." % projectName,
                title="Projet existant",
                buttons=["Supprimer et ouvrir", "Annuler"],
            )
            if answer != "Supprimer et ouvrir":
                return

            current = pm.GetCurrentProject()
            isCurrent = bool(current) and current.GetName() == projectName
            if isCurrent and hasattr(pm, "SaveProject"):
                pm.SaveProject()

            safetyFile = self._safetyExport(projectName)

            if isCurrent:
                pm.CloseProject(current)

            if not pm.DeleteProject(projectName):
                raise RuntimeError("Suppression impossible de '%s'.\nCopie de sécurité : %s"
                                % (projectName, safetyFile))

        if not pm.ImportProject(filePath):
            raise RuntimeError("Import impossible : %s" % filePath)

        if not pm.LoadProject(projectName):
            raise RuntimeError("Le projet '%s' a été importé mais n'a pas pu être ouvert." % projectName)

        # On ne mémorise l'état du master que si c'est bien le master qu'on vient d'ouvrir
        try:
            isMaster = (os.path.normcase(os.path.abspath(filePath))
                        == os.path.normcase(os.path.abspath(self._masterFile())))
        except RuntimeError:
            isMaster = False
        if isMaster:
            self._recordMaster()

    @err_catcher(name=__name__)
    def BakeCurrentShot(self):
        print("bakeCurrentShot in Function found")
        
    @err_catcher(name=__name__)
    def Render(self):
        print("Render in Function found")