import json
import logging
import requests
from urllib3 import Retry
from itertools import chain
from .misc import ThreadPool
from requests.adapters import HTTPAdapter
from .constants import VERSION, VERSION_CHECK_API
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class VersionCheckWorker(QObject):
    haveNewVersion = pyqtSignal(str, str)
    finished = pyqtSignal()
    start = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.UpdateCheckWorker')

    def run(self):
        try:
            self.logger.info('检查新版本')
            rsp = requests.get(VERSION_CHECK_API, timeout=20).json()
            version = rsp['tag_name']
            changeLog = rsp['body']
            if version != VERSION:
                self.logger.info(f'检查到新版本:{version}--{changeLog.strip()}')
                self.haveNewVersion.emit(version.strip(), changeLog.strip())
            else:
                self.logger.info(f'当前为最新版本:{VERSION}')
        except Exception as e:
            self.logger.error(f'版本检查失败{e}')

        finally:
            self.finished.emit()


class LoginStateCheckWorker(QObject):
    start = pyqtSignal()
    logSuccess = pyqtSignal(str)
    logFailed = pyqtSignal()

    def __init__(self, checkFn, cookie):
        super().__init__()
        self.checkFn = checkFn
        self.cookie = cookie

    def run(self):
        loginState = self.checkFn(self.cookie)
        if loginState:
            self.logSuccess.emit(json.dumps(self.cookie))
        else:
            self.logFailed.emit()


class RemoteWordFetchingWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    setProgress = pyqtSignal(int)
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
            self.tick.emit()
            return wordPerPage

        for groupName, groupId in self.selectedGroups:
            totalPage = self.selectedDict.getTotalPage(groupName, groupId)
            self.setProgress.emit(totalPage)
            with ThreadPool(max_workers=3) as executor:
                for i in range(totalPage):
                    executor.submit(_pull, i, groupName, groupId)
            remoteWordList = list(chain(*[ft for ft in executor.result]))
            self.doneThisGroup.emit(remoteWordList)

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

        with ThreadPool(max_workers=3) as executor:
            for word in self.wordList:
                executor.submit(_query, word['term'], word['row'])

        self.allQueryDone.emit()


class AudioDownloadWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    done = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.AudioDownloadWorker')
    retries = Retry(total=5, backoff_factor=3, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    def __init__(self, audios: [tuple]):
        super().__init__()
        self.audios = audios

    def run(self):
        currentThread = QThread.currentThread()

        def __download(fileName, url):
            try:
                if currentThread.isInterruptionRequested():
                    return
                r = self.session.get(url, stream=True)
                with open(fileName, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                self.logger.info(f'{fileName} 下载完成')
            except Exception as e:
                self.logger.warning(f'下载{fileName}:{url}异常: {e}')
            finally:
                self.tick.emit()

        with ThreadPool(max_workers=3) as executor:
            for fileName, url in self.audios:
                executor.submit(__download, fileName, url)
        self.done.emit()
