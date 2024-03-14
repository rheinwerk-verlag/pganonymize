# Contributing to PostgreSQL Anonymizer

First of all: thanks for your interest in this project and taking the time to contribute.

The following document is a small set of guidelines for contributing to this project. They are guidelines and no rules.

## Reporting bugs

If you have found a bug, please check the project's 
[issue](https://github.com/rheinwerk-verlag/pganonymize/issues) page first and feel free to create a 
[new issue](https://github.com/rheinwerk-verlag/pganonymize/issues/new), if no one else has reported it yet.

## Making changes

Create a fork if you want to make changes or clone the repo if you want a readonly access to the current development
version:

```bash
$ git clone git@github.com:rheinwerk-verlag/pganonymize.git
$ cd pganonymize
```

For the development use a virtualenv or install the requirements directly:

```bash
$ sudo pip install -r requirements.txt
```

## Coding style

We have created an [EditorConfig](https://editorconfig.org/) file for this project that should be usable for most IDEs. 
Otherwise please make sure to adhere to the specifications from the config file.

## Creating a pull request

Before creating a pull request make sure to check:

* existing docstrings have been updated
* new code has valid docstrings
* whether existing [tests](https://github.com/rheinwerk-verlag/pganonymize/tree/development/tests) have to be fixed
* new tests have to be written first
* the documentation (in particular the [Sphinx documentation](https://github.com/rheinwerk-verlag/pganonymize/tree/development/docs)) has to be modified
