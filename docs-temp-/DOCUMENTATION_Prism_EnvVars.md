# Variables d'environnement dans Prism — guide complet (PipeEsma)

> Basé sur le code de Prism v2 (`C:\Program Files\Prism2\Scripts\PrismUtils\Users.py`,
> `Projects.py`, `PrismSettings.py`) et les plugins installés (Maya, Houdini, USD, FTrack…).
>
> Deux choses différentes portent le nom « variables d'environnement » dans Prism :
> 1. **Les variables que TU définis via l'UI de Prism** (User/Project Settings → Environment).
>    Prism les injecte dans `os.environ` → visibles par les DCC et tes scripts.
> 2. **Les variables `PRISM_*` que Prism LIT** pour configurer son propre comportement.
>    Tu les définis soit dans l'OS, soit via le mécanisme du point 1.
>
> Les deux se règlent « via Prism ». Ce document couvre les deux.

---

## Partie A — Définir tes propres variables via l'UI de Prism

### A.1 Les deux portées (scopes)

| Portée | Où la régler | Stockage | Appliquée quand |
|---|---|---|---|
| **Utilisateur** | *Prism Settings → onglet « Environment »* (table Variable / Value) | config **user** (`environmentVariables`) | au démarrage de Prism, pour cet utilisateur, tous projets confondus |
| **Projet** | *Project Settings → Environment* | config **project** (`environmentVariables`) | au chargement du projet, pour tous les utilisateurs du projet |

