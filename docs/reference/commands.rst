.. vim: spell

Command Reference
******************

All inmanta commands and services are started by the ``inmanta`` command. This page provides an
overview of all subcommands available:

.. _reference_commands_inmanta:

inmanta
#########

.. argparse::
   :module: inmanta.app
   :func: cmd_parser
   :prog: inmanta

inmanta-cli
###########

The ``inmanta-cli`` command can be used to interact with the inmanta server and agents,
including managing projects, environments, parameters and more.
The following reference explains the available subcommands.

.. click:: inmanta.main:cmd
   :prog: inmanta-cli
   :show-nested:
