#!/usr/bin/env python
# coding=utf-8

import os
import sys
import json
import urllib2
import time
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


obs_gnome_devel = "http://download.meego.com/live/devel:/gnome/standard/"

def warn(message):
    print "WARNING: %s" % message

def note(message):
    global options
    if options.verbose:
        print message

def debug(message):
    global options
    if options.verbose > 1:
        print message

def is_debug_enabled():
    global options
    return options.verbose > 1

class OBSRepository:
    def __init__(self, url):
        self.url = url
        self.packages = {}
        self.parse_repo_data()

    def get_repomd_path(self):
        return "%s/repodata/repomd.xml" % self.url

    def parse_repo_data(self):
        md = self.get_repomd_path()
        f = urllib2.urlopen(md)
        tree = etree.ElementTree()
        tree.parse(f)
        ns = "http://linux.duke.edu/metadata/repo"
        configs = tree.findall('{%s}data' %ns)
        for c in configs:
            if c.attrib.get("type") == "primary":
                loc = c.find('{%s}location' %ns)
                dbfile = loc.attrib.get("href")
                note("Parsing %s" % dbfile)
                fpgz = urllib2.urlopen("%s/%s" % (self.url, dbfile))
                local = open("primary.xml.gz", "w")
                local.write(fpgz.read())
                local.close()
                root = etree.parse("primary.xml.gz")
                ns2 = "http://linux.duke.edu/metadata/common"
                for s in root.findall('{%s}package' % ns2):
                    arch = s.find('{%s}arch' % ns2).text
                    if arch == 'src':
                        name = s.find('{%s}name' % ns2)
                        version = s.find('{%s}version' % ns2)
                        ver = version.attrib.get("ver")
                        self.packages[name.text] = ver

class GNOME:
    def __init__(self):
        self.base_url = "http://ftp.gnome.org/pub/GNOME/sources"
        # upstream name -> info
        self.packages = {}
        # OBS name -> upstream name
        self.package_map = {
            'librsvg2'    : 'librsvg',      'gtk3'           : 'gtk+',
            'libunique3'  : 'libunique',    'gnome-python2'  : 'gnome-python',
            'GConf2'      : 'Gconf',        'libgtop2'       : 'libgtop',
            'glib2'       : 'glib',         'gtksourceview2' : 'gtksourceview',
            'gtkhtml3'    : 'gtkhtml',      'gnome-vfs2'     : 'gnome-vfs',
            'gtk2-engines': 'gtk-engines',

            'libgnomeprint22': 'libgnomeprint',
            'libgnomeprintui22': 'libgnomeprintui',
            'abattis-cantarell-fonts': 'cantarell-fonts',
        }

    def get_package(self, name):
        if self.package_map.has_key(name):
            name = self.package_map[name]

        if not self.packages.has_key(name):
            self.packages[name] = self.get_package_real(name)
        return self.packages[name]

    def get_package_real(self, upstream_name):
        global options
        package = {}

        base = "%s/%s" % (self.base_url, upstream_name)
        url = "%s/cache.json" % base
        debug("Opening URL: %s for %s" % (url, upstream_name))
        try:
            fp = urllib2.urlopen(url)
            j = json.load(fp)
            stable = [x for x in j[2][upstream_name] if \
                      int(x.split(".")[1]) % 2 == 0 ]
            unstable = [x for x in j[2][upstream_name] if \
                        int(x.split(".")[1]) % 2 == 1 ]
            package['stable'] = stable[-1] if len(stable) > 0 else None
            package['unstable'] = unstable[-1] if len(unstable) > 0 else None

            # In debug mode print out the parsed json object if we haven't
            # been able to parse the stable or unstable version
            if is_debug_enabled():
                if not package['stable'] or not package['unstable']:
                    print(j[2])

        except urllib2.HTTPError:
            package = {'stable': 'Not found', 'unstable': 'Not found'}

        return package

if __name__ == '__main__':
    global options
    parser = optparse.OptionParser()

    parser.add_option("-p", "--package", type="string", dest="package",
                      help="package name")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_option("-d", "--debug", action="store_const", const=2,
                      dest="verbose")

    (options, args) = parser.parse_args()

    gnome = GNOME()
    repo = OBSRepository(obs_gnome_devel)

    # list of OBS packages to ignore (because they are in devel:gnome but not
    # being hosted on gnome.org
    ignore = (
        # freedesktop
        'cairo', 'telepathy-logger', 'polkit', 'polkit-gnome', 'upower',

        # own web site
        'avahi', 'libcanberra', 'sqlite', 'xulrunner', 'syncevolution',
        'webkitgtk',
    )

    print("% 28s % 12s% 12s" % ('Package', 'devel:gnome', 'upstream'))
    for obs_package, obs_version in repo.packages.iteritems():
        if obs_package in ignore:
            note("Ignored %s" % obs_package)
            continue

        upstream = gnome.get_package(obs_package)
        if obs_version != upstream['stable']:
            print "% 28s % 12s% 12s" % (obs_package, obs_version,
                                        upstream['stable'])
        time.sleep(0.2) # rate limit at 5 requests/s
