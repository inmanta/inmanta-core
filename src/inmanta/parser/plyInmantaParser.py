"""
    Copyright 2017 Inmanta

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

import logging
import re
from typing import List, Optional, Tuple, Union

import ply.yacc as yacc
from ply.yacc import YaccProduction

import inmanta.warnings as inmanta_warnings
from inmanta.ast import LocatableString, Location, Namespace, Range
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.constraint.expression import IsDefined, Not, Operator
from inmanta.ast.statements import Literal, Statement
from inmanta.ast.statements.assign import CreateDict, CreateList, IndexLookup, MapLookup, ShortIndexLookup, StringFormat
from inmanta.ast.statements.call import FunctionCall
from inmanta.ast.statements.define import (
    DefineAttribute,
    DefineEntity,
    DefineImplement,
    DefineImplementation,
    DefineImport,
    DefineIndex,
    DefineRelation,
    DefineTypeConstraint,
    DefineTypeDefault,
    TypeDeclaration,
)
from inmanta.ast.statements.generator import ConditionalExpression, Constructor, For, If, WrappedKwargs
from inmanta.ast.variables import AttributeReference, Reference
from inmanta.execute.util import NoneValue
from inmanta.parser import ParserException, SyntaxDeprecationWarning, plyInmantaLex
from inmanta.parser.cache import CacheManager
from inmanta.parser.plyInmantaLex import reserved, tokens  # NOQA

# the token map is imported from the lexer. This is required.

LOGGER = logging.getLogger()


file = "NOFILE"
namespace = None

precedence = (
    ("right", ","),
    ("nonassoc", ":"),
    ("nonassoc", "?"),
    ("left", "OR"),
    ("left", "AND"),
    ("left", "CMP_OP"),
    ("nonassoc", "NOT"),
    ("left", "IN"),
    ("right", "MLS"),
    ("right", "MLS_END"),
)


def attach_lnr(p: YaccProduction, token: int = 1) -> None:
    v = p[0]
    v.location = Location(file, p.lineno(token))
    v.namespace = namespace
    v.lexpos = p.lexpos(token)


def merge_lnr_to_string(p: YaccProduction, starttoken: int = 1, endtoken: int = 2) -> None:
    v = p[0]

    et = p[endtoken]
    endline = et.elnr
    endchar = et.end

    st = p[starttoken]
    if isinstance(st, LocatableString):
        startline = st.lnr
        startchar = st.start
    else:
        startline = et.lnr
        startchar = et.start

    p[0] = LocatableString(v, Range(file, startline, startchar, endline, endchar), endchar, namespace)


def attach_from_string(p: YaccProduction, token: int = 1) -> None:
    v = p[0]
    v.location = p[token].location
    v.namespace = p[token].namespace


def make_none(p: YaccProduction, token: int) -> Literal:
    none = Literal(NoneValue())
    none.location = Location(file, p.lineno(token))
    none.namespace = namespace
    none.lexpos = p.lexpos(token)
    return none


def p_main_collect(p: YaccProduction) -> None:
    "main : top_stmt main"
    v = p[2]
    v.insert(0, p[1])
    p[0] = v


def p_main_term(p: YaccProduction) -> None:
    "main : empty"
    p[0] = []


def p_top_stmt(p: YaccProduction) -> None:
    """top_stmt : mls
    | entity_def
    | implement_def
    | implementation_def
    | relation
    | statement
    | typedef
    | index
    | import"""
    p[0] = p[1]


def p_empty(p: YaccProduction) -> None:
    "empty : "
    pass


#######################
# IMPORT
#######################


def p_import(p: YaccProduction) -> None:
    """import : IMPORT ns_ref"""
    p[0] = DefineImport(str(p[2]), str(p[2]))
    attach_lnr(p, 1)


def p_import_1(p: YaccProduction) -> None:
    """import : IMPORT ns_ref AS ID"""
    p[0] = DefineImport(str(p[2]), p[4])
    attach_lnr(p, 1)


#######################
# STMTS
#######################


def p_stmt(p: YaccProduction) -> None:
    """statement : assign
    | constructor
    | function_call
    | for
    | if"""
    p[0] = p[1]


# def p_stmt_err(p):
#     '''statement : list_def
#               | map_def
#               | var_ref
#               | index_lookup'''
#     raise ParserException(file, p[1].location.lnr, lexer.lexpos, "",
#                           msg="expressions are not valid statements, assign this value to a variable to fix this error")


def p_stmt_list_collect(p: YaccProduction) -> None:
    """stmt_list : statement stmt_list"""
    v = p[2]
    v.append(p[1])
    p[0] = v


def p_stmt_list_empty(p: YaccProduction) -> None:
    "stmt_list : empty"
    p[0] = []


def p_assign(p: YaccProduction) -> None:
    "assign : var_ref '=' operand"
    p[0] = p[1].as_assign(p[3])
    attach_lnr(p, 2)


def p_assign_extend(p: YaccProduction) -> None:
    "assign : var_ref PEQ operand"
    p[0] = p[1].as_assign(p[3], list_only=True)
    attach_lnr(p, 2)


def p_for(p: YaccProduction) -> None:
    "for : FOR ID IN operand ':' block"
    p[0] = For(p[4], p[2], BasicBlock(namespace, p[6]))
    attach_lnr(p, 1)


def p_if(p: YaccProduction) -> None:
    "if : IF expression ':' block"
    p[0] = If(p[2], BasicBlock(namespace, p[4]), BasicBlock(namespace, []))
    attach_lnr(p, 1)


def p_if_else(p: YaccProduction) -> None:
    "if : IF expression ':' stmt_list ELSE ':' block"
    p[0] = If(p[2], BasicBlock(namespace, p[4]), BasicBlock(namespace, p[7]))
    attach_lnr(p, 1)


#######################
# DEFINITIONS
#######################


def p_entity(p: YaccProduction) -> None:
    "entity_def : ENTITY CID ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[4][0], [], p[4][1])
    attach_lnr(p)


def p_entity_err_1(p: YaccProduction) -> None:
    "entity_def : ENTITY ID ':' entity_body_outer "
    raise ParserException(p[2].location, str(p[2]), "Invalid identifier: Entity names must start with a capital")


def p_entity_extends(p: YaccProduction) -> None:
    "entity_def : ENTITY CID EXTENDS class_ref_list ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[6][0], p[4], p[6][1])
    attach_lnr(p)


def p_entity_extends_err(p: YaccProduction) -> None:
    "entity_def : ENTITY ID EXTENDS class_ref_list ':' entity_body_outer "
    raise ParserException(p[2].location, str(p[2]), "Invalid identifier: Entity names must start with a capital")


def p_entity_body_outer(p: YaccProduction) -> None:
    """entity_body_outer : mls entity_body END"""
    p[0] = (p[1], p[2])


def p_entity_body_outer_1(p: YaccProduction) -> None:
    """entity_body_outer : entity_body END """
    p[0] = (None, p[1])


def p_entity_body_outer_none(p: YaccProduction) -> None:
    """entity_body_outer : END """
    p[0] = (None, [])


def p_entity_body_outer_4(p: YaccProduction) -> None:
    """entity_body_outer : mls END"""
    p[0] = (p[1], [])


def p_entity_body_collect(p: YaccProduction) -> None:
    """ entity_body : entity_body attr"""
    p[1].append(p[2])
    p[0] = p[1]


def p_entity_body(p: YaccProduction) -> None:
    """ entity_body : attr"""
    p[0] = [p[1]]


def p_attribute_base_type(p: YaccProduction) -> None:
    """attr_base_type : ns_ref"""
    p[0] = TypeDeclaration(p[1])
    attach_from_string(p, 1)


def p_attribute_type_multi(p: YaccProduction) -> None:
    """attr_type_multi : attr_base_type '[' ']'"""
    p[1].multi = True
    p[0] = p[1]


def p_attribute_type_opt(p: YaccProduction) -> None:
    """attr_type_opt : attr_type_multi '?'
    | attr_base_type '?'"""
    p[1].nullable = True
    p[0] = p[1]


def p_attribute_type(p: YaccProduction) -> None:
    """attr_type : attr_type_opt
    | attr_type_multi
    | attr_base_type"""
    p[0] = p[1]


def p_attr(p: YaccProduction) -> None:
    "attr : attr_type ID"
    p[0] = DefineAttribute(p[1], p[2], None)
    attach_from_string(p, 2)


def p_attr_cte(p: YaccProduction) -> None:
    """attr : attr_type ID '=' constant
    | attr_type ID '=' constant_list"""
    p[0] = DefineAttribute(p[1], p[2], p[4])
    attach_from_string(p, 2)


def p_attr_undef(p: YaccProduction) -> None:
    "attr : attr_type ID '=' UNDEF"
    p[0] = DefineAttribute(p[1], p[2], None, remove_default=True)
    attach_from_string(p, 2)


def p_attr_dict(p: YaccProduction) -> None:
    "attr : DICT ID"
    p[0] = DefineAttribute(TypeDeclaration(p[1]), p[2], None)
    attach_from_string(p, 2)


def p_attr_list_dict(p: YaccProduction) -> None:
    "attr : DICT ID '=' map_def"
    p[0] = DefineAttribute(TypeDeclaration(p[1]), p[2], p[4])
    attach_from_string(p, 2)


def p_attr_list_dict_null_err(p: YaccProduction) -> None:
    "attr : DICT ID '=' NULL"
    raise ParserException(p[2].location, str(p[2]), 'null can not be assigned to dict, did you mean "dict? %s = null"' % p[2])


def p_attr_dict_nullable(p: YaccProduction) -> None:
    "attr : DICT '?' ID"
    p[0] = DefineAttribute(TypeDeclaration(p[1], nullable=True), p[3], None)
    attach_from_string(p, 3)


def p_attr_list_dict_nullable(p: YaccProduction) -> None:
    "attr : DICT '?'  ID '=' map_def"
    p[0] = DefineAttribute(TypeDeclaration(p[1], nullable=True), p[3], p[5])
    attach_from_string(p, 3)


def p_attr_list_dict_null(p: YaccProduction) -> None:
    "attr : DICT '?'  ID '=' NULL"
    p[0] = DefineAttribute(TypeDeclaration(p[1], nullable=True), p[3], make_none(p, 5))
    attach_from_string(p, 3)


# IMPLEMENT
def p_implement_ns_list_ref(p: YaccProduction) -> None:
    "implement_ns_list : ns_ref"
    p[0] = (False, [p[1]])


def p_implement_ns_list_parents(p: YaccProduction) -> None:
    "implement_ns_list : PARENTS"
    p[0] = (True, [])


def p_implement_ns_list_collect(p: YaccProduction) -> None:
    "implement_ns_list : implement_ns_list ',' implement_ns_list"
    p[0] = (p[1][0] or p[3][0], p[1][1] + p[3][1])


def p_implement(p: YaccProduction) -> None:
    """implement_def : IMPLEMENT class_ref USING implement_ns_list empty
    | IMPLEMENT class_ref USING implement_ns_list mls"""
    (inherit, implementations) = p[4]
    p[0] = DefineImplement(p[2], implementations, Literal(True), inherit=inherit, comment=p[5])
    attach_lnr(p)


def p_implement_when(p: YaccProduction) -> None:
    """implement_def : IMPLEMENT class_ref USING implement_ns_list WHEN expression empty
    | IMPLEMENT class_ref USING implement_ns_list WHEN expression mls"""
    (inherit, implementations) = p[4]
    p[0] = DefineImplement(p[2], implementations, p[6], inherit=inherit, comment=p[7])
    attach_lnr(p)


# IMPLEMENTATION


def p_implementation_def(p: YaccProduction) -> None:
    "implementation_def : IMPLEMENTATION ID FOR class_ref implementation"
    docstr, stmts = p[5]
    p[0] = DefineImplementation(namespace, p[2], p[4], BasicBlock(namespace, stmts), docstr)


# def p_implementation_def_2(p):
#     "implementation_def : IMPLEMENTATION ID implementation"
#     p[0] = DefineImplementation(namespace, p[2], None, BasicBlock(namespace, p[3]))
#     attach_lnr(p)


def p_implementation(p: YaccProduction) -> None:
    "implementation : ':' mls block"
    p[0] = (p[2], p[3])


def p_implementation_1(p: YaccProduction) -> None:
    "implementation : ':' block"
    p[0] = (None, p[2])


def p_block(p: YaccProduction) -> None:
    "block : stmt_list END"
    p[0] = p[1]


# RELATION
def p_relation_deprecated(p: YaccProduction) -> None:
    "relation : class_ref ID multi REL multi class_ref ID"
    if not (p[4] == "--"):
        LOGGER.warning(
            "DEPRECATION: use of %s in relation definition is deprecated, use -- (in %s)" % (p[4], Location(file, p.lineno(4)))
        )
    p[0] = DefineRelation((p[1], p[2], p[3]), (p[6], p[7], p[5]))
    attach_lnr(p, 2)
    deprecated_relation_warning(p)


def p_relation_deprecated_comment(p: YaccProduction) -> None:
    "relation : class_ref ID multi REL multi class_ref ID mls"
    if not (p[4] == "--"):
        LOGGER.warning(
            "DEPRECATION: use of %s in relation definition is deprecated, use -- (in %s)" % (p[4], Location(file, p.lineno(4)))
        )
    rel = DefineRelation((p[1], p[2], p[3]), (p[6], p[7], p[5]))
    rel.comment = str(p[8])
    p[0] = rel
    attach_lnr(p, 2)
    deprecated_relation_warning(p)


def deprecated_relation_warning(p: YaccProduction) -> None:
    def format_multi(multi: Tuple[int, Optional[int]]) -> str:
        values: Tuple[str, str] = tuple(v if v is not None else "" for v in multi)
        return "[%s:%s]" % values if values[0] != values[1] else "[%s]" % values[0]

    inmanta_warnings.warn(
        SyntaxDeprecationWarning(
            p[0].location,
            None,
            "The relation definition syntax"
            " `{entity_left} {attr_left_on_right} {multi_left} {rel} {multi_right} {entity_right} {attr_right_on_left}`"
            " is deprecated. Please use"
            " `{entity_left}.{attr_right_on_left} {multi_right} -- {entity_right}.{attr_left_on_right} {multi_left}`"
            " instead.".format(
                entity_left=p[1],
                attr_left_on_right=p[2],
                multi_left=format_multi(p[3]),
                rel=p[4],
                multi_right=format_multi(p[5]),
                entity_right=p[6],
                attr_right_on_left=p[7],
            ),
        ),
    )


def p_relation_outer_comment(p: YaccProduction) -> None:
    "relation : relation_def mls"
    rel = p[1]
    rel.comment = str(p[2])
    p[0] = rel


def p_relation_outer(p: YaccProduction) -> None:
    "relation : relation_def"
    p[0] = p[1]


def p_relation(p: YaccProduction) -> None:
    "relation_def : class_ref '.' ID multi REL class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_unidir(p: YaccProduction) -> None:
    "relation_def : class_ref '.' ID multi REL class_ref"
    p[0] = DefineRelation((p[1], None, None), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_annotated(p: YaccProduction) -> None:
    "relation_def : class_ref '.' ID multi operand_list class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]), p[5])
    attach_lnr(p, 2)


def p_relation_annotated_unidir(p: YaccProduction) -> None:
    "relation_def : class_ref '.' ID multi operand_list class_ref"
    p[0] = DefineRelation((p[1], None, None), (p[6], p[3], p[4]), p[5])
    attach_lnr(p, 2)


def p_multi_1(p: YaccProduction) -> None:
    "multi : '[' INT ']' "
    p[0] = (p[2], p[2])


def p_multi_2(p: YaccProduction) -> None:
    "multi : '[' INT ':' ']' "
    p[0] = (p[2], None)


def p_multi_3(p: YaccProduction) -> None:
    "multi : '[' INT ':' INT ']' "
    p[0] = (p[2], p[4])


def p_multi_4(p: YaccProduction) -> None:
    "multi : '['  ':' INT ']' "
    p[0] = (0, p[3])


# typedef


def p_typedef_outer(p: YaccProduction) -> None:
    """typedef : typedef_inner"""
    p[0] = p[1]


def p_typedef_outer_comment(p: YaccProduction) -> None:
    """typedef : typedef_inner mls"""
    tdef = p[1]
    tdef.comment = str(p[2])
    p[0] = tdef


def p_typedef_1(p: YaccProduction) -> None:
    """typedef_inner : TYPEDEF ID AS ns_ref MATCHING expression"""
    p[0] = DefineTypeConstraint(namespace, p[2], p[4], p[6])
    attach_lnr(p, 2)


def p_typedef_cls(p: YaccProduction) -> None:
    """typedef_inner : TYPEDEF CID AS constructor"""
    p[0] = DefineTypeDefault(namespace, p[2], p[4])
    attach_lnr(p, 2)


# index


def p_index(p: YaccProduction) -> None:
    """index : INDEX class_ref '(' id_list ')' """
    p[0] = DefineIndex(p[2], p[4])
    attach_lnr(p, 1)


#######################
# EXPRESSIONS


def p_expression(p: YaccProduction) -> None:
    """expression : boolean_expression
    | constant
    | function_call
    | var_ref
    | constructor
    | list_def
    | map_def
    | map_lookup
    | index_lookup
    | conditional_expression"""
    p[0] = p[1]


def p_expression_parentheses(p: YaccProduction) -> None:
    """ expression : '(' expression ')' """
    p[0] = p[2]


def p_boolean_expression(p: YaccProduction) -> None:
    """boolean_expression : expression CMP_OP expression
    | expression IN expression
    | expression AND expression
    | expression OR expression"""
    operator = Operator.get_operator_class(str(p[2]))
    if operator is None:
        raise ParserException(p[1].location, str(p[1]), f"Invalid operator {str(p[1])}")
    p[0] = operator(p[1], p[3])
    attach_lnr(p, 2)


def p_boolean_expression_not(p: YaccProduction) -> None:
    """ boolean_expression : NOT expression """
    p[0] = Not(p[2])
    attach_lnr(p)


def p_boolean_expression_is_defined(p: YaccProduction) -> None:
    """ boolean_expression : var_ref '.' ID IS DEFINED"""
    p[0] = IsDefined(p[1], p[3])
    attach_lnr(p, 2)


def p_boolean_expression_is_defined_short(p: YaccProduction) -> None:
    """ boolean_expression : ID IS DEFINED """
    p[0] = IsDefined(None, p[1])
    attach_lnr(p)


def p_operand(p: YaccProduction) -> None:
    """ operand : expression """
    p[0] = p[1]


def p_map_lookup(p: YaccProduction) -> None:
    """map_lookup : attr_ref '[' operand ']'
    | local_var '[' operand ']'
    | map_lookup '[' operand ']'"""
    p[0] = MapLookup(p[1], p[3])


def p_constructor(p: YaccProduction) -> None:
    " constructor : class_ref '(' param_list ')' "
    p[0] = Constructor(p[1], p[3][0], p[3][1], Location(file, p.lineno(2)), namespace)


def p_function_call(p: YaccProduction) -> None:
    " function_call : ns_ref '(' function_param_list ')'"
    (args, kwargs, wrapped_kwargs) = p[3]
    p[0] = FunctionCall(p[1], args, kwargs, wrapped_kwargs, Location(file, p.lineno(2)), namespace)


def p_list_def(p: YaccProduction) -> None:
    " list_def : '[' operand_list ']'"
    p[0] = CreateList(p[2])
    attach_lnr(p, 1)


def p_pair_list_collect(p: YaccProduction) -> None:
    """pair_list : STRING ':' operand ',' pair_list
    | STRING ':' operand empty pair_list_empty"""
    p[5].insert(0, (str(p[1]), p[3]))
    p[0] = p[5]


def p_pair_list_empty(p: YaccProduction) -> None:
    """pair_list : pair_list_empty
    pair_list_empty : empty"""
    p[0] = []


def p_map_def(p: YaccProduction) -> None:
    " map_def : '{' pair_list '}'"
    p[0] = CreateDict(p[2])
    attach_lnr(p, 1)


def p_index_lookup(p: YaccProduction) -> None:
    " index_lookup : class_ref '[' param_list ']'"
    p[0] = IndexLookup(p[1], p[3][0], p[3][1])
    attach_lnr(p, 2)


def p_short_index_lookup(p: YaccProduction) -> None:
    " index_lookup : attr_ref '[' param_list ']'"
    attref = p[1]
    p[0] = ShortIndexLookup(attref.instance, attref.attribute, p[3][0], p[3][1])
    attach_lnr(p, 2)


def p_conditional_expression(p: YaccProduction) -> None:
    " conditional_expression : expression '?' expression ':' expression"
    p[0] = ConditionalExpression(p[1], p[3], p[5])
    attach_from_string(p, 1)


#######################
# HELPERS


def p_constant(p: YaccProduction) -> None:
    """constant : INT
    | FLOAT
    """
    p[0] = Literal(p[1])
    attach_lnr(p)


def p_constant_none(p: YaccProduction) -> None:
    """constant : NULL"""
    p[0] = make_none(p, 1)
    attach_lnr(p)


def p_constant_regex(p: YaccProduction) -> None:
    """constant : REGEX"""
    p[0] = p[1]
    attach_lnr(p)


def p_constant_true(p: YaccProduction) -> None:
    """constant : TRUE"""
    p[0] = Literal(True)
    attach_lnr(p)


def p_constant_false(p: YaccProduction) -> None:
    """constant : FALSE"""
    p[0] = Literal(False)
    attach_lnr(p)


def p_constant_string(p: YaccProduction) -> None:
    " constant : STRING "
    p[0] = get_string_ast_node(p[1], Location(file, p.lineno(1)))
    attach_lnr(p)


def p_constant_rstring(p: YaccProduction) -> None:
    " constant : RSTRING "
    p[0] = Literal(str(p[1]))
    attach_from_string(p)


def p_constant_mls(p: YaccProduction) -> None:
    " constant : mls "
    p[0] = get_string_ast_node(p[1], p[1].location)
    attach_from_string(p)


format_regex = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
format_regex_compiled = re.compile(format_regex, re.MULTILINE | re.DOTALL)


def get_string_ast_node(string: LocatableString, location: Location) -> Union[Literal, StringFormat]:
    match_obj = format_regex_compiled.findall(str(string))
    if len(match_obj) == 0:
        return Literal(str(string))
    return create_string_format(string, match_obj, location)


def create_string_format(format_string: LocatableString, variables: List[List[str]], location: Location) -> StringFormat:
    """
    Create a string interpolation statement
    """
    _vars = []

    for var_str in variables:
        var_parts = var_str[1].split(".")
        ref = Reference(var_parts[0])
        ref.namespace = namespace

        if len(var_parts) > 1:
            for attr in var_parts[1:]:
                ref = AttributeReference(ref, attr)
                ref.location = location
                ref.namespace = namespace
            _vars.append((ref, var_str[0]))
        else:
            _vars.append((ref, var_str[0]))

    return StringFormat(str(format_string), _vars)


def p_constant_list(p: YaccProduction) -> None:
    " constant_list : '[' constants ']' "
    p[0] = CreateList(p[2])
    attach_lnr(p, 1)


def p_constants_term(p: YaccProduction) -> None:
    "constants : constant"
    p[0] = [p[1]]


def p_constants_term_2(p: YaccProduction) -> None:
    "constants : "
    p[0] = []


def p_constants_collect(p: YaccProduction) -> None:
    """constants : constant ',' constants"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_wrapped_kwargs(p: YaccProduction) -> None:
    "wrapped_kwargs : '*' '*' operand"
    p[0] = WrappedKwargs(p[3])


