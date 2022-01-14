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

The orchestrator server generally (see
:ref:`Advanced concepts<modules-distribution-advanced-concepts>`) installs modules from the configured Python package
repository, respecting the project's constraints on its modules and all inter-module constraints. The server is then responsible
for supplying the agents with the appropriate ``inmanta_plugins`` packages.

V1 modules
##########

Inmanta V1 modules are versioned based on git tags. The current version is reflected in the ``module.yml`` file.
The commit should be tagged with the version in the git repository as well. To
ease the use inmanta provides a command (``inmanta modules commit``) to modify module versions, commit to git and place the
correct tag.

Development Versions
--------------------
To make changes to a module, first create a new git branch:

.. code-block:: bash

    git checkout -b mywork

When done, first use git to add files:

.. code-block:: bash

    git add *

To commit, use the module tool. This will create a new dev release.

.. code-block:: bash

    inmanta module commit --patch -m "Fixed small bug"

This command will set the version to the next dev version (`+0.0.1dev`) and add a timestamp.

The module tool supports semantic versioning.
Use one of ``--major``, ``--minor`` or ``--patch`` to update version numbers: <major>.<minor>.<patch>

For the dev releases, no tags are created.

Release Versions
----------------

To make an actual release (without `.dev` at the end):

.. code-block:: bash

    inmanta module commit -r -m "First Release"

This will remove the `.dev` version and automatically set the right tags on the module.

To automatically freeze all dependencies of this module to the currently checked out versions

.. code-block:: bash

	inmanta module freeze --recursive --operator ==


Or for the current project

.. code-block:: bash

	inmanta project freeze --recursive --operator ==

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
