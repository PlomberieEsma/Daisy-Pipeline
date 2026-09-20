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

#-----------------------------------------------------------------------------------#
# Standalone "delete versions" window                                               #
# It knows nothing about why it was opened (version cap, manual clean up, ...) nor  #
# about what a version is made of: give it a list of version dicts and the function #
# that knows how to remove one, and it deletes the ones the user ticks              #
#-----------------------------------------------------------------------------------#

import os
import shutil

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


@err_catcher(name=__name__)
def getVersionInfo(core, versionPath):

    #-----------------------------------------------------------------------------------#
    # Read the versioninfo written next to a product version or a scenefile             #
    # (comment / date / user), empty dict when there is none                            #
    #-----------------------------------------------------------------------------------#

    if not versionPath:
        return {}

    infoPath = core.getVersioninfoPath(versionPath)
    return core.getConfig(configPath=infoPath) or {}


@err_catcher(name=__name__)
def deleteProductVersion(core, version):

    #-----------------------------------------------------------------------------------#
    # Remove a product version folder from every location it exists in                  #
    # This is what the window deletes unless the caller hands it something else         #
    # Returns the error messages, empty when it went through                            #
    #-----------------------------------------------------------------------------------#

    errors = []
    #a version can live in several locations (global/local) - drop them all
    paths = version.get("paths") or [version.get("path")]
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        #cheap guard against removing anything but a version folder
        if os.path.basename(path.rstrip("\\/")) != version.get("version"):
            errors.append("%s: unexpected path %s" % (version.get("version"), path))
            continue
        try:
            shutil.rmtree(path)
        except Exception as e:
            errors.append("%s: %s" % (version.get("version"), e))

    return errors


