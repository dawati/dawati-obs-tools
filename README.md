What is this about?
===================

dawati-obs-tools has a few scripts to help us maintain dawati-shell in an
OBS instance:

 *  **`dawati-obs-compare`**: Compares versions of packages we have in OBS
    projects with upstream versions
 *  **`dawati-obs update`**: Update a single package to a given version


Configuration
=============

Before using any of the dawati-obs-tools script you need to setup a small
configuration file ~/.dawati-obsrc that need to loo similar to:

    $ cat ~/.dawati-obsrc
    name="Damien Lespiau"
    email="damien.lespiau@foo.com"

    obs_repo_template='http://download.xxx.org/live/%s/Trunk_standard'
    obs_repo_trunk='http://download.xxx.org/live/Trunk/standard'

Obviously adjusting the value accordingly. This configuration file is designed
to be both loaded from a python script (execfile) and a bash script (source)
easily, so don't but any spaces aroud the '='!

The available keys are:

 *  `name`: Your name (for instance used to populate %changes in spec files)
 *  `email`: Your email address
 *  `obs_repo_template`: A URL template used to fetch the repomd.xml files from
    published rpm repositories. The OBS project name is inserted at %s
 *  `obs_repo_trunk`: The published URL for Trunk (in the general case, this is
    different from `obs_repo_template`)


dawati-obs-compare
==================

As stated above, this script is to compare some OBS packages with upstream
versions to flag packages that need an update. An example run:

    $ dawati-obs-compare -r MyProject:Devel
                         Package MyProject:Devel       upstream
                             atk          2.3.93          2.2.0
                         clutter           1.8.2         1.10.0
                     clutter-gtk           1.0.4          1.2.0
                          colord          0.1.16         0.1.18
                           dconf          0.11.6         0.12.0
                       evolution          3.3.91          3.4.0
                       farstream           0.1.1          0.1.2
                      gdk-pixbuf          2.25.2         2.26.0
                             gjs         1.31.20        1.31.22
                 glib-networking         2.31.22         2.30.2
                           glib2         2.31.20         2.32.0
                 gnome-bluetooth          3.3.92          3.2.2
            gnome-control-center           3.2.2          3.4.0
                   gnome-desktop           3.2.1          3.4.0
           gnome-online-accounts          3.3.92          3.4.0
           gnome-themes-standard          3.3.92          3.4.0
                          gnutls         2.12.18         3.0.17
           gobject-introspection         1.31.20         1.30.0
                gst-plugins-base         0.10.36         0.11.3
                gst-plugins-good         0.10.31         0.11.2
                       gstreamer         0.10.36         0.11.3
                            gtk3          3.3.18          3.4.0
                            gvfs          1.11.5         1.12.0
                        intltool          0.50.0         0.50.2
                        libcroco           0.6.4          0.6.5
                     libgnomekbd          3.3.90        3.4.0.1
                        librsvg2          2.35.2         2.36.0
                         libsoup         2.37.92         2.36.1
                     libxklavier             5.2          5.2.1
                            mesa          7.11.2          8.0.1
                         p11-kit            0.11           0.12
                           pango          1.29.5         1.28.4
                            rest          0.7.12      Not Found
             telepathy-farstream           0.2.2          0.2.3
                  telepathy-glib          0.17.6         0.17.7
                 totem-pl-parser          3.3.92          3.2.0
                            vala          0.15.2         0.16.0

The script will only shows the packages whose version is different from the
upstream version.

The script has some heuristics to detect stable/unstable versions. Note how we
have totem-pl-parser 3.3.92 is our OBS project, but the script is telling us
that upstream is still at 3.2.0. This is because it defaults to showing the
latest stable upstream version.

With the invocation above, the package list is simply all the packages we have
in the MyProject:Devel OBS project. There are other ways to give the tool the
packages we want to compare against upstream:

We want to compare a single package fro the MyProject:Devel project:

    $ dawati-obs-compare -r MyProject:Devel -p glib2
                         Package  MyProject:Devel       upstream
                           glib2         2.31.20         2.32.0

or we want to restrict the packages to a list we have in a file:

    $ cat packages.list
    farstream
    glib2
    gtk3
    gnome-desktop

    $ dawati-obs-compare -r MyProject:Devel -f packages.list
                         Package MyProject:Devel       upstream
                       farstream           0.1.1          0.1.2
                           glib2         2.31.20         2.32.0
                            gtk3          3.3.18          3.4.0
                   gnome-desktop           3.2.1          3.4.0

