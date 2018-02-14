# -*- coding: utf-8 -*-
import os
import re
import time
import json
import hashlib
import cookielib
import urllib
import urllib2
import sqlite3
import pickle
from HTMLParser import HTMLParser
import traceback
from PyQt4 import QtCore
class Eudict(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
    def login(self, username, password, rememberme):
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:58.0) Gecko/20100101 Firefox/58.0')]
        urllib2.install_opener(opener)

        authentication_url = 'http://dict.eudic.net/Account/Login?returnUrl=https://my.eudic.net/studylist'
        payload = {
            'UserName': username,
            'Password': password,
            'RememberMe': str(rememberme).lower(),
            'returnUrl': 'https://my.eudic.net/studylist'
        }
        req = urllib2.Request(authentication_url, urllib.urlencode(payload))
        urllib2.urlopen(req)
        if 'EudicWeb' in str(cj):
            self.__saveCookies(cj)
            return True
        else:
            return False

    def __saveCookies(self, cookiejar):
        MozillaCookieJar = cookielib.MozillaCookieJar()
        for c in cookiejar:
            args = dict(vars(c).items())
            args['rest'] = args['_rest']
            del args['_rest']
            c = cookielib.Cookie(**args)
            MozillaCookieJar.set_cookie(c)
        MozillaCookieJar.save('Eudict.cookie', ignore_discard=True)

    def __loadCookies(self):
        if os.path.exists('Eudict.cookie'):
            MozillaCookieJar = cookielib.MozillaCookieJar()
            MozillaCookieJar.load('Eudict.cookie', ignore_discard=True)
            return MozillaCookieJar
        else:
            return False

    def run(self):
        req = urllib2.Request("https://my.eudic.net/StudyList/WordsDataSource?length=100000000&categoryid=-1")
        cookie = self.__loadCookies()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        urllib2.install_opener(opener)
        response = urllib2.urlopen(req).read()
        wordList = [term['uuid']for term in json.loads(response)['data']]
        self.emit(QtCore.SIGNAL('updateProgressBar_dict(int,int)'),int(1), int(1))
        self.results = wordList

class Youdao(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
    def login(self, username, password, rememberme):
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:58.0) Gecko/20100101 Firefox/58.0')]
        urllib2.install_opener(opener)

        authentication_url = 'https://logindict.youdao.com/login/acc/login'
        payload = {
            'app':'web',
            'tp':'urstoken',
            'cf':'7',
            'fr':'1',
            'ru':'http://dict.youdao.com/wordbook/wordlist?keyfrom=login_from_dict2.index',
            'product':'DICT',
            'type':'1',
            'um':'true',
            'username':username,
            'password':hashlib.md5(password.encode('utf-8')).hexdigest(),
            'savelogin':rememberme and 1 or 0,
        }
        req = urllib2.Request(authentication_url, urllib.urlencode(payload))
        urllib2.urlopen(req)
        if username in str(cj):
            self.__saveCookies(cj)
            return True
        else:
            return False

    def __saveCookies(self, cookiejar):
        MozillaCookieJar = cookielib.MozillaCookieJar()
        for c in cookiejar:
            args = dict(vars(c).items())
            args['rest'] = args['_rest']
            del args['_rest']
            c = cookielib.Cookie(**args)
            MozillaCookieJar.set_cookie(c)
        MozillaCookieJar.save('Youdao.cookie', ignore_discard=True)

    def __loadCookies(self):
        if os.path.exists('Youdao.cookie'):
            MozillaCookieJar = cookielib.MozillaCookieJar()
            MozillaCookieJar.load('Youdao.cookie', ignore_discard=True)
            return MozillaCookieJar
        else:
            return False

    def run(self):
        def totalPage():
            # page index start from 0 end at max-1
            req = urllib2.Request('http://dict.youdao.com/wordbook/wordlist?p=0&tags=')
            cookie = self.__loadCookies()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
            urllib2.install_opener(opener)
            response = urllib2.urlopen(req)
            source = response.read()
            try:
                return int(re.search('<a href="wordlist.p=(.*).tags=" class="next-page">最后一页</a>', source, re.M | re.I).group(1)) - 1
            except Exception:
                return 1

        def everyPage(pageIndex):
            req = urllib2.Request("http://dict.youdao.com/wordbook/wordlist?p=" + str(pageIndex) + "&tags=")
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__loadCookies()))
            urllib2.install_opener(opener)
            response = urllib2.urlopen(req)
            return response.read().decode('utf-8')

        parser = parseYoudaoWordbook()
        tp = totalPage()
        for current in range(tp):
            parser.feed(everyPage(current))
            self.emit(QtCore.SIGNAL('updateProgressBar_dict(int,int)'),int(current+1), int(tp))

        self.results = parser.terms


