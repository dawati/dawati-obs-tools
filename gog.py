#!/usr/bin/env python
# coding=utf-8

import os
import sys
import json
import urllib2
import re
import time
import optparse
import string
from distutils import version
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


#obs_gnome_devel = "http://download.meego.com/live/devel:/gnome/standard/"
obs_gnome_devel = "http://download.meego.com/snapshots/latest/repos/oss/source//"

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

__rc_ups_regex = re.compile("(.*?)(-?(rc|pre|beta|alpha)([0-9]*))", re.I)

def split_rc(version):
    """ Split version into version and release candidate string +
        release candidate number if possible
    """
    match = __rc_ups_regex.match(version)
    if not match:
        return (version, "", "")

    rc_str = match.group(3)
    if rc_str:
        v = match.group(1)
        rc_num = match.group(4)
        return (v, rc_str, rc_num)
    else:
        # if version contains a dash, but no release candidate string is found,
        # v != version, therefore use version here
        # Example version: 1.8.23-20100128-r1100
        # Then: v=1.8.23, but rc_str=""
        return (version, "", "")

def rpm_cmp(v1, v2):
    import rpm
    diff = rpm.labelCompare((None, v1, None), (None, v2, None))
    return diff

def upstream_cmp(v1, v2):
    """ Compare two upstream versions

    :Parameters:
        v1 : str
            Upstream version string 1
        v2 : str
            Upstream version string 2

    :return:
        - -1 - second version newer
        - 0  - both are the same
        - 1  - first version newer

    :rtype: int

    """

    v1, rc1, rcn1 = split_rc(v1)
    v2, rc2, rcn2 = split_rc(v2)

    diff = rpm_cmp(v1, v2)
    if diff != 0:
        # base versions are different, ignore rc-status
        return diff

    if rc1 and rc2:
        # both are rc, higher rc is newer
        diff = cmp(rc1.lower(), rc2.lower())
        if diff != 0:
            # rc > pre > beta > alpha
            return diff
        if rcn1 and rcn2:
            # both have rc number
            return cmp(int(rcn1), int(rcn2))
        if rcn1:
            # only first has rc number, then it is newer
            return 1
        if rcn2:
            # only second has rc number, then it is newer
            return -1
        # both rc numbers are missing or same
        return 0

    if rc1:
        # only first is rc, then second is newer
        return -1
    if rc2:
        # only second is rc, then first is newer
        return 1

    # neither is a rc
    return 0

def upstream_max(list):
    list.sort(cmp=upstream_cmp)
    return list[-1]

class Package:
    def __init__(self, name, versions):
        self.name = name
        self.versions = versions
        self.versions.sort(cmp=upstream_cmp)

    def get_latest_version(self, stability='stable'):
        return self.versions[-1]

class OBSRepository:
    def __init__(self, url):
        self.url = url
        self.packages = {}
        self.parse_repo_data()

    def has_package(self, name):
        return self.packages.has_key(name)

    def get_version(self, name):
        if self.has_package(name):
            return self.packages[name]
        else:
            return None

    def get_repomd_path(self):
        return "%s/repodata/repomd.xml" % self.url

    def parse_repo_data(self):
        md = self.get_repomd_path()
        debug("Fetching %s" % md)
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

    def __init__ (self):
        # upstream name -> info
        self.packages = {}

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

class Index(PackageSource):
    __html_regex = re.compile(r'\bhref\s*=\s*["\']([^"\'/]+)/["\']', re.I)
    __text_regex = re.compile(r'^d.+\s(\S+)\s*$', re.I|re.M)

    def __init__(self, db):
        PackageSource.__init__(self)
        self.urldb = db


    def expand_subdirs(self, url, glob_char="*"):
        """ Expand glob_char in the given URL with the latest dir at that level
            Example URL: http://www.example.com/foo/*/

            The globbing char needs to be enclosed by slashes like "/*/".
        """
        glob_pattern = "/%s/" % glob_char
        glob_pos = url.find(glob_pattern)

        # url until first slash before glob_char
        url_prefix = url[0:glob_pos+1]

        # everything after the slash after glob_char
        url_suffix = url[glob_pos+len(glob_pattern):]

        if url_prefix != "":
            dir_listing = urllib2.urlopen(url_prefix).read()
            if not dir_listing:
                return url
            subdirs = []
            regex = url.startswith("ftp://") and \
                    Index.__text_regex or Index.__html_regex
            for match in regex.finditer(dir_listing):
                subdir = match.group(1)
                if subdir not in (".", ".."):
                    subdirs.append(subdir)
            if not subdirs:
                return url
            latest = upstream_max(subdirs)

            url = "%s%s/%s" % (url_prefix, latest, url_suffix)
            return self.expand_subdirs(url, glob_char)
        return url

    def get_package_real(self, obs_name, upstream_name):
        regex = self.urldb[obs_name][0]
        url = self.urldb[obs_name][1]

        try:
            url = self.expand_subdirs(url)
            debug("Fetching: %s" % url)
            page = urllib2.urlopen(url)
            upstream_versions = re.findall(regex, page.read())
            if not upstream_versions:
                warn("could not parse upstream versions for %s" % obs_name)
                return None
            return Package(obs_name, upstream_versions)

        except urllib2.HTTPError:
            return None

