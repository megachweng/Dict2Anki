import time
from aqt import mw
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot
from .ui import Ui_Dialog
from . import api
from . import dictionary
from . import cardManager
import json

__version__ = '5.0.0'
MODELNAME = 'Dict2Anki_NEW'


class Window(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.mw = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.updateUI()
        self.config = self.mw.addonManager.getConfig(__name__)
        self.setWindowTitle(f'Dict2Anki-{__version__}')
        self.makeConnections()
        self.threadPool = QThreadPool()
        self.threadPool.setMaxThreadCount(5)
        self.APIList = ['BingAPI', 'YoudaoAPI']
        self.dictionaryList = ['Eudict', 'Youdao']
        self.restoreConfig()
        self.show()
        self.queryResults = []

    def updateUI(self):
        self.ui.deckComboBox.addItems([deck['name'] for deck in mw.col.decks.all()])

    def makeConnections(self):
        self.ui.syncPushButton.clicked.connect(self.updateProgressBar)
        self.ui.syncPushButton.clicked.connect(self.btnOnclick)

    def updateProgressBar(self):
        if self.ui.progressBar.value() < self.ui.progressBar.maximum():
            self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)

    def log(self, info):
        self.ui.logPlainTextEdit.appendPlainText(f'{time.strftime("%Y-%m-%d %H.%M.%S")} :\n{info} \n')

    def exceptionHandler(self, e):
        self.log(e)
        # showInfo(e)
        self.threadPool.clear()
        self.ui.syncPushButton.setEnabled(True)

    def restoreConfig(self):
        self.log(f'Restore config: {self.config}')
        if self.config:
            self.ui.dictionaryComboBox.setCurrentIndex(self.config['dictionary'])
            self.ui.APIComboBox.setCurrentIndex(self.config['API'])
            self.ui.usernameLineEdit.setText(self.config['username'])
            self.ui.passwordLineEdit.setText(self.config['password'])
            self.ui.imageCheckBox.setCheckState(self.config['image'])
            self.ui.sampleCheckBox.setChecked(self.config['sample']),
            self.ui.BrEPronCheckBox.setChecked(self.config['BrEPron'])
            self.ui.AmEPronCheckBox.setChecked(self.config['AmEPron'])
            self.ui.BrEPhoneticCheckBox.setChecked(self.config['BrEPhonetic'])
            self.ui.AmEPhoneticCheckBox.setChecked(self.config['AmEPhonetic'])
            if self.config['deck'] is not None:
                self.ui.deckComboBox.setCurrentText(self.config['deck'])

    def __saveConfig(self):
        self.config = dict(
            dictionary=self.ui.dictionaryComboBox.currentIndex(),
            deck=self.ui.deckComboBox.currentText(),
            API=self.ui.APIComboBox.currentIndex(),
            username=self.ui.usernameLineEdit.text(),
            password=self.ui.passwordLineEdit.text(),
            image=self.ui.imageCheckBox.isChecked(),
            sample=self.ui.sampleCheckBox.isChecked(),
            BrEPron=self.ui.BrEPronCheckBox.isChecked(),
            AmEPron=self.ui.AmEPronCheckBox.isChecked(),
            BrEPhonetic=self.ui.BrEPhoneticCheckBox.isChecked(),
            AmEPhonetic=self.ui.AmEPhoneticCheckBox.isChecked(),
        )
        self.mw.addonManager.writeConfig(__name__, self.config)
        self.log(f'Save configuration: {self.config}')

    def btnOnclick(self):
        self.__saveConfig()
        # create card Model
        cardManager.createDeck(self.ui.deckComboBox.currentText(), MODELNAME)

        # Init api and dictionary instance
        self.api = getattr(api, self.APIList[self.ui.APIComboBox.currentIndex()])()
        self.dictionary = getattr(dictionary, self.dictionaryList[self.ui.dictionaryComboBox.currentIndex()])()
        self.log(f'Dictionary: {self.dictionary.__class__.__name__}')
        self.log(f'API: {self.api.__class__.__name__}')

        self.__login(self.ui.usernameLineEdit.text(), self.ui.passwordLineEdit.text())

    def __login(self, username, password):
        def __checkLogin(state):
            if not state:
                self.log('Login Failed')
                # showInfo('登录失败')
                self.ui.syncPushButton.setEnabled(True)
            else:
                self.log('Login Success')
                self.__getRemoteWordList()

        self.ui.syncPushButton.setEnabled(False)
        worker = Worker(self.dictionary.login, username, password)
        worker.signals.result.connect(__checkLogin)
        self.threadPool.start(worker)
        while self.threadPool.activeThreadCount():
            mw.app.processEvents()

    def __getRemoteWordList(self):
        self.log(f"Getting {self.dictionary.__class__.__name__} wordlist")
        worker = Worker(self.dictionary.getWordList)
        worker.signals.result.connect(self.__compare)
        self.threadPool.start(worker)
        while self.threadPool.activeThreadCount():
            mw.app.processEvents()

    def __compare(self, remoteWordList):
        # todo query word which is not in anki note
        localWordList = cardManager.getDeckWordList(
            deckName=self.ui.deckComboBox.currentText(),
            modelName=MODELNAME
        )
        local = set(localWordList)
        remote = set(remoteWordList)
        self.log(f'remote wordlist: \n{json.dumps(list(remote), indent=4)}')
        self.log(f'Local wordlist: \n{json.dumps(list(local), indent=4)}')
        needToDeleteWords = local - remote
        needToDeleteIds = cardManager.getNoteByWord(
            words=needToDeleteWords,
            modelName=MODELNAME,
            deckName=self.ui.deckComboBox.currentText()
        )
        needToAddWords = remote - local
        self.log(f'Preparing add:{json.dumps(list(needToAddWords), indent=4)}')
        self.log(f'Preparing delete:{json.dumps(list(needToDeleteWords) ,indent=4)}')
        self.log(f'Preparing delete note IDs:\n {needToDeleteIds}')
        mw.col.remNotes(needToDeleteIds)
        self.log(f'Deleted')

        self.__query(needToAddWords)

    def __query(self, words):
        # get query options

        def container(result):
            self.queryResults.append(result)

        self.ui.progressBar.setMaximum(len(words) - 1)
        self.ui.progressBar.reset()
        self.log(f'Preparing query:\n{json.dumps(list(words), indent=4)}')

        for word in words:
            worker = Worker(self.api.query, word, progressInfoPrefix='Querying: ')
            worker.signals.progress.connect(self.log)
            worker.signals.result.connect(container)
            worker.signals.finished.connect(self.updateProgressBar)
            self.threadPool.start(worker)

        while self.threadPool.activeThreadCount():
            mw.app.processEvents()

        self.log(f'Query results:\n{json.dumps(self.queryResults, indent=4, ensure_ascii=False)}')


class WorkerSignals(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)
    exception = pyqtSignal(object)
    progress = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.progressInfoPrefix = kwargs.pop('progressInfoPrefix', '')

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(f'{self.progressInfoPrefix}{self.args}')
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.exception.emit(e)
        finally:
            self.signals.finished.emit()


if __name__ == '__main__':
    app = QApplication([])
    w = Window()
    w.exec()
