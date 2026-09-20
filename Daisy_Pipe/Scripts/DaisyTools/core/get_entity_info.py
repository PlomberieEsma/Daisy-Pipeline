from DaisyTools.core.core import get_core

def get_entity_info():
    
    # Get information about the prism entity we are working on.
    # Ex:
    #   Type = Asset or Shot
    #   Entity = What we are working on (Ours ou Sq10_Sh10)
    # 
    # 
    # 
    # 
    # 
    # 
    # 
    # cc
    

    core = get_core()
    data = core.getCurrentScenefileData()
    entityType = data.get("type", "")

    if entityType not in ("asset", "shot"):
        core.popup("La scène n'est pas dans une entité Prism.", title="Export USD", severity="error")
        print("La scène n'est pas dans une entité Prism.")
        return None

    if entityType == "asset":
        entity = {"type": "asset", "asset_path": data.get("asset_path", "")}
        name = data.get("asset", "")
    else:
        entity = {"type": "shot", "sequence": data.get("sequence", ""),"shot": data.get("shot", "")}
        name = f"{data.get('sequence', '')}_{data.get('shot', '')}"

    path = core.paths.getEntityPath(entity=entity)

    return {
        "entity": entity,                       
        "name": name,
        "path": path,
        "department": data.get("department", ""),
        "task": data.get("task", ""),
        "project": core.projectName,            
        "projectPath": core.projectPath,
        "user": core.username,
    }