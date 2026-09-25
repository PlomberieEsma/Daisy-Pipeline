from DaisyTools.core.dcc.launcher import get_dcc
from DaisyTools.setupAsset.maya.setup_geo import setup_geo, geo_is_complete
import json, os

#path to the export usd parameters which are stocked in a json file
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_pkg_root, "lib", "usdParamsExport.json"), "r") as f:
    usdExportParams = json.load(f)

#pipeline-wide settings (extensions, limits, ...) stocked in config.json
with open(os.path.join(_pkg_root, "lib", "config.json"), "r", encoding="utf-8") as f:
    daisyConfig = json.load(f)

USD_FILE_FORMAT = daisyConfig["global"]["usd_file_format"]


def get_core():
    
    #import Prism Pipeline and pcore without UI
    
    try:
        # pyrefly: ignore [missing-import]
        import PrismInit
        core = PrismInit.pcore if getattr(PrismInit, "pcore", None) else PrismInit.prismInit(prismArgs=["noUI"])
    except Exception as e:
        print(f"[Daisy] Prism est introubable. Veuillez vérifier que Prism est installé et configuré correctement. Erreur: {e}")
        return None
    return core

    #To use it import the fonction in other modules using "from Daisy_Pipe.Scripts.DaisyTools.core.core import get_core" then execute with "core = get_core()"
    #You can then use core.exampleOfPrismFonction to call prism fonction


def find_or_create_entity_group(group_name):

    #Find the top-level group named after the entity/default_prim, or create it and
    #parent any loose top-level content into it (used for generic whole-scene export)

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    group_path = "|" + group_name
    if cmds.objExists(group_path) and cmds.nodeType(group_path) == "transform":
        return group_path

    group_path = "|" + cmds.group(empty=True, name=group_name)

    topNodes = [
        n for n in cmds.ls(assemblies=True, long=True)
        if n.split("|")[-1] not in ("persp", "top", "front", "side") and n != group_path
    ]
    if topNodes:
        cmds.parent(topNodes, group_path)

    return group_path


def create_selection_set(selectedobj, set_name):
    
    #Create maya quick selection set from selected objects

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    if cmds.objExists(set_name) and cmds.nodeType(set_name) == "objectSet":
        cmds.delete(set_name)
        
    #If selection set already existe we delete it to recreate a new one with the same name

    set_name = cmds.sets(selectedobj, name=set_name)

    return set_name


#Maps the "Subdivision Method" combo labels (state UI) to the real mayaUSDExport
#"defaultMeshScheme" flag values
SUBDIVISION_METHOD_MAP = {
    "Catmull-Clark": "catmullClark",
    "Bilinear": "bilinear",
    "Loop": "loop",
    "None": "none",
}


def write_usd(preset_name, file_path, default_prim="", selection_only=True, overrides=None, frame_range=None, is_shot=False, is_animation=False):

    #Write usd using mayaUsdPlugin if launched inside maya
    #overrides: dict of extra/override mayaUSDExport flags (e.g. from the state UI)
    #frame_range: (start, end) tuple/list to export an animated frameRange, or None for a static export

    dcc = get_dcc() #get in which dcc software the code is being executed (ex: Maya, Houdini)

    if dcc == "maya": #if we are in Maya we execute this code
        # pyrefly: ignore [missing-import]
        import maya.cmds as cmds

        if not cmds.pluginInfo("mayaUsdPlugin", q=True, loaded=True):
            cmds.loadPlugin("mayaUsdPlugin")

            #check if mayaUsdPlugin is loaded, if not we load it

        config = dict(usdExportParams["common"]) #get default export parameters from json file

        if preset_name in usdExportParams["presets"]:
            config.update(usdExportParams["presets"][preset_name])
        #departments without a dedicated preset just use the common export settings

        config["file"] = file_path
        config["defaultPrim"] = default_prim
        config["selection"] = True

        if overrides:
            config.update(overrides)

        if frame_range:
            config["frameRange"] = list(frame_range)

        if preset_name == "mod":

            root_exists = cmds.objExists("|" + default_prim) and cmds.nodeType("|" + default_prim) == "transform"

            if not root_exists or not geo_is_complete("|" + default_prim):
                master_grp = setup_geo(default_prim=default_prim)
                print(f"{master_grp} setup")
            else:
                master_grp = "|" + default_prim

            geo_set_name = default_prim + "_geoSet"
            existing_set = cmds.objExists(geo_set_name) and cmds.nodeType(geo_set_name) == "objectSet"

            if selection_only and existing_set:
                #the export selection set already exists: reuse it instead of the live viewport selection
                selection = cmds.sets(geo_set_name, query=True) or []
                if not selection:
                    raise RuntimeError(f"Le selection set '{geo_set_name}' existe mais est vide.")
                cmds.select(selection, replace=True)
            elif selection_only:
                selection = cmds.ls(selection=True, long=True)
                if not selection:
                    raise RuntimeError(
                        "Aucune géométrie sélectionnée : sélectionne les nœuds à "
                        "exporter avant de lancer l'export USD."
                    )
                if not is_shot and not is_animation:
                    #no set yet: build it from the geo added to the Maya Objects list, for reuse next time
                    #animation exports never author the set - they only reuse an existing one
                    create_selection_set(selection, geo_set_name)
            else:
                cmds.select(master_grp)
                selection = [master_grp]
                if not is_shot and not is_animation:
                    create_selection_set(selection, geo_set_name)

        else:
            #generic departments: no dedicated geo hierarchy, just export whatever is selected
            if selection_only:
                selection = cmds.ls(selection=True, long=True)
                if not selection:
                    raise RuntimeError(
                        "Aucune géométrie sélectionnée : sélectionne les nœuds à "
                        "exporter avant de lancer l'export USD."
                    )
            else:
                group_path = find_or_create_entity_group(default_prim)
                cmds.select(group_path, replace=True)

        # namespaces must never be baked into exported USD prim paths, for
        # either assets or shots - enforce this unconditionally regardless
        # of preset
        config["stripNamespaces"] = True

        cmds.mayaUSDExport(**config)