Another interesting feature is that you can spit out a CSV file with the
information above to be used later by another script:

    $ dawati-obs-compare -r MyProject:Devel -f packages.list -t csv -o packages

    $ cat packages
    Package;MyProject:Devel;upstream
    farstream;0.1.1;0.1.2
    glib2;2.31.20;2.32.0
    gtk3;3.3.18;3.4.0
    gnome-desktop;3.2.1;3.4.0


dawati-obs update
=================

This utility can be used to update a single package:

    $ osc co gnome-desktop && cd gnome-desktop
    A    gnome-desktop
    A    gnome-desktop-3.2.1.tar.xz
    A    gnome-desktop/gnome-desktop.changes
    A    gnome-desktop.spec

    $ dawati-obs update 3.3.92
    Info: Using gnome-desktop.spec
    Info: Updating to 3.3.92
    Info: Downloading http://download.gnome.org/sources/gnome-desktop/3.3/gnome-desktop-3.3.92.tar.xz
    gnome-desktop-3.3.92.tar.xz                              | 913 kB     00:00
    Info: Remove gnome-desktop-3.2.1.tar.xz

    $ osc diff

    Index: gnome-desktop.changes
    ===================================================================
    --- gnome-desktop.changes       (revision 9f6e6dc84012aac90e23f051215f2405)
    +++ gnome-desktop.changes       (working copy)
    @@ -1,3 +1,6 @@
    +* Mon Mar 26 2012 Damien Lespiau <damien.lespiau@intel.com> - 3.3.92
    +- Update to 3.3.92
    +
     * Tue Dec 13 2011 Damien Lespiau <damien.lespiau@intel.com> - 3.2.1
     - Update to 3.2.1
     - Cleanup spec file
    Index: gnome-desktop.spec
    ===================================================================
    --- gnome-desktop.spec  (revision 9f6e6dc84012aac90e23f051215f2405)
    +++ gnome-desktop.spec  (working copy)
    @@ -1,11 +1,11 @@
     Name:       gnome-desktop
     Summary:    GNOME Desktop Helper Library
    -Version:    3.2.1
    +Version:    3.3.92
     Release:    1
     Group:      System/Desktop
     License:    GPLv2+ LGPLv2+ GFDL
     URL:        http://www.gnome.org
    -Source0:    http://download.gnome.org/sources/%{name}/3.2/%{name}-%{version}.tar.xz
    +Source0:    http://download.gnome.org/sources/%{name}/3.3/%{name}-%{version}.tar.xz
     Requires(post): /sbin/ldconfig
     Requires(postun): /sbin/ldconfig
     BuildRequires:  pkgconfig(gtk-doc)


A Real World-ish Flow
=====================

Let's imagine I'm responsible for updating 4 package in an OBS based distro:

    $ cat ~/packages.list
    farstream
    glib2
    gtk3
    gnome-desktop

Let's now run compare to check which packages need an update:

    $ tmp=`mktemp -d` && cd $tmp

    $ dawati-obs-compare -r MyProject:Devel -f ~/packages.list -t csv -o need_update

    $ cat need_update
    Package;MyProject:Devel;upstream
    farstream;0.1.1;0.1.2
    glib2;2.31.20;2.32.0
    gtk3;3.3.18;3.4.0
    gnome-desktop;3.2.1;3.4.0

Now I can script around that file and dawati-obs update to do a bulk update. For
instance, this repository includes an update-packages script in scripts/:

    #!/bin/sh

    OBS_PROJECT=$1
    PACKAGES_LIST=$2

    # CSV file is name;obs_version;upstream_version (output of dawati-obs-compare)
    # The first line is column headers, so skip it.
    for line in `cat $PACKAGES_LIST | tail -n+2`; do
        csv=(${line//;/ })
        name=${csv[0]}
        version=${csv[2]}

        osc co $OBS_PROJECT $name
        cd $OBS_PROJECT/$name
        dawati-obs update $version
        osc ar
        osc commit -m "Update to $version"
        cd ..
    done

Which gives us:

    $ ~/src/dawati-obs-tools/scripts/update-packages MyProject:Devel need_update

    [lots of about about what it's doing]

Result: new the new tarballs have been uploaded, time to check OBS to fix the
eventual build errors.

Of course, this does not mean the work is over, you need to check for new
dependencies, fix the installed file list, do other useful cleanups, but this
takes care of the more boring and repetitive work.
