# -*- coding: utf-8 -*-
import json
import urllib
import urllib2
import json
import traceback
from PyQt4 import QtCore

class LookupThread(QtCore.QThread):
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
                self.emit(QtCore.SIGNAL('updateProgressBar'), current+1, tw)
                self.emit(QtCore.SIGNAL('seek'),'Looking up:' + self.wordList[current])
            self.emit(QtCore.SIGNAL('done'), self.lookUpedTerms)
            # return json.dumps(self.lookUpedTerms)
        else:
            self.emit(QtCore.SIGNAL('seek'),'No word has been lookuped')


# print(json.dumps(lookup('acute'),indent=4))
# print(LookupThread(['a','b']).run())
