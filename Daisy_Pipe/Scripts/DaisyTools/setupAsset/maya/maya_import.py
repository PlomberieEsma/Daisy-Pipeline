import os

from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

def get_source_scene(core, product_path):
    data = core.paths.getCachePathData(product_path) or {}
    src = data.get("sourceScene")
    if src:
        return src

    info_path = core.products.getVersionInfoPathFromProductFilepath(product_path)
    if info_path and os.path.exists(info_path):
        return core.getConfig("sourceScene", configPath=info_path)
    return None


def import_asset():
    core = get_core()
    info = get_entity_info()
    if info is None:
        return

    entity = info["entity"]
    is_shot = entity.get("type") == "shot"

    if is_shot:
        return

    if info["departement"] == "04_rig":
        product_path = core.products.getLatestVersionpathFromProduct("", entity=entity)
        if not product_path:
            print("Aucune version trouvée pour %s")
            return

        source_scene = get_source_scene(core, product_path)
        print("Product :", product_path)
        print("Source scene :", source_scene)
