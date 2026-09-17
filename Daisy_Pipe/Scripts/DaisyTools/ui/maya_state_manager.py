#                           .=     ,        =.
#                   _  _   /'/    )\,/,/(_   \ \
#                    `//-.|  (  ,\\)\//\)\/_  ) |
#                    //___\   `\\\/\\/\/\\///'  /
#                 ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
#                 \       `-.  '_`.      .'_` \ ,-"~`/
#                  `.__.-'`/  ( -\        /- )|-.__,'
#                    ||   |    \ O)  /^\ (O / |
#                    `\\  |         /   `\    /
#                      \\  \       /      `\ /
#                       `\\ `-.  /' .---.--.\
#                         `\\/`~(, '()      ('
#                          /(O) \\   _,.-.,_)
#                         //  \\ `\'`      /
#                        / |  ||   `""'"~"`
#                      /'  |__||
#                            `o
#      ___       _                    _          ___               
#     / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___       
#    / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)      
#   /____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/       
#                   /___/    /_/    /_/                            
#
#   by Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio
#   art by Joan G. Stark (Spunk)

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

class EsmaUsdExportClass(QWidget):
    className = "EsmaUsdExport"   # nom affiché dans le menu "Add state"
    listType = "Export"           # ou "Import" — la liste dans laquelle il se range

    def setup(self, state, core, stateManager, stateData=None):

        #-----------------------------------------------------------------------------------#
        # Initialize the state's Qt/Prism plumbing                                          #
        # Build the widgets, wire events and pre-fill the selection                         #
        # then restore any previously saved state data                                      #
        #-----------------------------------------------------------------------------------#

        self.core = core
        self.state = state
        self.stateManager = stateManager
        self.canSetVersion = True
        self.nodes = []
        self.setupUi()
        self.connectEvents()
        self.initializeContextDefaults()

        if stateData is not None:
            self.loadData(stateData)

    ##############################################################################################################
    ###########################     CONTEXT & FRAME RANGE Helpers     ############################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def getCurrentContext(self):

        #-----------------------------------------------------------------------------------#
        # Get the entity (asset/shot) the current scene file belongs to                     #
        #-----------------------------------------------------------------------------------#

        fileName = self.core.getCurrentFileName()
        return self.core.getScenefileData(fileName) or {}

    @err_catcher(name=__name__)
    def getContextFrameRange(self, context, rangeType):

        #-----------------------------------------------------------------------------------#
        # Work out the start/end frame for the given range type                             #
        # Mirrors Prism's own default Export state, trimmed to what this state exposes      #
        #-----------------------------------------------------------------------------------#

        # mirrors Prism's own default Export state (default_Export.py::getFrameRange),
        # trimmed to the range types this state exposes
        if rangeType == "Single Frame":
            if hasattr(self.core.appPlugin, "getCurrentFrame"):
                frame = int(self.core.appPlugin.getCurrentFrame())
                return frame, frame
            return None, None

        if rangeType in ("Shot", "Shot + 1") and context.get("type") == "shot" and "sequence" in context:
            frange = self.core.entities.getShotRange(context)
            if frange and frange[0] is not None and frange[1] is not None:
                start, end = int(frange[0]), int(frange[1])
                if rangeType == "Shot + 1":
                    start -= 1
                    end += 1
                return start, end

        if hasattr(self.core.appPlugin, "getFrameRange"):
            start, end = self.core.appPlugin.getFrameRange(self)
            if start is not None and end is not None:
                return int(start), int(end)

        return None, None

    @err_catcher(name=__name__)
    def refreshFrameRange(self, rangeType):

        #-----------------------------------------------------------------------------------#
        # Show/hide the range widgets for the chosen range type                             #
        # and fill them in from the current context unless the type is Custom               #
        #-----------------------------------------------------------------------------------#

        self.updateRangeVisibility(rangeType)
        if rangeType == "Custom":
            return

        context = self.getCurrentContext()
        start, end = self.getContextFrameRange(context, rangeType)
        if start is not None:
            self.sp_rangeStart.setValue(start)
            self.l_rangeStart.setText(str(start))
        if end is not None:
            self.sp_rangeEnd.setValue(end)
            self.l_rangeEnd.setText(str(end))

    @err_catcher(name=__name__)
    def setRangeType(self, rangeType):

        #-----------------------------------------------------------------------------------#
        # Select the given range type in the combo box                                      #
        # and refresh the frame range fields to match                                       #
        #-----------------------------------------------------------------------------------#

        idx = self.cb_rangeType.findText(rangeType)
        if idx != -1:
            self.cb_rangeType.setCurrentIndex(idx)
            self.refreshFrameRange(rangeType)

    @err_catcher(name=__name__)
    def getEntityName(self, context):

        #-----------------------------------------------------------------------------------#
        # Build the display name of the current asset or shot entity                        #
        #-----------------------------------------------------------------------------------#

        if context.get("type") == "asset":
            return context.get("asset", "")
        if context.get("type") == "shot":
            return f"{context.get('sequence', '')}_{context.get('shot', '')}"
        return ""

    @err_catcher(name=__name__)
    def initializeContextDefaults(self):

        #-----------------------------------------------------------------------------------#
        # Prefill the parent prim field with the entity name                                #
        # Remove range types that don't apply outside of shots                              #
        # and pick a sensible default range type/output for the entity type                 #
        #-----------------------------------------------------------------------------------#

        context = self.getCurrentContext()

        entityName = self.getEntityName(context)
        if entityName:
            self.e_parentPrim.setText(entityName)

        if context.get("type") != "shot":
            # "Shot"/"Shot + 1" need a shot's cut range from Prism - not applicable otherwise
            for rangeType in ("Shot + 1", "Shot"):
                idx = self.cb_rangeType.findText(rangeType)
                if idx != -1:
                    self.cb_rangeType.removeItem(idx)

        if context.get("type") == "asset":
            self.setRangeType("Single Frame")
            self.cb_outputType.setCurrentText(".usdc")
        elif context.get("type") == "shot":
            self.setRangeType("Shot")
        else:
            self.setRangeType("Scene")

    @err_catcher(name=__name__)
    def getDefaultPrim(self):

        #-----------------------------------------------------------------------------------#
        # Get the USD default prim name:                                                    #
        # the override field when it is checked and filled in,                              #
        # otherwise the current entity's name                                               #
        #-----------------------------------------------------------------------------------#

        if self.chb_parentPrim.isChecked() and self.e_parentPrim.text().strip():
            return self.e_parentPrim.text().strip()

        return self.getEntityName(self.getCurrentContext())

    ##############################################################################################################
    ###########################     SELECTION Helpers - Maya Objects     #########################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def getReferencedGeoSetNodes(self):

        #-----------------------------------------------------------------------------------#
        # Collect the members of every '<assetName>_geoSet' selection set                   #
        # found inside the Maya file references brought into a shot                         #
        # so a shot export can default to the same geo as each asset's own export           #
        #-----------------------------------------------------------------------------------#

        # a shot scene can have several rigs brought in as Maya file references;
        # each rig's own asset export already left a "<assetName>_geoSet" set
        # inside that referenced file - find all of them and union their members
        # pyrefly: ignore [missing-import]
        import maya.cmds as cmds
        import os

        # core.entities.getAsset() joins the name directly onto the asset root,
        # so it misses assets organized under subcategory folders - compare
        # against the basenames of every real asset path instead
        assetPaths = self.core.entities.getAssetPaths() or []
        validAssetNames = {os.path.basename(p) for p in assetPaths}

        nodes = []
        for objSet in cmds.ls(type="objectSet"):
            try:
                isReferenced = cmds.referenceQuery(objSet, isNodeReferenced=True)
            except RuntimeError:
                isReferenced = False
            if not isReferenced:
                continue

            shortName = objSet.rsplit(":", 1)[-1]
            if not shortName.endswith("_geoSet"):
                continue

            entityName = shortName[: -len("_geoSet")]
            if not entityName or entityName not in validAssetNames:
                continue

            nodes.extend(cmds.sets(objSet, query=True) or [])

        return list(dict.fromkeys(nodes))

    @err_catcher(name=__name__)
    def setObjects(self, nodes):

        #-----------------------------------------------------------------------------------#
        # Replace the Maya Objects list with the given nodes                                #
        #-----------------------------------------------------------------------------------#

        self.nodes = list(nodes)
        self.lw_objects.clear()
        for node in self.nodes:
            self.lw_objects.addItem(node.split("|")[-1])

    @err_catcher(name=__name__)
    def findExistingSelection(self):

        #-----------------------------------------------------------------------------------#
        # Look for an export selection already present in the scene                         #
        # (geo set or group from a previous export) and return its nodes                    #
        #-----------------------------------------------------------------------------------#

        default_prim = self.getDefaultPrim()
        if not default_prim:
            return []

        # pyrefly: ignore [missing-import]
        import maya.cmds as cmds

        if self.getCurrentContext().get("type") == "shot":
            return self.getReferencedGeoSetNodes()

        geo_set_name = default_prim + "_geoSet"
        if cmds.objExists(geo_set_name) and cmds.nodeType(geo_set_name) == "objectSet":
            return cmds.sets(geo_set_name, query=True) or []

        group_path = "|" + default_prim
        if cmds.objExists(group_path) and cmds.nodeType(group_path) == "transform":
            return [group_path]

        return []

    @err_catcher(name=__name__)
    def detectExistingSelection(self):

        #-----------------------------------------------------------------------------------#
        # Fill the Maya Objects list with the export selection already in the scene         #
        # (geo set or group from a previous export), on user request                        #
        #-----------------------------------------------------------------------------------#

        nodes = self.findExistingSelection()
        if not nodes:
            self.core.popup(
                "No existing export selection found in the scene.",
                title="EsmaUsdExport",
                severity="warning",
            )
            return

        self.setObjects(nodes)

    ##############################################################################################################
    ###########################     STATE Data - Load / Save     #################################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def loadData(self, data):

        #-----------------------------------------------------------------------------------#
        # Restore the state's saved name/enabled flag                                       #
        # then notify Prism the state settings have been loaded                             #
        #-----------------------------------------------------------------------------------#

        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "stateenabled" in data and type(data["stateenabled"]) == int:
            self.state.setCheckState(0, Qt.CheckState(data["stateenabled"]))

        self.core.callback("onStateSettingsLoaded", self, data)

    ##############################################################################################################
    ###########################     UI CONSTRUCTION     ##########################################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def _makeOverrideRow(self, default_text="", checkbox_label=None):

        #-----------------------------------------------------------------------------------#
        # Build a checkbox + line edit pair,                                                #
        # the widget used by every override field in this state's UI                        #
        #-----------------------------------------------------------------------------------#

        # checkbox + line edit, used by every "override" field
        row = QWidget()
        lo_row = QHBoxLayout(row)
        lo_row.setContentsMargins(0, 0, 0, 0)

        chb = QCheckBox(checkbox_label or "")
        e = QLineEdit(default_text)

        lo_row.addWidget(chb)
        lo_row.addWidget(e)

        return row, chb, e

    @err_catcher(name=__name__)
    def setupUi(self):

        #-----------------------------------------------------------------------------------#
        # Build the state's UI: Source, Comment, Target and Settings groups                 #
        #-----------------------------------------------------------------------------------#

        self.lo_main = QVBoxLayout(self)

        self.w_name = QWidget()
        self.lo_name = QHBoxLayout(self.w_name)
        self.l_name = QLabel("Name:")
        self.e_name = QLineEdit()
        self.e_name.setText(self.state.text(0))
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.lo_name.addWidget(self.l_name)
        self.lo_name.addWidget(self.e_name)
        self.lo_main.addWidget(self.w_name)

        # ------------------------------------------------------------ Source
        self.gb_source = QGroupBox("Source")
        self.lo_source = QVBoxLayout(self.gb_source)

        self.w_wholeScene = QWidget()
        self.lo_wholeScene = QHBoxLayout(self.w_wholeScene)
        self.l_wholeScene = QLabel("Export whole Scene:")
        self.chb_wholeScene = QCheckBox()
        self.lo_wholeScene.addWidget(self.l_wholeScene)
        self.lo_wholeScene.addStretch()
        self.lo_wholeScene.addWidget(self.chb_wholeScene)

        self.w_parentPrim = QWidget()
        self.lo_parentPrim = QHBoxLayout(self.w_parentPrim)
        self.l_parentPrim = QLabel("Parent USD Prim:")
        (
            self.row_parentPrim,
            self.chb_parentPrim,
            self.e_parentPrim,
        ) = self._makeOverrideRow()
        self.lo_parentPrim.addWidget(self.l_parentPrim)
        self.lo_parentPrim.addWidget(self.row_parentPrim)

        self.l_objects = QLabel("Maya Objects")
        self.lw_objects = QListWidget()
        self.lw_objects.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lw_objects.setStyleSheet(
            "QListWidget { border: 3px solid rgb(200,0,0); }"
        )
        self.b_addSelected = QPushButton("Add selected")
        self.b_detectExisting = QPushButton("Detect from scene")

        self.w_objectButtons = QWidget()
        self.lo_objectButtons = QHBoxLayout(self.w_objectButtons)
        self.lo_objectButtons.setContentsMargins(0, 0, 0, 0)
        self.lo_objectButtons.addWidget(self.b_addSelected)
        self.lo_objectButtons.addWidget(self.b_detectExisting)

        self.lo_source.addWidget(self.w_wholeScene)
        self.lo_source.addWidget(self.w_parentPrim)
        self.lo_source.addWidget(self.l_objects)
        self.lo_source.addWidget(self.lw_objects)
        self.lo_source.addWidget(self.w_objectButtons)

        # ----------------------------------------------------------- Comment
        self.gb_comment = QGroupBox("Comment")
        self.lo_comment = QVBoxLayout(self.gb_comment)
        self.te_comment = QTextEdit()
        self.te_comment.setFixedHeight(80)
        self.lo_comment.addWidget(self.te_comment)

        # ------------------------------------------------------------ Target
        self.gb_target = QGroupBox("Target")
        self.lo_target = QVBoxLayout(self.gb_target)

        self.w_master = QWidget()
        self.lo_master = QHBoxLayout(self.w_master)
        self.l_master = QLabel("Update Master Version:")
        self.chb_master = QCheckBox()
        self.chb_master.setChecked(True)
        self.lo_master.addWidget(self.l_master)
        self.lo_master.addStretch()
        self.lo_master.addWidget(self.chb_master)

        self.w_updateThumbnail = QWidget()
        self.lo_updateThumbnail = QHBoxLayout(self.w_updateThumbnail)
        self.l_updateThumbnail = QLabel("Update Thumbnail:")
        self.chb_updateThumbnail = QCheckBox()
        self.chb_updateThumbnail.setChecked(True)
        self.lo_updateThumbnail.addWidget(self.l_updateThumbnail)
        self.lo_updateThumbnail.addStretch()
        self.lo_updateThumbnail.addWidget(self.chb_updateThumbnail)

        self.w_outputType = QWidget()
        self.lo_outputType = QHBoxLayout(self.w_outputType)
        self.l_outputType = QLabel("Outputtype:")
        self.cb_outputType = QComboBox()
        self.cb_outputType.addItems([".usda", ".usdc", ".usdz"])
        self.cb_outputType.setCurrentText(".usdc")
        self.lo_outputType.addWidget(self.l_outputType)
        self.lo_outputType.addStretch()
        self.lo_outputType.addWidget(self.cb_outputType)

        self.lo_target.addWidget(self.w_master)
        self.lo_target.addWidget(self.w_updateThumbnail)
        self.lo_target.addWidget(self.w_outputType)

        # ----------------------------------------------------------- Settings
        self.gb_settings = QGroupBox("Settings")
        self.lo_settings = QVBoxLayout(self.gb_settings)

        self.w_rangeType = QWidget()
        self.lo_rangeType = QHBoxLayout(self.w_rangeType)
        self.l_rangeTypeLbl = QLabel("Framerange:")
        self.cb_rangeType = QComboBox()
        self.cb_rangeType.addItems(
            ["Scene", "Shot", "Shot + 1", "Single Frame", "Custom"]
        )
        self.lo_rangeType.addWidget(self.l_rangeTypeLbl)
        self.lo_rangeType.addStretch()
        self.lo_rangeType.addWidget(self.cb_rangeType)

        self.w_rangeStart = QWidget()
        self.lo_rangeStart = QHBoxLayout(self.w_rangeStart)
        self.l_startLbl = QLabel("Start:")
        self.l_rangeStart = QLabel("1")
        self.sp_rangeStart = QSpinBox()
        self.sp_rangeStart.setRange(-9999, 9999)
        self.sp_rangeStart.setValue(1)
        self.lo_rangeStart.addWidget(self.l_startLbl)
        self.lo_rangeStart.addStretch()
        self.lo_rangeStart.addWidget(self.l_rangeStart)
        self.lo_rangeStart.addWidget(self.sp_rangeStart)

        self.w_rangeEnd = QWidget()
        self.lo_rangeEnd = QHBoxLayout(self.w_rangeEnd)
        self.l_endLbl = QLabel("End:")
        self.l_rangeEnd = QLabel("120")
        self.sp_rangeEnd = QSpinBox()
        self.sp_rangeEnd.setRange(-9999, 9999)
        self.sp_rangeEnd.setValue(120)
        self.lo_rangeEnd.addWidget(self.l_endLbl)
        self.lo_rangeEnd.addStretch()
        self.lo_rangeEnd.addWidget(self.l_rangeEnd)
        self.lo_rangeEnd.addWidget(self.sp_rangeEnd)

        self.w_animationType = QWidget()
        self.lo_animationType = QHBoxLayout(self.w_animationType)
        self.l_animationType = QLabel("Animation Type:")
        self.cb_animationType = QComboBox()
        self.cb_animationType.addItems(["Time Samples", "File per Frame"])
        self.lo_animationType.addWidget(self.l_animationType)
        self.lo_animationType.addStretch()
        self.lo_animationType.addWidget(self.cb_animationType)

        self.w_exportUVs = QWidget()
        self.lo_exportUVs = QHBoxLayout(self.w_exportUVs)
        self.l_exportUVs = QLabel("Export UVs:")
        self.chb_exportUVs = QCheckBox()
        self.chb_exportUVs.setChecked(True)
        self.lo_exportUVs.addWidget(self.l_exportUVs)
        self.lo_exportUVs.addStretch()
        self.lo_exportUVs.addWidget(self.chb_exportUVs)

        self.w_subdivision = QWidget()
        self.lo_subdivision = QHBoxLayout(self.w_subdivision)
        self.l_subdivision = QLabel("Subdivision Method:")
        self.cb_subdivision = QComboBox()
        self.cb_subdivision.addItems(["Catmull-Clark", "Bilinear", "Loop", "None"])
        self.lo_subdivision.addWidget(self.l_subdivision)
        self.lo_subdivision.addStretch()
        self.lo_subdivision.addWidget(self.cb_subdivision)

        self.lo_settings.addWidget(self.w_rangeType)
        self.lo_settings.addWidget(self.w_rangeStart)
        self.lo_settings.addWidget(self.w_rangeEnd)
        self.lo_settings.addWidget(self.w_animationType)
        self.lo_settings.addWidget(self.w_exportUVs)
        self.lo_settings.addWidget(self.w_subdivision)

        self.lo_main.addWidget(self.gb_source)
        self.lo_main.addWidget(self.gb_comment)
        self.lo_main.addWidget(self.gb_target)
        self.lo_main.addWidget(self.gb_settings)

        self.updateRangeVisibility(self.cb_rangeType.currentText())

    ##############################################################################################################
    ###########################     EVENT Handling     ############################################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def connectEvents(self):

        #-----------------------------------------------------------------------------------#
        # Wire up the UI widgets to their handlers                                          #
        #-----------------------------------------------------------------------------------#

        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)

        self.chb_wholeScene.toggled.connect(self.wholeSceneToggled)
        self.chb_parentPrim.toggled.connect(self.e_parentPrim.setEnabled)
        self.cb_rangeType.currentTextChanged.connect(self.refreshFrameRange)
        self.b_addSelected.clicked.connect(self.addSelected)
        self.b_detectExisting.clicked.connect(self.detectExistingSelection)

    @err_catcher(name=__name__)
    def wholeSceneToggled(self, checked):

        #-----------------------------------------------------------------------------------#
        # Disable the Maya Objects list and its buttons                                     #
        # while 'Export whole Scene' is checked                                             #
        #-----------------------------------------------------------------------------------#

        self.lw_objects.setEnabled(not checked)
        self.b_addSelected.setEnabled(not checked)
        self.b_detectExisting.setEnabled(not checked)

    @err_catcher(name=__name__)
    def updateRangeVisibility(self, rangeType):

        #-----------------------------------------------------------------------------------#
        # Show the range spin boxes only for the Custom range type,                         #
        # the read-only labels otherwise                                                    #
        #-----------------------------------------------------------------------------------#

        isCustom = rangeType == "Custom"
        self.l_rangeStart.setVisible(not isCustom)
        self.l_rangeEnd.setVisible(not isCustom)
        self.sp_rangeStart.setVisible(isCustom)
        self.sp_rangeEnd.setVisible(isCustom)

    @err_catcher(name=__name__)
    def addSelected(self):

        #-----------------------------------------------------------------------------------#
        # Add the current Maya selection to the Maya Objects list                           #
        # creating the asset's geo group/selection set on first export if needed            #
        #-----------------------------------------------------------------------------------#

        # pyrefly: ignore [missing-import]
        import maya.cmds as cmds

        selection = cmds.ls(selection=True, long=True)
        if not selection:
            self.core.popup("Nothing selected in the scene.", title="EsmaUsdExport", severity="warning")
            return

        default_prim = self.getDefaultPrim()
        geo_set_name = default_prim + "_geoSet" if default_prim else ""
        existing_set = bool(geo_set_name) and cmds.objExists(geo_set_name) and cmds.nodeType(geo_set_name) == "objectSet"

        if self.getCurrentContext().get("type") == "asset" and default_prim and not existing_set:
            from DaisyTools.setupAsset.maya.setup_geo import setup_geo
            from DaisyTools.core.core import create_selection_set

            # setup_geo() parents the selected geo under "<master_grp>|<entity>_geo" -
            # the selection set should track that geo subgroup, not the loose
            # nodes that were selected before it got reparented
            setup_geo(default_prim=default_prim)
            geo_grp_path = "|" + default_prim + "|" + default_prim + "_geo"
            if cmds.objExists(geo_grp_path):
                create_selection_set([geo_grp_path], geo_set_name)
                selection = cmds.sets(geo_set_name, query=True) or [geo_grp_path]

        self.setObjects(selection)

    @err_catcher(name=__name__)
    def nameChanged(self, text):

        #-----------------------------------------------------------------------------------#
        # Keep the state's tree item label in sync with the name field                      #
        #-----------------------------------------------------------------------------------#

        self.state.setText(0, text)

    @err_catcher(name=__name__)
    def updateUi(self):

        #-----------------------------------------------------------------------------------#
        # Nothing to refresh - required by Prism's state interface                          #
        #-----------------------------------------------------------------------------------#

        return True

    ##############################################################################################################
    ###########################     EXPORT Execution     ##########################################################
    ##############################################################################################################

    @err_catcher(name=__name__)
    def getComment(self):

        #-----------------------------------------------------------------------------------#
        # Get the comment to embed in the exported product's version folder name,           #
        # falling back to the State Manager's shared publish comment when left empty        #
        #-----------------------------------------------------------------------------------#

        # the comment ends up embedded in the product's version folder name,
        # so collapse any line breaks from the multi-line field into spaces
        stateComment = " ".join(self.te_comment.toPlainText().split())

        # always use what's typed in this state's own field; only fall back
        # to the State Manager's shared publish comment when it's left empty
        return stateComment or self.stateManager.publishComment

    @err_catcher(name=__name__)
    def getExportParams(self):

        #-----------------------------------------------------------------------------------#
        # Collect this state's UI values into the plain dict                                #
        # that exportUSD.export_usd() expects                                               #
        #-----------------------------------------------------------------------------------#

        # plain dict, no Qt objects - this is what exportUSD.export_usd() consumes
        return {
            "whole_scene": self.chb_wholeScene.isChecked(),
            "nodes": list(self.nodes),
            "default_prim_override": (
                self.e_parentPrim.text().strip()
                if self.chb_parentPrim.isChecked() and self.e_parentPrim.text().strip()
                else None
            ),
            "extension": self.cb_outputType.currentText(),
            "update_master": self.chb_master.isChecked(),
            "update_thumbnail": self.chb_updateThumbnail.isChecked(),
            "export_uvs": self.chb_exportUVs.isChecked(),
            "subdivision_method": self.cb_subdivision.currentText(),
            "animation_type": self.cb_animationType.currentText(),
            "start_frame": self.sp_rangeStart.value(),
            "end_frame": self.sp_rangeEnd.value(),
            "comment": self.getComment(),
        }

    @err_catcher(name=__name__)
    def preExecuteState(self):

        #-----------------------------------------------------------------------------------#
        # Warn if there is nothing to export before the state actually runs                 #
        #-----------------------------------------------------------------------------------#

        warnings = []
        if not self.chb_wholeScene.isChecked() and not self.nodes:
            warnings.append(["No objects in the Maya Objects list.", "", 3])
        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):

        #-----------------------------------------------------------------------------------#
        # Run the USD export and report the result back to the State Manager                #
        #-----------------------------------------------------------------------------------#

        from DaisyTools.saveas.exportUSD import export_usd

        if not self.chb_wholeScene.isChecked() and not self.nodes:
            return [
                self.state.text(0)
                + ": error - No objects in the Maya Objects list. Add objects or check 'Export whole Scene'."
            ]

        try:
            outputPath = export_usd(self.getExportParams())
        except Exception as e:
            return [self.state.text(0) + " - error - %s" % e]

        if not outputPath:
            return [self.state.text(0) + " - error"]

        result = self.core.popupQuestion(
            "USD export: %s" % outputPath,
            title="EsmaUsdExport",
            buttons=["Open in Explorer", "Ok"],
            default="Ok",
        )
        if result == "Open in Explorer":
            self.core.openFolder(outputPath)

        return [self.state.text(0) + " - success"]

    @err_catcher(name=__name__)
    def getStateProps(self):

        #-----------------------------------------------------------------------------------#
        # Collect the state's own properties for Prism to save with the scene               #
        #-----------------------------------------------------------------------------------#

        stateProps = {}
        stateProps.update(
            {
                "statename": self.e_name.text(),
                "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
            }
        )
        return stateProps
