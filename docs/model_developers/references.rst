.. _references:

References and Secrets
######################

When a handler needs information that is not available to the compiler, references are used.

For example, to extract username and password from a environment variables:

.. code-block:: inmanta
    :emphasize-lines: 6-7

    leaf1 = nokia_srlinux::GnmiDevice(
        auto_agent=true,
        name="leaf1",
        mgmt_ip="172.30.0.210",
        yang_credentials=yang::Credentials(
            username=std::create_environment_reference("GNMI_USER"),
            password=std::create_environment_reference("GNMI_PASS"),
        ),
    )


This means that the username and password will never be present in the compiler, but that they will be picked up by the handler when needed.
This is very different from using `std::get_env`, which will resolve the environment variable in the compiler and store it in the database.

More advanced combination are also possible:

.. code-block:: inmanta
    :emphasize-lines: 1,3,13-14

    netbox_secret = netbox::create_netbox_reference(
        netbox_url=...,
        netbox_token=std::create_environment_reference("NETBOX_API_TOKEN"),
        device=leaf1.name,
        role="admin",
    )

    leaf1 = nokia_srlinux::GnmiDevice(
        auto_agent=true,
        name="leaf1",
        mgmt_ip="172.30.0.210",
        yang_credentials=yang::Credentials(
            username=netbox_secret.name,
            password=netbox_secret.password,
        ),
    )

Here we get the root secret from the environment variable ``NETBOX_API_TOKEN``, which we use to query the inventory for proper credentials for this device.

References can be used in the model and in resources transparently.
However any attempt to perform an operations (e.g. addition, string formatting,... ) on a reference will result in an exception.

References will be automatically resolved before passing the resource into a handler.
I.e. using references in handlers requires no special attention.


Creating new types of References
---------------------------------

When you want to expose your own type of reference, the following steps are required:

1. Create a subclass of :py:class:`inmanta.references.Reference`, with a type parameter that is either a primitive type of a dataclass.
2. Annotate it with :py:func:`inmanta.references.reference`
2. Implement the `resolve` method, that will resolve the reference. This method can use `self.resolve_others` to resolve any reference received as an argument. The logger passed into this method is similar to the ctx passed into a handler. The logger will write the logs into the database as well, when resolving references for a handler.
3. Create a plugin to construct the reference

.. code-block:: python


    @reference("std::Environment")
    class EnvironmentReference(Reference[str]):
        """A reference to fetch environment variables"""

        def __init__(self, name: str | Reference[str]) -> None:
            """
            :param name: The name of the environment variable.
            """
            super().__init__()
            # All fields will be serialized into the resources
            # i.e. it must be json serializable or a reference itself
            # Use `_` as a prefix to prevent serialization of the field
            self.name = name


        def resolve(self, logger: LoggerABC) -> str:
            """Resolve the reference"""
            # We call resolve_other to make sure that if self.name is also a reference
            # it will also be properly resolved
            env_var_name = self.resolve_other(self.name, logger)
            # It is good practice to log relevant steps
            logger.debug("Resolving environment variable %(name)s", name=self.name)
            # actual resolution
            value = os.getenv(env_var_name)
            # Validity check. Abort when not found.
            # Not special base exception is expected, exception handling follows the same rules as in handlers
            if value is None:
                raise LookupError(f"Environment variable {env_var_name} is not set")
            return value


    @plugin
    def create_environment_reference(name: str | Reference[str]) -> Reference[str]:
        """Create an environment reference

        :param name: The name of the variable to fetch from the environment
        :return: A reference to what can be resolved to a string
        """
        return EnvironmentReference(name=name)


Handling references in plugins
------------------------------

When a plugin supports references, it has to explicitly indicate this in the type annotation of the arguments and return value.

For example, to create a plugin that can concatenate two strings, where one of either can be a reference, we would do the following:

.. literalinclude:: examples/references_1.py
   :language: python

.. literalinclude:: examples/references_1.cf
   :language: inmanta


It is also possible to resolve reference in plugins, but this is not their intended use case:

.. literalinclude:: examples/references_2.py
   :language: python

.. literalinclude:: examples/references_2.cf
   :language: inmanta
