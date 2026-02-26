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

import bisect
import functools
import logging
import re
import string
import typing
import warnings
from collections import abc
from dataclasses import dataclass
from re import error as RegexError
from typing import Callable, Optional, Union

import pe
from inmanta.ast import LocatableString, Location, Namespace, Range, RuntimeException
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.constraint.expression import And as AstAnd
from inmanta.ast.constraint.expression import In, IsDefined
from inmanta.ast.constraint.expression import Not as AstNot
from inmanta.ast.constraint.expression import NotEqual, Operator
from inmanta.ast.constraint.expression import Regex as AstRegex
from inmanta.ast.statements import DynamicStatement, ExpressionStatement, Literal, ReferenceStatement, Statement
from inmanta.ast.statements.assign import (
    CreateDict,
    CreateList,
    IndexLookup,
    MapLookup,
    ShortIndexLookup,
    StringFormat,
    StringFormatV2,
)
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
    TypeDeclaration,
)
from inmanta.ast.statements.generator import ConditionalExpression, Constructor, For, If, ListComprehension, WrappedKwargs
from inmanta.ast.variables import AttributeReference, Reference
from inmanta.execute.util import NoneValue
from inmanta.parser import InvalidNamespaceAccess, ParserException, ParserWarning
from inmanta.parser.cache import CacheManager
from pe._grammar import Grammar
from pe.actions import Action
from pe.operators import AutoIgnore
from pe.operators import Capture as Cap
from pe.operators import Choice as Ch
from pe.operators import Class
from pe.operators import Dot as DOT
from pe.operators import Literal as Lit
from pe.operators import Nonterminal as NT
from pe.operators import Not
from pe.operators import Optional as Opt
from pe.operators import Plus, Regex
from pe.operators import Sequence as Seq
from pe.operators import Star
from pe.packrat import PackratParser

LOGGER = logging.getLogger(__name__)

