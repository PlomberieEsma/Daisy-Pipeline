import hou
import os
from Scripts.DaisyTools.core.core import get_core, houdini_relative_path, USD_FILE_FORMAT, create_master
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.version_cleanup import check_version_limit_for_output
from Scripts.DaisyTools.core.dcc.launcher import get_main_window

PROXY_WEDGE = "proxy"

def _product_path(extension, version, wedge=None):
    info = get_entity_info()
    kwargs = dict(
        entity=info["entity"],
        task=info["task"],
        extension=f".{extension.lstrip('.')}",
        version=version,
        location="global",
    )
    if wedge:
        kwargs["wedge"] = wedge
    return get_core().products.generateProductPath(**kwargs)

def create_path(hda):
    extension = hda.parm("extension").evalAsString()
    return houdini_relative_path(_product_path(extension, None))

def create_master_path(hda):
    # Le master est un simple wrapper sublayer/clips : son format suit
    # usd_file_format dans config.json, pas l'extension du fichier versionné
    return _product_path(USD_FILE_FORMAT, "master")

def create_proxy_path(hda):
    extension = hda.parm("extension").evalAsString()
    return houdini_relative_path(_product_path(extension, None, wedge=PROXY_WEDGE))


def create_proxy_master_path(hda):
    return _product_path(USD_FILE_FORMAT, "master", wedge=PROXY_WEDGE)


def has_proxy_input(hda):
    inputs = hda.inputs()
    return len(inputs) > 1 and inputs[1] is not None

def update_path(hda=None, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()
    try:
        hda.parm("path").set(create_path(hda).replace("\\", "\\\\"))
        hda.parm("masterpath").set(create_master_path(hda).replace("\\", "\\\\"))

        if has_proxy_input(hda):
            hda.parm("proxypath").set(create_proxy_path(hda).replace("\\", "\\\\"))
            hda.parm("proxymasterpath").set(create_proxy_master_path(hda).replace("\\", "\\\\"))
        else:
            hda.parm("proxypath").set("")
            hda.parm("proxymasterpath").set("")
    except Exception as e:
        print(f"[{hda.path()}] update_path: {e}")

def save_master(hda=None, file_parm="path", master_parm="masterpath"):
    hda = hda or hou.pwd()

    if not hda.parm("updatemaster").evalAsInt():
        return None

    file_path = hda.parm(file_parm).eval()
    master_path = hda.parm(master_parm).eval()

    if not file_path or not master_path:
        raise hou.NodeError(f"Chemins manquants : {file_parm}='{file_path}' {master_parm}='{master_path}'")

    default_prim = hda.parm("defaultprim").eval().lstrip("/")

    if hda.parm("trange").evalAsInt() == 0:
        frame_range = None
    else:
        frame_range = (hda.parm("f1").evalAsInt(), hda.parm("f2").evalAsInt())

    return create_master(file_path, master_path, default_prim=default_prim, frame_range=frame_range)

def update_thumbnail(hda, core, path):
    if not hda.parm("updateThumbnail").evalAsInt():
        return

    # Réglage Prism utilisateur : on l'active s'il ne l'est pas encore
    if not core.products.getUseProductPreviews():
        core.setConfig("globals", "capture_viewport_products", True, config="user")

    preview = core.products.generateProductPreview()
    if not preview:
        print(f"[{hda.path()}] update_thumbnail: aucune preview générée")
        return

    core.products.setProductPreview(os.path.dirname(path), preview)

    # Preview à côté du fichier de scène : <Asset>_<Task>_v<version>preview.jpg
    scene = core.getCurrentFileName()
    if scene:
        scene_preview = os.path.splitext(scene)[0] + "preview.jpg"
        if not preview.save(scene_preview, "JPG"):
            print(f"[{hda.path()}] update_thumbnail: échec d'écriture {scene_preview}")

def _finalize_export(hda, file_parm, master_parm, thumbnail=True):
    # Tout ce qui suit l'écriture d'un fichier : master, versioninfo, thumbnail, cleanup
    core = get_core()
    info = get_entity_info()
    entity = info["entity"]
    task = info["task"]

    path = hda.parm(file_parm).eval()
    master_path = hda.parm(master_parm).eval()
    update_master = hda.parm("updatemaster").evalAsInt()

    if update_master:
        save_master(hda, file_parm=file_parm, master_parm=master_parm)

    details = dict(entity)
    details["version"] = core.products.getProductDataFromFilepath(path).get("version", "")
    details["sourceScene"] = core.getCurrentFileName()
    details["product"] = task
    details["comment"] = hda.parm("comment").eval()

    info_path = core.products.getVersionInfoPathFromProductFilepath(path)
    core.saveVersionInfo(filepath=info_path, details=details)

    if thumbnail:
        update_thumbnail(hda, core, path)

    if update_master:
        master_info_path = core.products.getVersionInfoPathFromProductFilepath(master_path)
        core.saveVersionInfo(filepath=master_info_path, details=details)

    check_version_limit_for_output(core, entity, task, path, parent=get_main_window())

def post_export(hda=None):
    hda = hda or hou.pwd()
    _finalize_export(hda, "path", "masterpath", thumbnail=True)

def proxy_post_export(hda=None):
    hda = hda or hou.pwd()
    if not has_proxy_input(hda):
        return
    _finalize_export(hda, "proxypath", "proxymasterpath", thumbnail=False)

def on_export(kwargs):
    hda = kwargs["node"]
    update_path(hda)
    hda.node("usd_rop1").parm("execute").pressButton()
    if has_proxy_input(hda):
        hda.node("usd_rop2").parm("execute").pressButton()