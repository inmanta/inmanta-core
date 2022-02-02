Exceptions
==========

For more details about Compiler Exceptions, see :ref:`compiler-exceptions`

HTTP Exceptions
---------------

HTTP Exceptions are raised when a server request can't be completed successfully.
Each exception specifies what the HTTP status code of the response should be.
By using the correct exception type (and a descriptive error message) the clients can get more information about what went wrong.

.. autoclass:: inmanta.protocol.exceptions.BaseHttpException
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.Forbidden
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.UnauthorizedException
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.BadRequest
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.NotFound
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.Conflict
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.ServerError
    :show-inheritance:

.. autoclass:: inmanta.protocol.exceptions.ShutdownInProgress
    :show-inheritance:

Database Schema Related Exceptions
----------------------------------

For more details, see :doc:`database`

.. autoclass:: inmanta.data.schema.TableNotFound
    :show-inheritance:

.. autoclass:: inmanta.data.schema.ColumnNotFound
    :show-inheritance:
