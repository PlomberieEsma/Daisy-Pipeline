import sys

from DaisyTools.core.core import get_core
from DaisyTools.core.dcc.launcher import get_qt, get_main_window

QtWidgets, QtCore, QtGui = get_qt()


class AssetSetupWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        # resolve the DCC main window here rather than in the signature default,
        # so it isn't evaluated at import time (before Houdini's UI exists)
        if parent is None:
            parent = get_main_window()
        super(AssetSetupWindow, self).__init__(parent)

        self.setWindowTitle("Shot Setup")
        self.resize(480, 220)

        # change window icon - projectPath is the project root, so it resolves
        # the same way whether we're working on an asset or on a shot
        core = get_core()
        project_path = core.projectPath.replace("\\", "/").rstrip("/")
        self.setWindowIcon(QtGui.QIcon(f"{project_path}/00_Pipeline/Plugins/Daisy_Pipe/Integration/ui/daisy_logo.png"))

        # On macOS make the window a Tool to keep it on top of the DCC
        if sys.platform == "darwin":
            self.setWindowFlag(QtCore.Qt.Tool, True)

        # filled in by on_create(); the caller reads this after exec_()
        self.selected_departments = []

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.departments = ["SetDressing", "RLO", "FLO", "TLO","Animation", "FX", "CFX", "Lighting"]
        self.l_header = QtWidgets.QLabel("Setup Departments:")

        self.checkboxes = []
        for name in self.departments:
            cb = QtWidgets.QCheckBox(name)
            cb.setChecked(True)
            self.checkboxes.append(cb)

        self.btn_create = QtWidgets.QPushButton("Create")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.l_header)

        for cb in self.checkboxes:
            main_layout.addWidget(cb)

        main_layout.addStretch()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_create)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.btn_create.clicked.connect(self.on_create)
        self.btn_cancel.clicked.connect(self.reject)

    def on_create(self):
        self.selected_departments = [
            cb.text() for cb in self.checkboxes if cb.isChecked()
        ]
        self.accept()


if __name__ == "__main__":

    try:
        asset_setup_dialog.close()  # type: ignore
        asset_setup_dialog.deleteLater()  # type: ignore
    except Exception:
        pass

    asset_setup_dialog = AssetSetupWindow()
    # exec_() blocks until closed; on Accepted, read asset_setup_dialog.selected_departments
    asset_setup_dialog.show()
