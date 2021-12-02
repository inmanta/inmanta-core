Releasing Modules
=================

Inmanta modules are versioned based on git tags. The current version is reflected in the ``module.yml`` file for V1 modules or
in the ``setup.cfg`` file for V2 modules. The commit should be tagged with the version in the git repository as well. To
ease the use inmanta provides a command (``inmanta modules commit``) to modify module versions, commit to git and place the
correct tag.

Development Versions
####################
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
################

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

Distributing Inmanta modules
############################

Inmanta modules can be distributed in two different ways: using a Git repository (V1 modules) or using a Python package (V2
modules).

Git repository distribution format
----------------------------------

Distributing a V1 module using a Git repository happens by storing the source code of that module on a Git repository
that is accessible by the Inmanta orchestrator. The orchestrator will clone the source code of the module and install it in the
Inmanta project.

Python package distribution format
----------------------------------

Modules defined in the V2 module format can be distributed as a Python package. Run the ``inmanta module build`` command in
the source directory of a module to build a Python Wheel from that module. The resulting package is stored in the dist directory
of the module. The Python packages should be stored on a Python package repository, reachable by the orchestrator.
Uploading packages to the package repository should be done with the appropriate tool for the specific repository at hand.
