import re
import hashlib
import logging
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from ..misc import AbstractDictionary
logger = logging.getLogger('dict2Anki.dictionary.youdao')


class Youdao(AbstractDictionary):
    name = '有道词典'
    timeout = 10
    headers = {
        'Host': 'dict.youdao.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    def __init__(self):
        self.groups = []

    def login(self, username: str, password: str, cookie: dict = None) -> dict:
        """
        登陆
        :param username: 用户名
        :param password: 密码
        :param cookie: cookie
        :return: cookie dict
        """
        self.session.cookies.clear()
        if cookie and self._checkCookie(cookie):
            return cookie
        else:
            return self._login(username, password)

    def _checkCookie(self, cookie) -> bool:
        """
        cookie有效性检验
        :param cookie:
        :return: bool
        """
        rsp = requests.get('http://dict.youdao.com/wordbook/wordlist', cookies=cookie, headers=self.headers)
        if 'account.youdao.com/login' not in rsp.url:
            self.indexSoup = BeautifulSoup(rsp.text, features="html.parser")
            logger.info('Cookie有效')
            cookiesJar = requests.utils.cookiejar_from_dict(cookie, cookiejar=None, overwrite=True)
            self.session.cookies = cookiesJar
            return True
        logger.info('Cookie失效')
        return False

    def _login(self, username: str, password: str) -> dict:
        """账号和密码登陆"""
        data = (('app', 'mobile'),
                ('product', 'DICT'),
                ('tp', 'urstoken'),
                ('cf', '7'),
                ('show', 'true'),
                ('format', 'json'),
                ('username', username),
                ('password', hashlib.md5(password.encode('utf-8')).hexdigest()),
                ('um', 'true'),)
        try:
            self.session.post(
                url='https://dict.youdao.com/login/acc/login',
                timeout=self.timeout,
                headers=self.headers,
                data=data
            )
            cookie = requests.utils.dict_from_cookiejar(self.session.cookies)
            if username and username.lower() in cookie.get('DICT_SESS', ''):
                #  登陆后获取单词本首页的soup对象
                rsp = self.session.get('http://dict.youdao.com/wordbook/wordlist', timeout=self.timeout)
                self.indexSoup = BeautifulSoup(rsp.text, features="html.parser")
                logger.info('登陆成功')
                return cookie
            else:
                logger.error('登陆失败')
                return {}
        except Exception as error:
            logger.exception(f'网络异常:{error}')
            return {}

    def getGroups(self) -> [(str, int)]:
        """
        获取单词本分组
        :return: [(group_name,group_id)]
        """
        elements = self.indexSoup.find('select', id='select_category')
        groups = []
        if elements:
            groups = elements.find_all('option')
            groups = [(e.text, e['value']) for e in groups]
        logger.info(f'单词本分组:{groups}')
        self.groups = groups

        return groups

    def getTotalPage(self, groupName: str, groupId: int) -> int:
        """
        获取分组下总页数
        :param groupName: 分组名称
        :param groupId:分组id
        :return:
        """
        totalPages = 1
        try:
            r = self.session.get(
                url='http://dict.youdao.com/wordbook/wordlist',
                timeout=self.timeout,
                params={'tags': groupId}
            )
            soup = BeautifulSoup(r.text, features='html.parser')
            pagination = soup.find('div', id='pagination')
            if pagination:
                finalPageHref = pagination.find_all('a', class_='next-page')[-1].get('href')
                groups = re.search(r"wordlist\?p=(\d*)", finalPageHref)
                if groups:
                    totalPages = int(groups.group(1))
            else:
                totalPages = 1
        except Exception as error:
            logger.exception(f'网络异常{error}')

        finally:
            totalPages = totalPages - 1 if totalPages > 1 else totalPages
            logger.info(f'该分组({groupName}-{groupId})下共有{totalPages}页')
            return totalPages

    def getWordsByPage(self, pageNo: int, groupName: str, groupId: str) -> [str]:
        """
        获取分组下每一页的单词
        :param pageNo: 页数
        :param groupName: 分组名
        :param groupId: 分组id
        :return:
        """
        wordList = []
        try:
            logger.info(f'获取单词本(f{groupName}-{groupId})第:{pageNo + 1}页')
            rsp = self.session.get(
                'http://dict.youdao.com/wordbook/wordlist',
                params={'p': pageNo, 'tags': groupId},
            )
            soup = BeautifulSoup(rsp.text, features='html.parser')
            table = soup.find(id='wordlist').table.tbody
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                wordList.append(cols[1].div.a.text.strip())
        except Exception as e:
            logger.exception(f'网络异常{e}')
        finally:
            logger.info(wordList)
            return wordList
