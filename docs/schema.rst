Schema
======

Definition
----------

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

``search``
~~~~~~~~~~

You can also specify a (SQL WHERE) `search_condition`, to filter the table for rows to be anonymized.
This is useful if you need to anonymize one or more specific records, eg for "Right to be forgotten" (GDPR etc) purpose.

**Example**::

    tables:
     - auth_user:
        search: id BETWEEN 18 AND 140 AND user_type = 'customer'
        fields:
         - first_name:
            provider:
              name: clear

Providers
---------

Providers are the tools, which means functions, used to alter the data within the database. The following provider are
currently supported:

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

**Arguments:**

* ``sign``: The sign to be used to replace the original characters (default ``X``).

This provider will replace each character with a static sign.

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

The value can also be a dictionary for JSONB columns::

    tables:
     - auth_user:
        fields:
         - first_name:
            provider:
              name: set
              value: '{"foo": "bar", "baz": 1}'

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
