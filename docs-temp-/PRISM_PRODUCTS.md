# Les *Products* dans Prism — modèle, API et personnalisation de la fenêtre

Ce document explique :

1. Ce qu'est un **product** dans Prism (concept + structure disque + modèle de données).
2. Comment **utiliser** les products via l'API `core.products`.
3. Comment Prism **affiche** les products dans la fenêtre Products.
4. Comment le **plugin USD officiel** modifie cet affichage.
5. Comment **reproduire** la même chose dans notre plugin `EsmaUSD`.

> Sources lues dans l'install Prism de ce poste :
> - `C:\Program Files\Prism2\Scripts\PrismUtils\Products.py` (l'API)
> - `C:\Program Files\Prism2\Scripts\ProjectScripts\ProductBrowser.py` (la fenêtre)
> - `C:\ProgramData\Prism2\plugins\USD\Scripts\Prism_USD_Functions.cp311-win_amd64.pyd`
>   (le plugin USD — **compilé**, licence propriétaire : on ne peut lire que les noms
>   de méthodes/callbacks exportés, pas le corps).

---

## 1. C'est quoi un *product* ?

Un **product** (= « identifier ») est un *output versionné* d'un asset ou d'un shot :
un cache géométrique, un USD, une alembic, une caméra, etc. C'est l'équivalent côté
« sortie » de ce qu'une scenefile est côté « travail ».

Vocabulaire Prism, du plus large au plus précis :

```
entity (asset / shot)
└── product  (= identifier, ex: "mod", "_ShotCam", "char_main")
    └── version (vNNNN, + un éventuel "master")
        └── fichier(s)  (ex: mod_v0003.usda, + versioninfo.json)
```

### Layout sur le disque

La hiérarchie de dossiers n'est **pas codée en dur** : elle vient du *project template*
(résolu par `core.projects.getResolvedProjectStructurePath("products"/"productVersions"/…)`).
Pour notre projet, le template donne (cf. `CLAUDE.md`) :

```
Export/<department>/<task>/vNNNN/<name>_vNNNN.usda
Export/<department>/<task>/master/<name>_master.usda
```

Chaque dossier de version contient aussi un fichier **versioninfo**
(`versioninfo.json` / `.yml` selon la config projet) écrit via `core.saveVersionInfo(...)`,
qui porte les métadonnées (version, author, comment, date, sourceScene, product, …).

### Le `master`

`master` est une copie « toujours la dernière » de la version la plus récente, gérée par
`core.products.updateMasterVersion(path)` (copie/symlink + recopie du versioninfo).
Activé par le réglage projet `globals/useMasterVersion`
(`core.products.getUseMaster()`).

### « Linked to tasks »

Selon le réglage projet `globals/productTasks` (`core.products.getLinkedToTasks()`),
un product est identifié soit juste par son nom, soit par
`department/task/product`. Notre projet utilise les départements
(`PRISM_USE_DEPARTMENTS_FOR_PRODUCTS=1`), donc l'arbre est groupé par département → task.

---

## 2. Le modèle de données

### Le dict `entity`

C'est la monnaie d'échange de presque toutes les méthodes :

```python
{"type": "asset", "asset_path": "chars/ours_polaire"}
{"type": "shot",  "sequence": "a", "shot": "0010"}
```

### Le dict `product` (un identifier)

Renvoyé par `getProductNamesFromEntity` / `getProductsFromEntity`. En gros l'`entity`
+ :

```python
{
    "product": "mod",                 # nom de l'identifier
    "department": "02_mod",           # si linkedToTasks
    "task": "modeling",
    "locations": {"global": ".../Export/02_mod/modeling"},
}
```

### Le dict `version`

Renvoyé par `getVersionsFromContext` / `getVersionsFromProduct` :

```python
{
    "product": "mod",
    "version": "v0003",               # ou "master"
    "wedge": None,                    # pour le wedging, sinon absent
    "paths":     [".../v0003/mod_v0003.usda"],
    "locations": {"global": ".../v0003/mod_v0003.usda"},
    # + les clés de l'entity / du product
}
```

Le « fichier préféré » d'une version (celui qui s'affiche / s'importe) est résolu par
`getPreferredFileFromVersion(version)` : il lit la clé `preferredFile` du versioninfo
si elle existe, sinon il prend le premier fichier non blacklisté du dossier.
**C'est le point d'entrée que le plugin USD détourne** (voir §4).

---

## 3. L'API `core.products` (méthodes utiles)

Toutes dans `PrismUtils/Products.py`. Les plus importantes :

### Lister

```python
# tous les identifiers d'une entity, dédupliqués (dict {idf: productData})
core.products.getProductNamesFromEntity(entity, locations=None)

# bruts (un item par emplacement)
core.products.getProductsFromEntity(entity, locations=None)

# versions d'un product
core.products.getVersionsFromProduct(entity, product, locations="all")
core.products.getVersionsFromContext(productContext, locations=None)

# la dernière version (gère le master)
core.products.getLatestVersionFromVersions(versions, includeMaster=True, wedge=None)
core.products.getLatestVersionFromProduct(product, entity=None, includeMaster=True)
core.products.getLatestVersionpathFromProduct(product, entity=None, includeMaster=True)
```

### Résoudre des chemins / données

```python
core.products.getProductPathFromEntity(entity, includeProduct=False)
core.products.getPreferredFileFromVersion(version, location=None)
core.products.getProductDataFromFilepath(filepath)          # filepath -> dict {version, comment, user, ...}
core.products.getVersionInfoPathFromProductFilepath(filepath)  # = dirname(filepath)
core.products.getVersionFromFilepath(filepath, num=False)
core.products.getMasterVersionLabel(path)                   # "master (v0003)"
```

### Écrire / versionner (déjà utilisé dans `EsmaUSD/saveas/exportUSD.py`)

```python
# génère le chemin de la prochaine version (ou d'une version donnée / "master")
core.products.generateProductPath(entity, task, extension=".usda",
                                   version=None, location="global",
                                   comment=None, user=None, returnDetails=False)

core.products.getNextAvailableVersion(entity, product)      # "v0004"
core.products.createProduct(entity, product, location="global")  # crée le dossier + callback onProductCreated
core.products.ingestProductVersion(files, entity, product, comment=None, version=None)
core.products.updateMasterVersion(path)                     # promeut path en master
core.products.setComment(versionPath, comment)
```

### Réglages / groupes / tags

```python
core.products.getUseMaster()
core.products.getLinkedToTasks()
core.products.getGroupFromProduct(product) / setProductsGroup(products, group)
core.products.getTagsFromProduct(product) / setProductTags(product, tags)
```

> ⚠️ Côté EsmaUSD on s'appuie déjà sur `generateProductPath`, `getNextAvailableVersion`
> et le master, **comme recommandé dans `CLAUDE.md`** : on ne reconstruit jamais les
> chemins `vNNNN`/`master` à la main, sinon ça casse au moindre changement de template.

---

## 4. Comment la fenêtre Products affiche les choses

Fichier : `ProjectScripts/ProductBrowser.py` (classe `ProductBrowser(QDialog)`).

Trois zones :

| Widget | Rôle |
|---|---|
| `w_entities` | sélection asset/shot (gauche) |
| `tw_identifier` | **arbre des products** (= identifiers), au centre |
| `tw_versions`   | **tableau des versions** du product sélectionné, à droite |

Colonnes du tableau de versions (`self.versionLabels`) :
`["Version", "Comment", "Type", "User", "Date", "Path"]` (+ `Location`, `Size` selon config).

### Flux de remplissage

1. `updateIdentifiers()` (ligne ~1102) : vide `tw_identifier`, appelle
   `getProductNamesFromEntity`, puis **construit l'arbre** — groupé par
   `département → task` si `getLinkedToTasks()`, sinon à plat. Chaque item porte le
   dict product dans `item.setData(0, Qt.UserRole, productData)`.
2. `updateVersions()` (ligne ~1225) : pour le product sélectionné, appelle
   `getVersionsFromContext`, et pour chaque version résout `getPreferredFileFromVersion`
   puis `addVersionToTable(...)`.
3. `addVersionToTable(...)` (ligne ~1316) : crée les cellules (Version, Comment, Type
   = extension du fichier, etc.) et, en fin de méthode, émet le callback
   `productVersionAdded`.

### Points d'extension officiels (callbacks)

Ce sont les seuls « trous » prévus pour un plugin, repérés dans `ProductBrowser.py` :

| Callback | Args | Quand |
|---|---|---|
| `onProductBrowserOpen` | `[browser]` | à l'ouverture de la fenêtre (ligne 77) |
| `productSelectorContextMenuRequested` | `[browser, viewUi, pos, rcmenu]` | clic droit sur identifier/versions (ligne 707) |
| `productVersionAdded` | `[browser, row, filepath, versionName, comment, user, locations]` | chaque ligne de version ajoutée (ligne 1441) |
| `onCreateProductDlgOpen` / `onCreateVersionDlgOpen` | `[browser, dlg]` | dialogues de création |
| `onProductCreated` | `[products, path, context]` | dossier product créé |

Pour **personnaliser l'affichage de l'arbre lui-même** (`updateIdentifiers`), il n'y a
pas de callback : il faut faire du **monkeyPatch** (voir §6). C'est précisément ce que
fait le plugin USD.

---

## 5. Ce que fait *concrètement* le plugin USD

`Prism_USD_Functions` est livré **compilé** (`.pyd`), donc on ne voit que les symboles
exportés. Voici ce qu'ils révèlent (noms de méthodes + callbacks Cython visibles dans
le binaire) :

