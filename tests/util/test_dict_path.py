"""
    Copyright 2023 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

import copy
import logging
from collections.abc import Sequence
from itertools import chain
from typing import Optional

import pytest

from inmanta.util.dict_path import (
    ComposedPath,
    DictPath,
    DictPathValue,
    InDict,
    KeyedList,
    NormalValue,
    NullPath,
    NullValue,
    WildCardValue,
    WildComposedPath,
    WildInDict,
    WildKeyedList,
    WildNullPath,
    to_path,
    to_wild_path,
)


def test_dict_parser_round_trip() -> None:
    bag = {
        "a": {
            "b": {"c": "a.b.c"},
            "c": [{}, {"x": "z"}, {"z": "www", "d": {"e": "a.c[z=www].d.e"}}],
        }
    }
    items = ["a.b.c", "a.c[z=www].d.e"]
    for item in items:
        the_path = ComposedPath(path_str=item)
        assert the_path.un_parse() == item
        assert the_path.get_element(bag) == item


def test_set_value() -> None:
    bag: dict = {"e": {"f": {}}, "x": [{"a": "abc"}, {"b": "def"}]}
    items = [
        ("a.b.c", "d"),
        ("a.c[z=www].d.e", "f"),
        ("a.c[z=www].d.g", "h"),
        ("e.f", "g"),
        ("x[b=def]", {"b": "other-value"}),
    ]
    for item, value in items:
        the_path = ComposedPath(path_str=item)
        the_path.set_element(bag, value)

    after_bag = {
        "a": {"b": {"c": "d"}, "c": [{"z": "www", "d": {"e": "f", "g": "h"}}]},
        "e": {"f": "g"},
        "x": [{"a": "abc"}, {"b": "other-value"}],
    }

    assert bag == after_bag


def test_add() -> None:
    items = [
        ("a.b.c", "d"),
        ("a.c[z=www].d.e", "f"),
        ("a.c[z=www].d.g", "h"),
        ("e.f", "g"),
    ]
    for first, second in items:
        assert (ComposedPath(path_str=first) + ComposedPath(path_str=second)).to_str() == first + "." + second


def test_null_path() -> None:
    items = [
        ("a.b.c", "d"),
        ("a.c[z=www].d.e", "f"),
        ("a.c[z=www].d.g", "h"),
        ("e.f", "g"),
    ]
    for first, second in items:
        assert (ComposedPath(path_str=first) + NullPath() + ComposedPath(path_str=second)).to_str() == first + "." + second

    # Test parsing
    assert isinstance(to_path("."), NullPath)
    assert to_path(".").to_str() == "."

    # Test get_element() on NullPath
    np = to_path(".")
    container = {"a": "b", "c": "d"}
    assert np.get_element(container) == container

    np = NullPath()
    with pytest.raises(LookupError):
        np.get_element(None)

    inc = {}
    assert inc is np.get_element(inc)

    incp = ComposedPath(path_str="a")

    # Adding to nullpath is a null operation
    assert incp == np + incp
    assert incp == incp + np


def test_wild_null_path() -> None:
    items = [
        ("a.b.c", "d"),
        ("a.c[z=www].d.e", "f"),
        ("a.c[z=www].d.g", "h"),
        ("e.f", "g"),
    ]
    for first, second in items:
        assert (
            WildComposedPath(path_str=first) + WildNullPath() + WildComposedPath(path_str=second)
        ).to_str() == first + "." + second

    # Test parsing
    assert isinstance(to_wild_path("."), WildNullPath)
    assert to_wild_path(".").to_str() == "."

    # Test get_elements() on WildNullPath
    np = to_wild_path(".")
    container = {"a": "b", "c": "d"}
    assert np.get_elements(container) == [container]

    np = WildNullPath()
    with pytest.raises(LookupError):
        np.get_elements(None)

    inc = {}
    assert inc is np.get_elements(inc)[0]

    incp = WildComposedPath(path_str="a")

    # Adding to nullpath is a null operation
    assert incp == np + incp, f"{incp} != {np + incp}"
    assert incp == incp + np, f"{np + incp} != {incp}"


@pytest.mark.parametrize(
    "escaped, unescaped",
    [(r"a\.b\=\[\\\*", r"a.b=[\*")],
)
def test_escape_and_un_escape(escaped: str, unescaped: str) -> None:
    """
    Round-trip test of the WildDictPath.escape() and WildDictPath.un_escape() methods.
    """
    dict_path_value = DictPathValue.create(escaped)
    assert dict_path_value.value == unescaped
    assert dict_path_value.escape() == escaped


@pytest.mark.parametrize(
    "dict_path, value_to_parse, expected",
    [
        (r"a.b\.c.d", {"a": {"b.c": {"d": "value"}}}, "value"),
        (r"one\\.two", {"one\\": {"two": "value"}}, "value"),
        (r"a.b\.\[\\c\]", {"a": {r"b.[\c]": "value"}, "b": "other"}, "value"),
        (
            r"a[k\=e\.y=t\[e\]st]",
            {"a": [{"k=e.y": "other", "c": "d"}, {"k=e.y": "t[e]st", "e": "f"}]},
            {"k=e.y": "t[e]st", "e": "f"},
        ),
        (
            r"a[k\.e\[y\]=valu\=e]",
            {"a": [{"k.e[y]": "other", "c": "d"}, {"k.e[y]": "valu=e", "e": "f"}]},
            {"k.e[y]": "valu=e", "e": "f"},
        ),
        (
            r"a[key=\*]",
            {"a": [{"key": "other", "c": "d"}, {"key": "*", "e": "f"}]},
            {"key": "*", "e": "f"},
        ),
        (
            r"\*",
            {"a": "b", "*": "d"},
            "d",
        ),
    ],
)
def test_parsing_special_characters(dict_path: str, value_to_parse: dict, expected: object) -> None:
    """
    End-to-end test to verify whether escape characters are correctly interpreted.
    """
    dp = to_path(dict_path)
    assert dp.get_element(value_to_parse) == expected

    # Verify parsing round trip
    assert ComposedPath(path_str=dict_path).un_parse() == dict_path


def test_wild_composed_path() -> None:
    """
    Test whether the star operator works correctly.
    """
    dict_path_str = "*"
    container = {"a": "b", "c": "d"}
    dp = to_wild_path(dict_path_str)
    assert sorted(dp.get_elements(container)) == sorted([v for v in container.values()])


@pytest.mark.parametrize(
    "dict_path_str, valid_path, relation, key_value_pairs",
    [
        (r"abc[kkk=vvv]", True, NormalValue("abc"), [(NormalValue("kkk"), NormalValue("vvv"))]),
        (r"a\[b\\c[k\=k\*k=v\.v\=v]", True, NormalValue(r"a[b\c"), [(NormalValue("k=k*k"), NormalValue("v.v=v"))]),
        (r"abc\\[kkk=vvv]", True, NormalValue("abc\\"), [(NormalValue("kkk"), NormalValue("vvv"))]),
        (r"abc[=vvv]", False, None, None),
        (r"abc[kkk=]", True, NormalValue("abc"), [(NormalValue("kkk"), NormalValue(""))]),
        (r"abc[=]", False, None, None),
        (r"abc[*=*]", True, NormalValue("abc"), [(WildCardValue(), WildCardValue())]),
        (r"abc[x=*]", True, NormalValue("abc"), [(NormalValue("x"), WildCardValue())]),
        (r"abc[*=y]", True, NormalValue("abc"), [(WildCardValue(), NormalValue("y"))]),
        (r"abc[x=\*]", True, NormalValue("abc"), [(NormalValue("x"), NormalValue("*"))]),
        (r"abc[\*=y]", True, NormalValue("abc"), [(NormalValue("*"), NormalValue("y"))]),
        (r"abc[**=*]", False, None, None),
        (r"abc[*=**]", False, None, None),
        (r"abc[kkk=vvv]test", False, None, None),
        (r"[kkk=vvv]test", False, None, None),
        (r"abc[k.k=vv]", False, None, None),
        (r"test", False, None, None),
        (r"[=]", False, None, None),
        (r"abc\\\[kkk=vvv]test", False, None, None),
        (r"abc[kkkvvv]", False, None, None),
        (r"abc[kk=vvv", False, None, None),
        (r"abc[kkk=\0]", True, NormalValue("abc"), [(NormalValue("kkk"), NullValue())]),
        (r"abc[kkk=\\0]", True, NormalValue("abc"), [(NormalValue("kkk"), NormalValue(r"\0"))]),
        (
            r"abc[k1=v1][k2=v2][k3=v3]",
            True,
            NormalValue("abc"),
            [
                (NormalValue("k1"), NormalValue("v1")),
                (NormalValue("k2"), NormalValue("v2")),
                (NormalValue("k3"), NormalValue("v3")),
            ],
        ),
        (
            r"abc[k1=v1][k2=*][k3=\0]",
            True,
            NormalValue("abc"),
            [(NormalValue("k1"), NormalValue("v1")), (NormalValue("k2"), WildCardValue()), (NormalValue("k3"), NullValue())],
        ),
    ],
)
def test_parsing_keyed_list(
    dict_path_str: str,
    valid_path: bool,
    relation: Optional[DictPathValue],
    key_value_pairs: Optional[Sequence[tuple[Optional[DictPathValue], Optional[DictPathValue]]]],
) -> None:
    """
    Verify whether the KeyedList/WildKeyedList classes correctly parse
    the relation, key_attribute and the key_value from a dict path.
    """
    parsed = WildKeyedList.parse(dict_path_str)
    assert (parsed is not None) == valid_path
    if valid_path:
        assert relation is not None and key_value_pairs is not None
        # Verify parsing round-trip
        assert parsed.to_str() == dict_path_str

        assert parsed.relation == relation
        assert parsed.key_value_pairs == key_value_pairs

        if any(isinstance(v, WildCardValue) for v in chain.from_iterable(key_value_pairs)):
            with pytest.raises(ValueError):
                KeyedList.parse(dict_path_str)
        else:
            parsed_no_wild = KeyedList.parse(dict_path_str)
            assert parsed.relation == parsed_no_wild.relation
            assert parsed.key_value_pairs == parsed_no_wild.key_value_pairs
    else:
        assert KeyedList.parse(dict_path_str) is None


def test_parsing_keyed_list_error() -> None:
    """
    Verify that appropriate errors are raised for invalid key-value combinations.
    """
    with pytest.raises(ValueError, match="No duplicate keys allowed in keyed list path"):
        WildKeyedList.parse("list[key=v1][key=v2]")


@pytest.mark.parametrize(
    "dict_path_str, valid_path, key",
    [
        (r"abc", True, NormalValue(r"abc")),
        (r"abc\.def", True, NormalValue(r"abc.def")),
        (r"abc\\\.def", True, NormalValue(r"abc\.def")),
        (r"*", True, WildCardValue()),
        (r"\*", True, NormalValue("*")),
        (r"**", False, None),
        (r"a\[b\=c\.d\*e\]f", True, NormalValue(r"a[b=c.d*e]f")),
        (r"abc.def", False, None),
        (r"abc\\.def", False, None),
        (r"abc*def", False, None),
    ],
)
def test_parsing_in_dict(dict_path_str: str, valid_path: bool, key: Optional[DictPathValue]) -> None:
    """
    Verify whether the WildInDict/InDict classes correctly parse a dict path.
    """
    parsed = WildInDict.parse(dict_path_str)
    assert (parsed is not None) == valid_path
    if valid_path:
        # Verify parsing round-trip
        assert parsed.to_str() == dict_path_str
        assert parsed.key == key

        if isinstance(parsed.key, WildCardValue):
            with pytest.raises(ValueError):
                InDict.parse(dict_path_str)
        else:
            assert InDict.parse(dict_path_str) is not None


WILD_PATH_TEST_CONTAINER = {
    "one": 1,
    "two": 2,
    "mylist": [
        {
            "k1": 0,
            "k2": 0,
            "nested": {
                "value": 10,
            },
        },
        {
            "k1": 0,
            "k2": 1,
            "nested": {
                "value": 20,
            },
        },
        {
            "k1": 1,
            "k2": 0,
            "nested": {
                "value": 30,
            },
        },
    ],
    "special_list": [
        {
            "key": None,
            "value": "null",
        },
        {
            "key": "None",
            "value": "just-a-string",
        },
        {
            "key": r"\0",
            "value": r"literal \0",
        },
        {
            "key": "0",
            "value": "number 0",
        },
    ],
    3.0: "float key 3.0",
    4: "int key 4",
    "mixed_list": [
        {"key": 5.0, "value": "float key 5.0"},
        {"key": 6, "value": "int key 6"},
    ],
    "7.0": "str key 7.0",
    "8": "str key 8",
    "mixed_list_str": [
        {"key": "9.0", "value": "str key 9.0"},
        {"key": "10", "value": "str key 10"},
    ],
}


@pytest.mark.parametrize_any("wild_path", [True, False])  # verify consistent behavior for both types
@pytest.mark.parametrize(
    "container, dict_path, result, wild_only",
    [
        (None, "one", [1], False),
        (None, "two", [2], False),
        (None, "doesnotexist", [], False),
        ({"x": 1, "y": 2}, "*", [1, 2], True),
        (None, "mylist[k1=1]", [{"k1": 1, "k2": 0, "nested": {"value": 30}}], False),
        (None, "mylist[k1=0].nested.value", [10, 20], True),
        (None, "mylist[k1=0][k2=0]", [{"k1": 0, "k2": 0, "nested": {"value": 10}}], False),
        (None, "mylist[k1=0][k2=0].nested.value", [10], False),
        (None, "mylist[*=*].nested", [{"value": x} for x in (10, 20, 30)], True),
        (None, "*", list(WILD_PATH_TEST_CONTAINER.values()), True),
        (None, r"special_list[key=\0].value", ["null"], False),
        (None, "special_list[key=None].value", ["just-a-string"], False),
        (None, r"special_list[key=\\0].value", [r"literal \0"], False),
        (None, "special_list[key=0].value", ["number 0"], False),
        (None, "3", ["float key 3.0"], False),
        (None, "4", ["int key 4"], False),
        (None, r"3\.0", ["float key 3.0"], False),
        (None, r"4\.0", ["int key 4"], False),
        (None, "mixed_list[key=5]", [{"key": 5.0, "value": "float key 5.0"}], False),
        (None, "mixed_list[key=6]", [{"key": 6, "value": "int key 6"}], False),
        (None, r"mixed_list[key=5\.0]", [{"key": 5.0, "value": "float key 5.0"}], False),
        (None, r"mixed_list[key=6\.0]", [{"key": 6, "value": "int key 6"}], False),
        (None, r"7\.0", ["str key 7.0"], False),
        (None, "7", [], False),
        (None, r"8\.0", [], False),
        (None, "8", ["str key 8"], False),
        (None, r"mixed_list_str[key=9\.0]", [{"key": "9.0", "value": "str key 9.0"}], False),
        (None, r"mixed_list_str[key=9]", [], False),
        (None, r"mixed_list_str[key=10\.0]", [], False),
        (None, r"mixed_list_str[key=10]", [{"key": "10", "value": "str key 10"}], False),
    ],
)
def test_dict_path_get_elements(
    wild_path: bool,
    container: Optional[object],
    dict_path: str,
    result: object,
    wild_only: bool,
) -> None:
    """
    Verify the selection behavior of the dict path library. For non-wild dict paths, additionally when the result is non-empty,
    verify that `construct=True` does not modify the object and returns the expected result.

    :param wild_path: Whether or not to use the wildcard-enabled dict path objects.
    :param container: The container to use as input. If None, WILD_PATH_TEST_CONTAINER is used.
    :param dict_path: The dict path expression to use.
    :param result: The expected result of calling `get_elements`.
    :param wild_only: True iff this expression requires wildcards enabled, in which case the `wild_path` parameter will be
        ignored.
    """
    use_wild: bool = wild_path or wild_only
    container_copy: object = copy.deepcopy(container if container is not None else WILD_PATH_TEST_CONTAINER)
    if use_wild:
        assert to_wild_path(dict_path).get_elements(container_copy) == result
    else:
        dict_path_obj: DictPath = to_path(dict_path)
        assert dict_path_obj.get_elements(container_copy) == result
        if result:
            assert dict_path_obj.get_element(container_copy, construct=True) == result[0]
        else:
            with pytest.raises(LookupError):
                dict_path_obj.get_element(container_copy, construct=False)
    assert container_copy == (container if container is not None else WILD_PATH_TEST_CONTAINER)


@pytest.mark.parametrize(
    ("wild_path", "dict_paths"),
    [
        (".", ["."]),
        (".*", list(str(InDict(str(k))) for k in WILD_PATH_TEST_CONTAINER.keys())),
        ("mylist[k1=*][k2=*]", ["mylist[k1=0][k2=0]", "mylist[k1=0][k2=1]", "mylist[k1=1][k2=0]"]),
        (
            "mylist[k1=*][k2=*].nested.value",
            ["mylist[k1=0][k2=0].nested.value", "mylist[k1=0][k2=1].nested.value", "mylist[k1=1][k2=0].nested.value"],
        ),
    ],
)
def test_dict_path_get_paths(
    wild_path: str,
    dict_paths: list[str],
) -> None:
    """ """
    container_copy: object = copy.deepcopy(WILD_PATH_TEST_CONTAINER)
    all_paths = to_wild_path(wild_path).get_paths(container_copy)
    assert {str(p) for p in all_paths} == set(dict_paths)


@pytest.mark.parametrize(
    "container, dict_path, result",
    [
        (None, "three", {**WILD_PATH_TEST_CONTAINER, "three": {}}),
        (None, "three.nested.values", {**WILD_PATH_TEST_CONTAINER, "three": {"nested": {"values": {}}}}),
        ({"l": [{"k": 1, "v": 1}, {"k": 2, "v": 2}]}, "l[k=1].new", {"l": [{"k": 1, "v": 1, "new": {}}, {"k": 2, "v": 2}]}),
        ({"l": [{"k": 1}]}, "l[k=1].new[k=10]", {"l": [{"k": 1, "new": [{"k": "10"}]}]}),
        ({"l": [{"k": 1}]}, "l[k=1].new[k=10][k2=20].field", {"l": [{"k": 1, "new": [{"k": "10", "k2": "20", "field": {}}]}]}),
    ],
)
def test_dict_path_get_element_construct(container: Optional[object], dict_path: str, result: Optional[object]) -> None:
    """
    Verify the get_element behavior of non-wildcard enabled dict paths when construct=True.

    :param container: The container to use as input. Will not be modified. If None, WILD_PATH_TEST_CONTAINER is used.
    :param dict_path: The dict path expression to use.
    :param result: The expected resulting object, i.e. the object after construction side effects. If None, the object is
        expected to remain unchanged.
    """
    container_copy: object = copy.deepcopy(container if container is not None else WILD_PATH_TEST_CONTAINER)
    to_path(dict_path).get_element(container_copy, construct=True)
    assert container_copy == result if result is not None else container if container is not None else WILD_PATH_TEST_CONTAINER


def test_keyed_list_deprecated_constructor(caplog) -> None:
    """
    Verify that the deprecated constructor for KeyedList and WildKeyedList still works as expected (for backwards compatibility)
    and raises a deprecation warning.
    """

    def assert_warning(class_name: str, expect_warning: bool) -> None:
        msg: str = (
            f"The {class_name}(relation: str, key_attribute: str, key_value: str, /) constructor is deprecated and will be"
            f" removed in a future version. Please use {class_name}(relation: str, key_value_pairs: Sequence[Tuple[str, str]])"
            " instead"
        )
        found: bool = any(
            "inmanta.util.dict_path" in logger_name and log_level == logging.WARNING and msg in message
            for logger_name, log_level, message in caplog.record_tuples
        )
        assert found == expect_warning

    with caplog.at_level(logging.WARNING):
        caplog.clear()
        wild = WildKeyedList("a", "key", "value")
        assert_warning("WildKeyedList", expect_warning=True)

        caplog.clear()
        normal = KeyedList("a", "key", "value")
        assert_warning("KeyedList", expect_warning=True)

        caplog.clear()
        assert wild == WildKeyedList("a", [("key", "value")])
        assert normal == KeyedList("a", [("key", "value")])
        assert_warning("WildKeyedList", expect_warning=False)
        assert_warning("KeyedList", expect_warning=False)
