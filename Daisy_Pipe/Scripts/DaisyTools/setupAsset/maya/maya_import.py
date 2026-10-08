import os
import maya.cmds as cmds

from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

USD_EXTENSIONS = (".usd", ".usda", ".usdc", ".usdz")
SETDRESS_PRODUCT = "SetDress"
SETDRESS_SHOT = "MASTER"
RIG_PRODUCT = "04_rig"  # à adapter au nom réel du product rig


def get_source_scene(core, product_path):
    data = core.paths.getCachePathData(product_path) or {}
    src = data.get("sourceScene")
    if src:
        return src

    info_path = core.products.getVersionInfoPathFromProductFilepath(product_path)
    if info_path and os.path.exists(info_path):
        return core.getConfig("sourceScene", configPath=info_path)
    return None


def get_master_path(core, entity, product):
    versions = core.products.getVersionsFromProduct(entity, product)
    master = next((v for v in versions if v.get("version") == "master"), None)
    if not master:
        return None
    return core.products.getPreferredFileFromVersion(master)


def load_usd_stage(path, name, scale=100.0):
    cmds.loadPlugin("mayaUsdPlugin", quiet=True)
    xform = cmds.createNode("transform", name=name)
    shape = cmds.createNode("mayaUsdProxyShape", name=name + "Shape", parent=xform)
    cmds.setAttr(shape + ".filePath", path, type="string")
    cmds.connectAttr("time1.outTime", shape + ".time")
    cmds.setAttr(xform + ".scale", scale, scale, scale, type="double3")
    return shape


def import_master_usd(core, entity, product):
    path = get_master_path(core, entity, product)
    if not path:
        cmds.warning("Pas de master trouvé pour %s sur %s" % (product, entity))
        return None

    if not path.lower().endswith(USD_EXTENSIONS):
        cmds.warning("Le fichier préféré du master n'est pas un USD : %s" % path)
        return None

    name = "%s_%s_%s" % (entity["sequence"], entity["shot"], product)
    shape = load_usd_stage(path.replace("\\", "/"), name)
    print("Stage chargé : %s -> %s" % (shape, path))
    return shape


def get_setdress_entity(shot_entity):
    entity = {
        "type": "shot",
        "sequence": shot_entity["sequence"],
        "shot": SETDRESS_SHOT,
    }
    if "episode" in shot_entity:
        entity["episode"] = shot_entity["episode"]
    return entity


def import_asset():
    core = get_core()
    info = get_entity_info()
    if info is None:
        return

    entity = info["entity"]

    if entity.get("type") == "shot":

        if info["departement"] == "03_anim":
            return import_master_usd(core, get_setdress_entity(entity), SETDRESS_PRODUCT)

    else:
        if info["departement"] == "04_rig":
            product_path = core.products.getLatestVersionpathFromProduct(RIG_PRODUCT, entity=entity)
            if not product_path:
                print("Aucune version trouvée pour %s sur %s" % (RIG_PRODUCT, entity))
                return

            source_scene = get_source_scene(core, product_path)
            print("Product :", product_path)
            print("Source scene :", source_scene)