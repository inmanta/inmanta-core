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
An inmanta project is required to make use of a module. In most cases you'll want to develop a
project and some of its modules simultaneously, since modules are most often developed/extended
specifically to offer functionality to a project under development. This section will explain how
to make changes to both a project and its modules so that they are all taken into account by the
compiler.

Setting up the dev environment
------------------------------
v1 modules
^^^^^^^^^^
A v1 module is a module that is not packaged and published to a pip index but is solely distributed
via git. V1 modules are installed on the fly by the compiler and can be found in the `libs`
directory. Any changes you make to the module source in the `libs` dir will be reflected in the next
compile. To set up your development environment simply clone the project repo and run a compile.

v2 modules
^^^^^^^^^^
A v2 module in development form has mostly the same structure as a v1 module. The main difference is
that it is meant to be published as a Python package. The project then lists all required v2 modules
as dependencies in its `pyproject.toml`. The compiler does not install v2 modules on the fly. In
line with how Python depdencies work in general they are expected to be installed in advance.
As a result they will not be placed in the `libs` directory.

To set up your development environment, first clone all modules you wish to develop against and
install them in editable mode with `poetry install`. Then clone the project repo and install its
depdencies with `poetry install`. This will fetch all its other modules from the Python package
index and install them in the active Python environment. Any modules you pre-installed should
remain as is, provided they meet the project's version constraints. You can double-check the
desired modules are installed in editable mode by checking the output of `pip list --editable`.
If you want to add another module to the set under development, you can always run `poetry install`
on it in a later stage, overwriting the published package that was installed previously.

Working on the dev environment
------------------------------
After setting up, you should be left with a dev environment where all required v2 modules have been
installed (either in editable or in packaged form) and all required v1 modules are present in the
`libs` directory. When you run a compile from that Python environment context, the compiler will
find both the v1 and v2 modules and use them for both their model and their plugins.

TODO: talk about unit tests => investigate how pytest-inmanta works now -> loads current module into libs, lets compiler take care of the rest (for single module tests)

Stand-alone module development
------------------------------
TODO: work on module in stand-alone manner, without a project. Make changes and use unit tests to
test behavior. Focus of this subsection is on how the tests find the required files.


Distributing modules
====================
TODO: package + publish + freeze project + checkout on the orchestrator
