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
import ply.lex as lex
from inmanta.parser import ParserException
from inmanta.ast.variables import Reference
from inmanta.ast.constraint.expression import Regex
from inmanta.ast import LocatableString, Range

states = (
    ('mls', 'exclusive'),
)

keyworldlist = ['typedef', 'as', 'matching', 'entity', 'extends', 'end', 'in',
                'implementation', 'for', 'index', 'implement', 'using', 'when', 'and', 'or', 'not', 'true', 'false', 'import',
                'is', 'defined', 'dict', 'null', 'undef', "parents"]
literals = [':', '[', ']', '(', ')', '=', ',', '.', '{', '}', '?']
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
    'MLS_END',
    'CMP_OP',
    'REGEX',
    'REL',
    'PEQ'
] + sorted(list(reserved.values()))


def t_ID(t):  # noqa: N802
    r'[a-zA-Z_][a-zA-Z_0-9-]*'
    t.type = reserved.get(t.value, 'ID')  # Check for reserved words
    if t.value[0].isupper():
        t.type = "CID"
    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(t.value, Range(lexer.inmfile, lexer.lineno, start,
                                             lexer.lineno, end), lexer.lexpos, lexer.namespace)
    return t


def t_SEP(t):  # noqa: N802
    r'[:]{2}'
    return t


def t_REL(t):  # noqa: N802
    r'--|->|<-'
    return t


def t_CMP_OP(t):  # noqa: N802
    r'!=|==|>=|<=|<|>'
    return t


def t_PEQ(t):  # noqa: N802
    r'[+]='
    return t


def t_COMMENT(t):  # noqa: N802
    r'\#.*?\n'
    t.lexer.lineno += 1
    t.lexer.linestart = t.lexer.lexpos
    pass


def t_JCOMMENT(t):  # noqa: N802
    r'\//.*?\n'
    t.lexer.lineno += 1
    t.lexer.linestart = t.lexer.lexpos
    pass


def t_begin_mls(t):
    r'["]{3}'
    t.lexer.begin('mls')
    t.type = "MLS"

    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString("", Range(lexer.inmfile, lexer.lineno, start,
                                        lexer.lineno, end), lexer.lexpos, lexer.namespace)

    return t


def t_mls_end(t):
    r'.*["]{3}'
    t.lexer.begin('INITIAL')
    t.type = "MLS_END"
    value = t.value[:-3]

    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(value, Range(lexer.inmfile, lexer.lineno, start,
                                           lexer.lineno, end), lexer.lexpos, lexer.namespace)

    return t


def t_mls_MLS(t):  # noqa: N802
    r'.+'
    return t


def t_FLOAT(t):  # noqa: N802
    r'[-]?[0-9]*[.][0-9]+'
    t.value = float(t.value)
    return t


def t_INT(t):  # noqa: N802
    r'[-]?[0-9]+'
    t.value = int(t.value)
    return t


def t_STRING_EMPTY(t):  # noqa: N802
    r'(\"\")|(\'\')'
    t.type = "STRING"
    t.value = ""
    return t


def t_STRING(t):  # noqa: N802
    r'(\".*?[^\\]\")|(\'.*?[^\\]\')'
    t.value = bytes(t.value[1:-1], "utf-8").decode("unicode_escape")
    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(t.value, Range(lexer.inmfile, lexer.lineno, start,
                                             lexer.lineno, end), lexer.lexpos, lexer.namespace)

    return t


def t_REGEX(t):  # noqa: N802
    r'/([^/]|\\/)*?[^\\]/'
    value = Reference("self")  # anonymous value
    expr = Regex(value, t.value[1:-1])
    t.value = expr
    return t


# Define a rule so we can track line numbers
def t_newline(t):  # noqa: N802
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexer.lexpos


def t_mls_newline(t):  # noqa: N802
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexer.lexpos
    t.type = "MLS"
    return t


# A string containing ignored characters (spaces and tabs)
t_ignore = ' \t'
t_mls_ignore = ''

# Error handling rule


def t_ANY_error(t):  # noqa: N802
    value = t.value
    if len(value) > 10:
        value = value[:10]

    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    r = Range(lexer.inmfile, lexer.lineno, start, lexer.lineno, end)

    raise ParserException("", r, value)


# Build the lexer
lexer = lex.lex()
