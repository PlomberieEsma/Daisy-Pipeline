# PrismInit.py
#
# Ce fichier est copie par Prism_SubstancePainter_Integration.addIntegration()
# dans : %USERPROFILE%\Documents\Adobe\Adobe Substance 3D Painter\python\plugins
#
# Substance Painter le charge automatiquement au demarrage (menu Python),
# ou manuellement via Python > PrismInit dans le menu de SP.

import os
import sys
import json
import logging
logger = logging.getLogger(__name__)

from PySide6 import QtGui
import substance_painter.ui as sp_ui
import substance_painter.event as sp_event
import substance_painter.project as sp_project

pcore = None
prism_menu = None

prismRoot = os.environ.get("PRISM_ROOT", r"C:/Program Files/Prism2")
ICON_PATH = os.path.join(prismRoot, "Plugins", "Apps", "SubstancePainter", "Resources", "daisy_logo.png")


def open_project_browser():
    if pcore is not None:
        pcore.projectBrowser()

def save_version():
    if pcore is not None:
        pcore.saveScene()

def save_comment():
    if pcore is not None and pcore.appPlugin is not None:
        pcore.appPlugin.SaveComment()

def geometry_path():
    if pcore is not None and pcore.appPlugin is not None:
        pcore.appPlugin.GeometryPath()

def export_textures():
    if pcore is not None and pcore.appPlugin is not None:
        pcore.appPlugin.ExportTextures()

def start_plugin():
    global pcore, prism_menu

    if pcore is not None:
        return

    scriptDir = os.path.join(prismRoot, "Scripts")
    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    try:
        import PrismCore
    except Exception as e:
        logger.warning("Impossible d'importer PrismCore: %s" % e)
        raise

    pcore = PrismCore.PrismCore(app="SubstancePainter")

    main_window = sp_ui.get_main_window()
    menu_bar = main_window.menuBar()

    prism_menu = menu_bar.addMenu("Prism")

    if os.path.isfile(ICON_PATH):
        prism_menu.setIcon(QtGui.QIcon(ICON_PATH))

    save_version_action = QtGui.QAction("Save Version", main_window)
    save_version_action.triggered.connect(save_version)
    prism_menu.addAction(save_version_action)

    save_comment_action = QtGui.QAction("Save Comment", main_window)
    save_comment_action.triggered.connect(save_comment)
    prism_menu.addAction(save_comment_action)

    project_browser_action = QtGui.QAction("Project Browser", main_window)
    project_browser_action.triggered.connect(open_project_browser)
    prism_menu.addAction(project_browser_action)

    import_geometry_action = QtGui.QAction("Geometry Path", main_window)
    import_geometry_action.triggered.connect(geometry_path)
    prism_menu.addAction(import_geometry_action)

    export_textures_action = QtGui.QAction("Export Textures", main_window)
    export_textures_action.triggered.connect(export_textures)
    prism_menu.addAction(export_textures_action)

def close_plugin():
    global prism_menu
    if prism_menu is not None:
        main_window = sp_ui.get_main_window()
        main_window.menuBar().removeAction(prism_menu.menuAction())
        prism_menu = None


##############################################################################################################
# Naming for pending scene from temporary json file
##############################################################################################################

def get_pending_file_path():
    if pcore is None or not getattr(pcore, "projectPath", None):
        return None
    return os.path.join(
        pcore.projectPath,
        "00_Pipeline", "Plugins", "SubstancePainter", "tmp",
        "SubstancePainterPending.json",
    )

def check_pending_scene(event):
    pendingFile = get_pending_file_path()
    if not pendingFile or not os.path.isfile(pendingFile):
        return

    try:
        with open(pendingFile, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("Impossible de lire le fichier pending: %s" % e)
        return

    filepath = data.get("filepath")
    if not filepath:
        return

    def onProjectReady(readyEvent):
        sp_event.DISPATCHER.disconnect(sp_event.ProjectEditionEntered, onProjectReady)
        try:
            sp_project.save_as(filepath)

            details = {
                "asset_path": data.get("asset_path", ""),
                "asset": data.get("asset", ""),
                "type": data.get("type", "asset"),
                "department": data.get("department", ""),
                "task": data.get("task", ""),
                "version": data.get("version", ""),
                "comment": data.get("comment", ""),
                "extension": data.get("extension", ""),
                "user": data.get("user", ""),
            }
            pcore.saveSceneInfo(filepath, details=details)

            os.remove(pendingFile)
        except Exception as e:
            logger.warning("Impossible de sauvegarder la scene en attente: %s" % e)

    sp_event.DISPATCHER.connect(sp_event.ProjectEditionEntered, onProjectReady)


# dans start_plugin(), en plus du reste :
sp_event.DISPATCHER.connect(sp_event.ProjectCreated, check_pending_scene)