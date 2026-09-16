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

from DaisyTools.core.get_entity_info import get_entity_info
from DaisyTools.core.core import get_core, write_usd, create_master, create_master_clips, SUBDIVISION_METHOD_MAP, USD_FILE_FORMAT
from DaisyTools.core.dcc.launcher import get_dcc


def export_usd(params=None):

    #Export the current scene to USD, driven by the export state's settings (params).
    #params comes from EsmaUsdExportClass.getExportParams() - a plain dict, no Qt involved here.

    core = get_core()
    if core is None:
        return

    info = get_entity_info()
    if info is None:
        return

    if not info["task"]:
        core.popup("Aucune task assignée à cette scène : impossible d'exporter l'asset/shot en USD.", title="Export USD", severity="error")
        return

    entity = info["entity"]
    task = info["task"]
    name = info["name"]
    is_shot = entity.get("type") == "shot"

    params = params or {}
    department = params.get("department") or info["department"]
    preset_name = department.split("_", 1)[-1] if "_" in department else department

    extension = params.get("extension") or ".usdc"
    default_prim = params.get("default_prim_override") or name
    whole_scene = params.get("whole_scene", False)
    nodes = params.get("nodes") or []
    update_master = params.get("update_master", True)
    update_thumbnail = params.get("update_thumbnail", True)
    export_uvs = params.get("export_uvs")
    subdivision_method = params.get("subdivision_method")
    animation_type = params.get("animation_type", "Time Samples")
    start_frame = params.get("start_frame")
    end_frame = params.get("end_frame")
    comment = params.get("comment", "")

    if not whole_scene and nodes and get_dcc() == "maya":
        # pyrefly: ignore [missing-import]
        import maya.cmds as cmds
        cmds.select(nodes, replace=True)

    overrides = {}
    if export_uvs is not None:
        overrides["exportUVs"] = export_uvs
    if subdivision_method:
        overrides["defaultMeshScheme"] = SUBDIVISION_METHOD_MAP.get(subdivision_method, subdivision_method)

    frame_range = None
    if start_frame is not None and end_frame is not None:
        frame_range = (start_frame, end_frame)

    #an export spanning more than one frame is an animation: it must reuse the
    #asset's existing geo selection set but never author a new one
    is_animation = bool(frame_range) and frame_range[0] != frame_range[1]

    path = core.products.generateProductPath(entity=entity, task=task, extension=extension, version=None, location="global")
    #the master's format is independent of the versioned file's Outputtype:
    #it's just a thin sublayer/clip wrapper, driven by config.json's usd_file_format
    master_path = core.products.generateProductPath(entity=entity, task=task, extension=f".{USD_FILE_FORMAT}", version="master", location="global")

    os.makedirs(os.path.dirname(path), exist_ok=True)

    is_file_per_frame = animation_type == "File per Frame" and frame_range and frame_range[0] != frame_range[1]

    if is_file_per_frame:
        base, ext = os.path.splitext(path)
        dcc = get_dcc()
        frame_paths = []
        for frame in range(int(frame_range[0]), int(frame_range[1]) + 1):
            if dcc == "maya":
                # pyrefly: ignore [missing-import]
                import maya.cmds as cmds
                cmds.currentTime(frame)
            frame_path = f"{base}.{frame:04d}{ext}"
            write_usd(preset_name, frame_path, default_prim=default_prim, selection_only=not whole_scene, overrides=overrides, frame_range=(frame, frame), is_shot=is_shot, is_animation=is_animation)
            frame_paths.append(frame_path)
        print(f"USD exported (file per frame): {len(frame_paths)} files in {os.path.dirname(path)}")
    else:
        write_usd(preset_name, path, default_prim=default_prim, selection_only=not whole_scene, overrides=overrides, frame_range=frame_range, is_shot=is_shot, is_animation=is_animation)
        print(f"USD exported: {path}")

    if update_master:
        if is_file_per_frame:
            clips_path = f"{base}.clips.usda"
            create_master_clips(frame_paths, frame_range, clips_path, default_prim=default_prim)
            create_master(clips_path, master_path, default_prim=default_prim, frame_range=frame_range)
        else:
            create_master(path, master_path, default_prim=default_prim, frame_range=frame_range)

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
        master_info_path = core.products.getVersionInfoPathFromProductFilepath(master_path)
        core.saveVersionInfo(filepath=master_info_path, details=details)

    return path