class GNOME(PackageSource):
    def __init__(self):
        PackageSource.__init__(self)
        self.base_url = "http://download.gnome.org/sources"
        # Some OBS packages have GNOME 2 versions of the software. These are
        # parallel installable with the GNOME 3 versions and need to be
        # tracked too
        self.gnome2 = (
            'gtk2', 'gtksourceview2', 'gtk2-engines',
        )

    def get_package_real(self, obs_name, upstream_name):
        global options

        base = "%s/%s" % (self.base_url, upstream_name)
        url = "%s/cache.json" % base
        debug("Fetching: %s for %s" % (url, upstream_name))
        try:
            fp = urllib2.urlopen(url)
            j = json.load(fp)

            stable = []
            unstable = []

            if upstream_name in PackageSource.no_odd_even_rule:
                versions = j[2][upstream_name]
            else:
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

                versions = stable

            if len(versions) == 0:
                warn("could not parse json data: %s" % j[2])
                return None

        except urllib2.HTTPError:
            return None

        return Package(obs_name, versions)

# We have 2 sources to get package info. The urldb with a database of packages
# ie. where to get information about new tarbals (which will be used mainly by
# the Index object) and # the GNOME source that requests information on a
# package dynamically using the GNOME-specific Source.
class Dispatcher:
    package_line_regex = re.compile('([^ ]*) (.*) ([^ ]*)')
    urldb = {}

    def __init__(self):
        if not Dispatcher.urldb:
            debug("Opening urldb")
            db = open('urldb', 'r')
            for line in db:
                line = string.strip(line)
                m = re.match(Dispatcher.package_line_regex, line)
                if not m:
                    warn("could not parse %s" % line)
                    continue
                obs_name = string.strip(m.group(1))
                regex = string.strip(m.group(2))
                url = string.strip(m.group(3))
                # obs_name => (regex, url, tags)
                entry = (self.resolve_regex(obs_name, regex),
                         self.resolve_url(obs_name, url),
                         [])
                # autotag packages with a gnome.org url as 'GNOME'
                if entry[1].find('gnome.org') != -1:
                    entry[2].append('GNOME')

                #debug("inserting %s => (%s,%s,%s)" % (obs_name, entry[0],
                #      entry[1], entry[2]))

                if Dispatcher.urldb.has_key(obs_name):
                    warn("Duplicate entry for %s, ignoring" % obs_name)
                elif entry[0].find('DEFAULT') != -1:
                    warn("Could not resolve regex for %s, ignoring" % obs_name)
                elif entry[1].find('DEFAULT') != -1:
                    warn("Could not resolve url for %s, ignoring" % obs_name)
                else:
                    Dispatcher.urldb[obs_name] = entry
            debug("urldb parsed")

        self.index = Index(Dispatcher.urldb)
        self.gnome = GNOME()

    def resolve_regex(self, obs_name, regex):
        name = obs_name
        # allow name override with e.g. DEFAULT:othername
        if regex:
            name_override = re.match(r"^((?:FM-)?DEFAULT)(?::(.+))$", regex)
            if name_override:
                regex = name_override.group(1)
                name = name_override.group(2)

        # use DEFAULT regex but alter the name
        if regex == "CPAN-DEFAULT":
            # strip "perl-" prefix only if name was not overridden
            if not name_override and name.startswith("perl-"):
                name = name[len("perl-"):]
                regex = "DEFAULT"
        elif regex == "PEAR-DEFAULT":
            # strip "php-pear-" prefix only if name was not overridden
            if not name_override and name.startswith("php-pear-"):
                name = name[len("php-pear-"):].replace("-","_")
                regex = "DEFAULT"
        elif regex == "PECL-DEFAULT":
            # strip "php-pecl-" prefix only if name was not overridden
            if not name_override and name.startswith("php-pecl-"):
                name = name[len("php-pecl-"):].replace("-","_")
                regex = "DEFAULT"

        # no elif here, because the previous regex aliases are only for name
        # altering
        if regex == "DEFAULT":
            regex = \
                r"\b%s[-_]" % re.escape(name)    + \
                r"(?i)"                          + \
                r"(?:(?:src|source)[-_])?"       + \
                r"([^-/_\s]*?"                   + \
                r"\d"                            + \
                r"[^-/_\s]*?)"                   + \
                r"(?:[-_.](?:src|source|orig))?" + \
                r"\.(?:tar|t[bglx]z|tbz2|zip)\b"
        elif regex == "FM-DEFAULT":
            regex = '<a href="/projects/[^/]*/releases/[0-9]*">([^<]*)</a>'
        elif regex == "HACKAGE-DEFAULT" or regex== "DIR-LISTING-DEFAULT":
            regex = 'href="([0-9][0-9.]*)/"'

        return regex

    def resolve_url(self, obs_name, url):
        name = obs_name
        # allow name override with e.g. SF-DEFAULT:othername
        if url:
            name_override = re.match(r"^((?:SF|FM|GNU|CPAN|HACKAGE|DEBIAN|GOOGLE|PEAR|PECL|PYPI|LP|GNOME)-DEFAULT)(?::(.+))$", url)
            if name_override:
                url = name_override.group(1)
                name = name_override.group(2)
        name = urllib2.quote(name, safe='')
        if url == "SF-DEFAULT":
            url = "http://sourceforge.net/api/file/index/project-name/%s/mtime/desc/limit/20/rss" % name
        elif url == "FM-DEFAULT":
            url = "http://freshmeat.net/projects/%s" % name
        elif url == "GNU-DEFAULT":
            url = "http://ftp.gnu.org/gnu/%s/" % name
        elif url == "CPAN-DEFAULT":
            # strip "perl-" prefix only if name was not overridden
            if not name_override and name.startswith("perl-"):
                name = name[len("perl-"):]
            url = "http://search.cpan.org/dist/%s/" % name
        elif url == "HACKAGE-DEFAULT":
            # strip "ghc-" prefix only if name was not overridden
            if not name_override and name.startswith("ghc-"):
                name = name[len("ghc-"):]
            url = "http://hackage.haskell.org/packages/archive/%s/" % name
        elif url == "DEBIAN-DEFAULT":
            url = "http://ftp.debian.org/debian/pool/main/%s/%s/" % (name[0], name)
        elif url == "GOOGLE-DEFAULT":
            url = "http://code.google.com/p/%s/downloads/list" % name
        elif url == "PYPI-DEFAULT":
            url = "http://pypi.python.org/packages/source/%s/%s" % (name[0], name)
        elif url == "PEAR-DEFAULT":
            # strip "php-pear-" prefix only if name was not overridden
            if not name_override and name.startswith("php-pear-"):
                name = name[len("php-pear-"):].replace("-","_")
            url = "http://pear.php.net/package/%s/download" % name
        elif url == "PECL-DEFAULT":
            # strip "php-pecl-" prefix only if name was not overridden
            if not name_override and name.startswith("php-pecl-"):
                name = name[len("php-pecl-"):].replace("-","_")
            url = "http://pecl.php.net/package/%s/download" % name
        elif url == "LP-DEFAULT":
            url = "https://launchpad.net/%s/+download" % name
        elif url == "GNOME-DEFAULT":
            url = "http://download.gnome.org/sources/%s/" % name

        return url

    def get_upstream_version(self, obs_name):
        if not Dispatcher.urldb.has_key (obs_name):
            return 'Not Found'

        entry = Dispatcher.urldb[obs_name]
        tags = entry[2]
        if 'GNOME' in tags:
            source = self.gnome
        else:
            source = self.index

        package = source.get_package(obs_name)
        if not package:
            return 'Not Found'

        return package.get_latest_version()

