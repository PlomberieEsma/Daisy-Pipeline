from pxr import Sdf, Usd, UsdGeom

USD_FILE    = "D:/document/Project/test_Pipe/03_Production/Assets/textureTest/Export/USD/layers/geo.usda"
NEW_VARIANT = "geo_var03"
PROXY_REF   = "../../Modeling/master/textureTest_Modeling_master.usda"
RENDER_REF  = "../../Modeling/master/textureTest_Modeling_master.usda"


stage = Usd.Stage.Open(USD_FILE)
root  = stage.GetPrimAtPath("/ours_asset")

vset = root.GetVariantSets().GetVariantSet("geo")
vset.AddVariant(NEW_VARIANT)
vset.SetVariantSelection(NEW_VARIANT)

with vset.GetVariantEditContext():
    geo    = stage.DefinePrim("/ours_asset/geo", "Scope")
    proxy  = stage.DefinePrim("/ours_asset/geo/proxy", "Scope")
    render = stage.DefinePrim("/ours_asset/geo/render", "Scope")

    UsdGeom.Imageable(geo).GetPurposeAttr().Set("default")
    UsdGeom.Imageable(proxy).GetPurposeAttr().Set("proxy")
    UsdGeom.Imageable(render).GetPurposeAttr().Set("render")

    proxy.GetReferences().AddReference(PROXY_REF)
    render.GetReferences().AddReference(RENDER_REF)
    render.CreateRelationship("proxyPrim").SetTargets([Sdf.Path("/ours_asset/geo/proxy")])

stage.GetRootLayer().Save()
print(f"Variant '{NEW_VARIANT}' ajouté")