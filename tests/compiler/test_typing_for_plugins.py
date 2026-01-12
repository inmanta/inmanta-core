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

import inspect
import numbers
import typing as py_type
from typing import Sequence

import inmanta.ast.type as inm_type
import utils
from inmanta import plugins
from inmanta.ast import Namespace, Range, TypingException, statements
from inmanta.ast.entity import Entity, Implementation
from inmanta.ast.type import (
    Any,
    Bool,
    ConstraintType,
    Float,
    Integer,
    Null,
    NullableType,
    OrReferenceType,
    ReferenceType,
    String,
    TypedDict,
    TypedList,
    Union,
)
from inmanta.plugins import Plugin, UnConvertibleEntity, to_dsl_type
from inmanta.references import Reference

namespace = Namespace("dummy-namespace")
namespace.primitives = inm_type.TYPES

location: Range = Range("test", 1, 1, 2, 1)


def to_dsl_type_simple(python_type: type[object]) -> inm_type.Type:
    return to_dsl_type(python_type, location, namespace)


def type_corresponds(
    it: inm_type.Type, does_correspond: py_type.Sequence[py_type.Type], does_not_correspond: py_type.Sequence[py_type.Type]
) -> None:
    """
    Test a set of positive and negative examples for a given inmanta type
    Also test optional variations
    """

    for pyt in does_correspond:
        tp = to_dsl_type_simple(pyt)
        assert it.corresponds_to(tp)
        assert inm_type.NullableType(it).corresponds_to(inm_type.NullableType(tp))
    for pyt in does_not_correspond:
        try:
            tp = to_dsl_type_simple(pyt)
        except TypingException:
            # type is invalid
            continue
        assert not it.corresponds_to(tp)
        assert not inm_type.NullableType(it).corresponds_to(inm_type.NullableType(tp))


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
        [dict, dict[str, int], dict[str, object]],
        [dict[str, list[list[list[str]]]]] + never_dict,
    )

    lang_dict = inm_type.LiteralDict()
    type_corresponds(
        lang_dict,
        [dict, dict[str, int], dict[str, list[list[list[str]]]], dict[str, object]],
        never_dict,
    )

    # Lists
    never_list = [dict] + never_supported_collection
    plain_list = inm_type.List()
    type_corresponds(plain_list, [list, list[str], list[int], list[object]], never_list)

    typed_list = inm_type.TypedList(inm_type.Integer())
    type_corresponds(typed_list, [list[int], list[object]], [list, list[str]] + never_list)

    lang_list = inm_type.LiteralList()
    type_corresponds(lang_list, [list[str], list[int], list[object]], [list] + never_list)

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
                assert it.corresponds_to(to_dsl_type_simple(pyt))
            else:
                assert not it.corresponds_to(to_dsl_type_simple(opyt))

    # Number
    inm_number = inm_type.Number()
    assert inm_number.corresponds_to(to_dsl_type_simple(int))
    assert inm_number.corresponds_to(to_dsl_type_simple(float))
    assert inm_number.corresponds_to(to_dsl_type_simple(numbers.Number))
    assert not inm_number.corresponds_to(to_dsl_type_simple(str))

    # Reference
    assert ReferenceType(String()).corresponds_to(to_dsl_type_simple(Reference[str]))
    assert OrReferenceType(String()).corresponds_to(to_dsl_type_simple(Reference[str] | str))
    assert not ReferenceType(String()).corresponds_to(OrReferenceType(String()))
    assert not OrReferenceType(String()).corresponds_to(ReferenceType(String()))
    assert not OrReferenceType(String()).corresponds_to(to_dsl_type_simple(Reference[str] | int))


def make_typedef(
    name: str, base_type: inm_type.Type, constraint: statements.ExpressionStatement | None = None
) -> ConstraintType:
    tp = ConstraintType(Namespace("mymodule", parent=Namespace("__root__")), name)
    tp.basetype = base_type
    tp.constraint = (
        constraint
        if constraint is not None
        # typedef <name> as <base_type> matching true
        else statements.Literal(True)
    )
    return tp


def test_type_utility_methods() -> None:

    def check_type(intypes: list[inm_type.Type], is_attr: bool, custom_to_python: bool):
        for intype in intypes:
            # Basic type compare
            assert intype.issubtype(Any())

            try:
                assert isinstance(intype, Any) or not intype.issupertype(Any())
            except NotImplementedError:
                # Valid response
                pass
            # Ensure we are not stuck in an infinite loop
            intype.get_no_reference()
            intype.get_base_type()
            # Make sure the recursive ones work
            assert intype.is_attribute_type() == is_attr, f"{intype}, is attribute expected {is_attr}"
            assert intype.has_custom_to_python() == custom_to_python

    primitives: list[inm_type.Type] = [Bool(), Integer(), Float(), String()]

    check_type(primitives, True, False)
    check_type([NullableType(primitive) for primitive in primitives], True, False)
    check_type([Union(primitives)], True, False)
    check_type([NullableType(Union(primitives))], True, False)
    check_type([Any()], False, False)
    check_type([TypedList(primitive) for primitive in primitives], True, False)
    check_type([TypedDict(primitive) for primitive in primitives], False, False)
    check_type([Null()], False, False)
    check_type([inm_type.ReferenceType(Bool()), inm_type.OrReferenceType(Bool())], True, False)
    dataclass_ref = inm_type.ReferenceType(Bool())
    dataclass_ref.is_dataclass = True  # mock a dataclass reference
    dataclass_ref_union = inm_type.OrReferenceType(Bool())
    dataclass_ref_union.reference_type.is_dataclass = True  # mock a dataclass reference union
    check_type([dataclass_ref, dataclass_ref_union], True, True)  # not real dataclasses => still attr type
    check_type(
        [
            inm_type.Number(),
            inm_type.LiteralList(),
            inm_type.LiteralDict(),
            inm_type.Literal(),
        ],
        True,
        False,
    )

    check_type(
        [
            inm_type.List(),
            inm_type.Dict(),
        ],
        False,
        False,
    )