# Set of all reserved keywords in the Inmanta DSL
_KEYWORDS: frozenset[str] = frozenset(
    [
        "typedef",
        "as",
        "entity",
        "extends",
        "end",
        "in",
        "implementation",
        "for",
        "matching",
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
)

# ---------------------------------------------------------------------------
# Parse state – updated before each parse call
# ---------------------------------------------------------------------------


class PositionTracker:
    """Convert a flat character offset to (line_nr, col) using bisect."""

    def __init__(self, text: str) -> None:
        self._line_starts: list[int] = [0]
        for i, c in enumerate(text):
            if c == "\n":
                self._line_starts.append(i + 1)

    def pos_to_lnr_col(self, pos: int) -> tuple[int, int]:
        idx = bisect.bisect_right(self._line_starts, pos) - 1
        return idx + 1, pos - self._line_starts[idx] + 1


@dataclass
class _ParseState:
    filename: str = "NOFILE"
    namespace: Optional[Namespace] = None
    tracker: Optional[PositionTracker] = None


_state: _ParseState = _ParseState()

# ---------------------------------------------------------------------------
# Helper: create AST location objects from a pe position
# ---------------------------------------------------------------------------


def _make_locatable(pos: int, end: int, text: str) -> LocatableString:
    assert _state.tracker is not None
    assert _state.namespace is not None
    tracker = _state.tracker
    start_lnr, start_col = tracker.pos_to_lnr_col(pos)
    end_lnr, end_col = tracker.pos_to_lnr_col(max(pos, end - 1))
    r = Range(_state.filename, start_lnr, start_col, end_lnr, end_col + 1)
    return LocatableString(text, r, pos, _state.namespace)


def _make_location(pos: int) -> Location:
    assert _state.tracker is not None
    lnr, _ = _state.tracker.pos_to_lnr_col(pos)
    return Location(_state.filename, lnr)


def _make_range(pos: int, end: int) -> Range:
    assert _state.tracker is not None
    start_lnr, start_col = _state.tracker.pos_to_lnr_col(pos)
    end_lnr, end_col = _state.tracker.pos_to_lnr_col(max(pos, end - 1))
    return Range(_state.filename, start_lnr, start_col, end_lnr, end_col + 1)


def _expand_range(start: Range, end: Range) -> Range:
    return Range(start.file, start.lnr, start.start_char, end.end_lnr, end.end_char)


def _locate(node: object, pos: int) -> object:
    """Attach location info to an ExpressionStatement/Statement."""
    assert _state.namespace is not None
    n = typing.cast(ExpressionStatement, node)
    n.location = _make_location(pos)
    n.namespace = _state.namespace
    n.lexpos = pos
    return n


def _locate_from_ls(node: object, ls: LocatableString) -> object:
    n = typing.cast(ExpressionStatement, node)
    n.location = ls.location
    n.namespace = ls.namespace
    n.lexpos = ls.lexpos
    return n


# ---------------------------------------------------------------------------
# Custom Action wrapper
# ---------------------------------------------------------------------------


class PosAction(Action):  # type: ignore[misc]
    """Action that receives (s, pos, end, args) and returns a single value."""

    def __init__(self, func: Callable[..., object]) -> None:
        self.func = func

    def __call__(
        self,
        s: str,
        pos: int,
        end: int,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> tuple[tuple[object, ...], Optional[dict[str, object]]]:
        result = self.func(s, pos, end, list(args))
        return (result,), None


def P(fn: Callable[..., object]) -> PosAction:
    return PosAction(fn)


# ---------------------------------------------------------------------------
# String helper functions (replicated from PLY lexer / parser)
# ---------------------------------------------------------------------------

format_regex = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
format_regex_compiled = re.compile(format_regex, re.MULTILINE | re.DOTALL)


def _safe_decode(raw: str, warning_message: str, start: int = 1, end: int = -1, location: Optional[Location] = None) -> str:
    """Decode escape sequences in a string literal, emitting a ParserWarning on invalid escapes."""
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="invalid escape sequence", category=DeprecationWarning)
            value: str = bytes(raw[start:end], "utf_8").decode("unicode_escape")
    except DeprecationWarning:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            value = bytes(raw[start:end], "utf_8").decode("unicode_escape")
        if location is not None:
            warnings.warn(ParserWarning(location=location, msg=warning_message, value=value))
    return value


def get_string_ast_node(string_ast: LocatableString, mls: bool) -> Union[Literal, StringFormat]:
    matches: list[re.Match[str]] = list(format_regex_compiled.finditer(str(string_ast)))
    if len(matches) == 0:
        return Literal(str(string_ast))

    start_lnr = string_ast.location.lnr
    start_char_pos = string_ast.location.start_char
    whole_string = str(string_ast)
    mls_offset: int = 3 if mls else 1

    def char_count_to_lnr_char(position: int) -> tuple[int, int]:
        before = whole_string[0:position]
        lines = before.count("\n")
        if lines == 0:
            return start_lnr, start_char_pos + position + mls_offset
        else:
            return start_lnr + lines, position - before.rindex("\n")

    locatable_matches: list[tuple[str, LocatableString]] = []
    for match in matches:
        start_line, start_char = char_count_to_lnr_char(match.start(2))
        end_line, end_char = char_count_to_lnr_char(match.end(2))
        r: Range = Range(string_ast.location.file, start_line, start_char, end_line, end_char)
        locatable_string = LocatableString(match[2], r, string_ast.lexpos, string_ast.namespace)
        locatable_matches.append((match[1], locatable_string))

    return StringFormat(str(string_ast), convert_to_references(locatable_matches))


def convert_to_references(variables: list[tuple[str, LocatableString]]) -> list[tuple["Reference", str]]:
    assert _state.namespace is not None
    ns = _state.namespace

    def normalize(variable: str, locatable: LocatableString, offset: int = 0) -> LocatableString:
        start_char = locatable.location.start_char + offset
        end_char = start_char + len(variable)
        variable_left_trim = variable.lstrip()
        left_spaces: int = len(variable) - len(variable_left_trim)
        variable_full_trim = variable_left_trim.rstrip()
        right_spaces: int = len(variable_left_trim) - len(variable_full_trim)
        r: Range = Range(
            locatable.location.file,
            locatable.location.lnr,
            start_char + left_spaces,
            locatable.location.lnr,
            end_char - right_spaces,
        )
        return LocatableString(variable_full_trim, r, locatable.lexpos, locatable.namespace)

    _vars: list[tuple[Reference, str]] = []
    for match, var in variables:
        var_name: str = str(var)
        var_parts: list[str] = var_name.split(".")
        ref_locatable_string: LocatableString = normalize(var_parts[0], var)
        ref: Reference = Reference(ref_locatable_string)
        ref.location = ref_locatable_string.location
        ref.namespace = ns
        if len(var_parts) > 1:
            offset = len(var_parts[0]) + 1
            for attr in var_parts[1:]:
                attr_locatable_string: LocatableString = normalize(attr, var, offset=offset)
                ref = AttributeReference(ref, attr_locatable_string)
                ref.location = attr_locatable_string.location
                ref.namespace = ns
                offset += len(attr) + 1
            _vars.append((ref, match))
        else:
            _vars.append((ref, match))
    return _vars


# ---------------------------------------------------------------------------
# ForSpecifier dataclass (used in list comprehension parsing)
# ---------------------------------------------------------------------------


@dataclass
class ForSpecifier:
    variable: LocatableString
    iterable: ExpressionStatement
    guard: Optional[ExpressionStatement] = None


# ---------------------------------------------------------------------------
# Lazy parser singleton
# ---------------------------------------------------------------------------

_parser: Optional[PackratParser] = None

# Concrete Operator subclasses have __init__(op1, op2), but get_operator_class() returns
# Type[Operator] whose base __init__ signature doesn't match. Use this alias for casts.
_BinaryOpFactory = Callable[[ExpressionStatement, ExpressionStatement], Operator]


def _build_parser() -> PackratParser:  # noqa: C901
    """Build and return the pe PackratParser (called once)."""

    # ------------------------------------------------------------------
    # Whitespace / comment (shared primitives, used only for PackratParser ignore)
    # ------------------------------------------------------------------
    COMMENT = Seq(Lit("#"), Star(Seq(Not(Lit("\n")), DOT())), Opt(Lit("\n")))
    WS_ELEM = Ch(Class(" \t\n\r"), COMMENT)
    WS = Star(WS_ELEM)

    # ------------------------------------------------------------------
    # Keyword rules: use Regex so they're Primary (not split by autoignore).
    # Each keyword regex uses a negative lookahead to prevent matching idents.
    # ------------------------------------------------------------------
    IDENT_CONT_PAT = r"(?![a-zA-Z0-9_\-])"

    def kw(word: str) -> object:
        """Return a Regex that matches 'word' only when not followed by ident chars."""
        return Regex(word + IDENT_CONT_PAT)

    KW_TYPEDEF = kw("typedef")
    KW_AS = kw("as")
    KW_ENTITY = kw("entity")
    KW_EXTENDS = kw("extends")
    KW_END = kw("end")
    KW_IN = kw("in")
    KW_IMPLEMENTATION = kw("implementation")
    KW_FOR = kw("for")
    KW_INDEX = kw("index")
    KW_IMPLEMENT = kw("implement")
    KW_USING = kw("using")
    KW_WHEN = kw("when")
    KW_AND = kw("and")
    KW_OR = kw("or")
    KW_NOT = kw("not")
    KW_TRUE = kw("true")
    KW_FALSE = kw("false")
    KW_IMPORT = kw("import")
    KW_IS = kw("is")
    KW_DEFINED = kw("defined")
    KW_DICT = kw("dict")
    KW_NULL = kw("null")
    KW_UNDEF = kw("undef")
    KW_PARENTS = kw("parents")
    KW_IF = kw("if")
    KW_ELSE = kw("else")
    KW_ELIF = kw("elif")
    KW_MATCHING = kw("matching")

    # All keywords as a single Regex alternative for negative lookahead in ID
    all_kw_words = [
        "typedef",
        "as",
        "entity",
        "extends",
        "end",
        "in",
        "implementation",
        "for",
        "matching",
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
    # Sort longest first so "implement" matches before "in", etc.
    all_kw_words_sorted = sorted(all_kw_words, key=len, reverse=True)
    KEYWORD_REGEX = Regex(r"(?:" + "|".join(re.escape(w) for w in all_kw_words_sorted) + r")" + IDENT_CONT_PAT)

    # ------------------------------------------------------------------
    # Basic token patterns (all Regex = Primary type, won't be split by autoignore)
    # ------------------------------------------------------------------
    MLS_PAT = AutoIgnore(Cap(Regex(r'"{3,5}[\s\S]*?"{3,5}')))
    FSTRING_PAT = AutoIgnore(Cap(Regex(r'f"(?:[^\\"\n]|\\.)*"|f\'(?:[^\\\'\n]|\\.)*\'')))
    RSTRING_PAT = AutoIgnore(Cap(Regex(r'r"(?:[^\\"\n]|\\.)*"|r\'(?:[^\\\'\n]|\\.)*\'')))
    STRING_PAT = AutoIgnore(Cap(Regex(r'"(?:[^\\"\n]|\\.)*"|\'(?:[^\\\'\n]|\\.)*\'')))
    REGEX_TOKEN_PAT = AutoIgnore(Cap(Regex(r"matching\s+/(?:[^/\\\n]|\\.)+/")))
    # Patterns for unclosed single-line strings (contain newline before closing quote)
    # These are error patterns — their actions raise ParserException("Illegal character")
    ILLEGAL_STRING_DBL_PAT = AutoIgnore(Cap(Regex(r'"[^"\n]*\n')))
    ILLEGAL_STRING_SGL_PAT = AutoIgnore(Cap(Regex(r"'[^'\n]*\n")))
    ILLEGAL_FSTRING_DBL_PAT = AutoIgnore(Cap(Regex(r'f"[^"\n]*\n')))
    ILLEGAL_FSTRING_SGL_PAT = AutoIgnore(Cap(Regex(r"f'[^'\n]*\n")))
    ILLEGAL_RSTRING_DBL_PAT = AutoIgnore(Cap(Regex(r'r"[^"\n]*\n')))
    ILLEGAL_RSTRING_SGL_PAT = AutoIgnore(Cap(Regex(r"r'[^'\n]*\n")))
    FLOAT_PAT = AutoIgnore(Cap(Regex(r"-?[0-9]*\.[0-9]+")))
    INT_PAT = AutoIgnore(Cap(Regex(r"-?[0-9]+")))
    # ID: not a keyword, then lowercase-start ident
    ID_PAT = AutoIgnore(Seq(Not(KEYWORD_REGEX), Cap(Regex(r"[a-z_][a-zA-Z0-9_\-]*"))))
    CID_PAT = AutoIgnore(Cap(Regex(r"[A-Z][a-zA-Z0-9_\-]*")))

    # Punctuation: use Regex (Primary) to avoid autoignore splitting
    # The PackratParser ignore handles whitespace before each token.
    SEP = Regex(r"::")
    REL_PAT = AutoIgnore(Regex(r"--|->|<-"))
    CMP_OP_PAT = AutoIgnore(Cap(Regex(r"!=|==|>=|<=|<|>")))
    PEQ = Regex(r"\+=")

    LPAREN = Regex(r"\(")
    RPAREN = Regex(r"\)")
    LBRACK = Regex(r"\[")
    RBRACK = Regex(r"\]")
    LBRACE = Regex(r"\{")
    RBRACE = Regex(r"\}")
    COMMA = Regex(r",")
    DOT_OP = Regex(r"\.")
    # COLON: matches ':' but not '::'
    COLON = Regex(r":(?!:)")
    # EQUALS: matches '=' but not '==' or '=>'
    EQUALS = Regex(r"=(?![=>])")
    PLUS_OP = Cap(Regex(r"\+"))
    MINUS_OP = Cap(Regex(r"-"))
    DOUBLE_STAR = Regex(r"\*\*")
    STAR_OP = Cap(Regex(r"\*"))
    SLASH_OP = Cap(Regex(r"/"))
    PERCENT_OP = Cap(Regex(r"%"))
    QUESTION_OP = Regex(r"\?")

    # ------------------------------------------------------------------
    # Actions for token rules
    # ------------------------------------------------------------------

    def act_ID(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        return _make_locatable(pos, end, str(args[0]))

    def act_CID(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        return _make_locatable(pos, end, str(args[0]))

    def act_INT(s: str, pos: int, end: int, args: list[object]) -> Literal:
        return Literal(int(str(args[0])))

    def act_FLOAT(s: str, pos: int, end: int, args: list[object]) -> Literal:
        return Literal(float(str(args[0])))

    def act_STRING(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        raw = str(args[0])
        loc = _make_location(pos)
        value = _safe_decode(raw, "Invalid escape sequence in string.", start=1, end=-1, location=loc)
        return _make_locatable(pos, end, value)

    def act_MLS(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        raw = str(args[0])
        loc = _make_location(pos)
        value = _safe_decode(raw, "Invalid escape sequence in multi-line string.", start=3, end=-3, location=loc)
        assert _state.tracker is not None
        assert _state.namespace is not None
        start_lnr, start_col = _state.tracker.pos_to_lnr_col(pos)
        lines = raw.split("\n")
        end_lnr = start_lnr + len(lines) - 1
        end_col_val = len(lines[-1]) + 1
        r = Range(_state.filename, start_lnr, start_col, end_lnr, end_col_val)
        return LocatableString(value, r, pos, _state.namespace)

    def act_FSTRING(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        raw = str(args[0])
        loc = _make_location(pos)
        value = _safe_decode(raw, "Invalid escape sequence in f-string.", start=2, end=-1, location=loc)
        return _make_locatable(pos, end, value)

    def act_RSTRING(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        raw = str(args[0])
        value = raw[2:-1]
        return _make_locatable(pos, end, value)

    def _act_illegal_string(pos: int, quote_char: str, prefix_len: int) -> None:
        """Raise a PLY-compatible 'Illegal character' ParserException."""
        assert _state.tracker is not None
        # The error position is at the opening quote, which is at pos + prefix_len
        char_pos = pos + prefix_len
        lnr, col = _state.tracker.pos_to_lnr_col(char_pos)
        r = Range(_state.filename, lnr, col, lnr, col + 1)
        raise ParserException(r, quote_char, f"Illegal character '{quote_char}'")

    def act_illegal_string_dbl(s: str, pos: int, end: int, args: list[object]) -> None:
        """Matched an unclosed double-quoted string (contains newline) — raise lexer-style error."""
        _act_illegal_string(pos, '"', 0)

    def act_illegal_string_sgl(s: str, pos: int, end: int, args: list[object]) -> None:
        """Matched an unclosed single-quoted string (contains newline) — raise lexer-style error."""
        _act_illegal_string(pos, "'", 0)

    def act_illegal_prefixed_string_dbl(s: str, pos: int, end: int, args: list[object]) -> None:
        """Matched an unclosed double-quoted f/r-string (contains newline) — raise lexer-style error."""
        _act_illegal_string(pos, '"', 1)

    def act_illegal_prefixed_string_sgl(s: str, pos: int, end: int, args: list[object]) -> None:
        """Matched an unclosed single-quoted f/r-string (contains newline) — raise lexer-style error."""
        _act_illegal_string(pos, "'", 1)

    def act_REGEX_TOKEN(s: str, pos: int, end: int, args: list[object]) -> AstRegex:
        raw = str(args[0])
        index_first_slash = raw.index("/")
        regex_with_slashes = raw[index_first_slash:]
        regex_as_str = regex_with_slashes[1:-1]
        value = Reference(_make_locatable(pos, end, "self"))
        try:
            return AstRegex(value, regex_as_str)
        except RegexError as error:
            r = _make_range(pos + index_first_slash, end)
            raise ParserException(r, regex_with_slashes, f"Regex error in {regex_with_slashes}: '{error}'")

    # ------------------------------------------------------------------
    # Reference rules
    # ------------------------------------------------------------------

    def act_ns_ref(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        parts: list[LocatableString] = [typing.cast(LocatableString, a) for a in args]
        if len(parts) == 1:
            return parts[0]
        combined = "::".join(str(p) for p in parts)
        first = parts[0]
        last = parts[-1]
        r = _expand_range(first.location, last.location)
        assert _state.namespace is not None
        return LocatableString(combined, r, first.lexpos, _state.namespace)

    def act_class_ref_qualified(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        # ns_ref SEP CID -> "ns::CID"
        ns_r = typing.cast(LocatableString, args[0])
        cid = typing.cast(LocatableString, args[1])
        combined = f"{str(ns_r)}::{str(cid)}"
        assert _state.namespace is not None
        r = _expand_range(ns_r.location, cid.location)
        return LocatableString(combined, r, ns_r.lexpos, _state.namespace)

    def act_class_ref_simple(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        return typing.cast(LocatableString, args[0])

    def act_class_ref_dot_err(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        var = args[0]
        cid = typing.cast(LocatableString, args[1])
        assert _state.namespace is not None
        if isinstance(var, LocatableString):
            var_str: LocatableString = var
        else:
            var_str = typing.cast(Reference, var).locatable_name
        full = LocatableString(
            f"{var_str}.{cid}",
            _expand_range(var_str.location, cid.location),
            var_str.lexpos,
            _state.namespace,
        )
        raise InvalidNamespaceAccess(full)

    def act_class_ref_id_err(s: str, pos: int, end: int, args: list[object]) -> None:
        """Raise error for lowercase class reference (in class_ref_list context)."""
        ls = typing.cast(LocatableString, args[0])
        raise ParserException(ls.location, str(ls), "Invalid identifier: Entity names must start with a capital")

    def act_var_ref(s: str, pos: int, end: int, args: list[object]) -> Union[Reference, AttributeReference]:
        assert _state.namespace is not None
        ns_r = typing.cast(LocatableString, args[0])
        ref: Union[Reference, AttributeReference] = Reference(ns_r)
        # PLY: attach_from_string → uses ns_ref's location (Range with column)
        ref.location = ns_r.location
        ref.namespace = _state.namespace
        ref.lexpos = ns_r.lexpos
        for attr in args[1:]:
            ls = typing.cast(LocatableString, attr)
            new_ref: AttributeReference = AttributeReference(ref, ls)
            # PLY: attach_lnr(p, 2) on "attr_ref : var_ref '.' ID" → Location (no column)
            new_ref.location = _make_location(ls.lexpos)
            new_ref.namespace = _state.namespace
            new_ref.lexpos = ls.lexpos
            ref = new_ref
        return ref

    def act_attr_ref(s: str, pos: int, end: int, args: list[object]) -> AttributeReference:
        return typing.cast(AttributeReference, act_var_ref(s, pos, end, args))

    # ------------------------------------------------------------------
    # Constant actions
    # ------------------------------------------------------------------

    def act_constant_INT(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        node = typing.cast(Literal, args[0])
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_constant_FLOAT(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        node = typing.cast(Literal, args[0])
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_constant_NULL(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        node = Literal(NoneValue())
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_constant_TRUE(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        node = Literal(True)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_constant_FALSE(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        node = Literal(False)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_constant_STRING(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        ls = typing.cast(LocatableString, args[0])
        node = get_string_ast_node(ls, False)
        # PLY uses attach_lnr (Location, no column) for STRING tokens
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = ls.lexpos
        return node

    def act_constant_MLS(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        ls = typing.cast(LocatableString, args[0])
        node = get_string_ast_node(ls, True)
        node.location = ls.location
        node.namespace = _state.namespace
        node.lexpos = ls.lexpos
        return node

    def act_constant_FSTRING(s: str, pos: int, end: int, args: list[object]) -> StringFormatV2:
        assert _state.namespace is not None
        ls = typing.cast(LocatableString, args[0])
        formatter = string.Formatter()
        try:
            parsed = list(formatter.parse(str(ls)))
        except ValueError as e:
            raise ParserException(ls.location, str(ls), f"Invalid f-string: {e}")

        start_lnr = ls.location.lnr
        start_char_pos = ls.location.start_char + 2  # skip f"

        locatable_matches: list[tuple[str, LocatableString]] = []

        def locate_match(match: tuple[str, Optional[str], Optional[str], Optional[str]], scp: int, ecp: int) -> None:
            assert match[1]
            r = Range(ls.location.file, start_lnr, scp, start_lnr, ecp)
            locatable_string = LocatableString(match[1], r, ls.lexpos, ls.namespace)
            locatable_matches.append((match[1], locatable_string))

        for match in parsed:
            if not match[1]:
                break
            literal_text_len = len(match[0])
            field_name_len = len(match[1])
            brackets_length = 1 if field_name_len else 0
            start_char_pos += literal_text_len + brackets_length
            end_char = start_char_pos + field_name_len

            locate_match(match, start_char_pos, end_char)
            start_char_pos += field_name_len

            if match[2]:
                start_char_pos += 1
                sub_parsed = formatter.parse(match[2])
                for submatch in sub_parsed:
                    if not submatch[1]:
                        break
                    ll = len(submatch[0])
                    ifl = len(submatch[1])
                    ibl = 1 if ifl else 0
                    start_char_pos += ll + ibl
                    ecp2 = start_char_pos + ifl
                    locate_match(submatch, start_char_pos, ecp2)
                    start_char_pos += ifl + ibl

            start_char_pos += brackets_length

        node = StringFormatV2(str(ls), convert_to_references(locatable_matches))
        node.location = ls.location
        node.namespace = _state.namespace
        node.lexpos = ls.lexpos
        return node

    def act_constant_RSTRING(s: str, pos: int, end: int, args: list[object]) -> Literal:
        assert _state.namespace is not None
        ls = typing.cast(LocatableString, args[0])
        node = Literal(str(ls))
        node.location = ls.location
        node.namespace = _state.namespace
        node.lexpos = ls.lexpos
        return node

    def act_constant_REGEX(s: str, pos: int, end: int, args: list[object]) -> AstRegex:
        assert _state.namespace is not None
        node = typing.cast(AstRegex, args[0])
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    # ------------------------------------------------------------------
    # Expression actions
    # ------------------------------------------------------------------

    def act_cond_expr(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        # Seq(or_expr, QUESTION, cond_expr, COLON, cond_expr)
        # PLY uses attach_from_string(p, 1) — takes location from the condition expression
        assert _state.namespace is not None
        cond = typing.cast(ExpressionStatement, args[0])
        true_expr = typing.cast(ExpressionStatement, args[1])
        false_expr = typing.cast(ExpressionStatement, args[2])
        node = ConditionalExpression(cond, true_expr, false_expr)
        node.location = cond.location
        node.namespace = cond.namespace if cond.namespace is not None else _state.namespace
        node.lexpos = cond.lexpos
        return node

    def act_or_expr(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        # Seq(and_expr, and_expr, ...) – fold left
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        for right in args[1:]:
            op_cls = Operator.get_operator_class("or")
            assert op_cls is not None
            node = typing.cast(_BinaryOpFactory, op_cls)(left, typing.cast(ExpressionStatement, right))
            node.location = _make_location(pos)
            node.namespace = _state.namespace
            node.lexpos = pos
            left = node
        return left

    def act_and_expr(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        for right in args[1:]:
            op_cls = Operator.get_operator_class("and")
            assert op_cls is not None
            node = typing.cast(_BinaryOpFactory, op_cls)(left, typing.cast(ExpressionStatement, right))
            node.location = _make_location(pos)
            node.namespace = _state.namespace
            node.lexpos = pos
            left = node
        return left

    def act_not_expr_not(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        # NOT not_expr
        assert _state.namespace is not None
        inner = typing.cast(ExpressionStatement, args[0])
        node: AstNot = AstNot(inner)  # type: ignore[no-untyped-call]
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_cmp_is_defined(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        """Handle 'postfix_expr is defined'."""
        assert _state.namespace is not None
        expr = args[0]
        if isinstance(expr, AttributeReference):
            node_is: IsDefined = IsDefined(expr.instance, expr.attribute)
        elif isinstance(expr, Reference):
            node_is = IsDefined(None, expr.locatable_name)
        elif isinstance(expr, MapLookup):
            # syntactic sugar for map key existence
            location = expr.location
            lexpos = expr.lexpos
            ns: Namespace = _state.namespace

            def _att(inp: ExpressionStatement) -> ExpressionStatement:
                inp.location = location
                inp.lexpos = lexpos
                inp.namespace = ns
                return inp

            key_in_dict = _att(In(expr.key, expr.themap))
            not_none = _att(NotEqual(expr, _att(Literal(NoneValue()))))
            not_empty_list = _att(NotEqual(expr, _att(CreateList(list()))))
            out = _att(AstAnd(_att(AstAnd(key_in_dict, not_none)), not_empty_list))
            return out
        else:
            raise ParserException(
                _make_location(pos),
                str(expr),
                "'is defined' can only be applied to a variable reference or map lookup",
            )
        node_is.location = _make_location(pos)
        node_is.namespace = _state.namespace
        node_is.lexpos = pos
        return node_is

    def act_cmp_not_in(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        right = typing.cast(ExpressionStatement, args[1])
        inner = In(left, right)
        inner.location = _make_location(pos)
        inner.namespace = _state.namespace
        inner.lexpos = pos
        node: AstNot = AstNot(inner)  # type: ignore[no-untyped-call]
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_cmp_in(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        right = typing.cast(ExpressionStatement, args[1])
        node: In = In(left, right)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_cmp_op(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        op_str = str(args[1])
        right = typing.cast(ExpressionStatement, args[2])
        op_cls = Operator.get_operator_class(op_str)
        if op_cls is None:
            raise ParserException(_make_location(pos), op_str, f"Invalid operator {op_str}")
        node = typing.cast(_BinaryOpFactory, op_cls)(left, right)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_additive(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        # args: left, op1, right1, op2, right2, ...
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        i = 1
        while i < len(args):
            op_str = str(args[i])
            right = typing.cast(ExpressionStatement, args[i + 1])
            i += 2
            op_cls = Operator.get_operator_class(op_str)
            if op_cls is None:
                raise ParserException(_make_location(pos), op_str, f"Invalid operator {op_str}")
            node = typing.cast(_BinaryOpFactory, op_cls)(left, right)
            node.location = _make_location(pos)
            node.namespace = _state.namespace
            node.lexpos = pos
            left = node
        return left

    def act_mul(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        i = 1
        while i < len(args):
            op_str = str(args[i])
            right = typing.cast(ExpressionStatement, args[i + 1])
            i += 2
            op_cls = Operator.get_operator_class(op_str)
            if op_cls is None:
                raise ParserException(_make_location(pos), op_str, f"Invalid operator {op_str}")
            node = typing.cast(_BinaryOpFactory, op_cls)(left, right)
            node.location = _make_location(pos)
            node.namespace = _state.namespace
            node.lexpos = pos
            left = node
        return left

    def act_pow(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        # Seq(postfix_expr, DOUBLE_STAR, pow_expr)
        assert _state.namespace is not None
        left = typing.cast(ExpressionStatement, args[0])
        right = typing.cast(ExpressionStatement, args[1])
        op_cls = Operator.get_operator_class("**")
        if op_cls is None:
            raise ParserException(_make_location(pos), "**", "Invalid operator **")
        node = typing.cast(_BinaryOpFactory, op_cls)(left, right)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_postfix_subscript(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        """postfix_expr '[' subscript_content ']': primary + one subscript."""
        # args: [base, subscript_result]
        assert _state.namespace is not None
        base = typing.cast(ExpressionStatement, args[0])
        subscript = args[1]
        node = _apply_subscript(base, subscript, pos)
        return node

    def _apply_subscript(base: ExpressionStatement, subscript: object, pos: int) -> ExpressionStatement:
        assert _state.namespace is not None
        if isinstance(subscript, tuple):
            # param_list -> IndexLookup / ShortIndexLookup
            kwargs_list_raw, wrapped_raw = typing.cast(tuple[list[object], list[object]], subscript)
            kwargs_list = typing.cast(list[tuple[LocatableString, ExpressionStatement]], kwargs_list_raw)
            wrapped = typing.cast(list[WrappedKwargs], wrapped_raw)
            if isinstance(base, AttributeReference):
                node: ExpressionStatement = ShortIndexLookup(base.instance, base.attribute, kwargs_list, wrapped)
            else:
                node = IndexLookup(typing.cast(LocatableString, base), kwargs_list, wrapped)
        else:
            # expression -> MapLookup
            node = MapLookup(base, typing.cast(ExpressionStatement, subscript))
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    # primary sub-actions

    def act_primary_constructor(s: str, pos: int, end: int, args: list[object]) -> Constructor:
        assert _state.namespace is not None
        class_r = typing.cast(LocatableString, args[0])
        param = typing.cast(tuple[list[object], list[object]], args[1])
        kwargs_list_raw, wrapped_raw = param
        kwargs_list = typing.cast(list[tuple[LocatableString, ExpressionStatement]], kwargs_list_raw)
        wrapped = typing.cast(list[WrappedKwargs], wrapped_raw)
        node = Constructor(class_r, kwargs_list, wrapped, _make_location(pos), _state.namespace)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_primary_index_lookup(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        class_r = typing.cast(LocatableString, args[0])
        param = typing.cast(tuple[list[object], list[object]], args[1])
        kwargs_list_raw, wrapped_raw = param
        kwargs_list = typing.cast(list[tuple[LocatableString, ExpressionStatement]], kwargs_list_raw)
        wrapped = typing.cast(list[WrappedKwargs], wrapped_raw)
        node: ExpressionStatement = IndexLookup(class_r, kwargs_list, wrapped)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_primary_func_err(s: str, pos: int, end: int, args: list[object]) -> object:
        attr_r = typing.cast(AttributeReference, args[0])
        raise InvalidNamespaceAccess(attr_r.locatable_name)

    def act_primary_func_call(s: str, pos: int, end: int, args: list[object]) -> FunctionCall:
        assert _state.namespace is not None
        ns_r = typing.cast(LocatableString, args[0])
        fparams = typing.cast(tuple[list[object], list[object], list[object]], args[1])
        pos_args_raw, kwargs_list_raw, wrapped_raw = fparams
        pos_args = typing.cast(list[ExpressionStatement], pos_args_raw)
        kwargs_list = typing.cast(list[tuple[LocatableString, ExpressionStatement]], kwargs_list_raw)
        wrapped = typing.cast(list[WrappedKwargs], wrapped_raw)
        node = FunctionCall(ns_r, pos_args, kwargs_list, wrapped, _state.namespace)
        # FunctionCall.__init__ already sets location = name.get_location() (a Range)
        # Do NOT override with _make_location(pos) (a Location) — that would lose column info.
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_primary_list_comp(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        lc_ns: Namespace = _state.namespace
        value_expr = typing.cast(ExpressionStatement, args[0])
        specifiers = typing.cast(list[ForSpecifier], args[1])
        guard = typing.cast(Optional[ExpressionStatement], args[2])

        if specifiers:
            specifiers[0].guard = guard

        def create_lc(ve: ExpressionStatement, spec: ForSpecifier) -> ListComprehension:
            result = ListComprehension(ve, spec.variable, spec.iterable, spec.guard)
            result.location = _make_location(pos)
            result.namespace = lc_ns
            result.lexpos = pos
            return result

        final: ExpressionStatement = functools.reduce(
            lambda acc, spec: create_lc(acc, spec),
            specifiers,
            value_expr,
        )
        return final

    def act_primary_list_def(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        items = typing.cast(list[ExpressionStatement], args[0])
        node: ExpressionStatement = CreateList(items)
        try:
            node = Literal(typing.cast(CreateList, node).as_constant())
        except RuntimeException:
            pass
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_primary_map_def(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        assert _state.namespace is not None
        pairs = typing.cast(list[tuple[str, ExpressionStatement]], args[0])
        node: ExpressionStatement = CreateDict(typing.cast(list[tuple[str, ReferenceStatement]], pairs))
        try:
            node = Literal({k: v.as_constant() for k, v in pairs})
        except RuntimeException:
            pass
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_primary_paren(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        return typing.cast(ExpressionStatement, args[0])

    def act_primary_varref(s: str, pos: int, end: int, args: list[object]) -> ExpressionStatement:
        return typing.cast(ExpressionStatement, args[0])

    # ------------------------------------------------------------------
    # Operand / param list actions
    # ------------------------------------------------------------------

    def act_operand_list(s: str, pos: int, end: int, args: list[object]) -> list[ExpressionStatement]:
        return [typing.cast(ExpressionStatement, a) for a in args]

    def act_param_list_kwarg(s: str, pos: int, end: int, args: list[object]) -> tuple[object, object]:
        # ID '=' expression  -> ((ID, expr), None)
        k = args[0]
        v = args[1]
        return ((k, v), None)

    def act_param_list_wrapped(s: str, pos: int, end: int, args: list[object]) -> tuple[object, object]:
        # '**' expression -> (None, WrappedKwargs)
        assert _state.namespace is not None
        expr = typing.cast(ExpressionStatement, args[0])
        wk = WrappedKwargs(expr)
        wk.location = _make_location(pos)
        wk.namespace = _state.namespace
        wk.lexpos = pos
        return (None, wk)

    def act_param_list(s: str, pos: int, end: int, args: list[object]) -> tuple[list[object], list[object]]:
        # args: sequence of (pair_or_None, wrapped_or_None) tuples
        kwargs_list: list[object] = []
        wrapped_list: list[object] = []
        for elem in args:
            pair, wkw = typing.cast(tuple[object, object], elem)
            if pair is not None:
                kwargs_list.append(pair)
            if wkw is not None:
                wrapped_list.append(wkw)
        return (kwargs_list, wrapped_list)

    def act_function_param_positional(s: str, pos: int, end: int, args: list[object]) -> tuple[object, object, object]:
        # positional arg -> (expr, None, None)
        return (args[0], None, None)

    def act_function_param_kwarg(s: str, pos: int, end: int, args: list[object]) -> tuple[object, object, object]:
        # ID '=' expression -> (None, (ID, expr), None)
        k = args[0]
        v = args[1]
        return (None, (k, v), None)

    def act_function_param_wrapped(s: str, pos: int, end: int, args: list[object]) -> tuple[object, object, object]:
        assert _state.namespace is not None
        expr = typing.cast(ExpressionStatement, args[0])
        wk = WrappedKwargs(expr)
        wk.location = _make_location(pos)
        wk.namespace = _state.namespace
        wk.lexpos = pos
        return (None, None, wk)

    def act_function_param_list(
        s: str, pos: int, end: int, args: list[object]
    ) -> tuple[list[ExpressionStatement], list[tuple[LocatableString, ExpressionStatement]], list[WrappedKwargs]]:
        pos_args: list[ExpressionStatement] = []
        kwargs_list: list[tuple[LocatableString, ExpressionStatement]] = []
        wrapped_list: list[WrappedKwargs] = []
        for elem in args:
            a, k, w = typing.cast(tuple[object, object, object], elem)
            if a is not None:
                pos_args.append(typing.cast(ExpressionStatement, a))
            if k is not None:
                kwargs_list.append(typing.cast(tuple[LocatableString, ExpressionStatement], k))
            if w is not None:
                wrapped_list.append(typing.cast(WrappedKwargs, w))
        return (pos_args, kwargs_list, wrapped_list)

    # ------------------------------------------------------------------
    # Pair list / dict key actions
    # ------------------------------------------------------------------

    def act_dict_key_string(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        ls = typing.cast(LocatableString, args[0])
        key_str = str(ls)
        if format_regex_compiled.search(key_str):
            raise ParserException(
                ls.location,
                key_str,
                "String interpolation is not supported in dictionary keys. "
                "Use raw string to use a key containing double curly brackets",
            )
        return ls

    def act_dict_key_rstring(s: str, pos: int, end: int, args: list[object]) -> LocatableString:
        return typing.cast(LocatableString, args[0])

    def act_pair_entry(s: str, pos: int, end: int, args: list[object]) -> tuple[str, ExpressionStatement]:
        key = typing.cast(LocatableString, args[0])
        val = typing.cast(ExpressionStatement, args[1])
        return (str(key), val)

    def act_pair_list(s: str, pos: int, end: int, args: list[object]) -> list[tuple[str, ExpressionStatement]]:
        return [typing.cast(tuple[str, ExpressionStatement], a) for a in args]

    # ------------------------------------------------------------------
    # id_list / class_ref_list
    # ------------------------------------------------------------------

    def act_id_list(s: str, pos: int, end: int, args: list[object]) -> list[LocatableString]:
        return [typing.cast(LocatableString, a) for a in args]

    def act_class_ref_list(s: str, pos: int, end: int, args: list[object]) -> list[LocatableString]:
        result: list[LocatableString] = []
        for a in args:
            if isinstance(a, (Reference, AttributeReference)):
                raise ParserException(
                    a.locatable_name.location,
                    str(a.locatable_name),
                    "Invalid identifier: Entity names must start with a capital",
                )
            result.append(typing.cast(LocatableString, a))
        return result

    # ------------------------------------------------------------------
    # Statement actions
    # ------------------------------------------------------------------

    def act_assign_normal(s: str, pos: int, end: int, args: list[object]) -> Statement:
        assert _state.namespace is not None
        vr = typing.cast(Union[Reference, AttributeReference], args[0])
        expr = typing.cast(ExpressionStatement, args[1])
        node = vr.as_assign(expr)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_assign_extend(s: str, pos: int, end: int, args: list[object]) -> Statement:
        assert _state.namespace is not None
        vr = typing.cast(Union[Reference, AttributeReference], args[0])
        expr = typing.cast(ExpressionStatement, args[1])
        node = vr.as_assign(expr, list_only=True)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_for_stmt(s: str, pos: int, end: int, args: list[object]) -> For:
        assert _state.namespace is not None
        var_id = typing.cast(LocatableString, args[0])
        iterable = typing.cast(ExpressionStatement, args[1])
        stmts = typing.cast(list[DynamicStatement], args[2])
        node = For(iterable, var_id, BasicBlock(_state.namespace, stmts))
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_if_stmt(s: str, pos: int, end: int, args: list[object]) -> If:
        assert _state.namespace is not None
        cond = typing.cast(ExpressionStatement, args[0])
        true_stmts = typing.cast(list[DynamicStatement], args[1])
        else_block = typing.cast(BasicBlock, args[2])
        node = If(cond, BasicBlock(_state.namespace, true_stmts), else_block)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_if_next_elif(s: str, pos: int, end: int, args: list[object]) -> BasicBlock:
        assert _state.namespace is not None
        cond = typing.cast(ExpressionStatement, args[0])
        stmts = typing.cast(list[DynamicStatement], args[1])
        next_block = typing.cast(BasicBlock, args[2])
        inner = If(cond, BasicBlock(_state.namespace, stmts), next_block)
        inner.location = _make_location(pos)
        inner.namespace = _state.namespace
        inner.lexpos = pos
        return BasicBlock(_state.namespace, [inner])

    def act_if_next_else(s: str, pos: int, end: int, args: list[object]) -> BasicBlock:
        assert _state.namespace is not None
        stmts = typing.cast(list[DynamicStatement], args[0])
        return BasicBlock(_state.namespace, stmts)

    def act_if_next_empty(s: str, pos: int, end: int, args: list[object]) -> BasicBlock:
        assert _state.namespace is not None
        return BasicBlock(_state.namespace, [])

    def act_stmt_list(s: str, pos: int, end: int, args: list[object]) -> list[Statement]:
        # PLY's stmt_list is right-recursive and appends each statement to the END of the sub-list,
        # resulting in reversed source order. BasicBlock depends on this ordering.
        return list(reversed(typing.cast(list[Statement], args)))

    # ------------------------------------------------------------------
    # List comprehension
    # ------------------------------------------------------------------

    def act_lc_for(s: str, pos: int, end: int, args: list[object]) -> list[ForSpecifier]:
        # args: ID, iterable, optional(sub_fors)
        var_id = typing.cast(LocatableString, args[0])
        iterable = typing.cast(ExpressionStatement, args[1])
        sub: list[ForSpecifier] = list(typing.cast(list[ForSpecifier], args[2])) if len(args) > 2 else []
        sub.append(ForSpecifier(variable=var_id, iterable=iterable))
        return sub

    def act_lc_for_with_sub(s: str, pos: int, end: int, args: list[object]) -> list[ForSpecifier]:
        var_id = typing.cast(LocatableString, args[0])
        iterable = typing.cast(ExpressionStatement, args[1])
        sub = list(typing.cast(list[ForSpecifier], args[2]))
        sub.append(ForSpecifier(variable=var_id, iterable=iterable))
        return sub

    def act_lc_guard(s: str, pos: int, end: int, args: list[object]) -> Optional[ExpressionStatement]:
        # args: condition, optional(rest)
        cond = typing.cast(ExpressionStatement, args[0])
        rest = typing.cast(Optional[ExpressionStatement], args[1]) if len(args) > 1 else None
        if rest is None:
            return cond
        node: AstAnd = AstAnd(cond, rest)
        node.location = cond.location
        node.namespace = cond.namespace
        node.lexpos = cond.lexpos
        return node

    # ------------------------------------------------------------------
    # Multiplicity
    # ------------------------------------------------------------------

    def act_multi_exact(s: str, pos: int, end: int, args: list[object]) -> tuple[int, Optional[int]]:
        n = int(str(args[0]))
        return (n, n)

    def act_multi_lower(s: str, pos: int, end: int, args: list[object]) -> tuple[int, Optional[int]]:
        n = int(str(args[0]))
        return (n, None)

    def act_multi_range(s: str, pos: int, end: int, args: list[object]) -> tuple[int, Optional[int]]:
        lo = int(str(args[0]))
        hi = int(str(args[1]))
        return (lo, hi)

    def act_multi_upper(s: str, pos: int, end: int, args: list[object]) -> tuple[int, Optional[int]]:
        hi = int(str(args[0]))
        return (0, hi)

    # ------------------------------------------------------------------
    # Definition actions
    # ------------------------------------------------------------------

    def act_attr_base_type(s: str, pos: int, end: int, args: list[object]) -> TypeDeclaration:
        ns_r = typing.cast(LocatableString, args[0])
        node = TypeDeclaration(ns_r)
        node.location = ns_r.location
        node.namespace = ns_r.namespace
        return node

    def act_attr_type_multi(s: str, pos: int, end: int, args: list[object]) -> TypeDeclaration:
        td = typing.cast(TypeDeclaration, args[0])
        td.multi = True
        return td

    def act_attr_type_opt(s: str, pos: int, end: int, args: list[object]) -> TypeDeclaration:
        td = typing.cast(TypeDeclaration, args[0])
        td.nullable = True
        return td

    def act_attr_normal(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        assert _state.namespace is not None
        td = typing.cast(TypeDeclaration, args[0])
        name = typing.cast(LocatableString, args[1])
        default = typing.cast(Optional[ExpressionStatement], args[2]) if len(args) > 2 else None
        node = DefineAttribute(td, name, default)
        node.location = name.location
        node.namespace = name.namespace
        node.lexpos = name.lexpos
        return node

    def act_attr_undef(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        assert _state.namespace is not None
        td = typing.cast(TypeDeclaration, args[0])
        name = typing.cast(LocatableString, args[1])
        node = DefineAttribute(td, name, None, remove_default=True)
        node.location = name.location
        node.namespace = name.namespace
        node.lexpos = name.lexpos
        return node

    def act_attr_cid_err(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        cid = typing.cast(LocatableString, args[0])
        raise ParserException(
            cid.location, str(cid), "Invalid identifier: attribute names must start with a lower case character"
        )

    def act_attr_dict(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        # args: dict_ls (from DICT_KW), name, optional_default
        assert _state.namespace is not None
        dict_ls = typing.cast(LocatableString, args[0])
        name = typing.cast(LocatableString, args[1])
        default = typing.cast(Optional[ExpressionStatement], args[2]) if len(args) > 2 else None
        td = TypeDeclaration(dict_ls)
        node = DefineAttribute(td, name, default)
        node.location = name.location
        node.namespace = name.namespace
        node.lexpos = name.lexpos
        return node

    def act_attr_dict_nullable(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        # args: dict_ls (from DICT_KW), name, optional_default
        assert _state.namespace is not None
        dict_ls = typing.cast(LocatableString, args[0])
        name = typing.cast(LocatableString, args[1])
        default = typing.cast(Optional[ExpressionStatement], args[2]) if len(args) > 2 else None
        td = TypeDeclaration(dict_ls, nullable=True)
        node = DefineAttribute(td, name, default)
        node.location = name.location
        node.namespace = name.namespace
        node.lexpos = name.lexpos
        return node

    def act_attr_dict_null_err(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        # args: dict_ls, name
        name = typing.cast(LocatableString, args[1])
        raise ParserException(
            name.location, str(name), 'null can not be assigned to dict, did you mean "dict? %s = null"' % name
        )

    def act_attr_dict_cid_err(s: str, pos: int, end: int, args: list[object]) -> DefineAttribute:
        cid = typing.cast(LocatableString, args[-1])
        raise ParserException(
            cid.location, str(cid), "Invalid identifier: attribute names must start with a lower case character"
        )

    def act_entity_def(s: str, pos: int, end: int, args: list[object]) -> DefineEntity:
        assert _state.namespace is not None
        name = typing.cast(LocatableString, args[0])
        parents: list[LocatableString] = []
        if len(args) == 3:
            parents = typing.cast(list[LocatableString], args[1])
            body = typing.cast(tuple[object, list[object]], args[2])
        else:
            body = typing.cast(tuple[object, list[object]], args[1])
        docstr_raw, attrs_raw = body
        docstr = typing.cast(Optional[LocatableString], docstr_raw)
        attrs = typing.cast(list[DefineAttribute], attrs_raw)
        node = DefineEntity(_state.namespace, name, docstr, parents, attrs)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_entity_err(s: str, pos: int, end: int, args: list[object]) -> DefineEntity:
        name = typing.cast(LocatableString, args[0])
        raise ParserException(name.location, str(name), "Invalid identifier: Entity names must start with a capital")

    def act_entity_body_outer_with_doc(s: str, pos: int, end: int, args: list[object]) -> tuple[object, list[object]]:
        doc = args[0]
        # args[1] is the entity_body result (a list of DefineAttribute)
        attrs = typing.cast(list[object], args[1])
        return (doc, attrs)

    def act_entity_body_outer_no_doc(s: str, pos: int, end: int, args: list[object]) -> tuple[object, list[object]]:
        # args[0] is the entity_body result (a list of DefineAttribute)
        attrs = typing.cast(list[object], args[0])
        return (None, attrs)

    def act_constant_list(s: str, pos: int, end: int, args: list[object]) -> CreateList:
        assert _state.namespace is not None
        node = CreateList(typing.cast(list[ExpressionStatement], list(args)))
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    # implement_ns_list
    def act_impl_ns_ref(s: str, pos: int, end: int, args: list[object]) -> tuple[bool, list[LocatableString]]:
        ns_r = typing.cast(LocatableString, args[0])
        return (False, [ns_r])

    def act_impl_parents(s: str, pos: int, end: int, args: list[object]) -> tuple[bool, list[LocatableString]]:
        return (True, [])

    def act_impl_ns_list(s: str, pos: int, end: int, args: list[object]) -> tuple[bool, list[LocatableString]]:
        # args: sequence of (bool, list) tuples
        result_inherit = False
        result_impls: list[LocatableString] = []
        for elem in args:
            inh, impls = typing.cast(tuple[bool, list[LocatableString]], elem)
            result_inherit = result_inherit or inh
            result_impls.extend(impls)
        return (result_inherit, result_impls)

    def act_implement_def_no_when(s: str, pos: int, end: int, args: list[object]) -> DefineImplement:
        assert _state.namespace is not None
        class_r = typing.cast(LocatableString, args[0])
        impl_list_raw = typing.cast(tuple[bool, list[LocatableString]], args[1])
        inherit, implementations = impl_list_raw
        comment = typing.cast(Optional[LocatableString], args[2]) if len(args) > 2 else None
        when: Literal = Literal(True)
        when.location = _make_location(pos)
        when.namespace = _state.namespace
        when.lexpos = pos
        node = DefineImplement(class_r, implementations, when, inherit=inherit, comment=comment)
        node.copy_location(when)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_implement_def_when(s: str, pos: int, end: int, args: list[object]) -> DefineImplement:
        assert _state.namespace is not None
        class_r = typing.cast(LocatableString, args[0])
        impl_list_raw = typing.cast(tuple[bool, list[LocatableString]], args[1])
        inherit, implementations = impl_list_raw
        when_expr = typing.cast(ExpressionStatement, args[2])
        comment = typing.cast(Optional[LocatableString], args[3]) if len(args) > 3 else None
        node = DefineImplement(class_r, implementations, when_expr, inherit=inherit, comment=comment)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_implementation_def(s: str, pos: int, end: int, args: list[object]) -> DefineImplementation:
        assert _state.namespace is not None
        name = typing.cast(LocatableString, args[0])
        class_r = typing.cast(LocatableString, args[1])
        # args[2] is optional MLS docstring (may be absent)
        if len(args) == 4:
            docstr = typing.cast(LocatableString, args[2])
            stmts = typing.cast(list[DynamicStatement], args[3])
        else:
            docstr = typing.cast(LocatableString, None)
            stmts = typing.cast(list[DynamicStatement], args[2])
        node = DefineImplementation(_state.namespace, name, class_r, BasicBlock(_state.namespace, stmts), docstr)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_typedef_no_comment(s: str, pos: int, end: int, args: list[object]) -> DefineTypeConstraint:
        assert _state.namespace is not None
        name = typing.cast(LocatableString, args[0])
        parent = typing.cast(LocatableString, args[1])
        constraint = typing.cast(ExpressionStatement, args[2])
        node = DefineTypeConstraint(_state.namespace, name, parent, constraint)
        node.location = name.location
        node.namespace = _state.namespace
        node.lexpos = name.lexpos
        return node

    def act_typedef_with_comment(s: str, pos: int, end: int, args: list[object]) -> DefineTypeConstraint:
        # args[0] is the DefineTypeConstraint node from typedef_inner, args[1] is the MLS comment
        node = typing.cast(DefineTypeConstraint, args[0])
        comment = typing.cast(LocatableString, args[1])
        node.comment = str(comment)
        return node

    def act_typedef_cls(s: str, pos: int, end: int, args: list[object]) -> None:
        # typedef CID AS constructor — this syntax is no longer supported
        cid = typing.cast(LocatableString, args[0])
        raise ParserException(cid.location, str(cid), "The use of default constructors is no longer supported")

    def act_index(s: str, pos: int, end: int, args: list[object]) -> DefineIndex:
        assert _state.namespace is not None
        class_r = typing.cast(LocatableString, args[0])
        id_list = typing.cast(list[LocatableString], args[1])
        node = DefineIndex(class_r, id_list)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_import(s: str, pos: int, end: int, args: list[object]) -> DefineImport:
        assert _state.namespace is not None
        ns_r = typing.cast(LocatableString, args[0])
        node = DefineImport(ns_r, ns_r)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_import_as(s: str, pos: int, end: int, args: list[object]) -> DefineImport:
        assert _state.namespace is not None
        ns_r = typing.cast(LocatableString, args[0])
        alias = typing.cast(LocatableString, args[1])
        node = DefineImport(ns_r, alias)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_relation_bidir(s: str, pos: int, end: int, args: list[object]) -> DefineRelation:
        assert _state.namespace is not None
        class1 = typing.cast(LocatableString, args[0])
        id1 = typing.cast(LocatableString, args[1])
        multi1 = typing.cast(tuple[int, Optional[int]], args[2])
        class2 = typing.cast(LocatableString, args[3])
        id2 = typing.cast(LocatableString, args[4])
        multi2 = typing.cast(tuple[int, Optional[int]], args[5])
        node = DefineRelation((class1, id2, multi2), (class2, id1, multi1))
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_relation_bidir_ann(s: str, pos: int, end: int, args: list[object]) -> DefineRelation:
        assert _state.namespace is not None
        class1 = typing.cast(LocatableString, args[0])
        id1 = typing.cast(LocatableString, args[1])
        multi1 = typing.cast(tuple[int, Optional[int]], args[2])
        annotations = typing.cast(list[ExpressionStatement], args[3])
        class2 = typing.cast(LocatableString, args[4])
        id2 = typing.cast(LocatableString, args[5])
        multi2 = typing.cast(tuple[int, Optional[int]], args[6])
        node = DefineRelation((class1, id2, multi2), (class2, id1, multi1), annotations)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_relation_unidir(s: str, pos: int, end: int, args: list[object]) -> DefineRelation:
        assert _state.namespace is not None
        class1 = typing.cast(LocatableString, args[0])
        id1 = typing.cast(LocatableString, args[1])
        multi1 = typing.cast(tuple[int, Optional[int]], args[2])
        class2 = typing.cast(LocatableString, args[3])
        node = DefineRelation((class1, None, None), (class2, id1, multi1))
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_relation_unidir_ann(s: str, pos: int, end: int, args: list[object]) -> DefineRelation:
        assert _state.namespace is not None
        class1 = typing.cast(LocatableString, args[0])
        id1 = typing.cast(LocatableString, args[1])
        multi1 = typing.cast(tuple[int, Optional[int]], args[2])
        annotations = typing.cast(list[ExpressionStatement], args[3])
        class2 = typing.cast(LocatableString, args[4])
        node = DefineRelation((class1, None, None), (class2, id1, multi1), annotations)
        node.location = _make_location(pos)
        node.namespace = _state.namespace
        node.lexpos = pos
        return node

    def act_relation_with_comment(s: str, pos: int, end: int, args: list[object]) -> DefineRelation:
        rel = typing.cast(DefineRelation, args[0])
        comment = typing.cast(LocatableString, args[1])
        rel.comment = str(comment)  # type: ignore[assignment]
        return rel

    def act_start(s: str, pos: int, end: int, args: list[object]) -> list[Statement]:
        result: list[Statement] = []
        for a in args:
            if isinstance(a, list):
                result.extend(typing.cast(list[Statement], a))
            elif a is not None:
                result.append(typing.cast(Statement, a))
        return result

    # ------------------------------------------------------------------
    # Grammar rules dictionary
    # ------------------------------------------------------------------
    rules: dict[str, object] = {}

    # --- Token rules ---
    rules["MLS"] = MLS_PAT
    rules["FSTRING"] = FSTRING_PAT
    rules["RSTRING"] = RSTRING_PAT
    rules["STRING"] = STRING_PAT
    rules["REGEX_TOKEN"] = REGEX_TOKEN_PAT
    rules["FLOAT"] = FLOAT_PAT
    rules["INT"] = INT_PAT
    rules["ID"] = ID_PAT
    rules["CID"] = CID_PAT
    rules["SEP"] = SEP
    rules["REL"] = REL_PAT
    rules["CMP_OP"] = CMP_OP_PAT
    # Illegal string error rules (unclosed single-line strings containing newlines)
    rules["illegal_string_dbl"] = ILLEGAL_STRING_DBL_PAT
    rules["illegal_string_sgl"] = ILLEGAL_STRING_SGL_PAT
    rules["illegal_fstring_dbl"] = ILLEGAL_FSTRING_DBL_PAT
    rules["illegal_fstring_sgl"] = ILLEGAL_FSTRING_SGL_PAT
    rules["illegal_rstring_dbl"] = ILLEGAL_RSTRING_DBL_PAT
    rules["illegal_rstring_sgl"] = ILLEGAL_RSTRING_SGL_PAT

    # --- Reference rules ---
    rules["ns_ref"] = AutoIgnore(Seq(NT("ID"), Star(Seq(SEP, NT("ID")))))

    # class_ref alternatives as separate named rules
    rules["class_ref_qualified"] = AutoIgnore(Seq(NT("ns_ref"), SEP, NT("CID")))
    rules["class_ref_simple"] = AutoIgnore(NT("CID"))
    rules["class_ref_dot_err"] = AutoIgnore(Seq(NT("var_ref"), DOT_OP, NT("CID")))
    rules["class_ref"] = AutoIgnore(Ch(NT("class_ref_qualified"), NT("class_ref_simple"), NT("class_ref_dot_err")))
    # class_ref_id_err matches a lowercase ID in a class_ref_list context to raise a nice error
    rules["class_ref_id_err"] = AutoIgnore(NT("ID"))
    rules["class_ref_or_err"] = AutoIgnore(Ch(NT("class_ref"), NT("class_ref_id_err")))

    rules["var_ref"] = AutoIgnore(Seq(NT("ns_ref"), Star(Seq(DOT_OP, NT("ID")))))
    rules["attr_ref"] = AutoIgnore(Seq(NT("ns_ref"), Plus(Seq(DOT_OP, NT("ID")))))

    # --- Constant rules (one named rule per alternative) ---
    rules["constant_INT"] = AutoIgnore(NT("INT"))
    rules["constant_FLOAT"] = AutoIgnore(NT("FLOAT"))
    rules["constant_NULL"] = AutoIgnore(KW_NULL)
    rules["constant_TRUE"] = AutoIgnore(KW_TRUE)
    rules["constant_FALSE"] = AutoIgnore(KW_FALSE)
    rules["constant_STRING"] = AutoIgnore(NT("STRING"))
    rules["constant_MLS"] = AutoIgnore(NT("MLS"))
    rules["constant_FSTRING"] = AutoIgnore(NT("FSTRING"))
    rules["constant_RSTRING"] = AutoIgnore(NT("RSTRING"))
    rules["constant_REGEX"] = AutoIgnore(NT("REGEX_TOKEN"))
    rules["constant"] = AutoIgnore(
        Ch(
            NT("constant_REGEX"),
            NT("constant_FLOAT"),
            NT("constant_INT"),
            NT("constant_NULL"),
            NT("constant_TRUE"),
            NT("constant_FALSE"),
            NT("constant_MLS"),
            NT("constant_FSTRING"),
            NT("constant_RSTRING"),
            NT("constant_STRING"),
            # Error cases: unclosed single-line strings (must come after valid patterns)
            NT("illegal_fstring_dbl"),
            NT("illegal_fstring_sgl"),
            NT("illegal_rstring_dbl"),
            NT("illegal_rstring_sgl"),
            NT("illegal_string_dbl"),
            NT("illegal_string_sgl"),
        )
    )

    # constant_list
    rules["constant_list"] = AutoIgnore(Seq(LBRACK, Opt(Seq(NT("constant"), Star(Seq(COMMA, NT("constant"))))), RBRACK))

    # --- Operand list ---
    # Support trailing comma (e.g. [1, 2, 3,])
    rules["operand_list"] = AutoIgnore(Opt(Seq(NT("expression"), Star(Seq(COMMA, NT("expression"))), Opt(COMMA))))

    # --- Dict key / pair list ---
    rules["dict_key_string"] = AutoIgnore(NT("STRING"))
    rules["dict_key_rstring"] = AutoIgnore(NT("RSTRING"))
    rules["dict_key"] = AutoIgnore(Ch(NT("dict_key_rstring"), NT("dict_key_string")))
    rules["pair_entry"] = AutoIgnore(Seq(NT("dict_key"), COLON, NT("expression")))
    rules["pair_list"] = AutoIgnore(Opt(Seq(NT("pair_entry"), Star(Seq(COMMA, NT("pair_entry"))), Opt(COMMA))))

    # --- Param list ---
    rules["param_list_kwarg"] = AutoIgnore(Seq(NT("ID"), EQUALS, NT("expression")))
    rules["param_list_wrapped"] = AutoIgnore(Seq(DOUBLE_STAR, NT("expression")))
    rules["param_list_element"] = AutoIgnore(Ch(NT("param_list_kwarg"), NT("param_list_wrapped")))
    rules["param_list"] = AutoIgnore(Opt(Seq(NT("param_list_element"), Star(Seq(COMMA, NT("param_list_element"))), Opt(COMMA))))

    # --- Function param list ---
    rules["function_param_positional"] = AutoIgnore(NT("expression"))
    rules["function_param_kwarg"] = AutoIgnore(Seq(NT("ID"), EQUALS, NT("expression")))
    rules["function_param_wrapped"] = AutoIgnore(Seq(DOUBLE_STAR, NT("expression")))
    rules["function_param_element"] = AutoIgnore(
        Ch(NT("function_param_kwarg"), NT("function_param_wrapped"), NT("function_param_positional"))
    )
    rules["function_param_list"] = AutoIgnore(
        Opt(Seq(NT("function_param_element"), Star(Seq(COMMA, NT("function_param_element"))), Opt(COMMA)))
    )

    # --- List comprehension ---
    rules["list_comprehension_for_inner"] = AutoIgnore(
        Seq(KW_FOR, NT("ID"), KW_IN, NT("expression"), NT("list_comprehension_for"))
    )
    rules["list_comprehension_for_last"] = AutoIgnore(Seq(KW_FOR, NT("ID"), KW_IN, NT("expression")))
    rules["list_comprehension_for"] = AutoIgnore(Ch(NT("list_comprehension_for_inner"), NT("list_comprehension_for_last")))

    rules["list_comprehension_guard_with"] = AutoIgnore(Seq(KW_IF, NT("expression"), NT("list_comprehension_guard")))
    rules["list_comprehension_guard_last"] = AutoIgnore(Seq(KW_IF, NT("expression")))
    rules["list_comprehension_guard"] = AutoIgnore(Ch(NT("list_comprehension_guard_with"), NT("list_comprehension_guard_last")))
    rules["list_comprehension_guard_opt"] = AutoIgnore(Opt(NT("list_comprehension_guard")))

    # --- Primary expressions (separate named rules per alternative) ---
    rules["primary_constructor"] = AutoIgnore(Seq(NT("class_ref"), LPAREN, NT("param_list"), RPAREN))
    rules["primary_index_lookup"] = AutoIgnore(Seq(NT("class_ref"), LBRACK, NT("param_list"), RBRACK))
    rules["primary_func_err"] = AutoIgnore(Seq(NT("attr_ref"), LPAREN, NT("function_param_list"), RPAREN))
    rules["primary_func_call"] = AutoIgnore(Seq(NT("ns_ref"), LPAREN, NT("function_param_list"), RPAREN))
    rules["primary_list_comp"] = AutoIgnore(
        Seq(LBRACK, NT("expression"), NT("list_comprehension_for"), NT("list_comprehension_guard_opt"), RBRACK)
    )
    rules["primary_list_def"] = AutoIgnore(Seq(LBRACK, NT("operand_list"), RBRACK))
    rules["primary_map_def"] = AutoIgnore(Seq(LBRACE, NT("pair_list"), RBRACE))
    rules["primary_constant"] = AutoIgnore(NT("constant"))
    rules["primary_paren"] = AutoIgnore(Seq(LPAREN, NT("expression"), RPAREN))
    rules["primary_varref"] = AutoIgnore(NT("var_ref"))
    rules["primary"] = AutoIgnore(
        Ch(
            NT("primary_constructor"),
            NT("primary_index_lookup"),
            NT("primary_func_err"),
            NT("primary_func_call"),
            NT("primary_list_comp"),
            NT("primary_list_def"),
            NT("primary_map_def"),
            NT("primary_constant"),
            NT("primary_paren"),
            NT("primary_varref"),
        )
    )

    # Subscript steps — two separate named rules to keep them distinct.
    # Map lookup:   a["key"]   a[expr]    → expression subscript
    # Index lookup: A[k=v]     A[k=v, m=n] → param_list_nonempty subscript
    # Must use separate rules because param_list uses Opt() which always succeeds.
    rules["param_list_nonempty"] = AutoIgnore(
        Seq(NT("param_list_element"), Star(Seq(COMMA, NT("param_list_element"))), Opt(COMMA))
    )
    rules["subscript_map"] = AutoIgnore(Seq(LBRACK, NT("expression"), RBRACK))
    rules["subscript_index"] = AutoIgnore(Seq(LBRACK, NT("param_list_nonempty"), RBRACK))
    # Try subscript_index first: if the content is ID=expr, it's an index; otherwise map lookup.
    # subscript_index only matches when there's at least one param_list_element (non-empty),
    # so it won't match map-style subscripts.
    rules["postfix_subscript_step"] = AutoIgnore(Ch(NT("subscript_index"), NT("subscript_map")))
    # Full postfix: primary followed by zero or more subscript steps
    # args: [primary, subscript1, subscript2, ...]
    rules["postfix_expr"] = AutoIgnore(Seq(NT("primary"), Star(NT("postfix_subscript_step"))))

    # pow_expr: separate rules
    rules["pow_expr_with_pow"] = AutoIgnore(Seq(NT("postfix_expr"), DOUBLE_STAR, NT("pow_expr")))
    rules["pow_expr"] = AutoIgnore(Ch(NT("pow_expr_with_pow"), NT("postfix_expr")))

    # mul_expr
    rules["mul_expr"] = AutoIgnore(
        Seq(
            NT("pow_expr"),
            Star(Ch(Seq(STAR_OP, NT("pow_expr")), Seq(SLASH_OP, NT("pow_expr")), Seq(PERCENT_OP, NT("pow_expr")))),
        )
    )

    # additive_expr
    rules["additive_expr"] = AutoIgnore(
        Seq(NT("mul_expr"), Star(Ch(Seq(PLUS_OP, NT("mul_expr")), Seq(MINUS_OP, NT("mul_expr")))))
    )

    # cmp_expr alternatives as separate named rules
    rules["cmp_is_defined"] = AutoIgnore(Seq(NT("postfix_expr"), KW_IS, KW_DEFINED))
    rules["cmp_op_expr"] = AutoIgnore(Seq(NT("additive_expr"), NT("CMP_OP"), NT("additive_expr")))
    rules["cmp_not_in_expr"] = AutoIgnore(Seq(NT("additive_expr"), KW_NOT, KW_IN, NT("additive_expr")))
    rules["cmp_in_expr"] = AutoIgnore(Seq(NT("additive_expr"), KW_IN, NT("additive_expr")))
    rules["cmp_expr"] = AutoIgnore(
        Ch(
            NT("cmp_is_defined"),
            NT("cmp_op_expr"),
            NT("cmp_not_in_expr"),
            NT("cmp_in_expr"),
            NT("additive_expr"),
        )
    )

    # not_expr: separate named rules
    rules["not_expr_not"] = AutoIgnore(Seq(KW_NOT, NT("not_expr")))
    rules["not_expr"] = AutoIgnore(Ch(NT("not_expr_not"), NT("cmp_expr")))

    # and_expr
    rules["and_expr"] = AutoIgnore(Seq(NT("not_expr"), Star(Seq(KW_AND, NT("not_expr")))))

    # or_expr
    rules["or_expr"] = AutoIgnore(Seq(NT("and_expr"), Star(Seq(KW_OR, NT("and_expr")))))

    # cond_expr: separate named rules
    rules["cond_expr_ternary"] = AutoIgnore(Seq(NT("or_expr"), QUESTION_OP, NT("cond_expr"), COLON, NT("cond_expr")))
    rules["cond_expr"] = AutoIgnore(Ch(NT("cond_expr_ternary"), NT("or_expr")))

    rules["expression"] = AutoIgnore(NT("cond_expr"))

    # --- Statements ---
    rules["assign_normal"] = AutoIgnore(Seq(NT("var_ref"), EQUALS, NT("expression")))
    rules["assign_extend"] = AutoIgnore(Seq(NT("var_ref"), PEQ, NT("expression")))
    rules["assign"] = AutoIgnore(Ch(NT("assign_extend"), NT("assign_normal")))

    rules["for_stmt"] = AutoIgnore(Seq(KW_FOR, NT("ID"), KW_IN, NT("expression"), COLON, NT("stmt_list"), KW_END))

    rules["if_next_elif"] = AutoIgnore(Seq(KW_ELIF, NT("expression"), COLON, NT("stmt_list"), NT("if_next")))
    rules["if_next_else"] = AutoIgnore(Seq(KW_ELSE, COLON, NT("stmt_list")))
    rules["if_next_empty"] = AutoIgnore(Lit(""))
    rules["if_next"] = AutoIgnore(Ch(NT("if_next_elif"), NT("if_next_else"), NT("if_next_empty")))

    rules["if_stmt"] = AutoIgnore(Seq(KW_IF, NT("expression"), COLON, NT("stmt_list"), NT("if_next"), KW_END))

    rules["statement"] = AutoIgnore(Ch(NT("assign"), NT("for_stmt"), NT("if_stmt"), NT("expression")))
    rules["stmt_list"] = AutoIgnore(Star(NT("statement")))

    # --- Multiplicity ---
    rules["multi_range"] = AutoIgnore(Seq(LBRACK, NT("INT"), COLON, NT("INT"), RBRACK))
    rules["multi_lower"] = AutoIgnore(Seq(LBRACK, NT("INT"), COLON, RBRACK))
    rules["multi_upper"] = AutoIgnore(Seq(LBRACK, COLON, NT("INT"), RBRACK))
    rules["multi_exact"] = AutoIgnore(Seq(LBRACK, NT("INT"), RBRACK))
    rules["multi"] = AutoIgnore(Ch(NT("multi_range"), NT("multi_lower"), NT("multi_upper"), NT("multi_exact")))

    # --- id_list ---
    rules["id_list"] = AutoIgnore(Seq(NT("ID"), Star(Seq(COMMA, NT("ID")))))

    # --- class_ref_list ---
    # Use class_ref_or_err so lowercase IDs raise a nice error about capital letters
    rules["class_ref_list"] = AutoIgnore(Seq(NT("class_ref_or_err"), Star(Seq(COMMA, NT("class_ref_or_err")))))

    # --- Attr type hierarchy ---
    rules["attr_base_type"] = AutoIgnore(NT("ns_ref"))
    rules["attr_type_multi"] = AutoIgnore(Seq(NT("attr_base_type"), LBRACK, RBRACK))
    rules["attr_type_multi_opt"] = AutoIgnore(Seq(NT("attr_type_multi"), QUESTION_OP))
    rules["attr_type_base_opt"] = AutoIgnore(Seq(NT("attr_base_type"), QUESTION_OP))
    rules["attr_type"] = AutoIgnore(
        Ch(NT("attr_type_multi_opt"), NT("attr_type_base_opt"), NT("attr_type_multi"), NT("attr_base_type"))
    )

    # DICT_KW: capturing keyword rule for 'dict' (produces a LocatableString)
    rules["DICT_KW"] = AutoIgnore(Cap(Regex(r"dict(?![a-zA-Z0-9_\-])")))

    # --- Attribute definitions (many alternatives, each with its own named rule) ---
    # Normal attr: type id [= constant | constant_list | undef]
    rules["attr_no_default"] = AutoIgnore(Seq(NT("attr_type"), NT("ID")))
    rules["attr_with_const"] = AutoIgnore(Seq(NT("attr_type"), NT("ID"), EQUALS, NT("constant")))
    rules["attr_with_const_list"] = AutoIgnore(Seq(NT("attr_type"), NT("ID"), EQUALS, NT("constant_list")))
    rules["attr_with_undef"] = AutoIgnore(Seq(NT("attr_type"), NT("ID"), EQUALS, KW_UNDEF))
    # Error: CID name
    rules["attr_cid_err"] = AutoIgnore(Seq(NT("attr_type"), NT("CID")))

    # Dict attrs: use NT("DICT_KW") which captures the "dict" keyword as a LocatableString
    # dict? CID -> error
    rules["attr_dict_nullable_cid_err"] = AutoIgnore(Seq(NT("DICT_KW"), QUESTION_OP, NT("CID")))
    rules["attr_dict_cid_err"] = AutoIgnore(Seq(NT("DICT_KW"), NT("CID")))
    # dict ID = null -> error
    rules["attr_dict_null_err"] = AutoIgnore(Seq(NT("DICT_KW"), NT("ID"), EQUALS, KW_NULL))
    # dict? ID = null
    rules["attr_dict_nullable_null"] = AutoIgnore(Seq(NT("DICT_KW"), QUESTION_OP, NT("ID"), EQUALS, KW_NULL))
    # dict ID = map_def
    rules["attr_dict_map"] = AutoIgnore(Seq(NT("DICT_KW"), NT("ID"), EQUALS, NT("primary_map_def")))
    # dict? ID = map_def
    rules["attr_dict_nullable_map"] = AutoIgnore(Seq(NT("DICT_KW"), QUESTION_OP, NT("ID"), EQUALS, NT("primary_map_def")))
    # dict ID
    rules["attr_dict_plain"] = AutoIgnore(Seq(NT("DICT_KW"), NT("ID")))
    # dict? ID
    rules["attr_dict_nullable_plain"] = AutoIgnore(Seq(NT("DICT_KW"), QUESTION_OP, NT("ID")))

    rules["attr"] = AutoIgnore(
        Ch(
            NT("attr_dict_nullable_cid_err"),
            NT("attr_dict_cid_err"),
            NT("attr_dict_nullable_null"),
            NT("attr_dict_null_err"),
            NT("attr_dict_nullable_map"),
            NT("attr_dict_map"),
            NT("attr_dict_nullable_plain"),
            NT("attr_dict_plain"),
            NT("attr_cid_err"),
            NT("attr_with_undef"),
            NT("attr_with_const"),
            NT("attr_with_const_list"),
            NT("attr_no_default"),
        )
    )

    # --- Entity body ---
    rules["entity_body"] = AutoIgnore(Star(NT("attr")))
    rules["entity_body_outer_with_doc"] = AutoIgnore(Seq(NT("MLS"), NT("entity_body"), KW_END))
    rules["entity_body_outer_no_doc"] = AutoIgnore(Seq(NT("entity_body"), KW_END))
    rules["entity_body_outer"] = AutoIgnore(Ch(NT("entity_body_outer_with_doc"), NT("entity_body_outer_no_doc")))

    # --- Entity definition ---
    rules["entity_def_plain"] = AutoIgnore(Seq(KW_ENTITY, NT("CID"), COLON, NT("entity_body_outer")))
    rules["entity_def_extends"] = AutoIgnore(
        Seq(KW_ENTITY, NT("CID"), KW_EXTENDS, NT("class_ref_list"), COLON, NT("entity_body_outer"))
    )
    rules["entity_def_plain_err"] = AutoIgnore(Seq(KW_ENTITY, NT("ID"), COLON, NT("entity_body_outer")))
    rules["entity_def_extends_err"] = AutoIgnore(
        Seq(KW_ENTITY, NT("ID"), KW_EXTENDS, NT("class_ref_list"), COLON, NT("entity_body_outer"))
    )
    rules["entity_def"] = AutoIgnore(
        Ch(NT("entity_def_plain"), NT("entity_def_extends"), NT("entity_def_plain_err"), NT("entity_def_extends_err"))
    )

    # --- Implement ns list ---
    rules["impl_ns_ref"] = AutoIgnore(NT("ns_ref"))
    rules["impl_parents"] = AutoIgnore(KW_PARENTS)
    rules["impl_ns_item"] = AutoIgnore(Ch(NT("impl_ns_ref"), NT("impl_parents")))
    rules["implement_ns_list"] = AutoIgnore(Seq(NT("impl_ns_item"), Star(Seq(COMMA, NT("impl_ns_item")))))

    # --- Implement definition ---
    rules["implement_def_no_when"] = AutoIgnore(
        Seq(KW_IMPLEMENT, NT("class_ref"), KW_USING, NT("implement_ns_list"), Opt(NT("MLS")))
    )
    rules["implement_def_when"] = AutoIgnore(
        Seq(KW_IMPLEMENT, NT("class_ref"), KW_USING, NT("implement_ns_list"), KW_WHEN, NT("expression"), Opt(NT("MLS")))
    )
    rules["implement_def"] = AutoIgnore(Ch(NT("implement_def_when"), NT("implement_def_no_when")))

    # --- Implementation definition ---
    rules["implementation_def_with_doc"] = AutoIgnore(
        Seq(KW_IMPLEMENTATION, NT("ID"), KW_FOR, NT("class_ref"), COLON, NT("MLS"), NT("stmt_list"), KW_END)
    )
    rules["implementation_def_no_doc"] = AutoIgnore(
        Seq(KW_IMPLEMENTATION, NT("ID"), KW_FOR, NT("class_ref"), COLON, NT("stmt_list"), KW_END)
    )
    rules["implementation_def"] = AutoIgnore(Ch(NT("implementation_def_with_doc"), NT("implementation_def_no_doc")))

    # --- Relation definitions ---
    rules["relation_bidir"] = AutoIgnore(
        Seq(NT("class_ref"), DOT_OP, NT("ID"), NT("multi"), NT("REL"), NT("class_ref"), DOT_OP, NT("ID"), NT("multi"))
    )
    rules["relation_bidir_ann"] = AutoIgnore(
        Seq(NT("class_ref"), DOT_OP, NT("ID"), NT("multi"), NT("operand_list"), NT("class_ref"), DOT_OP, NT("ID"), NT("multi"))
    )
    rules["relation_unidir"] = AutoIgnore(Seq(NT("class_ref"), DOT_OP, NT("ID"), NT("multi"), NT("REL"), NT("class_ref")))
    rules["relation_unidir_ann"] = AutoIgnore(
        Seq(NT("class_ref"), DOT_OP, NT("ID"), NT("multi"), NT("operand_list"), NT("class_ref"))
    )
    rules["relation_def"] = AutoIgnore(
        Ch(NT("relation_bidir_ann"), NT("relation_bidir"), NT("relation_unidir_ann"), NT("relation_unidir"))
    )
    rules["relation_with_comment"] = AutoIgnore(Seq(NT("relation_def"), NT("MLS")))
    rules["relation"] = AutoIgnore(Ch(NT("relation_with_comment"), NT("relation_def")))

    # --- Typedef ---
    rules["typedef_regex"] = AutoIgnore(Seq(KW_TYPEDEF, NT("ID"), KW_AS, NT("ns_ref"), NT("REGEX_TOKEN")))
    rules["typedef_expr"] = AutoIgnore(Seq(KW_TYPEDEF, NT("ID"), KW_AS, NT("ns_ref"), KW_MATCHING, NT("expression")))
    # Legacy error: typedef CID AS constructor — raises ParserException
    rules["typedef_cls"] = AutoIgnore(Seq(KW_TYPEDEF, NT("CID"), KW_AS, NT("primary_constructor")))
    rules["typedef_inner"] = AutoIgnore(Ch(NT("typedef_regex"), NT("typedef_expr"), NT("typedef_cls")))
    rules["typedef_with_comment"] = AutoIgnore(Seq(NT("typedef_inner"), NT("MLS")))
    rules["typedef"] = AutoIgnore(Ch(NT("typedef_with_comment"), NT("typedef_inner")))

    # --- Index ---
    rules["index"] = AutoIgnore(Seq(KW_INDEX, NT("class_ref"), LPAREN, NT("id_list"), RPAREN))

    # --- Import ---
    rules["import_as"] = AutoIgnore(Seq(KW_IMPORT, NT("ns_ref"), KW_AS, NT("ID")))
    rules["import_plain"] = AutoIgnore(Seq(KW_IMPORT, NT("ns_ref")))
    rules["import_stmt"] = AutoIgnore(Ch(NT("import_as"), NT("import_plain")))

    # --- Top-level statement ---
    rules["top_stmt"] = AutoIgnore(
        Ch(
            NT("entity_def"),
            NT("implement_def"),
            NT("implementation_def"),
            NT("relation"),
            NT("typedef"),
            NT("index"),
            NT("import_stmt"),
            NT("statement"),
        )
    )

    # --- Start rule ---
    rules["Start"] = AutoIgnore(Seq(Opt(NT("MLS")), Star(NT("top_stmt")), Not(DOT())))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    actions: dict[str, object] = {
        # Tokens
        "ID": P(act_ID),
        "CID": P(act_CID),
        "DICT_KW": P(act_ID),  # same as ID action – produces LocatableString
        "INT": P(act_INT),
        "FLOAT": P(act_FLOAT),
        "STRING": P(act_STRING),
        "MLS": P(act_MLS),
        "FSTRING": P(act_FSTRING),
        "RSTRING": P(act_RSTRING),
        "REGEX_TOKEN": P(act_REGEX_TOKEN),
        # References
        "ns_ref": P(act_ns_ref),
        "class_ref_qualified": P(act_class_ref_qualified),
        "class_ref_simple": P(act_class_ref_simple),
        "class_ref_dot_err": P(act_class_ref_dot_err),
        "class_ref": P(lambda s, pos, end, a: a[0]),
        "class_ref_id_err": P(act_class_ref_id_err),
        "class_ref_or_err": P(lambda s, pos, end, a: a[0]),
        "var_ref": P(act_var_ref),
        "attr_ref": P(act_attr_ref),
        # Constants
        "constant_INT": P(act_constant_INT),
        "constant_FLOAT": P(act_constant_FLOAT),
        "constant_NULL": P(act_constant_NULL),
        "constant_TRUE": P(act_constant_TRUE),
        "constant_FALSE": P(act_constant_FALSE),
        "constant_STRING": P(act_constant_STRING),
        "constant_MLS": P(act_constant_MLS),
        "constant_FSTRING": P(act_constant_FSTRING),
        "constant_RSTRING": P(act_constant_RSTRING),
        "constant_REGEX": P(act_constant_REGEX),
        # Illegal string error rules
        "illegal_string_dbl": P(act_illegal_string_dbl),
        "illegal_string_sgl": P(act_illegal_string_sgl),
        "illegal_fstring_dbl": P(act_illegal_prefixed_string_dbl),
        "illegal_fstring_sgl": P(act_illegal_prefixed_string_sgl),
        "illegal_rstring_dbl": P(act_illegal_prefixed_string_dbl),
        "illegal_rstring_sgl": P(act_illegal_prefixed_string_sgl),
        "constant": P(lambda s, pos, end, a: a[0]),
        "constant_list": P(act_constant_list),
        # Operand list
        "operand_list": P(act_operand_list),
        # Dict key / pair
        "dict_key_string": P(act_dict_key_string),
        "dict_key_rstring": P(act_dict_key_rstring),
        "dict_key": P(lambda s, pos, end, a: a[0]),
        "pair_entry": P(act_pair_entry),
        "pair_list": P(act_pair_list),
        # Param lists
        "param_list_kwarg": P(act_param_list_kwarg),
        "param_list_wrapped": P(act_param_list_wrapped),
        "param_list_element": P(lambda s, pos, end, a: a[0]),
        "param_list": P(act_param_list),
        "function_param_positional": P(act_function_param_positional),
        "function_param_kwarg": P(act_function_param_kwarg),
        "function_param_wrapped": P(act_function_param_wrapped),
        "function_param_element": P(lambda s, pos, end, a: a[0]),
        "function_param_list": P(act_function_param_list),
        # List comprehension
        "list_comprehension_for_last": P(
            lambda s, pos, end, a: [
                ForSpecifier(variable=typing.cast(LocatableString, a[0]), iterable=typing.cast(ExpressionStatement, a[1]))
            ]
        ),
        "list_comprehension_for_inner": P(act_lc_for_with_sub),
        "list_comprehension_for": P(lambda s, pos, end, a: a[0]),
        "list_comprehension_guard_last": P(lambda s, pos, end, a: a[0]),
        "list_comprehension_guard_with": P(act_lc_guard),
        "list_comprehension_guard": P(lambda s, pos, end, a: a[0]),
        "list_comprehension_guard_opt": P(lambda s, pos, end, a: a[0] if a else None),
        # Primary
        "primary_constructor": P(act_primary_constructor),
        "primary_index_lookup": P(act_primary_index_lookup),
        "primary_func_err": P(act_primary_func_err),
        "primary_func_call": P(act_primary_func_call),
        "primary_list_comp": P(act_primary_list_comp),
        "primary_list_def": P(act_primary_list_def),
        "primary_map_def": P(act_primary_map_def),
        "primary_constant": P(lambda s, pos, end, a: a[0]),
        "primary_paren": P(act_primary_paren),
        "primary_varref": P(act_primary_varref),
        "primary": P(lambda s, pos, end, a: a[0]),
        # Subscript
        # param_list_nonempty uses same action as param_list
        "param_list_nonempty": P(act_param_list),
        # subscript_map: Seq(LBRACK, expression, RBRACK) → expression
        "subscript_map": P(lambda s, pos, end, a: a[0]),
        # subscript_index: Seq(LBRACK, param_list_nonempty, RBRACK) → (kwargs, wrapped) tuple
        "subscript_index": P(lambda s, pos, end, a: a[0]),
        # postfix_subscript_step: Ch(subscript_index, subscript_map) → passes through
        "postfix_subscript_step": P(lambda s, pos, end, a: a[0]),
        # postfix_expr: Seq(primary, Star(postfix_subscript_step))
        # args: [primary, subscript1, subscript2, ...]
        "postfix_expr": P(
            lambda s, pos, end, a: (
                a[0]
                if len(a) == 1
                else functools.reduce(
                    lambda base, sub: _apply_subscript(typing.cast(ExpressionStatement, base), sub, pos), a[1:], a[0]
                )
            )
        ),
        # pow_expr
        "pow_expr_with_pow": P(act_pow),
        "pow_expr": P(lambda s, pos, end, a: a[0]),
        # mul_expr
        "mul_expr": P(act_mul),
        # additive_expr
        "additive_expr": P(act_additive),
        # cmp_expr
        "cmp_is_defined": P(act_cmp_is_defined),
        "cmp_op_expr": P(act_cmp_op),
        "cmp_not_in_expr": P(act_cmp_not_in),
        "cmp_in_expr": P(act_cmp_in),
        "cmp_expr": P(lambda s, pos, end, a: a[0]),
        # not_expr
        "not_expr_not": P(act_not_expr_not),
        "not_expr": P(lambda s, pos, end, a: a[0]),
        # and_expr
        "and_expr": P(act_and_expr),
        # or_expr
        "or_expr": P(act_or_expr),
        # cond_expr
        "cond_expr_ternary": P(act_cond_expr),
        "cond_expr": P(lambda s, pos, end, a: a[0]),
        "expression": P(lambda s, pos, end, a: a[0]),
        # Statements
        "assign_normal": P(act_assign_normal),
        "assign_extend": P(act_assign_extend),
        "assign": P(lambda s, pos, end, a: a[0]),
        "for_stmt": P(act_for_stmt),
        "if_next_elif": P(act_if_next_elif),
        "if_next_else": P(act_if_next_else),
        "if_next_empty": P(act_if_next_empty),
        "if_next": P(lambda s, pos, end, a: a[0]),
        "if_stmt": P(act_if_stmt),
        "statement": P(lambda s, pos, end, a: a[0]),
        "stmt_list": P(act_stmt_list),
        # Multiplicity
        "multi_exact": P(act_multi_exact),
        "multi_lower": P(act_multi_lower),
        "multi_range": P(act_multi_range),
        "multi_upper": P(act_multi_upper),
        "multi": P(lambda s, pos, end, a: a[0]),
        # id_list, class_ref_list
        "id_list": P(act_id_list),
        "class_ref_list": P(act_class_ref_list),
        # Attr type
        "attr_base_type": P(act_attr_base_type),
        "attr_type_multi": P(act_attr_type_multi),
        "attr_type_multi_opt": P(lambda s, pos, end, a: act_attr_type_opt(s, pos, end, a)),
        "attr_type_base_opt": P(lambda s, pos, end, a: act_attr_type_opt(s, pos, end, a)),
        "attr_type": P(lambda s, pos, end, a: a[0]),
        # Attrs
        "attr_no_default": P(lambda s, pos, end, a: act_attr_normal(s, pos, end, list(a))),
        "attr_with_const": P(lambda s, pos, end, a: act_attr_normal(s, pos, end, list(a))),
        "attr_with_const_list": P(lambda s, pos, end, a: act_attr_normal(s, pos, end, list(a))),
        "attr_with_undef": P(act_attr_undef),
        "attr_cid_err": P(lambda s, pos, end, a: act_attr_cid_err(s, pos, end, [a[1]])),
        "attr_dict_plain": P(lambda s, pos, end, a: act_attr_dict(s, pos, end, list(a))),
        "attr_dict_map": P(lambda s, pos, end, a: act_attr_dict(s, pos, end, list(a))),
        "attr_dict_null_err": P(lambda s, pos, end, a: act_attr_dict_null_err(s, pos, end, list(a))),
        "attr_dict_nullable_plain": P(lambda s, pos, end, a: act_attr_dict_nullable(s, pos, end, list(a))),
        "attr_dict_nullable_map": P(lambda s, pos, end, a: act_attr_dict_nullable(s, pos, end, list(a))),
        "attr_dict_nullable_null": P(
            lambda s, pos, end, a: act_attr_dict_nullable(s, pos, end, list(a) + [_locate(Literal(NoneValue()), pos)])
        ),
        "attr_dict_cid_err": P(lambda s, pos, end, a: act_attr_dict_cid_err(s, pos, end, [a[-1]])),
        "attr_dict_nullable_cid_err": P(lambda s, pos, end, a: act_attr_dict_cid_err(s, pos, end, [a[-1]])),
        "attr": P(lambda s, pos, end, a: a[0]),
        # Entity body
        "entity_body": P(lambda s, pos, end, a: list(a)),
        "entity_body_outer_with_doc": P(act_entity_body_outer_with_doc),
        "entity_body_outer_no_doc": P(act_entity_body_outer_no_doc),
        "entity_body_outer": P(lambda s, pos, end, a: a[0]),
        # Entity def
        "entity_def_plain": P(lambda s, pos, end, a: act_entity_def(s, pos, end, [a[0], a[1]])),
        "entity_def_extends": P(lambda s, pos, end, a: act_entity_def(s, pos, end, [a[0], a[1], a[2]])),
        "entity_def_plain_err": P(act_entity_err),
        "entity_def_extends_err": P(act_entity_err),
        "entity_def": P(lambda s, pos, end, a: a[0]),
        # Implement ns list
        "impl_ns_ref": P(act_impl_ns_ref),
        "impl_parents": P(act_impl_parents),
        "impl_ns_item": P(lambda s, pos, end, a: a[0]),
        "implement_ns_list": P(act_impl_ns_list),
        # Implement def
        "implement_def_no_when": P(act_implement_def_no_when),
        "implement_def_when": P(act_implement_def_when),
        "implement_def": P(lambda s, pos, end, a: a[0]),
        # Implementation def
        "implementation_def_with_doc": P(lambda s, pos, end, a: act_implementation_def(s, pos, end, [a[0], a[1], a[2], a[3]])),
        "implementation_def_no_doc": P(lambda s, pos, end, a: act_implementation_def(s, pos, end, [a[0], a[1], a[2]])),
        "implementation_def": P(lambda s, pos, end, a: a[0]),
        # Relation
        "relation_bidir": P(act_relation_bidir),
        "relation_bidir_ann": P(act_relation_bidir_ann),
        "relation_unidir": P(act_relation_unidir),
        "relation_unidir_ann": P(act_relation_unidir_ann),
        "relation_def": P(lambda s, pos, end, a: a[0]),
        "relation_with_comment": P(act_relation_with_comment),
        "relation": P(lambda s, pos, end, a: a[0]),
        # Typedef
        "typedef_regex": P(act_typedef_no_comment),
        "typedef_expr": P(act_typedef_no_comment),
        "typedef_cls": P(act_typedef_cls),
        "typedef_inner": P(lambda s, pos, end, a: a[0]),
        "typedef_with_comment": P(act_typedef_with_comment),
        "typedef": P(lambda s, pos, end, a: a[0]),
        # Index
        "index": P(act_index),
        # Import
        "import_as": P(act_import_as),
        "import_plain": P(act_import),
        "import_stmt": P(lambda s, pos, end, a: a[0]),
        # Top-level
        "top_stmt": P(lambda s, pos, end, a: a[0]),
        # Start
        "Start": P(act_start),
    }

    grammar = Grammar(rules, actions=actions, start="Start")
    WS_IGNORE = Star(Ch(Class(" \t\n\r"), COMMENT))
    parser = PackratParser(grammar, ignore=WS_IGNORE)
    return parser


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

cache_manager: CacheManager = CacheManager()


def base_parse(ns: Namespace, tfile: str, content: Optional[str]) -> list[Statement]:
    """Parse a file or string and return the list of AST statements."""
    global _parser

    _state.filename = tfile
    _state.namespace = ns

    if content is None:
        with open(tfile, encoding="utf-8") as fh:
            data = fh.read()
    else:
        data = content

    if len(data) == 0:
        return []

    # Ensure newline at end to prevent EOF issues
    if not data.endswith("\n"):
        data = data + "\n"

    _state.tracker = PositionTracker(data)

    if _parser is None:
        _parser = _build_parser()

    try:
        m = _parser.match(data, pos=0)
    except pe.ParseError as exc:
        # pe.ParseError stores (lineno, offset) relative to a line, not absolute pos.
        # Reconstruct absolute position from lineno + offset.
        assert _state.tracker is not None
        if exc.lineno is not None and exc.offset is not None:
            # lineno is 0-based; Range uses 1-based line numbers
            lnr = exc.lineno + 1
            # offset is 0-based; Range uses 1-based column numbers
            col = exc.offset + 1
        else:
            lnr, col = 1, 1
        r = Range(tfile, lnr, col, lnr, col + 1)
        # Compute absolute position in data
        lines = data.split("\n")
        abs_pos: int = sum(len(lines[i]) + 1 for i in range(exc.lineno or 0)) + (exc.offset or 0)
        char = data[abs_pos] if abs_pos < len(data) else None
        # Check if the failure position is at a reserved keyword (PLY-compatible error message)
        if char is not None and char.isalpha():
            # Extract word starting at abs_pos
            word_end = abs_pos
            while word_end < len(data) and (data[word_end].isalnum() or data[word_end] in "_-"):
                word_end += 1
            word = data[abs_pos:word_end]
            if word in _KEYWORDS:
                raise ParserException(r, word, f"invalid identifier, {word} is a reserved keyword") from exc
        # Check if the word immediately BEFORE abs_pos (skipping whitespace) is a keyword.
        # This covers: "index = x" where pe fails at "=" but the real issue is "index".
        scan_pos = abs_pos - 1
        while scan_pos >= 0 and data[scan_pos] in " \t":
            scan_pos -= 1
        if scan_pos >= 0 and (data[scan_pos].isalnum() or data[scan_pos] in "_-"):
            word_end2 = scan_pos + 1
            word_start2 = scan_pos
            while word_start2 > 0 and (data[word_start2 - 1].isalnum() or data[word_start2 - 1] in "_-"):
                word_start2 -= 1
            prev_word = data[word_start2:word_end2]
            if prev_word in _KEYWORDS:
                prev_lnr, prev_col = _state.tracker.pos_to_lnr_col(word_start2)
                prev_r = Range(tfile, prev_lnr, prev_col, prev_lnr, prev_col + len(prev_word))
                raise ParserException(prev_r, prev_word, f"invalid identifier, {prev_word} is a reserved keyword") from exc
        # Use PLY-compatible format: "Syntax error at token X" (no msg kwarg)
        raise ParserException(r, char) from exc

    if m is None:
        r = Range(tfile, 1, 1, 1, 1)
        raise ParserException(r, None, "Parse failed: no match")

    result = m.value()
    if result is None:
        return []
    if isinstance(result, list):
        return typing.cast(list[Statement], result)
    return [typing.cast(Statement, result)]


def parse(namespace: Namespace, filename: str, content: Optional[str] = None) -> list[Statement]:
    """Parse with cache support."""
    statements = cache_manager.un_cache(namespace, filename)
    if statements is not None:
        return statements
    statements = base_parse(namespace, filename, content)
    cache_manager.cache(namespace, filename, statements)
    return statements
