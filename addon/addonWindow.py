import time
from aqt import mw
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot

from .ui import Ui_Dialog
from . import api
from . import dictionary
from . import cardManager
import json
from queue import Queue

__version__ = '5.0.0'
MODELNAME = 'Dict2Anki_NEW'


class Window(QDialog):
    _config = None
    dictionary = None
    api = None
    queryResults = Queue()
    dictionaryList = ['Eudict', 'YoudaoDict']
    threadPool = QThreadPool()
    threadPool.setMaxThreadCount(3)

    def __init__(self):
        super(Window, self).__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.updateUI()
        self.setWindowTitle(f'Dict2Anki-{__version__}')
        self.makeConnections()
        self.restoreConfig()
        self.show()

    @property
    def config(self):
        if not self._config:
            self._config = mw.addonManager.getConfig(__name__)
        return self._config

    def saveConfig(self):
        index = self.ui.dictionaryComboBox.currentIndex()
        self._config['active'] = index
        self._config['dictionaries'][index]['username'] = self.ui.usernameLineEdit.text()
        self._config['dictionaries'][index]['password'] = self.ui.passwordLineEdit.text()
        self._config['deck'] = self.ui.deckComboBox.currentText()
        self._config['image'] = self.ui.imageCheckBox.isChecked()
        self._config['sample'] = self.ui.sampleCheckBox.isChecked()
        self._config['BrEPron'] = self.ui.BrEPronCheckBox.isChecked()
        self._config['AmEPron'] = self.ui.AmEPronCheckBox.isChecked()
        self._config['BrEPhonetic'] = self.ui.BrEPhoneticCheckBox.isChecked()
        self._config['AmEPhonetic'] = self.ui.AmEPhoneticCheckBox.isChecked()
        self.log(f'save configuration:\n{self._config}')
        mw.addonManager.writeConfig(__name__, self._config)

    def updateUI(self):
        self.ui.deckComboBox.addItems([deck['name'] for deck in mw.col.decks.all()])

    def makeConnections(self):
        self.ui.syncPushButton.clicked.connect(self.btnOnclick)

    def updateProgressBar(self):
        if self.ui.progressBar.value() < self.ui.progressBar.maximum():
            self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)

    def log(self, info):
        self.ui.logPlainTextEdit.appendPlainText(f'{time.strftime("%Y-%m-%d %H.%M.%S")} :\n{info} \n')

    def errorHandler(self, e):
        self.log(f"Error:{e}")

    def restoreConfig(self):
        if self.config:
            index = self.config['active']
            self.ui.dictionaryComboBox.setCurrentIndex(index)
            self.ui.usernameLineEdit.setText(self.config['dictionaries'][index]['username'])
            self.ui.passwordLineEdit.setText(self.config['dictionaries'][index]['password'])
            self.ui.imageCheckBox.setCheckState(self.config['image'])
            self.ui.sampleCheckBox.setChecked(self.config['sample']),
            self.ui.BrEPronCheckBox.setChecked(self.config['BrEPron'])
            self.ui.AmEPronCheckBox.setChecked(self.config['AmEPron'])
            self.ui.BrEPhoneticCheckBox.setChecked(self.config['BrEPhonetic'])
            self.ui.AmEPhoneticCheckBox.setChecked(self.config['AmEPhonetic'])
            if self.config['deck'] is not None:
                self.ui.deckComboBox.setCurrentText(self.config['deck'])

    def btnOnclick(self):
        self.ui.syncPushButton.setEnabled(False)
        # create card Model
        cardManager.createDeck(self.ui.deckComboBox.currentText(), MODELNAME)

        # Init dictionary instance by comboBox
        self.dictionary = getattr(dictionary, self.dictionaryList[self.ui.dictionaryComboBox.currentIndex()])
        self.log(f'Dictionary: {self.dictionary.__name__}')
        remoteWordList = self._getRemoteWordList(self.ui.usernameLineEdit.text(), self.ui.passwordLineEdit.text())

        # compare local and remote word list
        needToAddWords = self._compare(remoteWordList)
        self.log(f'需要查询的单词({len(needToAddWords)}):{needToAddWords}')

        # start query words
        queryResults = self._query(needToAddWords)

        # save to Anki
        self._saveToAnki(queryResults)
        self.ui.syncPushButton.setEnabled(True)

    def _getRemoteWordList(self, username, password):
        dicIndex = self.ui.dictionaryComboBox.currentIndex()
        cookie = self.config['dictionaries'][dicIndex]['cookie']
        if [username, password] != [self.config['dictionaries'][dicIndex]['username'], self.config['dictionaries'][dicIndex]['password']]:
            self.log('login...')
            cookie = None

        dictThread = self.dictionary(username, password, cookie)
        dictThread.signal.log.connect(self.log)
        dictThread.signal.updateProgress.connect(self.updateProgressBar)
        dictThread.signal.setTotalTasks.connect(self.ui.progressBar.setMaximum)
        dictThread.signal.exceptionOccurred.connect(self.errorHandler)
        dictThread.start()
        while not dictThread.isFinished():
            mw.app.processEvents()
            dictThread.wait(300)
        cookie = dictThread.cookie
        remoteWordList = dictThread.remoteWordList
        if cookie:
            self._config['dictionaries'][dicIndex]['cookie'] = cookie
            self.saveConfig()
        else:
            self.log('Login Failed')
            self.ui.syncPushButton.setEnabled(True)
        return remoteWordList

    def _compare(self, remoteWordList):
        localWordList = cardManager.getDeckWordList(
            deckName=self.ui.deckComboBox.currentText(),
        )
        local = set(localWordList)
        remote = set(remoteWordList)
        self.log(f'local wordlist: \n{json.dumps(list(local), indent=4)}')
        self.log(f'remote wordlist: \n{json.dumps(list(remote), indent=4)}')
        needToDeleteWords = local - remote
        needToDeleteIds = cardManager.getNoteByWord(
            words=needToDeleteWords,
            deckName=self.ui.deckComboBox.currentText()
        )
        needToAddWords = remote - local
        if needToDeleteWords:
            self.log(f'Preparing delete:{json.dumps(list(needToDeleteWords), indent=4)}')
            self.log(f'Preparing delete note IDs:\n {needToDeleteIds}')
            mw.col.remNotes(needToDeleteIds)
            mw.col.reset()
            mw.reset()
            self.log(f'Deleted')

        return needToAddWords

    def _query(self, words):

        queryThread = api.YoudaoAPI(api.YoudaoParser, words)
        queryThread.signal.log.connect(self.log)
        queryThread.signal.updateProgress.connect(self.updateProgressBar)
        queryThread.signal.setTotalTasks.connect(self.ui.progressBar.setMaximum)
        queryThread.signal.exceptionOccurred.connect(self.errorHandler)
        queryThread.start()

        while not queryThread.isFinished():
            mw.app.processEvents()

        self.log(f"查询完毕!成功({queryThread.queryResults.qsize()})失败:({queryThread.failedQueries.qsize()})")
        return queryThread.queryResults

    def _saveToAnki(self, results=None):
        options = {
            'image': self.ui.imageCheckBox.isChecked(),
            'samples': self.ui.sampleCheckBox.isChecked(),
            'BrEPron': self.ui.BrEPronCheckBox.isChecked(),
            'AmEPron': self.ui.AmEPronCheckBox.isChecked(),
            'BrEPhonetic': self.ui.BrEPhoneticCheckBox.isChecked(),
            'AmEPhonetic': self.ui.AmEPhoneticCheckBox.isChecked(),
        }

        while results.qsize() > 0:
            term = results.get()
            note = cardManager.processNote(term, options)
            mw.col.addNote(note)
        self.log('添加完毕')
        mw.col.reset()
        mw.reset()


if __name__ == '__main__':
    app = QApplication([])
    w = Window()
    w.exec()