def p_param_list_element_explicit(p: YaccProduction) -> None:
    # param_list_element: Tuple[Optional[Tuple[ID, operand]], Optional[wrapped_kwargs]]
    "param_list_element : ID '=' operand"
    p[0] = ((p[1], p[3]), None)


def p_param_list_element_kwargs(p: YaccProduction) -> None:
    "param_list_element : wrapped_kwargs"
    # param_list_element: Tuple[Optional[Tuple[ID, operand]], Optional[wrapped_kwargs]]
    p[0] = (None, p[1])


def p_param_list_empty(p: YaccProduction) -> None:
    """param_list : param_list_empty
    param_list_empty : empty"""
    # param_list: Tuple[List[Tuple[ID, operand]], List[wrapped_kwargs]]
    p[0] = ([], [])


def p_param_list_nonempty(p: YaccProduction) -> None:
    """param_list : param_list_element empty param_list_empty
    | param_list_element ',' param_list"""
    # param_list parses a sequence of named arguments.
    # The arguments are separated by commas and take one of two forms:
    #   "key = value" -> p_param_list_element_explicit
    #   "**dict_of_name_value_pairs" -> p_param_list_element_kwargs
    # param_list: Tuple[List[Tuple[ID, operand]], List[wrapped_kwargs]]
    (pair, kwargs) = p[1]
    if pair is not None:
        p[3][0].insert(0, pair)
    if kwargs is not None:
        p[3][1].insert(0, kwargs)
    p[0] = p[3]


