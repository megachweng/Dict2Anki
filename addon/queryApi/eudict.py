import logging
import requests
from urllib3 import Retry
from requests.adapters import HTTPAdapter
from ..misc import AbstractQueryAPI
from bs4 import BeautifulSoup
logger = logging.getLogger('dict2Anki.queryApi.eudict')
__all__ = ['API']


class Parser:
    def __init__(self, html, term):
        self._soap = BeautifulSoup(html, 'html.parser')
        self.term = term

    @staticmethod
    def __fix_url_without_http(url):
        if url[0:2] == '//':
            return 'https:' + url
        else:
            return url

    @property
    def definition(self) -> list:
        ret = []
        div = self._soap.select('div #ExpFCChild')
        if not div:
            return ret

        div = div[0]
        els = div.select('li') # 多词性
        if not els: # 单一词性
            els = div.select('.exp')
        if not els: # 还有一奇怪的情况，不在任何的标签里面
            trans = div.find(id='trans')
            trans.replace_with('') if trans else ''

            script = div.find('script')
            script.replace_with('') if script else ''

            for atag in div.find_all('a'): # 赞踩这些字样
                atag.replace_with('')
            els = [div]

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
        if not els:
            return pron

        el = els[0]
        links = el.select('a')
        phons = el.select('.Phonitic')

        if not links:
            # 可能是只有一个发音的情况
            links = self._soap.select('div .gv_details .voice-button')
            # 返回两个相同的。下载只会按照用户选择下载一个，这样至少可以保证总是有发音
            links = [links[0], links[0]] if links else ''

        try:
            pron['BrEPhonetic'] = phons[0].get_text(strip=True)
        except (KeyError, IndexError):
            pass

        try:
            pron['BrEUrl'] = "{}{}".format('' if 'http' in links[0]['data-rel'] else url, links[0]['data-rel'])
        except (TypeError, KeyError, IndexError):
            pass

        try:
            pron['AmEPhonetic'] = phons[1].get_text(strip=True)
        except (KeyError, IndexError):
            pass

        try:
            pron['AmEUrl'] = "{}{}".format('' if 'http' in links[1]['data-rel'] else url, links[1]['data-rel'])
        except (TypeError, KeyError, IndexError):
            pass

        return pron

    @property
    def BrEPhonetic(self) -> str:
        """英式音标"""
        return self.pronunciations['BrEPhonetic']

    @property
    def AmEPhonetic(self) -> str:
        """美式音标"""
        return self.pronunciations['AmEPhonetic']

    @property
    def BrEPron(self) -> str:
        """英式发音url"""
        return self.pronunciations['BrEUrl']

    @property
    def AmEPron(self) -> str:
        """美式发音url"""
        return self.pronunciations['AmEUrl']

    @property
    def sentence(self) -> list:
        els = self._soap.select('div #ExpLJChild .lj_item')
        ret = []
        for el in els:
            try:
                line = el.select('p')
                sentence = "".join([ str(c) for c in line[0].contents])
                sentence_translation = line[1].get_text(strip=True)
                ret.append((sentence, sentence_translation))
            except KeyError as e:
                pass
        return ret

    @property
    def image(self) -> str:
        els = self._soap.select('div .word-thumbnail-container img')
        ret = None
        if els:
            try:
                img = els[0]
                if 'title' not in img.attrs:
                    ret = self.__fix_url_without_http(img['src'])
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
                exp = el.find(class_='exp').get_text(strip=True)
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
            logger.debug(f'code:{rsp.status_code}- word:{word} text:{rsp.text[:100]}')
            queryResult = cls.parser(rsp.text, word).result
        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(queryResult)
            return queryResult
