Model debugging
===============

.. warning::
    This is a beta feature. It does not support the full language yet and it might not
    work as expected. Currently known limitations:

    - lists and dicts not supported
    - string interpolation not supported
    - constructor kwargs not supported
    - plugins not supported
    - conditionals not supported
    - for loops not supported
    - boolean operations not supported
    - explicit index lookups not supported
    - only double assignment, exceeding relation arity and incomplete instance errors are supported

    Support for the listed language features will be added gradually.

The inmanta DSL is essentially a data flow oriented language. As a model developer you never
explicitly manipulate control flow. Instead you declare data flow: the statement ``x = y``
for example declares that the data in ``y`` should flow towards ``x``. Even dynamic statements
such as implementations and for loops do not explicitly manipulate control flow. They too can be
interpreted as data flow declarations.

Because of this property conventional debugging methods such as inspecting a stack trace are not
directly applicable to the inmanta language. A stack trace is meant to give the developer insight
in the part of the control flow that led to the error.
Extending this idea to the inmanta DSL leads to the concept of a data trace. Since
the language is data flow oriented, a trace of the flow to some erroneous part of the configuration
model gives the developer insight in the cause of the error.

Additionally, a root cause analysis will be done on any incomplete instances and only those root
causes will be reported.

The first section, :ref:`Enabling the data trace<enable-data-trace>` describes how to enable these two
tools. The tools themselves are described in the sections
:ref:`Interpreting the data trace<datatrace>` and :ref:`Root cause analysis<rootcause>`
respectively. An example use case is shown in :ref:`Usage example<data-trace-usage>`, and the final section,
:ref:`Graphic visualization<data-flow-graphic>`, shortly describes a graphic representation of the data flow.


.. _enable-data-trace:

Enabling the data trace
------------------------

To show a data trace when an error occurs, compile the model with the ``--experimental-data-trace``
flag. For example:

.. code-block:: inmanta
    :caption: main.cf
    :linenos:

    x = 1
    x = 2

Compiling with ``inmanta compile --experimental-data-trace`` results in

.. code-block::

    inmanta.ast.DoubleSetException: value set twice:
        old value: 1
            set at ./main.cf:1
        new value: 2
            set at ./main.cf:2

    data trace:
    x
    ├── 1
    │   SET BY `x = 1`
    │   AT ./main.cf:1
    └── 2
        SET BY `x = 2`
        AT ./main.cf:2
     (reported in x = 2 (./main.cf:2))


.. _datatrace:

Interpreting the data trace
---------------------------

Let's have another look at the data trace for the model above:

.. code-block::
    :linenos:

    x
    ├── 1
    │   SET BY `x = 1`
    │   AT ./main.cf:1
    └── 2
        SET BY `x = 2`
        AT ./main.cf:2

Line 1 shows the variable where the error occurred. A tree departs from there with branches going to
lines 2 and 5 respectively. These branches indicate the data flow to ``x``. In this case line 2 indicates
``x`` has been assigned the literal ``1`` by the statement ``x = 1`` at ``main.cf:1`` and the literal
``2`` by the statement ``x = 2`` at ``main.cf:2``.

Now let's go one step further and add an assignment to another variable.

.. code-block:: inmanta
    :caption: variable-assignment.cf
    :linenos:

    x = 0
    x = y
    y = 1

.. code-block::
    :caption: data trace for variable-assignment.cf
    :linenos:

    x
    ├── y
    │   SET BY `x = y`
    │   AT ./variable-assignment.cf:2
    │   └── 1
    │       SET BY `y = 1`
    │       AT ./variable-assignment.cf:3
    └── 0
        SET BY `x = 0`
        AT ./variable-assignment.cf:1

As before we can see the data flow to ``x`` as declared in the model. Following the tree from ``x`` to its
leaves leads to the conclusion that ``x`` has indeed received two inconsistent values, and it gives insight
into how those values came to be assigned to ``x`` (``0`` directly and ``1`` via ``y``).

