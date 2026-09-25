import hou
import os
from Scripts.DaisyTools.core.core import get_core, houdini_relative_path, USD_FILE_FORMAT, create_master
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.version_cleanup import check_version_limit_for_output
from Scripts.DaisyTools.core.dcc.launcher import get_main_window


def _product_path(extension, version):
    info = get_entity_info()
    return get_core().products.generateProductPath(
        entity=info["entity"],
        task=info["task"],
        extension=f".{extension.lstrip('.')}",
        version=version,
        location="global",
    )

def create_path(hda):
    extension = hda.parm("extension").evalAsString()
    return houdini_relative_path(_product_path(extension, None))


def create_master_path(hda):
    # Le master est un simple wrapper sublayer/clips : son format suit
    # usd_file_format dans config.json, pas l'extension du fichier versionné
    return _product_path(USD_FILE_FORMAT, "master")


def update_path(hda=None, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()
    try:
        hda.parm("path").set(create_path(hda))
        hda.parm("masterpath").set(create_master_path(hda))
    except Exception as e:
        # Scène pas encore sauvée dans Prism, pas d'entity : on ne bloque pas
        print(f"[{hda.path()}] update_path: {e}")

def save_master(hda):
    node = hou.pwd()
    hda = hda or hou.pwd()

    file_path = hda.parm("path").eval()
    master_path = hda.parm("masterpath").eval()

    if not file_path or not master_path:
        raise hou.Error(f"Chemins manquants : path='{file_path}' masterpath='{master_path}'")

    default_prim = hda.parm("defaultprim").eval().lstrip("/")

    rel_path = os.path.relpath(file_path, os.path.dirname(master_path)).replace("\\", "/")
    if not rel_path.startswith("."):
        rel_path = "./" + rel_path

    if node.parm("trange").eval() == 0:
        frame_range = None
    else:
        frame_range = (int(node.parm("f1").eval()), int(node.parm("f2").eval()))

    create_master(rel_path, master_path, default_prim=default_prim, frame_range=frame_range)


def save_version_info():
    core = get_core()
    info = get_entity_info()
    entity = info["entity"]
    task = info["task"]

    scene = core.getCurrentFileName()
    details = core.getScenefileData(scene)
    details.pop("filename", None)
    details.pop("extension", None)
    details["version"] = core.products.getProductDataFromFilepath(file_path).get("version", "")
    details["sourceScene"] = scene
    details["product"] = task
    details["comment"] = ""

    info_path = core.products.getVersionInfoPathFromProductFilepath(file_path)
    core.saveVersionInfo(filepath=info_path, details=details)

    master_info_path = core.products.getVersionInfoPathFromProductFilepath(master_path)
    core.saveVersionInfo(filepath=master_info_path, details=details)

    check_version_limit_for_output(core, entity, task, file_path, parent=get_main_window())