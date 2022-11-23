Deploy
======

A new release (PyPi package) will be created automatically if a tag was created using `Github actions`_. If the release
has to be uploaded manually, you will have to install ``twine`` first:

.. code-block:: bash

    $ pip install twine

Then you have to create a new distribution file:

.. code-block:: bash

    $ make dist

Finally you can upload the file to PyPi:

.. code-block:: bash

    $ twine upload dist/*

.. _Github actions: https://github.com/rheinwerk-verlag/pganonymize/actions
