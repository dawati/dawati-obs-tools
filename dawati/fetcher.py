# coding=utf-8

import string

import urllib2
from message import Message

from dawati import config

class Fetcher(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Fetcher, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        try:
            user = config.get('user')
            password = config.get('password')

            # extract the top level URL (skip http[s]:// and search for '/'))
            trunk = config.get('obs_repo_trunk')
            end = string.find(trunk, '/', 8)
            top_level_url = trunk[:end]

            manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, top_level_url, user, password)
            handler = urllib2.HTTPBasicAuthHandler(manager)
            opener = urllib2.build_opener(handler)
            urllib2.install_opener(opener)

        except KeyError:
            pass

    def get(self, url):
        m = Message()

        m.debug("Fetching: %s" % url)
        return urllib2.urlopen(url)
