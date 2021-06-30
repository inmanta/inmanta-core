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

