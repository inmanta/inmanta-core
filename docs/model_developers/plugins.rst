.. _module-plugins:

Developing Plugins
*********************


Adding new plugins
========================

Plugins provide :ref:`functions<lang-plugins>` that can be called from the :term:`DSL`. This is the
primary mechanism to interface Python code with the orchestration model at compile time. For Example,
this mechanism is also used for std::template and std::file. In addition to this, Inmanta also registers all
plugins with the template engine (Jinja2) to use as filters.

A plugin is a python function, registered with the platform with the :func:`~inmanta.plugins.plugin`
decorator. This plugin accepts arguments when called from the DSL and can return a value. Both the
arguments and the return value must by annotated with the allowed types from the orchestration model.
Type annotations are provided as a string (Python3 style argument annotation). ``any`` is a special
type that effectively disables type validation.

Through the arguments of the function, the Python code in the plugin can navigate the orchestration
model. The compiler takes care of scheduling the execution at the correct point in the model
evaluation.

.. note::

    A module's Python code lives in the ``inmanta_plugins.<module_name>`` namespace.

A simple plugin that accepts no arguments, prints out "hello world" and returns no value requires
the following code:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin
    def hello() -> None:
        print("Hello world!")


If the code above is placed in the plugins directory of the example module
(``examples/plugins/__init__.py``) the plugin can be invoked from the orchestration model as
follows:

.. code-block:: inmanta

    import example

    example::hello()

The plugin decorator accepts an argument name. This can be used to change the name of the plugin in
the DSL. This can be used to create plugins that use python reserved names such as ``print`` for example:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin("print")
    def printf() -> None:
        """
            Prints inmanta
        """
        print("inmanta")


A more complex plugin accepts arguments and returns a value. Compared to what `python supports as
function arguments <https://docs.python.org/3/glossary.html#term-parameter>`_, only positional-only
arguments are not supported.
The following example creates a plugin that converts a string to uppercase:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin
    def upper(value: "string") -> "string":
        return value.upper()


This plugin can be tested with:

.. code-block:: inmanta

    import example

    std::print(example::upper("hello world"))


Argument type annotations are strings that refer to Inmanta primitive types or to entities. If an
entity is passed to a plugin, the python code of the plugin can navigate relations throughout the
orchestration model to access attributes of other entities.

A base exception for plugins is provided in ``inmanta.plugins.PluginException``. Exceptions raised
from a plugin should be of a subtype of this base exception.

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin, PluginException

    @plugin
    def raise_exception(message: "string") -> None:
        raise PluginException(message)

If your plugin requires external libraries, add them as dependencies of the module. For more details on how to add dependencies
see :ref:`moddev-module`.

.. todo:: context
.. todo:: new statements




Deprecate plugins
========================

To deprecate a plugin the :func:`~inmanta.plugins.deprecated` decorator can be used in combination with the :func:`~inmanta.plugins.plugin`
decorator. Using this decorator will log a warning message when the function is called. This decorator also accepts an
optional argument ``replaced_by`` which can be used to potentially improve the warning message by telling which other
plugin should be used in the place of the current one.

for example if the plugin below is called:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin, deprecated

    @deprecated(replaced_by="my_new_plugin")
    @plugin
    def printf() -> None:
        """
            Prints inmanta
        """
        print("inmanta")


it will give following warning:

.. code-block::

    Plugin 'printf' in module 'inmanta_plugins.<module_name>' is deprecated. It should be replaced by 'my_new_plugin'

Should the replace_by argument be omitted, the warning would look like this:

.. code-block::

    Plugin 'printf' in module 'inmanta_plugins.<module_name>' is deprecated.

If you want your module to stay compatible with older versions of inmanta you will also need to add a little piece of code that changes how
:func:`~inmanta.plugins.deprecated` is imported as it does not exist in all versions.

The previous example would then look like this. For older inmanta versions, replace the decorator with a no-op.

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    try:
        from inmanta.plugins import deprecated
    except ImportError:
        deprecated = lambda function=None, **kwargs: function if function is not None else deprecated


    @deprecated(replaced_by="my_new_plugin")
    @plugin
    def printf() -> None:
        """
            Prints inmanta
        """
        print("inmanta")

