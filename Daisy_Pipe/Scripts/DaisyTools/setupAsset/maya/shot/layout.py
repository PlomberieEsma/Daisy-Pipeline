import maya.cmds as cmds

from Scripts.DaisyTools.core.framerange_convert import FramerangeFile
from Scripts.DaisyTools.setupAsset.maya.scene_loaders import MASTER_SHOT, USD_EXTENSIONS, get_master_path, get_master_shot_entity, load_usd_stage

LAYOUT_PRODUCT = "layout"


# ------------------------------------------------------------------------------ #
#                                     Layout                                     #
# ------------------------------------------------------------------------------ #

def import_master_usd(core, entity, product):
    #-------------------------------------------------------------------------------------#
    # Load the master USD of a product as a stage in the Maya scene                       #
    #                                                                                     #
    # core = Prism core                                                                   #
    # entity = Prism entity dict of the shot                                              #
    # product = name of the product to load (e.g.: layout)                                #
    #                                                                                     #
    # return the name of the created mayaUsdProxyShape, or None if there is no USD master #
    #-------------------------------------------------------------------------------------#

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


def get_default_prim_name(stage_shape):
    #------------------------------------------------------------------#
    # Get the name of the defaultPrim of the USD stage                 #
    #                                                                  #
    # stage_shape = mayaUsdProxyShape of the stage                     #
    #                                                                  #
    # return the defaultPrim name, or None if the stage has none       #
    #------------------------------------------------------------------#

    import mayaUsd.ufe

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    default_prim = stage.GetDefaultPrim()
    if not default_prim:
        cmds.warning("Pas de defaultPrim dans le stage %s" % stage_shape)
        return None
    return default_prim.GetName()


def deactivate_usd_cameras(stage_shape):
    #--------------------------------------------------------------------#
    # Deactivate all the cameras of the USD stage so they do not appear  #
    # in the Maya camera list                                            #
    # The edit is done in the session layer, the USD file is not changed #
    #                                                                    #
    # stage_shape = mayaUsdProxyShape of the layout                      #
    #                                                                    #
    # return the number of deactivated cameras                           #
    #--------------------------------------------------------------------#

    import mayaUsd.ufe
    from pxr import Usd, UsdGeom

    stage = mayaUsd.ufe.getStage(cmds.ls(stage_shape, long=True)[0])
    # Get the list first: deactivating a prim during the traversal breaks it
    cameras = [p for p in stage.Traverse() if p.IsA(UsdGeom.Camera)]
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        for camera in cameras:
            camera.SetActive(False)

    print("%d caméra(s) USD désactivée(s) dans %s" % (len(cameras), stage_shape))
    return len(cameras)


# ------------------------------------------------------------------------------ #
#                                  Frame range                                   #
# ------------------------------------------------------------------------------ #

def get_shot_ranges(sequence, shot):
    #-------------------------------------------------------------------------#
    # Get the shot frame range in the shot time and in the MASTER time        #
    #                                                                         #
    # sequence = sequence name (e.g.: sq0010)                                 #
    # shot = shot name (e.g.: sh0010)                                         #
    #                                                                         #
    # return a tuple (shot_range, master_range), or (None, None) if not found #
    #-------------------------------------------------------------------------#

    # Shot frame range in the shot time and in the MASTER time
    try:
        framerange = FramerangeFile()
        return framerange.get_shot_range(sequence, shot), framerange.get_master_range(sequence, shot)
    except Exception as e:
        cmds.warning("Frame range introuvable pour %s_%s (%s)" % (sequence, shot, e))
        return None, None


def offset_stage_time(stage_shape, shot_range, master_range):
    #--------------------------------------------------------------------------#
    # Offset the USD stage time so the shot reads the right part of the MASTER #
    #                                                                          #
    # stage_shape = mayaUsdProxyShape of the layout                            #
    # shot_range = shot frame range in the shot time                           #
    # master_range = shot frame range in the MASTER time                       #
    #                                                                          #
    # return the animCurveTT connected to the stage time                       #
    #--------------------------------------------------------------------------#

    # Time -> time curve: the shot start frame reads the shot start frame in the MASTER
    curve = cmds.createNode("animCurveTT", name=stage_shape.split("|")[-1] + "_timeOffset")
    cmds.setKeyframe(curve, time=shot_range[0], value=master_range[0])
    cmds.setKeyframe(curve, time=shot_range[1], value=master_range[0] + shot_range[1] - shot_range[0])
    cmds.keyTangent(curve, inTangentType="linear", outTangentType="linear")
    cmds.setInfinity(curve, preInfinite="linear", postInfinite="linear")
    cmds.connectAttr(curve + ".output", stage_shape + ".time", force=True)
    return curve



def load_shot_layout(core, entity):
    #-----------------------------------------------------------------------------#
    # Load the shot layout master, or the MASTER shot layout master if none       #
    # The MASTER layout is offset in time to read the shot part of the MASTER     #
    #                                                                             #
    # core = Prism core                                                           #
    # entity = Prism entity dict of the shot                                      #
    #                                                                             #
    # return a tuple (layout stage shape or None, shot_range, master_range)       #
    #-----------------------------------------------------------------------------#

    sequence, shot = entity["sequence"], entity["shot"]
    shot_range, master_range = get_shot_ranges(sequence, shot)

    if get_master_path(core, entity, LAYOUT_PRODUCT):
        # The shot layout is already in the shot time: no time offset
        layout = import_master_usd(core, entity, LAYOUT_PRODUCT)
        return layout, shot_range, shot_range

    core.popup(
        "No layout published on %s_%s.\nThe %s shot layout is imported instead." % (sequence, shot, MASTER_SHOT),
        title="Daisy import",
        severity="warning",
    )
    layout = import_master_usd(core, get_master_shot_entity(entity), LAYOUT_PRODUCT)
    if layout and shot_range:
        offset_stage_time(layout, shot_range, master_range)
    return layout, shot_range, master_range

