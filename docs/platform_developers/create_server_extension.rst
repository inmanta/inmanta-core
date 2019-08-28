***************************
Creating a server extension
***************************

An Inmanta server extension adds extra functionality to the Inmanta core. Each extension consists of one or more server slices
that provide certain functionality. This page describes how to create a new extension and the associated server slice(s).


Define a server extension
#########################

Each Inmanta server extension is defined as a subpackage of the ``inmanta_ext`` package. The following directory structure is
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


Create a server slice
#####################

A server slice is defined by creating a class that extends from ``ServerSlice``.

.. code-block::

    class NewSlice(ServerSlice):

        def __init__():
            super().__init__("<slice-name>")

        async def prestart(self, server: Server) -> None:
            """
            Called by the RestServer host prior to start, can be used to collect references to other server slices
            Dependencies are not up yet.
            """
            await super(NewSlice, self).prestart(server)
            # TODO: Custom implementation here

        async def start(self) -> None:
            """
                Start the server slice.

                This method `blocks` until the slice is ready to receive calls

                Dependencies are up (if present) prior to invocation of this call
            """
            await super(NewSlice, self).start()
            # TODO: Custom implementation here

        async def prestop(self) -> None:
            """
                Always called before stop

                Stop producing new work:
                - stop timers
                - stop listeners
                - notify shutdown to systems depending on us (like agents)

                Slice should remain functional.

                All dependencies are up (if present)
            """
            await super(NewSlice, self).prestop()
            # TODO: Custom implementation here

        async def stop(self) -> None:
            """
                Go down

                All dependencies are up (if present)

                This method `blocks` until the slice is down
            """
            await super(NewSlice, self).stop()
            # TODO: Custom implementation here

        def get_dependencies(self) -> List[str]:
            """List of names of slices that must be started before this one."""
            return []

        def get_depended_by(self) -> List[str]:
            """List of names of slices that must be started after this one."""
            return []


* Replace ``<slice-name>`` with the name of the extension. This name should have the format
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
