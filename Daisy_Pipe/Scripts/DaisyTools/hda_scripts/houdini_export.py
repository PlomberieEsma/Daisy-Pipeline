from Scripts.DaisyTools.core.core import get_core
from Scripts.DaisyTools.core.get_entity_info import get_entity_info
import hou

def update_path(hda=None):
    hda = hda or hou.pwd()
    hda.parm("path").set(create_path(hda))

def create_path(hda):
    info = get_entity_info()
    extension = hda.parm("extension").evalAsString()
    core = get_core()
    return core.products.generateProductPath(entity=info["entity"],task=info["task"],extension=f".{extension}",version=None,location="global")