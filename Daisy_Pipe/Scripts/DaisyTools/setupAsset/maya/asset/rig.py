import maya.cmds as cmds

from Scripts.DaisyTools.setupAsset.maya.scene_loaders import get_source_scene, import_maya_scene

# Rig task -> modeling product whose source scene is imported
RIG_PRODUCTS = {
    "RigL": "ModL",
    "RigH": "ModH",
}


# ------------------------------------------------------------------------------ #
#                                      Rig                                       #
# ------------------------------------------------------------------------------ #

def import_rig_source_scene(core, entity, product):
    #-----------------------------------------------------------------------#
    # Import the source scene of the latest version of the modeling product #
    #                                                                       #
    # core = Prism core                                                     #
    # entity = Prism entity dict of the asset                               #
    # product = modeling product name (e.g.: ModL)                          #
    #                                                                       #
    # return the list of imported nodes, or None if the import failed       #
    #-----------------------------------------------------------------------#

    product_path = core.products.getLatestVersionpathFromProduct(product, entity=entity)
    if not product_path:
        cmds.warning("Aucune version trouvée pour %s sur %s" % (product, entity))
        return None

    source_scene = get_source_scene(core, product_path)
    print("Product :", product_path)
    print("Source scene :", source_scene)
    return import_maya_scene(source_scene)


def setup_rig(core, info):
    #-----------------------------------------------------------------------#
    # Set up a rig scene: import the modeling source scene                  #
    # RigL imports the ModL source scene, RigH imports the ModH one         #
    #                                                                       #
    # core = Prism core                                                     #
    # info = dict returned by get_entity_info()                             #
    #                                                                       #
    # return the list of imported nodes, or None                            #
    #-----------------------------------------------------------------------#

    product = RIG_PRODUCTS.get(info["task"])
    if product is None:
        return None
    return import_rig_source_scene(core, info["entity"], product)
