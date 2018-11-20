import json
from abc import ABCMeta, abstractmethod
import requests
from urllib.parse import urlencode


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


class API(metaclass=ABCMeta):
    api_address = None

    @abstractmethod
    def query(self, word):
        pass


class YoudaoParser(Parser):
    def __init__(self, json_obj):
        self._result = json_obj

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
    def image(self) -> list:
        try:
            return [i['image'] for i in self._result['pic_dict']['pic']][0]
        except KeyError:
            return []


class YoudaoAPI(API):
    url = 'https://dict.youdao.com/jsonapi'
    params = {
        "dicts": {"count": 99, "dicts": [["ec", "pic_dict"], ["web_trans"], ["fanyi"], ["blng_sents_part"]]}
    }

    def __init__(self, parser):
        self.parser = parser

    def query(self, word) -> Parser:
        rsp = requests.get(
            self.url,
            params=urlencode(dict(self.params, **{'q': word})),
            timeout=10
        )
        return self.parser(rsp.json())


if __name__ == '__main__':
    pass
