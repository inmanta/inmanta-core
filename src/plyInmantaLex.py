'''
Created on Apr 10, 2016

@author: wouter
'''
import ply.lex as lex
import time

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
    r'[-]{2}'
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

t_INT = r'[0-9]+'
t_FLOAT = r'[0-9]*[.][0-9]+'


def t_STRING_EMPTY(t):
    r'\"\"'
    t.type = "STRING"
    return t

t_STRING = r'\".*?[^\\]\"'
t_REGEX = r'/[^/]*/'

# Define a rule so we can track line numbers


def t_ANY_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore = ' \t'

# Error handling rule


def t_ANY_error(t):
    print("Illegal character '%s' %s" % (t.value[0], t.lexer.lineno))
    t.lexer.skip(1)


# Build the lexer
lexer = lex.lex()


def test():
    f1 = "/home/wouter/projects/inmanta-infra/main.cf"
    f2 = "/home/wouter/projects/inmanta-infra/libs/config/model/_init.cf"

    now = time.time()
    with open(f2, 'r') as myfile:
        data = myfile.read()

        # Give the lexer some input
        lexer.input(data)

        # Tokenize
        i = 0
        while True:
            tok = lexer.token()
            if not tok:
                break      # No more input
            # print(tok)
            i = i + 1
    print(time.time() - now)

# test()
