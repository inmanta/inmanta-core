Understanding Projects
======================

A project is the basic unit of orchestration. It contains:

* ``main.cf``: the entry point for the compiler to start executing
* ``project.yml``: the project meta data, defines where to find modules and which versions to use. For detailed documentation see: :ref:`project_yml`.
* ``requirements.txt``: the python dependencies of the project, defines which python dependencies to install and which versions to use.

.. code-block:: sh

    project
    |
    |__ project.yml
    |__ requirements.txt
    |__ main.cf

