import anki
from aqt import mw
from PyQt5.QtWidgets import QAction
from .addon.addonWindow import Window



def showWindow():
    window = Window(mw)
    window.exec_()

action = QAction("Dick2Anki...", mw)
action.triggered.connect(showWindow)
mw.form.menuTools.addAction(action)