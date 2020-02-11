Tests
=====

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
