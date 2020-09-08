Inmanta Compile Data Reference
==============================

This page documents the compile data output when compiling with the `--export-compile-data` flag. The structure
of this JSON is defined by :py:class:`inmanta.data.model.CompileData` which inherits
from :py:class:`pydantic.BaseModel`. To produce the JSON representation of the object, `model.json()` is called. See the
`pydantic documentation <https://pydantic-docs.helpmanual.io/usage/exporting_models/#modeljson>`_
for more information on how exactly a JSON is generated from a model.

.. autoclass:: inmanta.data.model.CompileData
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:

.. autoclass:: inmanta.ast.export.Error
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:

.. autoclass:: inmanta.ast.export.ErrorCategory
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:

.. autoclass:: inmanta.ast.export.Location
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:

.. autoclass:: inmanta.ast.export.Range
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:

.. autoclass:: inmanta.ast.export.Position
    :show-inheritance:
    :members:
    :exclude-members: Config
    :undoc-members:
