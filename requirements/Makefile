REQUIREMENTS_SOURCES := $(wildcard *.in)
REQUIREMENTS := $(REQUIREMENTS_SOURCES:.in=.txt)
PIP_INDEX_URL ?= https://devpi.intern.rheinwerk.de/rheinwerk/prod/+simple

all: $(REQUIREMENTS)

dev.txt: tox.txt

%.txt: %.in
	pip-compile \
	    --verbose \
	    --rebuild \
	    --index-url=$(PIP_INDEX_URL) \
	    --output-file=$@ $<
	sed -i -e 's|^--|#--|' $@

check:
	@which pip-compile > /dev/null

clean: check
	rm -f *.txt

.PHONY: all check clean
