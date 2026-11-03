# Problèmes connus
[< page précédente](../maya_usd.md)

Cette page regroupe les problèmes courants rencontrés avec l'USD dans Maya, et leur solution.

| Problème | Solution |
|---|---|
| Les couleurs écrites dans `displayColor` présentent un décalage gamma après l'export. | Définir la variable d'environnement `PIXMAYA_LINEAR_COLORS` sur `true` avant de lancer Maya. |
| L'échelle est incorrecte à l'import d'un asset venant d'un autre logiciel. | Mettre à jour le plugin maya-usd vers la dernière version disponible sur GitHub. |
| Les normales sont cassées après un export puis une réimportation dans Maya 2026. | Dans les options d'export USD, régler la méthode de subdivision sur _None (polygonal mesh)_. |
| Impossible d'éditer ou de cibler un layer. | Vérifier que le layer n'est pas verrouillé, qu'il n'est pas en lecture seule, et que vous n'éditez pas dans un layer plus faible que celui qui contient déjà la valeur. |
| Les matériaux RenderMan ne s'affichent pas. | Ils ne sont pas pris en charge dans Maya. Voir la page [matériaux](maya_materiaux.md). |

[< page précédente](../maya_usd.md)

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*