def create_master(file_path, master_path, default_prim="", frame_range=None):

    #Create a master usd file with sublayer pointing to the lastest version of the entity usd file

    from pxr import Usd, Sdf #import Usd and Sdf library from Pxr

    start_frame, end_frame = frame_range if frame_range else (1, 1)

    #store the sublayer path relative to the master file so the project stays
    #portable across drives/machines instead of baking in an absolute path
    relative_file_path = os.path.relpath(file_path, os.path.dirname(master_path)).replace("\\", "/")

    if not os.path.exists(master_path): #check if master usd file already exists if not we create it

        master_stage = Usd.Stage.CreateNew(master_path) #create new master usd file
        root_layer = master_stage.GetRootLayer() #get root layer of master usd file

        root_layer.defaultPrim = default_prim #set default prim
        root_layer.startTimeCode = start_frame #set start time code
        root_layer.endTimeCode = end_frame #set end time code
        master_stage.SetMetadata("metersPerUnit", 0.01) #set meters per unit

        root_layer.subLayerPaths.append(relative_file_path) #append relative file path to sublayer paths

        root_layer.Save()

        print(f"Fichier créé : {master_path}")

    else: #if master usd file already exists we update the sublayer paths and framerange
        layer = Sdf.Layer.FindOrOpen(master_path) #find master usd file

        layer.subLayerPaths.clear() #clear sublayer paths
        layer.subLayerPaths.append(relative_file_path) #append relative file path to sublayer paths

        layer.startTimeCode = start_frame #keep the framerange in sync with the current export
        layer.endTimeCode = end_frame

        layer.Save() #save master usd file

        print(f"SubLayer mis à jour : {master_path}")


def create_master_clips(frame_paths, frame_range, clips_path, default_prim=""):

    #Build a usd file that stitches multiple per-frame usd files together using
    #USD Value Clips, so a "File per Frame" export still plays back as continuous
    #animation instead of a single static frame.
    #This file is NOT the master itself: it's meant to be handed to create_master()
    #as its file_path, so the master stays a plain sublayer wrapper either way.

    from pxr import Usd, Sdf

    if os.path.exists(clips_path):
        os.remove(clips_path)
        #clips are always rebuilt from the current export rather than merged with
        #a previous one, since the clip list has to match the frames on disk

    start_frame, end_frame = frame_range
    prim_path = "/" + default_prim
    frames = list(range(int(start_frame), int(end_frame) + 1))

    clips_stage = Usd.Stage.CreateNew(clips_path)
    root_layer = clips_stage.GetRootLayer()

    root_layer.defaultPrim = default_prim
    root_layer.startTimeCode = start_frame
    root_layer.endTimeCode = end_frame
    clips_stage.SetMetadata("metersPerUnit", 0.01)

    prim = clips_stage.DefinePrim(prim_path)

    #Value Clips only override time-varying attribute VALUES - they never bring in
    #the prim hierarchy/mesh topology itself. Without this reference the clip prim
    #stays empty/untyped and no geometry shows up, so we reference frame 0 to get
    #the actual mesh/hierarchy/material structure, then let the clips drive the
    #time-sampled attributes (points, xforms, ...) on top of it.
    prim.GetReferences().AddReference(frame_paths[0])

    clipsAPI = Usd.ClipsAPI(prim)
    clipsAPI.SetClipAssetPaths([Sdf.AssetPath(p) for p in frame_paths])
    clipsAPI.SetClipPrimPath(prim_path)
    clipsAPI.SetClipManifestAssetPath(Sdf.AssetPath(frame_paths[0]))
    clipsAPI.SetClipActive([(float(frame), float(i)) for i, frame in enumerate(frames)])
    clipsAPI.SetClipTimes([(float(frame), float(frame)) for frame in frames])

    root_layer.Save()

    print(f"Fichier de clips créé : {clips_path}")

    return clips_path

import os


def houdini_relative_path(file_path, env_var="$PRISM_JOB"):
    if not file_path:
        return file_path

    project_path = get_core().projectPath

    norm_file = os.path.normpath(file_path).replace("\\", "/")
    norm_project = os.path.normpath(project_path).replace("\\", "/").rstrip("/")

    if norm_file.lower() == norm_project.lower():
        return env_var

    if norm_file.lower().startswith(norm_project.lower() + "/"):
        return env_var + norm_file[len(norm_project):]

    return norm_file