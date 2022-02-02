Compiler Configuration Reference
===================================

.. _project_yml:

project.yml
###########

Inside any project the compiler expects a ``project.yml`` file that defines metadata about the project,
the location to store modules, repositories where to find modules and possibly specific versions of
modules.

For basic usage information, see :ref:`project-creation-guide`.

The ``project.yml`` file defines the following settings:

.. autoclass:: inmanta.module.ProjectMetadata

.. autoclass:: inmanta.module.ModuleRepoInfo
    :show-inheritance:

.. autoclass:: inmanta.module.ModuleRepoType
    :show-inheritance:


The code snippet below provides an example of a complete ``project.yml`` file:

.. code-block:: yaml

    name: quickstart
    description: A quickstart project that installs a drupal website.
    author: Inmanta
    author_email: code@inmanta.com
    license: Apache 2.0
    copyright: Inmanta (2021)
    modulepath: libs
    downloadpath: libs
    install_mode: release
    repo:
      - url: https://github.com/inmanta/
        type: git
      - url: https://pypi.org/simple/
        type: package
    requires:
      - apache ~= 0.5.2
      - drupal ~= 0.7.3
      - exec ~= 1.1.4
      - ip ~= 1.2.1
      - mysql ~= 0.6.2
      - net ~= 1.0.5
      - php ~= 0.3.1
      - redhat ~= 0.9.2
      - std ~= 3.0.2
      - web ~= 0.3.3
      - yum ~= 0.6.2
    freeze_recursive: true
    freeze_operator: ~=


Module metadata files
#####################

The metadata of a V1 module is present in the module.yml file. V2 modules keep their metadata in the setup.cfg file. Below
sections describe each of these metadata files.

.. _module_yml:

module.yml
----------

Inside any V1 module the compiler expects a ``module.yml`` file that defines metadata about the module.

The ``module.yml`` file defines the following settings:

.. autoclass:: inmanta.module.ModuleMetadata

The code snippet below provides an example of a complete ``module.yml`` file:

.. code-block:: yaml

    name: openstack
    description: A module to manage networks, routers, virtual machine, etc. on an Openstack cluster.
    version: 3.7.1
    license: Apache 2.0
    compiler_version: 2020.2
    requires:
      - ip
      - net
      - platform
      - ssh
      - std
    freeze_recursive: false
    freeze_operator: ~=


.. _modules_v2_setup_cfg:

setup.cfg
---------

Inside any V2 module the compiler expects a ``setup.cfg`` file that defines metadata about the module.

The code snippet below provides an example of a complete ``setup.cfg`` file:

.. code-block:: ini

    [metadata]
    name = inmanta-module-openstack
    description = A module to manage networks, routers, virtual machine, etc. on an Openstack cluster.
    version = 3.7.1
    license = Apache 2.0
    compiler_version = 2020.2
    freeze_recursive = false
    freeze_operator = ~=

    [options]
    install_requires =
      inmanta-modules-ip
      inmanta-modules-net
      inmanta-modules-platform
      inmanta-modules-ssh
      inmanta-modules-std
