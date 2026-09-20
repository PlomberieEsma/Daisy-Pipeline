from pxr import Sdf

USD_FILE       = "D:/document/Project/test_Pipe/03_Production/Assets/textureTest/Export/USD/layers/geo.usda"
VARIANT_TO_DEL = "geo_var02"

layer     = Sdf.Layer.FindOrOpen(USD_FILE)
root_spec = layer.GetPrimAtPath("/ours_asset")
vset_spec = root_spec.variantSets["geo"]

var_list = list(vset_spec.variants.keys())

print(var_list)

variant_spec = vset_spec.variants[VARIANT_TO_DEL]
Sdf.VariantSetSpec.RemoveVariant(vset_spec, variant_spec)

root_spec.variantSelections["geo"] = var_list[-2]

layer.Save()
print(f"Variant '{VARIANT_TO_DEL}' supprimé")