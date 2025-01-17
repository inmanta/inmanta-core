.. _module-finalizers:

Finalizers
*********************
When writing models it can be useful to have functions that will be run at the end of the compilation. A typical use case is making sure all resources are properly flushed back and all connections are properly closed.
To help with this, finalizers can be used.

Adding new finalizers
========================

A finalizer is a python function that is registered by using the :func:`~inmanta.compiler.finalizer` function as decorator
or as callback.
This function should be a function that doesn't take arguments and that doesn't return anything.
Functions registered this way will be called when the compiler finishes (with no guarantee on the execution order).

An example of a finalizer that will close an open connection using the decorator option requires the following code:

.. code-block:: python
    :linenos:

    from inmanta import compiler

    connection = None

    def get_connection():
       global connection
       if connection is None:
            connection = connect()
       return connection

    @compiler.finalizer
    def finalize_connection():
       if connection:
          connection.close()

The same example but using the callback option would look like this:

.. code-block:: python
    :linenos:

    from inmanta import compiler

    connection = None

    def get_connection():
      global connection
      if not connection:
           connection = connect()
           compiler.finalizer(finalize_connection)
       return connection

    def finalize_connection():
       if connection:
          connection.close()
