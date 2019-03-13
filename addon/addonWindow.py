import sys
import logging
import json

try:
    from aqt import mw
    from .noteManager import getOrCreateDeck, getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, addNoteToDeck, getWordsByDeck, getNotes
except ImportError:
    from test.mock_noteManager import getOrCreateDeck, getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, addNoteToDeck, getWordsByDeck, getNotes

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QListWidgetItem, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QThread, Qt

from .queryApi import apis
from .UIForm import wordGroup, mainUI, icons_rc
from .workers import LoginWorker, VersionCheckWorker, RemoteWordFetchingWorker, QueryWorker
from .dictionary import dictionaries
from .logger import Handler
from .misc import Mask
from .constants import BASIC_OPTION, EXTRA_OPTION, MODEL_NAME

logger = logging.getLogger('dict2Anki')


def fatal_error(exc_type, exc_value, exc_traceback):
    logger.exception(exc_value, exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = fatal_error


class Windows(QDialog, mainUI.Ui_Dialog):
    isRunning = False

    def __init__(self, parent=None):
        super(Windows, self).__init__(parent)
        self.setupUi(self)
        self.postUISetup()
        self.setupLogger()
        self.initCore()
        self.connect()
        # self.check_update()
        self.selectedDict = None
        self.currentConfig = dict()

        self.workerThread = QThread(self)
        self.workerThread.start()
        self.updateCheckThead = QThread(self)
        self.updateCheckThead.start()

        self.loginWorker = None
        self.queryWorker = None
        self.pullWorker = None

        self.localWords = []
        self.doNotQuery = False

        self.__dev()

    def closeEvent(self, event):
        if self.workerThread.isRunning():
            self.workerThread.requestInterruption()
            self.workerThread.quit()
            self.workerThread.wait()

        if self.updateCheckThead.isRunning():
            self.updateCheckThead.quit()
            self.updateCheckThead.wait()
        event.accept()

    def __dev(self):
        self.queryBtn.setEnabled(True)
        self.insertWordToListWidget(['hardly...than...', 'rather than', 'grsdgwe'])

    def postUISetup(self):
        self.setWindowTitle(MODEL_NAME)

    def setupLogger(self):
        def onDestroyed():
            logging.getLogger().removeHandler(handler)

        logTextBox = QPlainTextEdit(self)
        logTextBox.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout = QVBoxLayout()
        layout.addWidget(logTextBox)
        self.logTab.setLayout(layout)
        handler = Handler(self)
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        handler.newRecord.connect(logTextBox.appendPlainText)
        logTextBox.destroyed.connect(onDestroyed)

    def restoreConfig(self):
        self.usernameLineEdit.setText('megachweng@163.com')
        self.passwordLineEdit.setText(str(Mask('cs123456')))
        self.cookieLineEdit.setText(str(Mask(
            '''{'EudicWeb': 'EBD6EBD5A6AE776E0BF9418342A19199E728A8C2E866F4B08DDFA6A72557673ABE3C211C8801BA062C4AD4558E7C771F532DE7300F1433BD8778BC8116A97613A825E55883D12EC8A11BD6F3E5359E8DA5CA26592E4DEAE3C87BFB74F376E4906D0C52FE8DDB12E83A6F2962C186D1DBAF379206355D592A4209CD8E7DF857E1E48C35C5', '__cfduid': 'd92561578a8933b41395b531ae7b18d691552038729', 'ASP.NET_SessionId': '2lcrqnuzbsajgq35jhyfjef5', 'EudicWebSession': 'QYNeyJ0b2tlbiI6InpKeVpOdldpYjdHYzdRdndYanAvd0dQWmVDMD0iLCJleHBpcmVpbiI6MTMxNDAwMCwidXNlcmlkIjoiYTMxOWU5OGQtYTBkZS0xMWU3LWFjODMtMDAwYzI5ZmZlZjliIiwidXNlcm5hbWUiOiJtZWdhY2h3ZW5nQDE2My5jb20iLCJjcmVhdGlvbl9kYXRlIjoiMjAxNy0wOS0yNFQwNDoxMjo1NFoiLCJyb2xlcyI6bnVsbCwib3BlbmlkX3R5cGUiOm51bGwsIm9wZW5pZF9kZXNjIjpudWxsLCJwcm9maWxlIjp7Im5pY2tuYW1lIjoiTUdDIiwiZW1haWwiOiJtZWdhY2h3ZW5nQDE2My5jb20iLCJnZW5kZXIiOiIiLCJwYXNzd29yZCI6bnVsbCwidm9jYWJ1bGFyaWVzIjp7fX19'}'''.replace(
                '\'', '\"'))))

    def initCore(self):
        self.dictionaryComboBox.addItems([d.name for d in dictionaries])
        self.apiComboBox.addItems([d.name for d in apis])
        self.deckComboBox.addItems(getDeckList())
        self.restoreConfig()

    def getCurrentConfig(self) -> dict:
        """获取当前设置"""
        currentConfig = dict(
            selectedDict=self.dictionaryComboBox.currentIndex(),
            selectedApi=self.apiComboBox.currentIndex(),
            username=self.usernameLineEdit.text(),
            password=Mask(self.passwordLineEdit.text()),
            cookie=Mask(self.cookieLineEdit.text()),
            definition=self.definitionCheckBox.isChecked(),
            sentence=self.sentenceCheckBox.isChecked(),
            image=self.imageCheckBox.isChecked(),
            phrase=self.phraseCheckBox.isChecked(),
            AmEPhonetic=self.AmEPhoneticCheckBox.isChecked(),
            BrEPhonetic=self.BrEPhoneticCheckBox.isChecked(),
            BrEPron=self.BrEPronRadioButton.isChecked(),
            AmEPron=self.AmEPronRadioButton.isChecked(),
            noPron=self.noPronRadioButton.isChecked(),
        )
        logger.info(f'当前设置:{currentConfig}')
        self.currentConfig = currentConfig
        return currentConfig

    def checkUpdate(self):
        pass
        # @pyqtSlot(str, str)
        # def on_have_new_version(version, change_log):
        #     logger.info(f'{version}{change_log}')
        #
        # self.thread_version_checking = QThread()
        # self.worker_version_checking = VersionCheckWorker()
        # self.worker_version_checking.moveToThread(self.thread_version_checking)
        # self.worker_version_checking.haveNewVersion.connect(on_have_new_version)
        # self.worker_version_checking.finished.connect(self.thread_version_checking.quit)
        # self.thread_version_checking.started.connect(self.worker_version_checking.run)
        # self.thread_version_checking.start()

    def updateCredential(self, dictionary_name: str, username: str, password: str, cookie: str):
        self.currentDictionaryLabel.setText(f'当前选择词典:{dictionary_name}')
        self.usernameLineEdit.setText(username)
        self.passwordLineEdit.setText(password)
        self.cookieLineEdit.setText(cookie)

    def connect(self):
        """连接事件"""
        pass

    @pyqtSlot(int)
    def on_dictionaryComboBox_currentIndexChanged(self, index):
        self.currentDictionaryLabel.setText(f'当前选择词典: {self.dictionaryComboBox.currentText()}')

    @pyqtSlot()
    def on_pullRemoteWordsBtn_clicked(self):
        """获取单词按钮点击事件"""
        self.pullRemoteWordsBtn.setEnabled(False)
        self.queryBtn.setEnabled(False)
        self.syncBtn.setEnabled(False)
        self.deckComboBox.setEnabled(False)
        self.dictionaryComboBox.setEnabled(False)
        self.apiComboBox.setEnabled(False)
        # 清空 word_table_widget
        self.wordListWidget.clear()
        self.progressBar.setMaximum(0)

        currentConfig = self.getCurrentConfig()
        self.selectedDict = dictionaries[currentConfig['selectedDict']]()

        self.loginWorker = LoginWorker(self.selectedDict.login, str(currentConfig['username']), str(currentConfig['password']), json.loads(str(currentConfig['cookie'])))
        self.loginWorker.moveToThread(self.workerThread)
        self.loginWorker.logSuccess.connect(self.showGroupDialog)
        self.loginWorker.start.connect(self.loginWorker.run)
        self.loginWorker.logFailed.connect(self.onLoginFailed)
        self.loginWorker.start.emit()

    @pyqtSlot()
    def onLoginFailed(self):
        # todo apt.utl.show_critical('登录失败')
        self.tabWidget.setCurrentIndex(1)

    @pyqtSlot()
    def showGroupDialog(self):
        logger.info('缓存中获取单词本分组')
        self.selectedDict.getGroups()

        container = QDialog(self)
        group = wordGroup.Ui_Dialog()
        group.setupUi(container)
        for group_name in [str(group_name) for group_name, _ in self.selectedDict.groups]:
            item = QListWidgetItem()
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            item.setText(group_name)
            group.wordGroupListWidget.addItem(item)

        def onAccepted():
            selectedGroups = [group.wordGroupListWidget.item(index).text() for index in range(group.wordGroupListWidget.count()) if
                              group.wordGroupListWidget.item(index).checkState() == Qt.Checked]

            self.progressBar.setValue(0)
            self.progressBar.setMaximum(len(selectedGroups))
            logger.info(f'选中单词本{selectedGroups}')
            self.getRemoteWordList(selectedGroups)
            self.progressBar.setMaximum(len(selectedGroups))

        def onRejected():
            self.progressBar.setValue(0)
            self.progressBar.setMaximum(1)
            self.pullRemoteWordsBtn.setEnabled(True)
            self.dictionaryComboBox.setEnabled(True)
            self.apiComboBox.setEnabled(True)
            self.deckComboBox.setEnabled(True)
            self.queryBtn.setEnabled(False)
            self.syncBtn.setEnabled(False)

        group.buttonBox.accepted.connect(onAccepted)
        group.buttonBox.rejected.connect(onRejected)
        container.exec()

    def getRemoteWordList(self, selected_groups: [str]):
        """根据选中到分组获取分组下到全部单词，并添加到word_table_widget"""
        group_map = dict(self.selectedDict.groups)
        self.localWords = getWordsByDeck(self.deckComboBox.currentText())

        self.pullWorker = RemoteWordFetchingWorker(self.selectedDict, [(group_name, group_map[group_name],) for group_name in selected_groups])
        self.pullWorker.moveToThread(self.workerThread)
        self.pullWorker.start.connect(self.pullWorker.run)
        self.pullWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
        self.pullWorker.doneThisGroup.connect(self.insertWordToListWidget)
        self.pullWorker.done.connect(self.on_allPullWork_done)
        self.pullWorker.start.emit()

    @pyqtSlot(list)
    def insertWordToListWidget(self, words: list):
        self.wordListWidget.addItems(words)
        self.wordListWidget.clearSelection()

    @pyqtSlot()
    def on_allPullWork_done(self):
        localWordList = set(getWordsByDeck(self.deckComboBox.currentText()))
        remoteWordList = set([self.wordListWidget.item(row).text() for row in range(self.wordListWidget.count())])

        newWords = remoteWordList - localWordList
        needToDeleteWords = localWordList - remoteWordList
        needToDeleteIds = getNotes(wordList=needToDeleteWords, deckName=self.deckComboBox.currentText())
        logger.info(f'本地: {localWordList}')
        logger.info(f'远程: {remoteWordList}')
        logger.info(f'待查: {newWords}')
        logger.info(f'待删: {needToDeleteWords} --- {needToDeleteIds}')
        # todo 无操作时的提示（无待查，待删）
        self.wordListWidget.clear()
        waitIcon = QIcon(':/icons/wait.png')
        for word in newWords:
            item = QListWidgetItem(word)
            item.setIcon(waitIcon)
            self.wordListWidget.addItem(item)
        self.wordListWidget.clearSelection()

        self.progressBar.setValue(0)
        self.progressBar.setMaximum(1)
        self.dictionaryComboBox.setEnabled(True)
        self.apiComboBox.setEnabled(True)
        self.deckComboBox.setEnabled(True)
        self.pullRemoteWordsBtn.setEnabled(True)
        self.queryBtn.setEnabled(True)
        self.syncBtn.setEnabled(False)

    @pyqtSlot()
    def on_queryBtn_clicked(self):
        logger.info('点击查询按钮')

        currentConfig = self.getCurrentConfig()

        self.queryBtn.setEnabled(False)
        self.pullRemoteWordsBtn.setEnabled(False)
        self.syncBtn.setEnabled(False)

        wordList = []
        selectedWords = self.wordListWidget.selectedItems()
        if selectedWords:
            for wordItem in selectedWords:
                wordBundle = dict()
                row = self.wordListWidget.row(wordItem)
                wordBundle['term'] = wordItem.text()
                for configName in BASIC_OPTION + EXTRA_OPTION:
                    wordBundle[configName] = currentConfig[configName]
                    wordBundle['row'] = row
                wordList.append(wordBundle)
        else:
            for row in range(self.wordListWidget.count()):
                wordBundle = dict()
                wordItem = self.wordListWidget.item(row)
                wordBundle['term'] = wordItem.text()
                for configName in BASIC_OPTION + EXTRA_OPTION:
                    wordBundle[configName] = currentConfig[configName]
                    wordBundle['row'] = row
                wordList.append(wordBundle)

        logger.info(f'待查询单词{wordList}')
        self.progressBar.setMaximum(len(wordList))
        if currentConfig['selectedApi'] >= len(apis):
            #  todo 不进行查询时的提示
            logger.info('不查询')
            self.queryBtn.setEnabled(True)
            self.pullRemoteWordsBtn.setEnabled(True)
            self.syncBtn.setEnabled(True)
            return
        self.queryWorker = QueryWorker(wordList, apis[currentConfig['selectedApi']])
        self.queryWorker.moveToThread(self.workerThread)
        self.queryWorker.thisRowDone.connect(self.on_thisRowDone)
        self.queryWorker.thisRowFailed.connect(self.on_thisRowFailed)
        self.queryWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
        self.queryWorker.allQueryDone.connect(self.on_allQueryDone)
        self.queryWorker.start.connect(self.queryWorker.run)
        self.queryWorker.start.emit()

    @pyqtSlot(int, dict)
    def on_thisRowDone(self, row, result):
        """该行单词查询完毕"""
        doneIcon = QIcon(':/icons/done.png')
        wordItem = self.wordListWidget.item(row)
        wordItem.setIcon(doneIcon)
        wordItem.queryResult = result

    @pyqtSlot(int)
    def on_thisRowFailed(self, row):
        failedIcon = QIcon(':/icons/failed.png')
        failedWordItem = self.wordListWidget.item(row)
        failedWordItem.setIcon(failedIcon)
        failedWordItem.queryResult = None

    @pyqtSlot()
    def on_allQueryDone(self):
        failed = []
        for i in range(self.wordListWidget.count()):
            wordItem = self.wordListWidget.item(i)
            if getattr(wordItem, 'queryFailed', False):
                failed.append(wordItem.text())
        if failed:
            logger.warning(f'查询失败:{failed}')
        self.pullRemoteWordsBtn.setEnabled(True)
        self.queryBtn.setEnabled(True)
        self.syncBtn.setEnabled(True)

    @pyqtSlot()
    def on_syncBtn_clicked(self):
        currentConfig = self.getCurrentConfig()
        model = getOrCreateModel(MODEL_NAME)
        getOrCreateModelCardTemplate(model, 'default')
        deck = getOrCreateDeck(self.deckComboBox.currentText())

        logger.info('同步点击')
        for row in range(self.wordListWidget.count()):
            wordItem = self.wordListWidget.item(row)
            if wordItem.queryResult:
                addNoteToDeck(deck, model, currentConfig, wordItem.queryResult)
