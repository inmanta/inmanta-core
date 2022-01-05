.. _moddev-module:

Understanding Modules
========================
In Inmanta all orchestration model code and related files, templates, plugins and resource handlers are packaged in a module.
Modules can be defined in two different formats, the V1 format and the V2 format. The biggest difference between both formats is
that all Python tools can run on V2 modules, because V2 modules are essentially Python packages. New modules should use the V2
module format. The following sections describe the directory layout of the V1 and the V2 module formats and their metadata
files.


.. _moddev-module-v2:

V2 module format
################


A complete V2 module might contain the following files:

.. code-block:: sh

    module
    |
    |__ MANIFEST.in
    |__ setup.cfg
    |__ pyproject.toml
    |
    |__ model
    |    |__ _init.cf
    |    |__ services.cf
    |
    |__ inmanta_plugins/<module-name>/
    |    |__ __init__.py
    |    |__ functions.py
    |
    |__ files
    |    |__ file1.txt
    |
    |__ templates
         |__ conf_file.conf.tmpl


* The root of the module directory contains a ``setup.cfg`` file. This is the metadata file of the module. It contains
  information, such as the version of the module. More details about the ``setup.cfg`` file are defined in the next section.
* The ``pyproject.toml`` file defines the build system that should be used to package the module and install the module into a
  virtual environment from source.
* The only mandatory subdirectory is the ``model`` directory containing a file called ``_init.cf``.
  What is defined in the ``_init.cf`` file is available in the namespace linked with the name of the
  module. Other files in the model directory create subnamespaces.
* The ``inmanta_plugins/<module-name>/`` directory contains Python files that are loaded by the platform and can extend it
  using the Inmanta API.  This python code can provide plugins or resource handlers.

The template, file and source plugins from the std module expect the following directories as well:

* The ``files`` directory contains files that are deployed verbatim to managed machines.
* The ``templates`` directory contains templates that use parameters from the orchestration model to generate configuration files.


The setup.cfg metadata file
---------------------------
The ``setup.cfg`` file defines metadata about the module. The following code snippet provides an example about what this
``setup.cfg`` file looks like:

.. code-block:: ini

    [metadata]
    name = inmanta-module-mod1
    version = 1.2.3
    license = Apache 2.0

    [options]
    install_requires =
      inmanta-modules-net ~=0.2.4
      inmanta-modules-std >1.0,<2.5

      cookiecutter~=1.7.0
      cryptography>1.0,<3.5

    zip_safe=False
    include_package_data=True
    packages=find_namespace:


* The ``metadata`` section defines the following fields:

  * ``name``: The name of the resulting Python package when this module is packaged. This name should follow the naming schema: ``inmanta-module-<module-name>``.
  * ``version``: The version of the module. Modules must use semantic versioning.
  * ``license``: The license under which the module is distributed.

* The ``install_requires`` config option in the ``options`` section of the ``setup.cfg`` file defines the dependencies of the
  module on other Inmanta modules and external Python libraries. These version specs use
  `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_. Adding a new module dependency to the module
  should be done using the ``inmanta module add`` command instead of altering the ``setup.cfg`` file by hand.

A full list of all available options can be found in :ref:`here<modules_v2_setup_cfg>`.

The pyproject.toml file
-----------------------

The ``pyproject.toml`` file defines the build system that has to be used to build a python package and perform editable
installs. This file should always have the following content:

.. code-block:: toml

    [build-system]
    requires = ["setuptools", "wheel"]
    build-backend = "setuptools.build_meta"


The MANIFEST.in file
--------------------
This file enables ``setuptools`` to correctly build the package. It is documented `here <https://packaging.python.org/guides/using-manifest-in/>`_.
An example that includes the model, files, templates and metadata file in the package looks like this:

.. code-block::

    include inmanta_plugins/mod1/setup.cfg
    recursive-include inmanta_plugins/mod1/model *.cf
    graft inmanta_plugins/mod1/files
    graft inmanta_plugins/mod1/templates

