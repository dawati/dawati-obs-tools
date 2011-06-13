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
                debug("Parsing %s" % dbfile)
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

class PackageSource:
    # These variables are shared between all the instances of PackageSource
    # OBS name -> upstream name
    package_map = {
        'librsvg2'    : 'librsvg',      'gtk3'           : 'gtk+',
        'libunique3'  : 'libunique',    'gnome-python2'  : 'gnome-python',
        'GConf2'      : 'GConf',        'libgtop2'       : 'libgtop',
        'glib2'       : 'glib',         'gtksourceview2' : 'gtksourceview',
        'gtkhtml3'    : 'gtkhtml',      'gnome-vfs2'     : 'gnome-vfs',
        'gtk2-engines': 'gtk-engines',  'gtk2'           : 'gtk+',

        'libgnomeprint22': 'libgnomeprint',
        'libgnomeprintui22': 'libgnomeprintui',
        'abattis-cantarell-fonts': 'cantarell-fonts',
    }
    # Some packages don't follow the odd/even for unstable/stable rule or
    # we need the latest unstable version
    no_odd_even_rule = (
        'libnotify', 'notification-daemon', 'dconf', 'gjs', 'libxklavier',
        'gnome-video-effects', 'gtk-doc',

        # unstable version "for now"
        'folks',
    )

    def __init__ (self, base_url):
        # upstream name -> info
        self.packages = {}
        self.base_url = base_url

    def get_package(self, name):
        obs_name = name
        upstream_name = name

        if PackageSource.package_map.has_key(name):
            upstream_name = PackageSource.package_map[name]

        if not self.packages.has_key(name):
            self.packages[name] = self.get_package_real(obs_name, upstream_name)
        return self.packages[name]

    def get_package_real(self, name):
        warn("subclasses must implement get_package_real()")
        return None


class GNOME(PackageSource):
    def __init__(self):
        PackageSource.__init__(self, "http://download.gnome.org/sources")
        # Some OBS packages have GNOME 2 versions of the software. These are
        # parallel installable with the GNOME 3 versions and need to be
        # tracked too
        self.gnome2 = (
            'gtk2', 'gtksourceview2', 'gtk2-engines',
        )

    def get_package_real(self, obs_name, upstream_name):
        global options
        package = {}

        base = "%s/%s" % (self.base_url, upstream_name)
        url = "%s/cache.json" % base
        debug("Opening URL: %s for %s" % (url, upstream_name))
        try:
            fp = urllib2.urlopen(url)
            j = json.load(fp)

            package['stable'] = None
            package['unstable'] = None

            if upstream_name in PackageSource.no_odd_even_rule:
                package['stable'] = j[2][upstream_name][-1]
                package['unstable'] = package['stable']
            else:
                stable = []
                unstable = []

                for version in j[2][upstream_name]:
                    v = version.split(".")
                    major = int(v[0])
                    minor = int(v[1])

                    if obs_name in self.gnome2 and (major != 2 or minor >= 90):
                        continue

                    if minor % 2 == 0:
                        stable.append(version)
                    else:
                        unstable.append(version)

                if len(stable) > 0:
                    package['stable'] = stable[-1]
                if len(unstable) > 0:
                    package['unstable'] = stable[-1]

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
        'dbus-glib',

        # source forge
        'inkscape',

        # own web site
        'avahi', 'libcanberra', 'sqlite', 'xulrunner', 'syncevolution',
        'webkitgtk', 'gimp', 'media-explorer',
    )

    print("% 28s % 12s% 12s" % ('Package', 'devel:gnome', 'upstream'))

    packages = repo.packages.items()
    packages.sort()
    for package in packages:
        obs_package = package[0]
        obs_version = package[1]

        if obs_package in ignore:
            note("Ignored %s" % obs_package)
            continue

        upstream = gnome.get_package(obs_package)
        if obs_version != upstream['stable']:
            print "% 28s % 12s% 12s" % (obs_package, obs_version,
                                        upstream['stable'])
        time.sleep(0.2) # rate limit at 5 requests/s
