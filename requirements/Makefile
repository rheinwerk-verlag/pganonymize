REQUIREMENTS_SOURCES := $(wildcard *.in)
REQUIREMENTS := $(REQUIREMENTS_SOURCES:.in=.txt)
PIP_INDEX_URL ?= https://pypi.python.org/simple

all: $(REQUIREMENTS)

dev-py2.txt: tox-py2.txt
dev-py3.txt: tox-py3.txt

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
