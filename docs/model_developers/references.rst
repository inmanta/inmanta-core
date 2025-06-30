.. _references:

References and Secrets
######################

When a handler needs information that is not available to the compiler, references are used.

For example, to extract username and password from an environment variables:

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


This means that the username and password will never be present in the compiler, logs or database, but that they will be picked up by the handler when needed.
This is very different from using ``std::get_env``, which will resolve the environment variable in the compiler and store it in the database.

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
However any attempt to perform an operation (e.g. addition, string formatting,... ) on a reference will result in an exception.

References will be automatically resolved before passing the resource into a handler.
I.e. using references in handlers requires no special attention.


Creating new types of References
---------------------------------

When you want to expose your own type of reference, the following steps are required:

1. Create a subclass of :py:class:`inmanta.references.Reference`, with a type parameter that is either a primitive type or a dataclass. Multiple layers of inheritance are also supported, but due to practical limitations, each concrete reference type still has to inherit from ``Reference[<concrete_type>]`` directly.
2. Annotate it with :py:func:`inmanta.references.reference`.
3. Implement the ``resolve`` method, that will resolve the reference. This method can use ``self.resolve_others`` to resolve any reference received as an argument. The logger passed into this method is similar to the ``ctx`` argument passed into a handler. The logger will write the logs into the database as well, when resolving references for a handler.
4. Create a plugin to construct the reference.

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
This has to be explicit, even for plugins that accept ``object`` or untyped ``list`` / ``dict``.

For example, to create a plugin that can concatenate two strings, where either one can be a reference, we would do the following:

.. literalinclude:: examples/references_1.py
   :language: python

.. literalinclude:: examples/references_1.cf
   :language: inmanta


The requirement for explicit declaration of references exists because it is impossible to pass references around transparently
in the Python domain (as we do in the model domain). Since the Python domain is so flexible, most of it is out of the compiler's
control. Therefore, we have to make sure that we only pass in values that the plugin developer might reasonably expect.  e.g.
consider a plugin parameter annotated as ``bool``. A plugin developer would expect that its value would be either ``True`` or
``False``, and might use statements such as ``if <value>``. This would not be valid with a reference value. The same goes for
more complex operations. Therefore, references are only passed into plugins when the plugin developer has explicitly declared
that they are expected, so that they know to take them into account.

A known limitation of this validation is with parameters annotated as ``object`` or untyped ``list`` / ``dict``. For these
parameters, we can validate the object itself, and we can go one layer deeper for ``list`` / ``dict``. But below that, the
compiler can not make any assumptions about the structure of the argument value, so reference validation only applies to that
top level. Concretely, this means that an ``object`` annotation would reject ``my_reference``, but not ``[my_reference]``. The
plugin developer should be aware that references may show up in nested values when working with ``object``-annotated plugins.

The above covers values passed as arguments to a plugin. But there is another way that model values can enter the Python
domain: to access attributes on a model instance. Model instances are not converted to a native Python value on the plugin
boundary, but instead they are represented by a proxy object. When you access an attribute on it, the associated value is
fetched from the model. For the same reasons as outlined above, references can not be accessed in such a way, unless the plugin
developer has indicated that references are expected. To this end, the :py:func:`inmanta.plugins.allow_reference_values` method
is provided. The following example demonstrates this.

.. code-block:: python

    from inmanta import plugins


    @plugin
    def get_value(instance: "std::Entity") -> int | Reference[int]:
        return plugins.allow_reference_values(instance).value


Resolving references in plugins
-------------------------------

It is also possible to resolve reference in plugins, but this is not their intended use case:

.. literalinclude:: examples/references_2.py
   :language: python

.. literalinclude:: examples/references_2.cf
   :language: inmanta


References to dataclasses
-------------------------

References can also be used with :ref:`dataclasses`. This mostly works exactly as you would expect out of the box. However,
some advanced use cases might require a more in-depth knowledge of how these two concepts interact.

There are two aspects to the interaction of dataclasses and references. One is references `to` dataclass instances. The other is
references `inside` a dataclass instance. And then there are the two domains in which these values live: the model domain and the
plugin (Python) domain.

Let's start with references inside dataclasses and look at the representation in both domains.

.. code-block:: python

    @dataclasses.dataclass(frozen=True)
    class Data:
        value: int | Reference[int]
        description: str

.. code-block:: inmanta

    entity Data extends std::Dataclass:
        int value
        string description
    end

Note how in the Python domain, the reference support is annotated just as it is for plugin parameters. This is also completely
in line with what you might expect of Python type annotations. In the model however, references are always transparent, and so
they have no explicit declaration there. Furthermore, in the model references are always allowed, regardless of the
annotations in the Python domain. It is only when (if) a corresponding Python object is constructed, that its type validation
comes into play.

As a result the behavior of these references in dataclasses is also very similar to that of other plugin parameters. A plugin
that accepts a dataclass instance will have to convert the model representation to the Python dataclass. If any of the
attributes turns out to be a reference, it will be allowed only if the corresponding Python attribute is annotated with a ``Reference``
annotation. In the case of the ``Data`` example above, if ``description`` were a reference in the model instance, it would be
rejected with a clear error message. ``value`` on the other hand supports references in the Python domain, so if it is a
reference in the model, the conversion to the Python dataclass is allowed.

Now, let's consider the other aspect: references `to` dataclasses, e.g. ``Reference[Data]``. This too works mostly as you would
expect. As with other plugin parameter types, a plugin that accepts a reference to a dataclass, will get a reference object
if the value that is passed in is a reference. However, for the other direction, it is slightly more flexible than for other
reference types. Suppose a plugin doesn't declare reference support, it just accepts ``Data``. The compiler recognizes that
conceptually a reference to a dataclass can be safely represented as a dataclass with references for all its attributes, as
long as all attributes support references. So in that case, the reference to the dataclass is simply coerced to a dataclass
with reference attributes. Let's look at an example:

.. code-block:: python

    @dataclasses.dataclass(frozen=True)
    class SimpleData:
        value: int | Reference[int]

    @dataclasses.dataclass(frozen=True)
    class DescribedData:
        value: int | Reference[int]
        description: str

    @plugin
    def create_simple_data_reference() -> Reference[SimpleData]:
        ...

    @plugin
    def create_described_data_reference() -> Reference[DescribedData]:
        ...

    @plugin
    def process_data(data: SimpleData | DescribedData) -> None:
        ...

Now consider that we'd call ``process_data(create_simple_data_reference())`` from the model. ``process_data`` accepts a dataclass,
but we pass in a reference. Luckily, all ``SimpleData``'s attributes support references, so the compiler converts the argument
to ``SimpleData(value=<reference>)``. On the other hand, if we'd call ``process_data(create_described_data_reference())`` from the
model, the compiler will raise an error, because ``DescribedData`` does not allow references for its ``description`` attribute.


References in resources
-----------------------

References may occur in resource entities, as in any other entities. Consequentially, they may also appear when accessing the
model for field mapping methods (``get_$(field_name)`` as described in the :ref:`resources` section). Unlike in plugins,
references are supposed to be transparent in resources. Therefore, the resource developer should be aware when accessing model
values from these mapping methods, reference values may occur anywhere.
