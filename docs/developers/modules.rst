Module Developers Guide
========================
In inmanta all configuration model code and related files, templates, plugins and resource handlers are packaged in a module.

Module layout
*************
Inmanta expects that each module is a git repository with a specific layout:

* The name of the module is determined by the top-level directory. Within this module directory, a ``module.yml`` file has 
  to be specified.
* The only mandatory subdirectory is the ``model`` directory containing a file called ``_init.cf``. What is defined in the 
  ``_init.cf`` file is available in the namespace linked with the name of the module. Other files in the model directory 
  create subnamespaces.
* The ``plugins`` directory contains Python files that are loaded by the platform and can extend it using the Inmanta API.
  This python code can provide plugins or resource handlers.

The template, file and source plugins from the std module expect the following directories as well:

* The ``files`` directory contains files that are deployed verbatim to managed machines.
* The ``templates`` directory contains templates that use parameters from the configuration model to generate configuration
  files.

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


Module metadata
***************
The module.yml file provides metadata about the module. This file is a yaml file with the following three keys mandatory:

* *name*: The name of the module. This name should also match the name of the module directory.
* *license*: The license under which the module is distributed.
* *version*: The version of this module. For a new module a start version could be 0.1dev0 These versions are parsed using the 
  same version parser as python setuptools.

For example the following module.yaml from the :doc:`../quickstart`

.. code-block:: yaml

    name: lamp
    license: Apache 2.0
    version: 0.1

Module depdencies are indicated by importing a module in a model file. However, these import do not have a specifc version 
identifier. The version of a module import can be constrained in the module.yml file. The *requires* key excepts a list of 
version specs. These version specs use `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.

To specify specific version are required, constraints can be added to the requires list::

    license: Apache 2.0
    name: ip
    source: git@github.com:inmanta/ip
    version: 0.1.15
    requires:
        net: net ~= 0.2.4
        std: std >1.0 <2.5

A module can also indicate a minimal compiler version with the *compiler_version* key.

*source* indicates the authoritative repository where the module is maintained.

Versioning
**********
Inmanta modules should be versioned. The current version is reflected in the module.yml file and in the commit is should be 
tagged in the git repository as well. To ease the use inmanta provides a command (inmanta modules commit) to modify module 
versions, commit to git and place the correct tag.

To make changes to a module, first create a new git branch::

    git checkout -b mywork

When done, first use git to add files::

    git add *

To commit, use the module tool. It will autmatically set the right tags on the module::

    inmanta moduletool commit -m "First commit"

This will create a new dev release. To make an actual release::

    inmanta moduletool commit -r -m "First Release"

To set a specific version::

    inmanta moduletool commit -r -m "First Release" -v 1.0.1

The module tool also support semantic versioning instead of setting versions directly. Use one
of ``--major``, ``--minor`` or ``--patch`` to update version numbers: <major>.<minor>.<patch>
