.. _moddev-module:

Understanding Modules
========================
In inmanta all orchestration model code and related files, templates, plugins and resource handlers
are packaged in a module.

Module layout
-------------
Inmanta expects that each module is a git repository with a specific layout:

* The name of the module is determined by the top-level directory. Within this module directory, a
  ``module.yml`` file has to be specified.
* The only mandatory subdirectory is the ``model`` directory containing a file called ``_init.cf``.
  What is defined in the ``_init.cf`` file is available in the namespace linked with the name of the
  module. Other files in the model directory create subnamespaces.
* The ``plugins`` directory contains Python files that are loaded by the platform and can extend it
  using the Inmanta API.  This python code can provide plugins or resource handlers.

The template, file and source plugins from the std module expect the following directories as well:

* The ``files`` directory contains files that are deployed verbatim to managed machines.
* The ``templates`` directory contains templates that use parameters from the orchestration model to generate configuration files.

A complete module might contain the following files:

.. code-block:: sh

    module
    |
    |__ module.yml
    |
    |__ files
    |    |__ file1.txt
    |
    |__ model
    |    |__ _init.cf
    |    |__ services.cf
    |
    |__ plugins
    |    |__ functions.py
    |
    |__ templates
         |__ conf_file.conf.tmpl


To quickly initialize a module use cookiecutter:

.. code-block:: sh

   pip install cookiecutter
   cookiecutter gh:inmanta/inmanta-module-template


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

Module dependencies are indicated by importing a module in a model file. However, these imports do not
have a specific version identifier. The version of a module import can be constrained in the
module.yml file. The *requires* key expects a list of version specs. These version specs use `PEP440
syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.

To specify specific version are required, constraints can be added to the requires list::

    license: Apache 2.0
    name: ip
    source: git@github.com:inmanta/ip
    version: 0.1.15
    requires:
        - net ~= 0.2.4
        - std >1.0 <2.5

A module can also indicate a minimal compiler version with the ``compiler_version`` key.

``source`` indicates the authoritative repository where the module is maintained.


Extending Inmanta
-----------------
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

Only the compiler and agents load code included in modules (See :doc:`/architecture`). A module can
include a requirements.txt file with all external dependencies. Both the compiler and the agent will
install this dependencies with ``pip install`` in an virtual environment dedicated to the compiler
or agent. By default this is in `.env` of the project for the compiler and in
`/var/lib/inmanta/agent/env` for the agent.

Inmanta uses a special format of requirements that was defined in python PEP440 but never fully
implemented in all python tools (setuptools and pip). Inmanta rewrites this to the syntax pip
requires. This format allows module developers to specify a python dependency in a repo on a
dedicated branch. And it allows inmanta to resolve the requirements of all module to a
single set of requirements, because the name of module is unambiguously defined in the requirement.
The format for requires in requirements.txt is the folllowing:

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
------------------------------
To set up the development environment for a project, activate your development Python environment and
install the project with ``inmanta project install``. To set up the environment for a single module,
run ``inmanta module install`` instead.

The following subsections explain any additional steps you need to take if you want to make changes
to one of the dependent modules as well.

v1 modules
^^^^^^^^^^
Any modules you find in the project's ``modulepath`` after starting from a clean project and setting
up the development environment are v1 modules. You can make changes to these modules and they will
be reflected in the next compile. No additional steps are required.

v2 modules
^^^^^^^^^^
All other modules are v2 and have been installed by ``inmanta project install`` into the active Python
environment. If you want to be able to make changes to one of these modules, the easiest way is to
check out the module repo separately and run ``inmanta module install`` on it, overwriting the published
package that was installed previously. This will install the module in editable form: any changes you make
to the checked out files will be picked up by the compiler. You can also do this prior to installing the
project, in which case the pre-installed module will remain installed in editable form when you install
the project, provided it matches the version constraints. Since these modules are essentially
Python packages, you can double check the desired modules are installed in editable mode by checking
the output of ``pip list --editable``.


Working on the dev environment
------------------------------
After setting up, you should be left with a dev environment where all required v2 modules have been
installed (either in editable or in packaged form). If you're working on a project, all required v1
modules should be checked out in the ``modulepath`` directory.

When you run a compile from the active Python environment context, the compiler will find both the
v1 and v2 modules and use them for both their model and their plugins.

Similarly, when you run a module's unit tests, the installed v2 modules will automatically be used
by the compiler. As for v1 modules, by default, the ``pytest-inmanta`` extension makes sure the
compile itself runs against an isolated project, downloading any v1 module dependencies at
compile-time. If you want to compile against local versions of v1 modules, have a look at the
``--use-module-in-place`` option in the ``pytest-inmanta`` documentation.


Distributing modules
====================
This section is about v2 modules. V1 modules only require a version tag to be recognized as a
released version. While a version tag is still good practice for v2 modules, it isn't sufficient
to consider it released.

You can package a v2 module with ``inmanta module build`` which will create an sdist and a bdist
of the Python package. You can then publish this to the Python package repository of your choice,
for example the public PyPi repository. For an inmanta project, follow the same procedure but
substitute ``module`` with ``project``.

The orchestrator server generally (see
:ref:`Advanced concepts<modules-distribution-advanced-concepts`) installs both project and modules
from the configured Python package repository, respecting the environment's version constraints on
the project package, the project's constraints on its modules and all inter-module constraints. The
server is then responsible for supplying the agents with the appropriate ``inmanta_plugins``
packages.

.. _modules-distribution-advanced-concepts

Advanced concepts
-----------------

Freezing a project
^^^^^^^^^^^^^^^^^^
Prior to releasing a new stable version of an inmanta project, you might wish to freeze its module
dependencies. This will ensure that the orchestrator server will always work with the exact
versions specified. You can achieve this with
``inmanta project freeze --recursive --operator "=="``. This command will freeze all module
dependencies to their exact version as they currently exist in the Python environment. The recursive
option makes sure all module dependencies are frozen, not just the direct dependencies. In other
words, if the project depends on module ``a`` which in turn depends on module ``b``, both modules
will be pinned to their current version in ``pyproject.toml``.

Manual export
^^^^^^^^^^^^^
The `inmanta export` command exports a project and all its modules to the orchestrator server.
When this method is used, the orchestrator does not install any modules from the Python package
repository but instead contains all code (both model and plugins) as present in the local Python
environment.
