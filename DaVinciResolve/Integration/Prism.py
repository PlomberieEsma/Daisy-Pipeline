import os, sys

PRISM_ROOT = os.getenv("PRISM_ROOT") or r"C:\Program Files\Prism2"
sys.path.append(os.path.join(PRISM_ROOT, "Scripts"))

import PrismCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from qtpy.QtGui import QIcon

pcore = PrismCore.create(app="DaVinciResolve", prismArgs=["noProjectBrowser"])
pcore.appPlugin.resolve = resolve

def callPlugin(methodName):
    plugin = getattr(pcore, "appPlugin", None)
    method = getattr(plugin, methodName, None) if plugin else None
    if method is None:
        print("Prism: '%s' is not implemented in the DaVinciResolve plugin." % methodName)
        return
    method()


ACTIONS = [
    ("Project Browser",         lambda: pcore.projectBrowser()),
    ("Open Scene",              lambda: callPlugin("OpenScene")),
    ("Save Version",            lambda: callPlugin("SaveVersion")),
    ("Save BackUp Version",     lambda: callPlugin("SaveBackUpVersion")),
    ("Add Shot",                lambda: callPlugin("AddShot")),
    ("Bake Current Shot",       lambda: callPlugin("BakeCurrentShot")),
    ("Modify Current Shot",     lambda: callPlugin("ModifyCurrentShot")),
    ("Apply Render Settings",   lambda: callPlugin("Render")),
]

qapp = QApplication.instance() or QApplication([])

win = QWidget()
win.setWindowTitle("Prism")
win.setWindowFlag(Qt.WindowStaysOnTopHint)
layout = QVBoxLayout(win)

for text, fn in ACTIONS:
    btn = QPushButton(text)
    btn.clicked.connect(lambda checked=False, fn=fn: fn())
    layout.addWidget(btn)

win.setFixedWidth(200)
iconPath = os.path.join(
    pcore.projectPath,
    "00_Pipeline", "Plugins", "DaVinciResolve", "Resources", "daisy_logo.png"
)
iconPath = os.path.normpath(iconPath)
if os.path.isfile(iconPath):
    win.setWindowIcon(QIcon(iconPath))
else:
    print("Prism: icône introuvable : %s" % iconPath)

win.show()
qapp.exec()