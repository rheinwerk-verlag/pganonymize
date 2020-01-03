BROWSER ?= xdg-open
PYTHON_PACKAGE = pganonymizer
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

flake8: ## run style checks and static analysis with flake8
	@poetry run flake8

release: clean ## package and upload a release
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

test:
	@poetry run pytest --cov=poetry --cov-config .coveragerc tests/ -sq