def test_issubtype_of_own_python_type() -> None:
    """
    Verify round-trip compatibility of tp.issubtype(to_dsl_type(tp.as_python_type_string()))
    """
    verified_types: set[type[inm_type.Type]] = set()

    primitives: Sequence[inm_type.Type] = [Bool(), Integer(), Float(), String()]
    for tp in [
        *primitives,
        *[NullableType(primitive) for primitive in primitives],
        *[make_typedef("mytype", primitive) for primitive in primitives],
        Union(primitives),
        NullableType(Union(primitives)),
        Any(),
        *[TypedList(primitive) for primitive in primitives],
        *[TypedDict(primitive) for primitive in primitives],
        plugins.Null(),
        inm_type.ReferenceType(Bool()),
        inm_type.OrReferenceType(Bool()),
        inm_type.Number(),
        inm_type.List(),
        inm_type.LiteralList(),
        inm_type.LiteralDict(),
        inm_type.Dict(),
        inm_type.Literal(),
        # Entity("test", Namespace("__root__"), ""), TODO: too complex to set up for now
    ]:
        rt_ed = to_dsl_type_simple(eval(tp.as_python_type_string()))
        # Round trip makes the type less strict
        assert tp.issubtype(rt_ed)
        verified_types.add(type(tp))

    all_types = {
        tp_cls
        for tp_cls in utils.get_all_subclasses(inm_type.Type)
        if not inspect.isabstract(tp_cls) and not issubclass(tp_cls, Plugin)
    }
    except_types = {
        Plugin,  # not relevant
        inm_type.NamedType,  # abstract
        inm_type.Primitive,  # abstract
        inm_type.Type,  # abstract
        Implementation,  # not relevant
        UnConvertibleEntity,  # TODO
        Entity,  # TODO
    }
    assert verified_types == all_types - except_types


def test_issubtype_widening() -> None:
    """
    Verify issubtype accepts wider types and rejects narrower or unrelated ones.
    """

    def verify(narrow: inm_type.Type, wide: inm_type.Type) -> None:
        assert narrow.issubtype(wide)
        assert not wide.issubtype(narrow)

    verify(Integer(), Union([Integer(), String()]))
    verify(Integer(), NullableType(Integer()))
    verify(Integer(), Any())

    assert not Integer().issubtype(String())

    verify(plugins.Null(), NullableType(Integer()))

    verify(Union([Integer(), String()]), Union([Integer(), TypedList(Float()), String()]))
    verify(Union([Integer(), String()]), Any())

    verify(make_typedef("mytype", Integer()), Integer())
    verify(make_typedef("mytype", Integer()), NullableType(Integer()))
    verify(make_typedef("mytype", Integer()), Union([Integer(), String()]))
    verify(make_typedef("mytype", Integer()), Any())
    assert not make_typedef("mytype", Integer()).issubtype(String())
    assert not make_typedef("mytype", Integer()).issubtype(make_typedef("othertype", Integer()))

    namespace = Namespace("dummy_namespace")
    entity: Entity = Entity("DummyEntity", namespace)
    sub_entity: Entity = Entity("DummyEntitySub", namespace)

    entity.child_entities.append(sub_entity)
    sub_entity.parent_entities.append(entity)

    assert sub_entity.is_subclass(entity)
    assert not entity.is_subclass(sub_entity)
    assert not entity.issubtype(sub_entity)

    verify(sub_entity, entity)
    verify(sub_entity, Any())

    assert not entity.issubtype(Integer())
    assert not Integer().issubtype(entity)


def test_issubtype_references() -> None:
    """
    Verify that issubtype works as expected with Reference and OrReference types.
    """
    # internal representation of a `string[]?` attribute type
    or_ref_list = OrReferenceType(NullableType(TypedList(OrReferenceType(String()))))
    plain_list = NullableType(TypedList(String()))
    # reference type as constructed for dataclass attributes in Entity.from_python
    plain_list_ref = ReferenceType(plain_list)
    assert plain_list.issubtype(or_ref_list)
    assert plain_list_ref.issubtype(or_ref_list)
