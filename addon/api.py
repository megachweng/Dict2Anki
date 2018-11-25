import requests
from abc import ABCMeta, abstractmethod
from PyQt5.QtCore import QThread
from .signals import APISignals
from .threadpool import ThreadPool
from urllib.parse import urlencode
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from queue import Queue


class Parser(metaclass=ABCMeta):

    @abstractmethod
    def definitions(self):
        pass

    @abstractmethod
    def pronunciations(self):
        pass

    @abstractmethod
    def samples(self):
        pass

    @abstractmethod
    def image(self):
        pass


class YoudaoParser(Parser):
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


class YoudaoAPI(QThread):
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.1)
    s.mount('http://', HTTPAdapter(max_retries=retries))
    url = 'https://dict.youdao.com/jsonapi'
    params = {
        "dicts": {"count": 99, "dicts": [["ec", "pic_dict"], ["web_trans"], ["fanyi"], ["blng_sents_part"]]}
    }
    signal = APISignals()

    def __init__(self, parser, terms):
        super(YoudaoAPI, self).__init__()
        self.parser = parser
        self.terms = terms
        self.queryResults = Queue()
        self.failedQueries = Queue()

    def query(self, word) -> Parser:
        rsp = self.s.get(
            self.url,
            params=urlencode(dict(self.params, **{'q': word})),
            timeout=5
        )
        return self.parser(rsp.json(), word).json

    def run(self):
        self.signal.setTotalTasks.emit(len(self.terms))
        threadPool = ThreadPool(3, self.signal)

        for term in self.terms:
            try:
                threadPool.add_task(self.query, term)
                result = threadPool.wait_completion()[0]
                self.queryResults.put(result)
            except Exception as e:
                self.signal.exceptionOccurred.emit(e)
                self.failedQueries.put(term)


if __name__ == '__main__':
    pass
