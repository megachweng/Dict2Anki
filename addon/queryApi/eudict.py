import logging
import requests
from urllib3 import Retry
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from ..misc import AbstractQueryAPI
from bs4 import BeautifulSoup
from bs4.element import Comment
logger = logging.getLogger('dict2Anki.queryApi.youdao')
__all__ = ['API']


class Parser:
    def __init__(self, html, term):
        self._soap= BeautifulSoup(html, 'html.parser')
        self.term = term

    @property
    def definition(self) -> list:
        els = self._soap.select('div #ExpFCChild li') # 多词性
        els = self._soap.select('div #ExpFCChild .exp') if not els else els # 单一词性
        ret = []
        for el in els:
            ret.append(el.get_text(strip=True))
        return ret

    @property
    def pronunciations(self) -> dict:
        url = 'https://api.frdic.com/api/v2/speech/speakweb?'
        pron = {
            'AmEPhonetic': None,
            'AmEUrl': None,
            'BrEPhonetic': None,
            'BrEUrl': None
        }

        els = self._soap.select('.phonitic-line')
        if els:
            el = els[0]
            links = el.select('a')
            phons = el.select('.Phonitic')

            try:
                pron['BrEPhonetic'] = phons[0].get_text(strip=True)
            except KeyError:
                pass

            try:
                pron['BrEUrl'] = url + links[0]['data-rel']
            except (TypeError, KeyError):
                pass


            try:
                pron['AmEPhonetic'] = phons[1].get_text(strip=True)
            except KeyError:
                pass

            try:
                pron['AmEUrl'] = url + links[0]['data-rel']
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
        els = self._soap.select('div #ExpLJChild .lj_item')
        ret = []
        for el in els:
            try:
                line = el.select('p')
                sentence = line[0].get_text(strip=True)
                sentence_translation = line[1].get_text(strip=True)
                ret.append((sentence, sentence_translation))
            except KeyError as e:
                pass
        return ret

    @property
    def image(self)->str:
        els = self._soap.select('div .word-thumbnail-container img')
        ret = None
        if els:
            try:
                img = els[0]
                if 'title' not in img.attrs:
                    ret = img['src']
            except KeyError:
                pass
        return ret

    @property
    def phrase(self) -> list:
        els = self._soap.select('div #ExpSPECChild #phrase')
        ret = []
        for el in els:
            try:
                phrase = el.find('i').get_text(strip=True)
                exp = el.find('div').get_text(strip=True)
                ret.append((phrase, exp))
            except AttributeError:
                pass
        return ret

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
    name = '欧陆词典 API'
    timeout = 10
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    url = 'https://dict.eudic.net/dicts/en/{}'
    parser = Parser

    @classmethod
    def query(cls, word) -> dict:
        queryResult = None
        try:
            rsp = cls.session.get(cls.url.format(word), timeout=cls.timeout)
            logger.debug(f'code:{rsp.status_code}- word:{word} text:{rsp.text}')
            queryResult = cls.parser(rsp.text, word).result
        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(queryResult)
            return queryResult
