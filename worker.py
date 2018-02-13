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
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__loadCookies()))
        urllib2.install_opener(opener)
        response = urllib2.urlopen(req).read()
        wordList = [term['uuid']for term in json.loads(response)['data']]

        self.emit(QtCore.SIGNAL('updateProgressBar'), 1, 1)
        self.emit(QtCore.SIGNAL('seek'),'Get Eudict wordList: Done')
        self.emit(QtCore.SIGNAL('done'),wordList)
        return wordList

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
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__loadCookies()))
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
            self.emit(QtCore.SIGNAL('updateProgressBar'), current+1, tp)
        self.emit(QtCore.SIGNAL('seek'),'Get  Youdao wordList: Done')
        self.emit(QtCore.SIGNAL('done'),parser.terms)

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
            self.emit(QtCore.SIGNAL('updateProgressBar'), current+1, ti)
            self.emit(QtCore.SIGNAL('seek'),'Getting image: ' + self.imageUrls[current][0])


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
            try:
                urllib.urlretrieve(self.soundAPI.format(self.terms[current],str(self.ptype)), "MG-" + self.terms[current] + '.mp3')
                self.emit(QtCore.SIGNAL('updateProgressBar'), current+1, tp)
                self.emit(QtCore.SIGNAL('seek'),'Getting pronunciation: ' + self.terms[current])
            except Exception,e:
                self.emit(QtCore.SIGNAL('seek'),str(e))



# test = Youdao()
# test.run()
# print test.results
