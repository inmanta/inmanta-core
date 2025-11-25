.. _moddev-module:

Understanding Modules
=====================
In Inmanta all orchestration model code and related files, templates, plugins and resource handlers are packaged in a module.
Inmanta modules are essentially Python packages. The following sections describe the module format and their metadata
files.

.. note::

   This page provides information about V2 modules, given that V1 modules are no longer supported.
   Use the procedure in :ref:`this section<convert-v1-to-v2>` to convert an old V1 module to a V2 module.

Module format
################

A complete module might contain the following files:

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

    [options.extras_require]
    feature-x =
      inmanta-modules-mod2

    zip_safe=False
    include_package_data=True
    packages=find_namespace:

    [options.packages.find]
    include = inmanta_plugins*


* The ``metadata`` section defines the following fields:

  * ``name``: The name of the resulting Python package when this module is packaged. This name should follow the naming schema: ``inmanta-module-<module-name>``.
  * ``version``: The version of the module. Modules must use semantic versioning.
  * ``license``: The license under which the module is distributed.
  * ``deprecated``: Optional field. If set to True, this module will print a warning deprecation message when used.

* The ``install_requires`` config option in the ``options`` section of the ``setup.cfg`` file defines the dependencies of the
  module on other Inmanta modules and external Python libraries. These version specs use
  `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_. Adding a new module dependency to the module
  should be done using the ``inmanta module add`` command instead of altering the ``setup.cfg`` file by hand.
  Dependencies with extras can be defined in this section using the ``dependency[extra-a,extra-b]`` syntax.

* The ``options.extras_require`` config option can be used to define optional dependencies, only required by a specific
  feature of the inmanta module.

A full list of all available options can be found in :ref:`here<modules_setup_cfg>`.

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

.. _convert-v1-to-v2:

Convert a module from V1 to V2 format
#####################################

V1 modules are no longer supported by the orchestration platform. To convert a V1 module to the V2 format,
execute the following command in the module folder:

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

Only the compiler and executors load code included in modules (See :doc:`/architecture`). A module can include external
dependencies. Both the compiler and the executors will install these dependencies with ``pip install``, each in a
dedicated virtual environment. By default this is in `.env` of the project for the compiler and in
`/var/lib/inmanta/server/<environment>/executors/venvs/` for the executors.

Inmanta uses a special format of requirements that was defined in python PEP440 but never fully
implemented in all python tools (setuptools and pip). Inmanta rewrites this to the syntax pip
requires. This format allows module developers to specify a python dependency in a repo on a
dedicated branch. And it allows inmanta to resolve the requirements of all module to a
single set of requirements, because the name of module is unambiguously defined in the requirement.
The format for requires in requirements.txt is the following:

 * Either, the name of the module and an optional constraint
 * Or a repository location such as  git+https://github.com/project/python-foo The correct syntax
   to use is then: eggname@git+https://../repository#branch with branch being optional.


Installing modules
==================
Since modules often have dependencies on other modules, it is common to develop against multiple
modules (or a project and one or more modules) simultaneously. One might for example need to
extend a dependent module to add support for some new feature. Because this use case is so common,
this section will describe how to work on multiple modules simultaneously so that any changes are
visible to the compiler. This procedure is of course applicable for working on a single module as well.

Setting up the dev environment
##############################
To set up the development environment for a project, activate your development Python environment and
install the project with ``inmanta project install``.
If you want to be able to make changes to one of these modules, the easiest way is to
check out the module repo separately and run ``pip install -e <path>`` on it, overwriting the published
package that was installed previously. This will install the module in editable form: any changes you make
to the checked out files will be picked up by the compiler. You can also do this prior to installing the
project, in which case the pre-installed module will remain installed in editable form when you install
the project, provided it matches the version constraints. Since these modules are essentially
Python packages, you can double check the desired modules are installed in editable mode by checking
the output of ``pip list --editable``.


Working on the dev environment
##############################

After setting up, you should be left with a dev environment where all required modules have been
installed (either in editable or in packaged form).
When you run a compile from the active Python environment context, the compiler will find the
modules and use them for both their model and their plugins.
Similarly, when you run a module's unit tests, the installed modules will automatically be used
by the compiler.


Module installation on the server
#################################

The orchestrator server generally installs modules from the configured Python package
repository, respecting the project's constraints on its modules and all inter-module constraints. The server is then responsible
for supplying the agents with the appropriate ``inmanta_plugins`` packages.

The only exception to this rule is when using the ``inmanta export`` command. It exports a project and all its modules'
``inmanta_plugins`` packages to the orchestrator server. When this method is used, the orchestrator does not install any modules
from the Python package repository but instead contains all Python code as present in the local Python environment.

.. _setting_up_pip_index_authentication:


Configure the Inmanta server to install modules from a private python package repository
----------------------------------------------------------------------------------------

Modules can be installed from a Python package repository that requires authentication. This section explains how the Inmanta server should be configured to install modules from such a Python package repository.

Create a file named ``/var/lib/inmanta/.netrc`` in the orchestrator's file system.
Add the following content to the file:

.. code-block:: text

  machine <hostname of the private repository>
  login <username>
  password <password>

For more information see the doc about `pip authentication <https://pip.pypa.io/en/stable/topics/authentication/>`_.

You will also need to specify the url of the repository in the ``project.yml`` file of your project (See: :ref:`specify_location_pip`).

By following the previous steps, the Inmanta server will be able to install modules from a private Python package repository.

