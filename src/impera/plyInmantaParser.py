'''
Created on Apr 10, 2016

@author: wouter
'''

# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
from plyInmantaLex import tokens
import logging
from ply.yacc import PlyLogger
import sys
import time


def p_main_collect(p):
    """main : top_stmt main"""
    p[2].append(p[1])
    p[0] = p[2]


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
                | index '''
    p[0] = p[1]

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
    p[2].append(p[1])
    p[0] = p[2]


def p_stmt_list_term(p):
    'stmt_list : statement'
    p[0] = [p[1]]


def p_assign(p):
    "assign : var_ref '=' operand"
    p[0] = ('=', p[1], p[2])


def p_for(p):
    "for : FOR ID IN operand implementation"
    p[0] = ("for", p[2], p[4], p[5])
#######################
# DEFINITIONS
#######################


def p_entity(p):
    "entity_def : ENTITY CID ':' entity_body_outer "
    p[0] = ('E', p[2], None)


def p_entity_extends(p):
    "entity_def : ENTITY CID EXTENDS class_ref ':' entity_body_outer "
    p[0] = ('E', p[2], p[5])


def p_entity_body_outer(p):
    '''entity_body_outer : mls entity_body END
                         | entity_body END '''
    p[0] = p[len(p) - 1]


def p_entity_body_outer_none(p):
    '''entity_body_outer : END 
                        | mls END'''
    p[0] = []


def p_entity_body_collect(p):
    ''' entity_body : entity_body attr'''
    p[1].append(p[2])
    p[0] = p[1]


def p_entity_body(p):
    ''' entity_body : attr'''
    p[0] = [p[1]]


def p_attr(p):
    "attr : ns_ref ID"
    p[0] = ('A', p[1], p[2], None)


def p_attr_cte(p):
    "attr : ns_ref ID '=' constant"
    p[0] = ('A', p[1], p[2], p[3])

# IMPLEMENT


def p_implement(p):
    "implement_def : IMPLEMENT class_ref USING ns_list"
    p[0] = ('I', p[2], p[4], None)


def p_implement_when(p):
    "implement_def : IMPLEMENT class_ref USING ns_list WHEN condition"
    p[0] = ('I', p[2], p[4], p[6])


# IMPLEMENTATION

def p_implementation_def(p):
    "implementation_def : IMPLEMENTATION ID FOR class_ref implementation"
    p[0] = ('Impl', p[2], p[4], p[5])


def p_implementation_def_2(p):
    "implementation_def : IMPLEMENTATION ID implementation"
    p[0] = ('Impl', p[2], None, p[3])


def p_implementation(p):
    "implementation : ':' mls stmt_list END"
    p[0] = p[3]


def p_implementation_1(p):
    "implementation : ':' stmt_list END"
    p[0] = p[2]

# RELATION


def p_relation(p):
    "relation : class_ref ID multi REL multi class_ref ID"
    p[0] = ("R", p[1], p[2], p[3], p[5], p[6], p[7])


def p_multi_1(p):
    "multi : '[' INT ']' "
    p[0] = ('M', p[2], p[2])


def p_multi_2(p):
    "multi : '[' INT ':' ']' "
    p[0] = ('M', p[2], None)


def p_multi_3(p):
    "multi : '[' INT ':' INT ']' "
    p[0] = ('M', p[3], p[4])


def p_multi_4(p):
    "multi : '['  ':' INT ']' "
    p[0] = ('M', None, p[3])

# typedef


def p_typedef_1(p):
    """typedef : TYPEDEF ID AS ns_ref MATCHING REGEX
                | TYPEDEF ID AS ns_ref MATCHING condition"""
    p[0] = ("TD", p[2], p[4], p[6])


def p_typedef_cls(p):
    """typedef : TYPEDEF CID AS constructor"""
    p[0] = ("TDC", p[2], p[4])

# index


def p_index(p):
    """index : INDEX class_ref '(' id_list ')' """
    p[0] = ("IDX", p[1], p[3])


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
    p[0] = (p[1], p[2], p[3])


def p_condition_3(p):
    "condition : function_call"
    p[0] = p[1]


def p_condition_not(p):
    """condition : NOT condition"""
    p[0] = (None, p[1], p[2])


def p_condition_term_1(p):
    """condition : TRUE
                | FALSE"""
    p[0] = ('CTE', p[1])

#######################
# EXPRESSIONS


# TODO
def p_operand(p):
    """ operand : constant
              | function_call
              | constructor
              | list_def
              | var_ref 
              | index_lookup"""
    p[0] = p[1]


def p_constructor(p):
    " constructor : class_ref '(' param_list ')' "
    p[0] = ("CONSTRUCT", p[1], p[3])


def p_function_call(p):
    " function_call : ns_ref '(' operand_list ')'"
    p[0] = ('F', p[1], p[3])


def p_list_def(p):
    " list_def : '[' operand_list ']'"
    p[0] = ('LD', p[2])


def p_index_lookup(p):
    " index_lookup : class_ref '[' param_list ']'"
    p[0] = ("IL", p[1], p[3])
#######################
# HELPERS


def p_constant(p):
    """ constant : TRUE 
    | FALSE
    | STRING
    | INT
    | FLOAT
    | mls
    | REGEX """
    p[0] = ('CTE', p[1])


def p_param_list_collect(p):
    """param_list : ID '=' operand ',' param_list"""
    p[5].append(('A', p[1], p[3]))
    p[0] = p[5]


def p_param_list_term(p):
    "param_list : ID '=' operand"
    p[0] = [('A', p[1], p[3])]


def p_operand_list_collect(p):
    """operand_list : operand ',' operand_list"""
    p[3].append(p[1])
    p[0] = p[3]


def p_operand_list_term(p):
    'operand_list : operand'
    p[0] = [p[1]]


def p_ns_list_collect(p):
    """ns_list : ns_ref ',' ns_list"""
    p[3].append(p[1])
    p[0] = p[3]


def p_ns_list_term(p):
    'ns_list : ns_ref'
    p[0] = [p[1]]


def p_class_ref_direct(p):
    "class_ref : CID"
    p[0] = [p[1]]


def p_var_ref(p):
    "var_ref : ns_ref '.' varlist"
    p[0] = ('V', p[1], p[3])


def p_var_ref_2(p):
    "var_ref : ns_ref"
    p[0] = ('V', p[1], None)


def p_varlist_collect(p):
    """varlist : ID '.' varlist"""
    p[3].append(p[1])
    p[0] = p[3]


def p_varlist_term(p):
    'varlist : ID'
    p[0] = [p[1]]


def p_class_ref(p):
    "class_ref : ns_ref SEP CID"
    p[1].append(p[3])
    p[0] = p[1]


def p_ns_ref(p):
    "ns_ref : ns_ref SEP ID"
    p[1].append(p[3])
    p[0] = p[1]


def p_ns_ref_term(p):
    "ns_ref : ID"
    p[0] = [p[1]]


def p_id_list_collect(p):
    """id_list : ID "," id_list"""
    p[3].append(p[1])
    p[0] = p[3]


def p_id_list_term(p):
    'id_list : ID'
    p[0] = [p[1]]


def p_mls_term(p):
    "mls : MLS"
    p[0] = p[1]


def p_mls_collect(p):
    "mls : MLS mls"
    p[0] = "%s\n%s" % (p[1], p[2])


# Error rule for syntax errors
def p_error(p):
    print("Syntax error in input!", p)
    raise Exception()


# Build the parser
parser = yacc.yacc(debug=True)

f1 = "/home/wouter/projects/inmanta-infra/main.cf"
f2 = "/home/wouter/projects/inmanta-infra/libs/config/model/_init.cf"

now = time.time()
with open(f2, 'r') as myfile:
    data = myfile.read()

result = parser.parse(data, debug=False)
print(time.time() - now, result)
