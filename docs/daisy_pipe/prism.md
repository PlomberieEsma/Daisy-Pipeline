# Prism (Daisy Pipe)
[< page précédente](../daisy_pipe.md)

Daisy Pipeline est un plugin Prism, il intègre des fonctionnalités sur Houdini et Maya mais aussi dans Prism lui même. Cette page fait l'inventaire de ces fonctionnalités, certaines plus importantes que d'autres mais toutes très utiles. Voici ce qu'elle contient :

- [Create USD asset](#create-usd-asset)
- [Pack USD asset](#pack-usd-asset)
- [Add variant](#add-variant)
- [Duplicate and convert USD](#duplicate-and-convert-usd)
- [View with usdview](#view-with-usdview)

## Create USD asset
Commençons avec l'une des actions que vous allez le plus utiliser dans Prism. Le "Create USD Asset". Mais qu'est-ce que c'est ?<br>
Tout d'abord il faut comprendre ce qu'est un **asset** en USD. C'est un fichier USD qui va en référencer d'autres pour n'avoir à appeler qu'un seul fichier par la suite. **C'est une sorte de grosse boite dans laquelle on met la geo, le groom, les shaders ...**

Par exemple, j'ai un asset de poisson. Je lui ai créé une geo et un shader, que j'ai exporté en 2 USD séparés. Je vais créer un asset USD pour combiner ma geo et mon shader dans un seul fichier qui référencera les 2. Comme ça, si je veux retoucher la geo et que quelqu'un veut modifier le shader, on pourra le faire en même temps et l'asset final sera mis à jour automatiquement.

![houdini pufferfish asset](src/prism/houdini_pufferfish_asset.png)

Cette fonctionnalité d'asset USD permet également d'ajouter des éléments propres à l'USD comme :
- la création de variants
- la gestion de proxys
- la création de payloads
- la gestion des primitives avec une classe

Maintenant vous vous dites peut-être : "Ok super, t'es bien gentil mais comment on le crée ton asset de poisson ?". Très bonne question cher ami pêcheur !

Tout d'abord ouvrez Prism (de préférence pas depuis un logiciel, ouvrez directement Prism).

## Pack USD asset

## Add variant

## Duplicate and convert USD

## View with usdview

[< page précédente](../daisy_pipe.md) - 
[page suivante >](departments.md)<br>
*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*