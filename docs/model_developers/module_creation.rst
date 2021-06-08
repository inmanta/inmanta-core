.. _module-creation-guide:

Module creation guide
============================

This guide explains how to create a module.
For detailed documentation see: :ref:`module_yml`.

Create a new source module
---------------------------


.. code-block:: sh
  :linenos:

  pip install cookiecutter
  cookiecutter gh:inmanta/inmanta-module-template

.. note::

    The cookiecutter template also sets up git for the new module.
    This is a best practice to version control your infrastructure code.


Inside the module the compiler expects a ``module.yml`` file that defines metadata about the module.
 :ref:`module_yml` provides an overview about the supported metadata attributes.

An example ``module.yml`` could be:

.. code-block:: yaml
  :linenos:

  license: Apache 2.0
  name: ip
  source: git@github.com:inmanta/ip
  version: 0.1.15
  requires:
      - net ~= 0.2.4
      - std >1.0 <2.5
