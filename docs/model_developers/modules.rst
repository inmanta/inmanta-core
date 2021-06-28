.. _moddev-module:

Understanding Modules
========================
In Inmanta all orchestration model code and related files, templates, plugins and resource handlers are packaged in a module.
Modules can be defined in two different formats, the V1 format and the V2 format. The biggest difference between both formats is
that V2 modules can be packaged into a Python package, while V1 modules cannot. New modules should use the V2 module
format. The following sections describe the directory layout of the V1 and the V2 module formats and their metadata files.

V2 module format
################

.. warning::

   The V2 module format is currently under development.

A complete V2 module might contain the following files:

.. code-block:: sh

    module
    |
    |-- setup.cfg
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
  information, such as the name of the module. More details about the ``setup.cfg`` file are defined in the next section.
* The ``pyproject.toml`` file defines the build system that should be used to package the module and install the module into a
  venv from source.
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
The ``setup.cfg`` file defines metadata about the module. The code snippet provides an example about what this ``setup.cfg``
file looks like:

.. code-block:: ini

    [metadata]
    name = inmanta-module-mod1
    version = 1.2.3
    license = Apache 2.0

    [options]
    install_requires =
      net ~=0.2.4
      std >1.0,<2.5

      cookiecutter~=1.7.0
      cryptography>1.0,<3.5


* The ``metadata`` section defines the following fields:
  ** ``name``: The name of the resulting Python package when this module is packaged. This name should follow the
     naming schema: ``inmanta-module-<module-name>``.
  ** ``version``: The version of the module. Modules must use semantic versioning.
  ** ``license``: The license under which the module is distributed.
* Dependencies to other Inmanta modules and dependencies to external Python libraries can be defined using the
  ``install_requires`` config option in the ``options`` section of the ``setup.cfg`` file. These version specs use `PEP440
  syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.

A full list of all available options can be found in :ref:`here<modules_v2_pyproject_toml>`.

The pyproject.toml file
-----------------------

The ``pyproject.toml`` file defines the build system that has to be used to build a python package and perform editable
installs. This file should always have the following content:

.. code-block:: toml

    [build-system]
    requires = ["setuptools", "wheel"]
    build-backend = "setuptools.build_meta"


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
The format for requires in requirements.txt is the following:

 * Either, the name of the module and an optional constraint
 * Or a repository location such as  git+https://github.com/project/python-foo The correct syntax
   to use is then: eggname@git+https://../repository#branch with branch being optional.
