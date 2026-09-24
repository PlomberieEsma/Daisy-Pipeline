from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
import hou

def create_path()
    info = get_entity_info()

    entity = info["entity"]
    task = info["task"]

    node = hou.pwd()
    extension = node.parm("extension").evalAsString()

    core = get_core()
    path = core.products.generateProductPath(entity=entity, task=task, extension=f".{extension}", version=None, location="global")

    return path


