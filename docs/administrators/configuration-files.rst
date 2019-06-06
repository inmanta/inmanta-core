Configuration files
===================

Inmanta server and Inmanta agent
--------------------------------

The Inmanta server and the Inmanta agent read configuration files from the following two locations:

1. ``/etc/inmanta/inmanta.cfg``
2. ``/etc/inmanta.d/*.cfg``

The configuration options specified in the ``/etc/inmanta.d/`` directory override the configuration options specified in
``/etc/inmanta/inmanta.cfg``. If the directory ``/etc/inmanta.d/`` contains two files with the same configuration option, the
conflict is resolved using the alfabetical order of the filesnames. Filenames which appear later in the alfabetical order
override the configuration options from their predecessors in that order.


Inmanta CLI tools
-----------------

The Inmanta CLI reads its configuration from the following files:

1. ``/etc/inmanta/inmanta.cfg``
2. ``/etc/inmanta.d/*.cfg``
3. ``~/.inmanta.cfg``
4. ``.inmanta``
5. ``.inmanta.cfg``

The Inmanta CLI tools will search for the files ``.inmanta`` and ``.inmanta.cfg`` in the current working directory where the
CLI command is executed from.

Configuration files which are ranked lower in the above-mentioned list override the configuration options specified by their
predecessors. If the directory ``/etc/inmanta.d/`` contains two files with the same configuration option, the conflict is
resolved using the alfabetical order of the filesnames. Filenames which appear later in the alfabetical order override the
configuration options from their predecessors in that order.