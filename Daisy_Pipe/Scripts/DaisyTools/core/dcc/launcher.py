def get_dcc():
    try:
        import hou
        return "houdini"
    except ImportError:
        pass
    try:
        import maya.cmds as cmds
        return "maya"
    except ImportError:
        pass
    return "standalone"

def get_qt():

    dcc = get_dcc()

    if dcc == "houdini":
        from PySide2 import QtWidgets, QtCore, QtGui
    elif dcc == "maya":
        try:
            from PySide2 import QtWidgets, QtCore, QtGui
        except:
            from PySide6 import QtWidgets, QtCore, QtGui
    else:
        try:
            from PySide2 import QtWidgets, QtCore, QtGui
        except ImportError:
            from PyQt5 import QtWidgets, QtCore, QtGui
    return QtWidgets, QtCore, QtGui

def get_main_window():
    dcc = get_dcc()

    if dcc == "houdini":
        import hou
        return hou.ui.mainQtWindow()

    elif dcc == "maya":
        try:
            from PySide2 import QtWidgets
            import shiboken2
        except ImportError:
            from PySide6 import QtWidgets
            import shiboken6 as shiboken2
        from maya import OpenMayaUI
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)

    return None