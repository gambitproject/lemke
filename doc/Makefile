# Makefile for Sphinx documentation

SPHINXBUILD = sphinx-build
BUILDDIR    = _build

.PHONY: help clean html livehtml

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html      to make standalone HTML files"
	@echo "  livehtml  to make HTML files with auto-rebuild and live server"
	@echo "  clean     to remove the built documentation"

clean:
	-rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html . $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

livehtml:
	sphinx-autobuild -b html . $(BUILDDIR)/html
