Compiler Configuration Reference
===================================

.. _project_yml:

project.yml
------------

Inside any project the compiler expects a ``project.yml`` file that defines metadata about the project,
the location to store modules, repositories where to find modules and possibly specific versions of
modules.

For basic usage information, see :ref:`project-creation-guide`.

The ``project.yml`` file defines the following settings:

.. autoclass:: inmanta.module.ProjectMetadata


.. _module_yml:

module.yml
----------

Inside any module the compiler expects a ``module.yml`` file that defines metadata about the module.

The ``module.yml`` file defines the following settings:

.. autoclass:: inmanta.module.ModuleMetadata

