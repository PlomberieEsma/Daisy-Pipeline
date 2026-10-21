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


"""Fonctions du plugin Prism pour DaVinci Resolve (callbacks Prism + outils de montage)."""

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
OPEN_TASKS = [("Trailer", "trailer"), ("Layout", "layout"), ("Final", "final")]

class Prism_DaVinciResolve_Functions(object):
    """Fonctions du plugin Prism pour DaVinci Resolve.

    Deux familles de méthodes :
    - les callbacks standard exigés par Prism (startup, sm_*, getFPS...) : pour la
      plupart de simples stubs sans effet sous Resolve ;
    - les fonctions du pipeline de montage (section "Specific functions scripting") :
      sauvegarde / ouverture des projets .drp (master et backups), Shot Browser, rendu.

    Convention de nommage, par task (trailer, layout, final...) :
    - projet master : "<task>_master"  -> fichier <task>_master.drp
    - projet backup : "<task>_v####"   -> fichier Backups/<task>_v####.drp
    - dossier de task : <projet Prism>/04_Editing/Scenefiles/NN_<task>

    Attributs utilisés : self.core (core Prism), self.plugin et self.resolve
    (objet Resolve de l'API de script, à fournir sur l'instance par le plugin).
    """
    def __init__(self, core, plugin):
        """Initialise le plugin.

        Args:
            core: instance du core Prism (projectPath, popup, popupQuestion, entities...).
            plugin: instance du plugin Prism DaVinciResolve.
        """
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

        """Callback Prism appelé au démarrage du plugin.

        Arrête le timer de démarrage, crée le widget parent des messages
        (origin.messageParent, toujours au premier plan si core.useOnTop) et lance
        le timer d'autosave.

        Args:
            origin: objet d'intégration Prism (porte timer, messageParent...).
        """
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
        """Indique à Prism si l'autosave est actif.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            bool: toujours False (autosave non géré sous Resolve).
        """
        return False

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        """Callback Prism après ouverture d'une scène : relance le timer d'autosave
        si core.shouldAutosaveTimerRun() le demande.

        Args:
            origin: objet d'intégration Prism.
        """
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        """Nom ou chemin du fichier de scène courant.

        Args:
            origin: objet d'intégration Prism.
            path: True si Prism attend le chemin complet, False pour le nom seul
                (ignoré ici).

        Returns:
            str: toujours "" (un projet Resolve n'est pas un fichier de scène Prism).
        """
        return ""

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        """Extension des fichiers de scène du plugin.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            str: première valeur de self.sceneFormats (liste définie par le plugin).
        """
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        # save scenefile
        """Stub : ne sauvegarde rien (la sauvegarde passe par SaveVersion /
        SaveBackUpVersion).

        Args:
            origin: objet d'intégration Prism.
            filepath: chemin de scène demandé par Prism (ignoré).
            details: métadonnées de la version (ignorées).

        Returns:
            bool: toujours True.
        """
        return True

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        """Stub : chemins des fichiers importés dans la scène.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            list: toujours [].
        """
        return []

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        """Stub : plage d'images de la scène.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            list: [0, 100] (valeurs fixes, la timeline n'est pas lue).
        """
        startframe = 0
        endframe = 100

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        """Stub : ne fait rien.

        Args:
            origin: objet d'intégration Prism.
            startFrame: première image demandée.
            endFrame: dernière image demandée.
        """
        pass

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        """Stub : cadence de la scène.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            int: toujours 24.
        """
        return 24

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        """Stub : ne fait rien.

        Args:
            origin: objet d'intégration Prism.
            fps: cadence demandée.
        """
        pass

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        """Stub : version de l'application.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            str: toujours "1.0".
        """
        return "1.0"

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        # load scenefile
        """Stub du callback Prism d'ouverture de scène : n'ouvre rien.
        L'ouverture réelle d'un projet passe par OpenScene() (avec majuscule).

        Args:
            origin: objet d'intégration Prism.
            filepath: fichier demandé par Prism (ignoré).
            force: ouverture forcée (ignoré).

        Returns:
            bool: toujours True.
        """
        return True

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin, objects=None):
        """Ajoute des objets à la liste d'export du State Manager (origin.nodes),
        rafraîchit l'interface et sauve les states.

        Args:
            origin: état d'export du State Manager.
            objects: objets à ajouter. Si None, liste vide (la lecture de la
                sélection de la scène, prévue par le template, n'est pas implémentée).
        """
        if not objects:
            objects = []  # get selected objects from scene

        for i in objects:
            if not i in origin.nodes:
                origin.nodes.append(i)

        origin.updateUi()
        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getNodeName(self, origin, node):
        """Nom affichable d'un node.

        Args:
            origin: objet d'intégration Prism.
            node: objet node de la scène.

        Returns:
            str: node.name ; "invalid" si le node n'est pas valide ; le node lui-même
            (avec un avertissement Qt) si son nom est illisible.
        """
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
        """Doit sélectionner dans la scène les nodes choisis dans origin.lw_objects.
        L'appel de sélection est commenté : aucun effet réel sous Resolve.

        Args:
            origin: état d'export du State Manager (porte lw_objects et nodes).
        """
        if origin.lw_objects.selectedItems() != []:
            nodes = []
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.isNodeValid(origin, node):
                    nodes.append(node)
            # select(nodes)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, handle):
        """Stub : validité d'un node.

        Args:
            origin: objet d'intégration Prism.
            handle: node à tester.

        Returns:
            bool: toujours True.
        """
        return True

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        """Stub : liste des caméras de la scène.

        Args:
            origin: objet d'intégration Prism.
            cur: si True, ajoute "Current View" en tête de liste.

        Returns:
            list: [] ou ["Current View"].
        """
        sceneCams = []  # get cams from scene
        if cur:
            sceneCams = ["Current View"] + sceneCams

        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        """Nom d'une caméra.

        Args:
            origin: objet d'intégration Prism.
            handle: caméra ou "Current View".

        Returns:
            str: "Current View" si handle vaut ce texte. Sinon la ligne finale
            référence `nodes`, variable non définie (reste du template, jamais
            appelée sous Resolve).
        """
        if handle == "Current View":
            return handle

        return str(nodes[0])

    @err_catcher(name=__name__)
    def selectCam(self, origin):
        """Doit sélectionner la caméra courante. Appelle `select`, fonction non
        définie ici (reste du template, jamais appelée sous Resolve).

        Args:
            origin: état d'export (porte curCam).
        """
        if self.isNodeValid(origin, origin.curCam):
            select(origin.curCam)

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        """Stub : initialisation de l'état d'export du State Manager.

        Args:
            origin: état d'export.
        """
        pass

    # 	@err_catcher(name=__name__)
    # 	def sm_export_setTaskText(self, origin, prevTaskName, newTaskName):
    # 		origin.l_taskName.setText(newTaskName)

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        """Stub : retire un item du set d'export.

        Args:
            origin: état d'export.
            node: node à retirer.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin):
        """Stub : vide le set d'export.

        Args:
            origin: état d'export.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin):
        """Stub : met à jour la liste des objets d'export.

        Args:
            origin: état d'export.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        """Exporte la caméra courante en .abc puis en .fbx via
        sm_export_exportAppObjects (stub : rien n'est réellement exporté).

        Args:
            origin: état d'export (porte curCam).
            startFrame: première image à exporter.
            endFrame: dernière image à exporter.
            outputName: chemin de sortie sans extension.

        Returns:
            Résultat du dernier export (.fbx).
        """
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
        """Stub : export d'objets depuis l'application.

        Args:
            origin: état d'export.
            startFrame: première image.
            endFrame: dernière image.
            outputName: chemin de sortie complet, extension comprise.
            scaledExport: export avec mise à l'échelle.
            nodes: objets à exporter.
            expType: extension / type d'export (".abc", ".fbx"...).

        Returns:
            None.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin):
        """Stub : appelé avant la suppression d'un state d'export.

        Args:
            origin: état d'export.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_unColorObjList(self, origin):
        """Remet la bordure grise (50,50,50) de la liste des objets d'export.

        Args:
            origin: état d'export (porte lw_objects).
        """
        origin.lw_objects.setStyleSheet(
            "QListWidget { border: 3px solid rgb(50,50,50); }"
        )

    @err_catcher(name=__name__)
    def sm_export_typeChanged(self, origin, idx):
        """Stub : appelé quand le type d'export change.

        Args:
            origin: état d'export.
            idx: index du nouveau type.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        """Stub : vérifications avant export.

        Args:
            origin: état d'export.
            startFrame: première image.
            endFrame: dernière image.

        Returns:
            list: avertissements à afficher (toujours vide).
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_export_loadData(self, origin, data):
        """Stub : recharge les réglages sauvegardés d'un state d'export.

        Args:
            origin: état d'export.
            data: dictionnaire des réglages sauvegardés.
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_getStateProps(self, origin, stateProps):
        """Complète les propriétés du state d'export spécifiques à l'application
        (aucune ici).

        Args:
            origin: état d'export.
            stateProps: dictionnaire des propriétés du state.

        Returns:
            dict: stateProps, inchangé.
        """
        stateProps.update()

        return stateProps

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin):
        """Stub : initialisation de l'état de rendu.

        Args:
            origin: état de rendu.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_getRenderLayer(self, origin):
        """Stub : couches de rendu de la scène.

        Args:
            origin: état de rendu.

        Returns:
            list: noms des couches (toujours vide).
        """
        rlayerNames = []

        return rlayerNames

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin):
        """Stub : rafraîchit la liste des passes de rendu.

        Args:
            origin: état de rendu.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin, item=None):
        """Stub : ouvre la fenêtre des passes de rendu.

        Args:
            origin: état de rendu.
            item: item cliqué, optionnel.
        """
        pass

    @err_catcher(name=__name__)
    def removeAOV(self, aovName):
        """Stub : supprime une passe (AOV).

        Args:
            aovName: nom de la passe.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        """Stub : appelé avant l'envoi d'un rendu.

        Args:
            origin: état de rendu.
            rSettings: dictionnaire des réglages de rendu.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        """Stub : lance un rendu local.

        Args:
            origin: état de rendu.
            outputName: chemin de sortie du rendu.
            rSettings: dictionnaire des réglages de rendu.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin, rSettings):
        """Stub : annule les réglages de rendu appliqués temporairement.

        Args:
            origin: état de rendu.
            rSettings: dictionnaire des réglages à restaurer.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        """Stub : paramètres Deadline spécifiques à l'application.

        Args:
            origin: état de rendu.
            dlParams: dictionnaire des paramètres Deadline.
            homeDir: dossier utilisateur Deadline.
        """
        pass

    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin):
        """Stub : moteur de rendu courant.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            str: toujours "Renderer".
        """
        return "Renderer"

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        """Fichiers de la scène courante.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            list: [self.core.getCurrentFileName()].
        """
        curFileName = self.core.getCurrentFileName()
        scenefiles = [curFileName]
        return scenefiles

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin):
        """Stub : passes de rendu disponibles.

        Args:
            origin: état de rendu.

        Returns:
            list: toujours vide.
        """
        return []

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin, passName, steps):
        """Stub : ajoute une passe de rendu.

        Args:
            origin: état de rendu.
            passName: nom de la passe.
            steps: étapes / réglages de la passe.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        """Stub : vérifications avant rendu.

        Args:
            origin: état de rendu.

        Returns:
            list: avertissements à afficher (toujours vide).
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def getProgramVersion(self, origin):
        """Stub : version du programme.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            str: toujours "1.0".
        """
        return "1.0"

    @err_catcher(name=__name__)
    def sm_render_getDeadlineSubmissionParams(self, origin, dlParams, jobOutputFile):
        """Complète les paramètres d'envoi Deadline : Build, OutputFilePath
        (dossier de sortie), OutputFilePrefix (nom sans extension), Renderer et,
        si la résolution est surchargée, ImageWidth / ImageHeight.

        Args:
            origin: état de rendu (porte chb_resOverride, sp_resWidth, sp_resHeight).
            dlParams: dictionnaire des paramètres Deadline (doit contenir "build").
            jobOutputFile: chemin complet du fichier de sortie du job.

        Returns:
            dict: dlParams complété.
        """
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
        """Stub : supprime des nodes de la scène.

        Args:
            origin: objet d'intégration Prism.
            handles: nodes à supprimer.
            num: indice optionnel (non utilisé).
        """
        pass

    @err_catcher(name=__name__)
    def sm_import_disableObjectTracking(self, origin):
        """Arrête le suivi des objets importés en supprimant le node set d'import.

        Args:
            origin: état d'import (porte setName).
        """
        self.deleteNodes(origin, [origin.setName])

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        """Doit importer un fichier dans l'application. Le corps réfère `result`,
        variable non définie (reste du template, jamais appelée sous Resolve).

        Args:
            origin: état d'import.
            doImport: True pour importer réellement.
            update: True pour mettre à jour un import existant.
            impFileName: chemin du fichier à importer.

        Returns:
            dict: {"result": ..., "doImport": doImport}.
        """
        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin):
        """Stub : met à jour la liste des objets importés.

        Args:
            origin: état d'import.
        """
        pass

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin):
        """Stub : retire les namespaces des objets importés.

        Args:
            origin: état d'import.
        """
        pass

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin):
        """Initialise le state Playblast : reporte la plage de getFrameRange()
        dans les champs sp_rangeStart / sp_rangeEnd.

        Args:
            origin: état Playblast.
        """
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        """Stub : crée le playblast.

        Args:
            origin: état Playblast.
            jobFrames: plage d'images à capturer.
            outputName: chemin de sortie.
        """
        pass

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin):
        """Stub : vérifications avant playblast.

        Args:
            origin: état Playblast.

        Returns:
            list: avertissements à afficher (toujours vide).
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin):
        """Stub : exécute le playblast.

        Args:
            origin: état Playblast.
        """
        pass

    @err_catcher(name=__name__)
    def sm_playblast_postExecute(self, origin):
        """Stub : appelé après le playblast.

        Args:
            origin: état Playblast.
        """
        pass

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        """Stub : écrit les states du State Manager dans la scène.

        Args:
            origin: objet d'intégration Prism.
            buf: contenu texte à sauvegarder.
        """
        pass

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        """Stub : écrit la liste des imports dans la scène.

        Args:
            origin: objet d'intégration Prism.
            importPaths: chemins des fichiers importés.
        """
        pass

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        """Stub : relit les states sauvegardés dans la scène.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            list: toujours vide.
        """
        return []

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        """Stub : supprime les states sauvegardés dans la scène.

        Args:
            origin: objet d'intégration Prism.
        """
        pass

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        """Stub : fichiers externes référencés par la scène.

        Args:
            origin: objet d'intégration Prism.

        Returns:
            list: [fichiers externes, fichiers à ignorer], les deux listes vides.
        """
        extFiles = []
        return [extFiles, []]

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin):
        """Callback du bouton "Create Render" : crée un state de type "Render".

        Args:
            origin: State Manager.
        """
        origin.createPressed("Render")



    ##############################################################################################################
    # Specific functions scripting
    ##############################################################################################################

    def getScenefilesRoot(self):
        """Racine des fichiers de scène de montage.

        Returns:
            str: <projet Prism>/04_Editing/Scenefiles.
        """
        return os.path.join(self.core.projectPath, "04_Editing", "Scenefiles")

    def getTask(self):
        # "trailer_master" / "trailer_v0003" -> "trailer"
        """Task du projet Resolve courant : son nom sans suffixe "_master" ni
        "_v####" (insensible à la casse).

        Exemples : "trailer_master" -> "trailer" ; "layout_v0003" -> "layout".

        Returns:
            str: nom de la task.
        """
        return re.sub(r"_(master|v\d+)$", "", self._projectName(), flags=re.I)

    def _masterFile(self):
        # Toujours <task>_master.drp, quel que soit le nom du projet Resolve
        """Chemin du fichier master de la task courante, quel que soit le nom du
        projet Resolve ouvert (master ou backup).

        Returns:
            str: <dossier de task>/<task>_master.drp (le fichier peut ne pas exister).

        Raises:
            RuntimeError: si aucun dossier de task ne correspond (voir getTaskFolder).
        """
        task = self.getTask()
        return os.path.join(self.getEditingScenefilePath(), "%s_master.drp" % task)

    def findTaskFolder(self, task):
        """Cherche le dossier "NN_<task>" (NN = 2 chiffres) dans Scenefiles.

        Args:
            task: nom de la task, sans préfixe numérique, insensible à la casse
                (ex. "trailer").

        Returns:
            str | None: nom du dossier (ex. "00_trailer"), ou None s'il n'existe pas.
        """
        root = self.getScenefilesRoot()
        if not os.path.isdir(root):
            return None
        for folder in sorted(os.listdir(root)):
            m = TASK_FOLDER_PATTERN.match(folder)
            if m and m.group(1).lower() == task.lower() and os.path.isdir(os.path.join(root, folder)):
                return folder
        return None

    def getTaskFolder(self, task=None):
        """Comme findTaskFolder, mais lève une erreur si le dossier est introuvable.

        Args:
            task: nom de la task ; si None, task du projet Resolve courant.

        Returns:
            str: nom du dossier de task (ex. "00_trailer").

        Raises:
            RuntimeError: si aucun dossier ne correspond.
        """
        task = task or self.getTask()
        folder = self.findTaskFolder(task)
        if folder:
            return folder
        raise RuntimeError("Le projet Resolve '%s' ne correspond à aucun dossier de task dans :\n%s"
                        % (self._projectName(), self.getScenefilesRoot()))

    def getMasterFileForTask(self, task):
        """Chemin du master d'une task donnée, uniquement s'il existe sur disque.

        Args:
            task: nom de la task (ex. "layout").

        Returns:
            str | None: chemin de <task>_master.drp, ou None si le dossier ou le
            fichier est absent.
        """
        folder = self.findTaskFolder(task)
        if not folder:
            return None
        path = os.path.join(self.getScenefilesRoot(), folder, "%s_master.drp" % task)
        return path if os.path.isfile(path) else None

    def listBackupsForTask(self, task):
        """Liste les backups <task>_v####.drp du dossier Backups d'une task.

        Args:
            task: nom de la task (ex. "trailer").

        Returns:
            list[tuple[int, str]]: [(numéro de version, chemin)], du plus récent au
            plus ancien ; [] s'il n'y en a pas.
        """
        folder = self.findTaskFolder(task)
        if not folder:
            return []
        backupsDir = os.path.join(self.getScenefilesRoot(), folder, "Backups")
        if not os.path.isdir(backupsDir):
            return []
        pattern = re.compile(r"^%s_v(\d+)\.drp$" % re.escape(task), re.I)
        out = []
        for f in os.listdir(backupsDir):
            m = pattern.match(f)
            if m:
                out.append((int(m.group(1)), os.path.join(backupsDir, f)))
        return sorted(out, reverse=True)

    def getEditingScenefilePath(self):
        """Dossier des fichiers de scène de la task du projet Resolve courant.

        Returns:
            str: <projet>/04_Editing/Scenefiles/NN_<task>.

        Raises:
            RuntimeError: si le dossier de task est introuvable.
        """
        task=self.getTaskFolder()
        path=os.path.join(self.core.projectPath,"04_Editing", "Scenefiles", task)
        return path

    def getEditingRenderPath(self):
        """Dossier de sortie des rendus de la task du projet Resolve courant.

        Returns:
            str: <projet>/04_Editing/Output/NN_<task>.

        Raises:
            RuntimeError: si le dossier de task est introuvable.
        """
        task=self.getTaskFolder()
        path=os.path.join(self.core.projectPath,"04_Editing", "Output", task)
        return path

    def _projectName(self):
        """Nom du projet Resolve actuellement ouvert.

        Returns:
            str: ex. "trailer_master" ou "trailer_v0003".
        """
        return self.resolve.GetProjectManager().GetCurrentProject().GetName()

    def _renameCurrentProject(self, newName):
        """Renomme le projet Resolve courant. Si un autre projet local porte déjà ce
        nom, demande confirmation, en fait une copie de sécurité (_safetyExport)
        puis le supprime avant de renommer.

        Args:
            newName: nouveau nom du projet (ex. "trailer_master").

        Returns:
            bool: True si le projet porte maintenant ce nom (ou le portait déjà) ;
            False si l'utilisateur a annulé le remplacement.

        Raises:
            RuntimeError: si la suppression ou le renommage échoue.
        """
        pm = self.resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if project.GetName() == newName:
            return True

        if newName in (pm.GetProjectListInCurrentFolder() or []):
            answer = self.core.popupQuestion(
                "Un autre projet nommé '%s' existe déjà sur ce PC.\n\n"
                "Il va être remplacé par le projet courant (copie de sécurité automatique)." % newName,
                title="Projet existant",
                buttons=["Remplacer", "Annuler"],
            )
            if answer != "Remplacer":
                return False
            self._safetyExport(newName)
            if not pm.DeleteProject(newName):
                raise RuntimeError("Suppression impossible de '%s'." % newName)

        if not project.SetName(newName):
            raise RuntimeError("Renommage impossible : '%s' -> '%s'" % (project.GetName(), newName))
        return True

    # --- état local : "quelle version du master ai-je vue en dernier ?" ---

    def _stateFile(self):
        """Fichier d'état local qui mémorise la date du master vu en dernier.

        Crée le dossier si besoin.

        Returns:
            str: %LOCALAPPDATA%/PrismResolve/master_state.json (dossier temporaire
            système si LOCALAPPDATA n'est pas défini).
        """
        base = os.path.join(os.getenv("LOCALAPPDATA", tempfile.gettempdir()), "PrismResolve")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "master_state.json")

    def _loadState(self):
        """Lit le fichier d'état local.

        Returns:
            dict: {chemin du master: date de modification connue} ; {} si le
            fichier est absent ou illisible.
        """
        try:
            with open(self._stateFile(), "r") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _recordMaster(self):
        """Enregistre la date de modification actuelle du master (si le fichier
        existe) dans le fichier d'état. SaveVersion s'en sert ensuite pour détecter
        une modification du master par quelqu'un d'autre.
        """
        master = self._masterFile()
        if os.path.exists(master):
            state = self._loadState()
            state[master] = os.path.getmtime(master)
            with open(self._stateFile(), "w") as f:
                json.dump(state, f)

    def _exportDrp(self, destFile):
        """Exporte le projet Resolve courant vers un fichier .drp (avec stills et
        LUTs). L'export passe par un dossier temporaire puis est copié à destination,
        dossiers parents créés si besoin.

        Args:
            destFile: chemin complet du .drp à écrire.

        Returns:
            str: nom du projet exporté.

        Raises:
            RuntimeError: si ExportProject échoue.
        """
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
        """Bouton "Save Version" : le projet courant devient le master de sa task.

        Si le master existe et a changé depuis la dernière ouverture ou sauvegarde
        connue, demande confirmation avant de l'écraser. Renomme ensuite le projet
        en "<task>_master", exporte <task>_master.drp et mémorise son état.

        Raises:
            RuntimeError: si le chemin du master est incohérent ou si l'export échoue.
        """
        task = self.getTask()
        master = self._masterFile()
        if os.path.basename(master).lower() != ("%s_master.drp" % task).lower():
            raise RuntimeError("Chemin master inattendu : %s" % master)

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

        # Le projet courant devient le master
        if not self._renameCurrentProject("%s_master" % task):
            return

        self._exportDrp(master)
        self._recordMaster()
        self.core.popup("Master mis à jour.")

    @err_catcher(name=__name__)
    def SaveBackUpVersion(self):
        """Bouton "Save Backup" : exporte une version numérotée Backups/<task>_v####.drp
        (numéro = plus grand existant + 1).

        - Projet courant = backup (nom en _v####) : il est renommé avec le nouveau
          nom, donc on bascule sur la nouvelle version.
        - Projet courant = master (ou autre nom) : pas de renommage, on reste dessus
          et seule une copie est exportée.
        """
        task = self.getTask()
        backupsDir = os.path.join(self.getEditingScenefilePath(), "Backups")

        pattern = re.compile(r"^%s_v(\d+)\.drp$" % re.escape(task), re.I)
        files = os.listdir(backupsDir) if os.path.isdir(backupsDir) else []
        numbers = [int(m.group(1)) for m in map(pattern.match, files) if m]
        version = max(numbers, default=0) + 1
        versionName = "%s_v%04d" % (task, version)

        # Sur une version backup : on bascule sur le projet au nouveau nom.
        # Sur le master : on reste dessus, on exporte seulement une copie.
        onBackup = bool(re.search(r"_v\d+$", self._projectName(), re.I))
        if onBackup:
            if not self._renameCurrentProject(versionName):
                return

        self._exportDrp(os.path.join(backupsDir, versionName + ".drp"))

        if onBackup:
            self.core.popup("Backup v%04d enregistré (projet renommé en '%s')." % (version, versionName))
        else:
            self.core.popup("Backup v%04d enregistré (vous restez sur '%s')."
                            % (version, self._projectName()))

    def _projectNameFromFile(self, filePath):
        # trailer_master.drp -> "trailer_master" ; trailer_v0003.drp -> "trailer_v0003"
        """Nom du projet Resolve correspondant à un fichier .drp.

        Args:
            filePath: chemin du .drp.

        Returns:
            str: nom du fichier sans extension (ex. "trailer_v0003").
        """
        return os.path.splitext(os.path.basename(filePath))[0]

    def _safetyExport(self, projectName):
        """Copie de sécurité d'un projet Resolve local avant suppression ou
        remplacement.

        Args:
            projectName: nom du projet à exporter (doit exister dans Resolve).

        Returns:
            str: chemin de la copie, %LOCALAPPDATA%/PrismResolve/SafetyBackups/
            <projectName>_<date>_<heure>.drp.

        Raises:
            RuntimeError: si l'export échoue.
        """
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
        """Bouton "Open Scene" : affiche OpenSceneDialog (task + master ou backup)
        puis ouvre le .drp choisi avec _openDrpFile. Ne fait rien si le dialogue est
        annulé.
        """
        dlg = OpenSceneDialog(self)
        self.core.parentWindow(dlg)
        if dlg.exec_() != QDialog.Accepted or not dlg.filePath:
            return
        self._openDrpFile(dlg.filePath)

    def _openDrpFile(self, filePath):
        """Importe un .drp dans Resolve et l'ouvre, sous le nom du fichier.

        Étapes : confirmation + copie de sécurité si un projet local du même nom
        existe ; sauvegarde puis fermeture du projet courant ; suppression de
        l'ancien projet homonyme ; import du .drp (nom imposé) ; chargement. Si
        l'import ou le chargement échoue, l'ancien projet est rouvert. Mémorise
        l'état du master si c'est le master qui vient d'être ouvert.

        Args:
            filePath: chemin du .drp à ouvrir.

        Raises:
            RuntimeError: si la suppression, l'import ou le chargement échoue.
        """
        pm = self.resolve.GetProjectManager()
        projectName = self._projectNameFromFile(filePath)

        current = pm.GetCurrentProject()
        currentName = current.GetName() if current else None
        isCurrent = (currentName == projectName)

        # 1) Un projet local du même nom existe déjà : confirmation + copie de sécurité
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
            if isCurrent and hasattr(pm, "SaveProject"):
                pm.SaveProject()
            safetyFile = self._safetyExport(projectName)
        else:
            safetyFile = None

        # 2) Dans tous les cas : on sauvegarde et on ferme le projet courant
        #    (un autre montage du même dossier ouvert peut bloquer l'import / le chargement)
        if current:
            if hasattr(pm, "SaveProject"):
                pm.SaveProject()
            if not pm.CloseProject(current):
                print("[OpenScene] CloseProject a renvoyé False pour '%s'" % currentName)

        # 3) Suppression de l'ancien projet du même nom (désormais fermé)
        if safetyFile:
            if not pm.DeleteProject(projectName):
                if currentName:
                    pm.LoadProject(currentName)
                raise RuntimeError("Suppression impossible de '%s'.\nCopie de sécurité : %s"
                                % (projectName, safetyFile))

        # 4) Import (nom imposé, repli sans nom)
        ok = pm.ImportProject(filePath, projectName)
        print("[OpenScene] ImportProject(%s, %s) -> %s" % (filePath, projectName, ok))
        if not ok:
            ok = pm.ImportProject(filePath)
            print("[OpenScene] ImportProject sans nom -> %s" % ok)
        if not ok:
            if currentName:
                pm.LoadProject(currentName)
            raise RuntimeError("Import impossible : %s" % filePath)

        # 5) Chargement
        if not pm.LoadProject(projectName):
            existing = pm.GetProjectListInCurrentFolder() or []
            print("[OpenScene] LoadProject('%s') a échoué ; projets présents : %s" % (projectName, existing))
            if currentName and currentName != projectName:
                pm.LoadProject(currentName)      # on remet l'ancien projet
            raise RuntimeError("Le projet '%s' a été importé mais n'a pas pu être ouvert.\n"
                            "Projets présents dans le dossier : %s" % (projectName, existing))

        # On ne mémorise l'état du master que si c'est bien le master qu'on vient d'ouvrir
        try:
            isMaster = (os.path.normcase(os.path.abspath(filePath))
                        == os.path.normcase(os.path.abspath(self._masterFile())))
        except RuntimeError:
            isMaster = False
        if isMaster:
            self._recordMaster()

    @err_catcher(name=__name__)
    def AddShot(self):
        """Bouton "Add Shot" : ouvre le Shot Browser en mode "add" pour la task
        courante. La pose des clips est faite par le Shot Browser lui-même ; ici on
        affiche seulement les shot_path validés dans la console.
        """
        task = self.getTask()
        shotBrowser = ShotBrowserUI(self.core)
        shots = shotBrowser.onShotBrowserTriggered(task, action="add")
        if not shots:
            return
        for s in shots:
            print(s["shot_path"])
            
    @err_catcher(name=__name__)
    def BakeCurrentShot(self):
        """Bouton "Bake" : ouvre le Shot Browser en mode "bake" (met à jour les
        shots de la timeline vers une version plus avancée). Le travail est fait
        par le Shot Browser ; ici on affiche seulement les shot_path validés.
        """
        task = self.getTask()
        shotBrowser = ShotBrowserUI(self.core)
        shots = shotBrowser.onShotBrowserTriggered(task, action="bake")
        if not shots:
            return
        for s in shots:
            print(s["shot_path"])
                        
    @err_catcher(name=__name__)
    def ModifyCurrentShot(self):
        """Bouton "Modify" : ouvre le Shot Browser en mode "modify" (choix manuel
        de la version de chaque shot de la timeline). Le travail est fait par le Shot
        Browser ; ici on affiche seulement les shot_path validés.
        """
        task = self.getTask()
        shotBrowser = ShotBrowserUI(self.core)
        shots = shotBrowser.onShotBrowserTriggered(task, action="modify")
        if not shots:
            return
        for s in shots:
            print(s["shot_path"])

    def _nextRenderVersion(self, folder, task):
        """Prochain numéro de version de rendu.

        Args:
            folder: dossier de sortie à examiner (peut ne pas exister).
            task: nom de la task ; on cherche les noms commençant par <task>_v####.

        Returns:
            int: plus grand numéro trouvé + 1 (1 si aucun).
        """
        pattern = re.compile(r"^%s_v(\d+)" % re.escape(task))
        names = os.listdir(folder) if os.path.isdir(folder) else []
        numbers = [int(m.group(1)) for m in map(pattern.match, names) if m]
        return max(numbers, default=0) + 1

    def _shotsRange(self):
        """Plage de rendu de la timeline courante.

        Début : première image du premier clip du Shot Browser, shots et masters
        de séquence confondus (d'après leurs marqueurs). Fin : fin du clip le
        plus éloigné de la timeline, toutes pistes vidéo et audio confondues.

        Returns:
            tuple[int, int] | None: (première image, dernière image incluse), ou None
            s'il n'y a ni timeline ni shot ni master.
        """
        timeline = self.resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
        if not timeline:
            return None

        browser = ShotBrowserUI(self.core)
        shots = browser.getTimelineShots(timeline)
        starts = [ref["start"] for refList in shots.values() for ref in refList]
        ends = [ref["start"] + ref["duration"] for refList in shots.values() for ref in refList]

        # Masters de séquence : frames absolues (origine 0)
        for s, e in browser.getMasterRanges(timeline, 0):
            starts.append(s)
            ends.append(e)

        if not starts:
            return None

        # Fin de timeline : le clip qui finit le plus loin, sur toutes les pistes
        for kind in ("video"):
            try:
                trackCount = timeline.GetTrackCount(kind)
            except Exception:
                continue
            for t in range(1, trackCount + 1):
                for item in timeline.GetItemListInTrack(kind, t) or []:
                    ends.append(item.GetEnd())

        start = min(starts)
        end = max(ends)                                              # fin exclusive
        return int(start), int(end) - 1                              # MarkOut est inclusif

    @err_catcher(name=__name__)
    def ResetCounters(self):
        """Bouton "Reset Counters" : remet à zéro les compteurs Fusion (expressions
        retirées, valeurs neutres) via ShotBrowserUI.resetFrameCounters, puis
        affiche une confirmation.
        """
        ShotBrowserUI(self.core).resetFrameCounters()
        self.core.popup("Compteurs Fusion réinitialisés.")

    @err_catcher(name=__name__)
    def Render(self):
        """Bouton "Render" : prépare la page Deliver de Resolve.

        Dossier = getEditingRenderPath(), nom = <task>_v#### (version suivante).
        La plage rendue (_shotsRange) commence au premier shot ou master de séquence
        et finit à la fin du clip le plus éloigné de la timeline ; sans shot ni
        master, toute la timeline. Ouvre ensuite la page Deliver ; affiche un message si
        Resolve refuse les réglages.
        """
        task = self.getTask()
        folder = self.getEditingRenderPath()
        name = "%s_v%04d" % (task, self._nextRenderVersion(folder, task))
    
        os.makedirs(folder, exist_ok=True)
    
        settings = {
            "TargetDir": folder,        # champ Location
            "CustomName": name,         # champ File name (sans extension)
        }
    
        shotsRange = self._shotsRange()
        if shotsRange:
            settings.update({
                "SelectAllFrames": False,
                "MarkIn": shotsRange[0],
                "MarkOut": shotsRange[1],
            })
        else:
            settings["SelectAllFrames"] = True
            print("[Render] aucun shot du Shot Browser trouvé : timeline entière")
    
        project = self.resolve.GetProjectManager().GetCurrentProject()
        ok = project.SetRenderSettings(settings)
        print("[Render] %s -> %s" % (settings, ok))
        if not ok:
            self.core.popup("Resolve a refusé les réglages de rendu (dossier, nom ou plage invalide).")
            return
    
        self.resolve.OpenPage("deliver")

class OpenSceneDialog(QDialog):
    """Fenêtre "Open Scene" : choix de la task (Trailer / Layout / Final) puis
    du master ou d'une version backup. Après exec_(), l'attribut filePath contient
    le .drp choisi (None si annulé).
    """
    def __init__(self, plugin, parent=None):
        """Construit la fenêtre et présélectionne la task du projet courant si
        possible, sinon la première task disponible.

        Args:
            plugin: instance de Prism_DaVinciResolve_Functions (donne accès aux
                dossiers, master et backups).
            parent: widget parent Qt, optionnel.
        """
        super(OpenSceneDialog, self).__init__(parent)
        self.plugin = plugin
        self.filePath = None
        self.setWindowTitle("Open Scene")
        self.setMinimumWidth(340)

        lo = QVBoxLayout(self)

        # --- Task ---
        lo.addWidget(QLabel("Task :"))
        lo_task = QHBoxLayout()
        self.taskGroup = QButtonGroup(self)
        self.taskButtons = {}
        for label, task in OPEN_TASKS:
            rb = QRadioButton(label)
            rb.setEnabled(plugin.findTaskFolder(task) is not None)
            self.taskGroup.addButton(rb)
            self.taskButtons[task] = rb
            rb.toggled.connect(self._refresh)
            lo_task.addWidget(rb)
        lo.addLayout(lo_task)

        # --- Source : master ou backup ---
        lo.addWidget(QLabel("Version :"))
        self.rb_master = QRadioButton("Master")
        self.rb_backup = QRadioButton("Backup")
        self.cb_backup = QComboBox()
        self.rb_master.toggled.connect(self._updateBackupCombo)
        self.rb_backup.toggled.connect(self._updateBackupCombo)
        lo.addWidget(self.rb_master)
        lo_bk = QHBoxLayout()
        lo_bk.addWidget(self.rb_backup)
        lo_bk.addWidget(self.cb_backup, 1)
        lo.addLayout(lo_bk)

        # --- Boutons ---
        lo_btn = QHBoxLayout()
        lo_btn.addStretch()
        self.btn_open = QPushButton("Open")
        self.btn_open.clicked.connect(self._onOpen)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        lo_btn.addWidget(self.btn_open)
        lo_btn.addWidget(btn_cancel)
        lo.addLayout(lo_btn)

        # Présélection : la task du projet courant si possible, sinon la première dispo
        try:
            current = self.plugin.getTask().lower()
        except Exception:
            current = None
        order = ([current] if current in self.taskButtons else []) + [t for _, t in OPEN_TASKS]
        for task in order:
            if self.taskButtons[task].isEnabled():
                self.taskButtons[task].setChecked(True)
                break
        else:
            self.btn_open.setEnabled(False)

    def currentTask(self):
        """Task actuellement cochée.

        Returns:
            str | None: nom de la task (ex. "layout"), ou None si aucune.
        """
        for task, rb in self.taskButtons.items():
            if rb.isChecked():
                return task
        return None

    def _refresh(self, *args):
        """Recharge master et backups quand la task change : remplit la liste
        déroulante des backups, active ou grise les options et choisit master par
        défaut (sinon backup).

        Args:
            *args: arguments du signal Qt, ignorés.
        """
        task = self.currentTask()
        if not task:
            return
        self.master = self.plugin.getMasterFileForTask(task)
        backups = self.plugin.listBackupsForTask(task)

        self.cb_backup.clear()
        for number, path in backups:
            date = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%y/%m/%d %H:%M")
            self.cb_backup.addItem("v%04d  (%s)" % (number, date), path)

        self.rb_master.setEnabled(bool(self.master))
        self.rb_backup.setEnabled(bool(backups))
        if self.master:
            self.rb_master.setChecked(True)
        elif backups:
            self.rb_backup.setChecked(True)
        self.btn_open.setEnabled(bool(self.master or backups))
        self._updateBackupCombo()

    def _updateBackupCombo(self, *args):
        """Active la liste des backups uniquement si "Backup" est coché et disponible.

        Args:
            *args: arguments du signal Qt, ignorés.
        """
        self.cb_backup.setEnabled(self.rb_backup.isChecked() and self.rb_backup.isEnabled())

    def _onOpen(self):
        """Bouton "Open" : mémorise dans self.filePath le master ou le backup
        choisi, puis ferme la fenêtre avec accept().
        """
        if self.rb_master.isChecked() and self.rb_master.isEnabled():
            self.filePath = self.master
        elif self.rb_backup.isChecked() and self.rb_backup.isEnabled():
            self.filePath = self.cb_backup.currentData()
        if self.filePath:
            self.accept()