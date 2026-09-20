from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

from DaisyTools.core.version_cleanup import check_version_limit_for_output
from DaisyTools.core.dcc.launcher import get_main_window

core = get_core()
info = get_entity_info()
entity = info["entity"]
task = info["task"]
path = core.products.getLatestVersionFromProduct(entity=entity, product=task, includeMaster=False)["path"]
core.popup(path)
name = info["name"]
extension = "usda"

comment = ""

scene = core.getCurrentFileName()
details = core.getScenefileData(scene)
details.pop("filename", None)
details.pop("extension", None)
details["version"] = core.products.getProductDataFromFilepath(path).get("version", "")
details["sourceScene"] = scene
details["product"] = task
details["comment"] = comment

info_path = core.products.getVersionInfoPathFromProductFilepath(path)
core.saveVersionInfo(filepath=path, details=details)

check_version_limit_for_output(core, entity, task, path, parent=get_main_window())
