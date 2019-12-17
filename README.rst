PostgreSQL Anonymizer
=====================

.. image:: https://travis-ci.org/hkage/postgresql-anonymizer.svg?branch=master
    :target: https://travis-ci.org/hkage/postgresql-anonymizer

.. image:: https://img.shields.io/badge/license-MIT-green.svg
    :target: https://github.com/hkage/postgresql-anonymizer/blob/master/LICENSE.rst


A commandline tool to anonymize PostgreSQL databases.

Installation
------------

The default installation method is to use ``pip``::

    $ pip install pganonymize

Usage
-----

::

    usage: pganonymize [-h] [-v] --schema SCHEMA [--dbname DBNAME] [--user USER]
              [--password PASSWORD] [--host HOST] [--port PORT] [--dry-run]

    Anonymize data of a PostgreSQL database

    optional arguments:
    -h, --help           show this help message and exit
    -v, --verbose        Increase verbosity
    --schema SCHEMA      A YAML file that contains the anonymization rules
    --dbname DBNAME      Name of the database
    --user USER          Name of the database user
    --password PASSWORD  Password for the database user
    --host HOST          Database hostname
    --port PORT          Port of the database
    --dry-run            Dont commit changes made on the database

Schema definition
-----------------

``pganonymize`` uses a YAML based schema definition for the anonymization rules.

On the top level a list of tables can be defined with the ``tables`` keyword. This will define
which tables should be anonymized.

On the table level you can specify the tables primary key with the keyword ``primary_key`` if it
isn't the default ``id``.

Starting with the keyword ``fields`` you can specify all fields, that should be available for the
anonymization process. Each field entry has its own ``provider`` that defines how the field should
be treated.

**Example**::

    tables:
     - auth_user:
        primary_key: id
        fields:
         - first_name:
            provider: clear
     - customer_email:
        fields:
         - email:
            provider: md5
            append: @localhost


Providers
---------

Provider are the tools, that means functions, used to alter the data within the database.
The following provider are currently supported:

``clear``
~~~~~~~~~

**Arguments:** none

The ``clear`` provider will set a database field to ``null``.

.. note::
   But remember, that you can set fields to ``null`` only if the database field is not nullable.

**Example usage**::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider: clear


``fake``
~~~~~~~~

**Arguments:** none

``pganonymize`` supports all providers from the Python library Faker_. All you have to do is prefix
the provider with ``faker`` and use the provider function from the Faker library, e.g:

* ``fake.first_name``
* ``fake.street_name``

.. note::
   Please note: using the ``Faker`` library will generate randomly generated data for each data row
   within a table. This will dramatically slow down the anonymization process.

**Example usage**::

    tables:
     - auth_user:
        fields:
         - email:
            provider: fake.email


``md5``
~~~~~~~

**Arguments:** none

This provider will hash the given field value with the MD5 algorithm.

**Example usage**::

    tables:
     - auth_user:
        fields:
         - password:
            provider: md5


``set``
~~~~~~~

**Arguments:**

* ``value``: The value to set

**Example usage**::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider: set
            value: "Foo"


Arguments
---------

In addition to the providers there is also a list of arguments that can be added to each provider:

``append``
~~~~~~~~~~

This argument will append a value at the end of the altered value:

**Example usage**::

    tables:
     - auth_user:
        fields:
         - email:
            provider: md5
            append: "@example.com"

Quickstart
----------

Clone repo::

    $ git clone git@github.com:hkage/postgresql-anonymizer.git
    $ cd postgresql-anonymizer

Install tox, either system-wide via your distribution's package manager,
e.g. on debian/Ubuntu with::

    $ sudo apt-get install python-tox

... or create a virtualenv and install tox into it::

    $ mkvirtualenv postgresql-anonymizer
    (postgresql-anonymizer)$ pip install tox

Run the tests with the default Python version::

    $ py.test -v tests/

or::

    $ make test

Run the tests via tox for all Python versions configured in ``tox.ini``::

    $ tox

To see all available make target just run ``make`` without arguments.

Code Quality Assurance
----------------------

The included Makefile is set up to run several Python static code
checking and reporting tools. To print a list of available Makefile
targets and the tools they run, simple run::

    $ make

Unless noted otherwise, these targets run all tools directly, i.e.
without tox, which means they need to be installed in your Python
environment, preferably in a project-specific virtual environment.
To create a virtual environment with Python 3 (you may have to
install the package ``python3-virtualenv`` first) run::

    $ python3 -m venv postgresql-anonymizer

Or with Python 2 (you may have to install the packages
``virtualenv`` and ``virtualenvwrapper``) run::

    $ mkvirtualenv postgresql-anonymizer --python=python3.5

and to install all supported tools and their dependencies run::

    (postgresql-anonymizer)$ pip install -r requirements/dev.txt

Then run the Makefile target of your choice, e.g.::

    $ make flake8

Documentation
-------------

Package documentation is generated by Sphinx. The documentation can be build
with::

    $ make docs

After a successful build the documentation index is opened in your web browser.
You can override the command to open the browser (default ``xdg-open``) with
the ``BROWSER`` make variable, e.g.::

    $ make BROWSER=chromium-browser docs


TODOs
-----
* Add tests
* Add exceptions for certain field values
* Make the providers more pluggable (e.g. as own classes with a unqiue character id)
* Add option to create a database dump
* Add ``choice`` provider to randomly choice from a list of values


.. _Faker: https://faker.readthedocs.io/en/master/providers.html
