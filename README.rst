PostgreSQL Anonymizer
=====================

This commandline tool makes PostgreSQL database anonymization easy. It uses a YAML definition file
to define which tables and fields should be anonymized and provides various methods of anonymization
(e.g. masking, faking or truncating complete tables).

.. class:: no-web no-pdf

    |license| |pypi| |downloads| |build|

.. contents::

.. section-numbering::

Installation
------------

``pganonymize`` is Python 2 and Python 3 compatible.

The default installation method is to use ``pip``::

    $ pip install pganonymize

Usage
-----

::

    usage: pganonymize [-h] [-v] [-l] [--schema SCHEMA] [--dbname DBNAME]
                       [--user USER] [--password PASSWORD] [--host HOST]
                       [--port PORT] [--dry-run]

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

Example call::

    $ pganonymize --schema=myschema.yml \
        --dbname=test_database \
        --user=username \
        --password=mysecret \
        --host=db.host.example.com \
        -v
      
Schema definition
-----------------

``pganonymize`` uses a YAML based schema definition for the anonymization rules.

``tables``
~~~~~~~~~~

On the top level a list of tables can be defined with the ``tables`` keyword. This will define
which tables should be anonymized.

On the table level you can specify the tables primary key with the keyword ``primary_key`` if it
isn't the default ``id``.

``fields``
~~~~~~~~~~

Starting with the keyword ``fields`` you can specify all fields of a table, that should be available for the
anonymization process. Each field entry has its own ``provider`` that defines how the field should
be treated.

**Example**::

    tables:
     - auth_user:
        primary_key: id
        fields:
         - first_name:
            provider:
              name: clear
     - customer_email:
        fields:
         - email:
            provider:
              name: md5
            append: @localhost

``excludes``
~~~~~~~~~~~~

For each table you can also specify a list of ``excludes``. Each entry has to be a field name which contains
a list of exclude patterns. If one of these patterns matches, the whole table row won't ne anonymized.

**Example**::

    tables:
     - auth_user:
        primary_key: id
        fields:
         - first_name:
            provider:
              name: clear
        excludes:
         - email:
           - "\\S[^@]*@example\\.com"

This will exclude all data from the table ``auth_user`` that have an ``email`` field which matches the
regular expression pattern (the backslash is to escape the string for YAML).

``truncate``
~~~~~~~~~~~~

In addition to the field level providers you can also specify a list of tables that should be cleared with
the  `truncated` key. This is useful if you don't need the table data for development purposes or the reduce 
the size of the database dump.

**Example**::

    truncate:
     - django_session
     - my_other_table

If two tables have a foreign key relation and you don't need to keep one of the table's data, just add the
second table and they will be truncated at once, without causing a constraint error.

Providers
---------

Providers are the tools, which means functions, used to alter the data within the database.
The following provider are currently supported:

``choice``
~~~~~~~~~~

This provider will define a list of possible values for a database field and will randomly make a choice
from this list.

**Arguments:**

* ``values``: All list of values

**Example usage**::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider:
              name: choice
              values:
                - "John"
                - "Lisa"
                - "Tom"

``clear``
~~~~~~~~~

**Arguments:** none

The ``clear`` provider will set a database field to ``null``.

.. note::
   But remember, that you can set fields to ``null`` only if the database field allows null values.

**Example usage**::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider:
              name: clear


``fake``
~~~~~~~~

**Arguments:** none

``pganonymize`` supports all providers from the Python library Faker_. All you have to do is prefix
the provider with ``fake`` and then use the function name from the Faker library, e.g:

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
            provider:
              name: fake.email

``mask``
~~~~~~~~

This provider will replace each character with a static sign.

**Arguments:**

* ``sign``: The sign to be used to replace the original characters (default ``X``).

**Example usage**::

    tables:
     - auth_user:
        fields:
         - last_name:
            provider:
              name: mask
              sign: '?'


``md5``
~~~~~~~

**Arguments:** none

This provider will hash the given field value with the MD5 algorithm.

**Example usage**::

    tables:
     - auth_user:
        fields:
         - password:
            provider:
              name: md5


``set``
~~~~~~~

**Arguments:**

* ``value``: The value to set

**Example usage**::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider:
              name: set
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
            provider:
              name: md5
            append: "@example.com"

Quickstart
----------

Clone repo::

    $ git clone git@github.com:rheinwerk-verlag/postgresql-anonymizer.git
    $ cd postgresql-anonymizer

For making changes and developing pganonymizer, you need to install ``poetry``::

    $ sudo pip install poetry

Now you cann install all requirements and activate the virtualenv::

    $ poetry install
    $ poetry shell

For testing you have to install tox, either system-wide via your distribution's package manager,
e.g. on debian/Ubuntu with::

    $ sudo apt-get install python-tox

or via pip::

    $ sudo pip install tox

Run the tests via tox for all Python versions configured in ``tox.ini``::

    $ tox

If you want to test only against your default Python version, just run::

    $ make test

or activate the virtualenv and run::

    $ poetry shell
    $ pytest -v

To see all available make target just run ``make`` without arguments.

Docker
------

If you want to run the anonymizher within a Docker container you first have to build the image::

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

Documentation
-------------

Package documentation is generated by Sphinx. The documentation can be build
with::

    $ make docs

After a successful build the documentation index is opened in your web browser.
You can override the command to open the browser (default ``xdg-open``) with
the ``BROWSER`` make variable, e.g.::

    $ make BROWSER=chromium-browser docs


.. _Faker: https://faker.readthedocs.io/en/master/providers.html

.. |license| image:: https://img.shields.io/badge/license-MIT-green.svg
    :target: https://github.com/rheinwerk-verlag/postgresql-anonymizer/blob/master/LICENSE.rst

.. |pypi| image:: https://badge.fury.io/py/pganonymize.svg
    :target: https://badge.fury.io/py/pganonymize

.. |downloads| image:: https://pepy.tech/badge/pganonymize
    :target: https://pepy.tech/project/pganonymize
    :alt: Download count

.. |build| image:: https://github.com/rheinwerk-verlag/postgresql-anonymizer/workflows/Test/badge.svg
    :target: https://github.com/rheinwerk-verlag/postgresql-anonymizer/actions
