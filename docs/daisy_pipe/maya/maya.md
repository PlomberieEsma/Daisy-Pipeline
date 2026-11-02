# Maya
[< page précédente](../installation.md)  

Cette page a pour but de documenter l'utilisation de l'entièreté du pipeline alembic et USD, de la hiérarchie des groupes,
à comment passer d'un departement a un autre au sein de Maya.
Dans cette documentation nous partirons du principe que vous connaissez un minimum ***Maya***. Nous partirons également du principe que vous connaissez  ***[les principes de base de l'USD](../overview/usd.md)***que nous avons expliqué dans cette documentation.  

Voici un petit sommaire pour vous aider :

- [L'USD dans Maya](#lusd-dans-maya)
- [Templates](houdini/templates.md)
- [HDA](houdini/hda.md)

## L'USD dans Maya

Tout d'abord, avant de vouloir tout passer en USD, il faut être conscient de plusieurs points concernant l'USD dans Maya.
Les prims USD (affichés via le proxy shape de maya-usd) et les nodes Maya natifs peuvent coexister dans la même scène, mais ils ne vivent pas dans le même graphe.
Les outils Maya comme les deformers, les contraintes ou le rig ne peuvent donc pas agir directement sur les prims USD. Pour les modifier,
il faut passer par _"l'outliner"_ USD, ou utiliser « Edit As Maya Data » puis renvoyer les changements vers le stage.

><img src="../../src/information.png" width=50em><br>
>Pour plus d'informations sur l'USD Maya, retrouvez la ***[documentation officielle ici](https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=GUID-9E9D45F2-4DA9-497B-8D69-1573ED6B2BA8)***.

Comment acceder aux outils usd de maya ? Assurez-vous d'avoir le mayaUsdPlugin de maya d'activé. Pour vérifiez, allez dans : Winsdows

<img src="src/solaris/houdini_stage_icon.png" width=200em><br>

[< page précédente](../installation.md) - 
[page suivante >](../houdini.md)  

*<sub>Daisy Pipeline 2026 - by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio</sub>*