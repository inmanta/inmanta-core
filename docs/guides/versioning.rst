Versioning
**********

Inmanta has the moduletool subcommand to hanlde installing and checking of modules.


Creating a project
==================

To create a project,

1. Make a project directory
2. Create a project.yml file::

    name: Testproject
    description: A project to demonstrate project creation
    modulepath: libs
    downloadpath: libs
    repo:
        - git@github.com:inmanta/

* The modulepath is a list of paths where the compiler will search for modules
* The downloadpath is the path where the moduletool will install new modules
* The repo is a list of paths where the moduletool will search for new modules

Installing modules
==================
Once you have a project.yml file, you can automatically install the required modules::

    inmanta modules install

This will clone the module and check out the last version.

Changing a module
==================

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

Requires format
===============

To specify specific version are required, constraints can be added to the requires list::

    license: Apache 2.0
    name: ip
    source: git@github.com:inmanta/ip
    version: 0.1.15
    requires:
        net: net ~= 0.2.4
        std: std >1.0 <2.5
