import time
from abc import ABCMeta, abstractmethod
import requests
import random
from json.decoder import JSONDecodeError


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


class API(Parser, metaclass=ABCMeta):
    api_address = None

    @abstractmethod
    def query(self, word):
        pass


class BingAPI(API):
    session = requests.Session()
    api_address = 'http://xtk.azurewebsites.net/BingDictService.aspx'
    result = None

    def query(self, word):
        time.sleep(random.choice(range(5)))
        r = self.session.get(url=self.api_address, params={'Word': word})
        try:
            self.result = r.json()
        except JSONDecodeError:
            pass
        return self.result

    @property
    def definitions(self):
        return [f"{r.get('def', '')} {r.get('pos','')}" for r in self.result.get('defs', [dict()])]

    @property
    def pronunciations(self):
        pron = self.result.get('pronunciation', dict())
        return {
            'American': {'phonetic': pron.get('AmE', None), 'audio': pron.get('AmEmp3', None)},
            'British': {'phonetic': pron.get('BrE', None), 'audio': pron.get('BrEmp3', None)},
        }

    @property
    def samples(self):
        sams = self.result.get('sams', [dict()])
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