def p_function_param_list_element(p: YaccProduction) -> None:
    # function_param_list_element: Tuple[Optional[argument], Optional[Tuple[ID, operand]], Optional[wrapped_kwargs]]
    """function_param_list_element : param_list_element"""
    (kwargs, wrapped_kwargs) = p[1]
    p[0] = (None, kwargs, wrapped_kwargs)


def p_function_param_list_element_arg(p: YaccProduction) -> None:
    # function_param_list_element: Tuple[Optional[argument], Optional[Tuple[ID, operand]], Optional[wrapped_kwargs]]
    """function_param_list_element : operand"""
    p[0] = (p[1], None, None)


def p_function_param_list_empty(p: YaccProduction) -> None:
    """function_param_list : function_param_list_empty
    function_param_list_empty : empty"""
    # param_list: Tuple[List[Tuple[ID, operand]], List[wrapped_kwargs]]
    p[0] = ([], [], [])


def p_function_param_list_nonempty(p: YaccProduction) -> None:
    """function_param_list : function_param_list_element empty function_param_list_empty
    | function_param_list_element ',' function_param_list"""
    # function_param_list parses a sequence of named arguments.
    # The arguments are separated by commas and take one of three forms:
    #   "value" -> p_function_param_list_element_arg
    #   "key = value" -> p_function_param_list_element
    #   "**dict_of_name_value_pairs" -> p_function_param_list_element
    # function_param_list: Tuple[List[argument], List[Tuple[ID, operand]], List[wrapped_kwargs]]
    (args, kwargs, wrapped_kwargs) = p[1]
    if args is not None:
        p[3][0].insert(0, args)
    if kwargs is not None:
        p[3][1].insert(0, kwargs)
    if wrapped_kwargs is not None:
        p[3][2].insert(0, wrapped_kwargs)
    p[0] = p[3]


