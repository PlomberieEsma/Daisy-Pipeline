import hou
import os
from Scripts.DaisyTools.core.core import get_core, houdini_relative_path, USD_FILE_FORMAT, create_master, create_master_clips
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.version_cleanup import check_version_limit_for_output
from Scripts.DaisyTools.core.dcc.launcher import get_main_window

PROXY_WEDGE = "proxy"
FILE_PER_FRAME = "fileperframe"
FRAME_TOKEN = ".$F4"


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
    return _product_path(USD_FILE_FORMAT, "master")


def create_proxy_path(hda):
    extension = hda.parm("extension").evalAsString()
    return houdini_relative_path(_product_path(extension, None, wedge=PROXY_WEDGE))


def create_proxy_master_path(hda):
    base, ext = os.path.splitext(create_master_path(hda))
    return f"{base}_{PROXY_WEDGE}{ext}"


def has_proxy_input(hda):
    inputs = hda.inputs()
    return len(inputs) > 1 and inputs[1] is not None


def _get_frame_range(hda):
    if hda.parm("trange").evalAsInt() == 0:
        return None
    # f1/f2 sont des parms float (frame range Houdini) : evalAsInt() lève une TypeError
    return (int(round(hda.parm("f1").eval())), int(round(hda.parm("f2").eval())))


def is_file_per_frame(hda):
    frame_range = _get_frame_range(hda)
    if not frame_range or frame_range[0] == frame_range[1]:
        return False
    return hda.parm("animationtype").evalAsString() == FILE_PER_FRAME


def _with_frame_token(path, per_frame):
    # En file per frame, $F4 dans le chemin suffit : le USD ROP écrit
    # alors un fichier séparé pour chaque frame
    if not per_frame:
        return path
    base, ext = os.path.splitext(path)
    return f"{base}{FRAME_TOKEN}{ext}"


def _base_path(hda, parm_name):
    # Chemin sans numéro de frame (version, versionInfo, clips, cleanup)
    raw = hda.parm(parm_name).unexpandedString().replace(FRAME_TOKEN, "")
    return hou.text.expandString(raw)


def _set_path(parm, value):
    # Si le parm a une expression/keyframe, set() écrirait dans l'expression
    parm.deleteAllKeyframes()
    parm.set(value.replace("\\", "\\\\"))


def update_path(hda=None, strict=False, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()
    try:
        per_frame = is_file_per_frame(hda)

        _set_path(hda.parm("path"), _with_frame_token(create_path(hda), per_frame))
        _set_path(hda.parm("masterpath"), create_master_path(hda))

        if has_proxy_input(hda):
            _set_path(hda.parm("proxypath"), _with_frame_token(create_proxy_path(hda), per_frame))
            _set_path(hda.parm("proxymasterpath"), create_proxy_master_path(hda))
        else:
            for name in ("proxypath", "proxymasterpath"):
                _set_path(hda.parm(name), "")
    except Exception as e:
        print(f"[{hda.path()}] update_path: {e}")
        if strict:
            raise


def _frame_paths(hda, file_parm):
    start, end = _get_frame_range(hda)
    parm = hda.parm(file_parm)
    return [parm.evalAtFrame(frame) for frame in range(int(start), int(end) + 1)]


def save_master(hda=None, file_parm="path", master_parm="masterpath"):
    hda = hda or hou.pwd()

    if not hda.parm("updatemaster").evalAsInt():
        return None

    file_path = _base_path(hda, file_parm)
    master_path = hda.parm(master_parm).eval()

    if not file_path or not master_path:
        raise hou.NodeError(f"Chemins manquants : {file_parm}='{file_path}' {master_parm}='{master_path}'")

    default_prim = hda.parm("defaultprim").eval().lstrip("/")
    frame_range = _get_frame_range(hda)

    if is_file_per_frame(hda):
        frame_paths = _frame_paths(hda, file_parm)
        clips_path = f"{os.path.splitext(file_path)[0]}.clips.usda"
        create_master_clips(frame_paths, frame_range, clips_path, default_prim=default_prim)
        return create_master(clips_path, master_path, default_prim=default_prim, frame_range=frame_range)

    return create_master(file_path, master_path, default_prim=default_prim, frame_range=frame_range)


def update_thumbnail(hda, core, path):
    if not hda.parm("updateThumbnail").evalAsInt():
        return

    if not core.products.getUseProductPreviews():
        core.setConfig("globals", "capture_viewport_products", True, config="user")

    preview = core.products.generateProductPreview()
    if not preview:
        print(f"[{hda.path()}] update_thumbnail: aucune preview générée")
        return

    core.products.setProductPreview(os.path.dirname(path), preview)

    scene = core.getCurrentFileName()
    if scene:
        scene_preview = os.path.splitext(scene)[0] + "preview.jpg"
        if not preview.save(scene_preview, "JPG"):
            print(f"[{hda.path()}] update_thumbnail: échec d'écriture {scene_preview}")


def _check_written(hda, file_parm):
    if is_file_per_frame(hda):
        missing = [p for p in _frame_paths(hda, file_parm) if not os.path.isfile(p)]
        if missing:
            raise hou.NodeError(f"{len(missing)} frame(s) manquante(s), ex : '{missing[0]}'")
    else:
        path = hda.parm(file_parm).eval()
        if not path or not os.path.isfile(path):
            raise hou.NodeError(f"Fichier exporté introuvable : '{path}'")


def _finalize_export(hda, file_parm, master_parm, thumbnail=True, master_info=True):
    core = get_core()
    info = get_entity_info()
    entity = info["entity"]
    task = info["task"]

    path = _base_path(hda, file_parm)
    master_path = hda.parm(master_parm).eval()
    update_master = hda.parm("updatemaster").evalAsInt()

    _check_written(hda, file_parm)

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

    if update_master and master_info:
        master_info_path = core.products.getVersionInfoPathFromProductFilepath(master_path)
        core.saveVersionInfo(filepath=master_info_path, details=details)

    check_version_limit_for_output(core, entity, task, path, parent=get_main_window())


def post_export(hda=None):
    hda = hda or hou.pwd()
    _finalize_export(hda, "path", "masterpath", thumbnail=True, master_info=True)


def proxy_post_export(hda=None):
    hda = hda or hou.pwd()
    if not has_proxy_input(hda):
        return
    _finalize_export(hda, "proxypath", "proxymasterpath", thumbnail=False, master_info=False)


def _set_wait_text(wait, text):
    if getattr(wait, "msg", None):
        wait.msg.setText(text)
    try:
        from PySide6.QtCore import QCoreApplication
    except ImportError:
        from PySide2.QtCore import QCoreApplication
    QCoreApplication.processEvents()


def _render_rop(rop):
    rop.parm("execute").pressButton()
    errors = rop.errors()
    if errors:
        raise hou.NodeError(f"{rop.path()} : {' / '.join(errors)}")


def on_export(kwargs):
    hda = kwargs["node"]
    core = get_core()
    export_proxy = has_proxy_input(hda)

    wait = core.waitPopup(core, "Mise à jour des chemins...", title="Daisy Export")
    with wait:
        update_path(hda, strict=True)

        _set_wait_text(wait, "Export USD en cours...")
        _render_rop(hda.node("usd_rop1"))

        if export_proxy:
            _set_wait_text(wait, "Export du proxy en cours...")
            _render_rop(hda.node("usd_rop2"))

    # Post-export hors du render loop et hors du popup
    post_export(hda)
    if export_proxy:
        proxy_post_export(hda)