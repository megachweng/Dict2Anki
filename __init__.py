from aqt import mw
from .addon.mainWindow import MainWindow
from PyQt5.QtWidgets import QAction


def showWindow():
    w = MainWindow()
    w.exec()


action = QAction("Dick2Anki...", mw)
action.triggered.connect(showWindow)
mw.form.menuTools.addAction(action)
