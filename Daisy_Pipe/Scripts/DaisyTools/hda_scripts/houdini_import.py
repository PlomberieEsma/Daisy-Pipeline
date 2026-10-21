from Scripts.DaisyTools.core.asset_browser_import import AssetBrowserUI
from Scripts.DaisyTools.core.core import get_core, get_source_scene, houdini_relative_path
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
import hou

core = get_core()
info = get_entity_info()

MAYA_EXTENSIONS = (".ma", ".mb")


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
        hda.parm("path").set(houdini_relative_path(str(path)))
    except Exception as e:
        print(f"[{hda.path()}] set_import_path: {e}")
        return

    if entity.get("type") == "shot" and is_maya_product(path):
        setup_maya_overlay(hda, entity)


def is_maya_product(path):
    # Vrai si le produit a été publié depuis Maya : son USD est un overlay du
    # layout (voir saveas/exportShotAnim.py), pas un stage autonome
    scene = get_source_scene(core, str(path)) or ""
    return scene.lower().endswith(MAYA_EXTENSIONS)


def import_layout_under(hda, entity):
    # Charge sous le node le layout sur lequel l'anim Maya a été exportée, pour que
    # l'overlay se pose dessus : géo et caméras en place, kinds hérités de l'assembly
    from Scripts.DaisyTools.saveas.exportShotAnim import get_layout

    path, time_offset, is_shot_layout = get_layout(core, entity)
    if not path:
        core.popup("Aucun layout publié pour ce plan : l'overlay Maya n'a rien sur quoi se poser.", severity="warning")
        return None

    parent = hda.parent()
    if is_shot_layout:
        layout = parent.createNode("Daisy::daisy_import", node_name="layout_import")
        layout.parm("path").set(houdini_relative_path(str(path)))
        layout.parm("mayascale").set(0)
    else:
        # Layout du MASTER : décalé dans le temps pour lire la partie du plan, comme
        # template_layout.py - le daisy_import n'expose pas de time offset
        layout = parent.createNode("sublayer", node_name="layout_MASTER_import")
        layout.parm("filepath1").set(houdini_relative_path(str(path)))
        layout.parm("timeoffset1").set(-time_offset)

    hda.setInput(0, layout)
    layout.moveToGoodPosition()
    print(f"[{hda.path()}] layout chargé sous l'import Maya : {path}")
    return layout


def setup_maya_overlay(hda, entity):
    # Un USD publié depuis Maya sur un plan est un overlay du layout, déjà à l'échelle
    # de l'assembly : on le sous-layer sans le scale Maya et on met le layout dessous
    for name, value in (("importAs", 0), ("mayascale", 0)):
        parm = hda.parm(name)
        if parm:
            parm.set(value)

    inputs = hda.inputs()
    if inputs and inputs[0] is not None:
        return None
    return import_layout_under(hda, entity)


def on_click(kwargs):
    hda = kwargs["node"]

    asset_list = openui()
    if not asset_list:
        return

    set_import_path(hda, asset_list[0])
