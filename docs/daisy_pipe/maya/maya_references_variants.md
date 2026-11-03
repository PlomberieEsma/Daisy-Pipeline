# Maya
[< retour à la page Maya](maya_usd.md)

Cette page explique comment Maya gère les références, les payloads et les variants d'un stage USD.

## Les références

Une référence amène le contenu d'un autre fichier USD sous un prim, sans le copier. Dans le layout de l'exemple, le prim `sq040_sh0010` référence le setDress master : la ligne `prepend references` visible dans la Layer Data Window indique le chemin du fichier référencé.

Pour ajouter une référence, faites un clic droit sur un prim dans l'Outliner et choisissez _Add USD Reference_. Les modifications que vous faites sur un contenu référencé sont écrites dans le target layer, jamais dans le fichier source. Le fichier référencé reste donc intact et peut être mis à jour indépendamment.

## Les payloads

Un payload fonctionne comme une référence, mais il peut être chargé ou déchargé à la demande. C'est utile pour alléger une scène lourde : on décharge ce dont on n'a pas besoin, et on le recharge au moment voulu.

Dans l'Outliner, un clic droit sur un prim qui porte un payload propose les options _Load_, _Load with Descendants_ et _Unload_.

## Les variants

Un variant set permet de choisir entre plusieurs versions d'un même prim, par exemple plusieurs états d'un asset. Dans Maya, la sélection se fait dans l'Attribute Editor, dans la section dédiée aux variants du prim.

[< retour à la page Maya](maya_usd.md)

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*
