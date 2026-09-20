# Documentation — Plugin Prism « Maya » & Développement de plugins pour PipeEsma

> Rédigé à partir de l'analyse du code source du plugin installé dans
> `C:\ProgramData\Prism2\plugins\Maya` (Prism v2, plugin Maya **v2.0.17**),
> du template officiel `PluginEmpty` et de ton plugin custom existant `EsmaUSD`.

---

## Table des matières

1. [Qu'est-ce que Prism et comment s'articulent les plugins](#1)
2. [Les types de plugins Prism](#2)
3. [Anatomie du plugin Maya — arborescence des fichiers](#3)
4. [Le pattern d'assemblage (mixins) — `*_init.py`](#4)
5. [Les Variables du plugin (`*_Variables.py`)](#5)
6. [L'intégration côté Maya : comment Prism s'injecte dans Maya](#6)
7. [La séquence de démarrage complète (boot sequence)](#7)
8. [Le système de callbacks (le cœur de l'extensibilité)](#8)
9. [L'API « App plugin » : toutes les fonctions que Prism appelle](#9)
10. [Concepts Maya spécifiques utilisés par Prism](#10)
11. [Le State Manager : Export / Import / Playblast / Render en détail](#11)
12. [Variables d'environnement reconnues par le plugin](#12)
13. [Développer des plugins Prism pour PipeEsma — guide pratique](#13)
14. [Recettes / snippets prêts à l'emploi](#14)
15. [Débogage & pièges courants](#15)

---

<a name="1"></a>
## 1. Qu'est-ce que Prism et comment s'articulent les plugins

**Prism Pipeline** est un gestionnaire de pipeline pour la production d'animation/VFX. Son rôle :
gérer le versioning des scènes, les *products* (exports publiés), la *media* (rendus/playblasts),
les entités (assets / shots / séquences), et l'intégration dans les logiciels (DCC).

### Architecture en couches

```
┌─────────────────────────────────────────────────────────────┐
│  PrismCore  (C:\Program Files\Prism2\Scripts\PrismCore.py)    │
│  = l'objet central « pcore ». Gère projet, entités, products,│
│    media, UI (Project Browser, State Manager), callbacks...  │
└───────────────┬─────────────────────────────────────────────┘
                │ charge dynamiquement
        ┌───────┴────────┬──────────────┬───────────────┐
        ▼                ▼              ▼               ▼
   App plugins      Custom plugins  Project Mgmt    Renderfarm
   (Maya, Houdini,  (EsmaUSD,       (FTrack,        (Deadline…)
    Photoshop…)      USD, Hub…)      ProjectMgmt…)
```

- **`pcore`** (instance de `PrismCore`) est l'objet global. Dans Maya il est accessible
  via la variable Python globale `pcore` (créée par `userSetup.py`).
- Chaque plugin est une **classe Python** que Prism instancie en lui passant `core`
  (= `pcore`). Le plugin se branche ensuite sur Prism via des **callbacks**.
- `pcore.appPlugin` = le plugin de l'application courante (ici le plugin Maya quand on est
  dans Maya). `pcore.getPlugin("NomDuPlugin")` permet de récupérer n'importe quel plugin chargé.

### Le DCC actif vs. le mode standalone

Le même code de plugin sert dans deux contextes :
- **Dans Maya** : `pcore` tourne *à l'intérieur* du process Maya, le plugin a accès à
  `maya.cmds`. C'est `Prism_Maya_Functions` qui est chargé.
- **En standalone** (Project Browser lancé seul, ou installeur de Prism) : Maya n'est pas là.
  Seules les classes « légères » sont chargées (`Prism_Maya_init_unloaded`), qui n'importent
  jamais `maya.cmds`. Cela permet par exemple à l'installeur d'afficher « Maya » dans la liste
  des intégrations à installer, sans avoir Maya ouvert.

---

<a name="2"></a>
## 2. Les types de plugins Prism

Le champ `self.pluginType` (dans `*_Variables.py`) détermine la catégorie :

| `pluginType` | Rôle | Exemples |
|---|---|---|
| `App`        | Intégration d'un DCC (Maya, Houdini, Nuke, Photoshop…). Implémente l'API scène/export/import/render. | **Maya**, Houdini, USD |
| `Custom`     | Plugin libre qui ajoute des fonctionnalités via callbacks, sans être lié à un DCC. | **EsmaUSD** (le tien), Hub |
| `ProjectManagement` | Connexion à un tracker (ShotGrid, Ftrack, Kitsu…). | FTrack |
| `RenderfarmManager`  | Soumission de jobs ferme de rendu. | Deadline |

Champs possibles de `pluginType` côté code Prism : `App`, `Custom`, `ProjectManagement`,
`RenderfarmManager`. Le plugin Maya est un **`App`** ; ton `EsmaUSD` est un **`Custom`**.

### Emplacement des plugins

Prism scanne plusieurs dossiers de plugins :
- **Plugins fournis** : `C:\Program Files\Prism2\Plugins\{Apps,Custom,Standalone}\…`
- **Plugins utilisateur / studio** : `C:\ProgramData\Prism2\plugins\…` ← *c'est ici que vit
  le plugin Maya et ton dossier `Custom\EsmaUSD`*.
- Des chemins additionnels peuvent être ajoutés dans les réglages utilisateur/projet.

Un dossier est reconnu comme plugin s'il contient `Scripts\Prism_<Nom>_init.py` exposant une
classe `Prism_<Nom>` (ou `Prism_Plugin_<Nom>`).

---

<a name="3"></a>
## 3. Anatomie du plugin Maya — arborescence des fichiers

```
C:\ProgramData\Prism2\plugins\Maya\
│
├── Scripts\                         ← le code Python du plugin (chargé par Prism)
│   ├── Prism_Maya_init.py           ← assemble la classe complète (Maya ouvert)
│   ├── Prism_Maya_init_unloaded.py  ← version « légère » (standalone, sans maya.cmds)
│   ├── Prism_Maya_Variables.py      ← métadonnées (version, formats, couleurs, passes...)
│   ├── Prism_Maya_Functions.py      ← LE gros fichier : toute l'API DCC (4111 lignes)
│   ├── Prism_Maya_externalAccess_Functions.py  ← fonctions dispo même sans Maya
│   └── Prism_Maya_Integration.py    ← installer/désinstaller l'intégration dans Maya
│
├── Integration\                     ← fichiers COPIÉS dans les prefs Maya à l'installation
│   ├── Prism.mod                    ← module Maya (déclare PRISM_ROOT, shelves…)
│   ├── scripts\
│   │   ├── PrismInit.py             ← bootstrap : crée `pcore` dans Maya
│   │   └── userSetup.py             ← exécuté au lancement de Maya → appelle PrismInit
│   ├── shelves\
│   │   └── shelf_Prism.mel          ← la shelf « Prism » (boutons Save/Browser/Export…)
│   └── icons\                       ← icônes PNG des boutons de shelf
│
├── Presets\
│   └── EmptyScene Maya.ma           ← scène vierge proposée à la création d'un scenefile
│
└── Resources\
    └── maya.png                     ← icône du plugin (UI Prism)
```

### Rôle de chaque fichier Python

| Fichier | Chargé quand | Contenu |
|---|---|---|
| `Prism_Maya_Variables.py` | Toujours | Constantes : `version`, `pluginName`, `sceneFormats`, `outputFormats`, `renderPasses`, `appColor`… |
| `Prism_Maya_Integration.py` | Toujours | `addIntegration` / `removeIntegration`, détection du chemin Maya via le registre, UI de l'installeur. |
| `Prism_Maya_externalAccess_Functions.py` | Toujours | Réglages utilisateur/projet, presets de scène, copie de fichiers `.xgen/.abc` annexes. Ne dépend PAS de `maya.cmds`. |
| `Prism_Maya_Functions.py` | **Seulement dans Maya** | Toute l'implémentation qui appelle `maya.cmds` / `maya.mel` : sauvegarde, ouverture, export, import, playblast, render… |

C'est pour ça qu'il existe **deux** fichiers `init` : `init_unloaded` exclut volontairement
`Prism_Maya_Functions` (qui ferait un `import maya.cmds` → crash hors de Maya).

---

<a name="4"></a>
## 4. Le pattern d'assemblage (mixins) — `*_init.py`

Prism construit le plugin par **héritage multiple** (mixins). Chaque aspect est une classe
séparée, et `init.py` les combine :

```python
# Prism_Maya_init.py
from Prism_Maya_Variables import Prism_Maya_Variables
from Prism_Maya_externalAccess_Functions import Prism_Maya_externalAccess_Functions
from Prism_Maya_Functions import Prism_Maya_Functions
from Prism_Maya_Integration import Prism_Maya_Integration

class Prism_Plugin_Maya(
    Prism_Maya_Variables,
    Prism_Maya_externalAccess_Functions,
    Prism_Maya_Functions,
    Prism_Maya_Integration,
):
    def __init__(self, core):
        Prism_Maya_Variables.__init__(self, core, self)
        Prism_Maya_externalAccess_Functions.__init__(self, core, self)
        Prism_Maya_Functions.__init__(self, core, self)
        Prism_Maya_Integration.__init__(self, core, self)
```

Points importants :
- Toutes les méthodes de toutes les classes se retrouvent **sur un seul objet** `self`.
  `Prism_Maya_Functions` peut donc appeler `self.getMayaProject()` (défini dans `Integration`)
  ou lire `self.sceneFormats` (défini dans `Variables`).
- Chaque sous-classe reçoit `core` (= `pcore`) et `plugin` (= `self`, l'objet plugin complet),
  et les stocke : `self.core = core`, `self.plugin = plugin`.
- `init_unloaded.py` fait la même chose **sans** `Prism_Maya_Functions` → c'est la version
  standalone.

C'est exactement le pattern que tu réutilises dans `EsmaUSD` (mais en plus simple : 2 classes
seulement, `Variables` + `Functions`).

---

<a name="5"></a>
## 5. Les Variables du plugin (`*_Variables.py`)

Ce sont les métadonnées que Prism lit pour savoir comment traiter le plugin. Extrait commenté
du plugin Maya :

```python
self.version       = "v2.0.17"          # version du plugin (affichée dans Prism)
self.pluginName    = "Maya"             # nom unique → getPlugin("Maya")
self.pluginType    = "App"              # catégorie (cf. section 2)
self.appShortName  = "Maya"
self.appType       = "3d"               # 3d / 2d / … influence l'UI
self.hasQtParent   = True               # l'app a une fenêtre Qt parente (pour parenter les dialogs)
self.sceneFormats  = [".ma", ".mb"]     # extensions de scenefiles reconnues
self.appSpecificFormats = self.sceneFormats
self.outputFormats = [".abc", ".obj", ".fbx", ".ma", ".mb", "ShotCam"]  # formats d'export
self.appColor      = [44, 121, 207]     # couleur d'accent dans l'UI
self.platforms     = ["Windows", "Linux", "Darwin"]
self.appIcon       = os.path.join(self.pluginDirectory, "Resources", "maya.png")
```

Deux structures notables, propres au DCC 3D :

- **`renderPasses`** : mappe les noms de passes « jolis » de Prism vers les noms internes du
  moteur de rendu (V-Ray = dict, Arnold = liste, Redshift = liste). Sert au State Manager pour
  proposer/ajouter des AOVs.
- **`playblastSettings`** : réglages par défaut de capture viewport (format image, filmFit,
  overscan…).

> **Pour PipeEsma** : c'est le fichier minimal obligatoire. Un plugin Custom n'a besoin que de
> `version`, `pluginName`, `pluginType`, `platforms`, `pluginDirectory` (cf. ton `EsmaUSD`).

---

<a name="6"></a>
## 6. L'intégration côté Maya : comment Prism s'injecte dans Maya

Prism n'est **pas** un plugin Maya `.mll` natif. Il s'injecte via le mécanisme standard des
**modules Maya** + le **`userSetup.py`**. L'installation (déclenchée depuis *Prism Settings →
DCC integrations*, code dans `Prism_Maya_Integration.addIntegration`) copie des fichiers dans
les préférences Maya de l'utilisateur (`Documents\maya\<version>\`).

### 6.1 `Prism.mod` — le module Maya

Copié dans `…\maya\<version>\modules\Prism.mod`. Contenu (après substitution des placeholders) :

```
+ Prism 1.0.0 <PLUGINROOT>/Integration
PRISM_ROOT=<PRISMROOT>
MAYA_SHELF_PATH+:=shelves
```

- `+ Prism 1.0.0 <chemin>` déclare un module Maya pointant vers le dossier `Integration` du
  plugin. Maya ajoute automatiquement ses sous-dossiers `scripts`, `icons`, etc. aux chemins
  de recherche.
- `PRISM_ROOT=…` définit la variable d'environnement que `PrismInit.py` lira pour trouver le
  cœur de Prism.
- `MAYA_SHELF_PATH+:=shelves` ajoute le dossier `Integration/shelves` aux shelves chargées →
  la shelf « Prism » apparaît.

À l'installation, `addIntegration` lit `Prism.mod`, remplace les chaînes littérales
`PRISMROOT` et `PLUGINROOT` par les vrais chemins, puis écrit le fichier dans `modules\`.

### 6.2 `userSetup.py` — exécuté à chaque lancement de Maya

Maya exécute automatiquement tout `userSetup.py` trouvé dans ses `scripts`. Prism y injecte un
bloc délimité par `# >>>PrismStart` / `# <<<PrismEnd` (pour pouvoir le retirer proprement) :

```python
# >>>PrismStart
import sys
from maya import OpenMaya as omya
if omya.MGlobal.mayaState() != omya.MGlobal.kBatch:   # pas en mode batch/headless
    if "pcore" in locals() and pcore:                 # déjà chargé → warn double-load
        ... QMessageBox "Prism is loaded multiple times" ...
    elif sys.version[0] == "2":                        # Maya Python 2 non supporté
        ... warn ...
    else:
        try:
            import PrismInit
            pcore = PrismInit.prismInit()              # ← création de pcore
        except:
            print("Error occured while loading Prism: …")
# <<<PrismEnd
```

> Note : la désinstallation (`removeIntegration`) appelle
> `self.core.integration.removeIntegrationData(filepath=userSetup)` pour retirer uniquement ce
> bloc, sans casser le reste du `userSetup.py` de l'utilisateur.

### 6.3 `PrismInit.py` — le bootstrap

Construit l'objet `pcore` :

```python
def prismInit(prismArgs=[]):
    prismRoot = os.getenv("PRISM_ROOT")          # défini par Prism.mod
    if not prismRoot: raise Exception(...)

    import maya.cmds as cmds
    if cmds.about(batch=True):                   # Maya headless (mayapy/batch)
        # il faut une QApplication pour l'UI Prism, sinon on passe en "noUI"
        ... crée QApplication si besoin ...
        prismArgs.append("noUI")

    scriptDir = os.path.join(prismRoot, "Scripts")
    if scriptDir not in sys.path: sys.path.append(scriptDir)

    import PrismCore
    global pcore
    pcore = PrismCore.PrismCore(app="Maya", prismArgs=prismArgs)
    return pcore
```

Le paramètre `app="Maya"` indique à `PrismCore` de charger **le plugin dont `pluginName ==
"Maya"`** comme `appPlugin`, et donc d'utiliser `Prism_Maya_Functions`.

### 6.4 `shelf_Prism.mel` — la barre d'outils

Définit la shelf Maya avec les boutons : **Save / Save+comment**, **Project Browser**,
**Import**, **Export**, **USD Import**, **USD Export**, **Playblast**, **Render**, **State
Manager**, **Settings**.

Chaque bouton exécute du Python. Deux familles de commandes :
- Direct sur le core : `pcore.saveScene()`, `pcore.projectBrowser()`, `pcore.stateManager()`,
  `pcore.prismSettings()`.
- Délégué au plugin : `pcore.getPlugin("Maya").onShelfClickedExport()`,
  `…onShelfClickedImport()`, `…onShelfClickedPlayblast()`, `…onShelfClickedRender()`.
- Les boutons USD appellent un **autre** plugin :
  `pcore.getPlugin("USD").maya_onUsdInClicked(...)`. → illustration parfaite de la
  **collaboration entre plugins** : le plugin USD ajoute des comportements Maya sans modifier
  le plugin Maya.

Chaque commande est enveloppée dans un `try/except` qui, en cas d'échec, ouvre une boîte de
diagnostic (« Failed to load Prism », bouton *Details* qui re-tente `PrismInit.prismInit()` et
explique le problème). C'est pourquoi le MEL paraît énorme : 90 % est de la gestion d'erreur.

### 6.5 Détection du chemin Maya (registre Windows)

`getMayaPath()` lit `HKLM\SOFTWARE\Autodesk\Maya\<version>\Setup\InstallPath\
MAYA_INSTALL_LOCATION` pour trouver `maya.exe`. `examplePath` pointe vers
`Documents\maya\<version>` (le dossier de prefs où installer l'intégration). L'installeur
propose les versions 2022→2026.

---

<a name="7"></a>
## 7. La séquence de démarrage complète (boot sequence)

```
1. L'utilisateur lance Maya
        │
2. Maya lit Prism.mod  →  définit PRISM_ROOT, ajoute Integration/scripts au path,
                          charge la shelf Prism
        │
3. Maya exécute userSetup.py  →  bloc PrismStart
        │
4. userSetup.py importe PrismInit, appelle prismInit()
        │
5. PrismInit ajoute <PRISM_ROOT>\Scripts au sys.path, instancie PrismCore(app="Maya")
        │
6. PrismCore charge les plugins. Pour Maya il instancie Prism_Plugin_Maya :
        → __init__ de chaque mixin s'exécute
        → Prism_Maya_Functions.__init__ enregistre ses callbacks :
              onProjectBrowserStartup, onStateManagerOpen, onProjectChanged,
              prePlayblast, updatedEnvironmentVars
        → externalAccess enregistre : userSettings_save/load, getPresetScenes,
              preProjectSettingsLoad/Save, projectSettings_loadUI
        │
7. PrismCore appelle plugin.startup(origin)  (origin = pcore)
        → trouve la fenêtre "MayaWindow" (parent Qt des dialogs)
        → addMenu()  : crée le menu "Prism" dans la barre de menus Maya
        → startAutosaveTimer()
        → loadPlugin AbcExport / AbcImport / fbxmaya
        → enregistre un callback Maya natif kAfterOpen → origin.sceneOpen
        │
8. Prism est prêt. pcore est la variable globale, le menu + la shelf sont actifs.
```

`startup()` est *poll* : tant que la `MayaWindow` ou la shelf top-level n'existent pas encore,
il renvoie `False` et le `origin.timer` re-tente. Une fois l'UI Maya prête, `origin.timer.stop()`
et l'initialisation se termine.

---

<a name="8"></a>
## 8. Le système de callbacks (le cœur de l'extensibilité)

C'est **le** mécanisme à comprendre pour développer pour PipeEsma. Prism émet des
**événements** à des moments clés ; un plugin s'y abonne pour réagir.

### S'abonner

```python
self.core.registerCallback(
    "onStateManagerOpen",        # nom de l'événement
    self.onStateManagerOpen,     # ta fonction
    plugin=self.plugin,          # pour pouvoir la désenregistrer avec le plugin
)
```

> Variante équivalente vue dans `EsmaUSD` : `self.core.callbacks.registerCallback(...)`.
> `self.core.registerCallback` est un raccourci vers ce même gestionnaire.

### Émettre (déclencher) un callback — utile si TU crées un point d'extension

```python
self.core.callback(name="onMayaMenuCreated", args=[self, prism_menu])
```

Tous les plugins abonnés à `"onMayaMenuCreated"` seront appelés avec ces args.

### Callbacks utilisés par le plugin Maya (exemples concrets)

| Callback | Quand | Ce que fait Maya |
|---|---|---|
| `onProjectBrowserStartup` | ouverture du Project Browser | ajuste le style du media player |
| `onStateManagerOpen` | ouverture du State Manager | crée les boutons custom (Export/Import…) |
| `onProjectChanged` | changement de projet | (ré)applique Maya project + plugin paths |
| `prePlayblast` | avant un playblast | force la résolution / le gate |
| `updatedEnvironmentVars` | variables d'env modifiées | rafraîchit l'OCIO |
| `getPresetScenes` | nouvelle scène | ajoute `Presets\EmptyScene Maya.ma` |
| `userSettings_loadUI` / `_saveSettings` | Prism Settings | onglet Maya (type de save, Maya project…) |
| `projectSettings_loadUI` | Project Settings | champ « Selection Set Prefix » |

### Callbacks émis (points d'extension offerts par Maya à d'autres plugins)

- `preIntegrationAdded` (args `[plugin, integrationFiles]`)
- `onMayaMenuCreated` (args `[plugin, prism_menu]`)
- `maya_getCameraNodes` (args : liste de caméras)

> **Ton plugin `EsmaUSD`** utilise exactement ce système : il s'abonne à
> `openPBAssetTaskContextMenu` pour ajouter l'action « Create Variant » au clic droit sur une
> task d'asset dans le Project Browser. C'est le modèle à suivre pour étendre Prism **sans
> toucher** au code des plugins fournis.

### Où trouver la liste des callbacks disponibles ?

Cherche les appels `self.core.callback(name=...)` et `core.callback(name=...)` dans le code de
Prism (`C:\Program Files\Prism2\Scripts\`) et des plugins. Chaque `name=` est un point
d'extension auquel tu peux t'abonner. Quelques familles fréquentes :
`onProjectBrowserStartup`, `onStateManagerOpen`, `openPBAssetContextMenu`,
`openPBAssetTaskContextMenu`, `openPBShotContextMenu`, `postSaveScene`, `preExport`,
`postExport`, `preImport`, `postImport`, `sceneOpen`, `onProjectChanged`,
`userSettings_loadUI`, `projectSettings_loadUI`, `preProjectSettingsSave`…

---

<a name="9"></a>
## 9. L'API « App plugin » : toutes les fonctions que Prism appelle

Un plugin de type `App` doit implémenter un **contrat** : un ensemble de méthodes que le cœur
de Prism appelle par leur nom. Le template `PluginEmpty` (Apps) liste ce contrat avec des
implémentations vides — c'est la **référence canonique** de ce qu'un DCC doit fournir. Le
plugin Maya remplit chacune avec du `maya.cmds`.

### 9.1 Gestion des scènes

| Méthode | Rôle | Implémentation Maya (résumé) |
|---|---|---|
| `startup(origin)` | init à l'ouverture du DCC | trouve MayaWindow, menu, charge plugins Abc/fbx |
| `sceneOpen(origin)` | après ouverture d'une scène | redémarre l'autosave timer |
| `getCurrentFileName(origin, path=True)` | chemin de la scène courante | `cmds.file(q=True, sceneName=True)` |
| `getSceneExtension(origin)` | extension par défaut | `.ma` |
| `saveScene(origin, filepath, details, allowChangedExtension)` | sauvegarde | `cmds.file(rename=…); cmds.file(save=True, type=…)` ; choisit ma/mb selon réglage utilisateur |
| `openScene(origin, filepath, force)` | ouverture | gère « save changes? », `cmds.file(o=True, force=True)` |
| `getCurrentSceneFiles(origin)` | fichiers annexes de la scène | scène + `.xgen`/`.abc` |
| `getImportPaths(origin)` | imports trackés | lit `cmds.fileInfo("PrismImports")` |

### 9.2 Timeline / résolution / version

| Méthode | Maya |
|---|---|
| `getFrameRange(origin)` | `playbackOptions minTime/maxTime` |
| `setFrameRange(origin, start, end)` | `playbackOptions(...)` + `currentTime` |
| `getCurrentFrame()` | `cmds.currentTime(q=True)` |
| `getFPS(origin)` / `setFPS(origin, fps)` | via `mel currentUnit -time` |
| `getResolution()` / `setResolution(w, h)` | `defaultResolution.width/height` + aspect ratio |
| `getAppVersion(origin)` | `cmds.about(apiVersion=True)` |

### 9.3 Nodes / sélection (pour Export & Import)

`getSelectedNodes()`, `selectNodes(origin)`, `getNodeName(origin, node)`,
`isNodeValid(origin, handle)`, `deleteNodes(origin, handles)`,
`getCamNodes()/getCamName()/selectCam()`.

Particularité : `isNodeValid` gère aussi les **prims USD** (handles contenant une virgule →
résolus via `mayaUsd.ufe.ufePathToPrim`).

### 9.4 Hooks de shelf (entrées rapides)

`onShelfClickedImport`, `onShelfClickedExport`, `onShelfClickedPlayblast`,
`onShelfClickedRender`, `onShelfClickedImportConnectedAssets`. Ces méthodes créent un *state*
dans le State Manager et l'exécutent (en mode « doubleclick » = exécution instantanée).

> **À retenir** : pour ajouter une fonctionnalité « App », tu implémentes une méthode du
> contrat ci-dessus (si elle existe) **ou** tu t'abonnes à un callback (si c'est un
> comportement additionnel). Tu n'as jamais à modifier le cœur de Prism.

---

<a name="10"></a>
## 10. Concepts Maya spécifiques utilisés par Prism

Comprendre ces concepts est indispensable pour dev/maintenir le plugin :

- **Selection Sets comme « tâches d'export »**
  Chaque *Export state* du State Manager est matérialisé dans la scène par un **`set` Maya**
  (`cmds.sets`). Les objets à exporter sont membres du set (`cmds.sets(node, include=setName)`).
  Le nom du set = préfixe projet (`getSetPrefix()`, réglable dans Project Settings) + nom de
  tâche. Avantage : la sélection survit aux save/reload de la scène.

- **`fileInfo` pour persister des métadonnées Prism dans la scène**
  Ex. `cmds.fileInfo("PrismImports")` stocke la liste des imports. C'est le « scratch space »
  de Prism dans le `.ma`/`.mb`.

- **Maya Project / Workspace**
  `setMayaProject(path)` crée/ouvre un `workspace.mel` pointant sur le projet Prism (option
  réglable). Un template peut être fourni via `PRISM_MAYA_WORKSPACE_TEMPLATE`.

- **References / namespaces / GPU cache (à l'import)**
  `sm_import_importToApp` propose plusieurs modes : *Create Reference*, *Import Objects Only*,
  *Apply As Cache*, *Load As GPU Cache*. Les namespaces sont générés depuis un template
  (`defaultMayaNamespace`, ex. `"{entity}_{task}"`). Les références permettent l'update
  non-destructif (remplacer le fichier référencé).

- **Formats d'export** (`sm_export_exportAppObjects`)
  `.abc` (Alembic via `AbcExport`), `.fbx` (plugin fbxmaya + `FBXExport` MEL),
  `.obj`, `.ma`/`.mb` (avec options *import references*, *delete unknown nodes*), et
  **ShotCam** (export de caméra de shot).

- **AOVs / Render passes**
  `sm_render_*` interroge le moteur courant (`getCurrentRenderer`), liste/ajoute/supprime des
  passes via le mapping `renderPasses` (V-Ray / Arnold / Redshift). `sm_render_preSubmit`
  configure les *render settings* avant un rendu local ou une soumission Deadline.

- **Playblast**
  `sm_playblast_createPlayblast` capture le viewport (gère la parité de résolution, le gate,
  le thumbnail). `prePlayblast` ajuste la résolution avant capture.

- **Mode batch / headless**
  Quasi toutes les fonctions UI testent `cmds.about(batch=True)` pour ne pas créer de menu/UI
  en rendu de ferme.

---

<a name="11"></a>
## 11. Le State Manager : Export / Import / Playblast / Render en détail

Le **State Manager** (`pcore.stateManager()`) est la fenêtre où l'utilisateur empile des
« states » (tâches) à publier. Chaque type de state appelle des méthodes `sm_<type>_*` du
plugin. Le cycle de vie d'un Export state, par exemple :

```
sm_export_startup(origin)        → prépare l'UI du state (boutons FBX settings, etc.)
sm_export_addObjects(origin)     → crée le selection set, y ajoute la sélection courante
sm_export_updateObjects(origin)  → resynchronise la liste affichée avec le set
sm_export_setTaskText(...)       → renomme la tâche (et le set)
sm_export_preExecute(...)        → validations avant publish (renvoie warnings)
sm_export_exportShotcam(...)     ┐
sm_export_exportAppObjects(...)  ┘ → l'export réel (abc/fbx/obj/ma/mb/ShotCam)
sm_export_getStateProps / loadData → sauvegarde/relecture des réglages du state dans la scène
```

Symétriquement il existe :
- `sm_import_*` : `sm_import_importToApp` (le gros morceau : reference/import/cache/gpu),
  `sm_import_updateObjects`, `sm_import_removeNameSpaces`, `connectRefNode`.
- `sm_playblast_*` : `sm_playblast_preExecute`, `_createPlayblast`, `_postExecute`.
- `sm_render_*` : `sm_render_preSubmit`, `_startLocalRender`, `_undoRenderSettings`,
  `_getDeadlineParams`, `_getRenderPasses`, `_addRenderPass`, `removeAOV`.
- `sm_saveStates` / `sm_readStates` / `sm_deleteStates` : persistance de **tous** les states
  dans la scène (via `fileInfo`).

Les classes en fin de `Prism_Maya_Functions.py` (`…SubmitDeadline`, etc. avec `setupUi`,
`submit`) sont de petits **dialogs Qt** pour la soumission ferme de rendu.

---

<a name="12"></a>
## 12. Variables d'environnement reconnues par le plugin

| Variable | Effet |
|---|---|
| `PRISM_ROOT` | racine de Prism (définie par `Prism.mod`) — requise. |
| `PRISM_MAYA_WORKSPACE_TEMPLATE` | chemin d'un `workspace.mel` template copié quand Prism crée le Maya project. |
| `PRISM_MAYA_FBX_DELETE_OOR_KEYFRAMES` | `0`=non, `1`=oui, `2`=demander : suppression des keyframes hors range à l'export FBX. |
| `defaultMayaNamespace` (config projet, pas env) | template de namespace à l'import, ex. `{entity}_{task}`. |
| `MAYA_MODULE_PATH`, `MAYA_PLUG_IN_PATH`, `MAYA_SCRIPT_PATH`, `MAYA_PRESET_PATH`, `MAYA_SHELF_PATH`, `XBMLANGPATH` | enrichis par `addProjectPaths()` quand l'option « Add project to Maya plugin search paths » est activée (pointe vers `<pipeline>/CustomModules/Maya/{plug-ins,scripts,presets,shelves,icons}`). |
| `PRISM_USD_SITE_PACKAGES`, `PRISM_USD_DLL_DIR` | (ton `EsmaUSD`) localisation d'un build USD `pxr` quand on tourne dans le Python standalone de Prism. |

> Le « bouton » *Add current project to Maya module path* (UI réglages utilisateur) appelle
> `appendEnvFile("MAYA_MODULE_PATH")` qui écrit dans le `Prism.env` du projet pour que le DCC
> charge automatiquement le module Maya du studio.

---

<a name="13"></a>
## 13. Développer des plugins Prism pour PipeEsma — guide pratique

Tu as déjà un plugin **Custom** fonctionnel (`EsmaUSD`). Voici la méthode générale.

### 13.1 Choisir le type de plugin

- **Custom** (recommandé pour la plupart de tes besoins PipeEsma) : ajoute des
  fonctionnalités à Prism (menus, actions clic-droit, validations, outils USD…) **via
  callbacks**. C'est ce que fait `EsmaUSD`. Pas d'intégration DCC à gérer.
- **App** : seulement si tu intègres un *nouveau* logiciel non supporté. Lourd (il faut
  implémenter tout le contrat de la section 9 + l'intégration de la section 6).

### 13.2 Structure minimale d'un plugin Custom

```
C:\ProgramData\Prism2\plugins\Custom\MonPlugin\
└── Scripts\
    ├── Prism_MonPlugin_init.py
    ├── Prism_MonPlugin_Variables.py
    └── Prism_MonPlugin_Functions.py
```

`Prism_MonPlugin_Variables.py` :
```python
import os
class Prism_MonPlugin_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.0.0"
        self.pluginName = "MonPlugin"
        self.pluginType = "Custom"
        self.platforms = ["Windows"]
        self.pluginDirectory = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
```

`Prism_MonPlugin_init.py` :
```python
from Prism_MonPlugin_Variables import Prism_MonPlugin_Variables
from Prism_MonPlugin_Functions import Prism_MonPlugin_Functions

class Prism_MonPlugin(Prism_MonPlugin_Variables, Prism_MonPlugin_Functions):
    def __init__(self, core):
        Prism_MonPlugin_Variables.__init__(self, core, self)
        Prism_MonPlugin_Functions.__init__(self, core, self)
```

`Prism_MonPlugin_Functions.py` :
```python
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from PrismUtils.Decorators import err_catcher_plugin as err_catcher

class Prism_MonPlugin_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        # branche-toi sur un point d'extension :
        self.core.callbacks.registerCallback(
            "openPBAssetTaskContextMenu", self.onAssetTaskContextMenu, plugin=self
        )

    @err_catcher(name=__name__)
    def isActive(self):          # obligatoire pour un Custom : True = plugin chargé
        return True

    @err_catcher(name=__name__)
    def onAssetTaskContextMenu(self, *args, **kwargs):
        sceneBrowser, menu = args[0], args[1]
        act = menu.addAction("Mon action")
        act.triggered.connect(lambda: self.core.popup("Hello PipeEsma"))
```

### 13.3 Le décorateur `err_catcher`

**Toujours** décorer tes méthodes publiques :
- App plugin / méthodes appelées par le core : `from PrismUtils.Decorators import err_catcher`
- Plugin Custom : `err_catcher_plugin as err_catcher`

Il attrape les exceptions, les loggue proprement et évite que ton plugin fasse planter Prism ou
le DCC. Le `name=__name__` sert au logging.

### 13.4 L'objet `core` (pcore) — ce que tu utiliseras le plus

| Appel | Usage |
|---|---|
| `self.core.popup(msg, title=…, severity="info"/"warning"/"error")` | message à l'utilisateur |
| `self.core.popupQuestion(msg, buttons=[…])` | question (retourne le label cliqué) |
| `self.core.getCurrentFileName()` | scène courante |
| `self.core.getScenefileData(path)` | métadonnées (entity, type, task, version…) |
| `self.core.getStateManager()` / `self.core.stateManager()` | State Manager |
| `self.core.projectBrowser()` | ouvrir le Project Browser |
| `self.core.entities.*` | entités (assets/shots, connexions…) |
| `self.core.products.*` | products publiés (`generateProductPath`, `getProductsByTags`…) |
| `self.core.paths.getCachePathData(path)` | parser un chemin de product |
| `self.core.products.generateProductPath(entity, task, extension, version, location)` | construire un chemin de product (cf. ton `createVariant`) |
| `self.core.getConfig(area, key, config=…, dft=…)` / `setConfig(...)` | lire/écrire la config |
| `self.core.getPlugin("USD")` | accéder à un autre plugin |
| `self.core.callback(name=…, args=[…])` | émettre ton propre événement |
| `self.core.messageParent` | widget parent pour tes dialogs Qt |

### 13.5 Bonnes pratiques (tirées du code Maya + EsmaUSD)

1. **Sépare Variables / Functions** (mixins) comme les plugins officiels.
2. **Ne suppose jamais que le DCC est présent.** Si ton plugin Custom peut tourner en
   standalone, fais tes `import maya.cmds` / `from pxr import …` **à l'intérieur** des méthodes
   (pas en haut du module), et gère l'échec — exactement ce que fait `_ensurePxr()` dans
   `EsmaUSD`.
3. **Passe par les callbacks**, pas par la modification des plugins fournis : tes mises à jour
   de Prism ne casseront pas tes ajouts.
4. **Utilise `getConfig`/`setConfig`** pour la persistance (config projet ou utilisateur)
   plutôt que des fichiers ad hoc.
5. **Parente tes dialogs** avec `self.core.messageParent` (sinon ils se perdent derrière la
   fenêtre du DCC).
6. **Teste `self.core.uiAvailable`** avant de construire de l'UI (mode ferme/headless).
7. **Versionne `self.version`** : Prism l'affiche et peut s'en servir pour la compat.

---

<a name="14"></a>
## 14. Recettes / snippets prêts à l'emploi

**Ajouter une entrée au menu Prism dans Maya** (depuis un plugin Custom, sans toucher au plugin
Maya) :
```python
def __init__(self, core, plugin):
    self.core = core; self.plugin = plugin
    self.core.callbacks.registerCallback("onMayaMenuCreated", self.addMenuItem, plugin=self)

@err_catcher(name=__name__)
def addMenuItem(self, mayaPlugin, prism_menu):
    import maya.cmds as cmds
    cmds.menuItem(label="PipeEsma — Mon outil", parent=prism_menu,
                  command=lambda x: self.monOutil())
```

**Action clic-droit sur un shot** : s'abonner à `openPBShotContextMenu` (mêmes args que
`openPBAssetTaskContextMenu` : `[sceneBrowser, menu, modelIndex]`).

**Récupérer l'entité/department/task sélectionnés dans le Project Browser** (cf. `createVariant`) :
```python
entity     = sceneBrowser.getCurrentEntity()
department = sceneBrowser.getCurrentDepartment()
task       = sceneBrowser.getCurrentTask()
```

**Construire le chemin d'un product master USD** :
```python
master = self.core.products.generateProductPath(
    entity=entity, task="USD", extension=".usda", version="master", location="global")
```

**Émettre un nouveau point d'extension PipeEsma** (pour que d'autres plugins s'y branchent) :
```python
self.core.callback(name="pipeEsma_onVariantCreated", args=[self, entity, variantName])
```

---

<a name="15"></a>
## 15. Débogage & pièges courants

- **Prism ne se charge pas dans Maya** : vérifier la présence du bloc PrismStart dans
  `Documents\maya\<version>\scripts\userSetup.py`, du `Prism.mod` dans `…\modules\`, et que
  `PRISM_ROOT` est défini. Le bouton *Save* de la shelf affiche un diagnostic détaillé si le
  chargement échoue (bouton *Details*).
- **Double chargement** : si `pcore` existe déjà, Maya affiche « Prism is loaded multiple
  times » — nettoyer le `userSetup.py` de tout code Prism dupliqué et ré-ajouter l'intégration
  via *Prism Settings*.
- **`import maya.cmds` échoue** : tu exécutes du code DCC en standalone. Déplace l'import dans
  la méthode et protège-le, ou sépare la logique dans `*_Functions` (chargé seulement dans le
  DCC) vs `*_externalAccess_Functions` (toujours chargé).
- **Python 2** : non supporté. Maya 2022+ (Python 3) requis.
- **Mode batch** : protège toute création d'UI par `if cmds.about(batch=True): return`.
- **Logs** : `logging.getLogger(__name__)`. Le plugin Maya loggue les échecs de chargement de
  shelves/plugins en `warning`/`debug`. Régler le niveau de log via les réglages Prism.
- **`pyc` orphelins** : après modif d'un `.py`, supprimer les `__pycache__` si tu observes du
  code obsolète exécuté.
- **USD hors DCC** (spécifique EsmaUSD) : le Python embarqué de Prism n'a pas `pxr` ; passe par
  `PRISM_USD_SITE_PACKAGES` ou emprunte le build d'Houdini (Py 3.11), comme `_ensurePxr()`.

---

## Annexe — Référence rapide des fichiers du plugin Maya

| Fichier | Lignes | Responsabilité |
|---|---|---|
| `Scripts/Prism_Maya_Functions.py` | 4111 | API DCC complète (scène, export, import, render, playblast). |
| `Scripts/Prism_Maya_Integration.py` | 326 | Installer/désinstaller l'intégration, registre Maya, UI installeur. |
| `Scripts/Prism_Maya_externalAccess_Functions.py` | 246 | Réglages user/projet, presets, fichiers annexes (sans maya.cmds). |
| `Scripts/Prism_Maya_Variables.py` | 118 | Métadonnées + renderPasses + playblastSettings. |
| `Scripts/Prism_Maya_init.py` | 51 | Assemble le plugin complet (DCC). |
| `Scripts/Prism_Maya_init_unloaded.py` | 46 | Assemble la version standalone (sans Functions). |
| `Integration/Prism.mod` | 3 | Module Maya (PRISM_ROOT, shelves). |
| `Integration/scripts/PrismInit.py` | 35 | Bootstrap de `pcore` dans Maya. |
| `Integration/scripts/userSetup.py` | 24 | Lance PrismInit au démarrage de Maya. |
| `Integration/shelves/shelf_Prism.mel` | 376 | Shelf Prism (boutons + diagnostic d'erreur). |

---

*Document généré à partir de l'analyse du code source. Pour aller plus loin, explore
`C:\Program Files\Prism2\Scripts\PrismCore.py` et `PrismUtils\` : tu y trouveras la liste
exhaustive des méthodes de `core` et des `core.callback(name=...)` auxquels t'abonner.*
