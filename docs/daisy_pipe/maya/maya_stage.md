# Maya
[< retour à la page Maya](maya_usd.md)

Cette page explique comment créer un stage USD dans Maya et comment Maya l'affiche.

## Créer ou charger un stage

Un stage est un fichier USD racine et l'ensemble de ses layers. Dans Maya, il est affiché dans la scène par un node appelé _proxy shape_, qui apparaît dans l'Outliner. C'est en dépliant ce node que vous retrouvez la hiérarchie des prims.

Il existe deux façons de créer un stage :

| Option | Description |
|---|---|
| Stage with New Layer | Crée un stage vide, avec un nouveau layer anonyme. |
| Stage from File | Crée un stage à partir d'un fichier USD existant. Un explorateur s'ouvre pour choisir le fichier. |

Ces deux options sont disponibles dans le menu _Create_ de l'USD Layer Editor, ainsi que dans le menu _Create_ de Maya, sous _Universal Scene Description (USD)_.

## Choisir le stage affiché dans le Layer Editor

En haut de l'USD Layer Editor, le sélecteur _USD Stage_ indique le stage dont les layers sont affichés. Par défaut, il suit ce que vous sélectionnez dans l'Outliner : si vous cliquez sur un prim d'un autre stage, l'éditeur change de stage.

Le bouton _Pin_, à côté du sélecteur, fige ce choix. Le stage reste affiché même si vous sélectionnez autre chose dans l'Outliner, ce qui est pratique quand une scène contient plusieurs stages. Activer le pin déclenche une sauvegarde de la scène Maya, et son état est conservé d'une session à l'autre.

## Sauvegarder le stage

Le bouton _Save Stage_, en haut à droite de l'arbre des layers, enregistre en une fois toutes les modifications non sauvegardées du stage. Le nombre de modifications en attente est affiché à côté de l'icône. Pour sauvegarder un seul layer, utilisez _Save Edits_ dans son menu contextuel.

><img src="../../src/information.png" width=50em><br>
>Pour plus d'informations sur le Layer Editor, retrouvez la ***[documentation officielle ici](https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=GUID-4FAD73CA-E775-4009-9DCB-3BC6792C465E)***.

[< page précédente](maya_usd.md)

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*
