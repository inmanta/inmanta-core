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


Server-side checkout and authentication
---------------------------------------

For server-side compiles, the orchestrator obtains the project from a git repository. Each environment is
configured with a repository URL and a branch: the orchestrator clones this repository into the environment's
project directory on the first compile and pulls updates from it on subsequent compiles.

When the repository requires authentication, git takes credentials from its usual sources: a ``.netrc`` file,
credentials embedded in the repository URL, or a configured git credential helper. The simplest option is a
``.netrc`` file in the server's home directory (``/var/lib/inmanta/.netrc``). This is the same file that is used
to authenticate against a :ref:`private Python package repository<setting_up_pip_index_authentication>`, so a
single file can cover both the project checkout and module installation:

.. code-block:: text

    machine <hostname of the git repository>
    login <username>
    password <password>

If a checkout fails to authenticate, the compile report shows the ``Cloning repository`` or ``Pulling updates``
step failing with an ``Authentication failed`` error. See :ref:`debugging_project_authentication` for how to find
out which credential source git used.

