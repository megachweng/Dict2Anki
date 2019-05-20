import json
import logging

from PyQt5.QtCore import QThread, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QPlainTextEdit, QVBoxLayout
from .logger import Handler
from .form import mainWindowForm, icons_rc
from .dictionary import registered_dictionaries
from .api import registered_apis
from .noteManager import getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, getOrCreateDeck
from .loginDialog import LoginDialog
from .wordGroupDialog import WordGroupDialog
from .workers import RemoteWordFetchingWorker, QueryWorker
from .constants import MODEL_NAME
from aqt.utils import showInfo, askUser

logger = logging.getLogger('dict2Anki')


class MainWindow(QDialog, mainWindowForm.Ui_Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setupLogger()
        self.workerThread = QThread(self)
        self.workerThread.start()
        self.syncBtn.setEnabled(True)
        self.dictionaryComboBox.currentTextChanged.connect(
            lambda dictName: self.currentDictionaryLabel.setText('当前选择: ' + dictName)
        )
        self.queryBtn.clicked.connect(self.onQueryBtnClicked)
        self.pullRemoteWordsBtn.clicked.connect(self.onPullRemoteWordsBtnClicked)
        self.syncBtn.clicked.connect(self.onSyncBtnClicked)

        self.dictionaryComboBox.addItems([d.name for d in registered_dictionaries])
        self.apiComboBox.addItems([d.name for d in registered_apis])
        self.deckComboBox.addItems(getDeckList())
        self.selectedDict = None

        # self.setupGUIByConfig()
        self.remoteWordList = []

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

    @pyqtSlot()
    def onPullRemoteWordsBtnClicked(self):
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
        doneIcon = QIcon(':/icons/done.png')
        remoteWords = set(self.remoteWordList)
        self.remoteWordList = []
        localWords = {'a', 'b', 'c'}

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
        model = getOrCreateModel(MODEL_NAME)
        getOrCreateModelCardTemplate(model, 'default')
        deck = getOrCreateDeck(self.deckComboBox.currentText())
        from .noteManager import addNoteToDeck
        # addNoteToDeck(deck, model)
