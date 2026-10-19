def setup_geo(default_prim=""):
    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds
    from DaisyTools.core.get_entity_info import get_entity_info
    
    cmds.select(cl=True)
    
    info = get_entity_info()
    if info is None:
        return

    entity = info["entity"]          # dict Prism attendu par generateProductPath
    etype = entity["type"]
    dept = info["department"]
    task = info["task"]
    
    master_name = default_prim
    geo_name = f"{default_prim}_geo"

    if etype == "asset" and dept == "02_mod":
        #Find or create master group
        if cmds.objExists(master_name):
            existing = cmds.ls(master_name, long=True)[0]
            is_master_grp = (cmds.nodeType(existing) == "transform" and not cmds.listRelatives(existing, shapes=True, fullPath=True) and not cmds.listRelatives(existing, parent=True))
            if is_master_grp:
                master_grp = existing
            else:
                cmds.rename(existing, master_name + "_orig")
                master_grp = "|" + cmds.group(empty=True, name=master_name)
        else:
            master_grp = "|" + cmds.group(empty=True, name=master_name)
        #Find or create geo group
        geo_grp_path = f"{master_grp}|{geo_name}"
        if cmds.objExists(geo_grp_path):
            geo_grp = cmds.ls(geo_grp_path, long=True)[0]
        else:
            # Check if geo exists at the top level first
            if cmds.objExists(geo_name) and not cmds.listRelatives(geo_name, parent=True):
                geo_grp = cmds.parent(geo_name, master_grp)[0]
                geo_grp = cmds.ls(geo_grp, long=True)[0]
            else:
                new_geo = cmds.group(empty=True, name=geo_name)
                geo_grp = cmds.parent(new_geo, master_grp)[0]
                geo_grp = cmds.ls(geo_grp, long=True)[0]
        # Find all geometry shape nodes in the scene
        shapes = cmds.ls(geometry=True, noIntermediate=True)
        if shapes:
            # Find all unique top-level root nodes (transforms) containing these shapes
            roots = set()
            for shape in shapes:
                full_path = cmds.ls(shape, long=True)[0]
                parts = full_path.split("|")
                if len(parts) > 1 and parts[1]:
                    roots.add(parts[1])
            # Prepare paths to parent, avoiding parenting group itself or default cameras
            roots_to_parent = []
            for root in roots:
                root_path = "|" + root
                # Avoid parenting default cameras or the master group or geo group
                if root in ["persp", "top", "front", "side"]:
                    continue
                if root_path == master_grp or root_path == geo_grp:
                    continue
                # Check if it is already parented to geo_grp
                parent = cmds.listRelatives(root_path, parent=True, fullPath=True)
                if parent and parent[0] == geo_grp:
                    continue
                roots_to_parent.append(root_path)
            if roots_to_parent:
                cmds.parent(roots_to_parent, geo_grp)
        return master_name
    else:
        return

def geo_is_complete(master_grp):
    # pyrefly: ignore [missing-import]
    import maya.cmds as cmds

    entity_name = master_grp.rsplit("|", 1)[-1]
    geo_grp = f"{master_grp}|{entity_name}_geo"
    if not cmds.objExists(geo_grp):
        return False
    
    shapes = cmds.ls(geometry=True, noIntermediate=True)
    if not shapes:
        return True  # pas de géo dans la scène, rien à faire
    
    for shape in shapes:
        full_path = cmds.ls(shape, long=True)[0]
        if not full_path.startswith(geo_grp):
            return False
    
    return True