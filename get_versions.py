#!/usr/bin/python

import os
import sys
import urllib2
import optparse
try:
  from lxml import etree
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
        except ImportError:
          print("Failed to import ElementTree from any known place")

project_repo = "http://download.meego.com/live/devel:/gnome/standard/"

def get_repomd_path():
    return "%s/repodata/repomd.xml" %project_repo

def _parse_repo_data():
    md = get_repomd_path()
    f = urllib2.urlopen(md)
    tree = etree.ElementTree()
    tree.parse(f)
    ns = "http://linux.duke.edu/metadata/repo"
    configs = tree.findall('{%s}data' %ns)
    for c in configs:
        if c.attrib.get("type") == "primary":
            loc = c.find('{%s}location' %ns)
            dbfile = loc.attrib.get("href")
            print "Parsing %s" %dbfile
            fpgz = urllib2.urlopen("%s/%s" %(project_repo, dbfile))
            local = open("primary.xml.gz", "w")
            local.write(fpgz.read())
            local.close()
            root = etree.parse("primary.xml.gz")
            ns2 = "http://linux.duke.edu/metadata/common"
            for s in root.findall('{%s}package' %ns2):
                arch = s.find('{%s}arch' %ns2).text
                if arch == 'src':
                    name = s.find('{%s}name' %ns2)
                    version = s.find('{%s}version' %ns2)
                    ver = version.attrib.get("ver")
                    print "%s:%s" %(name.text, ver)



    f.close()


_parse_repo_data()
