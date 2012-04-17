#!/usr/bin/env python

import os, sys
from distutils.core import setup
try:
    import setuptools
    # enable "setup.py develop", optional
except ImportError:
    pass

if 'install' in sys.argv and \
   'MAKEFLAGS' not in os.environ and \
   'RPM_BUILD_ROOT' not in os.environ:
        repl = raw_input('WARNING: Please use `make install` for installation, continue(y/N)? ')
        if repl != 'y':
            sys.exit(1)

# For debian based systems, '--install-layout=deb' is needed after 2.6
if sys.version_info[:2] <= (2, 5) and '--install-layout=deb' in sys.argv:
    del sys.argv[sys.argv.index('--install-layout=deb')]

version_path = 'VERSION'
try:
    # first line should be the version number
    version = open(version_path).readline().strip()
    ver_file = open('dawati-obs/__version__.py', 'w')
    ver_file.write("VERSION = \"%s\"\n" % version)
    ver_file.close()
except IOError:
    print 'WARNING: Cannot write version number file'
    pass

setup(name='dawati-obs-tools',
      version = version,
      description='Tools to ease OBS maintainance for Dawati',
      author='Damien Lespiau',
      author_email='damien.lespiau@intel.com',
      url='http://www.dawati.org/',
      scripts=['tools/dawati-obs', 'tools/dawati-obs-compare',
               'tools/dawati-obs-import'],
      packages=['dawati'],
      package_data={'dawati-obs': ['data/urldb']},
     )
