
.. _validation_types:


*******************
Validation types
*******************


By default, the compiler validates the types of the attributes of a service instance. For certain types, type checking
is done at the API level, prior to compilation. This provides a more interactive feedback to the operator since
validation is performed before firing up the compile process. Type validation is done at the API level for the following
types:

* Primitive types: int, number, string, bool, dict and list.
* Certain types defined via the :ref:`typedef statement<language_reference_typedef>`.

The std module already defines many commonly used types for which validation is performed at the API level (e.g., ip,
url, date, ...).
The section below defines for which typedef statement validation is done at the API level.

Supported forms
###############


Enumeration
~~~~~~~~~~~

Syntax
------
.. code-block:: inmanta

    typedef <attr> as <type> matching self in <enumeration>

Examples
--------

.. code-block:: inmanta

    typedef colour as string matching self in ["red", "green", "blue"]
    typedef bundle_size as number matching self in [1, 10, 100]

------------

Regular expressions
~~~~~~~~~~~~~~~~~~~
Syntax
------
.. code-block:: inmanta

    typedef <attr> as <type> matching <pattern>

Example
-------

.. code-block:: inmanta

    typedef lowercase as string matching /^[a-z]+$/

------------

Number constraints
~~~~~~~~~~~~~~~~~~
Syntax
------

.. code-block:: inmanta

    typedef <attr> as <type> matching self <cmp> <value> [(or | and) <comparison_2> ...]
    typedef <attr> as <type> matching <value> <cmp> self [(or | and) <comparison_2> ...]

Where:

* <cmp> is one of `<, <=, >, >=`
* <value> is any number

Example
-------

.. code-block:: inmanta

    typedef port_number as int matching self > 1023 and self <= 65535

------------

std::validate_type()
~~~~~~~~~~~~~~~~~~~~

The `std::validate_type() <../../../reference/modules/std.html#std.validate_type>`_
function allows for finer grained type definition.

These three forms are supported:

.. code-block:: inmanta

    typedef <attr> as <type> matching std::validate_type(<parameters>)
    typedef <attr> as <type> matching std::validate_type(<parameters>) == true
    typedef <attr> as <type> matching true == std::validate_type(<parameters>)


Example
-------
.. code-block:: inmanta

    typedef my_type as int matching true == std::validate_type("pydantic.conint", self, {"gt": 0, "lt": 10})

