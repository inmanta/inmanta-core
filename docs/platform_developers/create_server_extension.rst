*******************************
Creating a new server extension
*******************************

Inmanta server extensions are separate Python packages with their own release cycle that can add additional server slices
to the orchestrator. Server slices are components in the service orchestrator. A slice can be responsible for API endpoints or
provide internal services to other slices. The core server extension provides all slices of the core service orchestrator.


The package layout of a server extension
########################################

Each Inmanta server extension is defined as a subpackage of the ``inmanta_ext`` package. ``inmanta_ext`` is a namespace package
used by the service orchestrator to discover new extensions. The following directory structure is
required for a new extension called ``new_extension``.

.. code-block:: sh

    inmanta_ext
    |
    |__ new_extension
    |    |__ __init__.py
    |    |__ extension.py


* The ``__init__.py`` file can be left empty. This file is only required to indicate that ``new_extension`` is a python package.
* The ``extension.py`` file must contain a ``setup`` function that registers the necessary server slices to the application
  context. An example ``extension.py`` file is shown below. The parameter ``<server-slice-instance>`` should be replaced with
  an instance of the server slice that belongs to the extension. Multiple server slices can be registered.

.. code-block:: python

    # File: extension.py
    from inmanta.server.extensions import ApplicationContext

    def setup(application: ApplicationContext) -> None:
        application.register_slice(<server-slice-instance>)


.. tip:: Indicate which version of the Inmanta core is compatible with the developed extension by pinning the version of the
         Inmanta core in the ``requirements.txt`` file of the extension.


Adding server slices to the extension
#####################################

A server slice is defined by creating a class that extends from :class:`inmanta.server.protocol.ServerSlice`.

.. autoclass:: inmanta.server.protocol.ServerSlice
    :members: prestart, start, prestop, stop, get_dependencies, get_depended_by


* The constructor of the ServerSlice class expects the name of the slice as an argument. This name should have the format
  ``"<extension-name>.<server-slice-name>"``. ``<extension-name>`` is the name of the package that contains the
  ``extension.py`` file. ``<server-slice-name>`` can be chosen by the developer.
* The ``prestart()``, ``start()``, ``prestop()``, ``stop()``, ``get_dependencies()`` and ``get_depended_by()`` methods can be
  overridden when required.


Enable the extension
####################

By default, no extensions are enabled on the Inmanta server. Extensions can be enabled by specifying them in the
:inmanta.config:option:`server.enabled-extensions` option of the Inmanta configuration file. This option accepts a
comma-separated list of extensions that should be enabled.

.. code-block::

    # File: /etc/inmanta/inmanta.d/0-extensions.cfg
    [server]
    enabled_extensions=new_extension


The Inmanta extension template
##############################

A new Inmanta extension can be created via the Inmanta extension template. This is a cookiecutter template to generate the
initial Python project for a new Inmanta extension. The documentation regarding this template is available on
https://github.com/inmanta/inmanta-extension-template.