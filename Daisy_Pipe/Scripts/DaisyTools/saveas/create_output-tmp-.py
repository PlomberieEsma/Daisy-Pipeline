# output de rendu
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

core = get_core()
info = get_entity_info()
entity = info["entity"]
task = info["task"]
version = core.products.getNextAvailableVersion(entity=entity, product=task)
name = info["name"]
extension = "usda"

path = core.products.getProductPathFromEntity(entity=entity, includeProduct=False)

output = f"{path}\\{task}\\{version}\\{name}_{task}_{version}.{extension}"

return output




# output de proxy
from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info

core = get_core()
info = get_entity_info()
name = info["name"]
entity = info["entity"]
task = info["task"]
version = core.products.getLatestVersionFromProduct(entity=entity, product=task, includeMaster=False)
version = version["version"]
extension = "usda"

path = core.products.getProductPathFromEntity(entity=entity, includeProduct=False)

return f"{path}\\{task}\\{version}_proxy\\{name}_{task}_proxy_{version}.{extension}"