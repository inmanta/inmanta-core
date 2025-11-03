Python client
-------------

The rest API endpoints described below are also available as a `redoc spec <openapi.html#http://>`_.


You can interact with the API endpoints detailed below by using the :py:class:`inmanta.protocol.endpoints.Client` python client:

.. code-block:: python

    client = inmanta.protocol.endpoints.Client(name="client_name", timeout=120)

    result = await client.environment_list(details=True)

    assert result.code == 200

    for key, value in result.result["data"].items():
        ...



Paging, sorting and filtering
=============================

The (v2) API endpoints that offer paging, sorting and filtering follow a convention.
They share the following parameters:

limit
    specifies the page size, so the maximum number of items returned from the query
start and first_id
    These parameters define the lower limit for the page,
end and last_id
    These parameters define the upper limit for the page
    (only one of the (`start`, `first_id`), (`end`, `last_id`) pairs should be specified at the same time).

filter
    The ``filter`` parameter is used for filtering the result set.

    Filters should be specified with the syntax ``?filter.<filter_key>=value``.

    It's also possible to provide multiple values for the same filter, in this case results are returned,
    if they match any of these filter values: ``?filter.<filter_key>=value&filter.<filter_key>=value2``

    Multiple different filters narrow the results however (they are treated as an 'AND' operator).
    For example ``?filter.<filter_key>=value&filter.<filter_key2>=value2`` returns results that match both filters.

    The documentation of each method describes the supported filters.

sort
    The sort parameter describes how the result set should be sorted.

    It should follow the pattern ``?<attribute_to_sort_by>.<order>``, for example ``?value.desc`` (case insensitive).

    The documentation of each method describes the supported attributes to sort by.

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

Type inspection
===============


Is it possible to inspect typing information about the :py:class:`inmanta.protocol.common.Result` (or :py:class:`inmanta.protocol.common.PageableResult`)
returned by an endpoint by using the inmanta mypy plugin.

Make sure you add the inmanta plugin to your mypy configuration, e.g. using the ``pyproject.toml`` file:


.. code-block:: toml

    [tool.mypy]
    plugins = 'inmanta.mypy'


For example, given the following python file:

.. code-block:: python

    from inmanta.protocol.endpoints import Client


    async def main() -> None:
        c: Client
        reveal_type(c)

        reveal_type(c.environment_list)
        reveal_type(await c.environment_list().value())
        reveal_type(c.environment_list().all())


Use mypy to reveal typing information:

.. code-block:: sh

    $ mypy <path/to/file.py>


Endpoints
---------


V1 endpoints
============
.. automodule:: inmanta.protocol.methods
    :members:


V2 endpoints
============

.. automodule:: inmanta.protocol.methods_v2
    :members:


