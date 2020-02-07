Deploy
======

To create a new release you will have to install ``twine`` first::

    $ pip install twine

Then you have to create a new distribution file::

    $ make dist

Finally you can upload the file to PyPi::

    $ twine upload dist/*