def p_operand_list_collect(p: YaccProduction) -> None:
    """operand_list : operand ',' operand_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_operand_list_term(p: YaccProduction) -> None:
    "operand_list : operand"
    p[0] = [p[1]]


def p_operand_list_term_2(p: YaccProduction) -> None:
    "operand_list :"
    p[0] = []


def p_var_ref(p: YaccProduction) -> None:
    "var_ref : attr_ref"
    p[0] = p[1]


def p_attr_ref(p: YaccProduction) -> None:
    "attr_ref : var_ref '.' ID"
    p[0] = AttributeReference(p[1], p[3])
    attach_lnr(p, 2)


def p_local_var(p: YaccProduction) -> None:
    "local_var : ns_ref"
    p[0] = Reference(p[1])
    attach_from_string(p, 1)


def p_var_ref_2(p: YaccProduction) -> None:
    "var_ref : ns_ref"
    p[0] = Reference(p[1])
    attach_from_string(p, 1)


def p_class_ref_direct(p: YaccProduction) -> None:
    "class_ref : CID"
    p[0] = p[1]


# def p_class_ref_direct_err(p):
#     "class_ref : ID"
#     raise ParserException(
#         file, p.lineno(1), p.lexpos(1), p[1], "Invalid identifier: Entity names must start with a capital")


def p_class_ref(p: YaccProduction) -> None:
    "class_ref : ns_ref SEP CID"
    p[0] = "%s::%s" % (str(p[1]), p[3])
    merge_lnr_to_string(p, 1, 3)


# def p_class_ref_err(p):
#     "class_ref : ns_ref SEP ID"
#     raise ParserException(
#         file, p.lineno(3), p.lexpos(3), p[3], "Invalid identifier: Entity names must start with a capital")


def p_class_ref_list_collect(p: YaccProduction) -> None:
    """class_ref_list : class_ref ',' class_ref_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_class_ref_list_collect_err(p: YaccProduction) -> None:
    """class_ref_list : var_ref ',' class_ref_list"""
    raise ParserException(p[1].location, str(p[1]), "Invalid identifier: Entity names must start with a capital")


