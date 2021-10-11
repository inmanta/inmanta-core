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

**Upgrading your ``pip`` will save you a lot of time and troubleshooting.**


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

To create a new project:

.. code-block:: bash

    pip install cookiecutter

    cookiecutter https://github.com/inmanta/inmanta-project-template.git


For more details go :ref:`here <project-creation-guide>`.

You need to install some essential packages as follows:

.. code-block:: bash

    pip install inmanta-core pytest-inmanta


Once you are done with creating a project, you can ``cd`` into that directory and open VS Code by running:

.. code-block:: bash

    cd <project_name>

    code .

Upon opening your vs code, and the ``main.cf`` file, you should see modules downloading in ``libs`` directory.

.. _dgs-existing-project:

Working on an Existing Project
==============================

When working on an existing project, you need to ``clone`` them first:

.. code-block:: bash

    git clone <project_url>


They also come with ``requirements.txt`` or ``requirements.dev.txt`` to install the required modules:

.. code-block:: bash

    pip install -r requirements.txt

    pip install -r requirements.dev.txt


Set project sources
#####################

When starting a new project, the next step is to set the sources of your project so that it knows where to get its required modules from.

If you only use opensource modules as provided by Inmanta, you can skip below step.

1. Find the module you want to work on
2. Copy the SSH URL of the repo
3. In your VS code, open the ``project.yml`` file and under ``repo:``, add the copied line there but keep in mind to replace the name of a specific module with a place holder, like below example:

.. code-block:: bash

    code project.yml

.. code-block:: yaml

    repo:
        - git@code.inmanta.com:example/my_module.git

Becomes:

.. code-block:: yaml

    repo:
        - git@code.inmanta.com:example/{}.git

* Now, in your ``main.cf`` file, if you import a module like, ``import <my_module>`` and save the file, you can get code completion. If you are working on an existing project with a populated ``main.cf`` file, code completion will work as expected.

**Please note, code completion and navigation work on modules that are imported in the** ``main.cf`` **file**.


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


There are also guides :ref:`here <moddev-module>` and `here <https://github.com/inmanta/inmanta-module-template>`_ that help you get up and running.

.. _dgs-existing-module:

Working on an Existing Module
=============================

Modules that you want to work on, have to be imported in the ``main.cf`` file that is located in your main project directory. For instance:

.. code-block:: inmanta

    import vyos

To download the imported modules in your ``main.cf`` file run:

.. code-block:: bash

    inmanta compile


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
