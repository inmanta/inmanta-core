# Impera Framework

[![docs](https://readthedocs.org/projects/impera/badge/?version=latest)](http://impera.readthedocs.org/en/latest/)

This repository contains the Impera configuration management tool.

## Download the latest version

Download a tarball of Impera or checkout the latest version from the git repository:

    wget https://github.com/bartv/impera/archive/master.zip
    unzip master.zip

or

    git clone git@github.com:bartv/impera.git

## Requirements

Impera uses Python3 and therefore requires Python3 to be installed. Most recent
distributions already provide at least the python3 runtime. Additional requirements are listed
in the requirements.txt file. This file can be used by pip to install all dependencies.

    pip install -r requirements.txt

The installation also requires python3-setuptools.

## Installation

Install Impera:

    python3 setup.py install

Now the ``impera`` command should be available.

## Documentation

http://impera.readthedocs.org/en/latest/

Check the docs/sphinx directory of the source distribution.

## Author

Bart Vanbrabant <bart@impera.io>, Impera