class DeleteVersionsWindow(QDialog):

    #-----------------------------------------------------------------------------------#
    # Let the user pick which versions to delete from disk                              #
    # Nothing is ticked on open: deleting is always an explicit choice                  #
    # Versions passed as locked are listed but can't be selected                        #
    #-----------------------------------------------------------------------------------#

    def __init__(
        self,
        core,
        product,
        versions,
        lockedVersions=None,
        message="",
        parent=None,
        deleteFunc=None,
        lockedLabel=" (in use by master)",
    ):
        super(DeleteVersionsWindow, self).__init__(parent)

        self.core = core
        self.product = product
        self.versions = versions
        self.lockedVersions = set(lockedVersions or [])
        self.message = message
        #what a version is made of depends on the caller (product folder, scenefile, ...)
        self.deleteFunc = deleteFunc or deleteProductVersion
        self.lockedLabel = lockedLabel
        #filled in by deleteSelected(), the caller reads it after exec_()
        self.deletedVersions = []

        self.setWindowTitle("Delete versions")
        self.resize(620, 400)

        project_path = self.core.projectPath.replace("\\", "/").rstrip("/")
        self.setWindowIcon(QIcon(f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Integration/ui/daisy_logo.png"))

        self.setupUi()
        self.connectEvents()
        self.fillVersions()

    @err_catcher(name=__name__)
    def setupUi(self):

        #-----------------------------------------------------------------------------------#
        # Header, version table and the two action buttons                                  #
        #-----------------------------------------------------------------------------------#

        self.lo_main = QVBoxLayout(self)

        self.l_header = QLabel(
            self.message
            or "'%s' has %s versions.\nSelect the versions to delete:"
            % (self.product, len(self.versions))
        )
        self.lo_main.addWidget(self.l_header)

        self.tw_versions = QTableWidget()
        self.tw_versions.setColumnCount(3)
        self.tw_versions.setHorizontalHeaderLabels(["Version", "Comment", "Date"])
        self.tw_versions.verticalHeader().setVisible(False)
        self.tw_versions.setSelectionMode(QAbstractItemView.NoSelection)
        self.tw_versions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_versions.horizontalHeader().setStretchLastSection(True)
        self.lo_main.addWidget(self.tw_versions)

        self.w_buttons = QWidget()
        self.lo_buttons = QHBoxLayout(self.w_buttons)
        self.lo_buttons.setContentsMargins(0, 0, 0, 0)
        self.lo_buttons.addStretch()
        self.b_delete = QPushButton("Delete selected")
        self.b_close = QPushButton("Close")
        self.lo_buttons.addWidget(self.b_delete)
        self.lo_buttons.addWidget(self.b_close)
        self.lo_main.addWidget(self.w_buttons)

    @err_catcher(name=__name__)
    def connectEvents(self):

        #-----------------------------------------------------------------------------------#
        # Wire up the dialog buttons                                                        #
        #-----------------------------------------------------------------------------------#

        self.b_delete.clicked.connect(self.deleteSelected)
        self.b_close.clicked.connect(self.reject)

    @err_catcher(name=__name__)
    def fillVersions(self):

        #-----------------------------------------------------------------------------------#
        # One row per version, in the order they were given, all unchecked                  #
        #-----------------------------------------------------------------------------------#

        self.tw_versions.setRowCount(len(self.versions))
        for row, version in enumerate(self.versions):
            versionName = version.get("version")
            isLocked = versionName in self.lockedVersions
            info = getVersionInfo(self.core, version.get("path"))

            label = versionName + (self.lockedLabel if isLocked else "")
            item = QTableWidgetItem(label)
            item.setData(Qt.UserRole, version)
            if isLocked:
                item.setFlags(Qt.ItemIsEnabled)
            else:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)

            self.tw_versions.setItem(row, 0, item)
            self.tw_versions.setItem(row, 1, QTableWidgetItem(info.get("comment", "")))
            self.tw_versions.setItem(row, 2, QTableWidgetItem(info.get("date", "")))

        self.tw_versions.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def getCheckedVersions(self):

        #-----------------------------------------------------------------------------------#
        # The version dicts whose row is ticked                                             #
        #-----------------------------------------------------------------------------------#

        versions = []
        for row in range(self.tw_versions.rowCount()):
            item = self.tw_versions.item(row, 0)
            if item and item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                versions.append(item.data(Qt.UserRole))
        return versions

    @err_catcher(name=__name__)
    def deleteVersion(self, version):

        #-----------------------------------------------------------------------------------#
        # Hand the version over to whoever knows how to remove it from disk                 #
        # Returns the error messages, empty when it went through                            #
        #-----------------------------------------------------------------------------------#

        return self.deleteFunc(self.core, version) or []

    @err_catcher(name=__name__)
    def deleteSelected(self):

        #-----------------------------------------------------------------------------------#
        # Confirm, then remove the ticked versions from disk                                #
        #-----------------------------------------------------------------------------------#

        versions = self.getCheckedVersions()
        if not versions:
            self.core.popup("No version selected.", title="Delete versions", severity="warning")
            return

        names = ", ".join(v.get("version") for v in versions)
        result = self.core.popupQuestion(
            "Permanently delete %s version(s)?\n\n%s\n\nThis cannot be undone."
            % (len(versions), names),
            title="Delete versions",
            buttons=["Delete", "Cancel"],
            default="Cancel",
        )
        if result != "Delete":
            return

        errors = []
        for version in versions:
            versionErrors = self.deleteVersion(version)
            errors.extend(versionErrors)
            if not versionErrors:
                self.deletedVersions.append(version.get("version"))

        if errors:
            self.core.popup(
                "Some versions could not be deleted:\n\n" + "\n".join(errors),
                title="Delete versions",
                severity="warning",
            )

        self.accept()


@err_catcher(name=__name__)
def openDeleteVersionsWindow(
    core,
    product,
    versions,
    lockedVersions=None,
    message="",
    parent=None,
    deleteFunc=None,
    lockedLabel=" (in use by master)",
):

    #-----------------------------------------------------------------------------------#
    # Open the window modally and return the names of the versions that were deleted    #
    #-----------------------------------------------------------------------------------#

    dlg = DeleteVersionsWindow(
        core,
        product,
        versions,
        lockedVersions=lockedVersions,
        message=message,
        parent=parent,
        deleteFunc=deleteFunc,
        lockedLabel=lockedLabel,
    )
    core.parentWindow(dlg)
    dlg.exec_()
    return dlg.deletedVersions
