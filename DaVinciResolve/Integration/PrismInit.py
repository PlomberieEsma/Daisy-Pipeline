import os, sys

PRISM_ROOT = os.getenv("PRISM_ROOT") or r"C:\Program Files\Prism2"
sys.path.append(os.path.join(PRISM_ROOT, "Scripts"))
# Si PySide n'est pas trouvé, ajoute ici le dossier PythonLibs de ton installation Prism

import PrismCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton

pcore = PrismCore.create(app="DaVinciResolve")

ACTIONS = [
    ("Project Browser",  lambda: pcore.projectBrowser()),
    ("Save BackUp Version", SaveBackUpVersion()),
    # ("Save and Comment", lambda: pcore.saveWithComment()),
]

qapp = QApplication.instance() or QApplication([])

win = QWidget()
win.setWindowTitle("Prism")
win.setWindowFlag(Qt.WindowStaysOnTopHint)
layout = QHBoxLayout(win)

for text, fn in ACTIONS:
    btn = QPushButton(text)
    btn.clicked.connect(lambda checked=False, fn=fn: fn())
    layout.addWidget(btn)

win.show()
qapp.exec_()

def SaveBackUpVersion():
    print("The Function Save BackUp Version is not coded yet")