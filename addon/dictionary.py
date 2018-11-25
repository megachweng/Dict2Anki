import hashlib
import re
import time
from PyQt5.QtCore import QThread
from bs4 import BeautifulSoup
import requests
import itertools
from .signals import DictSignals
from .threadpool import ThreadPool


class Eudict(QThread):
    signal = DictSignals()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }

    def __init__(self, username, password, cookie):
        super(Eudict, self).__init__()
        self.cookie = cookie
        self.username = username
        self.password = password
        self.timeout = 10
        self.remoteWordList = []

    @staticmethod
    def __checkCookie(cookie):
        if cookie:
            rsp = requests.get('https://my.eudic.net/studylist', cookies=cookie)
            if 'dict.eudic.net/account/login' not in rsp.url:
                return True
        return False

    def login(self, username, password, cookie):

        if self.__checkCookie(cookie):
            self.cookie = cookie
            return cookie

        data = {
            "UserName": username,
            "Password": password,
            "returnUrl": "http://my.eudic.net/studylist",
            "RememberMe": 'true'
        }
        session = requests.Session()
        session.post(
            url='https://dict.eudic.net/Account/Login?returnUrl=https://my.eudic.net/studylist',
            timeout=self.timeout,
            headers=self.headers,
            data=data
        )
        cookie = requests.utils.dict_from_cookiejar(session.cookies)
        if 'EudicWeb' in cookie.keys():
            self.cookie = cookie
            return cookie
        return None

    def getWordList(self):
        data = {
            'columns[2][data]': 'word',
            'start': 0,
            'length': 1000000,
            'categoryid': -1,
            '_': int(time.time()) * 1000,
        }
        r = requests.get(
            url='https://my.eudic.net/StudyList/WordsDataSource',
            timeout=self.timeout,
            data=data,
            headers=self.headers,
            cookies=self.cookie)
        wl = r.json()
        wordList = list(set(word['uuid'] for word in wl['data']))
        # update ui progressbar max value
        self.signal.setTotalTasks.emit(len(wordList))
        return wordList

    def run(self):
        try:
            if self.login(self.username, self.password, self.cookie):
                self.remoteWordList = self.getWordList()
        except Exception as e:
            self.signal.exceptionOccurred.emit(e)


class YoudaoDict(QThread):
    signal = DictSignals()

    def __init__(self, username, password, cookie):
        super(YoudaoDict, self).__init__()
        self.username = username
        self.password = password
        self.timeout = 10
        self.cookie = cookie
        self.remoteWordList = []

    @staticmethod
    def __checkCookie(cookie):
        if cookie:
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', cookies=cookie)
            print(rsp.url)
            if 'account.youdao.com/login' not in rsp.url:
                return True
        return False

    def login(self, username, password, cookie):

        if self.__checkCookie(cookie):
            self.cookie = cookie
            return cookie

        headers = {
            'Host': 'dict.youdao.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        }
        params = (
            ('app', 'mobile'),
            ('product', 'DICT'),
            ('tp', 'urstoken'),
            ('cf', '7'),
            ('show', 'true'),
            ('format', 'json'),
            ('username', username),
            ('password', hashlib.md5(password.encode('utf-8')).hexdigest()),
            ('um', 'true'),
        )
        session = requests.session()
        session.get('https://dict.youdao.com/login/acc/login', headers=headers, params=params, timeout=self.timeout)
        cookie = requests.utils.dict_from_cookiejar(session.cookies)
        if username and username.lower() in cookie.get('DICT_SESS', ''):
            self.cookie = cookie
            return cookie
        return None

    def getWordList(self):
        def _getTotalPage():
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', timeout=self.timeout, cookies=self.cookie)
            groups = re.search('<a href="wordlist.p=(.*).tags=" class="next-page">最后一页</a>', rsp.text, re.M | re.I)
            if groups:
                total = int(groups.group(1)) - 1
            else:
                total = 1
            return total

        def _getWordListPerPage(page_num):
            words = []
            soup = BeautifulSoup(requests.get('http://dict.youdao.com/wordbook/wordlist', params={'p': page_num}, cookies=self.cookie).text, features='html.parser')
            table = soup.find(id='wordlist').table.tbody
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                words.append(cols[1].div.a.text.strip())
            return words

        totalPages = _getTotalPage()
        # update ui progressbar max value
        self.signal.setTotalTasks.emit(totalPages)
        threadPool = ThreadPool(3, self.signal)

        for page in range(totalPages):
            threadPool.add_task(_getWordListPerPage, page)
        result = threadPool.wait_completion()
        result = list(itertools.chain(*result))
        return result

    def run(self):
        try:
            if self.login(self.username, self.password, self.cookie):
                self.remoteWordList = self.getWordList()
        except Exception as e:
            self.signal.exceptionOccurred.emit(e)


if __name__ == '__main__':
    pass
