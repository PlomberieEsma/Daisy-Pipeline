# Widgets & menus Prism Pipeline — fonctionnement et utilisation

> Référence : [API Prism](https://prism-pipeline.com/docs/latest/api/),
> [Developing Plugins](https://prism-pipeline.com/docs/latest/development/developingPlugins/),
> [Scripting API examples](https://prism-pipeline.com/docs/latest/development/apiExamples/).
>
> **Règle d'or projet** : dans le code qui tourne *à l'intérieur d'un plugin Prism*,
> on importe Qt via `qtpy` (`from qtpy.QtWidgets import *`), jamais via le launcher
> `setupAsset/dcc/launcher.py` (lui c'est uniquement pour setupAsset). Voir `CLAUDE.md`.

---

## 1. Vue d'ensemble

Prism expose son interface (Project Browser, State Manager, fenêtres de réglages…)
construite en **Qt** (PySide2/PySide6, abstrait par `qtpy`). Pour le développeur,
il y a **trois niveaux** d'intégration UI, du plus simple au plus complet :

1. **Helpers de popup du `core`** — boîtes de dialogue prêtes à l'emploi
   (`core.popup`, `core.popupQuestion`, `core.waitPopup`…). Aucun Qt à écrire.
2. **Widgets réutilisables de Prism** — classes de dialogue toutes faites
   (`PrismWidgets`, `ProjectWidgets`) : saisie de texte, création d'asset, choix
   d'entité, etc. On les instancie et on récupère le résultat.
3. **Widgets Qt 100 % maison** — on construit nos propres `QDialog`/`QWidget` et on
   les **injecte** dans l'UI de Prism via des **callbacks** (ex. ajouter un menu au
   Project Browser).

Oui : **on peut créer nos propres menus et fenêtres**, et même les greffer dans
l'interface existante de Prism. C'est l'objet de la section 4.

---

## 2. Helpers de popup du `core` (niveau 1)

Le plus rapide pour communiquer avec l'utilisateur. Disponibles sur l'objet `core`
(rappel d'accès : dans un plugin `self.core` ; dans Maya/Houdini `import PrismInit;
core = PrismInit.pcore`).

| Méthode | Signature (paramètres principaux) | Usage |
|---|---|---|
| `popup` | `popup(text, title, buttons, default, icon, parent)` | Message standard avec boutons/icône personnalisables. |
| `popupQuestion` | `popupQuestion(text, title, buttons, default, icon, parent)` | Question oui/non — retourne le bouton cliqué. |
| `popupNoButton` | `popupNoButton(text, title, buttons, default, icon, parent, show)` | Popup sans bouton (états d'attente/progress). |
| `waitPopup` | `waitPopup(core, text, title, buttons, default, icon, hidden, parent, allowCancel, activate)` | **Context manager** de progression pour opérations longues (annulable). |
| `parentWindow` | `parentWindow()` | Récupère la fenêtre parente pour bien parenter les dialogues (comportement modal correct). |

### Exemples

```python
# Message simple
core.popup("Export terminé.", title="EsmaUSD")

# Question (confirmation avant d'écraser une master)
result = core.popupQuestion(
    "Mettre à jour la master version ?",
    buttons=["Oui", "Non"],
    default="Non",
)
if result == "Oui":
    core.products.updateMasterVersion(path)

# Opération longue : barre d'attente annulable
with core.waitPopup(core, "Export USD en cours…", allowCancel=True) as wait:
    for dept in departments:
        export_department(dept)
        if wait.canceled:        # l'utilisateur a annulé
            break
```

> `waitPopup` est un *context manager* : la fenêtre s'ouvre à l'entrée du `with` et
> se ferme automatiquement à la sortie, même en cas d'exception. À privilégier dans
> `core/core.py` autour de boucles d'export.

---

## 3. Widgets réutilisables de Prism (niveau 2)

Prism fournit des **dialogues prêts à l'emploi** dans deux modules. On les instancie,
on appelle `.exec_()`, puis on lit le résultat. Cela garantit un look cohérent avec
le reste de l'app et évite de réécrire la validation des noms, le choix d'entité, etc.

### 3.1 `PrismWidgets` (widgets génériques)

| Classe | Constructeur (extrait) | À quoi ça sert |
|---|---|---|
| `EnterText` | `EnterText()` | Dialogue minimal : un champ texte + boutons OK/Annuler. |
| `CreateItem` | `CreateItem(startText='', showTasks=False, taskType='', core=None, getStep=False, showType=False, allowChars=None, denyChars=None, valueRequired=True, mode='', validate=True, presets=None, allowNext=False)` | Création d'un élément nommé avec **validation des caractères**, presets de tâches, champ département optionnel. |
| `CreateDepartmentDlg` | `CreateDepartmentDlg(core, entity=None, configData=None, department=None, parent=None)` | Configurer un département (nom, abréviation, tâches par défaut). |
| `CreateTaskPresetDlg` | `CreateTaskPresetDlg(core, entity=None, configData=None, preset=None, parent=None)` | Définir un preset de tâches lié à des départements. |
| `SetPath` | `SetPath(core)` | Sélection/validation d'un dossier projet local (avec bouton « Parcourir »). |
| `SaveComment` | `SaveComment(core)` | Saisie d'un commentaire de save + capture/sélection d'une image de preview. |
| `MediaPlayersWidget` / `MediaPlayerItem` | `MediaPlayersWidget(origin, playerData=None)` | Groupbox de config des lecteurs média externes. |

### 3.2 `ProjectWidgets` (widgets liés au projet/entités)

| Classe | Constructeur | À quoi ça sert |
|---|---|---|
| `EntityDlg` | `EntityDlg(core)` | **Sélecteur d'entités** projet (asset/shot). |
| `CreateAssetDlg` | `CreateAssetDlg(core)` | Création d'un asset (avec thumbnail). |
| `CreateFolderDlg` | `CreateFolderDlg(core)` | Création d'un dossier dans la hiérarchie. |
| `CreateProductDlg` | `CreateProductDlg(core)` | Création d'un product (choix département/tâche). |
| `CreateIdentifierDlg` | `CreateIdentifierDlg(core)` | Création d'un identifier avec assignation de tâche. |
| `CreateProductVersionDlg` | `CreateProductVersionDlg(core)` | Versionnage d'un product. |
| `CreateMediaVersionDlg` / `IngestMediaDlg` | `(core)` | Création/import d'une version média. |
| `VersionSpinBox` | `VersionSpinBox(core)` | Spinbox formatant les numéros de version (`vNNNN`). |
| `DefaultTasksWindow` | `DefaultTasksWindow(core)` | Config des tâches par défaut entité/département. |
| `ProductTagsDlg` / `ProductTagItem` | `(core)` | Gestion des tags de products. |
| `CreateProject` / `SetProject` / `ManagePresets` | `(core, …)` | Création / sélection / presets de projet. |

### Exemple : demander un nom validé à l'utilisateur

```python
from PrismUtils import PrismWidgets   # chemin réel : Prism/Scripts/PrismUtils

dlg = PrismWidgets.CreateItem(
    core=self.core,
    startText="ours_polaire",
    denyChars=[" ", "/"],     # validation automatique
    valueRequired=True,
)
dlg.setWindowTitle("Nom de l'asset")
if dlg.exec_():               # True si l'utilisateur valide
    name = dlg.itemName       # nom validé récupéré
```

### Exemple : laisser choisir une entité

```python
from PrismUtils import ProjectWidgets

dlg = ProjectWidgets.EntityDlg(self.core)
if dlg.exec_():
    entity = dlg.getCurrentEntity()   # {"type": "asset", "asset_path": "..."}
```

> Les noms exacts des getters (`itemName`, `getCurrentEntity`, …) peuvent varier
> selon la version de Prism : vérifier dans la source `Prism/Scripts/PrismUtils/`
> avant de s'appuyer dessus (cf. `CLAUDE.md` — toujours nommer le fichier source).

---

## 4. Créer ses propres menus et fenêtres (niveau 3)

C'est ici qu'on répond à « peut-on créer nos propres menus ? » → **oui**, de deux
façons combinables.

### 4.1 Injecter un menu/action dans l'UI de Prism via callback

On n'édite **jamais** le code de Prism. On s'abonne à un **callback** qui se
déclenche au bon moment et on ajoute notre widget à l'objet fourni (`origin`).

```python
from qtpy.QtWidgets import QMenu

class Prism_EsmaUSD_Functions:
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        # s'abonne au démarrage du Project Browser
        self.core.registerCallback(
            "onProjectBrowserStartup",
            self.onProjectBrowserStartup,
            plugin=self,
        )

    def onProjectBrowserStartup(self, origin):
        # 'origin' = la fenêtre Project Browser
        origin.esmaMenu = QMenu("EsmaUSD", origin)
        origin.esmaMenu.addAction("Exporter en USD", self.on_export_clicked)
        origin.menubar.addMenu(origin.esmaMenu)

    def on_export_clicked(self):
        self.core.popup("Lancement de l'export EsmaUSD…")
```

> Dans le projet, cette logique vient dans `prism/EsmaUSD/Scripts/Prism_EsmaUSD_Functions.py`,
> et chaque hook public **doit** être décoré par `err_catcher` (cf. `CLAUDE.md`).

### 4.2 Callbacks UI utiles

**Project Browser**
- `onProjectBrowserStartup` — au démarrage (le plus courant pour ajouter un menu).
- `projectBrowser_loadUI` — pendant la construction de l'interface.
- `projectBrowserContextMenuRequested` — menu contextuel général.
- `openPBFileContextMenu` — clic droit sur un fichier (ajouter une action contextuelle).
- `projectBrowser_getAssetMenu` — menu contextuel d'un asset.

**Réglages / dialogues**
- `onPrismSettingsOpen`, `prismSettings_loadUI` — fenêtre de préférences.
- `onProjectSettingsOpen` — réglages projet.
- `onCreateAssetDlgOpen`, `onShotDlgOpen` — à l'ouverture de ces dialogues.

**Autres**
- `trayContextMenuRequested` — menu de l'icône systray.

> Les callbacks sont l'approche **stable aux updates** de Prism (cf. `CLAUDE.md`,
> ordre de préférence : callbacks > API `core` directe > monkeyPatch).

### 4.3 Construire une fenêtre 100 % maison

Rien n'empêche de créer un `QDialog` complet et de l'ouvrir depuis une action de menu.
On le parente à la fenêtre de Prism pour un comportement modal correct.

```python
from qtpy.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

class EsmaExportDialog(QDialog):
    def __init__(self, core, parent=None):
        super().__init__(parent or core.messageParent)
        self.core = core
        self.setWindowTitle("Export EsmaUSD")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Choisir les départements à exporter :"))
        btn = QPushButton("Exporter")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)

# ouverture (par ex. depuis l'action de menu de 4.1)
dlg = EsmaExportDialog(self.core, parent=self.core.messageParent)
dlg.exec_()
```

> `core.messageParent` (ou `core.parentWindow()`) fournit le parent Qt adéquat selon
> le DCC hôte ; ça garantit que la fenêtre reste au-dessus et se ferme proprement.

---

## 5. Récapitulatif — quel niveau choisir ?

| Besoin | Solution recommandée |
|---|---|
| Informer / poser une question simple | `core.popup` / `core.popupQuestion` (§2) |
| Barre de progression pour une opération longue | `core.waitPopup` (§2) |
| Saisir un nom validé, choisir une entité/asset | Widgets `PrismWidgets` / `ProjectWidgets` (§3) |
| Ajouter une entrée de menu / action contextuelle | Callback `onProjectBrowserStartup` & co. (§4.1–4.2) |
| Fenêtre complète sur mesure | `QDialog` maison + parentage `core.messageParent` (§4.3) |

**Toujours** : `qtpy` pour Qt dans le plugin, `err_catcher` sur les hooks publics, et
privilégier l'API `core` / les widgets Prism existants plutôt que de réimplémenter.

---

### Sources
- [API Prism — PrismCore](https://prism-pipeline.com/docs/latest/api/api/core/prism-core/)
- [API Prism — PrismWidgets](https://prism-pipeline.com/docs/latest/api/api/core/utils/prism-widgets/)
- [API Prism — ProjectWidgets](https://prism-pipeline.com/docs/latest/api/api/core/utils/project-widgets/)
- [Developing Plugins](https://prism-pipeline.com/docs/latest/development/developingPlugins/)
- [Scripting API examples](https://prism-pipeline.com/docs/latest/development/apiExamples/)