You might notice that the model, files and templates directories, nor the metadata file reside in the ``inmanta_plugins``
directory. The inmanta build tool takes care of this to ensure the included files are included in the package
installation directory.


.. _moddev-module-v1:

V1 module format
################

A complete module might contain the following files:

.. code-block:: sh

    module
    |
    |__ module.yml
    |
    |__ model
    |    |__ _init.cf
    |    |__ services.cf
    |
    |__ plugins
    |    |__ functions.py
    |
    |__ files
    |    |__ file1.txt
    |
    |__ templates
    |    |__ conf_file.conf.tmpl
    |
    |__ requirements.txt

The directory layout of the V1 module is similar to that of a V2 module. The following difference exist:

* The metadata file of the module is called ``module.yml`` instead of ``setup.cfg``. The structure of the ``module.yml``
  file also differs from the structure of the ``module.yml`` file. More information about this ``module.yml`` file is available
  in the next section.
* The files contained in the ``inmanta_plugins/<module-name>/`` directory in the V2 format, are present in the ``plugins``
  directory in the V1 format.
* The ``requirements.txt`` file defines the dependencies of this module to other V2 modules and the dependencies to external
  libraries used by the code in the ``plugins`` directory. This file is not present in the V2 module format, since V2 modules
  defined their dependencies in the ``setup.cfg`` file.
* The ``pyproject.toml`` file doesn't exist in a V1 module, because V1 modules cannot be packaged into a Python package.

Module metadata
---------------
The module.yml file provides metadata about the module. This file is a yaml file with the following
three keys mandatory:

* *name*: The name of the module. This name should also match the name of the module directory.
* *license*: The license under which the module is distributed.
* *version*: The version of this module. For a new module a start version could be 0.1dev0 These
  versions are parsed using the same version parser as python setuptools.

For example the following module.yml from the :doc:`../quickstart`

.. code-block:: yaml

    name: lamp
    license: Apache 2.0
    version: 0.1

