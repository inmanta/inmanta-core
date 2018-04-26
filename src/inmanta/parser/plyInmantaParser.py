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

# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer. This is required.
from inmanta.parser.plyInmantaLex import tokens, reserved
from inmanta.ast.statements import Literal
from inmanta.ast import Location, LocatableString, Range
from inmanta.ast.statements.generator import For, Constructor
from inmanta.ast.statements.define import DefineEntity, DefineAttribute, DefineImplement, DefineImplementation, DefineRelation, \
    DefineTypeConstraint, DefineTypeDefault, DefineIndex, DefineImport, DefineImplementInherits
from inmanta.ast.constraint.expression import Operator, Not, IsDefined
from inmanta.ast.statements.call import FunctionCall
from inmanta.ast.statements.assign import CreateList, IndexLookup, StringFormat, CreateDict, ShortIndexLookup, MapLookup
from inmanta.ast.variables import Reference, AttributeReference
from inmanta.parser import plyInmantaLex, ParserException
from inmanta.ast.blocks import BasicBlock
import re
import logging
from inmanta.execute.util import NoneValue


LOGGER = logging.getLogger()


file = "NOFILE"
namespace = None

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('right', 'MLS'),
    ('right', 'MLS_END')
)


def attach_lnr(p, token=1):
    v = p[0]
    v.location = Location(file, p.lineno(token))
    v.namespace = namespace
    v.lexpos = p.lexpos(token)


def merge_lnr_to_string(p, starttoken=1, endtoken=2):
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


def attach_from_string(p, token=1):
    v = p[0]
    v.location = p[token].location
    v.namespace = p[token].namespace


def p_main_collect(p):
    """main : top_stmt main"""
    v = p[2]
    v.insert(0, p[1])
    p[0] = v


def p_main_term(p):
    'main : top_stmt'
    p[0] = [p[1]]


def p_top_stmt(p):
    '''top_stmt : mls
                | entity_def
                | implement_def
                | implementation_def
                | relation
                | statement
                | typedef
                | index
                | import '''
    p[0] = p[1]


#######################
# IMPORT
#######################

def p_import(p):
    '''import : IMPORT ns_ref'''
    p[0] = DefineImport(str(p[2]), str(p[2]))
    attach_lnr(p, 1)


def p_import_1(p):
    '''import : IMPORT ns_ref AS ID'''
    p[0] = DefineImport(str(p[2]), p[4])
    attach_lnr(p, 1)
#######################
# STMTS
#######################


def p_stmt(p):
    '''statement : assign
                | constructor
                | function_call
                | for'''
    p[0] = p[1]


# def p_stmt_err(p):
#     '''statement : list_def
#               | map_def
#               | var_ref
#               | index_lookup'''
#     raise ParserException(file, p[1].location.lnr, lexer.lexpos, "",
#                           msg="expressions are not valid statements, assign this value to a variable to fix this error")


def p_stmt_list_collect(p):
    """stmt_list : statement stmt_list"""
    v = p[2]
    v.append(p[1])
    p[0] = v


def p_stmt_list_term(p):
    'stmt_list : statement'
    p[0] = [p[1]]


def p_assign(p):
    "assign : var_ref '=' operand"
    p[0] = p[1].as_assign(p[3])
    attach_lnr(p, 2)


def p_assign_extend(p):
    "assign : var_ref PEQ operand"
    p[0] = p[1].as_assign(p[3], list_only=True)
    attach_lnr(p, 2)


def p_for(p):
    "for : FOR ID IN operand ':' block"
    p[0] = For(p[4], p[2], BasicBlock(namespace, p[6]))
    attach_lnr(p, 1)
#######################
# DEFINITIONS
#######################


def p_entity(p):
    "entity_def : ENTITY CID ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[4][0], [], p[4][1])
    attach_lnr(p)


def p_entity_err_1(p):
    "entity_def : ENTITY ID ':' entity_body_outer "
    raise ParserException(p[2].location, str(p[2]), "Invalid identifier: Entity names must start with a capital")


