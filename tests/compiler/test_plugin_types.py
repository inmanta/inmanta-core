from typing import Mapping, Any, Union

import pytest
from inmanta.ast import RuntimeException
from inmanta.plugins import to_dsl_type, Null
import inmanta.ast.type as inmanta_type
import collections.abc

def test_conversion():
    assert inmanta_type.Integer() == to_dsl_type(int)
    assert inmanta_type.Float() == to_dsl_type(float)
    assert inmanta_type.NullableType(inmanta_type.Float()) == to_dsl_type(float | None)
    assert inmanta_type.LiteralList() == to_dsl_type(list)
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(dict[str, str])
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(Mapping[str, str])
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(collections.abc.Mapping[str, str])

    assert Null() == to_dsl_type(Union[None] )

    assert isinstance(to_dsl_type(Any), inmanta_type.AnyType)


    with pytest.raises(RuntimeException):
        to_dsl_type(dict[int, int])

