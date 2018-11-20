import hashlib
import re
from abc import ABCMeta
from abc import abstractmethod
import time
from queue import Queue
from bs4 import BeautifulSoup
import requests
from threading import Thread
import itertools


class Dictionary(metaclass=ABCMeta):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'
    }
    timeout = 15
    signal = None

    @abstractmethod
    def login(self, username, password, session):
        pass

    @abstractmethod
    def getWordList(self):
        pass


class Eudict(Dictionary):
    def __init__(self):
        self.session = None

    def login(self, username, password):
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
        if 'EudicWeb' in requests.utils.dict_from_cookiejar(session.cookies).keys():
            self.session = session
            return True
        return False

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


class YoudaoDict(Dictionary):
    def __init__(self):
        self.timeout = 10
        self.cookie = None

    @staticmethod
    def __checkCookie(cookie):
        if cookie:
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', cookies=cookie)
            print(rsp.text)
            print(rsp.url)
            if 'account.youdao.com/login' not in rsp.url:
                return True
        return False

    def login(self, username, password, cookie):

        if self.__checkCookie(cookie):
            print('直接使用cookie')
            return cookie
        #
        # headers = {
        #     'Host': 'dict.youdao.com',
        #     'User-Agent': 'YoudaoDictPro/7.8.2.5 CFNetwork/974.2.1 Darwin/18.0.0',
        # }
        # params = (
        #     ('app', 'mobile'),
        #     ('product', 'DICT'),
        #     ('tp', 'urstoken'),
        #     ('cf', '7'),
        #     ('show', 'true'),
        #     ('format', 'json'),
        #     ('username', username),
        #     ('password', hashlib.md5(password.encode('utf-8')).hexdigest()),
        #     ('um', 'true'),
        # )
        # session = requests.session()
        # session.get('https://dict.youdao.com/login/acc/login', headers=headers, params=params, timeout=self.timeout)
        # cookie = requests.utils.dict_from_cookiejar(session.cookies)
        # if username.lower() in cookie.get('DICT_SESS', ''):
        #     self.cookie = cookie
        #     return cookie
        # return None

    def getWordList(self):
        def _getTotalPage():
            rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', timeout=self.timeout, cookies=self.cookie)
            return int(re.search('<a href="wordlist.p=(.*).tags=" class="next-page">最后一页</a>', rsp.text, re.M | re.I).group(1))

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
        threadPool = ThreadPool(3)

        for page in range(totalPages):
            threadPool.add_task(_getWordListPerPage, page)
        result = threadPool.wait_completion()

        result = list(itertools.chain(*result))
        return result


class ThreadPool:
    def __init__(self, number_of_workers):
        self.tasks_queue = Queue(number_of_workers)
        self.result_queue = Queue()
        for _ in range(number_of_workers):
            ThreadWorker(self.tasks_queue, self.result_queue)

    def add_task(self, func, *args, **kwargs):
        self.tasks_queue.put((func, args, kwargs))

    def wait_completion(self):
        self.tasks_queue.join()
        _result = []
        while not self.result_queue.empty():
            _result.append(self.result_queue.get())
        return _result


class ThreadWorker(Thread):
    def __init__(self, tasks_queue, result_queue):
        Thread.__init__(self)
        self.tasks_queue = tasks_queue
        self.result_queue = result_queue
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kwargs = self.tasks_queue.get()
            try:
                r = func(*args, **kwargs)
                self.result_queue.put(r)
            except Exception as e:
                self.result_queue.put(e)
            finally:
                self.tasks_queue.task_done()


if __name__ == '__main__':
    pass
