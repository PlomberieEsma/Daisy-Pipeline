import os
import maya.cmds as cmds

USD_EXTENSIONS = (".usd", ".usda", ".usdc", ".usdz")
MAYA_EXTENSIONS = (".ma", ".mb")
LOADED_PRIM_COLLECTION = "loaded_prim"


# ------------------------------------------------------------------------------ #
#                                 Prism products                                 #
# ------------------------------------------------------------------------------ #

def get_master_path(core, entity, product):
    #-----------------------------------------------------------------#
    # Get the preferred file of the master version of a Prism product #
    #                                                                 #
    # core = Prism core                                               #
    # entity = Prism entity dict (asset or shot)                      #
    # product = product name (e.g.: layout)                           #
    #                                                                 #
    # return the file path, or None if the product has no master      #
    #-----------------------------------------------------------------#

    versions = core.products.getVersionsFromProduct(entity, product)
    master = next((v for v in versions if v.get("version") == "master"), None)
    if not master:
        return None
    return core.products.getPreferredFileFromVersion(master)


def get_source_scene(core, product_path):
    #------------------------------------------------------------#
    # Get the source scene used to publish a product             #
    # Look in the cache path data first, then in the versioninfo #
    #                                                            #
    # core = Prism core                                          #
    # product_path = path of a published product file            #
    #                                                            #
    # return the source scene path, or None if not found         #
    #------------------------------------------------------------#

    data = core.paths.getCachePathData(product_path) or {}
    src = data.get("sourceScene")
    if src:
        return src

    info_path = core.products.getVersionInfoPathFromProductFilepath(product_path)
    if info_path and os.path.exists(info_path):
        return core.getConfig("sourceScene", configPath=info_path)
    return None


def get_latest_scene(core, entity, department, task):
    #-------------------------------------------------------------------#
    # Get the Maya work scene with the highest version of a task        #
    #                                                                   #
    # core = Prism core                                                 #
    # entity = Prism entity dict of the asset                           #
    # department = department name (e.g.: 04_rig)                       #
    # task = task name (e.g.: RigH)                                     #
    #                                                                   #
    # return the scene path, or None if the task has no Maya scene      #
    #-------------------------------------------------------------------#

    paths = core.entities.getScenefiles(
        entity, step=department, category=task, extensions=list(MAYA_EXTENSIONS)
    ) or []

    latest, latest_version = None, -1
    for path in paths:
        data = core.getScenefileData(path) or {}
        version = core.products.getIntVersionFromVersionName(data.get("version"))
        if version is not None and version > latest_version:
            latest, latest_version = path, version
    return latest


# ------------------------------------------------------------------------------ #
#                                   USD stages                                   #
# ------------------------------------------------------------------------------ #

def load_usd_stage(path, name, scale=100.0):
    #------------------------------------------------------------------#
    # Load a USD file in the Maya scene through a mayaUsdProxyShape    #
    # The stage follows the scene time and is scaled (Houdini -> Maya) #
    #                                                                  #
    # path = USD file path                                             #
    # name = name of the created transform                             #
    # scale = scale applied to the stage transform                     #
    #                                                                  #
    # return the name of the created mayaUsdProxyShape                 #
    #------------------------------------------------------------------#

    cmds.loadPlugin("mayaUsdPlugin", quiet=True)
    xform = cmds.createNode("transform", name=name)
    shape = cmds.createNode("mayaUsdProxyShape", name=name + "Shape", parent=xform)
    # Open the stage without payloads, they are loaded afterwards by load_stage_payloads()
    cmds.setAttr(shape + ".loadPayloads", False)
    cmds.setAttr(shape + ".filePath", path, type="string")
    cmds.connectAttr("time1.outTime", shape + ".time")
    cmds.setAttr(xform + ".scale", scale, scale, scale, type="double3")
    load_stage_payloads(shape)
    return shape


def get_loaded_prim_collection(stage):
    #-------------------------------------------------------------------#
    # Find the collection listing the prims to load in the USD stage    #
    #                                                                   #
    # stage = USD stage                                                 #
    #                                                                   #
    # return the Usd.CollectionAPI, or None if there is no collection   #
    #-------------------------------------------------------------------#

    from pxr import Usd

    for prim in stage.Traverse():
        for collection in Usd.CollectionAPI.GetAllCollections(prim):
            if collection.GetName() == LOADED_PRIM_COLLECTION:
                return collection
    return None


def load_stage_payloads(stage_shape):
    #------------------------------------------------------------------------#
    # Load the payloads of the prims listed in the loaded_prim collection    #
    # If the stage has no loaded_prim collection, everything is loaded       #
    #                                                                        #
    # stage_shape = mayaUsdProxyShape of the stage                           #
    #                                                                        #
    # return the list of loaded prim paths                                   #
    #------------------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import Sdf

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    collection = get_loaded_prim_collection(stage)
    if collection is None or collection.GetIncludeRootAttr().Get():
        stage.Load(Sdf.Path.absoluteRootPath)
        print("Pas de collection %s : tout le stage est chargé" % LOADED_PRIM_COLLECTION)
        return [Sdf.Path.absoluteRootPath]

    # The targets are used as they are: the prims under an unloaded payload
    # do not exist yet, so the collection membership can not be computed
    paths = collection.GetIncludesRel().GetTargets()
    for path in paths:
        stage.Load(path)
    for path in collection.GetExcludesRel().GetTargets():
        stage.Unload(path)

    print("%d prim(s) chargée(s) depuis la collection %s" % (len(paths), collection.GetPath()))
    return paths


# ------------------------------------------------------------------------------ #
#                                  Maya scenes                                   #
# ------------------------------------------------------------------------------ #

def import_maya_scene(path, namespace=":"):
    #-------------------------------------------------------------------#
    # Import a Maya scene (.ma or .mb) in the current scene             #
    #                                                                   #
    # path = path of the scene to import                                #
    # namespace = namespace to import the nodes in (":" = root)         #
    #                                                                   #
    # return the list of imported nodes, or None if the file is invalid #
    #-------------------------------------------------------------------#

    if not path or not os.path.exists(path):
        cmds.warning("Scène introuvable : %s" % path)
        return None

    if not path.lower().endswith(MAYA_EXTENSIONS):
        cmds.warning("La scène source n'est pas un fichier Maya : %s" % path)
        return None

    path = path.replace("\\", "/")
    file_type = "mayaAscii" if path.lower().endswith(".ma") else "mayaBinary"
    nodes = cmds.file(
        path,
        i=True,
        type=file_type,
        ignoreVersion=True,
        namespace=namespace,
        mergeNamespacesOnClash=True,
        preserveReferences=True,
        returnNewNodes=True,
    )
    print("Importé : %s (%d nodes)" % (path, len(nodes or [])))
    return nodes


def reference_maya_scene(path):
    #---------------------------------------------------------------------#
    # Reference a Maya scene (.ma or .mb) in the current scene            #
    # The nodes are referenced without namespace                          #
    #                                                                     #
    # path = path of the scene to reference                               #
    #                                                                     #
    # return the list of referenced nodes, or None if the file is invalid #
    #---------------------------------------------------------------------#

    if not path or not os.path.exists(path):
        cmds.warning("Scène introuvable : %s" % path)
        return None

    if not path.lower().endswith(MAYA_EXTENSIONS):
        cmds.warning("La scène n'est pas un fichier Maya : %s" % path)
        return None

    path = path.replace("\\", "/")
    nodes = cmds.file(path, reference=True, namespace=":", returnNewNodes=True)
    print("Référencé : %s (%d nodes)" % (path, len(nodes or [])))
    return nodes
