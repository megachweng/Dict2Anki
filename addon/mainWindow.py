import json
import logging
import sys
from copy import deepcopy
from PyQt5.QtCore import QThread, pyqtSlot, pyqtProperty, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QPlainTextEdit, QVBoxLayout
from .logger import Handler
from .form import mainWindowForm, icons_rc
from .dictionary import registered_dictionaries
from .api import registered_apis
from .noteManager import (
    getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, getOrCreateDeck, getWordsByDeck, addNoteToDeck,
    getNotes)
from .loginDialog import LoginDialog
from .wordGroupDialog import WordGroupDialog
from .workers import RemoteWordFetchingWorker, QueryWorker, AudioDownloadWorker
from .constants import MODEL_NAME

from aqt.utils import showInfo, askUser, tooltip
from aqt import mw

logger = logging.getLogger('dict2Anki')


def fatal_error(exc_type, exc_value, exc_traceback):
    logger.exception(exc_value, exc_info=(exc_type, exc_value, exc_traceback))


# 未知异常日志
sys.excepthook = fatal_error


class MainWindow(QDialog, mainWindowForm.Ui_Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setupLogger()
        self.dictionaryComboBox.addItems([d.name for d in registered_dictionaries])
        self.apiComboBox.addItems([d.name for d in registered_apis])
        self.deckComboBox.addItems(getDeckList())
        self.setupGUIByConfig()
        self.tabWidget.setCurrentIndex(int(self.cookieLineEdit.text() == ''))
        self.dictionaryComboBox.currentIndexChanged.connect(self.onDictionaryIndexChanged)
        self.queryBtn.clicked.connect(self.onQueryBtnClicked)
        self.pullRemoteWordsBtn.clicked.connect(self.onPullRemoteWordsBtnClicked)
        self.syncBtn.clicked.connect(self.onSyncBtnClicked)

        self.workerThread = QThread(self)
        self.workerThread.start()
        self.syncBtn.setEnabled(True)

        self.selectedDict = None
        self.selectedGroups = None
        self.remoteWordList = []

    @pyqtSlot(int)
    def onDictionaryIndexChanged(self, index):
        """词典候选框改变事件"""
        self.currentDictionaryLabel.setText(f'当前选择词典: {self.dictionaryComboBox.currentText()}')
        config = mw.addonManager.getConfig(__name__)
        self.cookieLineEdit.setText(config['credential'][index]['cookie'])

    def setupGUIByConfig(self):
        config = mw.addonManager.getConfig(__name__)
        self.deckComboBox.setCurrentText(config['deck'])
        self.dictionaryComboBox.setCurrentIndex(config['selectedDict'])
        self.apiComboBox.setCurrentIndex(config['selectedApi'])
        self.cookieLineEdit.setText(config['credential'][config['selectedDict']]['cookie'])
        self.definitionCheckBox.setChecked(config['definition'])
        self.imageCheckBox.setChecked(config['image'])
        self.sentenceCheckBox.setChecked(config['sentence'])
        self.phraseCheckBox.setChecked(config['phrase'])
        self.AmEPhoneticCheckBox.setChecked(config['AmEPhonetic'])
        self.BrEPhoneticCheckBox.setChecked(config['BrEPhonetic'])
        self.BrEPronRadioButton.setChecked(config['BrEPron'])
        self.AmEPronRadioButton.setChecked(config['AmEPron'])
        self.noPronRadioButton.setChecked(config['noPron'])
        self.definitionSpinBox.setValue(config['definitionCount'])
        self.phraseSpinBox.setValue(config['phraseCount'])
        self.sentenceSpinBox.setValue(config['sentenceCount'])

        self.selectedGroups = config['selectedGroup']

    def setupLogger(self):
        def onDestroyed():
            logger.removeHandler(QtHandler)

        # 防止 debug 信息写入stdout/stderr 导致 Anki 崩溃
        logging.basicConfig(handlers=[logging.FileHandler('dict2anki.log', 'w', 'utf-8')], level=logging.DEBUG, format='[%(asctime)s][%(levelname)8s] -- %(message)s - (%(name)s)')

        logTextBox = QPlainTextEdit(self)
        logTextBox.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout = QVBoxLayout()
        layout.addWidget(logTextBox)
        self.logTab.setLayout(layout)
        QtHandler = Handler(self)
        logger.addHandler(QtHandler)
        QtHandler.newRecord.connect(logTextBox.appendPlainText)

        # 日志Widget销毁时移除 Handlers
        logTextBox.destroyed.connect(onDestroyed)

    def closeEvent(self, event):
        # 插件关闭时退出所有线程
        while self.workerThread.isRunning():
            if not self.workerThread.isInterruptionRequested():
                self.workerThread.requestInterruption()
            self.workerThread.quit()
            self.workerThread.wait(5)

        event.accept()

    @pyqtProperty(dict)
    def currentConfig(self):
        currentConfig = dict(
            selectedDict=self.dictionaryComboBox.currentIndex(),
            selectedApi=self.apiComboBox.currentIndex(),
            selectedGroup=self.selectedGroups,
            deck=self.deckComboBox.currentText(),
            cookie=self.cookieLineEdit.text(),
            definition=self.definitionCheckBox.isChecked(),
            sentence=self.sentenceCheckBox.isChecked(),
            image=self.imageCheckBox.isChecked(),
            phrase=self.phraseCheckBox.isChecked(),
            AmEPhonetic=self.AmEPhoneticCheckBox.isChecked(),
            BrEPhonetic=self.BrEPhoneticCheckBox.isChecked(),
            BrEPron=self.BrEPronRadioButton.isChecked(),
            AmEPron=self.AmEPronRadioButton.isChecked(),
            noPron=self.noPronRadioButton.isChecked(),
            definitionCount=self.definitionSpinBox.value(),
            phraseCount=self.phraseSpinBox.value(),
            sentenceCount=self.sentenceSpinBox.value(),
        )
        _currentConfig = deepcopy(currentConfig)
        _currentConfig['cookie'] = '******'
        logger.info(f'当前设置:{_currentConfig}')
        self._saveConfig(currentConfig)
        return currentConfig

    @staticmethod
    def _saveConfig(currentConfig):
        config = mw.addonManager.getConfig(__name__)
        currentConfig = deepcopy(currentConfig)
        credential = config['credential']
        credential[currentConfig['selectedDict']]['cookie'] = currentConfig.pop('cookie')
        currentConfig['credential'] = credential
        logger.info(f'保存配置项:{currentConfig}')
        mw.addonManager.writeConfig(__name__, currentConfig)

    @pyqtSlot()
    def onPullRemoteWordsBtnClicked(self):
        logger.info(self.currentConfig)
        if not self.deckComboBox.currentText():
            showInfo('\n请选择或输入要同步的牌组')
            return

        self.mainTab.setEnabled(False)
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(0)

        self.selectedDict = registered_dictionaries[self.dictionaryComboBox.currentIndex()]()
        try:
            cookie = json.loads(self.cookieLineEdit.text())
        except json.JSONDecodeError:
            cookie = dict()

        isLogin = self.selectedDict.checkLoginState(cookie=cookie, first_login=False)

        if not isLogin:
            loginDialog = LoginDialog(url=self.selectedDict.wordBookUrl, callback=self.selectedDict.checkLoginState)
            loginDialog.loginSucceed.connect(self.onLoginSucceed)
            loginDialog.exec()
        else:
            self.onLoginSucceed(cookie)

    @pyqtSlot(dict)
    def onLoginSucceed(self, cookie: dict):
        self.cookieLineEdit.setText(json.dumps(cookie))
        wordGroupDialog = WordGroupDialog()
        wordGroup = self.selectedDict.getWordGroup()
        wordGroupDialog.init_data(wordGroup, previousChecked=None)

        def onRejected():
            self.mainTab.setEnabled(True)

        def onAccepted():
            logger.info(f'选择单词本:{wordGroupDialog.selectedGroup}')
            self.newWordListWidget.clear()
            self.needDeleteWordListWidget.clear()
            self.getRemoteWordList(wordGroupDialog.selectedGroup)

        wordGroupDialog.buttonBox.accepted.connect(onAccepted)
        wordGroupDialog.buttonBox.rejected.connect(onRejected)
        wordGroupDialog.exec()

    def getRemoteWordList(self, selectedWordGroup: (str, str)):
        """获取远程单词"""
        self.pullWorker = RemoteWordFetchingWorker(self.selectedDict, selectedWordGroup)
        self.pullWorker.moveToThread(self.workerThread)
        self.pullWorker.start.connect(self.pullWorker.run)
        self.pullWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
        self.pullWorker.setTotal.connect(self.progressBar.setMaximum)
        self.pullWorker.done.connect(self.onAllPullWorkDone)
        self.pullWorker.doneThisGroup.connect(self.onDoneThisGroup)
        self.pullWorker.start.emit()

    @pyqtSlot(list)
    def onDoneThisGroup(self, words):
        self.remoteWordList += words

    @pyqtSlot()
    def onAllPullWorkDone(self):
        waitIcon = QIcon(':/icons/wait.png')
        delIcon = QIcon(':/icons/delete.png')

        remoteWords = set(self.remoteWordList)
        self.remoteWordList = []
        localWords = set(getWordsByDeck(self.deckComboBox.currentText()))

        needQueryWords = remoteWords - localWords  # 新单词
        needDeleteWords = localWords - remoteWords  # 需要删除的单词
        logger.info(f'本地: {localWords}')
        logger.info(f'远程: {remoteWords}')
        logger.info(f'待查: {needQueryWords}')
        logger.info(f'待删: {needDeleteWords}')

        for w in needQueryWords:
            item = QListWidgetItem(w, self.newWordListWidget)
            item.setIcon(waitIcon)
            item.setData(Qt.UserRole, None)

        for w in needDeleteWords:
            item = QListWidgetItem(w)
            item.setIcon(delIcon)
            item.setCheckState(Qt.Checked)
            self.needDeleteWordListWidget.addItem(item)

        self.queryBtn.setEnabled(True)
        self.mainTab.setEnabled(True)

    @pyqtSlot()
    def onQueryBtnClicked(self):
        self.mainTab.setEnabled(False)
        self.queryBtn.setEnabled(False)

        wordList = []
        selectedWords = self.newWordListWidget.selectedItems()
        if selectedWords:
            # 如果选中单词则只查询选中的单词
            for wordItem in selectedWords:
                row = self.newWordListWidget.row(wordItem)
                wordList.append((row, wordItem.text()))
        else:  # 没有选择则查询全部
            for row in range(self.newWordListWidget.count()):
                wordItem = self.newWordListWidget.item(row)
                wordList.append((row, wordItem.text()))

        self.progressBar.setMaximum(len(wordList))
        self.queryWorker = QueryWorker(wordList, registered_apis[self.apiComboBox.currentIndex()])
        self.queryWorker.moveToThread(self.workerThread)
        self.queryWorker.thisRowDone.connect(self.onThisRowDone)
        self.queryWorker.thisRowFailed.connect(self.onThisRowFailed)
        self.queryWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
        self.queryWorker.allQueryDone.connect(self.onAllQueryDone)
        self.queryWorker.start.connect(self.queryWorker.run)
        self.queryWorker.start.emit()

    @pyqtSlot(int, dict)
    def onThisRowDone(self, row, queryResult):
        doneIcon = QIcon(':/icons/done.png')
        wordItem = self.newWordListWidget.item(row)
        wordItem.setIcon(doneIcon)
        wordItem.setData(Qt.UserRole, queryResult)

    @pyqtSlot(int)
    def onThisRowFailed(self, row):
        failedIcon = QIcon(':/icons/failed.png')
        failedWordItem = self.newWordListWidget.item(row)
        failedWordItem.setIcon(failedIcon)

    def onAllQueryDone(self):
        self.queryBtn.setEnabled(True)
        self.mainTab.setEnabled(True)
        self.syncBtn.setEnabled(True)

    def onSyncBtnClicked(self):
        failedGenerator = (self.newWordListWidget.item(row).data(Qt.UserRole) is None for row in range(self.newWordListWidget.count()))
        if any(failedGenerator):
            if not askUser('存在未查询或失败的单词，确定要加入单词本吗？\n 你可以选择失败的单词点击 "查询按钮" 来重试。'):
                return

        added, audiosDownloadTasks = self.addNotes()
        self.downloadAudio(audiosDownloadTasks)
        deleted = self.deleteLocalWords()

        tooltip(f'添加{added}个笔记\n删除{deleted}个笔记')

    def addNotes(self) -> (int, list):
        model = getOrCreateModel(MODEL_NAME)
        getOrCreateModelCardTemplate(model, 'default')
        deck = getOrCreateDeck(self.deckComboBox.currentText())

        newWordCount = self.newWordListWidget.count()
        added = 0
        audiosDownloadTasks = []

        # 判断是否需要下载发音
        if self.currentConfig['noPron']:
            logger.info('不下载发音')
            whichPron = None
        else:
            whichPron = 'AmEPron' if self.currentConfig['AmEPron'] else 'BrEPron'
            logger.info(f'下载发音{whichPron}')

        for row in range(newWordCount):
            wordItem = self.newWordListWidget.item(row)
            wordItemData = wordItem.data(Qt.UserRole)
            if wordItemData:
                addNoteToDeck(deck, model, self.currentConfig, wordItemData)
                added += 1
                # 添加发音任务
                if whichPron and wordItemData.get(whichPron):
                    audiosDownloadTasks.append((f"Dict2Anki_{wordItemData['term']}.mp3", wordItemData[whichPron],))
        mw.reset()
        return added, audiosDownloadTasks

    def downloadAudio(self, audiosDownloadTasks):
        logger.info(f'发音下载任务:{audiosDownloadTasks}')
        if audiosDownloadTasks:
            self.syncBtn.setEnabled(False)
            self.progressBar.setValue(0)
            self.progressBar.setMaximum(len(audiosDownloadTasks))

            self.audioDownloadWorker = AudioDownloadWorker(audiosDownloadTasks)
            self.audioDownloadWorker.moveToThread(self.workerThread)
            self.audioDownloadWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
            self.audioDownloadWorker.start.connect(self.audioDownloadWorker.run)
            self.audioDownloadWorker.done.connect(lambda: tooltip(f'发音下载完成'))
            self.audioDownloadWorker.start.emit()

            self.newWordListWidget.clear()

    def deleteLocalWords(self):
        needToDeleteWordItems = [
            self.needDeleteWordListWidget.item(row)
            for row in range(self.needDeleteWordListWidget.count())
            if self.needDeleteWordListWidget.item(row).checkState() == Qt.Checked
        ]
        needToDeleteWords = [i.text() for i in needToDeleteWordItems]

        deleted = 0

        if needToDeleteWords and askUser(f'确定要删除这些单词吗:{needToDeleteWords[:3]}...({len(needToDeleteWords)}个)', title='Dict2Anki', parent=self):
            needToDeleteWordNoteIds = getNotes(needToDeleteWords, self.currentConfig['deck'])
            mw.col.remNotes(needToDeleteWordNoteIds)
            deleted += 1
            mw.col.reset()
            mw.reset()
            for item in needToDeleteWordItems:
                self.needDeleteWordListWidget.takeItem(self.needDeleteWordListWidget.row(item))
            logger.info('删除完成')
        logger.info('完成')
        return deleted
