# Architecture & améliorations — faire fonctionner les tools Maya et le plugin Prism ensemble

> Document de travail. Objectif : passer de **deux moitiés déconnectées** (les
> tools `EsmaUSD/` côté Maya + le plugin Prism `prism/EsmaUSD/` qui ne fait
> rien) à **une seule pipeline cohérente** où Prism déclenche les tools via ses
> callbacks, et où la hiérarchie des modules reflète les dépendances réelles.

---

## 1. Constat : où on en est aujourd'hui

Le repo contient en réalité **deux blocs qui ne se parlent pas** :

| Bloc | Ce qu'il fait | Comment il est appelé |
|------|---------------|------------------------|
| `EsmaUSD/` (côté Maya) | toute la logique réelle : export USD, setup de hiérarchie geo, lecture de l'entité Prism, UI | manuellement, en exécutant un script (`exportUSD.py` lance `export_usd()` **au moment de l'import**) |
| `prism/EsmaUSD/Scripts/` (plugin Prism) | **rien**. `Prism_EsmaUSD_Functions` ne contient que `isActive()` | chargé par Prism au démarrage, mais ne s'abonne à aucun événement |

Le plugin Prism est donc une coquille vide. Toute la valeur est dans `EsmaUSD/`,
mais elle est déclenchée « à la main ». **Les deux ne fonctionnent pas ensemble :
ils coexistent.**

C'est le point n°1 à corriger. Tout le reste en découle.

---

## 2. Le problème central : le plugin ne s'abonne à aucun callback

Aujourd'hui, pour exporter en USD, il faut exécuter `saveas/exportUSD.py`, qui :

```python
# exportUSD.py — état actuel
core = get_core()                 # appel au niveau module
def export_usd(): ...
export_usd()                      # ← exécuté à l'import du module (effet de bord)
```

Conséquences :
- **Effet de bord à l'import** : importer le module *déclenche* un export. Un
  import doit définir des fonctions, pas agir.
- **Aucun lien avec le cycle de vie Prism** : l'export ne se déclenche pas
  « quand l'artiste sauvegarde », il se déclenche « quand quelqu'un ré-exécute le
  fichier ».
- `importlib.reload(EsmaUSD.core.core)` en haut du module : pratique de dev qui
  n'a rien à faire dans un chemin de chargement de prod.

### Ce qu'il faut faire à la place

Le plugin Prism doit **enregistrer des callbacks** dans son `__init__` et appeler
les tools depuis ces callbacks. C'est le mécanisme #1 recommandé par le
`CLAUDE.md` du projet (stable à travers les updates de Prism).

```python
# prism/EsmaUSD/Scripts/Prism_EsmaUSD_Functions.py — cible
import os
from qtpy.QtWidgets import *
from PrismUtils.Decorators import err_catcher_plugin as err_catcher

class Prism_EsmaUSD_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        # On branche la pipeline sur les événements Prism
        self.core.callbacks.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self
        )
        # exemple : export auto au save (si c'est le comportement voulu)
        # self.core.callbacks.registerCallback(
        #     "sceneSaved", self.onSceneSaved, plugin=self
        # )

    @err_catcher(name=__name__)
    def isActive(self):
        return True

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        # ajoute un menu/bouton « Export USD », « Setup Asset »… dans Prism
        ...

    @err_catcher(name=__name__)
    def onSceneSaved(self, *args, **kwargs):
        from EsmaUSD.saveas.exportUSD import export_usd
        export_usd()
```

Points clés (tous issus du `CLAUDE.md` du projet) :
- **`err_catcher` sur chaque méthode publique** du plugin → les exceptions vont
  dans le log Prism au lieu de crasher Maya.
- Dans le plugin, **Qt = `qtpy`** (jamais `launcher.py`). Le launcher, c'est pour
  le code qui tourne *hors* Prism (setupAsset).
- Le plugin reste **mince** : il branche et délègue. La logique reste dans
  `EsmaUSD/`. Le plugin ne réimplémente rien.

