import string
import logging
import requests
from urllib3 import Retry
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from ..misc import AbstractQueryAPI
logger = logging.getLogger('dict2Anki.queryApi.bing')
__all__ = ['API']


class Parser:
    def __init__(self, json_obj, term):
        self._result = json_obj
        self.term = term

    @property
    def definition(self) -> list:
        return [''.join([d.get('pos', ''), d.get('def', '')]) for d in self._result.get('defs') or []]

    @property
    def pronunciations(self) -> dict:
        return self._result.get('pronunciation') or dict()

    @property
    def BrEPhonetic(self) -> str:
        """英式音标"""
        return self.pronunciations.get('BrE')

    @property
    def AmEPhonetic(self) -> str:
        """美式音标"""
        return self.pronunciations.get('AmE')

    @property
    def BrEPron(self) -> str:
        """英式发音url"""
        return self.pronunciations.get('BrEmp3')

    @property
    def AmEPron(self) -> str:
        """美式发音url"""
        return self.pronunciations.get('AmEmp3')

    @property
    def sentence(self) -> list:
        return [(s.get('eng'), s.get('chn'),) for s in self._result.get('sams') or []]

    @property
    def image(self) -> None:
        return None

    @property
    def result(self) -> dict:
        return {
            'term': self.term,
            'definition': self.definition,
            'phrase': None,
            'image': self.image,
            'sentence': self.sentence,
            'BrEPhonetic': self.BrEPhonetic,
            'AmEPhonetic': self.AmEPhonetic,
            'BrEPron': self.BrEPron,
            'AmEPron': self.AmEPron
        }


class API(AbstractQueryAPI):
    name = '必应 API'
    timeout = 10
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
    retries = Retry(total=5, backoff_factor=3, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    url = 'http://xtk.azurewebsites.net/BingDictService.aspx'
    parser = Parser

    @classmethod
    def query(cls, word) -> dict:
        validator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))  # 第三方Bing API查询包含标点的单词时有可能会报错，所以用空格替换所有标点
        query_result = None
        try:
            rsp = cls.session.get(cls.url, params=urlencode({'Word': word.translate(validator)}), timeout=cls.timeout)
            logger.debug(f'code:{rsp.status_code}- word:{word} text:{rsp.text}')
            query_result = cls.parser(rsp.json(), word).result
        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(query_result)
            return query_result
