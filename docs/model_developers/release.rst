.. _Releasing and distributing modules:

Releasing and distributing modules
==================================

V2 modules
##########

.. _modules-distribution-v2:

Distributing V2 modules
-----------------------

V2 modules are distributed as Python packages. To build a package for a module, run ``inmanta module build`` in
the source directory of the module. The resulting Python wheel can then be found in the dist directory of the module.
You can then publish this to the Python package repository of your choice, for example the public PyPi repository.
The inmanta build tool will package a module named ``my_module`` under the name ``inmanta-module-my-module``.

V1 modules
##########

Inmanta V1 modules are versioned based on git tags. The current version is reflected in the ``module.yml`` file.
The commit should be tagged with the version in the git repository as well. To release a module, use the
`release <https://docs.inmanta.com/community/latest/reference/commands.html#release>`_ command
as outlined below.

Development Versions
--------------------
To make changes to a module, first create a new git branch:

.. code-block:: bash

    git checkout -b mywork

When done, first use git to add files:

.. code-block:: bash

    git add *

Create a new dev version:

.. code-block:: bash

    inmanta module release --dev --patch -m "Fixed small bug"

This command will set the version to the next dev version, e.g. ``+0.0.1dev`` for a patch increment.

The module tool supports semantic versioning.
Use one of ``--major``, ``--minor`` or ``--patch`` to update version numbers: ``<major>.<minor>.<patch>``

For the dev releases, no tags are created.
Once the dev version is ready for release, perform a proper release by following
the steps in the `Release Versions`_ section below.

Release Versions
----------------

To perform an actual stable release, checkout the main development branch
and use the ``inmanta module release`` command:

.. code-block:: bash

    inmanta module release
    git push
    git push origin {tag}

This will create a stable version corresponding to the current dev version without the ``.dev`` and tag it.
This will also setup the main development branch for further development by creating a new dev version
that is a patch ahead of the latest released version.


Distributing V1 modules
-----------------------

V1 modules are generally simply distributed using a Git repository. They can however also be built as a V2 Python package
and distributed the same as other V2 modules.

Git repository distribution format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Distributing a V1 module using a Git repository happens by storing the source code of that module on a Git repository
that is accessible by the Inmanta orchestrator. The orchestrator will clone the source code of the module and install it in the
Inmanta project. Tagging release versions as outlined above allows specifying constraints on the module version.

V2 package distribution format
------------------------------

A V2 package can be built for a V1 module with ``inmanta module build``. This package can be distributed as described in
:ref:`modules-distribution-v2`.
Modules installed from a package will always act as V2 modules and will be considered such by the compiler.


Freezing a project
##################
Prior to releasing a new stable version of an inmanta project, you might wish to freeze its module
dependencies. This will ensure that the orchestrator server will always work with the exact
versions specified. You can achieve this with
``inmanta project freeze --recursive --operator "=="``. This command will freeze all module
dependencies to their exact version as they currently exist in the Python environment. The recursive
option makes sure all module dependencies are frozen, not just the direct dependencies. In other
words, if the project depends on module ``a`` which in turn depends on module ``b``, both modules
will be pinned to their current version in ``setup.cfg``.