**Callbacks enregistrés** (via une méthode `registerCallbacks`) :

- `onProductBrowserOpen` → récupère le handle de la fenêtre, branche le reste.
- `productSelectorContextMenuRequested` → ajoute ~20 entrées au menu contextuel
  (chaînes visibles : `"Create Sublayer..."`, `"Open in Product Browser"`).
- `mediaPlayerContextMenuRequested`, `textureLibraryTextureContextMenuRequested`,
  `textureLibraryViewContextMenuRequested` → autres fenêtres.
- `openPBAssetContextMenu`, `openPBShotContextMenu` → menus des entities.

**MonkeyPatch** (la clé de l'affichage — symbole `monkeyPatch` présent) :

- `productBrowser_updateIdentifiers` → **remplace `ProductBrowser.updateIdentifiers`** :
  c'est ce qui change la façon dont les products apparaissent dans l'arbre (regroupement
  USD, sublayers, etc.).
- `getPreferredFileFromVersion` → patch de `core.products.getPreferredFileFromVersion`
  pour qu'une version USD pointe sur le bon layer (`.usd`/`.usda`) au lieu du premier
  fichier venu.
- `navigateToProduct` → navigation cohérente avec le regroupement custom.

**Méthodes métier USD** (visibles) :

- `getProductsFromStage` — lit les sublayers d'un stage USD pour en déduire des products.
- `createSublayer`, `createSublayerLayerForDepartment`,
  `setSublayerVersionInDepartmentLayer` — gestion des sublayers par département.
- `generateUsdProductPath`, `getDepartmentProductName`,
  `createDefaultUsdFileForProduct` — création d'un product « conteneur » USD.
- `addQuickViewToProductViewer`, `updateQuickViewInProductViewer` — ajoute un panneau
  d'aperçu (quick view) dans la fenêtre Products.

**Réglages exposés** (chaînes visibles) :
`"Create USD container product on entity creation"`, `chb_useSublayer`,
`chb_sublayerMasters`.

> En résumé : le plugin USD **n'édite pas Prism**. Il (1) s'accroche à l'ouverture de la
> fenêtre via `onProductBrowserOpen`, (2) **monkeyPatch `updateIdentifiers`** pour
> réécrire l'arbre des products, (3) **monkeyPatch `getPreferredFileFromVersion`** pour
> choisir le bon layer USD, (4) enrichit les menus contextuels, (5) ajoute un quick view.

---

## 6. Reproduire la même chose dans `EsmaUSD`

> **Implémentation livrée** (cf. `prism/EsmaUSD/Scripts/Prism_EsmaUSD_Functions.py`) :
> on affiche, dans un groupe **« USD »**, le **contenu du conteneur USD** de l'entity —
> c.-à-d. les products référencés en `subLayers` par le fichier
> `Export/USD/.../<entity>_USD_master.usda` (équivalent du `getProductsFromStage` du
> plugin officiel). Arbre obtenu :
>
> ```
> USD                  (groupe)
> ├── USD global       (le conteneur, product "USD" -> master + versions)
> ├── mod              (= _layer_mod_master, affiché avec juste le nom de task)
> └── surf             (= _layer_surf_master)
> ```
>
> Chaque enfant affiche normalement son master + ses versions ; seul le **texte** est
> changé (le `data` product reste intact pour la navigation). Tout est fait **à
> l'affichage** (monkeyPatch de `updateIdentifiers`, visible uniquement quand le plugin
> est actif — rien n'est écrit sur le disque). L'icône `prism/EsmaUSD/Resources/usd.png`
> est posée sur le groupe, les enfants et les versions USD.
>
> Mécanique : `buildUsdGlobalGroup()` récupère le conteneur via
> `core.products.getLatestVersionpathFromProduct("USD", entity)`, lit ses `subLayers`
> (pxr `Sdf.Layer` si dispo, sinon parsing texte du `.usda`), résout chaque sublayer en
> nom de product avec `core.products.getProductDataFromFilepath(...)`, puis reparente les
> items sous le groupe en relabellisant via `displayLabelForProduct()`. Constantes en
> haut du fichier : `USD_CONTAINER_PRODUCT`, `USD_GROUP_LABEL`, `USD_CONTAINER_LABEL`,
> `LAYER_NAME_RE`. Les entities sans conteneur USD gardent l'arbre Prism normal.
>
> Détail important confirmé dans `PrismUtils/PluginManager.py:getFunctionInfo` : pour une
> **méthode liée** (`browser.updateIdentifiers`), `monkeyPatch` cible
> `function.__self__`, c.-à-d. **l'instance** de la fenêtre, pas la classe. Le patch est
> donc posé par fenêtre (pas de conflit entre deux ProductBrowser), et comme on lui passe
> une méthode liée *au plugin*, `self` reste le plugin → on récupère la fenêtre via une
> référence stockée dans `onProductBrowserOpen`.

Tout passe par le plugin Prism `prism/EsmaUSD` (jamais en éditant Prism). On respecte
les conventions du `CLAUDE.md` : `qtpy` pour Qt, `err_catcher` sur chaque hook,
callbacks > API directe > monkeyPatch en dernier recours, et `callUnpatchedFunction`
pour ne pas dupliquer le corps de la fonction patchée.

### 6.1 Enregistrer les callbacks (dans `Prism_EsmaUSD_Functions.__init__`)

```python
def __init__(self, core, plugin):
    self.core = core
    self.plugin = plugin
    self.core.registerCallback("onProductBrowserOpen",
                               self.onProductBrowserOpen, plugin=self)
    self.core.registerCallback("productSelectorContextMenuRequested",
                               self.onProductContextMenu, plugin=self)
    self.core.registerCallback("productVersionAdded",
                               self.onProductVersionAdded, plugin=self)
```

### 6.2 Détourner l'affichage de l'arbre (monkeyPatch d'`updateIdentifiers`)

C'est l'équivalent direct du `productBrowser_updateIdentifiers` du plugin USD.

```python
@err_catcher(name=__name__)
def onProductBrowserOpen(self, browser):
    # garde une ref, et patche l'instance de la fenêtre
    self.core.plugins.monkeyPatch(browser.updateIdentifiers,
                                  self.updateIdentifiers, self, force=True)
    browser._esmaPatched = True
    self._browser = browser

@err_catcher(name=__name__)
def updateIdentifiers(self, *args, **kwargs):
    browser = self._browser
    # 1) laisse Prism construire l'arbre normal (ne PAS réécrire son corps)
    result = self.core.plugins.callUnpatchedFunction(
        browser.updateIdentifiers, *args, **kwargs)

    # 2) post-traite l'arbre : ici on peut renommer, regrouper, ajouter une icône
    tree = browser.tw_identifier
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        data = item.data(0, Qt.UserRole) or {}
        # ex : marquer les products USD
        if str(data.get("product", "")).endswith("_usd"):
            item.setText(0, "🟣 " + item.text(0))
    return result
```

> `monkeyPatch(orig, new, owner, force=True)` et `callUnpatchedFunction(orig, ...)` :
> source `PrismUtils/PluginManager.py`. On patche **l'instance** (`browser.updateIdentifiers`)
> reçue dans `onProductBrowserOpen`, ce qui est plus propre que patcher la classe.

### 6.3 Choisir le bon fichier d'une version (monkeyPatch de `getPreferredFileFromVersion`)

Si nos versions contiennent plusieurs fichiers et qu'on veut toujours afficher/importer
le `.usda` :

```python
@err_catcher(name=__name__)
def onProductBrowserOpen(self, browser):
    ...
    self.core.plugins.monkeyPatch(self.core.products.getPreferredFileFromVersion,
                                  self.getPreferredFileFromVersion, self, force=True)

@err_catcher(name=__name__)
def getPreferredFileFromVersion(self, version, location=None):
    path = self.core.plugins.callUnpatchedFunction(
        self.core.products.getPreferredFileFromVersion, version, location=location)
    if path and not path.endswith((".usd", ".usda", ".usdc")):
        folder = version.get("path") or os.path.dirname(path or "")
        for f in os.listdir(folder):
            if f.endswith((".usda", ".usd", ".usdc")):
                return os.path.join(folder, f)
    return path
```

### 6.4 Enrichir le menu contextuel

```python
@err_catcher(name=__name__)
def onProductContextMenu(self, browser, viewUi, pos, rcmenu):
    from qtpy.QtWidgets import QAction
    product = browser.getCurrentProduct()
    if not product:
        return
    act = QAction("EsmaUSD : créer un sublayer…", viewUi)
    act.triggered.connect(lambda: self.createSublayer(product))
    rcmenu.addAction(act)
```

### 6.5 Décorer les lignes de version (optionnel)

```python
@err_catcher(name=__name__)
def onProductVersionAdded(self, browser, row, filepath, versionName,
                          comment, user, locations):
    typeCol = browser.versionLabels.index("Type")
    item = browser.tw_versions.item(row, typeCol)
    if item and filepath and filepath.endswith((".usda", ".usd", ".usdc")):
        item.setText("USD")
```

---

## 7. Checklist pour égaler le plugin USD

- [ ] `registerCallback("onProductBrowserOpen", …)` pour obtenir le handle de la fenêtre.
- [ ] `monkeyPatch(browser.updateIdentifiers, …)` + `callUnpatchedFunction` → réécrire
      l'arbre des products (regroupement / icônes / sublayers).
- [ ] `monkeyPatch(core.products.getPreferredFileFromVersion, …)` → cibler le bon layer USD.
- [ ] `registerCallback("productSelectorContextMenuRequested", …)` → menus « Create
      Sublayer… », « Open in Product Browser… ».
- [ ] (option) `productVersionAdded` → colonnes / labels custom.
- [ ] (option) un quick view, à la `addQuickViewToProductViewer`.
- [ ] Tout dans le plugin, `qtpy` pour Qt, `err_catcher` sur chaque hook.

---

## 8. Limites / à vérifier soi-même

- `Prism_USD_Functions` est **compilé** : les détails d'implémentation (regroupement
  exact, structure des sublayers) sont déduits des noms de symboles, pas lus. À
  confirmer en testant le plugin USD activé dans le Project Browser.
- Le monkeyPatch d'`updateIdentifiers` dépend de l'API interne de `ProductBrowser` :
  c'est le « dernier recours » du `CLAUDE.md`. Le préférer **uniquement** parce qu'aucun
  callback ne couvre la reconstruction de l'arbre. Revalider à chaque update de Prism.
- Les noms de colonnes (`versionLabels`) et la structure de l'arbre peuvent changer
  entre versions de Prism — toujours passer par `browser.versionLabels.index(...)`.
```