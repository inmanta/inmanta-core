Understanding Projects
======================

A project is the basic unit of orchestration. It contains:

* ``main.cf``: the entry point for the compiler to start executing
* ``project.yml``: the project meta data, defines where to find modules and which versions to use. For detailed documentation see: :ref:`project_yml`.
* ``requirements.txt``: (optional) the python dependencies of the project, defines which python dependencies to
  install and which versions to use. Dependencies with extras can be defined in this file using the
  ``dependency[extra-a,extra-b]`` syntax. It has two main use cases:

    * It contains the listing of all modules that should be installed as a V2 module.
    * It contains version constraints to help pip resolve version conflicts on python packages.

.. code-block:: sh

    project
    |
    |__ project.yml
    |__ requirements.txt
    |__ main.cf

