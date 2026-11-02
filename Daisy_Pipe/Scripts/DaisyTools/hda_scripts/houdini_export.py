import hou
import os
import re
from pxr import Sdf, Vt
from Scripts.DaisyTools.core.core import get_core, houdini_relative_path, USD_FILE_FORMAT, create_master, create_master_clips, USD_CAM_KEYFRAMES, resolve_root_prim
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
from Scripts.DaisyTools.core.version_cleanup import check_version_limit_for_output
from Scripts.DaisyTools.core.dcc.launcher import get_main_window

PROXY_WEDGE = "proxy"
FILE_PER_FRAME = "fileperframe"
FRAME_TOKEN = ".$F4"

CAMERA_NODE_NAME = re.compile(r"^DaisyCam_sq\d+_sh\d+_camShape$")

NEXT_VERSION_PARM = "versions"
VERSION_NUM_PARM = "selectedversion"

DAISY_IMPORT_TYPE = "daisy_import"
LAYER_BREAK_TYPE = "layerbreak"
LAYER_BREAK_PARM = "layerbreak"
STRIP_PARM = "striplayerbreaks"
SAVE_STYLE_PARM = "savestyle"


# ---------- Version ----------

def _selected_version(hda):
    # None = Prism prend la prochaine version dispo
    if hda.parm(NEXT_VERSION_PARM).evalAsInt():
        return None
    num = max(1, hda.parm(VERSION_NUM_PARM).evalAsInt())
    padding = getattr(get_core(), "versionPadding", 4)
    return f"v{num:0{padding}d}"


# ---------- Chemins ----------

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
    return houdini_relative_path(_product_path(extension, _selected_version(hda)))


def create_master_path(hda):
    return _product_path(USD_FILE_FORMAT, "master")


def create_proxy_path(hda):
    extension = hda.parm("extension").evalAsString()
    return houdini_relative_path(_product_path(extension, _selected_version(hda), wedge=PROXY_WEDGE))


def create_proxy_master_path(hda):
    base, ext = os.path.splitext(create_master_path(hda))
    return f"{base}_{PROXY_WEDGE}{ext}"


MASTER_PATH_BUILDERS = {
    "masterpath": create_master_path,
    "proxymasterpath": create_proxy_master_path,
}


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


def _master_path(hda, master_parm):
    # Fallback si le parm est vide (update_path a échoué en silence)
    path = hda.parm(master_parm).eval()
    if not path:
        path = MASTER_PATH_BUILDERS[master_parm](hda)
        _set_path(hda.parm(master_parm), path)
    return path


def _set_path(parm, value):
    # Si le parm a une expression/keyframe, set() écrirait dans l'expression
    parm.deleteAllKeyframes()
    parm.set(value.replace("\\", "\\\\"))


