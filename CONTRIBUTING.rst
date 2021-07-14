Contributing to PostgreSQL Anonymizer
=====================================

First of all: thanks for your interest in this project and taking the time to contribute.

The following document is a small set of guidelines for contributing to this project. They are guidelines and no rules.

Reporting bugs
---------------

If you have found a bug, please check the project's `issue`_ page first and feel free to create a `new issue`_, if no
one else has reported it yet.

Making changes
--------------

Create a fork if you want to make changes or clone the repo if you want a readonly access to the current development
version:

.. code-block:: sh

    $ git clone git@github.com:rheinwerk-verlag/postgresql-anonymizer.git
    $ cd postgresql-anonymizer

We are using `poetry`_ for development, you may need to install it first:

.. code-block:: sh

    $ sudo pip install poetry

Now you can install all development requirements and activate the virtualenv:

.. code-block:: sh

    $ poetry install
    $ poetry shell

Coding style
------------

We have created an `EditorConfig`_ file for this project that should be usable for most IDEs. Otherwise please make
sure to adhere to the specifications from the config file.

Creating a pull request
-----------------------

Before creating a pull request make sure to check:

* existing docstrings have been updated
* new code has valid docstrings
* whether existing `tests`_ have to be fixed
* new tests have to be written first
* the documentation (in particular the `Sphinx documentation`_) has to be modified

.. _issue: https://github.com/rheinwerk-verlag/postgresql-anonymizer/issues
.. _new issue: https://github.com/rheinwerk-verlag/postgresql-anonymizer/issues/new
.. _poetry: https://python-poetry.org/
.. _EditorConfig: https://editorconfig.org/
.. _tests: https://github.com/rheinwerk-verlag/postgresql-anonymizer/tree/development/tests
.. _Sphinx documentation: https://github.com/rheinwerk-verlag/postgresql-anonymizer/tree/development/docs
