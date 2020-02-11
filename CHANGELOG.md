# Changelog

## Development

## 0.3.0 (2020-02-11)

* Use [python-poetry](https://github.com/python-poetry/poetry) for requirements management
* Added commandline argument to list all available providers (#4)
* Added commandline argument to create a dump file (#5)
* Execute table truncation in one statement to avoid foreign key constraint errors (thanks to [W1ldPo1nter](https://github.com/W1ldPo1nter))

## 0.2.4 (2020-01-03)

* Fixed several issues with the usage of ``dict.keys`` and Python 3

## 0.2.3 (2020-01-02)

* Fixed the wrong cStringIO import for Python 3
* Removed Travis-CI file in favor of the Github actions

## 0.2.2 (2020-01-02)

* Hide the progressbar completely if verbose is set to ``False``
* Restructured the requirement files and added flake8 to Travis CI

## 0.2.1 (2019-12-20)

* Added field based, regular expression excludes (to skip data under certain conditions).
  Currently only regular expressions are supported and the exclusion affects the whole row,
  not just one single column.

## 0.2.0 (2019-12-20)

* Added provider classes
* Added new providers:
  * choice - returns a random list element
  * mask - replaces the original value with a static sign

## 0.1.1 (2019-12-18)

Changed setup.py

## 0.1.0 (2019-12-16)

Initial release of the prototype
