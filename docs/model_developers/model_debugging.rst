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
    - only double assignment and exceeding relation arity errors are supported

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


Enabling the  data trace
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
shows this information at lines 2--5 along with the statements that casused the equivalence. The rest of the
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

    x = A(n = 42, m = 0)
    x = A(n = 42, m = 1)

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
    └── 0
        SET BY `A(n=42,m=0)`
        AT ./index.cf:10

This data trace highlights the index match between the two constructors at lines 6--8.

Usage examples
--------------

TODO: some more complicated examples where the usefulness of the trace becomes clear.

TODO: note the performance overhead
