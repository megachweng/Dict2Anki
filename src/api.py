from urllib.parse import urlencode

import requests
from PyQt5.QtCore import QObject, pyqtSlot
from .pool import ThreadPool

from .signals import APISIG, AudioDownloaderSIG


class YoudaoParser:
    def __init__(self, json_obj, term):
        self._result = json_obj
        self.term = term

    @property
    def definitions(self) -> list:
        try:
            ec = [d['tr'][0]['l']['i'][0] for d in self._result['ec']['word'][0]['trs']][:3]
        except KeyError:
            ec = []

        try:
            web_trans = [w['value'] for w in self._result['web_trans']['web-translation'][0]['trans']][:3]
        except KeyError:
            web_trans = []
        return ec if ec else web_trans

    @property
    def pronunciations(self) -> dict:
        url = 'http://dict.youdao.com/dictvoice?audio='
        pron = {
            'us_phonetic': None,
            'us_url': None,
            'uk_phonetic': None,
            'uk_url': None
        }
        try:
            pron['us_phonetic'] = self._result['simple']['word'][0]['usphone']
            pron['us_url'] = url + self._result['simple']['word'][0]['usspeech']
            pron['uk_phonetic'] = self._result['simple']['word'][0]['ukphone']
            pron['uk_url'] = url + self._result['simple']['word'][0]['ukspeech']
        except KeyError:
            pass
        return pron

    @property
    def samples(self):
        try:
            return [(s['sentence'], s['sentence-translation'],) for s in self._result['blng_sents_part']['sentence-pair']]
        except KeyError:
            return []

    @property
    def image(self):
        try:
            return [i['image'] for i in self._result['pic_dict']['pic']][0]
        except KeyError:
            return None

    @property
    def json(self):
        return {
            "term": self.term,
            "definitions": self.definitions,
            "image": self.image,
            "samples": self.samples,
            "pronunciations": self.pronunciations
        }


class YoudaoAPI(QObject):
    timeout = 10
    s = requests.Session()
    url = 'https://dict.youdao.com/jsonapi'
    params = {"dicts": {"count": 99, "dicts": [["ec", "pic_dict"], ["web_trans"], ["fanyi"], ["blng_sents_part"]]}}

    def __init__(self, wordList, parser):
        super().__init__()
        self.SIG = APISIG()
        self.wordList = wordList
        self.parser = parser

    def query(self, word):
        try:
            rsp = self.s.get(
                self.url,
                params=urlencode(dict(self.params, **{'q': word})),
            )
            jsonResult = self.parser(rsp.json(), word).json
            self.SIG.log.emit(f"查询:{word}")
            return jsonResult
        except Exception as e:
            self.SIG.log.emit(f"查询:{word}异常")
            self.SIG.exceptionOccurred.emit(e)
        finally:
            self.SIG.progress.emit()

    @pyqtSlot()
    def run(self):
        self.SIG.totalTasks.emit(len(self.wordList))
        TP = ThreadPool(2)
        for word in self.wordList:
            TP.add_task(self.query, word)
        queryResults = TP.wait_complete()
        self.SIG.wordsReady.emit(queryResults)


class AudioDownloader(QObject):
    timeout = 15
    s = requests.Session()

    def __init__(self, audios):
        super().__init__()
        self.SIG = AudioDownloaderSIG()
        self.audios = audios
        self.SIG.log.emit(f'待下载任务{audios}')

    def _download(self, file_name, url):
        try:
            r = self.s.get(url, stream=True)
            with open(f'{file_name}.mp3', 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            self.SIG.log.emit(f'{file_name} 下载完成')
        except Exception as e:
            self.SIG.log.emit(f'下载{file_name}:{url}异常: {e}')
        finally:
            self.SIG.progress.emit()

    @pyqtSlot()
    def run(self):
        self.SIG.totalTasks.emit(len(self.audios))
        TP = ThreadPool(2)
        for file_name, url in self.audios:
            TP.add_task(self._download, file_name, url)
        TP.wait_complete()
        self.SIG.downloadFinished.emit()
