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
Some of these options are detailed below:

pip.use-system-config
"""""""""""""""""""""

This option determines the isolation level of the project's pip config. When false (the default), any pip config set on
the system through pip config files is ignored, the ``PIP_INDEX_URL``, ``PIP_EXTRA_INDEX_URL`` and ``PIP_PRE``
environment variables are ignored, and pip will only look for packages in the index(es) defined in the project.yml.
When true, the orchestrator will use the system's pip configuration for the pip-related settings except when explicitly
overriden in the ``project.yml`` (See below for more details).

Setting this to ``false`` is generally recommended, especially during development, both for portability (achieving
consistent behavior regardless of the system it runs on, which is important for reproductive testing on developer
machines, easy compatibility with Inmanta pytest extensions, and consistency between compiler and agents) and for
security (the isolation reduces the risk of dependency confusion attacks).

Setting this to ``true`` will have the following consequences:

- If no index is set in the ``project.yml`` file i.e. both ``index-url`` and ``extra-index-url`` are unset, then Pip's
  default search behaviour will be used: environment variables, pip config files and then PyPi (in that order).

- If ``index-url`` is set, this value will be used over any index defined in the system's environment
  variables or pip config files.

- If ``extra-index-url`` is set, these indexes will be used in addition to any extra index defined in the system's
  environment variables or pip config files, and passed to pip as extra indexes.

- If ``pre`` is set, it will supersede pip's ``pre`` option set by the ``PIP_PRE`` environment variable or in pip
config file. When true, pre-release versions are allowed when installing v2 modules or v1 modules' dependencies.

- Auto-started agents live on the same host as the server, and so they will share the pip config at the system level.


.. warning::

    ``use-system-config = true`` should only be used if the pip configuration is fully managed at the system level
    and secure for each component of the orchestrator.

Example scenario
""""""""""""""""

1) During development

Using a single pip index isolated from any system config is the recommended approach. The ``pre=true`` option allows
pip to use pre-release versions, e.g. when testing dev versions of modules published to the dev index. Here is an
example of a dev config:

.. code-block:: yaml

    pip:
        index-url: https://my_repo.secure.example.com/repository/dev
        extra-index-url: []
        pre: true
        use-system-config: false

2) In production

Using a single pip index is still the recommended approach, and the use of pre-release versions should be disabled.


For a portable project (recommended), disable ``use-system-config``
and set ``index-url`` to the secure internal repo e.g.:

.. code-block:: yaml

    pip:
        index-url: https://my_repo.secure.example.com/repository/inmanta-production
        pre: false
        use-system-config: false

.. _system_level_pip_config_scenario:

If you prefer to manage the pip configuration at the system level, use ``use-system-config: true`` e.g.:

.. code-block:: yaml

    pip:
        pre: false
        use-system-config: true


.. note::
    Any pip config set explicitly in the project config will always take precedence over the system config. For more
    details see `pip.use-system-config`_.

    Pip-related settings that are not supported by the project config are not overridden.

    To use a setting from the system's pip configuration without overriding it, leave the corresponding option unset in
    the ``project.yml`` file.


.. note::

    Set up authentication towards the index using netrc. See this :ref:`section<setting_up_pip_index_authentication>`
    for more information.

.. _migrate_to_project_wide_pip_config:

Migrate to project-wide pip config
----------------------------------

This section is a migration guide for upgrading to ``inmanta-service-orchestrator 7.0.0`` or ``inmanta 2024.0``.
``inmanta-core 11.0.0`` introduced new options to configure pip settings for the whole project in a
centralized way. For detailed information, see :ref:`here<specify_location_pip>`. The following code sample can be used
as a baseline in the ``project.yml`` file:


.. code-block:: yaml

    pip:
        index-url: https://my_repo.secure.example.com/repository/inmanta-production
        pre: false
        use-system-config: false

Alternatively, if you prefer to manage the pip config at the system level, refer to this
:ref:`section <system_level_pip_config_scenario>`.

All the v2 module sources currently set in a ``repo`` section of the ``project_yml`` with type ``package`` should
also be duplicated in the ``pip.index-url`` (and ``pip.extra-index-url`` if more than one index is being used).

If you want to allow pre-releases for v2 modules and other Python packages, set ``pip.pre = true`` in the project config
file. This used to be controlled by the :class:`~inmanta.module.InstallMode` set at the project level or at a module
level.

Make sure the agents have access to the index(es) configured at the project level.

Run a full compile after upgrading in order to export the project pip config to the server, so that it
is available for agents. This will ensure that the agents follow the pip config defined in the project. For reference,
prior to ``inmanta-core 11.0.0``, the agents were always using their respective system's pip config.


Breaking changes:
"""""""""""""""""

    - Indexes defined through the ``repo`` option with type ``package`` will be ignored.
    - Dependencies for v1 modules will now be installed according to the pip config in the project configuration file,
      while they previously always used the system's pip config.
    - The agent will follow the pip configuration defined in the :ref:`project_yml`.
    - ``PIP_PRE`` is now ignored unless ``use-system-config`` is set.
    - Allowing the installation of pre-release versions for v2 modules through the :class:`~inmanta.module.InstallMode`
      is no longer supported. Use the project.yml ``pip.pre`` section instead.

Changes relative to ``inmanta-2023.4`` (OSS):
"""""""""""""""""""""""""""""""""""""""""""""

    - ``pip.use_config_file`` is refactored into ``pip.use-system-config``.
    - An error is now raised if ``pip.use-system-config`` is false and no "primary" index is set through ``pip.index-url``.
    - Pip environment variables are no longer ignored when ``pip.use-system-config`` is true and the corresponding option
      from the ``project_yml`` is unset.

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
