"""
    Copyright 2018 Inmanta

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

import numbers
import typing as py_type

import inmanta.ast.type as inm_type


def type_corresponds(
    it: inm_type.Type, does_correspond: py_type.Sequence[py_type.Type], does_not_correspond: py_type.Sequence[py_type.Type]
) -> None:
    """
    Test a set of positive and negative examples for a given inmanta type
    Also test optional variations
    """

    for pyt in does_correspond:
        assert it.corresponds_to(pyt)
        assert inm_type.NullableType(it).corresponds_to(pyt | None)

    for pyt in does_not_correspond:
        assert not it.corresponds_to(pyt)
        assert not inm_type.NullableType(it).corresponds_to(pyt | None)


def test_type_correspondence():
    """
    Test type correspondence between python and inmanta domain

    This code is tricky, untypable and cheap to test, so we test a lot

    We work based on test sets, that can be made into variations for optional types
    """

    # Dict types, test using positive/negative sets
    never_supported_collection = [int, py_type.Union[list[int], dict[str, int]], dict[int, object]]
    never_dict = [list] + never_supported_collection

    # Dicts
    plain_dict = inm_type.Dict()
    type_corresponds(
        plain_dict,
        [dict, dict[str, int], dict[str, object], dict[str, list[list[list[str]]]]],
        never_dict,
    )

    typed_dict = inm_type.TypedDict(inm_type.Integer())
    type_corresponds(
        typed_dict,
        [dict, dict[str, int]],
        [dict[str, object], dict[str, list[list[list[str]]]]] + never_dict,
    )

    lang_dict = inm_type.LiteralDict()
    type_corresponds(
        lang_dict,
        [dict, dict[str, int], dict[str, list[list[list[str]]]]],
        [dict[str, object]] + never_dict,
    )

    # Lists
    never_list = [dict] + never_supported_collection
    plain_list = inm_type.List()
    type_corresponds(plain_list, [list, list[str], list[int], list[object]], never_list)

    typed_list = inm_type.TypedList(inm_type.Integer())
    type_corresponds(typed_list, [list, list[int]], [list[str], list[object]] + never_list)

    lang_list = inm_type.LiteralList()
    type_corresponds(lang_list, [list, list[str], list[int]], [list[object]] + never_list)

    # Primtive cross check:
    # Have pairs of inmanta-python types that correspond, but not with any of the others
    primitive_types = [
        (inm_type.Integer(), int),
        (inm_type.String(), str),
        (inm_type.Float(), float),
        (inm_type.Bool(), bool),
    ]
    for it, pyt in primitive_types:
        for oit, opyt in primitive_types:
            if it is oit:
                assert it.corresponds_to(pyt)
            else:
                assert not it.corresponds_to(opyt)

    # Number
    inm_number = inm_type.Number()
    assert inm_number.corresponds_to(int)
    assert inm_number.corresponds_to(float)
    assert inm_number.corresponds_to(numbers.Number)
    assert not inm_number.corresponds_to(str)
