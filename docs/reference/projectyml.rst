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

.. autoclass:: inmanta.module.ProjectPipConfig


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
    pip:
        index-url: https://pypi.org/simple/
        extra-index-url: []
        pre: false
        use-system-config: false


.. _specify_location_pip:

Configure pip index
-------------------

This section explains how to configure a project-wide pip index. This index will be used to download v2 modules and v1
modules' dependencies.
By default, a project created using the :ref:`project-creation-guide` is configured to install packages from ``https://pypi.org/simple/``.
The :class:`~inmanta.module.ProjectPipConfig` section of the project.yml file offers options to configure this behaviour.

pip.use-system-config
"""""""""""""""""""""

This option determines the isolation level of the project's pip config. When false, any pip config set on the system
(e.g. through environment variables or pip config files) are ignored and pip will only look for packages
in the index(es) defined in the project.yml, when true, pip will in addition look in the eventual index(es) defined on the system.

Setting this to ``false`` is recommended during development both for portability (by making sure that only the pip
config defined in the project.yml will be used regardless of the sytem's pip config) and for security (The isolation
reduces the risk of dependency confusion attacks if the ``index-url`` option is set mindfully).

Setting this to ``true`` will have the following consequences:

- If no index is set in the project.yml file i.e. both ``index-url`` and ``extra-index-url`` are unset, then Pip's
  default search behaviour will be used: environment variables, pip config files and then PyPi (in that order).

- If ``index-url`` and/or ``extra-index-url`` are set, they will be used and any index defined in the system's environment
  variables or pip config files will also be used (in that order) and passed to pip as extra indexes.

- The ``PIP_PRE`` environment variable (if set) is no longer ignored and will be used to determine whether pre-release
  versions are allowed when installing v2 modules or v1 modules' dependencies.

Example scenario
""""""""""""""""

1) During development

Using a single pip index isolated from any system config is the recommended approach. The ``pre=true`` option allows
pip to use pre-release versions, e.g. when testing dev versions of modules published to the dev index. Here is an
example of a dev config:

.. code-block:: yaml

    pip:
        index-url: https://devpi.example.com/dev/
        extra-index-url: []
        pre: true
        use-system-config: false

2) In production

Using a single pip index is still the recommended approach, and the use of pre-release versions should be disabled. Here is an
example of a config suitable in production:

.. code-block:: yaml

    pip:
        index-url: https://devpi.example.com/stable/
        extra-index-url: []
        pre: false
        use-system-config: true

.. note::
    The options defined in the ``project.yml`` pip section will always take precedence over the corresponding pip options, even
    when ``use-system-config`` is set to true (other pip-related environment variables are not overridden).

    For example, in the production scenario above, if the following
    pip environment variables were set by mistake on the server running the compiler: ``PIP_INDEX_URL=https://devpi.example.com/dev/``
    and ``PIP_PRE=true``, the config used in the end would still be the one defined in the project.yml, namely
    ``index-url=https://devpi.example.com/stable/`` and ``pre=false``.

An alternative approach would be to configure all pip-related options through the system config. For example:

.. code-block:: yaml

    pip:
        index-url:
        extra-index-url: []
        pre:
        use-system-config: true

And set the following env variables:

.. code-block:: bash

    export PIP_INDEX_URL=https://devpi.example.com/stable/
    export PIP_PRE=false

In this scenario, pip options defined in env variables (if any) would be used over the system's pip config.

.. note::

    Using netrc is the recommended way to set up authentication towards the index. See
    this :ref:`section<setting_up_pip_index_authentication>` for more information.

.. _migrate_to_project_wide_pip_config:

Migrate to project-wide pip config
----------------------------------

Previously, there was no centralized way of configuring pip settings for the whole project. This section can be used
as a migration guide.

Defining a ``repo`` with type ``package`` is deprecated. Make sure you define this index through the pip.index-url option instead.

Previously, the :class:`InstallMode` set at the project level or at a module level was used to determine if the
installation of pre-release versions was allowed. This behaviour should now be set through the ``pip.pre`` option instead.

A full compile should be run after upgrading, in order to export the project pip config to the server, so that it
is available for agents.

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
