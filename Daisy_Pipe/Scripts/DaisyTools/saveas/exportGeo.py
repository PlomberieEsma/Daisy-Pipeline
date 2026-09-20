#                           .=     ,        =.
#                   _  _   /'/    )\,/,/(_   \ \
#                    `//-.|  (  ,\\)\//\)\/_  ) |
#                    //___\   `\\\/\\/\/\\///'  /
#                 ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
#                 \       `-.  '_`.      .'_` \ ,-"~`/
#                  `.__.-'`/  ( -\        /- )|-.__,'
#                    ||   |    \ O)  /^\ (O / |
#                    `\\  |         /   `\    /
#                      \\  \       /      `\ /
#                       `\\ `-.  /' .---.--.\
#                         `\\/`~(, '()      ('
#                          /(O) \\   _,.-.,_)
#                         //  \\ `\'`      /
#                        / |  ||   `""'"~"`
#                      /'  |__||
#                            `o
#      ___       _                    _          ___               
#     / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___       
#    / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)      
#   /____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/       
#                   /___/    /_/    /_/                            
#
#   by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio
#   art by Joan G. Stark (Spunk)

import os
import shutil

from DaisyTools.core.get_entity_info import get_entity_info
from DaisyTools.core.core import get_core


def _mel_bool(value):
    return "true" if value else "false"


def write_fbx(file_path, selection_only=True, frame_range=None, triangulate=False, smoothing_groups=True, skins=False, blendshapes=False, embed_textures=False):

    #Export the selection (or whole scene) to FBX with the fbxmaya plugin

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    # pyrefly: ignore [missing-import]
    import maya.mel as mel

    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")

    #an animated export bakes every frame of the range, a single frame export doesn't bake anything
    bake = bool(frame_range) and frame_range[0] != frame_range[1]

    mel.eval("FBXResetExport")
    mel.eval(f"FBXExportTriangulate -v {_mel_bool(triangulate)}")
    mel.eval(f"FBXExportSmoothingGroups -v {_mel_bool(smoothing_groups)}")
    mel.eval(f"FBXExportSkins -v {_mel_bool(skins)}")
    mel.eval(f"FBXExportShapes -v {_mel_bool(blendshapes)}")
    mel.eval(f"FBXExportEmbeddedTextures -v {_mel_bool(embed_textures)}")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval("FBXExportCameras -v false")
    mel.eval("FBXExportLights -v false")
    mel.eval(f"FBXExportBakeComplexAnimation -v {_mel_bool(bake)}")
    if bake:
        mel.eval(f"FBXExportBakeComplexStart -v {int(frame_range[0])}")
        mel.eval(f"FBXExportBakeComplexEnd -v {int(frame_range[1])}")
        mel.eval("FBXExportBakeComplexStep -v 1")

    export_cmd = f'FBXExport -f "{file_path.replace(os.sep, "/")}"'
    if selection_only:
        export_cmd += " -s"
    mel.eval(export_cmd)


def write_obj(file_path, selection_only=True, frame=None, materials=False, normals=False, smoothing=True):

    #Export the selection (or whole scene) to OBJ with the objExport plugin - OBJ has no animation,
    #so only one frame gets written

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    if not cmds.pluginInfo("objExport", query=True, loaded=True):
        cmds.loadPlugin("objExport")

    if frame is not None:
        cmds.currentTime(frame)

    options = f"groups=1;ptgroups=1;materials={int(materials)};smoothing={int(smoothing)};normals={int(normals)}"
    export_kwargs = {"force": True, "options": options, "type": "OBJexport", "preserveReferences": False}
    if selection_only:
        export_kwargs["exportSelected"] = True
    else:
        export_kwargs["exportAll"] = True

    cmds.file(file_path.replace(os.sep, "/"), **export_kwargs)


def export_geo(params=None):

    #Export the current scene to FBX or OBJ, driven by the export state's settings (params).
    #params comes from DaisyGeoExportClass.getExportParams() - a plain dict, no Qt involved here.
    #The master is a plain copy of the version we just wrote, in a "geo" subfolder of the master folder.

    core = get_core()
    if core is None:
        return

    info = get_entity_info()
    if info is None:
        return

    if not info["task"]:
        core.popup("Aucune task assignée à cette scène : impossible d'exporter l'asset/shot.", title="Export FBX/OBJ", severity="error")
        return

    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    entity = info["entity"]
    task = info["task"]

    params = params or {}
    extension = params.get("extension") or ".fbx"
    whole_scene = params.get("whole_scene", False)
    nodes = params.get("nodes") or []
    update_master = params.get("update_master", True)
    update_thumbnail = params.get("update_thumbnail", True)
    start_frame = params.get("start_frame")
    end_frame = params.get("end_frame")
    comment = params.get("comment", "")

    if not whole_scene and nodes:
        cmds.select(nodes, replace=True)

    frame_range = None
    if start_frame is not None and end_frame is not None:
        frame_range = (start_frame, end_frame)

    path = core.products.generateProductPath(entity=entity, task=task, extension=extension, version=None, location="global")
    #the geo master lives in its own "geo" subfolder of the master folder, apart from the USD master
    default_master_path = core.products.generateProductPath(entity=entity, task=task, extension=extension, version="master", location="global")
    master_path = os.path.join(os.path.dirname(default_master_path), "geo", os.path.basename(default_master_path))

    os.makedirs(os.path.dirname(path), exist_ok=True)

    if extension == ".obj":
        write_obj(path, selection_only=not whole_scene, frame=start_frame, materials=params.get("obj_materials", False), normals=params.get("obj_normals", False), smoothing=params.get("obj_smoothing", True))
    else:
        write_fbx(path, selection_only=not whole_scene, frame_range=frame_range, triangulate=params.get("fbx_triangulate", False), smoothing_groups=params.get("fbx_smoothing_groups", True), skins=params.get("fbx_skins", False), blendshapes=params.get("fbx_blendshapes", False), embed_textures=params.get("fbx_embed_textures", False))

    if not os.path.exists(path):
        raise RuntimeError(f"Export failed, nothing was written to {path}")

    print(f"{extension[1:].upper()} exported: {path}")

    details = dict(entity)
    details["version"] = core.products.getProductDataFromFilepath(path).get("version", "")
    details["sourceScene"] = core.getCurrentFileName()
    details["product"] = task
    details["comment"] = comment

    info_path = core.products.getVersionInfoPathFromProductFilepath(path)
    core.saveVersionInfo(filepath=info_path, details=details)

    if update_thumbnail and core.products.getUseProductPreviews():
        preview = core.products.generateProductPreview()
        if preview:
            core.products.setProductPreview(os.path.dirname(path), preview)

    if update_master:
        os.makedirs(os.path.dirname(master_path), exist_ok=True)
        shutil.copy2(path, master_path)
        print(f"Master copied: {master_path}")

        #the geo subfolder has its own version info, so it can't clobber the USD master's info
        master_info_path = core.products.getVersionInfoPathFromProductFilepath(master_path)
        core.saveVersionInfo(filepath=master_info_path, details=details)

    from DaisyTools.core.version_cleanup import check_version_limit_for_output
    from DaisyTools.core.dcc.launcher import get_main_window

    check_version_limit_for_output(core, entity, task, path, parent=get_main_window())

    return path
