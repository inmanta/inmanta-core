Python client
=============

The rest API endpoints described below are also available as a `swagger spec <swagger.html#http://>`_.


You can interact with the API endpoints detailed below by using the :py:class:`inmanta.protocol.endpoints.Client` python client:

.. code-block:: python

    client = inmanta.protocol.endpoints.Client(name="api", timeout=120)

    result = await client.environment_list(details=True)

    assert result.code == 200

    for key, value in result.result["data"].items():
        ...


When calling a :ref:`v2 endpoint <v2-endpoints>`, use the :py:meth:`inmanta.protocol.common.Result.value` method
to retrieve a fully typed object e.g.:

.. code-block:: python

    client = inmanta.protocol.endpoints.Client(name="api", timeout=120)

    env_uuid = ...
    env_object: inmanta.data.model.Environment = await client.environment_get(env_uuid).value()

    assert isinstance(env_object, inmanta.data.model.Environment)


Paging, sorting and filtering
#############################

The (v2) API endpoints that offer paging, sorting and filtering follow a convention.
They share the following parameters:

limit
    specifies the page size, so the maximum number of items returned from the query


sort
    The sort parameter describes how the result set should be sorted.

    It should follow the pattern ``?<attribute_to_sort_by>.<order>``, for example ``?value.desc`` (case insensitive).

    The documentation of each method describes the supported attributes to sort by.


start
    Min boundary value (exclusive) for the requested page for the primary sort column, regardless of sorting order.

end
    Max boundary value (exclusive) for the requested page for the primary sort column, regardless of sorting order.

first_id
    Min boundary value (exclusive) for the requested page for the secondary sort column, if there is one, regardless of sorting order.
    When used along with the ``start`` parameter, the value of this parameter is used as a tiebreaker on the secondary sort column
    for records whose primary sort column is equal to the ``start`` parameter.

last_id
    Max boundary value (exclusive) for the requested page for the secondary sort column, if there is one, regardless of sorting order.
    When used along with the ``end`` parameter, the value of this parameter is used as a tiebreaker on the secondary sort column
    for records whose primary sort column is equal to the ``end`` parameter.


(only one of the (``start``, ``first_id``), (``end``, ``last_id``) pairs should be specified at the same time).

filter
    The ``filter`` parameter is used for filtering the result set.

    Filters should be specified with the syntax ``?filter.<filter_key>=value``.

    It's also possible to provide multiple values for the same filter, in this case results are returned,
    if they match any of these filter values: ``?filter.<filter_key>=value&filter.<filter_key>=value2``

    Multiple different filters narrow the results however (they are treated as an 'AND' operator).
    For example ``?filter.<filter_key>=value&filter.<filter_key2>=value2`` returns results that match both filters.

    The documentation of each method describes the supported filters.

.. _helper_method_for_paging:

.. note::

    The return value of these methods that support paging contains a ``links`` tag, with the urls of the ``next`` and
    ``prev`` pages. To iterate over all the results, the client can follow these links, or alternatively call the
    helper methods on the :py:class:`inmanta.protocol.common.PageableResult` object:

    .. code-block:: python

        # Iterate over all results by fetching pages of size 20

        async for item in client.resource_list(tid=env.id, limit=20).all():
            ...


        # Iterate over results on a single page

        for item in await client.resource_list(tid=env.id, limit=20).value():
            ...


    When calling an endpoint from a synchronous context, the :py:meth:`inmanta.protocol.common.PageableResult.all_sync`
    method should be used instead of the all() method:

    .. code-block:: python

        # Iterate over all results by fetching pages of size 20
        for item in client.resource_list(tid=env.id, limit=20).all_sync():
            assert item == all_resources[idx]
            idx += 1


.. _python_client_mypy_plugin:

Static type checking
####################


The inmanta mypy plugin provides static type checking on the methods called via the python client.
Make sure you add the inmanta plugin to your mypy configuration, e.g. using the ``pyproject.toml`` file:


.. code-block:: toml

    [tool.mypy]
    plugins = 'inmanta.mypy'


And then use mypy for static type checking, e.g. given the following python file:

.. code-block:: python

    client = inmanta.protocol.endpoints.Client(name="api", timeout=120)

    env_id: str = "123"
    result = await client.resource_list(env_id)


Use mypy for type checking:

.. code-block:: sh

    $ mypy <path/to/file.py>

    (...) error: Argument 1 to "resource_list" has incompatible type "str"; expected "UUID"  [arg-type]
    Found 1 error in 1 file (checked 1 source file)



Endpoints
#########

This section contains an overview of all the API endpoints the server offers.

V1 endpoints
------------
.. automodule:: inmanta.protocol.methods
    :members:

.. _v2-endpoints:

V2 endpoints
------------

.. automodule:: inmanta.protocol.methods_v2
    :members:


