"""
    Copyright 2016 Inmanta

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
from inmanta.parser.plyInmantaLex import tokens
from inmanta.ast.statements import Literal
from inmanta.ast import Location
from inmanta.ast.statements.generator import For, Constructor
from inmanta.ast.statements.define import DefineEntity, DefineAttribute, DefineImplement, DefineImplementation, DefineRelation, \
    DefineTypeConstraint, DefineTypeDefault, DefineIndex, DefineImport
from inmanta.ast.constraint.expression import Operator, Not, IsDefined
from inmanta.ast.statements.call import FunctionCall
from inmanta.ast.statements.assign import CreateList, IndexLookup, StringFormat, CreateDict
from inmanta.ast.variables import Reference, AttributeReference
from inmanta.parser import plyInmantaLex, ParserException
from inmanta.ast.blocks import BasicBlock
import re
import logging


LOGGER = logging.getLogger()


file = "NOFILE"
namespace = None

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('right', 'MLS'),
)


def attach_lnr(p, token=1):
    v = p[0]
    v.location = Location(file, p.lineno(token))
    v.namespace = namespace


# def attach_lnr_for_parser(p, token=1):
#     v = p[0]
#     v.lineno = p.lineno(token)


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
    p[0] = DefineImport(p[2], p[2])
    attach_lnr(p, 1)


def p_import_1(p):
    '''import : IMPORT ns_ref AS ID'''
    p[0] = DefineImport(p[2], p[4])
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


def p_for(p):
    "for : FOR ID IN operand implementation"
    p[0] = For(p[4], p[2], BasicBlock(namespace, p[5]))
    attach_lnr(p, 1)
#######################
# DEFINITIONS
#######################


def p_entity(p):
    "entity_def : ENTITY CID ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[4][0], [], p[4][1])
    attach_lnr(p)


def p_entity_extends(p):
    "entity_def : ENTITY CID EXTENDS class_ref_list ':' entity_body_outer "
    p[0] = DefineEntity(namespace, p[2], p[6][0], p[4], p[6][1])
    attach_lnr(p)


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


def p_attr(p):
    "attr : ns_ref ID"
    p[0] = DefineAttribute(p[1], p[2], None)
    attach_lnr(p, 2)


def p_attr_cte(p):
    "attr : ns_ref ID '=' constant"
    p[0] = DefineAttribute(p[1], p[2], p[4])
    attach_lnr(p, 2)


def p_attr_list(p):
    "attr : ns_ref '[' ']' ID"
    p[0] = DefineAttribute(p[1], p[4], None, True)
    attach_lnr(p, 4)


def p_attr_list_cte(p):
    "attr : ns_ref '[' ']' ID '=' constant_list"
    p[0] = DefineAttribute(p[1], p[4], p[6], True)
    attach_lnr(p, 2)


def p_attr_dict(p):
    "attr : DICT ID"
    p[0] = DefineAttribute("dict", p[2], None)
    attach_lnr(p, 1)


def p_attr_list_dict(p):
    "attr : DICT ID '=' map_def"
    p[0] = DefineAttribute("dict", p[2], p[4])
    attach_lnr(p, 1)

# IMPLEMENT


def p_implement(p):
    "implement_def : IMPLEMENT class_ref USING ns_list"
    p[0] = DefineImplement(p[2], p[4], Literal(True))
    attach_lnr(p)


def p_implement_when(p):
    "implement_def : IMPLEMENT class_ref USING ns_list WHEN condition"
    p[0] = DefineImplement(p[2], p[4], p[6])
    attach_lnr(p)

# IMPLEMENTATION


def p_implementation_def(p):
    "implementation_def : IMPLEMENTATION ID FOR class_ref implementation"
    p[0] = DefineImplementation(namespace, p[2], p[4], BasicBlock(namespace, p[5]))
    attach_lnr(p)


# def p_implementation_def_2(p):
#     "implementation_def : IMPLEMENTATION ID implementation"
#     p[0] = DefineImplementation(namespace, p[2], None, BasicBlock(namespace, p[3]))
#     attach_lnr(p)


def p_implementation(p):
    "implementation : ':' mls stmt_list END"
    p[0] = p[3]


def p_implementation_1(p):
    "implementation : ':' stmt_list END"
    p[0] = p[2]


def p_implementation_2(p):
    "implementation : ':' END"
    p[0] = []

# RELATION


def p_relation(p):
    "relation : class_ref ID multi REL multi class_ref ID"
    if not(p[4] == '--'):
        LOGGER.warning("DEPRECATION: use of %s in relation definition is deprecated, use -- (in %s)" %
                       (p[4], Location(file, p.lineno(4))))
    p[0] = DefineRelation((p[1], p[2], p[3]), (p[6], p[7], p[5]))
    attach_lnr(p, 2)


def p_relation_new(p):
    "relation : class_ref '.' ID multi REL class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_new_unidir(p):
    "relation : class_ref '.' ID multi REL class_ref"
    p[0] = DefineRelation((p[1], None, None), (p[6], p[3], p[4]))
    attach_lnr(p, 2)


def p_relation_new_annotated(p):
    "relation : class_ref '.' ID multi operand_list class_ref '.' ID multi"
    p[0] = DefineRelation((p[1], p[8], p[9]), (p[6], p[3], p[4]), p[5])
    attach_lnr(p, 2)


def p_relation_new_annotated_unidir(p):
    "relation : class_ref '.' ID multi operand_list class_ref"
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


def p_typedef_1(p):
    """typedef : TYPEDEF ID AS ns_ref MATCHING REGEX
                | TYPEDEF ID AS ns_ref MATCHING condition"""
    p[0] = DefineTypeConstraint(namespace, p[2], p[4], p[6])
    attach_lnr(p)


def p_typedef_cls(p):
    """typedef : TYPEDEF CID AS constructor"""
    p[0] = DefineTypeDefault(namespace, p[2], p[4])
    attach_lnr(p)
# index


def p_index(p):
    """index : INDEX class_ref '(' id_list ')' """
    p[0] = DefineIndex(p[2], p[4])
    attach_lnr(p)

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
    operator = Operator.get_operator_class(p[2])
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
    attach_lnr(p)


def p_condition_is_defined_short(p):
    """condition : ID IS DEFINED"""
    p[0] = IsDefined(Reference('self'), p[1])
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
              | index_lookup"""
    p[0] = p[1]


