import os
import sys
import logging
import json
from copy import deepcopy
from tempfile import gettempdir

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QListWidgetItem, QVBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSlot, QThread, Qt

from .queryApi import apis
from .UIForm import wordGroup, mainUI, icons_rc
from .workers import LoginStateCheckWorker, VersionCheckWorker, RemoteWordFetchingWorker, QueryWorker, AudioDownloadWorker
from .dictionary import dictionaries
from .logger import Handler
from .loginDialog import LoginDialog
from .misc import Mask
from .constants import BASIC_OPTION, EXTRA_OPTION, MODEL_NAME, RELEASE_URL

try:
    from aqt import mw
    from aqt.utils import askUser, showCritical, showInfo, tooltip, openLink
    from .noteManager import getOrCreateDeck, getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, addNoteToDeck, getWordsByDeck, getNotes
except ImportError:
    from test.dummy_aqt import mw, askUser, showCritical, showInfo, tooltip, openLink
    from test.dummy_noteManager import getOrCreateDeck, getDeckList, getOrCreateModel, getOrCreateModelCardTemplate, addNoteToDeck, getWordsByDeck, getNotes

logger = logging.getLogger('dict2Anki')


def fatal_error(exc_type, exc_value, exc_traceback):
    logger.exception(exc_value, exc_info=(exc_type, exc_value, exc_traceback))


# 未知异常日志
sys.excepthook = fatal_error