def p_class_ref_list_term(p: YaccProduction) -> None:
    "class_ref_list : class_ref"
    p[0] = [p[1]]


def p_class_ref_list_term_err(p: YaccProduction) -> None:
    "class_ref_list : var_ref"

    raise ParserException(p[1].location, str(p[1]), "Invalid identifier: Entity names must start with a capital")


def p_ns_ref(p: YaccProduction) -> None:
    "ns_ref : ns_ref SEP ID"
    p[0] = "%s::%s" % (p[1], p[3])
    merge_lnr_to_string(p, 1, 3)


def p_ns_ref_term(p: YaccProduction) -> None:
    "ns_ref : ID"
    p[0] = p[1]


def p_id_list_collect(p: YaccProduction) -> None:
    """id_list : ID "," id_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_id_list_term(p: YaccProduction) -> None:
    "id_list : ID"
    p[0] = [p[1]]


def p_mls_term(p: YaccProduction) -> None:
    "mls : MLS_END"
    p[0] = p[1]


def p_mls_collect(p: YaccProduction) -> None:
    "mls : MLS mls"
    p[0] = "%s%s" % (p[1], p[2])
    merge_lnr_to_string(p, 1, 2)


# Error rule for syntax errors
def p_error(p: YaccProduction) -> None:
    pos = lexer.lexpos - lexer.linestart + 1
    r = Range(file, lexer.lineno, pos, lexer.lineno, pos)

    if p is None:
        # at end of file
        raise ParserException(r, None, "Unexpected end of file")

    # keyword instead of ID
    if p.type in reserved.values():
        if hasattr(p.value, "location"):
            r = p.value.location
        raise ParserException(r, str(p.value), "invalid identifier, %s is a reserved keyword" % p.value)

    if parser.symstack[-1].type in reserved.values():
        if hasattr(parser.symstack[-1].value, "location"):
            r = parser.symstack[-1].value.location
        raise ParserException(
            r, str(parser.symstack[-1].value), "invalid identifier, %s is a reserved keyword" % parser.symstack[-1].value
        )

    raise ParserException(r, p.value)


# Build the parser
lexer = plyInmantaLex.lexer
parser = yacc.yacc()


def base_parse(ns: Namespace, tfile: str, content: Optional[str]) -> List[Statement]:
    """ Actual parsing code """
    global file
    file = tfile
    lexer.inmfile = tfile
    global namespace
    namespace = ns
    lexer.namespace = ns
    lexer.begin("INITIAL")

    if content is None:
        with open(tfile, "r", encoding="utf-8") as myfile:
            data = myfile.read()
            if len(data) == 0:
                return []
            # prevent problems with EOF
            data = data + "\n"
            lexer.lineno = 1
            lexer.linestart = 0
            return parser.parse(data, lexer=lexer, debug=False)
    else:
        data = content
        if len(data) == 0:
            return []
        # prevent problems with EOF
        data = data + "\n"
        lexer.lineno = 1
        lexer.linestart = 0
        return parser.parse(data, lexer=lexer, debug=False)


cache_manager = CacheManager()


def parse(namespace: Namespace, filename: str, content: Optional[str] = None) -> List[Statement]:
    statements = cache_manager.un_cache(namespace, filename)
    if statements is not None:
        return statements
    statements = base_parse(namespace, filename, content)
    cache_manager.cache(filename, statements)
    return statements
