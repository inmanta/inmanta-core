********************************
Developer Getting Started Guide
********************************

This guide explains how to set up the recommended developer setup on a Linux machine. 
Other development setups are possible, but this one provides a good starting point.

* Install VS Code and Inmanta extension.
* Setting up Python virtual environments.
* Benefit from linting and code navigation by setting up a project.
* Set project sources
* Module developers guide

**The examples below are using ``pip`` your system might require you to use ``pip3``**.


Install VS Code and Inmanta extension
#######################################

The developer setup is based on VSCode with the Inmanta extension.

In order to install VS Code, you can refer to `this <https://code.visualstudio.com/learn/get-started/basics>`_ page.

Inmanta's extension in VS Code marketplace can be found `here <https://marketplace.visualstudio.com/items?itemName=inmanta.inmanta>`_. 

Further information about Inmanta VS Code extension is available on `this <https://github.com/inmanta/vscode-inmanta>`_ page.


Setting up Python virtual environments
########################################

Python ``venv``s are used to create virtual environments. If you need a refresher, you can check out `this <https://docs.python.org/3/tutorial/venv.html>`_ page.

Below example shows you how to create a virtual environment:

.. code-block:: bash
    
    python3 -m venv ~/.virtualenvs/<env_name>

Then activate it by running:

.. code-block:: bash
    
    source ~/.virtualenvs/<env_name>/bin/activate

**Upgrading your ``pip`` will save you a lot of time and troubleshooting (due to changes in the pip resolver in version 20 and 21).** you can do so by running:

.. code-block:: bash
    
    pip install --upgrade pip


Benefit from linting and code navigation by setting up a project
##################################################################

At the time of this writing, linting and code navigation in IDEs work only if you have a project, so even if you only work on a single module, it is best to have a project.

There are two scenarios:

1. There is already an existing project that you can ``git clone``.
2. Make a new project.

Steps to create a project are mentioned `here <https://docs.inmanta.com/community/latest/model_developers/configurationmodel.html>`_ for further reading.

``cookiecutter`` can be used to create projects in an easier and convenient fashion. It could be utilized like:

.. code-block:: bash

    pip install cookiecutter

    cookiecutter https://github.com/inmanta/inmanta-project-template.git

Further information about cookiecutter can be found `here <https://github.com/inmanta/inmanta-project-template>`_ and `here <https://docs.inmanta.com/community/latest/model_developers/configurationmodel.html>`_.


* If you are working on an existing project, they come with ``requirements.txt`` or ``requirements.dev.txt`` to install the required modules:

.. code-block:: bash

    pip install -r requirements.txt

    pip install -r requirements.dev.txt

* If you are working on a new project, you need to install some essential packages as follows:

.. code-block:: bash

    pip install inmanta-core

    pip install pytest

    pip install pytest-inmanta


Once you are done with creating a project and installing the required modules, you can ``cd`` into that directory and open vs code by running:

.. code-block:: bash
    
    code .

Upon opening your vs code, and the ``main.cf`` file, you should see modules downloading in ``libs`` directory.


Set project sources
#####################

When starting a new project, the next step is to set the sources of your project so that it knows, where to get its required modules from. Otherwise, you can skip this step and just ``import`` your desired modules.

If you only use opensource modules as provided by Inmanta, you can skip this step. 

1. Find the module you want to work on
2. Copy the SSH URL of the repo
3. In your VS code, open the ``project.yml`` file and under ``repo:``, add the copied line there but keep in mind to replace the name of a specific module with a place holder, like below example:

.. code-block:: yaml
    
    repo:
        - git@code.inmanta.com:example/my_module.git

Becomes:

.. code-block:: yaml
    
    repo:
        - git@code.inmanta.com:example/{}.git

Now, in your ``main.cf`` file, if you import a module like, ``import my_module`` and save the file, you can get code completion.

**Please note, code completion and navigation work on modules that are imported in the ``main.cf`` file**.


Module developers guide
#########################

While you need to work on modules, it is recommended to check the ``readme.md`` files to see the instructions on how to install and use them. There is also a guide `here <https://docs.inmanta.com/community/latest/model_developers/modules.html>`_ that helps you get up and running.

It is also recommended to set the ``INMANTA_TEST_ENV`` environment variable to speed up your tests and avoid creating virtual environments at each test run. It can be set to something like:

.. code-block:: bash
    
    mkdir /tmp/env
    source INMANTA_TEST_ENV=/tmp/env

There are multiple ways to set environment variables:

1. creating a file named ``.env_vars`` in current module directory.
2. Bash script.
3. Manually ``export $(cat .env_vars | xargs)``.
