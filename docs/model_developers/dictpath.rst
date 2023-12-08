.. _dict_path:

*********
Dict Path
*********

DictPath is a library for navigating json data.

The DictPath library offers a convenient way to get a specific value out of a structure of nested dicts and lists.

Writing DictPath expressions
############################

A DictPath expression is a ``.``-separated path.
The following elements are supported:

1. ``.dkey``: Return the value under ``dkey`` in the dict. ``dkey`` cannot be an empty string. Use the ``*`` character to get all values of the dictionary.
2. ``lst[lkey=lvalue]``: Find a dictionary in a list of dictionaries. Find the dict with ``lkey=lvalue``.  ``lvalue`` can be an empty string. ``lst`` and ``lkey`` cannot be an empty string. If no or more than one dict matches the filter, a LookupError is raised. The ``*`` character can be used for ``lkey`` and ``lvalue`` to match respectively any key or value. ``\0`` can be used for ``lvalue`` to match against the value``None``.
    If no single key uniquely identifies an object, multiple keys can be used: ``lst[lkey1=lvalue1][lkey2=lvalue2]``.

Each element of the path (keys or values) must escape the following special characters with a single backslash: ``\``, ``[``, ``]``, ``.``, ``*`` and ``=``. Other characters must not be escaped.

A leading ``.`` character represent the entire data structure provided to the dict path library. As such, the following dict paths are logically equivalent to each other: ``a.b.c`` and ``.a.b.c``. A dict path can also consist of a single dot (``.``). This expression represents the identity function.


Using DictPath in code
######################

.. warning::
    The dict path library only works correctly when the keys and values, referenced in a dict path expression, are of a primitive type and the type is the same for all keys and values at the same level. For example, ``{"True": 1, True: 2}`` is not a valid dictionary.


- To convert a dictpath expression to a ``DictPath`` instance, use ``dict_path.to_path``. Use ``dict_path.to_wild_path`` in order to allow wildcards (``*``) to be used in the dict path expression.
- To get the element from a collection use ``DictPath.get_element(collection)``
- To set an element in a collection use ``DictPath.set_element(collection, value)``

.. autoclass:: inmanta.util.dict_path.DictPath
   :members:

.. autofunction:: inmanta.util.dict_path.to_path
.. autofunction:: inmanta.util.dict_path.to_wild_path

Example
#######

.. code-block:: python

    from inmanta.util import dict_path

    container = {
        "a": "b",
        "c": {
            "e": "f"
        },
        "g": [
            {"h": "i", "j": "k"},
            {"h": "a", "j": "b"}
        ]
    }

    assert dict_path.to_path("a").get_element(container) == "b"
    assert dict_path.to_path("c.e").get_element(container) == "f"
    assert dict_path.to_path("g[h=i]").get_element(container) == {"h": "i", "j": "k"}

    assert dict_path.to_wild_path("c.*").get_elements(container) == ["f"]
    assert sorted(dict_path.to_wild_path("g[h=i].*").get_elements(container)) == ["i", "k"]
    assert dict_path.to_wild_path("g[*=k]").get_elements(container) == [{"h": "i", "j": "k"}]

    dict_path.to_path("g[h=b].i").set_element(container, "z")
    assert dict_path.to_path("g[h=b]").get_element(container) == {"h": "b", "i": "z"}
    assert dict_path.to_path("g[h=b].i").get_element(container) == "z"