def p_constructor(p):
    " constructor : class_ref '(' param_list ')' "
    p[0] = Constructor(p[1], p[3], Location(file, p.lineno(2)), namespace)


def p_constructor_empty(p):
    " constructor : class_ref '(' ')' "
    p[0] = Constructor(p[1], [], Location(file, p.lineno(2)), namespace)


def p_function_call_empty(p):
    " function_call : ns_ref '(' ')'"
    p[0] = FunctionCall(p[1], [])
    attach_lnr(p, 2)


def p_function_call(p):
    " function_call : ns_ref '(' operand_list ')'"
    p[0] = FunctionCall(p[1], p[3])
    attach_lnr(p, 2)


def p_list_def(p):
    " list_def : '[' operand_list ']'"
    p[0] = CreateList(p[2])
    attach_lnr(p, 2)


def p_list_def_empty(p):
    " list_def : '[' ']'"
    p[0] = CreateList([])
    attach_lnr(p, 1)


def p_pair_list_collect(p):
    """pair_list : STRING ':' operand ',' pair_list"""
    p[5].insert(0, (p[1], p[3]))
    p[0] = p[5]


def p_pair_list_term(p):
    "pair_list : STRING ':' operand"
    p[0] = [(p[1], p[3])]


def p_map_def(p):
    " map_def : '{' pair_list '}'"
    p[0] = CreateDict(p[2])
    attach_lnr(p, 2)


def p_map_def_empty(p):
    " map_def : '{' '}'"
    p[0] = CreateDict([])
    attach_lnr(p, 1)


def p_index_lookup(p):
    " index_lookup : class_ref '[' param_list ']'"
    p[0] = IndexLookup(p[1], p[3])
    attach_lnr(p, 2)
