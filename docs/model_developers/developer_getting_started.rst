********************************
Developer Getting Started Guide
********************************

This guide explains how to set up the recommended developer setup on a Linux machine.
Other development setups are possible, but this one provides a good starting point.

* Install VS Code and Inmanta extension.
* Setting up Python virtual environments.
* Setting up a project.
* Set project sources
* Setting up a module
* Run tests
* Module developers guide
* Required environment variables

**The examples below are using** ``pip`` **your system might require you to use** ``pip3``.


Install VS Code and Inmanta extension
#######################################

The developer setup is based on VSCode with the Inmanta extension.

In order to install VS Code, you can refer to `this <https://code.visualstudio.com/learn/get-started/basics>`_ page.

Inmanta's extension in VS Code marketplace can be found `here <https://marketplace.visualstudio.com/items?itemName=inmanta.inmanta>`_.

Further information about Inmanta VS Code extension is available on `this <https://github.com/inmanta/vscode-inmanta>`_ page.


Setting up Python virtual environments
########################################

For every project that you work on, we recommend using a new virtual environment.
If you are unfamiliar with venv's, you can check out `this <https://docs.python.org/3/tutorial/venv.html>`_ page.

To create a virtual environment:

.. code-block:: bash

    python3 -m venv ~/.virtualenvs/my_project

Then activate it by running:

.. code-block:: bash

    source ~/.virtualenvs/my_project/bin/activate

**Upgrading your** ``pip`` **will save you a lot of time and troubleshooting.**

You can do so by running:

.. code-block:: bash

    pip install --upgrade pip wheel


Setting up a project
##################################################################

At the time of this writing, linting and code navigation in IDEs work only if you have a project, so even if you only work on a single module, it is best to have a project.

There are two scenarios:

1. :ref:`Working on a New Project <dgs-new-project>`.
2. :ref:`Working on an Existing Project <dgs-existing-project>`.

.. _dgs-new-project:

Working on a New Project
========================

To create a new project you need to install some essential packages as follows:

.. code-block:: bash

    pip install inmanta-core pytest-inmanta

Create a new project using the inmanta-project-template:

.. code-block:: bash

    pip install cookiecutter

    cookiecutter https://github.com/inmanta/inmanta-project-template.git

Navigate into the project and install the module dependencies using the inmanta CLI tool:

.. code-block:: bash

    cd <project_name>

    inmanta project install

V1 modules will be downloaded to the ``downloadpath`` configured in the ``project.yml`` file. V2 modules are installed in the
active Python environment. For more details go :ref:`here <project-creation-guide>`. Once you are done with creating a project,
you can open VS Code by running:

.. code-block:: bash

    code .


.. _dgs-existing-project:

Working on an Existing Project
==============================

When working on an existing project, you need to ``clone`` them first:

.. code-block:: bash

    git clone <project_url>

They also come with a ``requirements.dev.txt`` to install the development dependencies:

.. code-block:: bash

    cd <project_name>

    pip install -r requirements.dev.txt

The module dependencies are installed using the inmanta CLI tool:

.. code-block:: bash

    inmanta project install


Set project sources
#####################

When starting a new project, the next step is to set the sources of your project so that it knows where to get its required modules from.

V1 module source
================

If you only use opensource v1 modules as provided by Inmanta, you can skip below step.

1. Find the module you want to work on
2. Copy the SSH URL of the repo
3. In your VS code, open the ``project.yml`` file and under ``repo:``, add the copied line there but keep in mind to replace the name of a specific module with a place holder, like below example:

.. code-block:: bash

    code project.yml

.. code-block:: yaml

    repo:
        - url: git@code.inmanta.com:example/my_module.git
          type: git

Becomes:

.. code-block:: yaml

    repo:
        - url: git@code.inmanta.com:example/{}.git
          type: git

* Now, in your ``main.cf`` file, if you import a module like, ``import <my_module>`` and save the file, you can get code completion. If you are working on an existing project with a populated ``main.cf`` file, code completion will work as expected.

**Please note, code completion and navigation work on modules that are imported in the** ``main.cf`` **file**.

V2 module source
================

Add the pip index where your modules are hosted to ``project.yml`` as a repo of type ``package``.
For example, for modules hosted on PyPi:

.. code-block:: yaml

    repo:
        - url: https://pypi.org/simple
          type: package


Setting up a module
#########################

Like projects, there are also two scenarios:

1. :ref:`Working on a New Module <dgs-new-module>`.
2. :ref:`Working on an Existing Module <dgs-existing-module>`.

.. _dgs-new-module:

Working on a New Module
=======================

Same as :ref:`Working on a New Project` part, modules can also be created like:

.. code-block:: bash

    pip install cookiecutter

    cookiecutter https://github.com/inmanta/inmanta-module-template.git

for a v1 module. For a v2 module, add ``--checkout v2`` to the cookiecutter command.


There are also guides :ref:`here <moddev-module>` and `here <https://github.com/inmanta/inmanta-module-template>`_ that help you get up and running.

.. _dgs-existing-module:

Working on an Existing Module
=============================

Modules that you want to work on, have to be added to your Inmanta project using the following command. This command also installs the module into the project.

.. code-block:: bash

    inmanta module add --v1 <module-name>

for a v1 module or

.. code-block:: bash

    inmanta module add --v2 <module-name>

for a v2 module. The latter will implicitly trust any Python package named ``inmanta-module-<module-name>`` in the project's configured module source.

When starting to work on an existing module, it is recommended to check the ``readme.md`` file that comes with the module to see the instructions on how to install and use them.

Running Test
##############################

To run test on modules, it is *recommended* to set the ``INMANTA_TEST_ENV`` environment variable to speed up your tests and avoid creating virtual environments at each test run.

1. Create a temp directory and export the path:

.. code-block:: bash

    export INMANTA_TEST_ENV=$(mktemp -d)


2. Install required dependencies

.. code-block:: bash

    pip install -r requirements.txt -r requirements.dev.txt

3. Run the test

.. code-block:: bash

    python -m pytest tests
