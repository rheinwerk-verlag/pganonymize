# Changelog

## Development

* [#53 Python 2.7 tests are failing](https://github.com/rheinwerk-verlag/pganonymize/pull/53)
  * Dropped Python 3.6, 3.7 support
  * Split requirements into Python 2 and 3
  * Use markdown for the changelog and contributing docs

## 0.11.0 (2024-02-29)

* [#52 Add update_json provider](https://github.com/rheinwerk-verlag/pganonymize/pull/52) ([bobslee](https://github.com/bobslee))

## 0.10.0 (2022-11-29)

* [#49 Configure psycopg2 to support UUID objects](https://github.com/rheinwerk-verlag/pganonymize/pull/49)
* [#48 Add support for localized "Faker" data](https://github.com/rheinwerk-verlag/pganonymize/pull/48)

## 0.9.0 (2022-11-23)

* [#46 Broken Python 2.7 compatibility](https://github.com/rheinwerk-verlag/pganonymize/pull/46)
* [#45 Add partial masked provider](https://github.com/rheinwerk-verlag/pganonymize/pull/45) ([Tilley](https://github.com/Tilley/))
* [#44 Pass kwargs through to faker functions from schema](https://github.com/rheinwerk-verlag/pganonymize/pull/44)([Tilley](https://github.com/Tilley>))

## 0.8.0 (2022-03-15)

* [#39 Renamed project to "pganonymize"](https://github.com/rheinwerk-verlag/pganonymize/issues/39)
* [#38 Allow environment variables in schema definition](https://github.com/rheinwerk-verlag/pganonymize/pull/38) ([nurikk](https://github.com/nurikk))

## 0.7.0 (2021-11-30)

* [#34 Subprocess "run" being used on Python2.7](https://github.com/rheinwerk-verlag/pganonymize/issues/34)
* [#35 parmap no longer supports Python 2.7](https://github.com/rheinwerk-verlag/pganonymize/issues/35)
  * Dropped Python 3.5 support
  * Pinned libraries Python 2.7
* [#32 Fixed pg_dump arguments](https://github.com/rheinwerk-verlag/pganonymize/pull/32) ([korsar182](https://github.com/korsar182))
* Simplified provider registration (no metaclass usage anymore)

## 0.6.1 (2021-07-13)

* Added missing dependencies for the `setup.py`

## 0.6.0 (2021-07-13)

* [#28 Add json support](https://github.com/rheinwerk-verlag/pganonymize/pull/25) ([nurikk](https://github.com/nurikk))
* [#27 Better anonymisation](https://github.com/rheinwerk-verlag/pganonymize/pull/25) ([nurikk](https://github.com/nurikk))
* [#25 Remove column specification for `cursor.copy_from` call](https://github.com/rheinwerk-verlag/pganonymize/pull/25) ([nurikk](https://github.com/nurikk))

## 0.5.0 (2021-06-30)

* [#22 Fix table and column name quotes in `cursor.copy_from` call](https://github.com/rheinwerk-verlag/pganonymize/pull/22) ([nurikk](https://github.com/nurikk))
* [#23 Allow uniq faker](https://github.com/rheinwerk-verlag/pganonymize/pull/23) ([nurikk](https://github.com/nurikk))

## 0.4.1 (2021-05-27)

* [#19 Make chunk size in the table definition dynamic](https://github.com/rheinwerk-verlag/pganonymize/pull/19) ([halilkaya](https://github.com/halilkaya))

## 0.4.0 (2021-05-05)

* [#18 Specify (SQL WHERE) search_condition, to filter the table for rows to be anonymized](https://github.com/rheinwerk-verlag/pganonymize/pull/18) (`bobslee <https://github.com/bobslee>`_)
* [#17 Fix anonymizing error if there is a JSONB column in a table](https://github.com/rheinwerk-verlag/pganonymize/pull/17) ([koptelovav](https://github.com/koptelovav))

## 0.3.3 (2021-04-16)

* [#16 Preserve column and table cases during the copy process](https://github.com/rheinwerk-verlag/pganonymize/issues/16)

## 0.3.2 (2021-01-25)

* [#15 Fix for exclude bug](https://github.com/rheinwerk-verlag/pganonymize/pull/15) ([abhinavvaidya90](https://github.com/abhinavvaidya90))

## 0.3.1 (2020-12-04)

* [#13 Fixed a syntax error if no truncated tables are defined](https://github.com/rheinwerk-verlag/pganonymize/pull/13) ([ray-man](https://github.com/ray-man))

## 0.3.0 (2020-02-11)

* Use [`python-poetry`](https://github.com/python-poetry/poetry) for requirements management
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