#######################
# HELPERS


def p_constant(p):
    """ constant : INT
    | FLOAT
    | mls
    """
    p[0] = Literal(p[1])
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
    match_obj = format_regex_compiled.findall(value)

    if len(match_obj) > 0:
        p[0] = create_string_format(value, match_obj, Location(file, p.lineno(1)))
    else:
        p[0] = Literal(value)
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
        ref.location = location

        if len(var_parts) > 1:
            for attr in var_parts[1:]:
                ref = AttributeReference(ref, attr)
                ref.location = location
                ref.namespace = namespace
            _vars.append((ref, var_str[0]))
        else:
            _vars.append((ref, var_str[0]))

    return StringFormat(format_string, _vars)


def p_constant_list_empty(p):
    " constant_list : '[' ']' "
    p[0] = CreateList([])
    attach_lnr(p, 1)


def p_constant_list(p):
    " constant_list : '[' constants ']' "
    p[0] = CreateList(p[2])
    attach_lnr(p, 1)


def p_constants_term(p):
    "constants : constant"
    p[0] = [p[1]]


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


def p_operand_list_collect(p):
    """operand_list : operand ',' operand_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_operand_list_term(p):
    'operand_list : operand'
    p[0] = [p[1]]


def p_ns_list_collect(p):
    """ns_list : ns_ref ',' ns_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_ns_list_term(p):
    'ns_list : ns_ref'
    p[0] = [p[1]]


def p_var_ref(p):
    "var_ref : var_ref '.' ID"
    p[0] = AttributeReference(p[1], p[3])
    attach_lnr(p, 2)


def p_var_ref_2(p):
    "var_ref : ns_ref"
    p[0] = Reference(p[1])
    attach_lnr(p)


def p_class_ref_direct(p):
    "class_ref : CID"
    p[0] = p[1]


def p_class_ref(p):
    "class_ref : ns_ref SEP CID"
    p[0] = "%s::%s" % (p[1], p[3])


def p_class_ref_list_collect(p):
    """class_ref_list : class_ref ',' class_ref_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_class_ref_list_term(p):
    'class_ref_list : class_ref'
    p[0] = [p[1]]


def p_ns_ref(p):
    "ns_ref : ns_ref SEP ID"
    p[0] = "%s::%s" % (p[1], p[3])
    # attach_lnr_for_parser(p, 2)


def p_ns_ref_term(p):
    "ns_ref : ID"
    p[0] = p[1]
    # attach_lnr_for_parser(p, 1)


def p_id_list_collect(p):
    """id_list : ID "," id_list"""
    p[3].insert(0, p[1])
    p[0] = p[3]


def p_id_list_term(p):
    'id_list : ID'
    p[0] = [p[1]]


def p_mls_term(p):
    "mls : MLS"
    p[0] = p[1]
    # attach_lnr_for_parser(p)


def p_mls_collect(p):
    "mls : MLS mls"
    p[0] = "%s\n%s" % (p[1], p[2])
    # attach_lnr_for_parser(p)


# Error rule for syntax errors
def p_error(p):
    if p is not None:
        raise ParserException(file, p.lineno, p.lexpos, p.value)
    # at end of file
    raise ParserException(file, lexer.lineno, lexer.lexpos, "")


# Build the parser
lexer = plyInmantaLex.lexer
parser = yacc.yacc()


def myparse(ns, tfile, content):
    global file
    file = tfile
    global namespace
    namespace = ns
    lexer.begin('INITIAL')
    try:
        if content is None:
            with open(tfile, 'r') as myfile:
                data = myfile.read()
                if len(data) == 0:
                    return []
                lexer.lineno = 1
                return parser.parse(data, lexer=lexer, debug=False)
        else:
            data = content
            if len(data) == 0:
                return []
            lexer.lineno = 1
            return parser.parse(content, lexer=lexer, debug=False)
    except ParserException as e:
        e.findCollumn(data)
        e.location.file = tfile
        raise e


def parse(namespace, filename, content=None):

    statements = myparse(namespace, filename, content)
    # self.cache(filename, statements)
    return statements
