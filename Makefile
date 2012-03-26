PYTHON ?= python
VERSION = $(shell cat VERSION)
TAGVER = $(shell cat VERSION | sed -e "s/\([0-9\.]*\).*/\1/")
DESTDIR ?= /

ifeq ($(VERSION), $(TAGVER))
	TAG = $(TAGVER)
else
	TAG = "HEAD"
endif

all:
	$(PYTHON) setup.py build

dist-bz2:
	git archive --format=tar --prefix=dawati-obs-$(VERSION)/ $(TAG) | \
		bzip2  > dawati-obs-$(VERSION).tar.bz2

install: all install-data
	$(PYTHON) setup.py install --root=${DESTDIR}

develop: all install-data
	$(PYTHON) setup.py develop

install-data:
	install -d ${DESTDIR}/usr/share/dawati-obs
	install -m 644 data/urldb ${DESTDIR}/usr/share/dawati-obs

clean:
	rm -rf build/
