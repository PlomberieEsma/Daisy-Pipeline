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
#   by Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio
#   art by Joan G. Stark (Spunk)

#-----------------------------------------------------------------------------------#
# Version cap checks run after an export (products) and after a save (scenefiles)   #
# Only decides when to offer a clean up - the window itself lives in                #
# delete_versions_window.py so it can be opened from anywhere else too              #
#-----------------------------------------------------------------------------------#

import os, json

from PrismUtils.Decorators import err_catcher

from DaisyTools.ui.delete_versions_window import openDeleteVersionsWindow

#get variables from config.json
current_dir = os.path.dirname(__file__)
config_file_path = os.path.join(current_dir, "../lib/config.json")
with open(config_file_path, mode="r", encoding="utf-8") as read_file:
    config_file = json.load(read_file)

#how many versions of a product we keep before offering a clean up
MAX_VERSIONS = config_file["global"]["max_product_version"]

#same idea for the work scenes of a task (Maya .ma/.mb, Houdini .hip/.hipnc/.hiplc)
MAX_SCENE_VERSIONS = config_file["global"]["max_scene_version"]


@err_catcher(name=__name__)
def getVersionNumber(core, version):

    #-----------------------------------------------------------------------------------#
    # Sortable integer for a version name ("v0003" -> 3), -1 when it can't be parsed     #
    #-----------------------------------------------------------------------------------#

    num = core.products.getIntVersionFromVersionName(version.get("version"))
    return -1 if num is None else num


@err_catcher(name=__name__)
def getProductVersions(core, entity, product):

    #-----------------------------------------------------------------------------------#
    # List the numbered versions of a product, oldest first                             #
    # 'master' is left out: it is a copy of the latest version, not a version of its own #
    #-----------------------------------------------------------------------------------#

    versions = core.products.getVersionsFromProduct(entity, product) or []
    versions = [
        v for v in versions if v.get("version") and v.get("version") != "master"
    ]
    return sorted(versions, key=lambda v: getVersionNumber(core, v))


@err_catcher(name=__name__)
def checkVersionLimit(core, entity, product, currentVersion=None, parent=None):

    #-----------------------------------------------------------------------------------#
    # Once a product has more than MAX_VERSIONS versions, offer a clean up               #
    # It is only ever an offer: nothing is deleted unless the user opens the window      #
    # and ticks versions there                                                           #
    #-----------------------------------------------------------------------------------#

    versions = getProductVersions(core, entity, product)
    if len(versions) <= MAX_VERSIONS:
        return []

    result = core.popupQuestion(
        "'%s' now has %s versions (soft limit is %s).\n\nDelete some of them?"
        % (product, len(versions), MAX_VERSIONS),
        title="Clean up versions",
        buttons=["Delete versions...", "Not now"],
        default="Not now",
        escapeButton="Not now",
    )
    if result != "Delete versions...":
        return []

    #the master layer sublayers the latest version, so deleting it would break the
    #master - lock the version we just wrote and the highest one on disk
    locked = {v for v in (currentVersion, versions[-1].get("version")) if v}

    return openDeleteVersionsWindow(
        core,
        product,
        versions,
        lockedVersions=locked,
        message=(
            "'%s' has %s versions (soft limit is %s).\nTick the versions you want to delete:"
            % (product, len(versions), MAX_VERSIONS)
        ),
        parent=parent,
    )


@err_catcher(name=__name__)
def getSceneEntity(core, data):

    #-----------------------------------------------------------------------------------#
    # Rebuild the Prism entity dict from the metadata of a scenefile                     #
    # Same shape as DaisyTools.core.get_entity_info, but silent on purpose: this runs    #
    # on every save, so a scene living outside the pipeline is simply ignored            #
    #-----------------------------------------------------------------------------------#

    entityType = data.get("type", "")

    if entityType == "asset":
        return {"type": "asset", "asset_path": data.get("asset_path", "")}

    if entityType == "shot":
        return {
            "type": "shot",
            "sequence": data.get("sequence", ""),
            "shot": data.get("shot", ""),
        }

    return None


