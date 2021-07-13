PostgreSQL Anonymizer
=====================

A commandline tool to anonymize PostgreSQL databases for DSGVO/GDPR purposes.

It uses a YAML file to define which tables and fields should be anonymized and provides various methods of anonymization. The tool requires a direct PostgreSQL connection to perform the anonymization.

.. class:: no-web no-pdf

    |python| |license| |pypi| |downloads| |build| |health|

.. contents::

.. section-numbering::

Features
--------

* Intentionally compatible with Python 2.7 (for old, productive platforms)
* Anonymize PostgreSQL tables on data level entry with various methods (s. table below)
* Exclude data for anonymization depending on regular expressions
* Truncate entire tables for unwanted data

+----------------+----------------------+-------------------------+----------------------------------+
| Field          | Value                | Provider                | Output                           |
+================+======================+=========================+==================================+
| ``first_name`` | John                 | ``choice``              | (Bob|Larry|Lisa)                 |
+----------------+----------------------+-------------------------+----------------------------------+
| ``title``      | Dr.                  | ``clear``               |                                  |
+----------------+----------------------+-------------------------+----------------------------------+
| ``street``     | Irving St            | ``faker.street_name``   | Miller Station                   |
+----------------+----------------------+-------------------------+----------------------------------+
| ``password``   | dsf82hFxcM           | ``mask``                | XXXXXXXXXX                       |
+----------------+----------------------+-------------------------+----------------------------------+
| ``email``      | jane.doe@example.com | ``md5``                 | 0cba00ca3da1b283a57287bcceb17e35 |
+----------------+----------------------+-------------------------+----------------------------------+
| ``email``      | jane.doe@example.com | ``faker.unique.email``  | alex7@sample.com                 |
+----------------+----------------------+-------------------------+----------------------------------+
| ``phone_num``  | 65923473             | ``md5`` as_number: True | 3948293448                       |
+----------------+----------------------+-------------------------+----------------------------------+
| ``ip``         | 157.50.1.20          | ``set``                 | 127.0.0.1                        |
+----------------+----------------------+-------------------------+----------------------------------+
| ``uuid_col``   | 00010203-0405-...... | ``uuid4``               | f7c1bd87-4d....                  |
+----------------+----------------------+-------------------------+----------------------------------+

Note: `faker.unique.[provider]` only supported on python3.5+ (Faker library min supported python version)
Note: `uuid4` - only for (native `uuid4<https://www.postgresql.org/docs/current/datatype-uuid.html>`) columns

See the `documentation`_ for a more detailed description of the provided anonymization methods.

Installation
------------

The default installation method is to use ``pip``::

    $ pip install pganonymize

Usage
-----

::

    usage: pganonymize [-h] [-v] [-l] [--schema SCHEMA] [--dbname DBNAME]
                   [--user USER] [--password PASSWORD] [--host HOST]
                   [--port PORT] [--dry-run] [--dump-file DUMP_FILE]

    Anonymize data of a PostgreSQL database

    optional arguments:
    -h, --help            show this help message and exit
    -v, --verbose         Increase verbosity
    -l, --list-providers  Show a list of all available providers
    --schema SCHEMA       A YAML schema file that contains the anonymization
                            rules
    --dbname DBNAME       Name of the database
    --user USER           Name of the database user
    --password PASSWORD   Password for the database user
    --host HOST           Database hostname
    --port PORT           Port of the database
    --dry-run             Don't commit changes made on the database
    --dump-file DUMP_FILE
                            Create a database dump file with the given name
    --init-sql INIT_SQL   SQL to run before starting anonymization

Despite the database connection values, you will have to define a YAML schema file, that includes
all anonymization rules for that database. Take a look at the `schema documentation`_ or the
`YAML sample schema`_.


Example call::

    $ pganonymize --schema=myschema.yml \
        --dbname=test_database \
        --user=username \
        --password=mysecret \
        --host=db.host.example.com \
        -v

    $ pganonymize --schema=myschema.yml \
        --dbname=test_database \
        --user=username \
        --password=mysecret \
        --host=db.host.example.com \
        --init-sql "set search_path to non_public_search_path; set work_mem to '1GB';" \
        -v

Database dump
~~~~~~~~~~~~~

With the ``--dump-file`` argument it is possible to create a dump file after anonymizing the database. Please note,
that the ``pg_dump`` command from the ``postgresql-client-common`` library is necessary to create the dump file for the
database, e.g. under Linux::

    sudo apt-get install postgresql-client-common

Example call::

    $ pganonymize --schema=myschema.yml \
        --dbname=test_database \
        --user=username \
        --password=mysecret \
        --host=db.host.example.com \
        --dump-file=/tmp/dump.gz \
        -v

Quickstart
----------

Clone repo::

    $ git clone git@github.com:rheinwerk-verlag/postgresql-anonymizer.git
    $ cd postgresql-anonymizer

For making changes and developing pganonymizer, you need to install ``poetry``::

    $ sudo pip install poetry

Now you can install all requirements and activate the virtualenv::

    $ poetry install
    $ poetry shell

Docker
------

If you want to run the anonymizer within a Docker container you first have to build the image::

    $ docker build -t pganonymizer .

After that you can pass a schema file to the container, using Docker volumes, and call the anonymizer::

    $ docker run \
        -v <path to your schema>:/schema.yml \
        -it pganonymizer \
        /usr/local/bin/pganonymize \
        --schema=/schema.yml \
        --dbname=<database> \
        --user=<user> \
        --password=<password> \
        --host=<host> \
        -v


.. _documentation: https://python-postgresql-anonymizer.readthedocs.io/en/latest/
.. _schema documentation: https://python-postgresql-anonymizer.readthedocs.io/en/latest/schema.html
.. _YAML sample schema: https://github.com/rheinwerk-verlag/postgresql-anonymizer/blob/master/sample_schema.yml

.. |python| image:: https://img.shields.io/pypi/pyversions/pganonymize
    :alt: PyPI - Python Version

.. |license| image:: https://img.shields.io/badge/license-MIT-green.svg
    :target: https://github.com/rheinwerk-verlag/postgresql-anonymizer/blob/master/LICENSE.rst

.. |pypi| image:: https://badge.fury.io/py/pganonymize.svg
    :target: https://badge.fury.io/py/pganonymize

.. |downloads| image:: https://static.pepy.tech/personalized-badge/pganonymize?period=total&units=international_system&left_color=blue&right_color=black&left_text=Downloads
    :target: https://pepy.tech/project/pganonymize
    :alt: Download count

.. |build| image:: https://github.com/rheinwerk-verlag/postgresql-anonymizer/workflows/Test/badge.svg
    :target: https://github.com/rheinwerk-verlag/postgresql-anonymizer/actions

.. |health| image:: https://snyk.io/advisor/python/pganonymize/badge.svg
  :target: https://snyk.io/advisor/python/pganonymize
  :alt: pganonymize