The *requires* key can be used to define the dependencies of this module on other Inmanta modules. Each entry in the list
should contain the name of an Inmanta module, optionally associated with a version constraint. These version specs use `PEP440
syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_. Adding a new entry to the requires list should be done
using the ``inmanta module add <module-name>`` command.

An example of a ``module.yml`` file that defines requires:

.. code-block:: yaml

    license: Apache 2.0
    name: ip
    source: git@github.com:inmanta/ip
    version: 0.1.15
    requires:
        - net ~= 0.2.4
        - std >1.0 <2.5

``source`` indicates the authoritative repository where the module is maintained.

A full list of all available options can be found in :ref:`here<module_yml>`.

Convert a module from V1 to V2 format
#####################################

To convert a V1 module to the V2 format, execute the following command in the module folder

.. code-block:: bash

   inmanta module v1tov2

Inmanta module template
#######################

To quickly initialize a module use the :ref:`inmanta module template<module-creation-guide>`.

Extending Inmanta
#################
Inmanta offers module developers an orchestration platform with many extension possibilities. When
modelling with existing modules is not sufficient, a module developer can use the Python SDK of
Inmanta to extend the platform. Python code that extends Inmanta is stored in the plugins directory
of a module. All python modules in the plugins subdirectory will be loaded by the compiler when at
least a ``__init__.py`` file exists, exactly like any other python package.

The Inmanta Python SDK offers several extension mechanism:

* Plugins
* Resources
* Resource handlers
* Dependency managers

Only the compiler and agents load code included in modules (See :doc:`/architecture`). A module can include external
dependencies. Both the compiler and the agent will install this dependencies with ``pip install`` in an virtual
environment dedicated to the compiler or agent. By default this is in `.env` of the project for the compiler and in
`/var/lib/inmanta/agent/env` for the agent.

Inmanta uses a special format of requirements that was defined in python PEP440 but never fully
implemented in all python tools (setuptools and pip). Inmanta rewrites this to the syntax pip
requires. This format allows module developers to specify a python dependency in a repo on a
dedicated branch. And it allows inmanta to resolve the requirements of all module to a
single set of requirements, because the name of module is unambiguously defined in the requirement.
The format for requires in requirements.txt is the following:

 * Either, the name of the module and an optional constraint
 * Or a repository location such as  git+https://github.com/project/python-foo The correct syntax
   to use is then: eggname@git+https://../repository#branch with branch being optional.


Working on modules
==================
Since modules often have dependencies on other modules, it is common to develop against multiple
modules (or a project and one or more modules) simultaneously. One might for example need to
extend a dependent module to add support for some new feature. Because this use case is so common,
this section will describe how to work on multiple modules simultaneously so that any changes are
visible to the compiler. This procedure is of course applicable for working on a single module as well.

Setting up the dev environment
##############################
To set up the development environment for a project, activate your development Python environment and
install the project with ``inmanta project install``. To set up the environment for a single v2 module,
run ``inmanta module install -e`` instead.

The following subsections explain any additional steps you need to take if you want to make changes
to one of the dependent modules as well.

v1 modules
----------
Any modules you find in the project's ``modulepath`` after starting from a clean project and setting
up the development environment are v1 modules. You can make changes to these modules and they will
be reflected in the next compile. No additional steps are required.

v2 modules
----------
All other modules are v2 and have been installed by ``inmanta project install`` into the active Python
environment. If you want to be able to make changes to one of these modules, the easiest way is to
check out the module repo separately and run ``inmanta module install -e <path>`` on it, overwriting the published
package that was installed previously. This will install the module in editable form: any changes you make
to the checked out files will be picked up by the compiler. You can also do this prior to installing the
project, in which case the pre-installed module will remain installed in editable form when you install
the project, provided it matches the version constraints. Since these modules are essentially
Python packages, you can double check the desired modules are installed in editable mode by checking
the output of ``pip list --editable``.


Working on the dev environment
##############################
After setting up, you should be left with a dev environment where all required v2 modules have been
installed (either in editable or in packaged form). If you're working on a project, all required v1
modules should be checked out in the ``modulepath`` directory.

When you run a compile from the active Python environment context, the compiler will find both the
v1 and v2 modules and use them for both their model and their plugins.

Similarly, when you run a module's unit tests, the installed v2 modules will automatically be used
by the compiler. As for v1 modules, by default, the ``pytest-inmanta`` extension makes sure the
compile itself runs against an isolated project, downloading any v1 module dependencies. If you want to compile against local
versions of v1 modules, have a look at the ``--use-module-in-place`` option in the ``pytest-inmanta`` documentation.


Distributing modules
====================
This section is about v2 modules. V1 modules only require a version tag to be recognized as a
released version. While a version tag is still good practice for v2 modules, it isn't sufficient
to consider it released.

You can package a v2 module with ``inmanta module build`` which will create a Python wheel.
You can then publish this to the Python package repository of your choice,
for example the public PyPi repository.
The module with name <module-name> will be distributed as a Python package with name inmanta-module-<module-name>.

The orchestrator server generally (see
:ref:`Advanced concepts<modules-distribution-advanced-concepts>`) installs modules from the configured Python package
repository, respecting the project's constraints on its modules and all inter-module constraints. The server is then responsible
for supplying the agents with the appropriate ``inmanta_plugins`` packages.


.. _modules-distribution-advanced-concepts:

Advanced concepts
#################

Freezing a project
------------------
Prior to releasing a new stable version of an inmanta project, you might wish to freeze its module
dependencies. This will ensure that the orchestrator server will always work with the exact
versions specified. You can achieve this with
``inmanta project freeze --recursive --operator "=="``. This command will freeze all module
dependencies to their exact version as they currently exist in the Python environment. The recursive
option makes sure all module dependencies are frozen, not just the direct dependencies. In other
words, if the project depends on module ``a`` which in turn depends on module ``b``, both modules
will be pinned to their current version in ``setup.cfg``.

Manual export
-------------
The ``inmanta export`` command exports a project and all its modules' ``inmanta_plugins`` packages
to the orchestrator server. When this method is used, the orchestrator does not install any modules
from the Python package repository but instead contains all Python code as present in the local
Python environment.
