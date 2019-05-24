import sys

from aqt import mw
from .addon.mainWindow import MainWindow
from PyQt5.QtWidgets import QAction
import logging

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


def showWindow():
    w = MainWindow()
    w.exec()


action = QAction("Dick2Anki...", mw)
action.triggered.connect(showWindow)
mw.form.menuTools.addAction(action)
