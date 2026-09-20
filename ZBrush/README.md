# Zbrush Plugin for Prism

## Install
To install the plugin properly, you need to make sure you have installed Prism or Prism2 and Zbrush 2022. Here is the install process:
- move the **Integration** folder content into: **C:/Program Files/Pixologic/ZBrush 2022 FL/ZStartup/ZPlugs64**
- move the **Zbrush folder** into: **C:/Program Files/Prism2/Plugins/Apps**
- in Prism, install the plugin by navigating through the menu **Options/Settings/Plugins** and **add existing plugin**. Then go to Apps and select the plugin.
- if the plugin is not aviable in Zbrush, go to **Zscript/Load** and load the file named **prism_menu.txt**. It should compile the script and create a .zsc file.

## How to use it
In Prism you can create new Zbrush files by **right clicking in the Files pannel** and choosing **Create new version from preset** and **EmptyScene Zbrush**

In Zbrush you can access a new window by clicking on **Zplugin/Prism/FloatingWindow**. This will open a floating window with several buttons:
- **.ztl** and **.zpr** checkbox: which allows you to choose the file extension
- **Save**: to save your file (with Prism versioninfo json file)
- **Save Version**: to save a new version of the file
- **Save Extended**: to save a new version with additional options like comment, description and custom preview
- **Import**: to import Prism products in Zbrush
- **Export**: to export Prism products from Zbrush
- **Project Browser**: to load a new instance of Prism project browser inside Zbrush
- **Turntable**: to record a turn of your 3D model and store it as a new media in Prism
- **Settings**: to open the Prism settings pannel

## Credits
*created by Mathieu Carrey (2025)*\
*modified by Thomas Rubio (2026)*