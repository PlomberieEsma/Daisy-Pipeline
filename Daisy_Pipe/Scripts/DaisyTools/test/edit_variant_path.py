from pxr import Usd, Sdf

USD_FILE = "D:/document/Project/test_Pipe/03_Production/Assets/textureTest/Export/USD/layers/geo.usda"
NEW_REF  = "../../Modeling/master/textureTest_Modeling_master.usda"

layer = Sdf.Layer.FindOrOpen(USD_FILE)


prim_path = Sdf.Path("/ours_asset{geo=geo_var03}geo/render")
prim_spec = layer.GetPrimAtPath(prim_path)

new_ref = Sdf.Reference(NEW_REF)
prim_spec.referenceList.prependedItems[:] = [new_ref]
layer.Save()
print(f"Référence mise à jour : {NEW_REF}")