- **User** = préférences perso / poste local (chemins d'outils, licences perso…).
- **Project** = config partagée du projet, versionnée avec le projet (le studio entier en hérite).
- Les deux finissent dans `os.environ`, donc **lisibles depuis Maya, Houdini, et n'importe
  quel script Python** qui tourne sous Prism.

### A.2 Comment ça marche en interne

À l'ouverture de Prism / au changement de projet :

```python
# Users.refreshEnvironment()  (et Projects.refreshProjectEnvironment())
for envVar in self.getUserEnvironment():
    os.environ[envVar["key"]] = envVar["value"]
self.core.callback(name="updatedEnvironmentVars", args=["refreshUser", envVars])
```

Points clés du code :
- **Expansion** : la valeur passe par `os.path.expandvars(...)` → tu peux référencer d'autres
  variables, ex. `%PRISM_JOB%\outils` ou `$HOME/tools`.
- **Hook `expandEnvVar`** : Prism émet le callback `expandEnvVar` sur chaque valeur ; un plugin
  peut réécrire la valeur (résolution custom de tokens). Utile pour PipeEsma si tu veux des
  jetons maison (ex. `@project@`).
- **Sauvegarde de l'original** : Prism mémorise `os.getenv(key)` avant de l'écraser
  (`"orig"`), pour **restaurer** la valeur d'origine quand on décharge le projet
  (`unloadProjectEnvironment`). Changer de projet ne « pollue » donc pas l'environnement.
- **`updatedEnvironmentVars`** est émis à chaque refresh (`refreshUser`, `refreshProject`,
  `unloadProject`). Le plugin Maya s'y abonne pour rafraîchir l'OCIO.

### A.3 Le cas spécial OCIO (color management)

```python
if key.lower().startswith("ocio") and appPluginName.lower() == key.split("_")[-1]:
    key = "OCIO"
```

Tu peux définir des variables **`OCIO_<app>`** (ex. `OCIO_maya`, `OCIO_houdini`) : Prism ne les
exporte comme `OCIO` que **dans l'application correspondante**. Ça permet d'avoir un config OCIO
différent par DCC. Dans Maya, le plugin appelle `refreshOcio()` quand `OCIO` change.

### A.4 Rendre une variable persistante au niveau Windows

Dans l'onglet Environment, le clic droit propose *Make persistent* :
```python
subprocess.Popen("setx %s %s" % (key, value))   # PrismSettings.makePersistent()
```
→ écrit la variable durablement dans l'environnement **utilisateur Windows** (`setx`), donc
disponible même hors Prism (autres applis, terminaux). À utiliser pour les variables que des
process externes (ferme de rendu lancée hors Prism, scripts CLI) doivent voir.

### A.5 Définir une variable par code (pour PipeEsma)

```python
# Niveau utilisateur
self.core.users.setUserEnvironmentVariable("PIPEESMA_TOOLS", r"D:\PipeEsma\tools")

# Lecture brute (dict) :
self.core.users.getUserEnvironmentVariables()          # {clé: valeur}
self.core.users.getUserEnvironment()                   # [{key, value, orig}, ...] (résolu)

# Niveau projet : via la config projet
self.core.setConfig("environmentVariables", val={"PIPEESMA_SHOWROOT": r"\\srv\esma\show"},
                    config="project")
self.core.projects.refreshProjectEnvironment()
```

---

## Partie B — Variables `PRISM_*` que Prism reconnaît

Tu peux les poser dans l'onglet Environment de Prism (Partie A) **ou** dans l'environnement de
l'OS (avant lancement). Liste extraite du code (cœur + plugins). Les booléens valent
généralement `"1"`/`"0"`.

### B.1 Chemins & démarrage du pipeline

| Variable | Effet |
|---|---|
| `PRISM_ROOT` | Racine de l'install Prism. Définie par l'intégration DCC (`Prism.mod`). |
| `PRISM_JOB` / `PRISM_JOB_LOCAL` | Chemin du projet courant (global / local). |
| `PRISM_PROJECT_CONFIG_PATH` | Emplacement non-standard du fichier de config projet. |
| `PRISM_PROJECT_PIPELINE_FOLDER` | Nom du dossier pipeline (défaut `00_Pipeline`). |
| `PRISM_PROJECT_PRESETS_PATH` / `PRISM_SCENEFILE_PRESET_PATHS` | Chemins de presets de projet / de scenefiles. |
| `PRISM_DATA_DIR` / `PRISM_USER_PREFS` | Dossier de données / prefs utilisateur de Prism. |
| `PRISM_LIBS` / `PRISM_NO_LIBS` | Emplacement des libs Python / désactiver leur chargement. |
| `PRISM_PYTHON_VERSION` | Version de Python à utiliser. |
| `PRISM_FFMPEG` | Chemin d'un binaire ffmpeg custom (transcodage media). |
| `PRISM_FILE_EXPLORER` | Explorateur de fichiers à ouvrir (« Open in explorer »). |

### B.2 Plugins : chargement

| Variable | Effet |
|---|---|
| `PRISM_PLUGIN_PATHS` | Dossiers de plugins additionnels (chemins directs). |
| `PRISM_PLUGIN_SEARCH_PATHS` | Dossiers à scanner récursivement pour trouver des plugins. |
| `PRISM_DEFAULT_PLUGIN_PATH` / `PRISM_FALLBACK_PLUGIN_PATH` | Chemins de plugins par défaut / de secours. |
| `PRISM_LOAD_PLUGINS_FROM_DFT_PATH` | Charger (ou non) les plugins du chemin par défaut. |
| `PRISM_LOAD_PRJ_PLUGINS_RECURSIVE` | Scanner récursivement les plugins du projet. |
| `PRISM_IGNORE_AUTOLOAD_PLUGINS` | Ne pas auto-charger certains plugins. |
| `PRISM_ENABLED` | Active/désactive globalement Prism. |

> **Pour PipeEsma** : `PRISM_PLUGIN_SEARCH_PATHS` est le moyen propre de faire charger ton
> dossier de plugins studio (ex. `\\srv\esma\prism\plugins`) sans les copier sous
> `C:\ProgramData\Prism2\plugins`.

### B.3 Identité utilisateur

| Variable | Effet |
|---|---|
| `PRISM_USERNAME` | Force le nom d'utilisateur Prism. |
| `PRISM_USER_ABBREVIATION` | Force l'abréviation (3 lettres) de l'utilisateur. |

### B.4 Entités, départements, nommage

| Variable | Effet |
|---|---|
| `PRISM_USE_DEPARTMENTS_FOR_PRODUCTS` | Inclure le department dans l'arbo des products. |
| `PRISM_USE_SEQUENCE_FOLDERS` | Utiliser des dossiers de séquence pour les shots. |
| `PRISM_SHOT_INCREMENT` | Pas d'incrément des numéros de shot. |
| `PRISM_EPISODE` | Token d'épisode. |
| `PRISM_SHOTCAM_TASK` / `PRISM_SHOTCAM_DEPARTMENT` | Task / department par défaut pour les ShotCam. |
| `PRISM_PREFER_NODENAME_OVER_TASKNAME` | (DCC) nommer l'export d'après le node plutôt que la task. |

### B.5 Versions / publish / master

| Variable | Effet |
|---|---|
| `PRISM_VERSION_UP_AFTER_PUBLISH` | Incrémente la version après un publish. |
| `PRISM_USE_HARDLINK_MASTER` | Crée les master versions par hardlink (au lieu de copie). |
| `PRISM_PRODUCT_MASTER_LOC` / `PRISM_MEDIA_MASTER_LOC` | Emplacement des master de products / media. |
| `PRISM_DFT_LOCAL_PATH` | Chemin local par défaut (workflow local files). |
| `PRISM_SHOW_INVALID_VERSION_NAMES` | Afficher les versions au nommage invalide. |

### B.6 Media / affichage

| Variable | Effet |
|---|---|
| `PRISM_SHOW_EXR_LAYERS` | Afficher les layers des EXR. |
| `PRISM_DISPLAY_MEDIA_RESOLUTION` | Afficher la résolution des media. |
| `PRISM_USE_NUKE_FOR_PREVIEWS` / `PRISM_NUKE_EXE` / `PRISM_NUKE_INTERACTIVE_LICENSE` | Utiliser Nuke pour les previews + chemin/licence. |
| `PRISM_REFRESH_OIIO_CACHE` | Rafraîchir le cache OpenImageIO. |
| `PRISM_ENTITY_THUMBNAIL_EXT` | Extension des thumbnails d'entité. |

### B.7 Débogage / divers core

| Variable | Effet |
|---|---|
| `PRISM_DEBUG` | Active les logs de debug (la plus utile au dev). |
| `PRISM_NO_PROJECT_BROWSER` | Ne pas ouvrir le Project Browser au démarrage. |
| `PRISM_IGNORE_PATH_LENGTH` | Ignorer la limite de longueur des chemins Windows. |
| `PRISM_SKIP_PROJECT_PATH_WARNING` | Masquer l'avertissement de chemin de projet. |
| `PRISM_DATE_FORMAT` | Format d'affichage des dates. |
| `PRISM_CONFIG_EXTENSION` | Extension des fichiers de config. |
| `PRISM_CONFIG_PERMISSION_WARNING` | Avertissement de permissions de config. |
| `PRISM_BLACKLISTED_EXTENSIONS` | Extensions de fichiers à ignorer. |
| `PRISM_AUTOSAVE_INTERVAL` | Intervalle d'autosave. |
| `PRISM_SLIDER_FIX` | Workaround UI (sliders). |
| `PRISM_VERSION` | (lecture) version de Prism. |

### B.8 Spécifiques aux plugins DCC

**Maya** (cf. aussi `DOCUMENTATION_Prism_Maya.md`) :

| Variable | Effet |
|---|---|
| `PRISM_MAYA_WORKSPACE_TEMPLATE` | `workspace.mel` template pour le Maya project. |
| `PRISM_MAYA_FBX_DELETE_OOR_KEYFRAMES` | `0`/`1`/`2` : supprimer les keyframes hors range à l'export FBX. |
| `PRISM_MAYA_RES_GATE` | Résolution gate du viewport (playblast). |
| `PRISM_MAYA_SHOW_ORNAMENTS` | Afficher les ornements (HUD) dans le playblast. |
| `PRISM_MAYA_SET_VISIBLE_OBJECT_TYPES` | Types d'objets visibles au playblast. |
| `PRISM_MAYA_DFT_RENDERLAYER_NAME` | Nom du render layer par défaut. |

**Houdini** : `PRISM_HOUDINI_IGNORE_LOCKED_PARM_WARNING`,
`PRISM_HOUDINI_IMPORT_SELECTABLE_PARMS`, `PRISM_HOUDINI_PLAYBLAST_SHOW_MPLAY`,
`PRISM_HOUDINI_PLAYBLAST_USE_NEW_VIEWPORT`, `PRISM_USE_HOUDINI_FILEREFERENCES`,
`PRISM_STANDALONE_KARMA`.

**USD** : `PRISM_USD_SITE_PACKAGES`, `PRISM_USD_DLL_DIR` (localiser `pxr` hors DCC — utilisé
par ton plugin EsmaUSD).

**Project Management — FTrack** : `PRISM_FTRACK_URL`, `PRISM_FTRACK_APIKEY`,
`PRISM_FTRACK_EMAIL`, `PRISM_FTRACK_ASSET_BASEPATH`.

**Photoshop** : `PRISM_PHOTOSHOP_KEY`.

> ⚠️ Ces listes sont extraites par recherche dans le code installé ; certaines variables sont
> des réglages avancés/expérimentaux. Pour confirmer l'effet exact d'une variable, cherche son
> usage :
> ```
> grep -rn "PRISM_MA_VARIABLE" "C:\Program Files\Prism2\Scripts" "C:\ProgramData\Prism2\plugins"
> ```

---

## Partie C — Recommandations pour PipeEsma

1. **Config partagée du studio → Project Settings (Environment)**. Versionnée avec le projet,
   tout le monde en hérite (ex. `PIPEESMA_SHOWROOT`, `OCIO_maya`, `PRISM_SHOTCAM_TASK`).
2. **Réglages machine/perso → User Settings (Environment)** (ex. chemins d'outils locaux).
3. **Pour un process externe** (ferme, scripts CLI hors Prism) → *Make persistent* (`setx`).
4. **Tokens dynamiques** → abonne-toi au callback `expandEnvVar` dans ton plugin Custom pour
   résoudre des jetons PipeEsma maison dans les valeurs.
5. **Réagir aux changements** → abonne-toi à `updatedEnvironmentVars` pour rafraîchir tes
   outils quand l'utilisateur change de projet (c'est ce que fait Maya pour l'OCIO).
6. **Plugins studio** → `PRISM_PLUGIN_SEARCH_PATHS` vers ton partage réseau, plutôt que de
   copier les plugins sur chaque poste.

---

### Snippets

```python
# S'abonner aux changements d'environnement (dans Prism_PipeEsma_Functions.__init__)
self.core.callbacks.registerCallback(
    "updatedEnvironmentVars", self.onEnvUpdated, plugin=self)

@err_catcher(name=__name__)
def onEnvUpdated(self, reason, envVars, *args):
    # reason ∈ {"refreshUser", "refreshProject", "unloadProject"}
    show = os.environ.get("PIPEESMA_SHOWROOT")
    ...

# Résoudre un token custom @show@ dans toutes les valeurs d'env
self.core.callbacks.registerCallback("expandEnvVar", self.expandEsma, plugin=self)

@err_catcher(name=__name__)
def expandEsma(self, value, *args):
    if "@show@" in value:
        return value.replace("@show@", self.core.projects.getProjectName() or "")
    # retourne None pour ne rien changer
```