> **Décision à prendre** : l'export doit-il se faire **automatiquement au save**
> (`sceneSaved`) ou **sur action explicite** de l'artiste (bouton dans le Project
> Browser / menu Maya) ? Les deux sont valides ; ça change le callback à brancher.
> Tant que ce n'est pas tranché, garde au moins une entrée manuelle propre (une
> fonction qu'on appelle, pas un script qui s'exécute à l'import).

---

## 3. Architecture cible : des couches, pas un plat de spaghettis

Le problème de *hiérarchisation* est réel et déjà visible : **`core/core.py`
importe `setupAsset.maya.setup_geo`**. Autrement dit, la couche « core »
(bas niveau, censée ne dépendre de rien) dépend d'un outil de haut niveau. C'est
une **inversion de dépendance**.

### Modèle en couches proposé

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRÉES (déclencheurs)                                      │
│  • plugin Prism (callbacks)      • UI setupAsset            │
│  • menu / shelf Maya             • exécution manuelle        │
└───────────────┬─────────────────────────────────────────────┘
                │  appelle
┌───────────────▼─────────────────────────────────────────────┐
│  ORCHESTRATION  (EsmaUSD/ops/ — « ce qu'on veut faire »)     │
│  export_usd(), setup_asset()… enchaînent les briques        │
│  Connaît Prism (entité, version, master) ET le DCC          │
└───────────────┬─────────────────────────────────────────────┘
                │  utilise
┌───────────────▼─────────────────────────────────────────────┐
│  BRIQUES MÉTIER  (par domaine, sans effet de bord)          │
│  • prism_io   : get_core, entité, generateProductPath…      │
│  • usd_io     : write_usd, create_master (pxr)              │
│  • dcc/maya   : setup_geo, sélection, plugins maya          │
└───────────────┬─────────────────────────────────────────────┘
                │  s'appuie sur
┌───────────────▼─────────────────────────────────────────────┐
│  SOCLE  (dcc/launcher.py — get_dcc / get_qt / main_window)  │
│  Ne dépend de RIEN d'autre dans le repo                     │
└─────────────────────────────────────────────────────────────┘
```

**Règle d'or : une couche ne dépend que des couches en dessous d'elle.**
- `launcher.py` ne doit importer aucun autre module EsmaUSD. ✅ (c'est déjà le cas)
- `setup_geo` (brique DCC) **ne doit pas** importer `core.core` ni appeler
  `get_entity_info` lui-même. Il doit **recevoir** ce dont il a besoin en
  paramètre (le nom du prim, le département). Aujourd'hui il rappelle
  `get_entity_info()` en interne → couplage inutile.
- `core.core` (briques USD) **ne doit pas** importer `setup_geo`. C'est
  l'orchestration (`export_usd`) qui appelle d'abord `setup_geo`, *puis*
  `write_usd`. Aujourd'hui `write_usd("mod", …)` appelle `setup_geo` lui-même →
  c'est ça qui crée l'inversion.

### Réorganisation de fichiers suggérée

L'arborescence actuelle mélange les rôles (`core/core.py` fait à la fois du Prism,
de l'USD et du Maya). Proposition :

```
EsmaUSD/
  prism_io.py        get_core(), get_entity_info()         (briques Prism)
  usd_io.py          write_usd(), create_master()          (briques USD/pxr)
  dcc/
    launcher.py      get_dcc/get_qt/get_main_window        (socle, inchangé)
    maya_geo.py      setup_geo(), geo_is_complete()        (brique DCC Maya)
  ops/
    export.py        export_usd()                           (orchestration)
    setup_asset.py   setup_asset()                          (orchestration)
  ui/
    dpt_choose_menu.py                                       (UI pure)
  lib/usdParamsExport.json
```

Tu n'es pas obligé de tout renommer d'un coup. Le strict minimum pour casser
l'inversion : **sortir l'appel à `setup_geo` de `write_usd`** et le remonter dans
`export_usd`.

---

## 4. `get_core()` : un seul point d'accès, pas dix

`get_core()` est appelé **au niveau module** dans `exportUSD.py`,
`get_entity_info.py` (via la fonction) et `dpt_choose_menu.py`. Chaque appel
re-déroule la logique `PrismInit`.

Deux problèmes :
1. **Au niveau module** = exécuté à l'import → si Prism n'est pas prêt, l'import
   plante. À déplacer *dans* les fonctions.
2. **Dans Maya/Houdini, le `pcore` existe déjà.** Inutile de re-tester
   `prismInit(prismArgs=["noUI"])` à chaque fois. `get_core()` fait déjà le bon
   `getattr(PrismInit, "pcore", None)` — il faut juste **l'appeler à la demande**
   et idéalement **mettre le résultat en cache**.

```python
# prism_io.py
_CORE = None

def get_core():
    global _CORE
    if _CORE is not None:
        return _CORE
    try:
        import PrismInit
        _CORE = PrismInit.pcore or PrismInit.prismInit(prismArgs=["noUI"])
    except Exception as e:
        print(f"[Daisy] Prism introuvable : {e}")
        return None
    return _CORE
```

Et dans les modules : **ne plus** faire `core = get_core()` en haut du fichier.
On appelle `get_core()` à l'intérieur de chaque fonction qui en a besoin.

---

## 5. Bugs concrets repérés à corriger en passant

Ce sont des choses qui *cassent* le fonctionnement aujourd'hui, indépendamment de
l'archi :

### 5.1 Incohérence sur le nom de département (`mod` vs `02_mod`) — **bug réel**

- `exportUSD.py` teste `dept == "02_mod"`
- `setup_geo.py` teste `dept == "mod"`

`get_entity_info()` renvoie `data.get("department")`, qui vaut le nom Prism réel
(avec préfixe, ex. `02_mod`). Donc la branche `if … dept == "mod"` de `setup_geo`
**n'est jamais vraie** → `setup_geo` ne fait rien et renvoie `None`. L'export
« mod » s'appuie donc sur une hiérarchie qui n'est jamais construite.

**Correctif** : une seule source de vérité pour les noms de départements. Soit une
constante/un mapping partagé, soit on normalise (`dept.split("_")[-1]`) à un seul
endroit. À ne **pas** dupliquer dans deux fichiers.

### 5.2 `setup_geo` rappelle `get_entity_info()` au lieu de recevoir ses entrées

`write_usd` connaît déjà `default_prim`, le département, la task… puis appelle
`setup_geo`, qui **re-interroge Prism** via `get_entity_info()`. Double appel,
double risque d'incohérence. → `setup_geo(default_prim, dept)` doit recevoir ce
dont il a besoin.

### 5.3 Effet de bord à l'import (`export_usd()` en fin de `exportUSD.py`)

Voir §2. À retirer ; l'appel doit venir d'un callback ou d'une action UI.

### 5.4 Valeurs en dur

- `comment = "coucou"` dans `exportUSD.py` : placeholder. Doit venir de l'UI ou
  des métadonnées de scène (`getScenefileData`).
- Le `path`/`master_Path` sont bien générés via
  `core.products.generateProductPath(...)` ✅ — c'est exactement ce que demande le
  `CLAUDE.md`. Bon réflexe, à garder.

### 5.5 Doublon d'import et imports inutilisés dans `core.py`

```python
from EsmaUSD.setupAsset import maya
from EsmaUSD.setupAsset import maya   # ← ligne dupliquée
from EsmaUSD import core              # ← s'importe lui-même, inutile
```

À nettoyer. `fixBrokenPixarSchemas` et `UsdSemantics` sont importés mais pas
utilisés non plus.

### 5.6 `dpt_choose_menu.py` — `parent=get_main_window()` dans la signature

```python
def __init__(self, parent=get_main_window()):
```

Un argument par défaut est évalué **une seule fois, à la définition de la classe**.
Donc `get_main_window()` est appelé à l'import du module, pas à l'ouverture de la
fenêtre. → mettre `parent=None` et résoudre dans le corps :

```python
def __init__(self, parent=None):
    if parent is None:
        parent = get_main_window()
    super().__init__(parent)
```

Aussi : `get_all_dept()` n'a pas de `self`, `create_connections` est vide → les
boutons ne sont pas branchés. UI encore à l'état de squelette.

---

## 6. Comment les deux mondes se rejoignent (le schéma final)

```
Artiste sauvegarde / clique « Export » dans Maya
        │
        ▼
Plugin Prism  (callback sceneSaved / bouton menu)      ← qtpy, err_catcher
        │  délègue (n'implémente rien)
        ▼
ops/export.py : export_usd()                            ← orchestration
        │   1. info = get_entity_info()      (prism_io)
        │   2. setup_geo(name, dept)          (dcc/maya_geo)   si mod
        │   3. path = core.products.generateProductPath(...)   (Prism API)
        │   4. write_usd(preset, path, ...)   (usd_io)
        │   5. create_master(path, master)    (usd_io)
        │   6. core.saveVersionInfo(...)      (Prism API)
        ▼
Fichiers USD versionnés + master + version info, conformes au template Prism
```

Le plugin Prism devient le **déclencheur officiel**. `setupAsset` (avec son
`launcher.py`) reste le déclencheur pour le code qui doit tourner aussi **hors
Prism / multi-DCC**. Les deux appellent la même couche d'orchestration.

---

## 7. Déploiement : le plugin et `EsmaUSD` à deux endroits du pipe

Sur le pipe, le plugin Prism (`prism/EsmaUSD/Scripts/`) et la boîte à outils
(`EsmaUSD/`) sont déposés à **deux emplacements différents**. **C'est correct et
voulu — il ne faut pas les fusionner dans un seul dossier.**

### Pourquoi deux emplacements sont obligatoires

Les deux blocs sont **découverts par deux mécanismes différents** :

| Bloc | Qui le charge | Où il doit être |
|------|---------------|------------------|
| `prism/EsmaUSD/Scripts/` | le **PluginManager de Prism**, qui scanne ses dossiers de plugins à la recherche de `Prism_*_init.py` | un **plugin search path de Prism** |
| `EsmaUSD/` | l'**interpréteur Python de Maya**, via `import EsmaUSD` | le **script path de Maya** (`PYTHONPATH` / `MAYA_SCRIPT_PATH`) |

Les coller dans le même dossier casserait une des deux découvertes : Maya n'ira
pas charger un plugin Prism, et Prism ne met pas `EsmaUSD` sur le path de Maya
tout seul.

### « Communiquer » ≠ « être côte à côte »

Deux packages Python se parlent quand ils sont **importables dans le même
process**, pas quand ils partagent un dossier.

- Prism est **intégré dans Maya** : quand un callback du plugin s'exécute, il
  tourne **dans l'interpréteur Python de Maya** — le même process où `EsmaUSD`
  est sur le script path.
- Donc le callback peut faire `from EsmaUSD.saveas.exportUSD import export_usd`
  **même avec les deux à des endroits différents**, à une seule condition :
  `EsmaUSD` doit être sur le `sys.path` de Maya.

**C'est ça qui détermine si ça communique, pas la proximité des dossiers.**

### Le maillon manquant aujourd'hui

Rien dans le repo ne monte `EsmaUSD` sur le path de Maya : pas de `userSetup.py`,
pas de `Maya.env`/`.mod`, aucun `sys.path`/`PYTHONPATH`. Ça doit donc se faire à
la main sur le pipe. **C'est ce maillon qu'il faut fiabiliser — pas la séparation
en deux emplacements.**

### Ce qu'il faut faire

1. **Une seule source versionnée, deux emplacements de déploiement.** Ce repo git
   contient déjà les deux : déploie-les **toujours ensemble depuis ce repo**. Deux
   dépôts indépendants sur le pipe = risque de **drift** (plugin `v2.0.0` appelant
   une API d'un `EsmaUSD` plus ancien).

2. **Rendre le path déterministe.** Deux options propres :
   - **Pointer plutôt que copier** : ajouter `prism/` aux *plugin search paths* de
     Prism, et la racine du repo au `PYTHONPATH`/`MAYA_SCRIPT_PATH` (via
     `Maya.env`, un `.mod`, ou `userSetup.py`). Les « deux emplacements »
     deviennent deux **entrées de path** vers le repo unique. Plus de copie, plus
     de drift.
   - **Plugin auto-suffisant** : dans `Prism_EsmaUSD_Functions.__init__`, ajouter
     le dossier d'`EsmaUSD` à `sys.path` s'il n'y est pas, **avant** tout
     `import EsmaUSD`. Le plugin garantit lui-même que sa boîte à outils est
     importable, sans dépendre d'un pré-montage du pipe :

     ```python
     import os, sys

     def _ensure_esmausd_on_path(self):
         # chemin du repo / racine où vit le package EsmaUSD, à adapter au pipe
         tools_root = os.environ.get("ESMAUSD_ROOT")  # ou un chemin déduit
         if tools_root and tools_root not in sys.path:
             sys.path.insert(0, tools_root)
     ```

3. **Garder la séparation des rôles** telle quelle (§2–§3) : le plugin reste
   l'adaptateur mince côté Prism, `EsmaUSD` reste la boîte à outils côté Maya.
   Deux emplacements ≠ deux responsabilités mal rangées.

**En une phrase :** le problème n'est pas « deux endroits », c'est « aucun garant
que `EsmaUSD` est importable là où le plugin s'exécute ». Règle ça (path
déterministe + déploiement conjoint depuis ce repo) et la séparation en deux
emplacements devient un **atout**, pas un obstacle.

---

## 8. Plan d'action priorisé

**P0 — débloque le « ça marche ensemble »**
1. Retirer l'appel `export_usd()` en bas de `exportUSD.py` (effet de bord).
2. Enregistrer un callback dans `Prism_EsmaUSD_Functions.__init__` qui appelle
   `export_usd()` (ou ajouter un bouton via `onProjectBrowserStartup`).
3. Mettre `err_catcher` sur les méthodes du plugin.
4. Corriger l'incohérence `mod` / `02_mod` (§5.1) — sinon l'export mod reste cassé.

**P1 — hiérarchie saine**
5. Sortir `setup_geo` de `write_usd` ; le faire appeler par `export_usd`.
6. `setup_geo` reçoit ses paramètres au lieu de rappeler `get_entity_info`.
7. `get_core()` mis en cache, appelé dans les fonctions (plus au niveau module).

**P2 — propreté / robustesse**
8. Nettoyer les imports de `core.py` (§5.5).
9. Corriger le défaut `parent=get_main_window()` (§5.6) et brancher l'UI.
10. Remplacer les valeurs en dur (`comment`) par de vraies entrées.

**P3 — quand la base est stable**
11. Découper `core/core.py` en `prism_io` / `usd_io` / `dcc/maya_geo` (§3).
12. Ajouter le support Houdini dans l'orchestration (le `launcher` est déjà prêt).
13. Centraliser les noms de départements / presets dans un seul module de config.

---

## 9. Règles à garder en tête (rappel du CLAUDE.md du projet)

- **Plugin Prism** : `qtpy`, `err_catcher`, callbacks > API directe > monkeyPatch.
  Ne jamais éditer les scripts de Prism eux-mêmes.
- **setupAsset / code hors Prism** : Qt via `dcc/launcher.py`, jamais `qtpy`.
  **Ne pas mélanger les deux.**
- **Chemins de version/master** : toujours via `core.products.*`
  (`generateProductPath`, `getNextAvailableVersion`, `updateMasterVersion`), pas
  de construction de chemin à la main.
- Quand on s'appuie sur un comportement Prism, citer le fichier source
  (`PrismUtils/Products.py`, etc.) pour qu'il soit vérifiable.
