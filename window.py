# -*- coding: utf-8 -*-
import json
import time
import ssl
import sqlite3
import hashlib
import cookielib
import urllib
import urllib2
import traceback
import pickle
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip

from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QWidget
from worker import Eudict, Youdao, imageDownloader, pronunciationDownloader
from API import LookupThread
from note import Note

ssl._create_default_https_context = ssl._create_unverified_context

class Window(QWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.__initDB()
        self.__setDefaultUI()
        self.__updateUI()
        self.dictThread = None
        self.LookupThread = None
        self.imageDownloadThread = None
        self.pronunciationDownloadThread = None
        self.show()

    def seek(self,something):
        self.debug.appendPlainText(something)

    def __setDefaultUI(self):
        self.resize(583, 381)
        self.setWindowTitle("Dict2Anki 3.0")
        self.container = QtGui.QTabWidget(self)
        self.container.setGeometry(QtCore.QRect(20, 10, 541, 351))

        # Sync tab
        self.syncTab = QtGui.QWidget()
        self.syncButton = QtGui.QPushButton(self.syncTab)
        self.syncButton.setText("Sync")
        self.syncButton.setGeometry(QtCore.QRect(410, 18, 111, 114))
        self.syncButton.clicked.connect(self.__startSync)
        self.progressBar = QtGui.QProgressBar(self.syncTab)
        self.progressBar.setGeometry(QtCore.QRect(20, 150, 491, 31))
        self.line = QtGui.QFrame(self.syncTab)
        self.line.setGeometry(QtCore.QRect(20, 130, 491, 31))
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.debug = QtGui.QPlainTextEdit(self.syncTab)
        self.debug.setGeometry(QtCore.QRect(20, 190, 491, 121))
        self.widget = QtGui.QWidget(self.syncTab)
        self.widget.setGeometry(QtCore.QRect(20, 9, 381, 131))
        self.syncTo = QtGui.QComboBox(self.widget)
        self.syncTo.setEditable(True)
        self.syncToLable = QtGui.QLabel(self.widget)
        self.syncToLable.setText("Sync to Deck")
        self.pronunciation = QtGui.QComboBox(self.widget)
        self.pronunciation.addItem("No Pronunciation")
        self.pronunciation.addItem("British Pronunciation")
        self.pronunciation.addItem("American Pronunciation")
        self.dictionary = QtGui.QComboBox(self.widget)
        self.dictionary.addItem("Eudict")
        self.dictionary.addItem("Youdao")
        self.dictionaryLable = QtGui.QLabel(self.widget)
        self.dictionaryLable.setText("Dictionary")
        self.saveImage = QtGui.QCheckBox(self.widget)
        self.saveImage.setText("Save Image")
        self.saveImage.setChecked(True)
        self.gridLayout_3 = QtGui.QGridLayout(self.widget)
        self.gridLayout_3.setMargin(0)
        self.gridLayout_3.setColumnStretch(1, 1)
        self.gridLayout_3.addWidget(self.syncTo, 0, 1, 1, 1)
        self.gridLayout_3.addWidget(self.syncToLable, 0, 0, 1, 1)
        self.gridLayout_3.addWidget(self.pronunciation, 2, 1, 1, 1)
        self.gridLayout_3.addWidget(self.dictionary, 1, 1, 1, 1)
        self.gridLayout_3.addWidget(self.dictionaryLable, 1, 0, 1, 1)
        self.gridLayout_3.addWidget(self.saveImage, 2, 0, 1, 1)
        self.container.addTab(self.syncTab, "Sync")

        # Account Tab
        self.accountTab = QtGui.QWidget()
        self.container.addTab(self.accountTab, "Account")
        self.eudictAccountSection = QtGui.QGroupBox(self.accountTab)
        self.eudictAccountSection.setTitle("Eudict")
        self.eudictAccountSection.setGeometry(QtCore.QRect(20, 0, 491, 141))
        self.widget1 = QtGui.QWidget(self.eudictAccountSection)
        self.widget1.setGeometry(QtCore.QRect(21, 29, 451, 91))
        self.eudictUsernameLabel = QtGui.QLabel(self.widget1)
        self.eudictUsernameLabel.setText("Username")
        self.eudictUsername = QtGui.QLineEdit(self.widget1)
        self.eudictPasswordLable = QtGui.QLabel(self.widget1)
        self.eudictPasswordLable.setText("Password")
        self.eudictPassword = QtGui.QLineEdit(self.widget1)
        self.eudictPassword.setEchoMode(QtGui.QLineEdit.PasswordEchoOnEdit)
        self.eudictRemember = QtGui.QCheckBox(self.widget1)
        self.eudictRemember.setText("Remember")
        self.eudictRemember.setChecked(True)
        self.eudcitLoginButton = QtGui.QPushButton(self.widget1)
        self.eudcitLoginButton.setText("Login")
        self.eudcitLoginButton.clicked.connect(self.__loginEudict)
        self.gridLayout = QtGui.QGridLayout(self.widget1)
        self.gridLayout.setMargin(0)
        self.gridLayout.addWidget(self.eudictUsernameLabel, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.eudictUsername, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.eudictPasswordLable, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.eudictPassword, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.eudictRemember, 1, 2, 1, 1)
        self.gridLayout.addWidget(self.eudcitLoginButton, 0, 2, 1, 1)

        self.youdaoAccountSection = QtGui.QGroupBox(self.accountTab)
        self.youdaoAccountSection.setTitle("Youdao")
        self.youdaoAccountSection.setGeometry(QtCore.QRect(20, 150, 491, 141))
        self.layoutWidget = QtGui.QWidget(self.youdaoAccountSection)
        self.layoutWidget.setGeometry(QtCore.QRect(21, 29, 451, 91))
        self.youdaoUsernameLable = QtGui.QLabel(self.layoutWidget)
        self.youdaoUsernameLable.setText("Username")
        self.youdaoUsername = QtGui.QLineEdit(self.layoutWidget)
        self.youdaoPasswordLable = QtGui.QLabel(self.layoutWidget)
        self.youdaoPasswordLable.setText("Password")
        self.youdaoPassword = QtGui.QLineEdit(self.layoutWidget)
        self.youdaoPassword.setEchoMode(QtGui.QLineEdit.PasswordEchoOnEdit)
        self.youdaoRemember = QtGui.QCheckBox(self.layoutWidget)
        self.youdaoRemember.setText("Remember")
        self.youdaoRemember.setChecked(True)
        self.youdaoLoginButton = QtGui.QPushButton(self.layoutWidget)
        self.youdaoLoginButton.setText("Login")
        self.youdaoLoginButton.clicked.connect(self.__loginYoudao)
        self.gridLayout_2 = QtGui.QGridLayout(self.layoutWidget)
        self.gridLayout_2.setMargin(0)
        self.gridLayout_2.addWidget(self.youdaoUsernameLable, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.youdaoUsername, 0, 1, 1, 1)
        self.gridLayout_2.addWidget(self.youdaoPasswordLable, 1, 0, 1, 1)
        self.gridLayout_2.addWidget(self.youdaoPassword, 1, 1, 1, 1)
        self.gridLayout_2.addWidget(self.youdaoRemember, 1, 2, 1, 1)
        self.gridLayout_2.addWidget(self.youdaoLoginButton, 0, 2, 1, 1)

        # History Tab
        self.historyTab = QtGui.QWidget()
        self.historyList = QtGui.QTableWidget(self.historyTab)
        self.historyList.setGeometry(QtCore.QRect(10, 10, 411, 301))
        self.historyList.setCornerButtonEnabled(False)
        self.historyList.setColumnCount(3)
        self.historyList.setRowCount(0)
        self.historyList.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem())
        self.historyList.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem())
        self.historyList.setHorizontalHeaderItem(2, QtGui.QTableWidgetItem())
        self.historyList.horizontalHeader().setVisible(True)
        self.historyList.horizontalHeader().setDefaultSectionSize(136)
        self.historyList.horizontalHeader().setHighlightSections(True)
        self.historyList.verticalHeader().setVisible(False)
        self.historyList.horizontalHeaderItem(0).setText("Sync Date")
        self.historyList.horizontalHeaderItem(1).setText("Dictionary")
        self.historyList.horizontalHeaderItem(2).setText("Deck")
        self.restoreButton = QtGui.QPushButton(self.historyTab)
        self.restoreButton.setText("Restore")
        self.restoreButton.setGeometry(QtCore.QRect(424, 10, 110, 32))
        self.deleteButton = QtGui.QPushButton(self.historyTab)
        self.deleteButton.setGeometry(QtCore.QRect(424, 50, 110, 32))
        self.deleteButton.setText("Delete")
        self.container.addTab(self.historyTab, "History")
        self.container.setCurrentIndex(self.container.indexOf(self.accountTab))

    def __initDB(self):
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        # cursor.execute('create table if not exists history (id INTEGER primary key, terms TEXT,time TEXT,mark TEXT,deckname TEXT)')
        cursor.execute('create table if not exists account (id INTEGER primary key, username TEXT,password TEXT,remember BOOL,dictionary INTEGER)')
        cursor.execute('create table if not exists sync_settings (id INTEGER primary key, syncto TEXT, dictionary INTEGER, saveimage BOOL, pronunciation INTEGER)')
        cursor.execute('create table if not exists history (id INTEGER primary key, terms TEXT,time TEXT,deck TEXT, dictionary INTEGER)')

        conn.commit()
        cursor.close()
        conn.close

    def __updateUI(self):
        def setAccountTab():
            conn = sqlite3.connect('Dict2Anki.db')
            cursor = conn.cursor()
            cursor.execute('select * from account where id=1')
            eudictAccount = cursor.fetchall()
            cursor.execute('select * from account where id=2')
            youdaoAccount = cursor.fetchall()
            conn.commit()
            cursor.close()
            conn.close()
            if eudictAccount:
                eudictUsername = eudictAccount[0][1]
                eudictPassword = eudictAccount[0][2]
                eudictRemember = eudictAccount[0][3]
                self.eudictUsername.setText(eudictUsername)
                self.eudictPassword.setText(eudictPassword)

            if youdaoAccount:
                youdaoUsername = youdaoAccount[0][1]
                youdaoPassword = youdaoAccount[0][2]
                youdaoRemember = youdaoAccount[0][3]
                self.youdaoUsername.setText(youdaoUsername)
                self.youdaoPassword.setText(youdaoPassword)
                self.youdaoRemember.setChecked(youdaoRemember)

        def setSyncTab():
            alldecks = mw.col.decks.allNames()[1:]
            for deckname in alldecks:
                self.syncTo.addItem(deckname)

            conn = sqlite3.connect('Dict2Anki.db')
            cursor = conn.cursor()
            cursor.execute('select * from sync_settings')
            values = cursor.fetchall()
            conn.commit()
            cursor.close()
            conn.close()
            if values:
                syncto = values[0][1]
                dictionary = values[0][2]
                saveimage = values[0][3]
                pronunciation = values[0][4]
                self.syncTo.setEditText(syncto)
                self.dictionary.setCurrentIndex(dictionary)
                self.saveImage.setChecked(saveimage)
                self.pronunciation.setCurrentIndex(pronunciation)

        def setHistoryTab():
            pass

        setAccountTab()
        setSyncTab()
        setHistoryTab()

    def __loginEudict(self):
        username = self.eudictUsername.text()
        password = self.eudictPassword.text()
        remember = self.eudictRemember.isChecked()
        self.eudcitLoginButton.setEnabled(False)
        self.eudcitLoginButton.setText("Logging...")
        if Eudict().login(username, password, remember):
            showInfo("Login Success!")
            self.eudcitLoginButton.setText("Logged")
            self.__saveAccount(username,password,remember,'eudict')
        else:
            self.eudcitLoginButton.setEnabled(True)
            self.eudcitLoginButton.setText("Login")
            showInfo("Login Failed!")

    def __loginYoudao(self):
        username = self.youdaoUsername.text()
        password = self.youdaoPassword.text()
        remember = self.youdaoRemember.isChecked()
        self.youdaoLoginButton.setEnabled(False)
        self.youdaoLoginButton.setText("Logging...")
        if Youdao().login(username, password, remember):
            showInfo("Login Success!")
            self.youdaoLoginButton.setText("Logged")
            self.__saveAccount(username,password,remember,'youdao')
        else:
            self.youdaoLoginButton.setEnabled(True)
            self.youdaoLoginButton.setText("Login")
            showInfo("Login Failed!")

    def __saveSyncSettings(self):
        syncTo = self.syncTo.currentText()
        dictionary = self.dictionary.currentIndex()
        saveImage = self.saveImage.isChecked()
        pronunciation = self.pronunciation.currentIndex()
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO sync_settings(id,syncto,dictionary,saveimage,pronunciation) VALUES(?,?,?,?,?)', (1,syncTo,dictionary,saveImage,pronunciation))
        conn.commit()
        conn.close()

    def __saveAccount(self,username,password,remember,dictionary):
        dictionary = dictionary=='youdao' and 2 or 1
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO account(id,username,password,remember,dictionary) VALUES(?,?,?,?,?)', (dictionary,username,password,remember,dictionary))
        conn.commit()
        conn.close()

    def updateProgressBar(self,current,total):
        self.progressBar.setMaximum(total)
        self.progressBar.setValue(current)

    def compareAndLookUp(self,currentWordList):
        lastWordList = self.__getLastWordList()
        data = {"deleted": [], "new": []}
        if lastWordList:
            self.seek("Last record exist & Do comparasion")
            for term in lastWordList:
                if term not in currentWordList:
                    data['deleted'].append(term)
            for term in currentWordList:
                if term not in lastWordList:
                    data['new'].append(term)
        else:
            self.seek("No record & First sync")
            data["new"] = currentWordList
            data['deleted'] = []

        self.data = data # for later usage

        self.seek("compare results:" + json.dumps(data))
        self.dictThread = None

        # start lookup
        if self.LookupThread:
            self.LookupThread.terminate()
        self.LookupThread = LookupThread(data['new'])
        self.connect(self.LookupThread,QtCore.SIGNAL('seek'),self.seek)
        self.connect(self.LookupThread,QtCore.SIGNAL('done'),self.__getAssets)
        self.connect(self.LookupThread,QtCore.SIGNAL('updateProgressBar'),self.updateProgressBar)
        self.LookupThread.start()
        self.seek('LookupThread started')
        # self.__saveWordList(currentWordList)

    def __getAssets(self,lookUpedTerms):
        imageUrls = [[term['term'],term['image']] for term in lookUpedTerms if term['image']]
        self.seek(json.dumps(imageUrls))


        if self.imageDownloadThread:
            self.imageDownloadThread.terminate()
        if self.pronunciationDownloadThread:
            self.pronunciationDownloadThread.terminate()

        if self.saveImage.isChecked():
            self.imageDownloadThread = imageDownloader(imageUrls)
            self.connect(self.imageDownloadThread,QtCore.SIGNAL('updateProgressBar'),self.updateProgressBar)
            self.connect(self.imageDownloadThread,QtCore.SIGNAL('seek'),self.seek)
            self.imageDownloadThread.start()

        if self.saveImage.isChecked():
            while not self.imageDownloadThread.isFinished():
                mw.app.processEvents()
                self.imageDownloadThread.wait(1)

        if self.pronunciation.currentIndex():
            self.pronunciationDownloadThread = pronunciationDownloader(self.data['new'],self.pronunciation.currentIndex())
            self.connect(self.pronunciationDownloadThread,QtCore.SIGNAL('updateProgressBar'),self.updateProgressBar)
            self.connect(self.pronunciationDownloadThread,QtCore.SIGNAL('seek'),self.seek)
            self.pronunciationDownloadThread.start()

        if self.pronunciation.currentIndex():
            while not self.pronunciationDownloadThread.isFinished():
                mw.app.processEvents()
                self.pronunciationDownloadThread.wait(1)

        self.__processNote(lookUpedTerms)


    def __processNote(self,lookUpedTerms):
        new = lookUpedTerms
        deleted = self.data['deleted']
        syncSettings = {'saveImage':self.saveImage.isChecked(),'pronunciation':self.pronunciation.currentIndex()}
        self.seek('lookup results: ' + json.dumps(new,indent=4))
        # self.seek(str(deleted))
        Note(new,deleted,syncSettings).processNote(self.syncTo.currentText())



    def __startSync(self):
        self.__getCurrentWordList()

    def __getCurrentWordList(self):

        if self.dictThread:
            self.dictThread.terminate()

        if self.dictionary.currentIndex():
            self.dictThread = Youdao()
        else:
            self.dictThread = Eudict()

        self.connect(self.dictThread,QtCore.SIGNAL('seek'),self.seek)
        self.connect(self.dictThread,QtCore.SIGNAL('updateProgressBar'),self.updateProgressBar)
        self.connect(self.dictThread,QtCore.SIGNAL('done'),self.compareAndLookUp) # compare current and last when thread done
        self.dictThread.start()

    def __getLastWordList(self):
        deck = self.syncTo.currentText()
        dictionary = self.dictionary.currentIndex()
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute("select terms from history where deck='%s' and dictionary = '%d' order by id desc limit 0, 1" % (deck, dictionary))
        values = cursor.fetchall()
        cursor.close()
        conn.close()
        if values:
            terms = pickle.loads(values[0][0])
            self.seek("last wordList:" + json.dumps(terms))
            return terms
        else:
            return False

    def __saveWordList(self, wordList):
        dictionary = self.dictionary.currentIndex()
        deck = self.syncTo.currentText()
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE into history (terms,time,deck,dictionary) values (?,?,?,?)', (pickle.dumps(wordList), time.strftime("%Y-%m-%d %H:%M:%S"), deck, dictionary))
        cursor.close()
        conn.commit()
        conn.close()
        self.seek("Current words Saved")
