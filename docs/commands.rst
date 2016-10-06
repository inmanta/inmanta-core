.. vim: spell

Command reference
******************

All inmanta commands and services are started by the ``inmanta`` command. This page provides an
overview of all subcommands available:

inmanta
#########

.. argparse::
   :module: inmanta.app
   :func: cmd_parser
   :prog: inmanta

inmanta-cli
###########

.. argparse::
   :module: inmanta.main
   :func: get_parser
   :prog: inmanta-cli
