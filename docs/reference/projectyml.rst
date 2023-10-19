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


When True, the indexes defined in `inmanta.module.ProjectPipConfig.index_url`
        and `inmanta.module.ProjectPipConfig.extra_index_url` (if any) will be used, in addition to indexes defined in pip
        environment variables (PIP_INDEX_URL and PIP_EXTRA_INDEX_URL) and/or config in the pip config file (in that order),
        including any extra-index-urls. If no indexes are defined in `inmanta.module.ProjectPipConfig.index_url` or
        `inmanta.module.ProjectPipConfig.extra_index_url`, fallback to pip's default behaviour: the index(es) defined in
        pip environment variables will override those defined in pip config files, which will override the default PyPi index.
        When False, only use the pip options defined in the project.yml file and ignore all pip config files and pip
        environment variables related to installation e.g. PIP_PRE.

Configure pip index
-------------------

This section explains how to configure a project-wide pip index. This index will be used to download v2 modules and v1
modules' dependencies.
By default, a project created using the :ref:`project-creation-guide` is configured to install packages from ``https://pypi.org/simple/``.
The :class:`~inmanta.module.ProjectPipConfig` section of the project.yml file offers options to configure this behaviour.

use-system-config
"""""""""""""""""

This option determines the isolation level of the project's pip config. When false, pip will only look for packages
in the index(es) defined in the project.yml, when true, pip will in addition look in the eventual index(es) defined on the system.

Setting this to `false` is recommended during development both for portability (by making sure that only the pip
config defined in the project.yml will be used regardless of the sytem's pip config) and for security (The isolation
reduces the risk of dependency confusion attacks if the `index-url` option is set mindfully).

Setting this to `true` will have the following consequences:

- If no index is set in the project.yml file i.e. both index_url and extra_index_url are unset -> Pip's
default behaviour to look for indexes will be used : environment variables, pip config files and then PyPi (in that order).

- If index_url and/or extra_index_url are set, they will be used and any index defined in the system's environment
variables or pip config files will also be used (in that order).

Using pip config file
"""""""""""""""""""""

By setting the ``use_config_file`` option of the pip section to ``True``, the project will use the pip config files.

.. code-block:: yaml

    pip:
      use_config_file: True

To specify the url of a pip repository, add the following to the pip config file of the ``inmanta`` user, located at ``/var/lib/inmanta/.config/pip/pip.conf``:

.. code-block:: text

  [global]
  timeout = 60
  index-url = <url of a python package repository>


Alternatively, a pip config file can be used at a custom location.
The ``index-url`` can be specified in this file as explained in the previous section.
To make this work, the ``PIP_CONFIG_FILE`` environment variable needs to be set to the path of the newly created file (See: :ref:`env_vars`).
For more information see the `Pip documentation <https://pip.pypa.io/en/stable/topics/configuration/>`_.

Specify the index-urls in the project.yml file
""""""""""""""""""""""""""""""""""""""""""""""

Another option is to use the  ``index_urls`` option in the ``pip`` section of the ``project.yml`` file:

.. code-block:: yaml

    pip:
      use_config_file: False
      index_urls:
        - <url of a python package repository>


.. note::
    The pip config file can also be used in combination with ``index-urls`` specified in the ``pip`` section of the ``project.yml`` file:

    * If the pip config is used (by setting ``use_config_file`` to ``true``), the ``index-url`` specified in the pip config file will take precedence and the ``index-urls`` specified in the ``pip`` section of the ``project.yml`` file will be used as ``extra-index-urls`` when installing with pip.
    * If the pip config is not used (by setting ``use_config_file`` to ``False``), then the first ``index_url`` specified in the project.yml will be used as an ``index_url`` and all the following ones will be used as ``extra-index-urls`` when installing with pip.

.. _migrate_from_repo_package:

Defining a `repo` with type `package` is deprecated. Make sure you define this index through the pip.index-url option instead.


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