# Youdao Only
class parseYoudaoWordbook(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.terms = []

    def handle_starttag(self, tag, attrs):
        # retrive the terms
        if tag == 'div':
            for attribute, value in attrs:
                if attribute == 'class' and value == 'word':
                    self.terms.append(attrs[1][1])


class imageDownloader(QtCore.QThread):
    """thread that download images of terms"""
    def __init__(self,imageUrls):
        QtCore.QThread.__init__(self)
        self.imageUrls = imageUrls

    def run(self):
        ti = len(self.imageUrls)
        for current in range(ti):
            urllib.urlretrieve(self.imageUrls[current][1], "MG-" + self.imageUrls[current][0] + '.jpg')
            self.emit(QtCore.SIGNAL('update'),current+1,ti)
            self.emit(QtCore.SIGNAL('updateProgressBar_img(int,int)'),int(current+1),int(ti))
            self.emit(QtCore.SIGNAL('seek_img(QString)'),str('Getting image: ' + self.imageUrls[current][0]))

class pronunciationDownloader(QtCore.QThread):
    def __init__(self,terms,ptype):
        QtCore.QThread.__init__(self)
        self.terms = terms
        self.ptype = ptype
        # 1 UK 2 US
        self.soundAPI = "http://dict.youdao.com/dictvoice?audio={}&type={}"

    def run(self):
        tp = len(self.terms)
        for current in range(tp):
            urllib.urlretrieve(self.soundAPI.format(self.terms[current],str(self.ptype)), "MG-" + self.terms[current] + '.mp3')
            self.emit(QtCore.SIGNAL('updateProgressBar_pron(int,int)'),int(current+1),int(tp))
            self.emit(QtCore.SIGNAL('seek_pron(QString)'),str('Getting pronunciation: ' + self.terms[current]))

class Lookupper(QtCore.QThread):
    def __init__(self, wordList):
        QtCore.QThread.__init__(self)
        self.wordList = wordList
        self.lookUpedTerms = []
    def run(self):
        if self.wordList:
            tw = len(self.wordList)
            for current in range(tw):
                query = urllib.urlencode({"q": self.wordList[current]})
                f = urllib2.urlopen("https://dict.youdao.com/jsonapi?{}&dicts=%7b%22count%22%3a+99%2c%22dicts%22%3a+%5b%5b%22ec%22%2c%22phrs%22%2c%22pic_dict%22%5d%2c%5b%22web_trans%22%5d%2c%5b%22fanyi%22%5d%2c%5b%22blng_sents_part%22%5d%5d%7d".format(query))
                r = f.read().decode('utf-8')
                try:
                    json_result = json.loads(r)
                except:
                    pass

                try:
                    explains = json_result["ec"]["word"][0]["trs"][0]["tr"][0]["l"]["i"][0]
                except:
                    try:
                        explains = json_result["web_trans"]["web-translation"][0]["trans"][0]["value"]
                    except:
                        try:
                            explains = json_result["fanyi"]["tran"]
                        except:
                            explains = None

                try:
                    uk_phonetic = json_result["ec"]["word"][0]["ukphone"]
                except:
                    try:
                        uk_phonetic = json_result["simple"]["word"][0]["ukphone"]
                    except:
                        try:
                            uk_phonetic = json_result["ec"]["word"][0]["phone"]
                        except:
                            uk_phonetic = None

                try:
                    us_phonetic = json_result["ec"]["word"][0]["usphone"]
                except:
                    try:
                        us_phonetic = json_result["simple"]["word"][0]["usphone"]
                    except:
                        try:
                            us_phonetic = json_result["ec"]["word"][0]["phone"]
                        except:
                            us_phonetic = None

                try:
                    phrases = []
                    phrase_explains = []
                    json_phrases = json_result["phrs"]["phrs"]
                    for value in json_phrases:
                        phrases.append(value["phr"]["headword"]["l"]["i"])
                        phrase_explains.append(value["phr"]["trs"][0]["tr"]["l"]["i"])
                except:
                    phrases = None
                    phrase_explains = None

                try:
                    sentences = []
                    sentences_explains = []
                    json_sentences = json_result["blng_sents_part"]["sentence-pair"]
                    for value in json_sentences:
                        sentences.append(value["sentence-eng"])
                        sentences_explains.append(value["sentence-translation"])
                except:
                    sentences = None
                    sentences_explains = None

                try:
                    img = json_result["pic_dict"]["pic"][0]["image"] + "&w=150"
                except:
                    img = None

                lookUpedTerm = {
                    "term": self.wordList[current],
                    "uk": uk_phonetic,
                    "us": us_phonetic,
                    "definition": explains,
                    "phrases": phrases and phrases[:3] or None,
                    "phrases_explains": phrase_explains and phrase_explains[:3] or None,
                    "sentences": sentences and sentences[:3] or None,
                    "sentences_explains": sentences_explains and sentences_explains[:3] or None,
                    "image": img
                }
                self.lookUpedTerms.append(lookUpedTerm)
                self.emit(QtCore.SIGNAL('updateProgressBar_lookup(int,int)'),int(current+1),int(tw))
                self.emit(QtCore.SIGNAL('seek_lookup(QString)'),str('Looking up: ' + self.wordList[current]))
        else:
            self.emit(QtCore.SIGNAL('seek_lookup(QString)'),str('No word has been lookupped'))

# test = Youdao()
# test.run()
# print test.results
