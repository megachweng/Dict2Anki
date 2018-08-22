# -*- coding: utf-8 -*-
import urllib2

def urlRequest(req, retry):
    count = 0
    while True:
        try:
            count += 1
            response = urllib2.urlopen(req, timeout=10)
        except Exception, e:
            if count >= retry:
                raise e
        else:
            return response

def urlRetrieve(url, path, retry):
    count = 0
    while True:
        try:
            count += 1
            f = urllib2.urlopen(url, timeout=10)
            with open(path, "wb") as file:
                file.write(f.read())
        except Exception, e:
            if count >= retry:
                raise e
        else:
            break