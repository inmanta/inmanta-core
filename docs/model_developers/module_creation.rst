.. _module-creation-guide:

Module creation guide
============================

This guide explains how to create a module.
For detailed documentation see: :ref:`module_yml` and :ref:`modules_v2_setup_cfg`.

Create a new source module
---------------------------

For a v1 module:

.. code-block:: sh
  :linenos:

  pip install cookiecutter
  cookiecutter gh:inmanta/inmanta-module-template

For a v2 module:

.. code-block:: sh
  :linenos:

  pip install cookiecutter
  cookiecutter --checkout v2 gh:inmanta/inmanta-module-template

.. note::

    The cookiecutter template also sets up git for the new module.
    This is a best practice to version control your infrastructure code.


Inside the module the compiler expects a ``module.yml`` file (for v1) or a ``setup.cfg`` file (for v2) that defines metadata
about the module. :ref:`module_yml` and :ref:`modules_v2_setup_cfg` provide an overview about the supported metadata
attributes.
