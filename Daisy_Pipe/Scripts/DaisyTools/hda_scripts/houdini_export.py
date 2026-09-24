import hou
from Scripts.DaisyTools.core.core import get_core, houdini_relative_path
from Scripts.DaisyTools.core.get_entity_info import get_entity_info


def _product_path(hda, version):
    info = get_entity_info()
    extension = hda.parm("extension").evalAsString().lstrip(".")
    return get_core().products.generateProductPath(
        entity=info["entity"],
        task=info["task"],
        extension=f".{extension}",
        version=version,
        location="global",
    )


def create_path(hda):
    return houdini_relative_path(_product_path(hda, None))


def create_master_path(hda):
    return _product_path(hda, "master")


def update_path(hda=None, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()
    try:
        hda.parm("path").set(create_path(hda))
        hda.parm("masterpath").set(create_master_path(hda))
    except Exception as e:
        # Scène pas encore sauvée dans Prism, pas d'entity : on ne bloque pas
        print(f"[{hda.path()}] update_path: {e}")