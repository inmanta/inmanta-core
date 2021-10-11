Releasing Modules
=================

Inmanta modules are versioned based on git tags. The current version is reflected in the ``module.yml`` file and in the
commit is should be tagged in the git repository as well. To ease the use inmanta provides a command (``inmanta modules
commit``) to modify module versions, commit to git and place the correct tag.

Development Versions
----------------------
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


For more information about the ``module.yml`` file see :ref:`module_yml`.