def p_entity_extends(p):
    "entity_def : ENTITY CID EXTENDS class_ref_list ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[6][0], p[4], p[6][1])
    attach_lnr(p)


def p_entity_extends_err(p):
    "entity_def : ENTITY ID EXTENDS class_ref_list ':' entity_body_outer "
    raise ParserException(p[2].location, str(p[2]), "Invalid identifier: Entity names must start with a capital")


def p_entity_body_outer(p):
    '''entity_body_outer : mls entity_body END'''
    p[0] = (p[1], p[2])


def p_entity_body_outer_1(p):
    '''entity_body_outer : entity_body END '''
    p[0] = (None, p[1])


def p_entity_body_outer_none(p):
    '''entity_body_outer : END '''
    p[0] = (None, [])


def p_entity_body_outer_4(p):
    '''entity_body_outer : mls END'''
    p[0] = (p[1], [])


def p_entity_body_collect(p):
    ''' entity_body : entity_body attr'''
    p[1].append(p[2])
    p[0] = p[1]


def p_entity_body(p):
    ''' entity_body : attr'''
    p[0] = [p[1]]


def p_attribute_type(p):
    '''attr_type : ns_ref'''
    p[0] = (p[1], False)


def p_attribute_type_opt(p):
    "attr_type : ns_ref '?'"
    p[0] = (p[1], True)


def p_attr(p):
    "attr : attr_type ID"
    (attr, nullable) = p[1]
    p[0] = DefineAttribute(attr, p[2], None, nullable=nullable)
    attach_lnr(p, 2)


def p_attr_cte(p):
    """attr : attr_type ID '=' constant
           | attr_type ID '=' constant_list"""
    (attr, nullable) = p[1]
    p[0] = DefineAttribute(attr, p[2], p[4], nullable=nullable)
    attach_lnr(p, 2)


def p_attr_undef(p):
    "attr : attr_type ID '=' UNDEF"
    (attr, nullable) = p[1]
    p[0] = DefineAttribute(attr, p[2], None, remove_default=True, nullable=nullable)
    attach_lnr(p, 2)


def p_attribute_type_multi(p):
    "attr_type_multi : ns_ref '[' ']'"
    p[0] = (p[1], False, Location(file, p.lineno(1)))


def p_attribute_type_multi_opt(p):
    "attr_type_multi : ns_ref '[' ']' '?'"
    p[0] = (p[1], True, Location(file, p.lineno(1)))


def p_attr_list(p):
    "attr : attr_type_multi ID"
    (attr, nullable, location) = p[1]
    p[0] = DefineAttribute(attr, p[2], None, True, nullable=nullable)
    attach_lnr(p, 2)


def p_attr_list_cte(p):
    "attr : attr_type_multi ID '=' constant_list"
    (attr, nullable, _) = p[1]
    p[0] = DefineAttribute(attr, p[2], p[4], True, nullable=nullable)
    attach_lnr(p, 3)


def p_attr_list_undef(p):
    "attr : attr_type_multi ID '=' UNDEF"
    (attr, nullable, _) = p[1]
    p[0] = DefineAttribute(attr, p[2], None, True, remove_default=True, nullable=nullable)
    attach_lnr(p, 3)


def p_attr_list_null(p):
    "attr : attr_type_multi ID '=' NULL"
    (attr, nullable, _) = p[1]
    p[0] = DefineAttribute(attr, p[2], Literal(NoneValue()), True, nullable=nullable)
    attach_lnr(p, 3)


def p_attr_dict(p):
    "attr : DICT ID"
    p[0] = DefineAttribute(p[1], p[2], None)
    attach_lnr(p, 1)


def p_attr_list_dict(p):
    "attr : DICT ID '=' map_def"
    p[0] = DefineAttribute(p[1], p[2], p[4])
    attach_lnr(p, 1)