One more before we move on to entities:

.. code-block:: inmanta
    :caption: assignment-loop.cf
    :linenos:

    x = y
    y = z
    z = x

    x = 0
    z = u
    u = 1

.. code-block::
    :caption: data trace for assignment-loop.cf
    :linenos:

    z
    EQUIVALENT TO {x, y, z} DUE TO STATEMENTS:
        `x = y` AT ./assignment-loop.cf:1
        `y = z` AT ./assignment-loop.cf:2
        `z = x` AT ./assignment-loop.cf:3
    ├── u
    │   SET BY `z = u`
    │   AT ./assignment-loop.cf:6
    │   └── 1
    │       SET BY `u = 1`
    │       AT ./assignment-loop.cf:7
    └── 0
        SET BY `x = 0`
        AT ./assignment-loop.cf:5

This model defines an assignment loop between ``x``, ``y`` and ``z``. Assignment to either of these variables
will result in a flow of data to all of them. In other words, the variables are equivalent. The data trace
shows this information at lines 2--5 along with the statements that caused the equivalence. The rest of the
trace is similar to before, except that the tree now shows all assignments to any of the three variables part
of the equivalence. The tree now no longer shows just the data flow to ``x`` but to the equivalence as a whole,
since any data that flows to the equivalence will also flow to ``x``.

.. code-block:: inmanta
    :caption: entities.cf
    :linenos:

    entity A:
        number n
    end

    implement A using std::none

    x = A(n = 0)

    template = x

    y = A(n = template.n)
    y.n = 1

.. code-block::
    :caption: data trace for entities.cf
    :linenos:

    attribute n on __config__::A instance
    SUBTREE for __config__::A instance:
        CONSTRUCTED BY `A(n=template.n)`
        AT ./entities.cf:11
    ├── template.n
    │   SET BY `A(n=template.n)`
    │   AT ./entities.cf:11
    │   SUBTREE for template:
    │       └── x
    │           SET BY `template = x`
    │           AT ./entities.cf:9
    │           └── __config__::A instance
    │               SET BY `x = A(n=0)`
    │               AT ./entities.cf:7
    │               CONSTRUCTED BY `A(n=0)`
    │               AT ./entities.cf:7
    │   └── 0
    │       SET BY `A(n=0)`
    │       AT ./entities.cf:7
    └── 1
        SET BY `y.n = 1`
        AT ./entities.cf:12

As usual, line 1 states the variable that represents
the root of the data flow tree. In this case it's the attribute ``n`` of an instance of ``A``. Which instance?
That is shown in the subtree for that instance on lines 2--4. In this case it's a very simple subtree that shows
just the construction of the instance and the line number in the configuration model. The tree for the attribute
starts at line 5. The first branch shows the assignment to ``template.n`` in the constructor for ``y``. Then
another subtree is shown at lines 8--16, this one more useful. It shows a data flow graph like we're used to
by now, with ``template`` as the root. Then at line 17 the trace shows the data flow ``template.n <- 0`` referring
to ``entities.cf:7``. This line doesn't assign to ``template.n`` directly, but it does assign to the instance at the
end of the subtree for ``template`` (the data that flows to ``template``).


Let's have a look at an implementation:

.. code-block:: inmanta
    :caption: implementation.cf
    :linenos:

    entity A:
        number n
    end

    implement A using i

    implementation i for A:
        self.n = 42
    end

    x = A(n = 0)

.. code-block::
    :caption: data trace for implementation.cf
    :linenos:

    attribute n on __config__::A instance
    SUBTREE for __config__::A instance:
        CONSTRUCTED BY `A(n=0)`
        AT ./implementation.cf:11
    ├── 0
    │   SET BY `A(n=0)`
    │   AT ./implementation.cf:11
    └── 42
        SET BY `self.n = 42`
        AT ./implementation.cf:8
        IN IMPLEMENTATION WITH self = __config__::A instance
            CONSTRUCTED BY `A(n=0)`
            AT ./implementation.cf:11

