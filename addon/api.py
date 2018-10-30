import time
from abc import ABCMeta, abstractmethod
import requests
import random
from json.decoder import JSONDecodeError


class Parser(metaclass=ABCMeta):

    @abstractmethod
    def term(self):
        pass

    @abstractmethod
    def definitions(self):
        pass

    @abstractmethod
    def BrEPron(self):
        pass

    @abstractmethod
    def AmEPron(self):
        pass

    @abstractmethod
    def BrEPhonetic(self):
        pass

    @abstractmethod
    def AmEPhonetic(self):
        pass

    @abstractmethod
    def samples(self):
        pass

    @abstractmethod
    def image(self):
        pass


class API(Parser, metaclass=ABCMeta):
    api_address = None

    @abstractmethod
    def query(self, word):
        pass


class BingAPI(API):
    session = requests.Session()
    api_address = 'http://xtk.azurewebsites.net/BingDictService.aspx'
    _result = None
    _term = None

    def query(self, word):
        self._term = word
        time.sleep(random.choice(range(5)))
        r = self.session.get(url=self.api_address, params={'Word': word})
        try:
            self._result = r.json()
        except JSONDecodeError:
            pass
        return dict(
            term=self.term,
            definitions=self.definitions,
            samples=self.samples,
            image=self.image,
            BrEPhonetic=self.BrEPhonetic,
            BrEPron=self.BrEPron,
            AmEPhonetic=self.AmEPhonetic,
            AmEPron=self.AmEPron
        )

    @property
    def term(self):
        return self._term.strip()

    @property
    def definitions(self):
        return [f"{r.get('def', '')} {r.get('pos','')}" for r in self._result.get('defs', [dict()])]

    @property
    def pronunciations(self):
        pron = self._result.get('pronunciation', dict())
        return {
            'American': {'phonetic': pron.get('AmE', None), 'audio': pron.get('AmEmp3', None)},
            'British': {'phonetic': pron.get('BrE', None), 'audio': pron.get('BrEmp3', None)},
        }

    @property
    def pron(self):
        return self._result.get('pronunciation', dict())

    @property
    def BrEPhonetic(self):
        return self.pron.get('BrE', None)

    @property
    def BrEPron(self):
        return self.pron.get('BrEmp3', None)

    @property
    def AmEPhonetic(self):
        return self.pron.get('AmE', None)

    @property
    def AmEPron(self):
        return self.pron.get('AmEmp3', None)

    @property
    def samples(self):
        sams = self._result.get('sams', [dict()])
        return [{'chn': s.get('chn', None), 'eng': s.get('eng')} for s in sams]

    @property
    def image(self):
        return None


class YoudaoAPI:
    pass


if __name__ == '__main__':
    from pprint import pprint

    bing = BingAPI()
    pprint(bing.query('apple'), indent=4)
    pprint(bing.definitions)
    pprint(bing.pronunciations)
    pprint(bing.samples)
