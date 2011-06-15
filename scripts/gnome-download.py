#!/usr/bin/python

import os
import sys
import json
import urllib2
import optparse


gnome_source = "http://ftp.gnome.org/pub/GNOME/sources"

def check(package, show_news):
    base = "%s/%s" %(gnome_source,package)
    url = "%s/cache.json" %base
    fp = urllib2.urlopen(url)
    j = json.load(fp)
    latest_stable = [x for x in j[2][package] if int(x.split(".")[1]) % 2 == 0 ]
    latest_unstable = [x for x in j[2][package] if int(x.split(".")[1]) % 2 == 1 ]
    print "Stable: %s" %latest_stable[-1]
    print "Unstable: %s" %latest_unstable[-1]
    if show_news:
        latest_data = j[1][package][latest_unstable[-1]]
        news = "%s/%s/%s" %(gnome_source, package, latest_data['news'])
        fpnews = urllib2.urlopen(news)
        print fpnews.read()

def download(package, unstable):
    base = "%s/%s" %(gnome_source,package)
    url = "%s/cache.json" %base
    fp = urllib2.urlopen(url)
    j = json.load(fp)
    latest_stable = [x for x in j[2][package] if int(x.split(".")[1]) % 2 == 0 ]
    latest_unstable = [x for x in j[2][package] if int(x.split(".")[1]) % 2 == 1 ]
    if unstable:
        latest = latest_unsstable[-1]
    else:
        latest = latest_stable[-1]
    latest_data = j[1][package][latest]
    tar = "%s/%s" %(base,latest_data['tar.bz2'])
    local_file = "%s" %os.path.basename(latest_data['tar.bz2'])
    if os.path.exists(local_file):
        print "file %s already exists" %local_file
    else:
        print "Downloading %s" %tar
        fptar = urllib2.urlopen(tar)
        local = open("%s" %local_file, "w")
        local.write(fptar.read())

if __name__ == '__main__':
    parser = optparse.OptionParser()

    parser.add_option("-p", "--package", type="string", dest="package",
                    help="package name")
    parser.add_option("-d", "--download", dest="download", action="store_true", 
                    help="download package", default=False)
    parser.add_option("-c", "--check", dest="check", action="store_true", 
                    help="check last version", default=False)
    parser.add_option("-u", "--unstable", dest="unstable", action="store_true", 
                    help="download unstable version", default=False)
    parser.add_option("-n", "--news", dest="news", action="store_true", 
                    help="check news", default=False)


    (options, args) = parser.parse_args()
    if options.package  and options.download:
        download(options.package, options.unstable)
    elif options.package  and options.check:
        check(options.package, options.news)



