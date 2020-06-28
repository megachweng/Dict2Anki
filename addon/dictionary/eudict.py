import time
import logging
import requests
from math import ceil
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from ..misc import AbstractDictionary

logger = logging.getLogger('dict2Anki.dictionary.eudict')


class Eudict(AbstractDictionary):
    name = '欧陆词典'
    loginUrl = 'https://dict.eudic.net/account/login'
    timeout = 10
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    def __init__(self):
        self.groups = []
        self.indexSoup = None

    def checkCookie(self, cookie: dict) -> bool:
        """
        cookie有效性检验
        :param cookie:
        :return: Boolean cookie是否有效
        """
        rsp = requests.get('https://my.eudic.net/studylist', cookies=cookie, headers=self.headers)
        if 'dict.eudic.net/account/login' not in rsp.url:
            self.indexSoup = BeautifulSoup(rsp.text, features="html.parser")
            logger.info('Cookie有效')
            cookiesJar = requests.utils.cookiejar_from_dict(cookie, cookiejar=None, overwrite=True)
            self.session.cookies = cookiesJar
            return True
        logger.info('Cookie失效')
        return False

    @staticmethod
    def loginCheckCallbackFn(cookie, content):
        if 'EudicWebSession' in cookie:
            return True
        return False

    def getGroups(self) -> [(str, int)]:
        """
        获取单词本分组
        :return: [(group_name,group_id)]
        """
        elements = self.indexSoup.find_all('a', class_='media_heading_a new_cateitem_click')
        groups = []
        if elements:
            groups = [(el.string, el['data-id']) for el in elements]

        logger.info(f'单词本分组:{groups}')
        self.groups = groups

    def getTotalPage(self, groupName: str, groupId: int) -> int:
        """
        获取分组下总页数
        :param groupName: 分组名称
        :param groupId:分组id
        :return:
        """
        try:
            r = self.session.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=self.timeout,
                data={'categoryid': groupId}
            )
            records = r.json()['recordsTotal']
            totalPages = ceil(records / 100)
            logger.info(f'该分组({groupName}-{groupId})下共有{totalPages}页')
            return totalPages
        except Exception as error:
            logger.exception(f'网络异常{error}')
            return 0

    def getWordsByPage(self, pageNo: int, groupName: str, groupId: int) -> [str]:
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
            r = self.session.get(
                url='https://my.eudic.net/StudyList/WordsDataSource',
                timeout=self.timeout,
                data=data
            )
            wl = r.json()
            wordList = list(set(word['uuid'] for word in wl['data']))
        except Exception as error:
            logger.exception(f'网络异常{error}')
        finally:
            logger.info(wordList)
            return wordList
