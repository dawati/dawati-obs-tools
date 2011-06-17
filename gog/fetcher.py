# coding=utf-8

import urllib2
from message import Message

class Fetcher(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Fetcher, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def get(self, url):
        m = Message()

        m.debug("Fetching: %s" % url)
        return urllib2.urlopen(url)
