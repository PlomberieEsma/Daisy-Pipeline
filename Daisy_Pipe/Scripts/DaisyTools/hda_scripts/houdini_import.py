from Scripts.DaisyTools.core.asset_browser_import import AssetBrowserUI
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
import hou

core = get_core()
info = get_entity_info()


def openui():

    entity = info["entity"]
    task = info["task"]

    asset_browser = AssetBrowserUI(core=core, plugin=None)

    while True:
        asset_list = asset_browser.onAssetBrowserTriggered(entity, task)

        if not asset_list:
            core.popup("Aucun asset sélectionné, annulation.", severity="warning")
            return None

        if len(asset_list) == 1:
            return asset_list

        core.popup("Plus d'un asset sélectionné, choisis-en un seul.", severity="warning")


def build_entity(item):
    # Reconstruit une entité Prism à partir du dict renvoyé par l'Asset Browser
    if item.get("type") == "shot":
        return {"type": "shot", "sequence": item["sequence"], "shot": item["shot"]}
    return {"type": "asset", "asset_path": item["asset_path"], "asset": item["name"]}


def choose_product(entity, label):
    # Liste les produits exportés de l'entité, choix auto si un seul
    products = core.products.getProductsFromEntity(entity) or []
    names = sorted({p.get("product") for p in products if p.get("product")})

    if not names:
        core.popup("Aucun produit exporté pour %s." % label, severity="warning")
        return None

    if len(names) == 1:
        return names[0]

    choice = hou.ui.selectFromList(
        names,
        exclusive=True,
        title="Choix du produit",
        message="Produits disponibles pour %s" % label,
    )
    return names[choice[0]] if choice else None


def set_import_path(hda, asset, **kwargs):
    hda = hda or kwargs.get("node") or hou.pwd()

    entity = build_entity(asset)
    product = choose_product(entity, asset["name"])
    if not product:
        return

    path = core.products.getLatestVersionpathFromProduct(product, entity=entity)
    if not path:
        core.popup("Aucune version trouvée pour %s / %s." % (asset["name"], product), severity="warning")
        return

    try:
        hda.parm("path").set(str(path).replace("\\", "/"))
    except Exception as e:
        print(f"[{hda.path()}] set_import_path: {e}")


def on_click(kwargs):
    hda = kwargs["node"]

    asset_list = openui()
    if not asset_list:
        return

    set_import_path(hda, asset_list[0])
