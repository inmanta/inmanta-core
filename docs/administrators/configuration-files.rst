Configuration files
===================

Inmanta server and Inmanta agent
--------------------------------

The Inmanta server and the Inmanta agent, started via systemd, read their configuration files at the following two locations:

1. ``/etc/inmanta/inmanta.cfg``
2. ``/etc/inmanta/inmanta.d/*.cfg``

The configuration options specified in the ``/etc/inmanta/inmanta.d/`` directory override the configuration options specified in
``/etc/inmanta/inmanta.cfg``. If the directory ``/etc/inmanta/inmanta.d/`` contains two files with the same configuration option, the
conflict is resolved using the alfabetical order of the filesnames. Filenames which appear later in the alfabetical order
override the configuration options from their predecessors in that order.


Inmanta CLI tool
----------------

The ``inmanta`` CLI tool reads its configuration at the following locations:

1. ``/etc/inmanta/inmanta.cfg``
2. ``/etc/inmanta/inmanta.d/*.cfg``     (override using the ``--config-dir`` option)
3. ``~/.inmanta.cfg``
4. ``.inmanta``
5. ``.inmanta.cfg``
6. The config file specified on the CLI using the ``-c`` options

The ``inmanta`` CLI tool searches for the ``.inmanta`` and ``.inmanta.cfg`` files in the directory where the CLI command is
executed.

Configuration files which are ranked lower in the above-mentioned list override the configuration options specified by their
predecessors. If the directory ``/etc/inmanta/inmanta.d/`` contains two files with the same configuration option, the conflict is
resolved using the alfabetical order of the filenames. Filenames which appear later in the alfabetical order override the
configuration options from their predecessors in that order.

The number 2 (``/etc/inmanta/inmanta.d/*.cfg``) in the above-mentioned list can be overridden using the ``--config-dir``
option of the ``inmanta`` command. More information about these options can be found in the
:ref:`inmanta command reference<reference_commands_inmanta>`