The only thing new in this trace can be found at lines 11---13. It highlights that a statement was executed within a dynamic context
and shows a subtree for the ``self`` variable.


And finally, an index:

.. code-block:: inmanta
    :caption: index.cf
    :linenos:

    entity A:
        number n
        number m
    end

    index A(n)

    implement A using std::none

    A(n = 42, m = 0)
    A(n = 42, m = 1)

.. code-block::
    :caption: data trace for index.cf
    :linenos:

    attribute m on __config__::A instance
    SUBTREE for __config__::A instance:
        CONSTRUCTED BY `A(n=42,m=0)`
        AT ./index.cf:10

        INDEX MATCH: `__config__::A instance`
            CONSTRUCTED BY `A(n=42,m=1)`
            AT ./index.cf:11
    ├── 1
    │   SET BY `A(n=42,m=1)`
    │   AT ./index.cf:11
    └── 0
        SET BY `A(n=42,m=0)`
        AT ./index.cf:10

This data trace highlights the index match between the two constructors at lines 6--8.


.. _rootcause:

Root cause analysis
-------------------

Enabling the data trace also enables a root cause analysis when multiple attributes have not received a value.
For example, compiling the model below results in three errors, one for each of the instances.

.. code-block:: inmanta
    :linenos:

    entity A:
        number n
    end

    implement A using std::none

    x = A()
    y = A()
    z = A()

    x.n = y.n
    y.n = z.n

.. code-block::
    :caption: compile output
    :linenos:

    Reported 3 errors
    error 0:
      The object __config__::A (instantiated at ./main.cf:7) is not complete: attribute n (./main.cf:2) is not set
    error 1:
      The object __config__::A (instantiated at ./main.cf:9) is not complete: attribute n (./main.cf:2) is not set
    error 2:
      The object __config__::A (instantiated at ./main.cf:8) is not complete: attribute n (./main.cf:2) is not set

Compiling with data trace enabled will do a root cause analysis on these errors. In this case it will infer that ``x.n``
and ``y.n`` are only unset because ``z.n`` is unset. Compiling then shows:

.. code-block::
    :caption: compile output with --experimental-data-trace
    :linenos:

    Reported 1 errors
    error 0:
      The object __config__::A (instantiated at ./main.cf:9) is not complete: attribute n (./main.cf:2) is not set

In cases where a single error leads to errors for a collection of related attributes, this can greatly simplify the
debugging process.


.. _data-trace-usage:

Usage example
--------------

Let's have a look at the model below:

.. _data-trace-model-service:

.. code-block:: inmanta
    :caption: service.cf
    :linenos:

    entity Port:
        string host
        number portn
    end

    index Port(host, portn)

    entity Service:
        string name
        string host
        number portn
    end

    Service.port [0:1] -- Port.service [0:1]


    implement Port using std::none
    implement Service using bind_port


    implementation bind_port for Service:
        self.port = Port(host = self.host, portn = self.portn)
    end


    sshd = Service(
        name = "opensshd",
        host = "my_host",
        portn = 22,
    )


    custom_service = Service(
        name = "some_custom_service",
        host = "my_host",
        portn = 22,
    )

Compiling this with data trace disabled outputs the following error:

.. code-block::
    :caption: compilation output for service.cf with data trace disabled

    Could not set attribute `port` on instance `__config__::Service (instantiated at ./service.cf:33)` (reported in self.port = Construct(Port) (./service.cf:22))
    caused by:
      Could not set attribute `service` on instance `__config__::Port (instantiated at ./service.cf:22,./service.cf:22)` (reported in __config__::Port (instantiated at ./service.cf:22,./service.cf:22) (./service.cf:22))
      caused by:
        value set twice:
        old value: __config__::Service (instantiated at ./service.cf:26)
            set at ./service.cf:22
        new value: __config__::Service (instantiated at ./service.cf:33)
            set at ./service.cf:22
     (reported in self.port = Construct(Port) (./service.cf:22))

