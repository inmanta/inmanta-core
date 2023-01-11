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
import typing
import warnings
from re import error as RegexError

import ply.lex as lex

from inmanta.ast import LocatableString, Location, Range
from inmanta.ast.constraint.expression import Regex
from inmanta.ast.variables import Reference
from inmanta.parser import ParserException, ParserWarning

keyworldlist = [
    "typedef",
    "as",
    "matching",
    "entity",
    "extends",
    "end",
    "in",
    "implementation",
    "for",
    "index",
    "implement",
    "using",
    "when",
    "and",
    "or",
    "not",
    "true",
    "false",
    "import",
    "is",
    "defined",
    "dict",
    "null",
    "undef",
    "parents",
    "if",
    "else",
    "elif",
]
literals = [":", "[", "]", "(", ")", "=", ",", ".", "{", "}", "?", "*"]
reserved = {k: k.upper() for k in keyworldlist}

# List of token names.   This is always required
tokens = ["INT", "FLOAT", "ID", "CID", "SEP", "STRING", "MLS", "CMP_OP", "REGEX", "REL", "PEQ", "RSTRING"] + sorted(
    list(reserved.values())
)


def t_RSTRING(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"r(\"([^\\\"\n]|\\.)*\")|r(\'([^\\\'\n]|\\.)*\')"
    t.value = t.value[2:-1]
    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(
        t.value, Range(lexer.inmfile, lexer.lineno, start, lexer.lineno, end), lexer.lexpos, lexer.namespace
    )

    return t


def t_ID(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"[a-zA-Z_][a-zA-Z_0-9-]*"
    t.type = reserved.get(t.value, "ID")  # Check for reserved words
    if t.value[0].isupper():
        t.type = "CID"
    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(
        t.value, Range(lexer.inmfile, lexer.lineno, start, lexer.lineno, end), lexer.lexpos, lexer.namespace
    )
    return t


def t_SEP(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"[:]{2}"
    return t


def t_REL(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"--|->|<-"
    return t


def t_CMP_OP(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"!=|==|>=|<=|<|>"
    return t


def t_PEQ(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"[+]="
    return t


def t_COMMENT(t: lex.LexToken) -> None:  # noqa: N802
    r"\#.*?\n"
    t.lexer.lineno += 1
    t.lexer.linestart = t.lexer.lexpos
    pass


def t_JCOMMENT(t: lex.LexToken) -> None:  # noqa: N802
    r"\//.*?\n"
    t.lexer.lineno += 1
    t.lexer.linestart = t.lexer.lexpos
    pass


def t_MLS(t: lex.LexToken) -> lex.LexToken:
    r'"{3,5}([\s\S]*?)"{3,5}'

    value = safe_decode(token=t, warning_message="Invalid escape sequence in multi-line string.", start=3, end=-3)

    lexer = t.lexer
    match = lexer.lexmatch[0]
    lines = match.split("\n")
    start_line = lexer.lineno
    end_line = lexer.lineno + len(lines) - 1
    t.lexer.lineno = end_line
    (s, e) = lexer.lexmatch.span()
    start = lexer.lexpos - lexer.linestart - (e - s) + 1
    end = len(lines[-1]) + 1

    t.value = LocatableString(value, Range(lexer.inmfile, start_line, start, end_line, end), lexer.lexpos, lexer.namespace)

    return t


def t_FLOAT(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"[-]?[0-9]*[.][0-9]+"
    t.value = float(t.value)
    return t


def t_INT(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"[-]?[0-9]+"
    t.value = int(t.value)
    return t


def t_STRING(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"(\"([^\\\"\n]|\\.)*\")|(\'([^\\\'\n]|\\.)*\')"

    t.value = safe_decode(token=t, warning_message="Invalid escape sequence in string.", start=1, end=-1)

    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    (s, e) = lexer.lexmatch.span()
    start = end - (e - s)

    t.value = LocatableString(
        t.value, Range(lexer.inmfile, lexer.lineno, start, lexer.lineno, end), lexer.lexpos, lexer.namespace
    )

    return t


def t_REGEX(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    r"/([^/\\]|\\.)+/"
    value = Reference("self")  # anonymous value
    try:
        expr = Regex(value, t.value[1:-1])
        t.value = expr
        return t
    except RegexError as error:
        end = t.lexer.lexpos - t.lexer.linestart + 1
        (s, e) = t.lexer.lexmatch.span()
        start = end - (e - s)

        r: Range = Range(t.lexer.inmfile, t.lexer.lineno, start, t.lexer.lineno, end)
        raise ParserException(r, t.value, "Regex error in %s: '%s'" % (t.value, error))


# Define a rule so we can track line numbers
def t_newline(t: lex.LexToken) -> None:  # noqa: N802
    r"\n+"
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexer.lexpos


# A string containing ignored characters (spaces and tabs)
t_ignore = " \t"
# Error handling rule


def t_ANY_error(t: lex.LexToken) -> lex.LexToken:  # noqa: N802
    lexer = t.lexer

    end = lexer.lexpos - lexer.linestart + 1
    char: str = t.value[0]
    r: Range = Range(lexer.inmfile, lexer.lineno, end, lexer.lineno, end + 1)
    raise ParserException(r, char, "Illegal character '%s'" % char)


# Build the lexer
lexer = lex.lex()


def safe_decode(token: lex.LexToken, warning_message: str, start: int = 1, end: int = -1) -> str:
    """
    Check for the presence of an invalid escape sequence (e.g. "\.") in the value attribute of a given token.  # noqa: W605
    This function assumes to be called from within a t_STRING or a t_MLS rule.

    - Python < 3.12 raises a DeprecationWarning when encountering an invalid escape sequence
    - Python 3.12 will raise a SyntaxWarning
    - Future versions will eventually raise a SyntaxError
    (see https://docs.python.org/3.12/whatsnew/3.12.html#other-language-changes )

    :param token: The token whose value we want to decode.
    :param warning_message: The warning message to display.
    :param start: Start of the value slice (To only decode the characters after the leading quotation mark(s))
    :param end: End of the value slice (To only decode the characters before the trailing quotation mark(s))

    :return: The token value as a python str.
    """

    try:
        # This first block will try to decode the value and turn any deprecation warning into an actual Exception.
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="invalid escape sequence", category=DeprecationWarning)
            value: str = bytes(typing.cast(str, token.value)[start:end], "utf_8").decode("unicode_escape")
    except DeprecationWarning:
        # If the first block did actually encounter an invalid escape sequence, we have to decode the value again, this time
        # ignoring this or any other python warning that has already been emitted, and raising a warning of our own.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            value = bytes(typing.cast(str, token.value)[start:end], "utf_8").decode("unicode_escape")

        warnings.warn(
            ParserWarning(location=Location(file=token.lexer.inmfile, lnr=token.lexer.lineno), msg=warning_message, value=value)
        )

    return value
