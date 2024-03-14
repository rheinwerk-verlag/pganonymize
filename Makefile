BROWSER ?= xdg-open
PYTHON_PACKAGE = pganonymize
TESTS_PACKAGE = tests

.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

help:
	@echo "Available Makefile targets:"
	@echo
	@echo "dist           builds source and wheel package"
	@echo "install        install the package to the active Python environment"
	@echo "docs           generate Sphinx HTML documentation, including API docs"
	@echo "docs-open      open the index HTML file from the docs in the default web browser"
	@echo "docs-all       generate the Sphinx HTML documentation and open it in the default web browser"
	@echo "test           run tests with the default Python version"
	@echo "test-all       run tests on every Python version with tox"
	@echo "flake8         run style checks and static analysis with flake8"
	@echo "pylint         run style checks and static analysis with pylint"
	@echo "docstrings     check docstring presence and style conventions with pydocstyle"
	@echo "coverage       check code coverage with the default Python version"
	@echo "metrics        print code metrics with radon"
	@echo "clean          remove all build, test, coverage and Python artifacts"
	@echo "clean-build    remove Python file artifacts"
	@echo "clean-pyc      remove Python file artifacts"

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr reports/

test: ## run tests quickly with the default Python
	python setup.py test

test-all: ## run tests on every Python version with tox
	tox

pylint: ## run style checks and static analysis with pylint
	@-mkdir -p reports/
	@-pylint $(PYTHON_PACKAGE) -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports/pylint.txt
	@echo "See reports/pylint.txt"
	@-pylint $(PYTHON_PACKAGE)

flake8: ## run style checks and static analysis with flake8
	@-mkdir -p reports/
	flake8 $(PYTHON_PACKAGE) $(TESTS_PACKAGE) --format='%(path)s:%(row)d: [%(code)s(%(code)s), ] %(text)s' --output-file=reports/flake8.txt --tee

docstrings: ## check docstring presence and style conventions with pydocstyle
	pydocstyle $(PYTHON_PACKAGE)

lint: flake8 docstrings pylint

coverage: ## check code coverage quickly with the default Python
	py.test --cov-report html:reports/htmlcov --cov-report xml:reports/coverage.xml
	@echo "See reports/htmlcov/index.html"

metrics: ## print code metrics with radon
	radon raw -s $(PYTHON_PACKAGE) $(TEST_PACKAGE)
	radon cc -s $(PYTHON_PACKAGE) $(TEST_PACKAGE)
	radon mi -s $(PYTHON_PACKAGE) $(TEST_PACKAGE)

docs: ## generate Sphinx HTML documentation, including API docs
	@if python -c 'import sys; sys.exit(sys.version_info[0]<3)'; then \
		rm -rf docs/_api; \
		sphinx-apidoc --no-toc -o docs/_api $(PYTHON_PACKAGE) "**/tests" "**/migrations" "**/south_migrations"; \
		$(MAKE) -C docs clean; \
		$(MAKE) -C docs html; \
		echo "See docs/_build/html/index.html"; \
	else \
		echo "Please build the docs using Python 3."; \
	fi

docs-open:
	$(BROWSER) docs/_build/html/index.html

docs-all: docs docs-open

release: clean ## package and upload a release
	python setup.py release upload

dist: clean ## builds source and wheel package
	python setup.py release
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
