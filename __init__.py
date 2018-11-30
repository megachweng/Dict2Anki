from aqt import mw
from PyQt5.QtWidgets import QAction
from .src.addonWindow import Window

_window = None


def showWindow():
    global _window
    _window = Window()


action = QAction("Dick2Anki...", mw)
action.triggered.connect(showWindow)
mw.form.menuTools.addAction(action)
