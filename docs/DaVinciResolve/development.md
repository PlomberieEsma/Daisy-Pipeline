# Développement
[< Page précédente](../davinciresolve.md)


## Installation

Avant d'ajouter correctement le plugin, assurez-vous d'avoir installé préalable Prism2 (ou Prism) ainsi que DaVinci Resolve 21.0. Retrouvez ci-dessous le processus d'installation.

Tout d'abord, copiez le dossier de plugin DaVinciResolve dans votre **ProjetPrism/00_Pipeline/Plugins**
  <br>
  <br>

Dans le dossier de plugin DaVinciResolve/Integration:

- Copiez le fichier **Prism.py** et collez-le dans **C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility**
  <br>
- Ajoutez la ligne ci-dessous au fichier **PluginPaths.json** déjà existant à cet emplacement **C:\Users\3D5\Documents\Prism2**
  > **{"path": "Z:\\ProjetPrism\\00_Pipeline\\Plugins\\DaVinciResolve"}**
  >> Adaptez le début du chemin à l'emplacement local de votre projet/plugin

  <br>
  <br>

***

[< Page précédente](../davinciresolve.md)
[Page suivante >](utilisation.md)<br>
*<sub>Daisy Pipeline 2025 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*