class Windows(QDialog, mainUI.Ui_Dialog):
    isRunning = False

    def __init__(self, parent=None):
        super(Windows, self).__init__(parent)
        self.selectedDict = None
        self.currentConfig = dict()
        self.localWords = []
        self.selectedGroups = []

        self.workerThread = QThread(self)
        self.workerThread.start()
        self.updateCheckThead = QThread(self)
        self.updateCheckThead.start()
        self.audioDownloadThread = QThread(self)

        self.updateCheckWork = None
        self.loginWorker = None
        self.queryWorker = None
        self.pullWorker = None
        self.audioDownloadWorker = None

        self.setupUi(self)
        self.setWindowTitle(MODEL_NAME)
        self.setupLogger()
        self.initCore()
        self.checkUpdate()
        # self.__dev() # 以备调试时使用

    def __dev(self):
        def on_dev():
            logger.debug('whatever')

        self.devBtn = QPushButton('Magic Button', self.mainTab)
        self.devBtn.clicked.connect(on_dev)
        self.gridLayout_4.addWidget(self.devBtn, 4, 3, 1, 1)

    def closeEvent(self, event):
        # 插件关闭时退出所有线程
        if self.workerThread.isRunning():
            self.workerThread.requestInterruption()
            self.workerThread.quit()
            self.workerThread.wait()

        if self.updateCheckThead.isRunning():
            self.updateCheckThead.quit()
            self.updateCheckThead.wait()

        if self.audioDownloadThread.isRunning():
            self.audioDownloadThread.requestInterruption()
            self.workerThread.quit()
            self.workerThread.wait()

        event.accept()

    def setupLogger(self):
        """初始化 Logger """

        def onDestroyed():
            logger.removeHandler(QtHandler)

        # 防止 debug 信息写入stdout/stderr 导致 Anki 崩溃
        logFile = os.path.join(gettempdir(), 'dict2anki.log')
        logging.basicConfig(handlers=[logging.FileHandler(logFile, 'w', 'utf-8')], level=logging.DEBUG, format='[%(asctime)s][%(levelname)8s] -- %(message)s - (%(name)s)')

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

    def setupGUIByConfig(self):
        config = mw.addonManager.getConfig(__name__)
        self.deckComboBox.setCurrentText(config['deck'])
        self.dictionaryComboBox.setCurrentIndex(config['selectedDict'])
        self.apiComboBox.setCurrentIndex(config['selectedApi'])
        self.usernameLineEdit.setText(config['credential'][config['selectedDict']]['username'])
        self.passwordLineEdit.setText(config['credential'][config['selectedDict']]['password'])
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
        self.selectedGroups = config['selectedGroup']

    def initCore(self):
        self.usernameLineEdit.hide()
        self.usernameLabel.hide()
        self.passwordLabel.hide()
        self.passwordLineEdit.hide()
        self.dictionaryComboBox.addItems([d.name for d in dictionaries])
        self.apiComboBox.addItems([d.name for d in apis])
        self.deckComboBox.addItems(getDeckList())
        self.setupGUIByConfig()

    def getAndSaveCurrentConfig(self) -> dict:
        """获取当前设置"""
        currentConfig = dict(
            selectedDict=self.dictionaryComboBox.currentIndex(),
            selectedApi=self.apiComboBox.currentIndex(),
            selectedGroup=self.selectedGroups,
            deck=self.deckComboBox.currentText(),
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
        self._saveConfig(currentConfig)
        self.currentConfig = currentConfig
        return currentConfig

    @staticmethod
    def _saveConfig(config):
        _config = deepcopy(config)
        _config['credential'] = [dict(username='', password='', cookie='')] * len(dictionaries)
        _config['credential'][_config['selectedDict']] = dict(
            username=_config.pop('username'),
            password=str(_config.pop('password')),
            cookie=str(_config.pop('cookie'))
        )
        maskedConfig = deepcopy(_config)
        maskedCredential = [
            dict(
                username=c['username'],
                password=Mask(c['password']),
                cookie=Mask(c['cookie'])) for c in maskedConfig['credential']
        ]
        maskedConfig['credential'] = maskedCredential
        logger.info(f'保存配置项:{maskedConfig}')
        mw.addonManager.writeConfig(__name__, _config)

    def checkUpdate(self):
        @pyqtSlot(str, str)
        def on_haveNewVersion(version, changeLog):
            if askUser(f'有新版本:{version}是否更新？\n\n{changeLog.strip()}'):
                openLink(RELEASE_URL)

        self.updateCheckWork = VersionCheckWorker()
        self.updateCheckWork.moveToThread(self.updateCheckThead)
        self.updateCheckWork.haveNewVersion.connect(on_haveNewVersion)
        self.updateCheckWork.finished.connect(self.updateCheckThead.quit)
        self.updateCheckWork.start.connect(self.updateCheckWork.run)
        self.updateCheckWork.start.emit()

    @pyqtSlot(int)
    def on_dictionaryComboBox_currentIndexChanged(self, index):
        """词典候选框改变事件"""
        self.currentDictionaryLabel.setText(f'当前选择词典: {self.dictionaryComboBox.currentText()}')
        config = mw.addonManager.getConfig(__name__)
        self.cookieLineEdit.setText(config['credential'][index]['cookie'])

    @pyqtSlot()
    def on_pullRemoteWordsBtn_clicked(self):
        """获取单词按钮点击事件"""
        if not self.deckComboBox.currentText():
            showInfo('\n请选择或输入要同步的牌组')
            return

        self.mainTab.setEnabled(False)
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(0)

        currentConfig = self.getAndSaveCurrentConfig()
        self.selectedDict = dictionaries[currentConfig['selectedDict']]()

        # 登陆线程
        self.loginWorker = LoginStateCheckWorker(self.selectedDict.checkCookie, json.loads(self.cookieLineEdit.text() or '{}'))
        self.loginWorker.moveToThread(self.workerThread)
        self.loginWorker.start.connect(self.loginWorker.run)
        self.loginWorker.logSuccess.connect(self.onLogSuccess)
        self.loginWorker.logFailed.connect(self.onLoginFailed)
        self.loginWorker.start.emit()

    @pyqtSlot()
    def onLoginFailed(self):
        showCritical('第一次登录或cookie失效!请重新登录')
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(1)
        self.mainTab.setEnabled(True)
        self.cookieLineEdit.clear()
        self.loginDialog = LoginDialog(
            loginUrl=self.selectedDict.loginUrl,
            loginCheckCallbackFn=self.selectedDict.loginCheckCallbackFn,
            parent=self
        )
        self.loginDialog.loginSucceed.connect(self.onLogSuccess)
        self.loginDialog.show()

    @pyqtSlot(str)
    def onLogSuccess(self, cookie):
        self.cookieLineEdit.setText(cookie)
        self.getAndSaveCurrentConfig()
        self.selectedDict.checkCookie(json.loads(cookie))
        self.selectedDict.getGroups()

        container = QDialog(self)
        group = wordGroup.Ui_Dialog()
        group.setupUi(container)

        for groupName in [str(group_name) for group_name, _ in self.selectedDict.groups]:
            item = QListWidgetItem()
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setText(groupName)
            item.setCheckState(Qt.Unchecked)
            group.wordGroupListWidget.addItem(item)

        # 恢复上次选择的单词本分组
        if self.selectedGroups:
            for groupName in self.selectedGroups[self.currentConfig['selectedDict']]:
                items = group.wordGroupListWidget.findItems(groupName, Qt.MatchExactly)
                for item in items:
                    item.setCheckState(Qt.Checked)
        else:
            self.selectedGroups = [list()] * len(dictionaries)

        def onAccepted():
            """选择单词本弹窗确定事件"""
            # 清空 listWidget
            self.newWordListWidget.clear()
            self.needDeleteWordListWidget.clear()
            self.mainTab.setEnabled(False)

            selectedGroups = [group.wordGroupListWidget.item(index).text() for index in range(group.wordGroupListWidget.count()) if
                              group.wordGroupListWidget.item(index).checkState() == Qt.Checked]
            # 保存分组记录
            self.selectedGroups[self.currentConfig['selectedDict']] = selectedGroups
            self.progressBar.setValue(0)
            self.progressBar.setMaximum(1)
            logger.info(f'选中单词本{selectedGroups}')
            self.getRemoteWordList(selectedGroups)

        def onRejected():
            """选择单词本弹窗取消事件"""
            self.progressBar.setValue(0)
            self.progressBar.setMaximum(1)
            self.mainTab.setEnabled(True)

        group.buttonBox.accepted.connect(onAccepted)
        group.buttonBox.rejected.connect(onRejected)
        container.exec()

    def getRemoteWordList(self, selected_groups: [str]):
        """根据选中到分组获取分组下到全部单词，并添加到 newWordListWidget"""
        group_map = dict(self.selectedDict.groups)
        self.localWords = getWordsByDeck(self.deckComboBox.currentText())

        # 启动单词获取线程
        self.pullWorker = RemoteWordFetchingWorker(self.selectedDict, [(group_name, group_map[group_name],) for group_name in selected_groups])
        self.pullWorker.moveToThread(self.workerThread)
        self.pullWorker.start.connect(self.pullWorker.run)
        self.pullWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
        self.pullWorker.setProgress.connect(self.progressBar.setMaximum)
        self.pullWorker.doneThisGroup.connect(self.insertWordToListWidget)
        self.pullWorker.done.connect(self.on_allPullWork_done)
        self.pullWorker.start.emit()

    @pyqtSlot(list)
    def insertWordToListWidget(self, words: list):
        """一个分组获取完毕事件"""
        for word in words:
            wordItem = QListWidgetItem(word, self.newWordListWidget)
            wordItem.setData(Qt.UserRole, None)
        self.newWordListWidget.clearSelection()

    @pyqtSlot()
    def on_allPullWork_done(self):
        """全部分组获取完毕事件"""
        localWordList = set(getWordsByDeck(self.deckComboBox.currentText()))
        remoteWordList = set([self.newWordListWidget.item(row).text() for row in range(self.newWordListWidget.count())])

        newWords = remoteWordList - localWordList  # 新单词
        needToDeleteWords = localWordList - remoteWordList  # 需要删除的单词
        logger.info(f'本地: {localWordList}')
        logger.info(f'远程: {remoteWordList}')
        logger.info(f'待查: {newWords}')
        logger.info(f'待删: {needToDeleteWords}')
        waitIcon = QIcon(':/icons/wait.png')
        delIcon = QIcon(':/icons/delete.png')
        self.newWordListWidget.clear()
        self.needDeleteWordListWidget.clear()

        for word in needToDeleteWords:
            item = QListWidgetItem(word)
            item.setCheckState(Qt.Checked)
            item.setIcon(delIcon)
            self.needDeleteWordListWidget.addItem(item)

        for word in newWords:
            item = QListWidgetItem(word)
            item.setIcon(waitIcon)
            self.newWordListWidget.addItem(item)
        self.newWordListWidget.clearSelection()

        self.dictionaryComboBox.setEnabled(True)
        self.apiComboBox.setEnabled(True)
        self.deckComboBox.setEnabled(True)
        self.pullRemoteWordsBtn.setEnabled(True)
        self.queryBtn.setEnabled(self.newWordListWidget.count() > 0)
        self.syncBtn.setEnabled(self.newWordListWidget.count() == 0 and self.needDeleteWordListWidget.count() > 0)
        if self.needDeleteWordListWidget.count() == self.newWordListWidget.count() == 0:
            logger.info('无需同步')
            tooltip('无需同步')
        self.mainTab.setEnabled(True)

    @pyqtSlot()
    def on_queryBtn_clicked(self):
        logger.info('点击查询按钮')
        currentConfig = self.getAndSaveCurrentConfig()
        self.queryBtn.setEnabled(False)
        self.pullRemoteWordsBtn.setEnabled(False)
        self.syncBtn.setEnabled(False)

        wordList = []
        selectedWords = self.newWordListWidget.selectedItems()
        if selectedWords:
            # 如果选中单词则只查询选中的单词
            for wordItem in selectedWords:
                wordBundle = dict()
                row = self.newWordListWidget.row(wordItem)
                wordBundle['term'] = wordItem.text()
                for configName in BASIC_OPTION + EXTRA_OPTION:
                    wordBundle[configName] = currentConfig[configName]
                    wordBundle['row'] = row
                wordList.append(wordBundle)
        else:  # 没有选择则查询全部
            for row in range(self.newWordListWidget.count()):
                wordBundle = dict()
                wordItem = self.newWordListWidget.item(row)
                wordBundle['term'] = wordItem.text()
                for configName in BASIC_OPTION + EXTRA_OPTION:
                    wordBundle[configName] = currentConfig[configName]
                    wordBundle['row'] = row
                wordList.append(wordBundle)

        logger.info(f'待查询单词{wordList}')
        # 查询线程
        self.progressBar.setMaximum(len(wordList))
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
        wordItem = self.newWordListWidget.item(row)
        wordItem.setIcon(doneIcon)
        wordItem.setData(Qt.UserRole, result)

    @pyqtSlot(int)
    def on_thisRowFailed(self, row):
        failedIcon = QIcon(':/icons/failed.png')
        failedWordItem = self.newWordListWidget.item(row)
        failedWordItem.setIcon(failedIcon)

    @pyqtSlot()
    def on_allQueryDone(self):
        failed = []

        for i in range(self.newWordListWidget.count()):
            wordItem = self.newWordListWidget.item(i)
            if not wordItem.data(Qt.UserRole):
                failed.append(wordItem.text())

        if failed:
            logger.warning(f'查询失败或未查询:{failed}')

        self.pullRemoteWordsBtn.setEnabled(True)
        self.queryBtn.setEnabled(True)
        self.syncBtn.setEnabled(True)

    @pyqtSlot()
    def on_syncBtn_clicked(self):

        failedGenerator = (self.newWordListWidget.item(row).data(Qt.UserRole) is None for row in range(self.newWordListWidget.count()))
        if any(failedGenerator):
            if not askUser('存在未查询或失败的单词，确定要加入单词本吗？\n 你可以选择失败的单词点击 "查询按钮" 来重试。'):
                return

        currentConfig = self.getAndSaveCurrentConfig()
        model = getOrCreateModel(MODEL_NAME)
        getOrCreateModelCardTemplate(model, 'default')
        deck = getOrCreateDeck(self.deckComboBox.currentText(), model=model)

        logger.info('同步点击')
        audiosDownloadTasks = []
        newWordCount = self.newWordListWidget.count()

        # 判断是否需要下载发音
        if currentConfig['noPron']:
            logger.info('不下载发音')
            whichPron = None
        else:
            whichPron = 'AmEPron' if self.AmEPronRadioButton.isChecked() else 'BrEPron'
            logger.info(f'下载发音{whichPron}')

        added = 0
        for row in range(newWordCount):
            wordItem = self.newWordListWidget.item(row)
            wordItemData = wordItem.data(Qt.UserRole)
            if wordItemData:
                addNoteToDeck(deck, model, currentConfig, wordItemData)
                added += 1
                # 添加发音任务
                if whichPron and wordItemData.get(whichPron):
                    audiosDownloadTasks.append((f"{whichPron}_{wordItemData['term']}.mp3", wordItemData[whichPron],))
        mw.reset()

        logger.info(f'发音下载任务:{audiosDownloadTasks}')

        if audiosDownloadTasks:
            self.syncBtn.setEnabled(False)
            self.progressBar.setValue(0)
            self.progressBar.setMaximum(len(audiosDownloadTasks))
            if self.audioDownloadThread is not None:
                self.audioDownloadThread.requestInterruption()
                self.audioDownloadThread.quit()
                self.audioDownloadThread.wait()

            self.audioDownloadThread = QThread(self)
            self.audioDownloadThread.start()
            self.audioDownloadWorker = AudioDownloadWorker(audiosDownloadTasks)
            self.audioDownloadWorker.moveToThread(self.audioDownloadThread)
            self.audioDownloadWorker.tick.connect(lambda: self.progressBar.setValue(self.progressBar.value() + 1))
            self.audioDownloadWorker.start.connect(self.audioDownloadWorker.run)
            self.audioDownloadWorker.done.connect(lambda: tooltip(f'发音下载完成'))
            self.audioDownloadWorker.done.connect(self.audioDownloadThread.quit)
            self.audioDownloadWorker.start.emit()

        self.newWordListWidget.clear()

        needToDeleteWordItems = [
            self.needDeleteWordListWidget.item(row)
            for row in range(self.needDeleteWordListWidget.count())
            if self.needDeleteWordListWidget.item(row).checkState() == Qt.Checked
        ]
        needToDeleteWords = [i.text() for i in needToDeleteWordItems]

        deleted = 0

        if needToDeleteWords and askUser(f'确定要删除这些单词吗:{needToDeleteWords[:3]}...({len(needToDeleteWords)}个)', title='Dict2Anki', parent=self):
            needToDeleteWordNoteIds = getNotes(needToDeleteWords, currentConfig['deck'])
            mw.col.remNotes(needToDeleteWordNoteIds)
            deleted += 1
            mw.col.reset()
            mw.reset()
            for item in needToDeleteWordItems:
                self.needDeleteWordListWidget.takeItem(self.needDeleteWordListWidget.row(item))
            logger.info('删除完成')
        logger.info('完成')

        if not audiosDownloadTasks:
            tooltip(f'添加{added}个笔记\n删除{deleted}个笔记')
