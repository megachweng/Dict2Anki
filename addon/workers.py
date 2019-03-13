import logging
import time
from itertools import chain
import requests
import json
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from concurrent.futures import ThreadPoolExecutor, as_completed
from .constants import VERSION, VERSION_CHECK_API


class VersionCheckWorker(QObject):
    haveNewVersion = pyqtSignal(str, str)
    finished = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.UpdateCheckWorker')

    def run(self):
        try:
            self.logger.info('检查新版本')
            rsp = requests.get(VERSION_CHECK_API, timeout=20).json()
            version = rsp['tag_name']
            changeLog = rsp['body']
            if version != VERSION:
                self.logger.info(f'检查到新版本{version}')
                self.haveNewVersion.emit(version.strip(), changeLog.strip())
            else:
                self.logger.info(f'当前为最新版本:{VERSION}')
        except Exception as e:
            self.logger.error(f'版本检查失败{e}')

        finally:
            self.finished.emit()


class LoginWorker(QObject):
    start = pyqtSignal()
    logSuccess = pyqtSignal(str)
    logFailed = pyqtSignal()

    def __init__(self, LoginFunc, *args, **kwargs):
        super().__init__()
        self.LoginFunc = LoginFunc
        self.args = args
        self.kwargs = kwargs

    def run(self):
        cookie = self.LoginFunc(*self.args, **self.kwargs)
        if cookie:
            self.logSuccess.emit(json.dumps(cookie))
        else:
            self.logFailed.emit()


class RemoteWordFetchingWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    done = pyqtSignal()
    doneThisGroup = pyqtSignal(list)
    logger = logging.getLogger('dict2Anki.workers.RemoteWordFetchingWorker')

    def __init__(self, selectedDict, selectedGroups: [tuple]):
        super().__init__()
        self.selectedDict = selectedDict
        self.selectedGroups = selectedGroups

    def run(self):
        currentThread = QThread.currentThread()

        def _pull(*args):
            if currentThread.isInterruptionRequested():
                return
            wordPerPage = self.selectedDict.getWordsByPage(*args)
            # self.done_this_page.emit(wordPerPage)
            return wordPerPage

        for groupName, groupId in self.selectedGroups:
            total = self.selectedDict.getTotalPage(groupName, groupId)

            with ThreadPoolExecutor(max_workers=3) as executor:
                futureToWords = [executor.submit(_pull, i, groupName, groupId) for i in range(total)]
                remoteWordList = list(chain(*[ft.result() for ft in as_completed(futureToWords)]))
                self.doneThisGroup.emit(remoteWordList)
            self.tick.emit()
        self.done.emit()


class QueryWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    thisRowDone = pyqtSignal(int, dict)
    thisRowFailed = pyqtSignal(int)
    allQueryDone = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.QueryWorker')

    def __init__(self, wordList: [dict], api):
        super().__init__()
        self.wordList = wordList
        self.api = api

    def run(self):
        currentThread = QThread.currentThread()

        def _query(word, row):
            if currentThread.isInterruptionRequested():
                return
            queryResult = self.api.query(word)
            if queryResult:
                self.logger.info(f'查询成功: {word} -- {queryResult}')
                self.thisRowDone.emit(row, queryResult)
            else:
                self.logger.warning(f'查询失败: {word}')
                self.thisRowFailed.emit(row)

            self.tick.emit()
            return queryResult

        with ThreadPoolExecutor(max_workers=3) as executor:
            for word in self.wordList:
                executor.submit(_query, word['term'], word['row'])

        self.allQueryDone.emit()
