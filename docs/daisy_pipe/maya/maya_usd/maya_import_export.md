# Import, export et unités

Cette page explique comment importer et exporter de l'USD avec Maya, et comment gérer les unités.

## Import ou stage ?

Il y a deux manières d'amener de l'USD dans une scène Maya, qui n'ont pas du tout le même effet.

| Méthode | Résultat |
|---|---|
| Créer un stage depuis un fichier | Le contenu reste de l'USD. Il est affiché par le proxy shape et reste lié à son fichier. |
| File → Import | Les données USD sont converties en données Maya natives. Il n'y a plus de lien avec le fichier d'origine. |

Pour un travail en pipeline, on privilégie le stage, qui conserve les layers et les références.

## Exporter vers l'USD

Pour exporter, utilisez _File → Export All_ ou _File → Export Selection_ et choisissez le format USD. La fenêtre d'options propose notamment les réglages suivants :

| Option | Description |
|---|---|
| Subdivision | Méthode de subdivision écrite dans le fichier. Voir la page [problèmes connus](maya_problemes_connus.md) pour le cas des normales. |
| USD Preview Surface | Écrit un matériau USD Preview Surface en plus du matériau Maya. Voir la page [matériaux](maya_materiaux.md). |
| Color Sets et UV Sets | Exportent les sets de couleurs et d'UV du maillage. À activer si vous en avez besoin dans la suite du pipeline. |

## Unités et échelle

Maya travaille par défaut en centimètres, alors que l'USD stocke l'unité de la scène dans la métadonnée `metersPerUnit`. Une valeur de 0.01 correspond à des centimètres, une valeur de 1 à des mètres.

Dans le layout de l'exemple, la Layer Data Window montre un `metersPerUnit` à 0.01 ainsi qu'une matrice `maya_scale` à 0.01 sur le prim racine. En cas de problème d'échelle, c'est le premier endroit à contrôler.

!!! tip

        Si l'échelle est incorrecte après l'import d'un asset venant d'un autre logiciel (Houdini de jeu par exemple), commencez par remettre à l'échelle l'asset en changeant la scale de l'usd dans l'attribute editor.