def update_path(hda=None, strict=False, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()
    # Le default de "path" est une expression hscript vide : si le chemin n'est pas
    # écrit, les nodes internes qui lisent ../path tombent en "Expression stack error"
    for name in ("path", "masterpath", "proxypath", "proxymasterpath"):
        hda.parm(name).deleteAllKeyframes()
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


# ---------- Cache USD ----------

def _reload_layers(paths):
    # En écrasement, Houdini garde l'ancienne version en mémoire :
    # sans reload, le master serait construit sur des données périmées
    for path in paths:
        if not path:
            continue
        layer = Sdf.Layer.Find(path)
        if layer:
            try:
                layer.Reload(force=True)
            except Exception as e:
                print(f"reload {path}: {e}")


# ---------- Validation ----------

def _parm_value(node, name, default=None):
    # Parms move from one hda revision to the next: a missing one must not break
    # the check itself
    parm = node.parm(name)
    if parm is None:
        return default
    try:
        return parm.eval()
    except hou.Error:
        return default


def _on_off(value):
    return "unknown" if value is None else ("ON" if value else "OFF")


def _stripping_nodes(hda):
    # A Daisy Import with "Layer Break" on puts everything it loads above a layer
    # break: with striplayerbreaks the rop drops it and the file comes out empty
    try:
        # defaults only: follow_subnets=True stops the walk at the first hda and
        # would miss the imports chained behind it
        ancestors = hda.inputAncestors()
    except hou.Error:
        return [], []

    imports, breaks = [], []
    for node in ancestors:
        # nothing an artist can act on lives inside a locked hda
        if node.isInsideLockedHDA():
            continue
        # match on the substring so a future ::1.0 namespace keeps working
        type_name = node.type().name()
        if DAISY_IMPORT_TYPE in type_name:
            if _parm_value(node, LAYER_BREAK_PARM, 0):
                imports.append(node.path())
        elif type_name == LAYER_BREAK_TYPE:
            breaks.append(node.path())
    return imports, breaks


def _empty_export_hint(hda):
    # Name the nodes to fix instead of leaving the artist to search the whole network
    imports, breaks = _stripping_nodes(hda)

    lines = []
    if imports:
        lines.append("Daisy Import nodes with 'Layer Break' on upstream:")
        lines += [f"  - {path}" for path in imports]
        lines.append("Turn off their 'Layer Break' toggle (Advanced Settings) and export again.")
    if breaks:
        lines.append("Layer Break nodes upstream:")
        lines += [f"  - {path}" for path in breaks]
    if not imports and not breaks:
        lines.append(
            "No layer break upstream: check the node wired into Daisy Export, a Prune or a "
            "Configure Layer can empty the stage too."
        )

    lines.append(
        f"Write settings of this export: 'Strip Layers Above Layer Breaks' = "
        f"{_on_off(_parm_value(hda, STRIP_PARM))}, 'Save Style' = "
        f"{_parm_value(hda, SAVE_STYLE_PARM) or 'unknown'}."
    )
    return "\n".join(lines)


def _export_error(hda, path, error):
    # The layer break hint only makes sense when the file really came out empty:
    # a several roots error has nothing to do with it
    layer = Sdf.Layer.Find(path)
    if layer is not None and not layer.rootPrims and not layer.subLayerPaths:
        return f"{error}\n\n{_empty_export_hint(hda)}"
    return str(error)


def _check_export(hda, file_parm):
    # The rop can succeed and still write stage metadata only: validate before Prism
    # records anything, otherwise an empty file becomes a published version
    if is_file_per_frame(hda):
        frame_paths = _frame_paths(hda, file_parm)
        # every frame comes out of the same network: first and last are enough
        paths = [frame_paths[0], frame_paths[-1]] if frame_paths else []
    else:
        paths = [_base_path(hda, file_parm)]

    # on an overwrite Houdini still holds the previous layer in memory: without a
    # reload the check would read stale, non empty data (same reason as save_master)
    _reload_layers(paths)

    default_prim = (_parm_value(hda, "defaultprim", "") or "").lstrip("/")

    for path in paths:
        try:
            resolve_root_prim(path, default_prim)
        except Exception as e:
            raise hou.NodeError(_export_error(hda, path, e))


# ---------- Master ----------

def save_master(hda=None, file_parm="path", master_parm="masterpath"):
    hda = hda or hou.pwd()

    if not hda.parm("updatemaster").evalAsInt():
        return None

    file_path = _base_path(hda, file_parm)
    master_path = _master_path(hda, master_parm)

    if not file_path or not master_path:
        raise hou.NodeError(f"Chemins manquants : {file_parm}='{file_path}' {master_parm}='{master_path}'")

    default_prim = hda.parm("defaultprim").eval().lstrip("/")
    frame_range = _get_frame_range(hda)

    if is_file_per_frame(hda):
        frame_paths = _frame_paths(hda, file_parm)
        clips_path = f"{os.path.splitext(file_path)[0]}.clips.usda"
        _reload_layers(frame_paths + [clips_path, master_path])
        create_master_clips(frame_paths, frame_range, clips_path, default_prim=default_prim)
        _reload_layers([clips_path])
        result = create_master(clips_path, master_path, default_prim=default_prim, frame_range=frame_range)
    else:
        _reload_layers([file_path, master_path])
        result = create_master(file_path, master_path, default_prim=default_prim, frame_range=frame_range)

    _reload_layers([master_path])

    if not os.path.isfile(master_path):
        raise hou.NodeError(f"Master non écrit : '{master_path}'")

    print(f"[{hda.path()}] master mis à jour : {master_path}")
    return result


# ---------- Clés caméra ----------

def _parm_keyframes(parm):
    # Un parm sans clé peut référencer un autre parm animé via ch()
    keyframes = parm.keyframes()
    if not keyframes:
        referenced = parm.getReferencedParm()
        if referenced != parm:
            keyframes = referenced.keyframes()
    return {int(round(key.frame())) for key in keyframes}


def _values_differ(a, b, tolerance=1e-6):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) > tolerance
    return a != b


