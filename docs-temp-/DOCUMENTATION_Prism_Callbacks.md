# Référence des Callbacks Prism — points d'extension pour PipeEsma

> Extraits du code de Prism v2 (`C:\Program Files\Prism2\Scripts`). Un callback est un
> **événement** émis par Prism via `self.core.callback(name="...", args=[...])`. Tu t'y abonnes
> avec `self.core.callbacks.registerCallback("...", maFonction, plugin=self)`.
>
> **Signature** : ta fonction reçoit les éléments de `args` dans l'ordre. Préfère
> `def maFonction(self, *args, **kwargs)` puis dépile, car la signature peut évoluer.

---

## 1. Démarrage / cycle de vie

| Callback | args | Quand |
|---|---|---|
| `postInitialize` | `[]` | Prism (core) entièrement initialisé. Bon endroit pour du setup global. |
| `onProjectListStartup` | `[origin]` | écran de sélection de projet. |
| `onSetProjectStartup` | `[…]` | au moment de définir le projet courant. |
| `onProjectChanged` | `[origin]` | le projet courant a changé. |
| `preLaunchApp` | `[…]` | juste avant de lancer un DCC depuis Prism. |
| `updatedEnvironmentVars` | `[reason, envVars, beforeRefresh]` | variables d'env modifiées. |
| `expandEnvVar` | `[…]` | résolution d'une variable d'environnement. |

## 2. Project Browser (fenêtre principale)

| Callback | args | Quand |
|---|---|---|
| `onProjectBrowserStartup` | `[origin]` | construction du Project Browser (UI prête). |
| `onProjectBrowserShow` | `[origin]` | le PB devient visible. |
| `onProjectBrowserRefreshUI` / `…Triggered` | `[origin]` | rafraîchissement UI. |
| `onProjectBrowserClose` | `[origin]` | fermeture. |
| `projectBrowser_loadUI` | `[origin]` | injecter des widgets/onglets custom. |
| `onSceneBrowserOpen` | `[sceneBrowser]` | onglet Scene Files ouvert. |
| `onMediaBrowserOpen` | `[mediaBrowser]` | onglet Media ouvert. |
| `onProductBrowserOpen` | `[productBrowser]` | onglet Products ouvert. |

## 3. Menus contextuels (clic droit) — **les plus utiles pour PipeEsma**

Tous ont la signature **`args = [browserWidget, rcmenu, modelIndex]`** (sauf indication).
Tu ajoutes tes actions au `QMenu` `rcmenu`.

| Callback | Cible (clic droit sur…) |
|---|---|
| `openPBAssetContextMenu` | un **asset** (arbre des entités) |
| `openPBShotContextMenu` | un **shot / séquence** |
| `openPBAssetDepartmentContextMenu` | un **department** d'asset |
| `openPBAssetTaskContextMenu` | une **task** d'asset ← *utilisé par EsmaUSD* |
| `openPBShotDepartmentContextMenu` | un **department** de shot |
| `openPBShotTaskContextMenu` | une **task** de shot |
| `openPBFileContextMenu` | un **scenefile** — args `[sceneBrowser, rcmenu, filepath]` |
| `openPBListContextMenu` | la liste media (MediaBrowser) |
| `sceneBrowserContextMenuRequested` / `mediaPlayerContextMenuRequested` / `projectBrowserContextMenuRequested` | bas niveau Qt |

> Pour récupérer la sélection courante depuis le `sceneBrowser` passé en argument :
> `getCurrentEntity()`, `getCurrentDepartment()`, `getCurrentTask()`.

## 4. Dialogs de création / édition

| Callback | Quand |
|---|---|
| `onCreateAssetDlgOpen` / `onCreateAssetDlgTypeChanged` | dialog « Create Asset ». |
| `onCreateProductDlgOpen` | « Create Product ». |
| `onCreateVersionDlgOpen` | « Create Version ». |
| `onCreateIdentifierDlgOpen` | « Create Identifier ». |
| `onCreateAovDlgOpen` | « Create AOV ». |
| `onDepartmentDlgOpen` / `onTaskDlgOpen` | dialogs department/task. |
| `onEditShotDlgLoaded` / `onEditShotDlgSaved` | édition de shot. |
| `onFolderDlgOpen` / `onAssetDlgOpen` | divers. |
| `onShotCreated` | un shot vient d'être créé. |
| `onEntityWidgetCreated` | widget d'entité instancié. |

## 5. State Manager & publish

| Callback | Quand |
|---|---|
| `onStateManagerOpen` | ouverture du State Manager (ajoute tes boutons/states). |
| `onStateManagerClose` | fermeture. |
| `onStateDeleted` | un state supprimé. |
| `prePublish` | avant un publish (validations globales). |

## 6. Scènes & versions

| Callback | args | Quand |
|---|---|---|
| `onSceneOpen` | `[…]` | une scène vient d'être ouverte. |
| `sceneSaved` | `[…]` | une scène vient d'être sauvegardée. |
| `masterVersionUpdated` | `[…]` | une *master version* a été mise à jour. |
| `productVersionAdded` | `[…]` | nouvelle version de product. |

## 7. Réglages (Settings)

| Callback | Quand |
|---|---|
| `onPrismSettingsOpen` / `onUserSettingsOpen` / `onUserSettingsSave` | réglages utilisateur. |
| `userSettings_loadUI` / `userSettings_saveSettings` / `userSettings_loadSettings` | onglet custom dans les réglages user. |
| `onProjectSettingsOpen` | réglages projet ouverts. |
| `projectSettings_loadUI` | injecter une section dans les réglages projet. |
| `preProjectSettingsLoad` / `postProjectSettingsLoad` | chargement des réglages projet. |
| `preProjectSettingsSave` / `postProjectSettingsSave` | sauvegarde des réglages projet. |

## 8. Media / divers

`onPreMediaPlayerDragged`, `onDependencyViewerOpen`, `onGetLastPathOptions`,
`onSaveExtendedOpen`, `trayIconClicked`, `openTrayContextMenu`, `getStateMenu`.

## 9. Callbacks émis par les plugins (inter-plugins)

| Callback | Émetteur |
|---|---|
| `onMayaMenuCreated` (`[mayaPlugin, prism_menu]`) | plugin **Maya** — ajoute des entrées au menu Prism de Maya. |
| `maya_getCameraNodes` | plugin **Maya** |
| `maya_export_abc` | plugin **Maya** |
| `preIntegrationAdded` (`[plugin, integrationFiles]`) | intégrations |
| `photoshop_onImageExported` | plugin **Photoshop** |
| `openPBAssetTaskContextMenu` (réémis) | plugin **EsmaUSD** s'y abonne |
| `pipeEsma_onVariantCreated` | **toi** (point d'extension custom — à émettre depuis ton code) |

---

### Comment vérifier une signature exacte

Cherche l'émetteur dans le code de Prism :
```
grep -rn 'name="leCallback"' "C:\Program Files\Prism2\Scripts"
```
Le tableau `args=[...]` à côté du `core.callback(...)` te donne l'ordre des arguments.
Exemple confirmé (`SceneBrowser.py:932`) :
```python
self.core.callback(name=callbackName, args=[self, rcmenu, widget.indexAt(pos)])
# → [sceneBrowser, QMenu, QModelIndex]
```
