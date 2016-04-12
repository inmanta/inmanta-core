'''
Created on Apr 10, 2016

@author: wouter
'''
import ply.lex as lex
from impera.parser import ParserException
from impera.ast.variables import Reference
from impera.ast.constraint.expression import Regex

states = (
    ('mls', 'exclusive'),
)

keyworldlist = ['typedef', 'as', 'matching', 'entity', 'extends', 'end', 'in',
                'implementation', 'for', 'index', 'implement', 'using', 'when', 'and', 'or', 'not', 'true', 'false']
literals = [':', '[', ']', '(', ')', '=', ',', '.']
reserved = {k: k.upper() for k in keyworldlist}

# List of token names.   This is always required
tokens = [
    'INT',
    'FLOAT',
    'ID',
    'CID',
    'SEP',
    'STRING',
    'MLS',
    'CMP_OP',
    'REGEX',
    'REL'
] + list(reserved.values())


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9-]*'
    t.type = reserved.get(t.value, 'ID')    # Check for reserved words
    if t.value[0].isupper():
        t.type = "CID"
    return t


def t_SEP(t):
    r'[:]{2}'
    return t


def t_REL(t):
    r'--|->|<-'
    return t


def t_CMP_OP(t):
    r'!=|==|>=|<=|<|>'
    return t


def t_COMMENT(t):
    r'\#.*?\n'
    pass


def t_JCOMMENT(t):
    r'\//.*?\n'
    pass


def t_begin_mls(t):
    r'["]{3}'
    t.lexer.begin('mls')


def t_mls_end(t):
    r'.*["]{3}'
    t.lexer.begin('INITIAL')
    t.type = "MLS"
    t.value = t.value[:-3]
    return t


def t_mls_MLS(t):
    r'.+'
    return t


def t_FLOAT(t):
    r'[0-9]*[.][0-9]+'
    t.value = float(t.value)
    return t


def t_INT(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t


def t_STRING_EMPTY(t):
    r'\"\"'
    t.type = "STRING"
    t.value = ""
    return t


def t_STRING(t):
    r'\".*?[^\\]\"'
    t.value = t.value[1: -1]
    return t


def t_REGEX(t):
    r'/[^/]*/'
    value = Reference("self")  # anonymous value
    expr = Regex(value, t.value[1:-1])
    t.value = expr
    return t

# Define a rule so we can track line numbers


def t_ANY_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore = ' \t'
t_mls_ignore = ''

# Error handling rule


def t_ANY_error(t):
    raise ParserException("",t.lexer.lineno, "Illegal character '%s' %s" % (t.value[0], t.lexer.lineno))


# Build the lexer
lexer = lex.lex()
