# Sanity checks Prism Pipeline — fonctionnement et utilisation

> Référence : [API Prism — SanityChecks](https://prism-pipeline.com/docs/latest/api/api/core/utils/sanity-checks/),
> [API Prism — PrismCore](https://prism-pipeline.com/docs/latest/api/api/core/prism-core/),
> [Developing Plugins](https://prism-pipeline.com/docs/latest/development/developingPlugins/).
>
> Voir aussi le doc frère [`prism_widgets.md`](./prism_widgets.md) : les sanity checks
> s'appuient sur les helpers de popup (`core.popup`, `core.popupQuestion`) décrits là-bas.

---

## 1. C'est quoi ?

Les **sanity checks** sont les contrôles de cohérence que Prism effectue sur la scène
courante : framerange, FPS, résolution, versions importées obsolètes, version de
l'appli, redémarrage requis… Ils servent à **détecter et corriger** les écarts entre
la scène ouverte dans le DCC et la config du projet/de l'entité (asset ou shot).

Ils sont regroupés dans une seule sous-système du core :

```python
self.sanities = SanityChecks.SanityChecks(self)   # dans PrismCore.py
```

Accès : `core.sanities` (dans un plugin : `self.core.sanities` ; dans Maya/Houdini :
`import PrismInit; PrismInit.pcore.sanities`). Source réelle :
`Prism/Scripts/PrismUtils/SanityChecks.py`.

---

## 2. Les méthodes disponibles

Chaque `checkXxx` détecte un problème et, le plus souvent, **propose une correction**
via une popup ; le handler `onXxxClicked` applique le choix de l'utilisateur.

| Méthode | Signature | Rôle |
|---|---|---|
| `runChecks` | `runChecks(category, settings=None) -> dict` | **Lance tous les checks d'une catégorie** et renvoie un dict de résultats (pass/fail). Point d'entrée principal. |
| `checkFramerange` | `checkFramerange(settings=None) -> None` | Vérifie que la framerange de la scène correspond à celle du shot/asset ; propose de corriger. |
| `onCheckFramerangeClicked` | `onCheckFramerangeClicked(button, shotRange, handleRange=None)` | Applique l'ajustement de framerange choisi dans la popup. |
| `checkFPS` | `checkFPS(settings=None) -> None` | Vérifie que le FPS de la scène = FPS projet/entité. |
| `onCheckFpsClicked` | `onCheckFpsClicked(button, projectFps)` | Applique le changement de FPS. |
| `checkResolution` | `checkResolution(settings=None) -> None` | Vérifie que la résolution = résolution projet/entité. |
| `onCheckResolutionClicked` | `onCheckResolutionClicked(button, projectResolution)` | Applique le changement de résolution. |
| `checkImportVersions` | `checkImportVersions(settings=None) -> None` | Détecte les products importés ayant une version plus récente disponible ; prévient l'utilisateur. |
| `onImportVersionsClicked` | `onImportVersionsClicked(button)` | Met à jour les imports ou ouvre le State Manager selon le choix. |
| `checkAppVersion` | `checkAppVersion() -> None` | Vérifie la compatibilité de la version du DCC avec celle requise par le projet. |
| `checkRestartRequired` | `checkRestartRequired(settings=None) -> bool` | Indique si un redémarrage de Prism est nécessaire (notification optionnelle). |

> **Convention** : un check `checkXxx` *présente* le problème (souvent une
> `core.popupQuestion`) ; le handler `onXxxClicked` reçoit le bouton cliqué + les
> valeurs cibles et *exécute* la correction dans le DCC. Si tu veux automatiser une
> correction sans popup, appelle directement le handler avec le bouton « valider ».

---

## 3. Comment les lancer

### 3.1 Lancer une catégorie de checks

```python
results = core.sanities.runChecks("onPublish")     # ou la catégorie voulue
# results -> dict { nom_du_check: {"result": bool, ...}, ... }

failed = [name for name, r in results.items() if not r.get("result")]
if failed:
    core.popup("Sanity checks en échec : " + ", ".join(failed))
```

`runChecks(category, settings)` est le point d'entrée : il exécute tous les checks
enregistrés dans la catégorie et renvoie un dictionnaire de résultats. Le paramètre
`settings` permet de passer des options/seuils au check.

### 3.2 Lancer un check précis

```python
# Vérifier la framerange de la scène courante (affiche une popup si écart)
core.sanities.checkFramerange()

# Vérifier le FPS, puis la résolution
core.sanities.checkFPS()
core.sanities.checkResolution()

# Avant un export USD dans EsmaUSD : tout valider d'un coup
core.sanities.checkFPS()
core.sanities.checkFramerange()
core.sanities.checkResolution()
```

> Idéal à brancher dans `EsmaUSD/saveas/exportUSD.py` ou `core/core.py` **avant**
> l'export, pour refuser/avertir si la scène n'est pas conforme au shot.

---

## 4. Les intégrer dans EsmaUSD

L'approche stable aux updates (cf. `CLAUDE.md`) : s'abonner à un **callback** plutôt
que d'appeler les checks « en dur » un peu partout.

```python
from PrismUtils.Decorators import err_catcher_plugin as err_catcher

class Prism_EsmaUSD_Functions:
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        # avant chaque export USD, valider la scène
        self.core.registerCallback(
            "preExport", self.on_pre_export, plugin=self
        )

    @err_catcher(name=__name__)
    def on_pre_export(self, *args, **kwargs):
        self.core.sanities.checkFPS()
        self.core.sanities.checkFramerange()
        self.core.sanities.checkResolution()
```

Callbacks pertinents pour déclencher des checks : `preExport` / `postExport`,
`sceneSaved` / `preSaveScene`, `postLoadScene` (Prism lui-même lance déjà des checks
à l'ouverture d'une scène). Liste complète : page *Developing Plugins* et
`PrismUtils/Callbacks.py`.

### Ajouter un check 100 % maison

Il n'y a pas (publiquement documentée) d'API d'enregistrement de check perso dans
`SanityChecks`. Le pattern recommandé pour EsmaUSD :

1. Écrire la logique de contrôle dans une méthode du plugin
   (`Prism_EsmaUSD_Functions.py`), décorée `err_catcher`.
2. La déclencher via un callback (`preExport`, `preSaveScene`…).
3. Réutiliser `core.popupQuestion` pour proposer la correction, à l'image des
   `checkXxx`/`onXxxClicked` de Prism.

```python
@err_catcher(name=__name__)
def check_naming(self, *args, **kwargs):
    import maya.cmds as cmds
    bad = [n for n in cmds.ls(transforms=True) if " " in n]
    if bad:
        ok = self.core.popupQuestion(
            f"{len(bad)} objets ont un espace dans leur nom. Continuer ?",
            buttons=["Oui", "Non"], default="Non",
        )
        return ok == "Oui"
    return True
```

> Si tu veux que ton check apparaisse vraiment dans la liste native de Prism,
> vérifie dans la source `PrismUtils/SanityChecks.py` comment les catégories sont
> peuplées (et regarde s'il existe un callback du type `sanityCheck`/`getChecks`
> dans `Callbacks.py` de ta version) — ce n'est pas garanti par la doc publique.

---

## 5. Récapitulatif

| Besoin | Appel |
|---|---|
| Tout valider pour une étape | `core.sanities.runChecks("<catégorie>")` |
| Vérifier framerange / FPS / résolution | `checkFramerange()` / `checkFPS()` / `checkResolution()` |
| Détecter des imports obsolètes | `checkImportVersions()` |
| Vérifier la version du DCC | `checkAppVersion()` |
| Savoir si un restart est requis | `checkRestartRequired()` |
| Brancher des checks automatiquement | callback `preExport` / `preSaveScene` (+ `err_catcher`) |

**Toujours** : décorer les hooks avec `err_catcher`, privilégier les callbacks à
l'appel en dur, et vérifier les signatures réelles dans
`Prism/Scripts/PrismUtils/SanityChecks.py` avant de s'appuyer dessus (les
arguments des `onXxxClicked` varient selon la version).

---

### Sources
- [API Prism — SanityChecks](https://prism-pipeline.com/docs/latest/api/api/core/utils/sanity-checks/)
- [API Prism — PrismCore](https://prism-pipeline.com/docs/latest/api/api/core/prism-core/)
- [Developing Plugins](https://prism-pipeline.com/docs/latest/development/developingPlugins/)
- [Changelog Prism](https://prism-pipeline.com/docs/latest/changelog/)
