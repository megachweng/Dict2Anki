#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import time
import json
import sqlite3
import pickle
import os
import sys
from sys import platform
from os.path import expanduser
import traceback
# Anki
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip
# PyQT
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import *
reload(sys)
sys.setdefaultencoding('utf-8')
home = expanduser("~")
# detecting operating system
if platform == "linux" or platform == "linux2":
    pass
elif platform == "darwin":
    eudictDB = home + "/Library/Eudb_en/.study.dat"
    youdaoDB = home + "/Library/Containers/com.youdao.YoudaoDict/Data/Library/com.youdao.YoudaoDict/wordbook.db"
elif platform == "win32":
    eudictDB = home + "\AppData\Roaming\Francochinois\eudic\study.db"
    youdaoDB = home + "\AppData\Local\Yodao\DeskDict\WbData\megachweng\local"

class Window(QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.initComponent()
    def initComponent(self):
        self.resize(321, 389)
        self.groupBox = QGroupBox(self)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 301, 161))
        self.groupBox.setTitle("")
        self.layoutWidget = QWidget(self.groupBox)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 50, 291, 32))
        self.horizontalLayout_2 = QHBoxLayout(self.layoutWidget)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.downloadimage = QCheckBox(self.layoutWidget)
        self.horizontalLayout_2.addWidget(self.downloadimage)
        self.syncButton_2 = QPushButton(self.layoutWidget)
        self.horizontalLayout_2.addWidget(self.syncButton_2)
        self.layoutWidget1 = QWidget(self.groupBox)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 120, 281, 20))
        self.horizontalLayout_4 = QHBoxLayout(self.layoutWidget1)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.total = QProgressBar(self.layoutWidget1)
        self.total.setMaximum(2)
        self.total.setProperty("value", 0)
        self.horizontalLayout_4.addWidget(self.total)
        self.label_3 = QLabel(self.layoutWidget1)
        self.horizontalLayout_4.addWidget(self.label_3)
        self.layoutWidget2 = QWidget(self.groupBox)
        self.layoutWidget2.setGeometry(QtCore.QRect(10, 90, 281, 20))
        self.horizontalLayout_3 = QHBoxLayout(self.layoutWidget2)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar(self.layoutWidget2)
        self.progress.setProperty("value", 0)
        self.horizontalLayout_3.addWidget(self.progress)
        self.label_2 = QLabel(self.layoutWidget2)
        self.horizontalLayout_3.addWidget(self.label_2)
        self.label = QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(12, 14, 46, 21))
        self.comboBox = QComboBox(self.groupBox)
        self.comboBox.setGeometry(QtCore.QRect(62, 12, 161, 26))
        self.comboBox.setEditable(True)
        self.syncButton = QPushButton(self.groupBox)
        self.syncButton.setGeometry(QtCore.QRect(230, 10, 72, 32))
        self.debug = QPlainTextEdit(self)
        self.debug.setGeometry(QtCore.QRect(10, 180, 301, 192))
        self.debug.setStyleSheet("background:black;color:orange")

        self.downloadimage.setText("Download images")
        self.syncButton_2.setText("Show Details")
        self.label_3.setText("Total")
        self.label_2.setText("Term")
        self.label.setText("Sync to")
        self.syncButton.setText("Sync")

        self.show()  # shows the window

def runYoudaoPlugin():
    try:
        """menu item pressed; display window"""
        global __window
        __window = Window()
    except Exception, e:
        traceback.print_exc(file=open('error.log', 'w+'))



# create menu item
action = QAction("Import your Youdao WordList", mw)
mw.connect(action, SIGNAL("triggered()"), runYoudaoPlugin)
mw.form.menuTools.addAction(action)