The error message refers to ``service.cf:22`` which is part of an implementation. It is not clear
which ``Service`` instance is being refined, which makes finding the cause of the error challenging.
Enabling data trace results in the trace below:

.. code-block::
    :caption: data trace for service.cf
    :linenos:

    attribute service on __config__::Port instance
    SUBTREE for __config__::Port instance:
        CONSTRUCTED BY `Port(host=self.host,portn=self.portn)`
        AT ./service.cf:22
        IN IMPLEMENTATION WITH self = __config__::Service instance
            CONSTRUCTED BY `Service(name='opensshd',host='my_host',portn=22)`
            AT ./service.cf:26

        INDEX MATCH: `__config__::Port instance`
            CONSTRUCTED BY `Port(host=self.host,portn=self.portn)`
            AT ./service.cf:22
            IN IMPLEMENTATION WITH self = __config__::Service instance
                CONSTRUCTED BY `Service(name='some_custom_service',host='my_host',portn=22)`
                AT ./service.cf:33
    ├── __config__::Service instance
    │   SET BY `self.port = Port(host=self.host,portn=self.portn)`
    │   AT ./service.cf:22
    │   IN IMPLEMENTATION WITH self = __config__::Service instance
    │       CONSTRUCTED BY `Service(name='some_custom_service',host='my_host',portn=22)`
    │       AT ./service.cf:33
    │   CONSTRUCTED BY `Service(name='some_custom_service',host='my_host',portn=22)`
    │   AT ./service.cf:33
    └── __config__::Service instance
        SET BY `self.port = Port(host=self.host,portn=self.portn)`
        AT ./service.cf:22
        IN IMPLEMENTATION WITH self = __config__::Service instance
            CONSTRUCTED BY `Service(name='opensshd',host='my_host',portn=22)`
            AT ./service.cf:26
        CONSTRUCTED BY `Service(name='opensshd',host='my_host',portn=22)`
        AT ./service.cf:26

At lines 15 and 23 it shows the two ``Service`` instances that are also mentioned in the original error
message. This time, the dynamic implementation context is mentioned and it's clear that these instances
have been assigned in a refinement for the ``Service`` instances constructed at lines 26 and 33 in the
configuration model respectively.

Lines 2--14 in the trace give some additional information about the
``Port`` instance. It indicates there is an index match between the ``Port`` instances constructed in the
implementations for both ``Service`` instances. This illustrates the existence of the two branches at lines
15 and 23, and why the assignment in this implementation
resulted in the exceeding of the relation arity: the right hand side is the same instance in both cases.


.. _data-flow-graphic:

Graphic visualization
---------------------

.. warning::
    This representation is not as complete as the data trace explained above. It does not show information
    about statements responsible for each assignment. It was primarily developed as an aid in developing
    the data flow framework on which the data trace and the root cause analysis tools are built. It's described
    here because it's closely related to the two tools described above. Its actual use in model debugging
    might be limited.

.. note::
    Using this feature requires one of inmanta's optional dependencies to be installed: ``pip install inmanta[dataflow_graphic]``.
    It also requires the ``fdp`` command to be available on your system. This is most likely packaged in your distribution's
    ``graphviz`` package.

Let's compile the model in :ref:`service.cf<data-trace-model-service>` again, this time with ``--experimental-dataflow-graphic``.
The compile results in an error, as usual, but this time it's accompanied by a graphic visualization of the data flow.


.. image:: ./images/dataflow_graphic_service.*


It shows all assignments, as well as the index match between the two ``Port`` constructions. An assignment where the right hand side is an
attribute ``x.y`` is shown by an arrow to ``x``, labeled with ``.y``. Variables are represented by ellipses, values by diamonds and instances
by rectangular containers.
