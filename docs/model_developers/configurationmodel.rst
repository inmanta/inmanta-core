.. _project-creation-guide:

Project creation guide
============================

This guide explains how to create a project.  
For detailed documentation see: :ref:`project_yml`.

Create a new source project
---------------------------
The Inmanta compiler expects a *project* with basic configuration. This project is a directory that
contains the source code of the configuration model. This project also matches with a
:term:`project` defined on the server, from which multiple :term:`environments<environment>` can be
deployed.

.. code-block:: sh
  :linenos:

  pip install cookiecutter
  cookiecutter gh:inmanta/inmanta-project-template

.. note::	

    The cookiecutter template also sets up git for the new project. 	
    This is a best practice to version control your infrastructure code.	

Inside the project the compiler expects a ``project.yml`` file that defines metadata about the project,
the location to store modules, repositories where to find modules and possibly specific versions of
modules. project.yml defines the following settings:

    * ``name`` The name of the project.
    * ``description`` An optional description of the project
    * ``author``  The author of the module
    * ``author_email`` The contact email address of author
    * ``license`` License the module is released under
    * ``copyright`` Copyright holder name and date.
    * ``install_mode`` This key determines what version of a module should be selected when a module
      is downloaded. The available values are:

        * release (default): Only use a released version, that is compatible with the current
          compiler and the version constraints defined in the ``requires`` list.
        * prerelease: Similar to release, but also prerelease versions are allowed.
        * master: Use the master branch.

    * ``repo`` This key requires a list (a yaml list) of repositories where Inmanta can find
      modules. Inmanta creates the git repo url by formatting {} or {0} with the name of the repo. If no formatter is present it
      appends the name of the module. Inmanta tries to clone a module in the order in which it is defined in this value.
    

For more information see :ref:`project_yml`.

An example ``project.yml`` could be:

.. code-block:: yaml
  :linenos:

  name: test
  description: a test project
  author: Inmanta
  author_email: code@inmanta.com
  license: ASL 2.0
  copyright: 2020 Inmanta
  modulepath: libs
  downloadpath: libs
  repo:
      - https://github.com/inmanta/
  install_mode: release
  requires:


The main file
-------------
The ``main.cf`` is the place where the compiler starts executing code first.
For example, the ``main.cf`` below calls the print plugin from the std module.

.. code-block:: inmanta
    :linenos:

    std::print("hello world")

.. note::
    The std module is the only module that does not have to be imported explicitly.

This example can be executed with ``inmanta compile``

This prints out "hello world" on stdout. The first execution takes longer because Inmanta needs to
fetch (clone) the std module from github. Subsequently compiles will use the std module downloaded
to the libs directory.