def p_attr_list_dict_null_err(p):
    "attr : DICT ID '=' NULL"
    raise ParserException(p[2].location, str(p[2]), "null can not be assigned to dict, did you mean \"dict? %s = null\"" % p[2])


def p_attr_dict_nullable(p):
    "attr : DICT '?' ID"
    p[0] = DefineAttribute(p[1], p[3], None, nullable=True)
    attach_lnr(p, 1)


def p_attr_list_dict_nullable(p):
    "attr : DICT '?'  ID '=' map_def"
    p[0] = DefineAttribute(p[1], p[3], p[5], nullable=True)
    attach_lnr(p, 1)


def p_attr_list_dict_null(p):
    "attr : DICT '?'  ID '=' NULL"
    p[0] = DefineAttribute(p[1], p[3], Literal(NoneValue()), nullable=True)
    attach_lnr(p, 1)


# IMPLEMENT
def p_implement_inh(p):
    "implement_def : IMPLEMENT class_ref USING PARENTS"
    p[0] = DefineImplementInherits(p[2])
    attach_lnr(p)


def p_implement(p):
    "implement_def : IMPLEMENT class_ref USING ns_list"
    p[0] = DefineImplement(p[2], p[4], Literal(True))
    attach_lnr(p)


def p_implement_when(p):
    "implement_def : IMPLEMENT class_ref USING ns_list WHEN condition"
    p[0] = DefineImplement(p[2], p[4], p[6])
    attach_lnr(p)


def p_implement_comment(p):
    "implement_def : IMPLEMENT class_ref USING ns_list mls"
    p[0] = DefineImplement(p[2], p[4], Literal(True), comment=p[5])
    attach_lnr(p)


def p_implement_inh_comment(p):
    "implement_def : IMPLEMENT class_ref USING PARENTS mls"
    p[0] = DefineImplementInherits(p[2], comment=p[5])
    attach_lnr(p)


def p_implement_when_comment(p):
    "implement_def : IMPLEMENT class_ref USING ns_list WHEN condition mls"
    p[0] = DefineImplement(p[2], p[4], p[6], comment=p[7])
    attach_lnr(p)


# IMPLEMENTATION


def p_implementation_def(p):
    "implementation_def : IMPLEMENTATION ID FOR class_ref implementation"
    docstr, stmts = p[5]
    p[0] = DefineImplementation(namespace, p[2], p[4], BasicBlock(namespace, stmts), docstr)
    attach_lnr(p)


# def p_implementation_def_2(p):
#     "implementation_def : IMPLEMENTATION ID implementation"
#     p[0] = DefineImplementation(namespace, p[2], None, BasicBlock(namespace, p[3]))
#     attach_lnr(p)

def p_implementation(p):
    "implementation : ':' mls block"
    p[0] = (p[2], p[3])


def p_implementation_1(p):
    "implementation : ':' block"
    p[0] = (None, p[2])


def p_block(p):
    "block : stmt_list END"
    p[0] = p[1]


def p_block_empty(p):
    "block : END"
    p[0] = []

# RELATION


def p_relation(p):
    "relation : class_ref ID multi REL multi class_ref ID"
    if not(p[4] == '--'):
        LOGGER.warning("DEPRECATION: use of %s in relation definition is deprecated, use -- (in %s)" %
                       (p[4], Location(file, p.lineno(4))))
    p[0] = DefineRelation((p[1], p[2], p[3]), (p[6], p[7], p[5]))
    attach_lnr(p, 2)


def p_relation_comment(p):
    "relation : class_ref ID multi REL multi class_ref ID mls"
    if not(p[4] == '--'):
        LOGGER.warning("DEPRECATION: use of %s in relation definition is deprecated, use -- (in %s)" %
                       (p[4], Location(file, p.lineno(4))))
    rel = DefineRelation((p[1], p[2], p[3]), (p[6], p[7], p[5]))
    rel.comment = str(p[8])
    p[0] = rel
    attach_lnr(p, 2)


