import anki
from aqt import mw
from PyQt5.QtWidgets import QAction
from .addon.addonWindow import Window

WINDOW = None


def showWindow():
    global WINDOW
    WINDOW = Window()
    WINDOW.exec_()


action = QAction("Dick2Anki...", mw)
action.triggered.connect(showWindow)
mw.form.menuTools.addAction(action)
