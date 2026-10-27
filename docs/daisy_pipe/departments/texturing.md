# Texturing
[< page précédente](../departments.md)<br>


- [Texturing](#texturing)
  - [Créer la scène de texture](#créer-la-scène-de-texture)
  - [Travail en cours](#travail-en-cours)
  - [Exporter votre travail](#exporter-votre-travail)
  - [Workflow hors Substance](#workflow-hors-substance)

***
Commençons par définir les shapes de nos assets. Nous allons nous attaquer à 2 types de modé : la modé low (ModL) et la modé high (ModH). La ModL servira de proxy dans nos futurs fichiers USD, il est donc important qu'elle soit la plus simple et légère possible. La ModH quand à elle sera la modé qui sera affichée au rendu (donc aussi celle qui sera texturée et shadée).

Pour ce qui concerne le texturing, un 3eme type de modé entre en jeu : la modé issue du Sculpt dans le cas des assets sculptés sur ZBrush. C'est la verison très très high poly que vous exportez de ZBrush et que vous souhaitez utiliser pour baker vos assets dans Substance Painter.

En règle générale, cet article de documentation concerne le texturing sur Substance Painter qui sort des maps utilisées en Shading sur Maya ou sur Houdini ensuite.

Donc, sans plus de détours, c'est comment qu'on fait ?

## Créer la scène de texture
Pour commencer à travailler, il faut créer sa scène de travail Substance Painter. Pour cela, rien de plus simple:
- Avoir [installé le plugin Substance Painter](../../SubstancePainter/installation.md) et avoir sa licence valide
> Si vous avez un problème avec Substance qui ne répond pas et crash lorsque le plugin est installé, allez dans **Prism > Options > Settings > User > Plugins** et faites un Clic Droit sur le plugin Substance Painter et **Reload**.
>> Ce problème est dû au fait que Prism croit reconnaître son propre plugin Substance Painter au lieu de celui codé par notre super team (sorry on aurait pu esquiver cette erreur mais bon voilà)

Il vous suffit ensuite d'ouvrir Substance Painter, une fenêtre popup apparait avec le Project Browser qui vous permet de choisir (ou créer) votre scène de travail.
A la création, sélectionnez la ModH pour votre texturing. La ModH ne sera généralement pas utiliser en texture sauf exception. La Modé Sculpt, elle, sera utilisé pour baker vos textures mais pas en tant qu'asset texturé puisque trop lourd.

Suivez ensuite le fonctionnement comme dans le [mode d'emploi du Substance Painter](../../SubstancePainter/imports.md)

## Travail en cours
Vous pouvez ensuite texturer comme bon vous semble sans aucune limitation particulière. Vous avez accès à toutes les fonctionnalités natives à Substance Painter.

Pour energistrer votre avancée, vous avez 2 options dans votre menu Prism : Save Version et Save Comment. Chacunes de ces 2 options permettent de sauver et incrémenter votre version. de travail, soit en mode rapide soit en ajoutant une commentaire et/ou un thumbnail. Si vous souhaitez uniquement sauver votre travail sans incrémenter, vous pouvez faire un Ctrl+S.

## Exporter votre travail
Pour l'export, veuillez suivre la logique de votre mode d'emploi d'export Substance Painter [mode d'emploi d'export Substance Painter](../../SubstancePainter/exports.md)

Les textures s'exporteront exactement au bon endroit dans votre pipeline avec un nomenclature contrôlée.

## Workflow hors Substance
Vous pouvez bien sûr utiliser d'autres workflow en dehors de Substance Painter comme Substance Designer (non supporté par le plugin) ou encore Photoshop ou Affinity Photo. Cependant, ces logiciels n'ayant pas été codés pour fonctionner dans le pipe, il vous sera nécessaire de gérer vous-même vos scènes de travail et vos exports pour qu'ils soient rangés à des endroits logiques et cohérents avec le reste de la pipeline.
> Si vous avez une question pour cela, n'hésitez pas à demander à Leeloo (qui a beaucoup trop travaillé la nomenclature et l'arborescence des fichiers pour ne pas savoir comment vous aider).




[< page précédente](../departments.md) - 
[page suivante >](shading.md)<br>
*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*