def p_relation_new_outer_comment(p):
    "relation : relationnew mls"
    rel = p[1]
    rel.comment = str(p[2])
    p[0] = rel


def p_relation_new_outer(p):
    "relation : relationnew"
    p[0] = p[1]


def p_relation_new(p):
    "relationnew : class_ref '.' ID multi REL class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_new_unidir(p):
    "relationnew : class_ref '.' ID multi REL class_ref"
    p[0] = DefineRelation((p[1], None, None), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_new_annotated(p):
    "relationnew : class_ref '.' ID multi operand_list class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]), p[5])
    attach_lnr(p, 2)


def p_relation_new_annotated_unidir(p):
    "relationnew : class_ref '.' ID multi operand_list class_ref"
    p[0] = DefineRelation((p[1], None, None), (p[6], p[3], p[4]), p[5])
    attach_lnr(p, 2)


def p_multi_1(p):
    "multi : '[' INT ']' "
    p[0] = (p[2], p[2])


def p_multi_2(p):
    "multi : '[' INT ':' ']' "
    p[0] = (p[2], None)


def p_multi_3(p):
    "multi : '[' INT ':' INT ']' "
    p[0] = (p[2], p[4])


def p_multi_4(p):
    "multi : '['  ':' INT ']' "
    p[0] = (None, p[3])

# typedef


def p_typedef_outer(p):
    """typedef : typedef_inner"""
    p[0] = p[1]


def p_typedef_outer_comment(p):
    """typedef : typedef_inner mls"""
    tdef = p[1]
    tdef.comment = str(p[2])
    p[0] = tdef


def p_typedef_1(p):
    """typedef_inner : TYPEDEF ID AS ns_ref MATCHING REGEX
                | TYPEDEF ID AS ns_ref MATCHING condition"""
    p[0] = DefineTypeConstraint(namespace, p[2], p[4], p[6])
    attach_lnr(p, 2)


def p_typedef_cls(p):
    """typedef_inner : TYPEDEF CID AS constructor"""
    p[0] = DefineTypeDefault(namespace, p[2], p[4])
    attach_lnr(p, 2)
# index


def p_index(p):
    """index : INDEX class_ref '(' id_list ')' """
    p[0] = DefineIndex(p[2], p[4])
    attach_lnr(p, 1)

#######################
# CONDITIONALS


def p_condition_1(p):
    "condition : '(' condition ')'"
    p[0] = p[2]


def p_condition_2(p):
    """condition : operand CMP_OP operand
                | operand IN list_def
                | operand IN var_ref
                | condition AND condition
                | condition OR condition """
    operator = Operator.get_operator_class(str(p[2]))
    p[0] = operator(p[1], p[3])
    attach_lnr(p, 2)


def p_condition_3(p):
    """condition : function_call
                | var_ref"""
    p[0] = p[1]


def p_condition_not(p):
    """condition : NOT condition"""
    p[0] = Not(p[2])
    attach_lnr(p)


def p_condition_is_defined(p):
    """condition : var_ref '.' ID IS DEFINED"""
    p[0] = IsDefined(p[1], p[3])
    attach_lnr(p, 2)


def p_condition_is_defined_short(p):
    """condition : ID IS DEFINED"""
    ref = Reference('self')
    ref.location = p[1].get_location()
    p[0] = IsDefined(ref, p[1])
    attach_lnr(p)


def p_condition_term_1(p):
    """condition : TRUE
                | FALSE"""
    p[0] = Literal(p[1])
    attach_lnr(p)

#######################
# EXPRESSIONS


# TODO
def p_operand(p):
    """ operand : constant
              | function_call
              | constructor
              | list_def
              | map_def
              | var_ref
              | index_lookup
              | map_lookup"""
    p[0] = p[1]


def p_map_lookup(p):
    """ map_lookup : attr_ref '[' operand ']'
                   | local_var '[' operand ']'
                   | map_lookup '[' operand ']'"""
    p[0] = MapLookup(p[1], p[3])


def p_constructor(p):
    " constructor : class_ref '(' param_list ')' "
    p[0] = Constructor(p[1], p[3], Location(file, p.lineno(2)), namespace)


def p_function_call(p):
    " function_call : ns_ref '(' operand_list ')'"
    p[0] = FunctionCall(str(p[1]), p[3])
    attach_lnr(p, 2)


def p_list_def(p):
    " list_def : '[' operand_list ']'"
    p[0] = CreateList(p[2])
    attach_lnr(p, 1)


def p_pair_list_collect(p):
    """pair_list : STRING ':' operand ',' pair_list"""
    p[5].insert(0, (str(p[1]), p[3]))
    p[0] = p[5]


def p_pair_list_term(p):
    "pair_list : STRING ':' operand"
    p[0] = [(str(p[1]), p[3])]


def p_pair_list_term_2(p):
    "pair_list : "
    p[0] = []


def p_map_def(p):
    " map_def : '{' pair_list '}'"
    p[0] = CreateDict(p[2])
    attach_lnr(p, 1)


def p_map_def_empty(p):
    " map_def : '{' '}'"
    p[0] = CreateDict([])
    attach_lnr(p, 1)


def p_index_lookup(p):
    " index_lookup : class_ref '[' param_list ']'"
    p[0] = IndexLookup(p[1], p[3])
    attach_lnr(p, 2)


def p_short_index_lookup(p):
    " index_lookup : attr_ref '[' param_list ']'"
    attref = p[1]
    p[0] = ShortIndexLookup(attref.instance, attref.attribute, p[3])
    attach_lnr(p, 2)
#######################
# HELPERS


def p_constant_mls(p):
    """ constant : mls """
    p[0] = Literal(str(p[1]))
    attach_from_string(p, 1)


def p_constant(p):
    """ constant : INT
    | FLOAT
    """
    p[0] = Literal(p[1])
    attach_lnr(p)


def p_constant_none(p):
    """ constant : NULL
    """
    p[0] = Literal(NoneValue())
    attach_lnr(p)


def p_constant_regex(p):
    """ constant : REGEX
    """
    p[0] = p[1]
    attach_lnr(p)


def p_constant_t(p):
    """ constant : TRUE
    """
    p[0] = Literal(True)
    attach_lnr(p)


def p_constant_f(p):
    """ constant : FALSE
    """
    p[0] = Literal(False)
    attach_lnr(p)


formatRegex = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
format_regex_compiled = re.compile(formatRegex, re.MULTILINE | re.DOTALL)


def p_string(p):
    " constant : STRING "
    value = p[1]
    match_obj = format_regex_compiled.findall(str(value))

    if len(match_obj) > 0:
        p[0] = create_string_format(value, match_obj, Location(file, p.lineno(1)))
    else:
        p[0] = Literal(str(value))
    attach_lnr(p)


def create_string_format(format_string, variables, location):
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


def p_constant_list(p):
    " constant_list : '[' constants ']' "
    p[0] = CreateList(p[2])
    attach_lnr(p, 1)


def p_constants_term(p):
    "constants : constant"
    p[0] = [p[1]]


def p_constants_term_2(p):
    "constants : "
    p[0] = []


def p_constants_collect(p):
    """constants : constant ',' constants"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_param_list_collect(p):
    """param_list : ID '=' operand ',' param_list"""
    p[5].insert(0, (p[1], p[3]))
    p[0] = p[5]


def p_param_list_term(p):
    "param_list : ID '=' operand"
    p[0] = [(p[1], p[3])]


def p_param_list_term_2(p):
    "param_list : "
    p[0] = []


def p_operand_list_collect(p):
    """operand_list : operand ',' operand_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_operand_list_term(p):
    'operand_list : operand'
    p[0] = [p[1]]


def p_operand_list_term_2(p):
    "operand_list :"
    p[0] = []


def p_ns_list_collect(p):
    """ns_list : ns_ref ',' ns_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_ns_list_term(p):
    'ns_list : ns_ref'
    p[0] = [p[1]]


def p_var_ref(p):
    "var_ref : attr_ref"
    p[0] = p[1]


def p_attr_ref(p):
    "attr_ref : var_ref '.' ID"
    p[0] = AttributeReference(p[1], p[3])
    attach_lnr(p, 2)


def p_local_var(p):
    "local_var : ns_ref"
    p[0] = Reference(p[1])
    attach_from_string(p, 1)


def p_var_ref_2(p):
    "var_ref : ns_ref"
    p[0] = Reference(p[1])
    attach_from_string(p, 1)


def p_class_ref_direct(p):
    "class_ref : CID"
    p[0] = p[1]


# def p_class_ref_direct_err(p):
#     "class_ref : ID"
#     raise ParserException(
#         file, p.lineno(1), p.lexpos(1), p[1], "Invalid identifier: Entity names must start with a capital")


def p_class_ref(p):
    "class_ref : ns_ref SEP CID"
    p[0] = "%s::%s" % (str(p[1]), p[3])
    merge_lnr_to_string(p, 1, 3)


# def p_class_ref_err(p):
#     "class_ref : ns_ref SEP ID"
#     raise ParserException(
#         file, p.lineno(3), p.lexpos(3), p[3], "Invalid identifier: Entity names must start with a capital")


def p_class_ref_list_collect(p):
    """class_ref_list : class_ref ',' class_ref_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_class_ref_list_collect_err(p):
    """class_ref_list : var_ref ',' class_ref_list"""
    raise ParserException(p[1].location, str(p[1]), "Invalid identifier: Entity names must start with a capital")


def p_class_ref_list_term(p):
    'class_ref_list : class_ref'
    p[0] = [p[1]]


def p_class_ref_list_term_err(p):
    'class_ref_list : var_ref'

    raise ParserException(p[1].location, str(p[1]), "Invalid identifier: Entity names must start with a capital")


def p_ns_ref(p):
    "ns_ref : ns_ref SEP ID"
    p[0] = "%s::%s" % (p[1], p[3])
    merge_lnr_to_string(p, 1, 3)


def p_ns_ref_term(p):
    "ns_ref : ID"
    p[0] = p[1]


def p_id_list_collect(p):
    """id_list : ID "," id_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_id_list_term(p):
    'id_list : ID'
    p[0] = [p[1]]


def p_mls_term(p):
    "mls : MLS_END"
    p[0] = p[1]


def p_mls_collect(p):
    "mls : MLS mls"
    p[0] = "%s%s" % (p[1], p[2])
    merge_lnr_to_string(p, 1, 2)


# Error rule for syntax errors
def p_error(p):
    pos = lexer.lexpos - lexer.linestart + 1
    r = Range(file, lexer.lineno, pos, lexer.lineno, pos)

    if p is None:
        # at end of file
        raise ParserException(r, "Unexpected end of file")

    # keyword instead of ID
    if p.type in reserved.values():
        if hasattr(p.value, "location"):
            r = p.value.location
        raise ParserException(r, str(p.value), "invalid identifier, %s is a reserved keyword" % p.value)

    if parser.symstack[-1].type in reserved.values():
        if hasattr(parser.symstack[-1].value, "location"):
            r = parser.symstack[-1].value.location
        raise ParserException(r, str(parser.symstack[-1].value),
                              "invalid identifier, %s is a reserved keyword" % parser.symstack[-1].value)

    raise ParserException(r, p.value)


# Build the parser
lexer = plyInmantaLex.lexer
parser = yacc.yacc()


def myparse(ns, tfile, content):
    global file
    file = tfile
    lexer.inmfile = tfile
    global namespace
    namespace = ns
    lexer.namespace = ns
    lexer.begin('INITIAL')

    if content is None:
        with open(tfile, 'r') as myfile:
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


def parse(namespace, filename, content=None):

    statements = myparse(namespace, filename, content)
    # self.cache(filename, statements)
    return statements
