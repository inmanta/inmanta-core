Create a configuration model
============================

This guide explains how to create a basic configuration model to manage an infrastructure: the
Inmanta *hello world*.  Each configuration model is completely defined in source code:
:term:`infrastructure-as-code`.

Create a new source project
---------------------------
The Inmanta compiler expects a *project* with basic configuration. This project is a directory that
contains the source code of the configuration model. This project also matches with a
:term:`project` defined on the server, from which multiple :term:`environments<environment>` can be
deployed.

.. note::

    Inmanta requires that a project is a git repository. This is not strictly required when using
    the embedded or push to server model (see :doc:`/architecture`). However in the autonomous
    server model, this is the only method to get the configuration code on the server. Additionally,
    it is also a good practive to version control your infrastructure code.

    Typically branches in this git repository are used to define multiple environments (if the
    differ in code)

.. code-block:: sh
    :linenos:

    mkdir hello-world
    cd hello-world
    git init

Inside the project the compiler expects a project.yml file that defines metadata about the project,
the location to store modules, repositories where to find modules and possibly specific versions of
modules. project.yml defines the following settings:

    * ``name`` An optional name of the project.
    * ``description`` An optional description of the project
    * ``modulepath`` This value is a list of paths where Inmanta should search for modules. Paths
      are separated with ``:``
    * ``downloadpath`` This value determines the path where Inmanta should download modules from
      repositories. This path is not automatically included in in modulepath!
    * ``install_mode`` This key determines what version of a module should be selected when a module
      is downloaded. This is used when the module version is not "pinned" in the ``requires`` list.
      The available values are:

        * release (default): Only use a released version, that is compatible with the current
          compiler. A version is released when there is a tag on a commit. This tag should be a
          valid version identifier (PEP440) and should not be a prerelease version. Inmanta selects
          the latest available version (version sort based on PEP440).
        * prerelease: Similar to release, but also prerelease versions are allowed.
        * master: Use the master branch.

    * ``repo`` This key requires a list (a yaml list) of repositories where Inmanta can find
      modules. The git url of a module is created by appending the name of the module to the repo
      in this list. Inmanta tries to clone a module in the order in which it is defined in this
      value.
    * ``requires`` Model files import other modules. These imports do not determine a version, this
      is based on the install_model setting. Modules and projects can constrain a version in the
      requires setting. Similar to the module, version constraints are defined using `PEP440 syntax
      <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.


An example project.yml could be:

.. code-block:: yaml
    :linenos:

    name: Hello world
    description: An Inmanta hello world like project!
    modulepath: libs
    downloadpath: libs
    repo:
        - https://github.com/inmanta/


Initial model
-------------
Most infrastructure code is contained in modules, but the compiler needs an *entrypoint*. This
entrypoint is the main.cf file in the toplevel directory of the project.

The main.cf below calls the print plugin from the std module.


.. note::
    The std module is the only module that does not have to be imported explicitly.

.. code-block:: none
    :linenos:

    std::print("hello world")


This example can be executed with ``inmanta compile``

This prints out "hello world" on stdout. The first execution takes longer because Inmanta needs to
fetch (clone) the std module from github. Subsequently compiles will use the std module downloaded
to the libs directory.


Deploy a file
-------------
With the deploy command, Inmanta can deploy a file to a machine with an embedded server and agent.

The main.cf below creates a file:

.. code-block:: none
    :linenos:

    host = std::Host(name="localhost", os=std::linux)
    std::File(host=host, path="/tmp/test", owner="user", group="group", mode=600, content="abcde")

.. note::

    Replace *user* and *group* in the main.cf above. The user and group should exist. If this
    command is not executed as root, make sure that user and group have the value of the current
    user.

Deploy the configuration model above with ``inmanta deploy``
