from copy import deepcopy

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QThread, pyqtSlot
from aqt import mw
from aqt.utils import askUser, showCritical, showInfo, tooltip, openLink
from .ui import Ui_Form
from . import cardManager
from . import dictionary
from . import api
from .notifier import Version
import time
import json

__VERSION__ = 'v5.0.2'
MODELNAME = 'Dict2Anki_NEW'
DICTIONARYLIST = ['Youdao', 'Eudict']


class Window(QWidget):
    _config = None
    hasStarted = False

    def __init__(self):
        super(Window, self).__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowTitle(f'Dict2Anki-{__VERSION__}')
        self.makeConnections()
        self.updateUI()
        self.restoreConfig()
        self.threadList = []
        self.versionCheckingThread = None
        self.checkVersion()
        self.show()

    def checkVersion(self):

        @pyqtSlot(object, object)
        def haveNewVersion(version, change_log):
            if askUser(f'有新版本:{version}是否更新？\n\n{change_log.strip()}'):
                openLink('https://github.com/megachweng/Dict2Anki/releases')

        self.versionCheckingThread = Version(__VERSION__)
        self.versionCheckingThread.hasNewVersion.connect(haveNewVersion)
        self.versionCheckingThread.log.connect(self.log)
        self.versionCheckingThread.start()

    @property
    def config(self):
        if not self._config:
            self._config = mw.addonManager.getConfig(__name__)
        return self._config

    def saveConfig(self):
        if not self.ui.deckComboBox.currentText():
            self.log('deck为空')
            showCritical('Deck不能为空')
            return False
        elif not self.ui.username.text() or not self.ui.password.text():
            self.log('用户名或密码为空')
            showCritical('未登录')
            self.ui.tabWidget.setCurrentIndex(1)
            return False

        index = self.ui.dictionaryComboBox.currentIndex()
        self._config['active'] = index
        self._config['dictionaries'][index]['username'] = self.ui.username.text()
        self._config['dictionaries'][index]['password'] = self.ui.password.text()
        self._config['deck'] = self.ui.deckComboBox.currentText()
        self._config['image'] = self.ui.imageCheckBox.isChecked()
        self._config['sample'] = self.ui.samplesCheckBox.isChecked()
        self._config['BrEPron'] = self.ui.BrEPronCheckBox.isChecked()
        self._config['AmEPron'] = self.ui.AmEPronCheckBox.isChecked()
        self._config['BrEPhonetic'] = self.ui.BrEPhoneticCheckBox.isChecked()
        self._config['AmEPhonetic'] = self.ui.AmEPhoneticCheckBox.isChecked()
        guardConfig = deepcopy(self._config)
        for i in range(len(guardConfig['dictionaries'])):
            guardConfig['dictionaries'][i]['username'] = '*******'
            guardConfig['dictionaries'][i]['password'] = '*******'
            guardConfig['dictionaries'][i]['cookie'] = '*******'
        self.log(f'保存配置项:\n{json.dumps(guardConfig, indent=4)}')
        mw.addonManager.writeConfig(__name__, self._config)
        return True

    def restoreConfig(self):
        if self.config:
            index = self.config['active']
            self.ui.dictionaryComboBox.setCurrentIndex(index)
            self.ui.username.setText(self.config['dictionaries'][index]['username'])
            self.ui.password.setText(self.config['dictionaries'][index]['password'])
            self.ui.imageCheckBox.setCheckState(self.config['image'])
            self.ui.samplesCheckBox.setChecked(self.config['sample']),
            self.ui.BrEPronCheckBox.setChecked(self.config['BrEPron'])
            self.ui.AmEPronCheckBox.setChecked(self.config['AmEPron'])
            self.ui.BrEPhoneticCheckBox.setChecked(self.config['BrEPhonetic'])
            self.ui.AmEPhoneticCheckBox.setChecked(self.config['AmEPhonetic'])
            if self.config['deck'] is not None:
                self.ui.deckComboBox.setCurrentText(self.config['deck'])

    @pyqtSlot(str)
    def log(self, message):
        self.ui.logBox.appendPlainText(f'{time.strftime("%Y-%m-%d %H.%M.%S")} :\n{message} \n')

    def makeConnections(self):

        self.ui.startSyncBtn.clicked.connect(self.OnClick)
        self.ui.dictionaryComboBox.currentIndexChanged.connect(self.changeCredential)

    def updateUI(self):
        self.ui.deckComboBox.addItems([deck['name'] for deck in mw.col.decks.all()])
        self.ui.dictionaryComboBox.addItems(DICTIONARYLIST)

    @pyqtSlot(int)
    def changeCredential(self, index):
        username = self.config['dictionaries'][index]['username']
        password = self.config['dictionaries'][index]['password']
        self.ui.username.setText(username)
        self.ui.password.setText(password)
        self.ui.currentDictionaryLable.setText('当前选择词典：' + self.ui.dictionaryComboBox.currentText())

    @pyqtSlot(object)
    def updateCookie(self, cookie):
        self._config['dictionaries'][self.ui.dictionaryComboBox.currentIndex()]['cookie'] = cookie
        self.saveConfig()

    @pyqtSlot()
    def updateProgress(self):
        if self.ui.progressBar.value() < self.ui.progressBar.maximum():
            self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)

    @pyqtSlot()
    def OnClick(self):
        self.log('开始同步')
        self.log('选择词典' + self.ui.dictionaryComboBox.currentText())
        if not self.saveConfig():
            return
        self.ui.startSyncBtn.setEnabled(False)
        cardManager.createDeck(self.ui.deckComboBox.currentText(), MODELNAME)
        dictIndex = self.ui.dictionaryComboBox.currentIndex()
        dictConfig = self.config['dictionaries'][dictIndex]

        credential = (
            self.ui.username.text(),
            self.ui.password.text(),
            None if (self.ui.username.text() != dictConfig['username']
                     or self.ui.password.text() != dictConfig['password'])
            else dictConfig['cookie']
        )

        dictWorker = getattr(dictionary, DICTIONARYLIST[self.ui.dictionaryComboBox.currentIndex()])(*credential)
        dictWorkerThread = QThread()
        self.threadList.append((dictWorker, dictWorkerThread))
        dictWorkerThread.started.connect(dictWorker.run)
        dictWorker.SIG.progress.connect(self.updateProgress)
        dictWorker.SIG.totalTasks.connect(self.ui.progressBar.setMaximum)
        dictWorker.SIG.wordsReady.connect(self.query)
        dictWorker.SIG.log.connect(self.log)
        dictWorker.SIG.saveCookie.connect(self.updateCookie)
        dictWorker.moveToThread(dictWorkerThread)
        dictWorkerThread.start()

    @pyqtSlot(object)
    def query(self, remoteWords):
        self.log(f"远程单词本:{remoteWords}")
        _, t = self.threadList[0]
        while not t.isFinished():
            t.wait(1)
            t.quit()
            mw.app.processEvents()

        needToQueryWords = self.compare(remoteWords)

        queryThread = QThread()
        queryWorker = api.YoudaoAPI(needToQueryWords, api.YoudaoParser)
        self.threadList.append((queryWorker, queryThread))
        queryWorker.SIG.progress.connect(self.updateProgress)
        queryWorker.SIG.totalTasks.connect(self.ui.progressBar.setMaximum)
        queryWorker.SIG.wordsReady.connect(self.addNote)
        queryWorker.SIG.log.connect(self.log)
        queryWorker.moveToThread(queryThread)
        queryThread.started.connect(queryWorker.run)
        queryThread.start()

    def compare(self, remoteWordList):
        localWordList = cardManager.getDeckWordList(
            deckName=self.ui.deckComboBox.currentText(),
        )
        local = set(localWordList)
        remote = set(remoteWordList)

        needToAddWords = remote - local
        needToDeleteWords = local - remote
        needToDeleteIds = cardManager.getNoteByWord(
            words=needToDeleteWords,
            deckName=self.ui.deckComboBox.currentText()
        )

        if needToDeleteWords and askUser(
                f'远程单词({len(needToDeleteWords)}个):\n{", ".join(list(needToDeleteWords)[:3])}...已经删除，\n是否删除Anki相应卡片？',
                title='Dict2Anki',
                parent=self
        ):
            self.log(f'准备删除:\n{list(needToDeleteWords)}')
            self.log(f'卡片 Ids:\n{needToDeleteIds}')
            mw.col.remNotes(needToDeleteIds)
            mw.col.reset()
            mw.reset()
            self.log(f'删除成功。')
        if needToAddWords:
            self.log(f'准备查询:{list(needToAddWords)}')
        else:
            self.log("没有需要查询的单词。")

        return needToAddWords

    @pyqtSlot(object)
    def addNote(self, words):
        if words:
            self.log(f'查询结果:{words}')
        _, t = self.threadList[1]
        while not t.isFinished():
            t.wait(1)
            t.quit()
            mw.app.processEvents()

        options = {
            'image': self.ui.imageCheckBox.isChecked(),
            'samples': self.ui.samplesCheckBox.isChecked(),
            'BrEPron': self.ui.BrEPronCheckBox.isChecked(),
            'AmEPron': self.ui.AmEPronCheckBox.isChecked(),
            'BrEPhonetic': self.ui.BrEPhoneticCheckBox.isChecked(),
            'AmEPhonetic': self.ui.AmEPhoneticCheckBox.isChecked(),
        }
        audios = []
        for word in words:
            self.log(f'添加卡片:{word["term"]}')
            note, BrEPron, AmEPron = cardManager.processNote(word, options)
            mw.col.addNote(note)
            for pron in [BrEPron, AmEPron]:
                if pron[1]:  # 只下载有发音的单词
                    audios.append(pron)
            mw.app.processEvents()
        mw.col.reset()
        mw.reset()

        tooltip(f'添加{len(words)}个笔记')

        if audios:
            self.log('下载发音')
            self.downloadAudio(audios)
        else:
            self.ui.startSyncBtn.setEnabled(True)

    def downloadAudio(self, audios):
        def done():
            for _, t in self.threadList:
                t.terminate()
            self.ui.startSyncBtn.setEnabled(True)
            tooltip(f'发音下载完成！')

        downloadThread = QThread()
        downloadWorker = api.AudioDownloader(audios)
        self.threadList.append((downloadWorker, downloadThread))
        downloadWorker.SIG.progress.connect(self.updateProgress)
        downloadWorker.SIG.totalTasks.connect(self.ui.progressBar.setMaximum)
        downloadWorker.SIG.log.connect(self.log)
        downloadWorker.moveToThread(downloadThread)
        downloadThread.started.connect(downloadWorker.run)
        downloadThread.start()
        downloadWorker.SIG.downloadFinished.connect(done)
