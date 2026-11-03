# Maya
[< retour à la page Maya](maya_usd.md)

Cette page explique comment gérer les matériaux avec l'USD dans Maya, et pourquoi les matériaux RenderMan posent problème.

## Matériaux Maya et USD Preview Surface

Pour qu'un matériau soit correctement traduit en USD, utilisez un matériau Maya Surface, Lambert ou Phong. Ce sont eux qui donnent les meilleurs résultats à l'export.

Le principe est le suivant : appliquez le matériau sur vos objets dans Maya, puis exportez en USD en vous assurant que l'option _USD Preview Surface_ est activée dans la fenêtre d'options d'export. Activez aussi _Color Sets_ et _UV Sets_. Pour tester le résultat, créez un stage depuis le fichier exporté : le matériau doit apparaître dans le viewport.

Pour un matériau Arnold, l'export passe par le menu Arnold, qui propose son propre export USD (_Export All_ ou _Export Selection_).

## Matériaux RenderMan

Les matériaux RenderMan ne fonctionnent pas dans Maya lorsqu'ils sont portés par un stage USD. Ils ne sont pas pris en charge par le proxy shape : ils ne s'affichent pas dans le viewport et ne sont pas éditables depuis Maya.

Concrètement, le viewport Maya ne permet pas de juger l'aspect final d'un asset destiné à RenderMan. Si vous avez besoin d'un aperçu dans Maya, assignez en plus un matériau compatible (Maya Surface, Lambert, Phong ou USD Preview Surface), et conservez le matériau RenderMan pour le rendu dans houdini.


>Un asset qui s'affiche gris ou uni dans Maya n'est donc pas forcément cassé : vérifiez son matériau dans l'outil prévu pour le rendu avant de conclure à une erreur.

[< page précédente](maya_usd.md)

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*
