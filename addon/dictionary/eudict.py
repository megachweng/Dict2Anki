import logging
import time
from math import ceil

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from ..misc import AbstractDictionary

logger = logging.getLogger('Dict2Anki.euDict')


class EuDict(AbstractDictionary):
    name = '欧陆词典'
    timeout = 15
    wordBookUrl = 'https://my.eudic.net/studylist'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    wordBookIndexSoup = None
    remoteWords = []

    @classmethod
    def checkLoginState(cls, cookie=None, content=None, first_login=False) -> bool:
        if first_login:
            logger.info('首次登录')
            isLogin = 'EudicWeb' in cookie
            cls.setData(cookie, content)
        else:
            logger.info('非首次登录')
            isLogin = cls._checkCookie(cookie)
        logger.debug(f'Cookie: {cookie}')
        logger.debug(f'Content: {content}')
        logging.info('已登录' if isLogin else '未登录')
        return isLogin

    @classmethod
    def _checkCookie(cls, cookie):
        cls.session.cookies = requests.utils.cookiejar_from_dict(cookie, cookiejar=None, overwrite=True)
        rsp = cls.session.get(cls.wordBookUrl)
        if rsp.url.startswith(cls.wordBookUrl):
            cls.setData(cookie, rsp.text)
            return True
        return False

    @classmethod
    def setData(cls, cookie, content):
        cls.session.cookies = requests.utils.cookiejar_from_dict(cookie, cookiejar=None, overwrite=True)
        cls.wordBookIndexSoup = BeautifulSoup(content, features='html.parser')

    @classmethod
    def getWordGroup(cls) -> [(str, int)]:
        """
        获取单词本分组
        :return: [(group_name,group_id)]
        """
        groups = []
        try:
            elements = cls.wordBookIndexSoup.find_all('a', class_='media_heading_a new_cateitem_click')
        except AttributeError:
            logger.warning('解析失败')
        else:
            if elements:
                groups = [(el.string, el['data-id']) for el in elements]
        finally:
            return groups

    @classmethod
    def getTotalPage(cls, groupName: str, groupId: str) -> int:
        """
        获取分组下总页数
        :param groupName: 分组名称
        :param groupId:分组id
        :return:
        """
        totalPages = 0
        try:
            r = cls.session.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=cls.timeout,
                data={'categoryid': groupId}
            )
            records = r.json()['recordsTotal']
            totalPages = ceil(records / 100)

        except Exception as error:
            logger.exception(f'网络异常{error}')
        finally:
            logger.info(f'该分组({groupName}-{groupId})下共有{totalPages}页')
            return totalPages

    @classmethod
    def getWordsPerPage(cls, pageNo: int, groupName: str, groupId: str) -> [str]:
        """
        获取分组下每一页的单词
        :param pageNo: 页数
        :param groupName: 分组名
        :param groupId: 分组id
        :return:
        """
        wordList = []
        data = {
            'columns[2][data]': 'word',
            'start': pageNo * 100,
            'length': 100,
            'categoryid': groupId,
            '_': int(time.time()) * 1000,
        }
        try:
            logger.info(f'获取单词本(f{groupName}-{groupId})第:{pageNo + 1}页')
            r = cls.session.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=cls.timeout,
                data=data
            )
            wl = r.json()
            wordList = list(set(word['uuid'] for word in wl['data']))
        except Exception as error:
            logger.exception(f'网络异常{error}')
        finally:
            logger.info(f'{groupName}分组下，第{pageNo + 1}页单词:{wordList}')
            cls.remoteWords += wordList
            return wordList
