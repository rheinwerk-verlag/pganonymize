Tests
=====

For testing you have to install tox, either system-wide via your distribution's package manager, e.g. on debian/Ubuntu
with::

    $ sudo apt-get install python-tox

or via pip::

    $ sudo pip install tox

Run the tests via tox for all Python versions configured in ``tox.ini``::

    $ tox

To see all available make target just run ``make`` without arguments.
