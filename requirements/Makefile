REQUIREMENTS_SOURCES := $(wildcard *.in)
REQUIREMENTS := $(REQUIREMENTS_SOURCES:.in=.txt)

all: $(REQUIREMENTS)

dev.txt: base.txt

production.txt: base.txt

%.txt: %.in
	pip-compile \
	    --verbose \
	    --rebuild \
	    --output-file=$@ $<
	sed -i -e 's|^--|#--|' $@

check:
	@which pip-compile > /dev/null

clean: check
	rm -f *.txt

.PHONY: all check clean