def _camera_moves_at(parms, frame):
    # Une clé ne sert que si la caméra bouge avant ou après elle
    for parm in parms:
        value = parm.evalAtFrame(frame)
        if any(_values_differ(value, parm.evalAtFrame(other)) for other in (frame - 1, frame + 1)):
            return True
    return False


def get_camera_keyframes():
    # Frames des clés posées sur chaque caméra de shot, par nom de prim
    # (le nom du node peut différer du prim, ex. node dupliqué d'une autre séquence)
    cameras = hou.lopNodeTypeCategory().nodeTypes()["camera"].instances()
    keyframes = {}
    for camera in cameras:
        primpath = camera.parm("primpath")
        prim_name = primpath.evalAsString().rstrip("/").split("/")[-1] if primpath else camera.name()
        if not CAMERA_NODE_NAME.match(prim_name):
            continue
        frames = set()
        animated_parms = []
        for parm in camera.parms():
            parm_frames = _parm_keyframes(parm)
            if parm_frames:
                frames |= parm_frames
                animated_parms.append(parm)
        frames = {frame for frame in frames if _camera_moves_at(animated_parms, frame)}
        if frames:
            keyframes.setdefault(prim_name, set()).update(frames)
    return {name: sorted(frames) for name, frames in keyframes.items()}


def write_camera_keyframes(file_path, keyframes):
    # USD ne garde que des valeurs par frame : on note les frames des clés Houdini
    # en customData sur la prim caméra pour que Maya puisse les retrouver
    if not keyframes:
        return

    _reload_layers([file_path])
    layer = Sdf.Layer.FindOrOpen(file_path)
    if not layer:
        print(f"write_camera_keyframes: layer introuvable {file_path}")
        return

    def visit(path):
        if not path.IsPrimPath() or path.name not in keyframes:
            return
        spec = layer.GetPrimAtPath(path)
        if spec.typeName != "Camera":
            return
        custom_data = dict(spec.customData)
        custom_data[USD_CAM_KEYFRAMES] = Vt.IntArray(keyframes[path.name])
        spec.SetInfo("customData", custom_data)

    layer.Traverse(Sdf.Path.absoluteRootPath, visit)
    layer.Save()


# ---------- Thumbnail ----------

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


# ---------- Post-export ----------

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
    update_master = hda.parm("updatemaster").evalAsInt()

    _check_written(hda, file_parm)
    _check_export(hda, file_parm)

    if not is_file_per_frame(hda):
        write_camera_keyframes(path, get_camera_keyframes())

    master_path = None
    if update_master:
        save_master(hda, file_parm=file_parm, master_parm=master_parm)
        master_path = _master_path(hda, master_parm)

    details = dict(entity)
    details["version"] = core.products.getProductDataFromFilepath(path).get("version", "")
    details["sourceScene"] = core.getCurrentFileName()
    details["product"] = task
    details["comment"] = hda.parm("comment").eval()

    info_path = core.products.getVersionInfoPathFromProductFilepath(path)
    core.saveVersionInfo(filepath=info_path, details=details)

    if thumbnail:
        update_thumbnail(hda, core, path)

    if master_path and master_info:
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


# ---------- Export ----------

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


def _report_error(hda, step, error):
    msg = f"{step} : {error}"
    print(f"[{hda.path()}] {msg}")
    if hou.isUIAvailable():
        hou.ui.displayMessage(msg, severity=hou.severityType.Error, title="Daisy Export")


def on_export(kwargs):
    hda = kwargs["node"]
    core = get_core()
    export_proxy = has_proxy_input(hda)

    try:
        wait = core.waitPopup(core, "Mise à jour des chemins...", title="Daisy Export")
        with wait:
            update_path(hda, strict=True)

            _set_wait_text(wait, "Export USD en cours...")
            _render_rop(hda.node("usd_rop1"))

            if export_proxy:
                _set_wait_text(wait, "Export du proxy en cours...")
                _render_rop(hda.node("usd_rop2"))
    except Exception as e:
        _report_error(hda, "Export", e)
        return

    # Post-export hors du render loop et hors du popup
    try:
        post_export(hda)
        if export_proxy:
            proxy_post_export(hda)
    except Exception as e:
        _report_error(hda, "Post-export", e)