if __name__ == '__main__':
    global options
    parser = optparse.OptionParser()

    parser.add_option("-p", "--package", type="string", dest="package",
                      help="package name")
    parser.add_option("-s", "--start-from", type="string", dest="start_from",
                      help="package name to start from")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_option("-d", "--debug", action="store_const", const=2,
                      dest="verbose")

    (options, args) = parser.parse_args()

    # list of OBS packages to ignore (because they trigger an error of some
    # kind)
    ignore = (
        # GNOME
        # Uses non conventional versions that break the upstream script
        # generating the json cache file
        'dia',
    )

    dispatcher = Dispatcher()

    # Holds the (package, obs version, upstream version) to display in the
    # summary at the end
    display_packages = []

    # The object representing the OBS project we are working with
    repo = OBSRepository(obs_gnome_devel)

    if options.package:
        name = options.package

        if not repo.has_package(name):
            warn("could not find %s in %s" % (name, obs_gnome_devel))
            sys.exit(1)

        obs_version = repo.get_version(name)
        display_packages.append((name,
                                 repo.get_version(name),
                                 dispatcher.get_upstream_version(name)))

    else:
        started = not options.start_from

        packages = repo.packages.items()
        packages.sort()
        for package in packages:
            obs_package = package[0]
            obs_version = package[1]

            started = started or obs_package == options.start_from
            if not started:
                continue

            if obs_package in ignore:
                note("Ignored %s" % obs_package)
                continue

            upstream_version = dispatcher.get_upstream_version(obs_package)
            if obs_version != upstream_version:
                display_packages.append((obs_package,
                                         obs_version,
                                         upstream_version))
            time.sleep(0.2) # rate limit at 5 requests/s

    print("% 28s % 12s% 12s" % ('Package', 'Trunk', 'upstream'))

    for l in display_packages:
        name = l[0]
        obs_version = l[1]
        upstream_version = l[2]
        print "% 28s % 12s% 12s" % (name, obs_version, upstream_version)
