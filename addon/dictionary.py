import time
from abc import ABCMeta
from abc import abstractmethod

import requests


class Dictionary(metaclass=ABCMeta):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
    timeout = 30
    signal = None

    @abstractmethod
    def login(self, username, password):
        pass

    @abstractmethod
    def getWordList(self):
        pass


class Eudict(Dictionary):
    state = False

    def login(self, username, password):
        self.session = requests.session()
        data = {
            "UserName": username,
            "Password": password,
            "returnUrl": "http://my.eudic.net/studylist",
            "RememberMe": 'true'
        }
        r = self.session.post(url='https://dict.eudic.net/Account/Login?returnUrl=https://my.eudic.net/studylist', timeout=self.timeout, headers=self.headers, data=data)
        if '导入生词本' in r.text:
            self.state = True
        else:
            self.state = False
        return self.state

    def getWordList(self):
        data = {
            'columns[2][data]': 'word',
            'start': 0,
            'length': 1000000,
            'categoryid': -1,
            '_': int(time.time()) * 1000,
        }
        r = self.session.get(url='https://my.eudic.net/StudyList/WordsDataSource', timeout=self.timeout, data=data)
        wl = r.json()
        return list(set(word['uuid'] for word in wl['data']))

class Youdao:
    pass

if __name__ == '__main__':
    e = Eudict()
    if e.login('megachweng@163.com', 'cs123456'):
        print(e.getWordList())
    else:
        print('登录失败')
