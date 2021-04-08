********************************
Developer Getting Started Guide
********************************

This page describes how to setup your development environment to:

* Setup Inmanta pip artifacts
* Verify that you already have GitLab SSH keys.
* Install VS Code and Inmanta extension.
* Setting up Python virtual environments.
* Benefit from linting and code navigation by setting up a project.
* Set project sources
* Module developers guide


Setup Inmanta pip artifacts
#############################

In order to use Inmanta's internal pip artifacts:

.. code-block:: bash

    mkdir   ~/.config/pip

    nano ~/.config/pip/pip.conf

And below text into your ``pip.conf`` file:

::
    [global]
    index_url=https://artifacts.internal.inmanta.com/inmanta/dev


Verify that you already setup GitLab SSH keys
###############################################

The steps to add SSH keys have already been mentioned in ``Inmanta Getting Started Guide`` which was emailed to you.
You can click `here <https://internal.inmanta.com/topics/starting.html>`_ to read it again.

In order to verify that it is working correctly, run below command:

.. code-block:: bash
    
    ssh git@git.inmanta.com


You should see your name in the response.


Install VS Code and Inmanta extension
#######################################

This step does not need any additional information but if you need some help, you can always ask a colleague.


Setting up Python virtual environments
########################################

Python virtual environments have to be created using ``venv`` by running:

.. code-block:: bash
    
    python3 -m venv ~/.virtualenvs/<env_name>

Then activated by running:

.. code-block:: bash
    
    source ~/.virtualenvs/<env_name>/bin/activate

**Upgrading your ``pip`` will save you a lot of time and troubleshooting.** you can do so by running:

.. code-block:: bash
    
    pip install --upgrade pip

Usually the projects that you will work on, come with ``requirements.txt`` or ``requirements.dev.txt`` to install the required modules, if not, it is a good idea to ``pip install``:

1. inmanta-core
2. pytest
3. pytest-inmanta
4. pytest-inmanta-yang


Benefit from linting and code navigation by setting up a project
##################################################################

At the time of this writing, linting and code navigation in IDEs work only if you have a project, so if you want to work on a single module, you still need to have a project.

There are two things that can be done:

1. Either there is already a project and you ``git clone`` your module there.
2. Make a project.

Steps to create a project are mentioned `here <https://docs.inmanta.com/community/latest/model_developers/configurationmodel.html>`_ for further reading.

Once you are done with creating a project, you can ``cd`` into that directory and open vs code by running:

.. code-block:: bash
    
    code .

Upon opening your vs code, and the ``main.cf`` file, you should see modules downloading in ``libs`` directory.


Set project sources
#####################

The next step is to set the sources of your project so that it knows, where to get its required modules from.

1. Find the module you want to work on
2. Copy the SSH URL by clicking on the ``CLONE`` button.
3. In your vs code, open the ``project.yml`` file and under ``repo:``, add the copied line there but keep in mind to replace the name of a specific module with a place holder, like below example:

.. code-block:: yaml
    
    repo:
        - git@code.inmanta.com:example/my_module.git

To:

.. code-block:: yaml
    
    repo:
        - git@code.inmanta.com:example/{}.git

Now, in your ``main.cf`` file, if you import a module like, ``import nokia_service_vprn`` and save the file, you can get code completion.

**Please note, code completion and navigation work on modules that are imported in the ``main.cf`` file**


Module developers guide
#########################

While you need to work on modules, it is recommended to check the ``readme.md`` files to see the instructions on how to install and use them.

There is also a guide `here <https://docs.inmanta.com/community/latest/model_developers/modules.html>`_ that helps you get up and running.

It is also recommended to set the ``INMANTA_TEST_ENV`` environment variable to speed up your tests and avoid creating virtual environments at each test run. It can be set to something like:

.. code-block:: bash
    
    mkdir /tmp/env
    source INMANTA_TEST_ENV=/tmp/env

There are multiple ways to set environment variables:

1. creating a file named ``.env_vars`` in current module directory.
2. Bash script.
3. Manually ``export $(cat .env_vars | xargs)``.
