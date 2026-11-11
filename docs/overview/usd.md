# USD

Bienvenue dans une partie importante de cette documentation : la compréhension de l'USD et de certains de ses concepts. Je sais que c'est un gros morceau un peu flou. Dans un premier temps il est possible que vous ne compreniez pas tout, mais à force d'utilisation et de manipulations vous finirez par vous en sortir ne vous en faites pas.<br>
Cette page n'est pas une présentation exhaustive des concepts de l'USD qui sont beaucoup trop nombreux pour rentrer dans une seule page. C'est pourquoi je vous met ici [la documentation officielle](https://openusd.org/release/index.html) qui sera plus détaillée, anisi qu'un [glossaire des concepts liés à l'USD](https://openusd.org/release/glossary.html).

<a href="https://youtu.be/SaBXE4yQetk?si=AtESIyEA6WNDqib4" target="blank">Lien vers une vidéo de présentation de l'USD</a><br>
<a href="https://developer.apple.com/videos/play/wwdc2022/10129/" target="blank">Lien vers une autre vidéo</a>

!!! warning

    À savoir que cette documentation a été rédigé pour vulgariser au maximum l'USD, elle contient donc certaines approximations. De plus l'USD étant un sujet dense et complexe, il est également possible que nous commettions des erreurs dans certaines définitions.

Voici un petit sommaire pour naviguer plus facilement sur cette page :

<div class="page-toc" markdown>

<p class="toc-title">Sommaire</p>

- [Présentation générale](#présentation-générale)
- [Layer](#layer)
- [Asset](#asset)
- [Primitive](#primitive)
    - [Name et path](#name-et-path)
    - [Type](#type)
    - [Kind](#kind)
    - [Attributes et Primvars](#attributes-et-primvars)
- [Proxy](#proxy)
- [Payload](#payload)
- [Variant](#variant)

</div>

***

## Présentation générale
Maintenant que tout cela est dit, passon aux présentations.<br>
L'USD (Universal Scene Description) est une manière de décrir une scène 3D. Créé par Pixar et rendu open source en 2016, l'USD se développe dans de plus en plus de studio. Ce format de fichier a été créé pour permettre un travail **collaboratif** et **non destructif**.

Le format USD est aussi pris en charge par la majorité des logiciels de 3D et des moteurs de rendu, d'où son caractère universel. Ceci devient très pratique pour faire un film, un jeu ou n'importe quelle autre production 3D à grande échelle puisqu'on peut passer d'un logiciel à l'autre très facilement.<br>

L'USD fonctionne par référence, c'est à dire que **les fichiers vont faire des appels en cascade** pour récupérer le contenu des uns et des autres. Ce fonctionnement permet une grande facilité de mise à jour puisqu'il suffit de modifier le contenu d'un fichier pour qu'il se mette à jour dans toute la chaîne et sur toutes les scènes. *Ce principe est très pratique mais est aussi fragile, si vous supprimez un fichier usd de la chaine, tous les autres fichiers seront impactés.*

Si vous voulez plus d'informations et d'exemples concrets, je vous invite à aller voir la [documentation de notre travail sur Daisy Pipeline](../daisy_pipe/index.md), un plugin Prism conçu pour gérer un pipe USD.

***

## Layer
Les layers sont les différents fichiers USD du pipe, ils permettent à plusieurs artistes de travailler sur un même asset en même temps.<br>
*Par exemple : Je veux travailler sur les roues d'une voiture pendant que la personne à côté de moi travail sur sa carosserie. Chacun d'entre nous va travailler sur un layer différent et nos 2 layers seront ensuite combinés dans un 3<sup>ème</sup> layer qui sera notre voiture finie.*

![layers scheme](../assets/images/usd/layers_schematic.png)

C'est le même principe que les références dans Maya : on assemble plusieurs fichiers .ma en référence dans un plus grand fichier qui va tout contenir. La différence ici c'est que contrairement au système de Maya, on peut faire autant de couches de référence qu'on veut. Une référence, dans une référence, dans une référence, dans une référence ... C'est référenceception.

Chaque layer va contenir uniquement les modifications qui auront étées apportées dans son domaine. Par exemple, si j'ai un asset de cabane, je peux modéliser la cabane dans un layer, importer ce layer dans un nouveau layer et modifier sa position dans ce dernier. Le second layer ne contiendra que la transformation, pas tout le processus de modeling.

***

## Asset
L'asset USD est justement un layer qui va rassembler les différents éléments qui le composent. Dans l'exemple du dessus, l'asset sera la voiture finale.<br>
Dans notre pipeline, les assets USD rassemblent la geo, le groom et les materials. Ils permettent aussi d'ajouter des fonctionnalités spécifiques comme les variants, les payloads ... Plein de choses dont on reparlera plus bas.<br>
Les différents assets sont bien souvent de type "component" (vous verrez ce que ça veut dire après) et sont rassemblés par la suite dans des scènes pour créer les shots.

***

## Primitive
En USD on peut dire que **tout est primitive**. Une primitive est le plus petit composant de l'USD, un objet est une primitive, un material est une primitive, une caméra, une light, un groupe, même un paramètre de rendu est une primitive.<br>
Bien souvent les primitives contiennent d'autres primitives pour former la hiérarchie de la scène.

*tout ça, c'est des primitives :*<br>
![primitive hierarchy](../assets/images/usd/primitive_hierarchy.png)

### Name et path
Cette partie là est très simple. **Le name représente le nom de la primitive**, et **le path : sa position dans la hiérarchie**. Comme un fichier sur votre PC. Par exemple si j'ai un asset d'armure, j'aurai probablement une primitive avec le name "casque" et le path "/armure/geo/casque"

Cest deux éléments sont des composants essentiels à chaque primitive, vous aurez toujours les deux que vous le vouliez ou non.

### Type
Comme son nom l'indique, le type est le type d'élément que sera la primitive. Par exemple : une caméra, un mesh, une curve, une light, un paramètre de rendu, une AOV ... Il se définit à la création de la primitive.

!!! info
    A noter que certaines primitives peuvent parfois ne pas avoir de type (c'est le cas des classes par exemple). Mais la grande majorité d'entre elles en ont, même les groupes qui peuvent être soit de type scope soit de type xform.

    **Xform** : celles-ci servent à contenir d'autres primitives mais peuvent aussi être transformées (translate, rotate, scale ...), contrairement aux scopes qui restent statiques.<br>
    **Scope** : ces primitives servent à contenire d'autres primitives comme des groupes statiques. On peut y ranger les primitives qui ne font pas vraiment parti du monde 3D comme les materials ou les paramètres de rendu par exemple.

### Kind
Là ça devient un peu plus complexe. Un kind est une information supplémentaire que l'on peut rajouter à une primitive pour structurer une scène. Il n'est pas obligatoir mais peut être très utile pour trier des primitives.<br>
Il en existe 4 :

|icon|Kind|Description
|---:|:---|:---
|![assembly icon](../assets/images/usd/assembly.png)|Assembly|C'est la primitive qui va rassembler toute une scène, une sorte de "super groupe", en général il n'y a qu'une primitive avec ce kind.
|![group icon](../assets/images/usd/group.png)|Group|C'est un groupe, tout ce qu'il y a de plus basique.
|![component icon](../assets/images/usd/component.png)|Component|Le component sert à ressembler plusieurs éléments appartenant à un même objet (que bien souvent on a pas l'intention de toucher). On l'utilise sur la primitive de l'[asset](#asset) qui contient tous les éléments de ce dernier (geo, materials, groom ...) mais qu'on ne veut pas forcément ouvrir.
|![subcomponent icon](../assets/images/usd/subcomponent.png)|Subcomponent|Ce sont de petits components (je vous avoue que je ne les utilise pas mais libre à vous de le faire si vous voulez).

### Attributes et Primvars
Nous en venons à présent aux éléments qui constituent chaque primitive : les attributs et les primvars.<br>
**Un attribut est une donnée stockée dans une primitive** qui est prévue par l'USD. Par exemple pour une primitive de type light, on aura probablement un attribut "intensity".<br>
**Une primvar est un attribut supplémentaire que l'utilisateur va ajouter à la primitive**.

!!! example
    Par exemple si je veux stocker l'information de quel personnage ma light va suivre, je vais créer une primvar qui va s'appeller "primvar:follow" et lui donner comme valeur le path vers mon personnage "/ma_scene/personnages/coiffeur".<br>
    Cet exemple est totalement arbitraire et ne suffit pas en lui même à faire quoi que ce soit. La primvar ne sert qu'à stocker des valeurs custom dans une primitive, ensuite il faut la récupérer pour en faire quelque chose.

***

## Proxy
Les proxys sont des versions simplifiées des modèles 3D. Ils sont utilisés pour économiser des ressources et donc gagner en performance quand on travail.

!!! info
    Dans Daisy Pipeline, les proxys sont automatiquement créés à partie de la modé low de chaque asset. Ils sont créés par la fonction "[Create USD Asset](../daisy_pipe/prism.md#create-usd-asset)".

***

## Payload
Un payload est un layer un peu particulier. C'est un layer (fichier USD) qui permet de choisir si l'on le veut charger (load) ou pas. Les payloads sont très pratiques pour gagner en performances dans une scène.

!!! abstract "intéressant"
    Dans Houdini les payloads qui ne sont pas chargés (unload) sont quand même visibles via leur bounding box.

!!! tip
    Sachez qu'il est quand même possible de décharger un layer qui n'a pas de payload, c'est pratique pour chaque artiste s'il/elle n'a pas besoin de certaines parties de la scène. Cependant ça reste temporaire, seulement valable sur une scène et surtout ce n'est pas définit dans le pipe, ce qui rend cette solution difficile à appliquer à grande échelle.

***

## Variant
Finalement, les variants.<br>
Un variant est une variation de l'asset qui va être stockée dans l'USD. Lorsque plusieurs variants ont étés définis, l'asset importé n'en chargera qu'un, mais il est possible de changer de variant autant que l'on veut.

Les variants sont définis par deux éléments :
- Le variant set : c'est le type d'élément qui sera modifié, par exemple la geo, le groom, le material ...
- Le variant name : c'est le nom du variant que vous voulez choisir

!!! example
    Si je veux modifier la coupe de cheveux d'un personnage, je choisirai le variant set "groom" (ou "grm" pour les intimes) et le variant name "cheveux attachés".
