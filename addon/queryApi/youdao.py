import logging
import requests
from urllib3 import Retry
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from ..misc import AbstractQueryAPI
logger = logging.getLogger('dict2Anki.queryApi.youdao')
__all__ = ['API']


class Parser:
    def __init__(self, json_obj, term):
        self._result = json_obj
        self.term = term

    @property
    def definition(self) -> list:
        try:
            ec = [d['tr'][0]['l']['i'][0] for d in self._result['ec']['word'][0]['trs']][:3]
        except KeyError:
            ec = []

        try:
            ee = [ d['pos'] + d['tr'][0]['l']['i'] for d in self._result['ee']['word']['trs']]
        except KeyError:
            ee = []
        
        ec += ee

        try:
            web_trans = [w['value'] for w in self._result['web_trans']['web-translation'][0]['trans']][:3]
        except KeyError:
            web_trans = []
        return ec if ec else web_trans

    @property
    def pronunciations(self) -> dict:
        url = 'http://dict.youdao.com/dictvoice?audio='
        pron = {
            'AmEPhonetic': None,
            'AmEUrl': None,
            'BrEPhonetic': None,
            'BrEUrl': None
        }
        try:
            pron['AmEPhonetic'] = self._result['simple']['word'][0]['usphone']
        except KeyError:
            pass

        try:
            pron['BrEPhonetic'] = self._result['simple']['word'][0]['ukphone']
        except KeyError:
            pass

        try:
            pron['AmEUrl'] = url + self._result['simple']['word'][0]['usspeech']
        except (TypeError, KeyError):
            pass

        try:
            pron['BrEUrl'] = url + self._result['simple']['word'][0]['ukspeech']
        except (TypeError, KeyError):
            pass

        return pron

    @property
    def BrEPhonetic(self)->str:
        """英式音标"""
        return self.pronunciations['BrEPhonetic']

    @property
    def AmEPhonetic(self)->str:
        """美式音标"""
        return self.pronunciations['AmEPhonetic']

    @property
    def BrEPron(self)->str:
        """英式发音url"""
        return self.pronunciations['BrEUrl']

    @property
    def AmEPron(self)->str:
        """美式发音url"""
        return self.pronunciations['AmEUrl']

    @property
    def sentence(self) -> list:
        try:
            return [(s['sentence'], s['sentence-translation'],) for s in self._result['blng_sents_part']['sentence-pair']]
        except KeyError:
            return []

    @property
    def image(self)->str:
        try:
            return [i['image'] for i in self._result['pic_dict']['pic']][0]
        except (KeyError, IndexError):
            return None

    @property
    def phrase(self) -> list:
        phrase = self._result.get('phrs', dict()).get('phrs', [])
        return [
            (
                p.get('phr', dict()).get('headword', dict()).get('l', dict()).get('i', None),
                p.get('phr', dict()).get('trs', [dict()])[0].get('tr', dict()).get('l', dict()).get('i', None)
            )
            for p in phrase if phrase
        ]

    @property
    def result(self):
        return {
            'term': self.term,
            'definition': self.definition,
            'phrase': self.phrase,
            'image': self.image,
            'sentence': self.sentence,
            'BrEPhonetic': self.BrEPhonetic,
            'AmEPhonetic': self.AmEPhonetic,
            'BrEPron': self.BrEPron,
            'AmEPron': self.AmEPron
        }


class API(AbstractQueryAPI):
    name = '有道 API'
    timeout = 10
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    url = 'https://dict.youdao.com/jsonapi'
    params = {"dicts": {"count": 99, "dicts": [["ec", "ee", "phrs", "pic_dict"], ["web_trans"], ["fanyi"], ["blng_sents_part"]]}}
    parser = Parser

    @classmethod
    def query(cls, word) -> dict:
        queryResult = None
        try:
            rsp = cls.session.get(cls.url, params=urlencode(dict(cls.params, **{'q': word})), timeout=cls.timeout)
            logger.debug(f'code:{rsp.status_code}- word:{word} text:{rsp.text}')
            queryResult = cls.parser(rsp.json(), word).result
        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(queryResult)
            return queryResult
