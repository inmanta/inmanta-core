.. _module-creation-guide:

Module creation guide
============================

This guide explains how to create a module.
For detailed documentation see: :ref:`modules_v2_setup_cfg`.

Create a new source module
---------------------------

.. code-block:: sh
  :linenos:

  pip install cookiecutter
  cookiecutter gh:inmanta/inmanta-module-template

.. note::

    The cookiecutter template also sets up git for the new module.
    This is a best practice to version control your infrastructure code.


Inside the module the compiler expects a ``setup.cfg`` file that defines metadata
about the module. :ref:`modules_v2_setup_cfg` provides an overview about the supported metadata
attributes.
