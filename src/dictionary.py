import hashlib
import re
import time
from itertools import chain
import requests
import logging
from bs4 import BeautifulSoup
from .signals import DictSIG
from math import ceil
from PyQt5.QtCore import QObject, pyqtSlot


class Youdao(QObject):
    timeout = 10

    def __init__(self, username, password, cookie):
        super().__init__()
        self.SIG = DictSIG()
        self.username = username
        self.password = password
        self.cookie = cookie
        self.logger = logging.getLogger('Youdao')

    def __checkCookie(self):
        if self.cookie:
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', cookies=self.cookie)
            if 'account.youdao.com/login' not in rsp.url:
                return True
        return False

    def login(self):
        if self.__checkCookie():
            self.SIG.log.emit('cookie有效，直接使用cookie')
            return True
        self.SIG.log.emit('cookie无效，重新登录')
        headers = {
            'Host': 'dict.youdao.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) \
                    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        }

        params = (('app', 'mobile'),
                  ('product', 'DICT'),
                  ('tp', 'urstoken'),
                  ('cf', '7'),
                  ('show', 'true'),
                  ('format', 'json'),
                  ('username', self.username),
                  ('password', hashlib.md5(self.password.encode('utf-8')).hexdigest()),
                  ('um', 'true'),)
        session = requests.session()
        try:
            session.get('https://dict.youdao.com/login/acc/login', headers=headers, params=params, timeout=self.timeout)
            cookie = requests.utils.dict_from_cookiejar(session.cookies)
            if self.username and self.username.lower() in cookie.get('DICT_SESS', ''):
                self.cookie = cookie
                self.SIG.log.emit(f'登录成功:{cookie}')
                self.SIG.saveCookie.emit(cookie)
                return True
            else:
                self.SIG.log.emit('登录失败')
                return False
        except Exception as e:
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit(f'网络异常:{e}')
            return False

    def getTotalPage(self):
        try:
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', timeout=self.timeout, cookies=self.cookie)
            groups = re.search('<a href="wordlist.p=(.*).tags=" class="next-page">最后一页</a>', rsp.text, re.M | re.I)
            if groups:
                total = int(groups.group(1)) - 1
            else:
                total = 1
            self.SIG.totalTasks.emit(total)
            self.SIG.log.emit(f"总页数:{total}")
            return total
        except Exception as e:
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit('网络异常')

    def getWordPerPage(self, pageNumber):
        words = []
        try:
            self.SIG.log.emit(f'获取单词本第:{pageNumber + 1}页')
            rsp = requests.get(
                'http://dict.youdao.com/wordbook/wordlist',
                params={'p': pageNumber},
                cookies=self.cookie
            )
            soup = BeautifulSoup(rsp.text, features='html.parser')
            table = soup.find(id='wordlist').table.tbody
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                words.append(cols[1].div.a.text.strip())
            self.SIG.progress.emit()
        except Exception as e:
            self.SIG.progress.emit()
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit('网络异常')
        finally:
            return words

    @pyqtSlot()
    def run(self):
        if self.login():
            words = chain(*[self.getWordPerPage(n) for n in range(self.getTotalPage())])
            self.SIG.wordsReady.emit(list(words))


class Eudict(QObject):
    timeout = 10
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) \
                            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }

    def __init__(self, username, password, cookie):
        super().__init__()
        self.SIG = DictSIG()
        self.username = username
        self.password = password
        self.cookie = cookie
        self.logger = logging.getLogger('Youdao')

    def __checkCookie(self):
        if self.cookie:
            rsp = requests.get('https://my.eudic.net/studylist', cookies=self.cookie, headers=self.headers)
            if 'dict.eudic.net/account/login' not in rsp.url:
                return True
        return False

    def login(self):

        if self.__checkCookie():
            self.SIG.log.emit('cookie有效，直接使用cookie')
            return True
        self.SIG.log.emit('cookie无效，重新登录')

        data = {
            "UserName": self.username,
            "Password": self.password,
            "returnUrl": "http://my.eudic.net/studylist",
            "RememberMe": 'true'
        }
        session = requests.Session()
        try:
            session.post(
                url='https://dict.eudic.net/Account/Login?returnUrl=https://my.eudic.net/studylist',
                timeout=self.timeout,
                headers=self.headers,
                data=data
            )
            cookie = requests.utils.dict_from_cookiejar(session.cookies)
            if 'EudicWeb' in cookie.keys():
                self.cookie = cookie
                self.SIG.log.emit(f'登录成功:{cookie}')
                self.SIG.saveCookie.emit(cookie)
                return True
            else:
                self.SIG.log.emit('登录失败')
                return False
        except Exception as e:
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit(f'网络异常:{e}')
            return False

    def getTotalPage(self):
        try:
            r = requests.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=self.timeout,
                cookies=self.cookie,
                data={'categoryid': -1}
            )
            records = r.json()['recordsTotal']
            total = ceil(records / 100)
            self.SIG.totalTasks.emit(total)
            self.SIG.log.emit(f"总页数:{total}")
            return total
        except Exception as e:
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit(f'网络异常{e}')

    def getWordPerPage(self, pageNumber):
        wordList = []
        data = {
            'columns[2][data]': 'word',
            'start': pageNumber * 100,
            'length': 100,
            'categoryid': -1,
            '_': int(time.time()) * 1000,
        }
        try:
            self.SIG.log.emit(f'获取单词本第:{pageNumber}页')
            r = requests.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=self.timeout,
                data=data,
                headers=self.headers,
                cookies=self.cookie)
            wl = r.json()
            wordList = list(set(word['uuid'] for word in wl['data']))
        except Exception as e:
            self.SIG.exceptionOccurred.emit(e)
            self.SIG.log.emit(f'网络异常{e}')
        finally:
            self.SIG.progress.emit()
            return wordList

    @pyqtSlot()
    def run(self):
        if self.login():
            words = [self.getWordPerPage(n) for n in range(self.getTotalPage())]
            chained_words = list(chain(*words))
            self.SIG.wordsReady.emit(chained_words)
