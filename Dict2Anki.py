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
        self.thread = None

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
        self.deckList = QComboBox(self.groupBox)
        self.deckList.setGeometry(QtCore.QRect(62, 12, 161, 26))
        self.deckList.setEditable(True)
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
        self.syncButton.clicked.connect(self.sync)

        self.getDeckNames()
        self.initDB()
        self.show()  # shows the window

    def initDB(self):
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute('create table if not exists history (id INTEGER primary key, terms TEXT,time TEXT,deckname TEXT)')
        cursor.execute('create table if not exists settings (id INTEGER primary key,deckname TEXT, downloadImage INTEGER)')
        cursor.close()
        conn.commit()
        conn.close()

    def getDeckNames(self):
        t = self.deckList.currentText()
        self.deckList.clear()
        alldecks = mw.col.decks.allNames()
        alldecks.remove('Default')
        for deckname in alldecks:
            self.deckList.addItem(deckname)
        if t:
            self.deckList.setEditText(t)
        self.debug.appendPlainText('Get Deck Names list')

    def sync(self):
        self.debug.appendPlainText("Click Sync")
        current = self.getCurrent()
        last = self.getLast()
        comparedTerms = self.compare(current, last)
        # stop the previous thread first
        if self.thread is not None:
            self.thread.terminate()
        # download the data!
        self.thread = lookUp(self, comparedTerms['new'])
        self.thread.start()
        while not self.thread.isFinished():
            mw.app.processEvents()

        self.thread = imageDownloader(self, self.thread.results['imageUrls'])
        self.thread.start()
        self.saveCurrent(current)

    def getCurrent(self):
        conn = sqlite3.connect(eudictDB)
        cursor = conn.cursor()
        cursor.execute('SELECT word FROM cus_studyrate WHERE deleted = 0')
        values = cursor.fetchall()
        conn.commit()
        conn.close()
        values = sum(map(list, values), [])
        self.debug.appendPlainText("Got current terms")
        return values

    def saveCurrent(self, current):
        deckname = self.deckList.currentText()
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute('insert OR IGNORE into history (terms,time,deckname) values (?,?,?)', (pickle.dumps(current), time.strftime("%Y-%m-%d %H:%M:%S"), deckname))
        cursor.close()
        conn.commit()
        conn.close()
        self.debug.appendPlainText("Current words Saved")

    def getLast(self):
        deckname = self.deckList.currentText()
        conn = sqlite3.connect('Dict2Anki.db')
        cursor = conn.cursor()
        cursor.execute("select * from history where deckname='%s'order by id desc limit 0, 1" % deckname)
        values = cursor.fetchall()
        cursor.close()
        conn.close()
        self.debug.appendPlainText("Got last terms")
        # values[number of raw][0->id,1->terms,2->time]
        if values:
            terms = pickle.loads(values[0][1])
            return terms
        else:
            return False

    def compare(self, current, last):
        data = {"deleted": [], "new": []}
        if last:
            self.debug.appendPlainText("Last record exist & Do comparasion")
            for term in last:
                if term not in current:
                    data['deleted'].append(term)

            for term in current:
                if term not in last:
                    data['new'].append(term)
            self.debug.appendPlainText(json.dumps(data, indent=4))
        else:
            self.debug.appendPlainText("First sync")
            data["new"] = current

        return data


class lookUp(QThread):
    """thread that lookup terms from public API"""

    def __init__(self, window, new):
        super(lookUp, self).__init__()
        self.window = window
        self.results = {"lookUpedTerms": [], "imageUrls": []}
        self.new = new

    def run(self):
        self.window.debug.appendPlainText("looking up thread")
        for term in self.new:
            self.window.debug.appendPlainText("looking up: " + term)
            r = self.publicAPI(term)

    def publicAPI(self, q):
        query = urllib.urlencode({"q": q})
        f = urllib2.urlopen("https://dict.youdao.com/jsonapi?{}&dicts=%7b%22count%22%3a+99%2c%22dicts%22%3a+%5b%5b%22ec%22%2c%22phrs%22%2c%22pic_dict%22%5d%2c%5b%22web_trans%22%5d%2c%5b%22fanyi%22%5d%2c%5b%22blng_sents_part%22%5d%5d%7d".format(query))
        r = f.read()
        json_result = json.loads(r)
        try:
            explains = json_result["ec"]["word"][0]["trs"][0]["tr"][0]["l"]["i"][0]
        except:
            try:
                explains = json_result["web_trans"]["web-translation"][0]["trans"][0]["value"]
            except:
                try:
                    explains = json_result["fanyi"]["tran"]
                except:
                    explains = None

        try:
            uk_phonetic = json_result["ec"]["word"][0]["ukphone"]
        except:
            try:
                uk_phonetic = json_result["simple"]["word"][0]["ukphone"]
            except:
                try:
                    uk_phonetic = json_result["ec"]["word"][0]["phone"]
                except:
                    uk_phonetic = None

        try:
            us_phonetic = json_result["ec"]["word"][0]["usphone"]
        except:
            try:
                us_phonetic = json_result["simple"]["word"][0]["usphone"]
            except:
                try:
                    us_phonetic = json_result["ec"]["word"][0]["phone"]
                except:
                    us_phonetic = None
        try:
            phrases = []
            phrase_explains = []
            json_phrases = json_result["phrs"]["phrs"]
            for value in json_phrases:
                phrases.append(value["phr"]["headword"]["l"]["i"])
                phrase_explains.append(value["phr"]["trs"][0]["tr"]["l"]["i"])
        except:
            phrases = ["No phrase"]
            phrase_explains = ["No phrase definition"]

        try:
            sentences = []
            sentences_explains = []
            json_sentences = json_result["blng_sents_part"]["sentence-pair"]
            for value in json_sentences:
                sentences.append(value["sentence-eng"])
                sentences_explains.append(value["sentence-translation"])
        except:
            sentences = [None]
            sentences_explains = [None]
        # window.progress.setValue(window.progress.value() + 1)

        try:
            img = json_result["pic_dict"]["pic"][0]["image"] + "&w=150"
            if self.window.downloadimage.isChecked():
                self.results['imageUrls'].append([img, q + ".jpg"])
                img = q
        except:
            img = None

        lookUpedTerms = {
            "term": q,
            "uk_phonetic": uk_phonetic,
            "us_phonetic": us_phonetic,
            "definition": explains,
            "phrases": phrases[:3],
            "phrase_explains": phrase_explains[:3],
            "sentences": sentences[:3],
            "sentences_explains": sentences_explains[:3],
            "image": img
        }
        self.results['lookUpedTerms'].append(lookUpedTerms)


class imageDownloader(QThread):
    """thread that download images of terms"""

    def __init__(self, window, imageUrls):
        super(imageDownloader, self).__init__()
        self.window = window
        self.imageUrls = imageUrls

    def run(self):
        self.window.debug.appendPlainText("Thread image downloading started")

        for imageUrl in self.imageUrls:
            self.window.debug.appendPlainText("Download image of " + imageUrl[1])
            urllib.urlretrieve(imageUrl[0], "Deck2Anki/" + imageUrl[1] + ".jpg")
        # "Dict2Anki/" + q + ".jpg"


def runYoudaoPlugin():
    try:
        """menu item pressed; display window"""
        global __window
        __window = Window()
    except Exception, e:
        traceback.print_exc(file=open('error.log', 'w+'))

# create menu item
action = QAction("Import your WordList", mw)
mw.connect(action, SIGNAL("triggered()"), runYoudaoPlugin)
mw.form.menuTools.addAction(action)