@err_catcher(name=__name__)
def getSceneVersions(core, entity, department, task):

    #-----------------------------------------------------------------------------------#
    # List the work scenes of a task, oldest first                                       #
    # Only the scene formats of the running DCC are counted, so Maya never sees the      #
    # Houdini files sitting next to it (and the other way around)                        #
    #-----------------------------------------------------------------------------------#

    extensions = list(getattr(core.appPlugin, "sceneFormats", None) or [])
    scenePaths = core.entities.getScenefiles(
        entity, step=department, category=task, extensions=extensions or None
    ) or []

    versions = []
    for scenePath in scenePaths:
        data = core.getScenefileData(scenePath) or {}
        version = {
            "version": data.get("version"),
            "path": scenePath,
            "paths": [scenePath],
        }
        #a file we can't put a version number on isn't a version of anything
        if not version["version"] or getVersionNumber(core, version) < 0:
            continue
        versions.append(version)

    return sorted(versions, key=lambda v: getVersionNumber(core, v))


@err_catcher(name=__name__)
def getSceneVersionFiles(core, scenePath):

    #-----------------------------------------------------------------------------------#
    # Every file that belongs to one scene version: the scene itself, its versioninfo,   #
    # its preview and whatever the app plugin attaches to it (.xgen/.abc in Maya)        #
    # The Maya plugin hands back bare file names, so anything relative is rebased on     #
    # the scene folder                                                                   #
    #-----------------------------------------------------------------------------------#

    sceneDir = os.path.dirname(scenePath)

    files = []
    for path in core.getScenefilePaths(scenePath) or []:
        if not os.path.isabs(path):
            path = os.path.join(sceneDir, path)
        path = path.replace("\\", "/")
        if path not in files:
            files.append(path)

    return files


@err_catcher(name=__name__)
def deleteSceneVersion(core, version):

    #-----------------------------------------------------------------------------------#
    # Remove one work scene and its side files from every location it exists in          #
    # Returns the error messages, empty when it went through                             #
    #-----------------------------------------------------------------------------------#

    #a scene can live in several locations (global/local) - drop them all
    scenePaths = []
    for scenePath in (version.get("paths") or [version.get("path")]):
        if not scenePath:
            continue
        candidates = [scenePath]
        if core.useLocalFiles:
            candidates += [
                core.convertPath(scenePath, target="global"),
                core.convertPath(scenePath, target="local"),
            ]
        for candidate in candidates:
            candidate = candidate.replace("\\", "/")
            if candidate not in scenePaths:
                scenePaths.append(candidate)

    errors = []
    for scenePath in scenePaths:
        if not os.path.isfile(scenePath):
            continue

        #cheap guard against removing anything but this version's own files
        prefix = os.path.splitext(os.path.basename(scenePath))[0]

        for path in getSceneVersionFiles(core, scenePath):
            if not os.path.isfile(path):
                continue
            if not os.path.basename(path).startswith(prefix):
                errors.append("%s: unexpected path %s" % (version.get("version"), path))
                continue
            try:
                os.remove(path)
            except Exception as e:
                errors.append("%s: %s" % (version.get("version"), e))

    return errors


@err_catcher(name=__name__)
def checkSceneVersionLimit(core, scenePath=None, parent=None):

    #-----------------------------------------------------------------------------------#
    # Once a task has more than MAX_SCENE_VERSIONS work scenes, offer a clean up         #
    # Same deal as checkVersionLimit does for products: it is only ever an offer,        #
    # nothing is deleted unless the user opens the window and ticks versions there       #
    #-----------------------------------------------------------------------------------#

    scenePath = scenePath or core.getCurrentFileName()
    if not scenePath:
        return []

    data = core.getScenefileData(scenePath) or {}
    entity = getSceneEntity(core, data)
    department = data.get("department")
    task = data.get("task")

    #scene saved outside the pipeline: nothing to watch over, stay quiet
    if not entity or not department or not task:
        return []

    versions = getSceneVersions(core, entity, department, task)
    if len(versions) <= MAX_SCENE_VERSIONS:
        return []

    result = core.popupQuestion(
        "'%s' now has %s scene versions (soft limit is %s).\n\nDelete some of them?"
        % (task, len(versions), MAX_SCENE_VERSIONS),
        title="Clean up scene versions",
        buttons=["Delete versions...", "Not now"],
        default="Not now",
        escapeButton="Not now",
    )
    if result != "Delete versions...":
        return []

    #the scene open in the DCC can't be pulled from under it, and the highest version
    #is the one everybody picks up next - lock them both
    locked = {v for v in (data.get("version"), versions[-1].get("version")) if v}

    return openDeleteVersionsWindow(
        core,
        task,
        versions,
        lockedVersions=locked,
        message=(
            "'%s' has %s scene versions (soft limit is %s).\nTick the versions you want to delete:"
            % (task, len(versions), MAX_SCENE_VERSIONS)
        ),
        parent=parent,
        deleteFunc=deleteSceneVersion,
        lockedLabel=" (in use)",
    )
