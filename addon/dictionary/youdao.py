import logging
import re

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

logger = logging.getLogger('Dict2Anki.youdaoDict')


class YoudaoDict:
    name = '有道词典'
    timeout = 15
    wordBookUrl = 'http://dict.youdao.com/wordbook/wordlist'
    headers = {
        'Host': 'dict.youdao.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    }
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    wordBookIndexSoup = None
    remoteWords = []

    @classmethod
    def checkLoginState(cls, cookie=None, content=None, first_login=False):
        if first_login:
            logger.info('首次登录')
            isLogin = 'DICT_SESS' in cookie
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
    def setData(cls, cookie: dict, content: str):
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
            elements = cls.wordBookIndexSoup.find('select', id='select_category')
        except AttributeError:
            pass
        else:
            if elements:
                groups = elements.find_all('option')
                groups = [(e.text, e['value']) for e in groups]
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
        totalPages = 1
        try:
            r = cls.session.get(
                url='http://dict.youdao.com/wordbook/wordlist',
                timeout=cls.timeout,
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
            logger.exception(f'网络异常:{error}')

        finally:
            totalPages = totalPages - 1 if totalPages > 1 else totalPages
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
        try:
            logger.info(f'获取单词本(f{groupName}-{groupId})第:{pageNo + 1}页')
            rsp = cls.session.get(
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
            logger.exception(f'网络异常:{e}')
        finally:
            logger.info(f'{groupName}分组下，第{pageNo + 1}页单词:{wordList}')
            cls.remoteWords += wordList
            return wordList
