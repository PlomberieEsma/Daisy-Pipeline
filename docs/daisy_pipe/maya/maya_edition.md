# target layer et Edit As Maya Data
[< page précédente](maya_usd.md)

Cette page explique où vont les modifications faites sur un stage USD dans Maya, et comment éditer un prim avec les outils Maya.

## Le target layer

Toute modification faite dans la scène (manipulateur, Attribute Editor, Outliner) est écrite dans le _target layer_. Pour définir un layer comme target, passez la souris à droite de son nom dans l'USD Layer Editor et cliquez sur l'icône grise de target. Elle est surlignée une fois le layer actif.

Dans une pile de layers, le layer du haut est le plus fort : ses valeurs l'emportent sur celles des layers du dessous. Il est donc recommandé de toujours éditer dans un layer fort et jamais dans un layer faible. Les modifications faites dans un layer plus faible que celui qui contient déjà une valeur sont bloquées, car le layer plus fort prendrait de toute façon le dessus.

## Session layer et root layer

| Layer | Rôle |
|---|---|
| Session layer | Layer tout en haut de la pile, dédié aux modifications temporaires. Son contenu n'est pas enregistré dans le fichier USD du stage. |
| Root layer | Layer principal du stage. C'est lui qui contient les sublayers. |

Le menu _Option_ de l'USD Layer Editor propose _Auto-Hide Session Layer_ pour masquer automatiquement le session layer dans l'arbre.

## Edit As Maya Data

Comme les prims USD ne vivent pas dans le même graphe que les nodes Maya, les outils Maya natifs (deformers, contraintes, rig) ne peuvent pas agir directement dessus. _Edit As Maya Data_ permet de contourner ce point.

Faites un clic droit sur le prim dans l'Outliner et choisissez _Edit As Maya Data_. Le prim est converti en nodes Maya que vous pouvez modifier avec les outils habituels. Une fois les modifications terminées, deux choix sont possibles : _Merge Maya Edits to USD_ renvoie les changements vers le stage, _Discard Maya Edits_ les annule et revient au prim d'origine.

><img src="../../src/information.png" width=50em><br>
>Avant de merger, vérifiez quel layer est défini comme target layer, afin que les changements arrivent dans le bon layer.

[< page précédente](maya_usd.md)

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*
