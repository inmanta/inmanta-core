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

Lark-based parser for the Inmanta DSL.
This is a port of the PLY-based parser (plyInmantaParser.py / plyInmantaLex.py) to Lark.
"""

import functools
import os
import re
import string
import typing
import warnings
from collections import abc
from dataclasses import dataclass, field
from re import error as RegexError
from typing import Optional, Union

from lark import Lark, Token, Transformer, UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, v_args
from lark.exceptions import UnexpectedToken, VisitError

from inmanta.ast import LocatableString, Location, Namespace, Range, RuntimeException
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.constraint.expression import And, In, IsDefined, Not, NotEqual, Operator
from inmanta.ast.statements import ExpressionStatement, Literal, Statement
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
from inmanta.parser import InvalidNamespaceAccess, ParserException, ParserWarning, SyntaxDeprecationWarning
from inmanta.parser.cache import CacheManager

# ---- Grammar loading ----

_GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "larkInmanta.lark")

with open(_GRAMMAR_FILE, encoding="utf-8") as _f:
    _GRAMMAR = _f.read()

_lark_parser = Lark(
    _GRAMMAR,
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
)


# ---- Format-string regex (same as PLY parser) ----

_format_regex = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
_format_regex_compiled = re.compile(_format_regex, re.MULTILINE | re.DOTALL)

# Set of reserved keywords – used to reject keywords used as identifiers.
# Lark's contextual lexer matches keywords as ID when ID is valid in the grammar,
# so we must validate at the transformer level.
_RESERVED_KEYWORDS: frozenset[str] = frozenset(
    [
        "typedef", "as", "entity", "extends", "end", "in", "implementation",
        "for", "matching", "index", "implement", "using", "when", "and", "or",
        "not", "true", "false", "import", "is", "defined", "dict", "null",
        "undef", "parents", "if", "else", "elif",
    ]
)


# ---- Helper dataclasses (internal to transformer) ----


@dataclass
class _ForClause:
    """Internal: represents a 'for ID in expression' clause in a list comprehension."""

    variable: LocatableString
    iterable: ExpressionStatement
    guard: Optional[ExpressionStatement] = None


@dataclass
class _GuardClause:
    """Internal: represents an 'if expression' clause in a list comprehension."""

    condition: ExpressionStatement


@dataclass
class _ImplementNsItem:
    """Internal: one item in an implement using ... list."""

    inherit_parents: bool
    ns_ref: Optional[LocatableString]  # None when inherit_parents is True


@dataclass
class _ParamListElement:
    """Internal: one element in a param_list (for constructors / index lookups)."""

    key: Optional[LocatableString]  # None for wrapped_kwargs
    value: Optional[ExpressionStatement]  # None for wrapped_kwargs
    wrapped_kwargs: Optional["WrappedKwargs"] = None


@dataclass
class _FunctionParamElement:
    """Internal: one element in a function_param_list."""

    arg: Optional[ExpressionStatement] = None
    key: Optional[LocatableString] = None
    value: Optional[ExpressionStatement] = None
    wrapped_kwargs: Optional["WrappedKwargs"] = None


# ---- String decoding (mirrors PLY safe_decode) ----


def _safe_decode(raw: str, warning_msg: str, location: Location) -> str:
    """
    Decode unicode escape sequences in a string, raising ParserWarning for invalid escapes.
    Mirrors PLY's safe_decode() function.
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="invalid escape sequence", category=DeprecationWarning)
            value: str = bytes(raw, "utf_8").decode("unicode_escape")
    except DeprecationWarning:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            value = bytes(raw, "utf_8").decode("unicode_escape")
        warnings.warn(ParserWarning(location=location, msg=warning_msg, value=value))
    return value


# ---- Transformer ----


class InmantaTransformer(Transformer):
    """
    Transforms a Lark parse tree for the Inmanta DSL into the AST used by the compiler.

    This mirrors the p_* functions in the PLY-based parser.
    Each method corresponds to one grammar rule alias.
    """

    def __init__(self, tfile: str, namespace: Namespace) -> None:
        super().__init__()
        self.file = tfile
        self.namespace = namespace

    # ---- Position helpers ----

    def _loc(self, token: Token) -> Location:
        """Create a Location (file + line) from a Lark Token."""
        return Location(self.file, token.line)

    def _range(self, token: Token) -> Range:
        """Create a Range from a Lark Token."""
        end_line = token.end_line if token.end_line is not None else token.line
        end_col = token.end_column if token.end_column is not None else (token.column + len(str(token)))
        return Range(self.file, token.line, token.column, end_line, end_col)

    def _locatable(self, token: Token) -> LocatableString:
        """Create a LocatableString from a Lark Token (ID, CID, or keyword token)."""
        return LocatableString(
            str(token),
            self._range(token),
            getattr(token, "pos_in_stream", 0) or 0,
            self.namespace,
        )

    def _meta_range(self, meta) -> Range:
        """Create a Range from a tree's meta (propagated positions)."""
        return Range(
            self.file,
            meta.line,
            meta.column,
            meta.end_line if meta.end_line is not None else meta.line,
            meta.end_column if meta.end_column is not None else meta.column,
        )

    def _meta_loc(self, meta) -> Location:
        return Location(self.file, meta.line)

    def _attach(self, node, location: Location, lexpos: int = 0) -> None:
        """Set location and namespace on an AST node (mirrors attach_lnr)."""
        node.location = location
        node.namespace = self.namespace
        node.lexpos = lexpos

    def _attach_from_string(self, node, ls: LocatableString) -> None:
        """Copy location and namespace from a LocatableString to a node (mirrors attach_from_string)."""
        node.location = ls.location
        node.namespace = ls.namespace

    def _make_none(self, location: Location, lexpos: int = 0) -> Literal:
        """Create a Literal(NoneValue()) with given location (mirrors make_none)."""
        none = Literal(NoneValue())
        none.location = location
        none.namespace = self.namespace
        none.lexpos = lexpos
        return none

    def _expand_range(self, start: Range, end: Range) -> Range:
        """Merge two ranges into one spanning from start to end."""
        return Range(start.file, start.lnr, start.start_char, end.end_lnr, end.end_char)

    def _validate_id(self, token: Token) -> None:
        """Raise ParserException if an ID token holds a reserved keyword value.

        Lark's contextual lexer matches keywords as ID when the grammar expects ID.
        We enforce keyword rejection here, mirroring the PLY parser's p_error behaviour.
        """
        value = str(token)
        if value in _RESERVED_KEYWORDS:
            r = self._range(token)
            raise ParserException(r, value, f"invalid identifier, {value} is a reserved keyword")

    # ---- Top-level ----

    def start(self, items):
        # items: [head_result, body_result]
        # head is None or a LocatableString (MLS docstring)
        # body is a list of statements
        head, body = items
        if head is not None:
            body.insert(0, head)
        return body

    def head(self, items):
        # items: [] or [MLS_token]
        if not items:
            return None
        return self._locatable(items[0])

    def body(self, items):
        return list(items)

    def top_stmt(self, items):
        return items[0]

    # ---- Imports ----

    @v_args(meta=True)
    def import_ns(self, meta, items):
        # items: [IMPORT_token, ns_ref_result]
        import_token = items[0]
        ns_ref = items[1]
        result = DefineImport(str(ns_ref), ns_ref)
        self._attach(result, self._loc(import_token), getattr(import_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def import_as(self, meta, items):
        # items: [IMPORT_token, ns_ref_result, AS_token, ID_token]
        import_token = items[0]
        ns_ref = items[1]
        id_token = items[3]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineImport(str(ns_ref), id_ls)
        self._attach(result, self._loc(import_token), getattr(import_token, "pos_in_stream", 0) or 0)
        return result

    # ---- Statements ----

    def statement(self, items):
        return items[0]

    def stmt_list(self, items):
        return list(items)

    def expr_stmt(self, items):
        return items[0]

    @v_args(meta=True)
    def assign_eq(self, meta, items):
        # items: [var_ref_result, EQ_token_or_nothing, operand_result]
        # "=" is anonymous => filtered; items = [var_ref, operand]
        var_ref = items[0]
        operand = items[1]
        result = var_ref.as_assign(operand)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def assign_plus_eq(self, meta, items):
        # items: [var_ref_result, PEQ_token, operand_result]
        var_ref = items[0]
        peq_token = items[1]
        operand = items[2]
        result = var_ref.as_assign(operand, list_only=True)
        self._attach(result, self._loc(peq_token), getattr(peq_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def for_stmt(self, meta, items):
        # items: [FOR_token, ID_token, IN_token, operand_result, block_result]
        for_token = items[0]
        id_token = items[1]
        # IN_token = items[2]
        self._validate_id(id_token)
        operand = items[3]
        block = items[4]
        id_ls = self._locatable(id_token)
        result = For(operand, id_ls, BasicBlock(self.namespace, block))
        self._attach(result, self._loc(for_token), getattr(for_token, "pos_in_stream", 0) or 0)
        return result

    def block(self, items):
        # items: [stmt_list, END_token]
        return items[0]

    @v_args(meta=True)
    def if_stmt(self, meta, items):
        # items: [IF_token, if_body_result, END_token]
        if_token = items[0]
        if_body = items[1]
        if_body.location = self._loc(if_token)
        if_body.namespace = self.namespace
        return if_body

    @v_args(meta=True)
    def if_body(self, meta, items):
        # items: [expression_result, stmt_list_result, if_next_result]
        # ":" is anonymous => filtered
        condition = items[0]
        stmts = items[1]
        next_block = items[2]
        result = If(condition, BasicBlock(self.namespace, stmts), next_block)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def if_next_empty(self, items):
        return BasicBlock(self.namespace, [])

    def if_next_else(self, items):
        # items: [ELSE_token, stmt_list_result]
        stmts = items[1]
        return BasicBlock(self.namespace, stmts)

    @v_args(meta=True)
    def if_next_elif(self, meta, items):
        # items: [ELIF_token, if_body_result]
        elif_token = items[0]
        if_body = items[1]
        result = BasicBlock(self.namespace, [if_body])
        result.location = self._loc(elif_token)
        result.namespace = self.namespace
        return result

    def operand(self, items):
        return items[0]

    # ---- Entity definitions ----

    @v_args(meta=True)
    def entity_def(self, meta, items):
        # items: [ENTITY_token, CID_token, entity_body_outer_result]
        entity_token = items[0]
        cid_token = items[1]
        docstr, attrs = items[2]
        cid_ls = self._locatable(cid_token)
        result = DefineEntity(self.namespace, cid_ls, docstr, [], attrs)
        self._attach(result, self._loc(entity_token), getattr(entity_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def entity_def_extends(self, meta, items):
        # items: [ENTITY_token, CID_token, EXTENDS_token, class_ref_list, entity_body_outer]
        entity_token = items[0]
        cid_token = items[1]
        # EXTENDS_token = items[2]
        class_ref_list = items[3]
        docstr, attrs = items[4]
        cid_ls = self._locatable(cid_token)
        result = DefineEntity(self.namespace, cid_ls, docstr, class_ref_list, attrs)
        self._attach(result, self._loc(entity_token), getattr(entity_token, "pos_in_stream", 0) or 0)
        return result

    def entity_def_err(self, items):
        # items: [ENTITY_token, ID_token, ...]
        id_token = items[1]
        id_ls = self._locatable(id_token)
        raise ParserException(id_ls.location, str(id_ls), "Invalid identifier: Entity names must start with a capital")

    def entity_def_extends_err(self, items):
        id_token = items[1]
        id_ls = self._locatable(id_token)
        raise ParserException(id_ls.location, str(id_ls), "Invalid identifier: Entity names must start with a capital")

    def entity_body_outer_mls(self, items):
        # items: [MLS_token, entity_body_result, END_token]
        mls_token = items[0]
        attrs = items[1]
        docstr = self._process_mls(mls_token)
        return (docstr, attrs)

    def entity_body_outer_plain(self, items):
        # items: [entity_body_result, END_token]
        attrs = items[0]
        return (None, attrs)

    def entity_body_outer_mls_only(self, items):
        # items: [MLS_token, END_token]
        mls_token = items[0]
        docstr = self._process_mls(mls_token)
        return (docstr, [])

    def entity_body_outer_empty(self, items):
        return (None, [])

    def entity_body(self, items):
        return list(items)

    def _process_mls(self, token: Token) -> LocatableString:
        """Process a MLS token into a LocatableString with decoded content."""
        raw = str(token)
        # Strip triple quotes (3-5 quotes)
        n = 0
        for c in raw:
            if c == '"':
                n += 1
            else:
                break
        content = raw[n:-n]
        loc = Location(self.file, token.line)
        decoded = _safe_decode(content, "Invalid escape sequence in multi-line string.", loc)
        # Calculate end position
        lines = raw.split("\n")
        end_line = token.line + len(lines) - 1
        end_col = len(lines[-1]) + 1
        r = Range(self.file, token.line, token.column, end_line, end_col)
        return LocatableString(decoded, r, getattr(token, "pos_in_stream", 0) or 0, self.namespace)

    # ---- Attributes ----

    def attr_base_type(self, items):
        # items: [ns_ref_result]
        ns = items[0]
        result = TypeDeclaration(ns)
        self._attach_from_string(result, ns)
        return result

    def attr_type_multi(self, items):
        # items: [attr_base_type_result]
        td = items[0]
        td.multi = True
        return td

    def attr_type_opt_multi(self, items):
        # items: [attr_type_multi_result]
        td = items[0]
        td.nullable = True
        return td

    def attr_type_opt_base(self, items):
        # items: [attr_base_type_result]
        td = items[0]
        td.nullable = True
        return td

    def attr_simple(self, items):
        # items: [attr_type_result, ID_token]
        attr_type = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_cte(self, items):
        # items: [attr_type_result, ID_token, constant_result]
        attr_type = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        constant = items[2]
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, constant)
        self._attach_from_string(result, id_ls)
        return result

    def attr_cte_list(self, items):
        # items: [attr_type_result, ID_token, constant_list_result]
        attr_type = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        clist = items[2]
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, clist)
        self._attach_from_string(result, id_ls)
        return result

    def attr_undef(self, items):
        # items: [attr_type_result, ID_token, UNDEF_token]
        attr_type = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, None, remove_default=True)
        self._attach_from_string(result, id_ls)
        return result

    def attr_err(self, items):
        # items: [attr_type_result, CID_token, ...]
        cid_token = items[1]
        cid_ls = self._locatable(cid_token)
        raise ParserException(
            cid_ls.location, str(cid_ls), "Invalid identifier: attribute names must start with a lower case character"
        )

    def _make_dict_type(self, dict_token: Token, nullable: bool = False) -> TypeDeclaration:
        """Create a TypeDeclaration for 'dict' from a DICT keyword token."""
        dict_ls = self._locatable(dict_token)
        return TypeDeclaration(dict_ls, nullable=nullable)

    def attr_dict(self, items):
        # items: [DICT_token, ID_token]
        dict_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token), id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict(self, items):
        # items: [DICT_token, ID_token, map_def_result]
        dict_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        map_def = items[2]
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token), id_ls, map_def)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_null_err(self, items):
        # items: [DICT_token, ID_token, NULL_token]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        raise ParserException(
            id_ls.location, str(id_ls), 'null can not be assigned to dict, did you mean "dict? %s = null"' % id_ls
        )

    def attr_dict_nullable(self, items):
        # items: [DICT_token, ID_token]  ("?" is anonymous => filtered)
        dict_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_nullable(self, items):
        # items: [DICT_token, ID_token, map_def_result]  ("?" filtered)
        dict_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        map_def = items[2]
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, map_def)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_null(self, items):
        # items: [DICT_token, ID_token, NULL_token]  ("?" filtered)
        dict_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        null_token = items[2]
        id_ls = self._locatable(id_token)
        none_val = self._make_none(self._loc(null_token), getattr(null_token, "pos_in_stream", 0) or 0)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, none_val)
        self._attach_from_string(result, id_ls)
        return result

    def attr_dict_err(self, items):
        # items: [DICT_token, (opt "?" token), CID_token, ...]
        # Find CID token - it's the first CID token in items
        for t in items:
            if isinstance(t, Token) and t.type == "CID":
                cid_ls = self._locatable(t)
                raise ParserException(
                    cid_ls.location,
                    str(cid_ls),
                    "Invalid identifier: attribute names must start with a lower case character",
                )
        raise ParserException(Location(self.file, 1), "?", "Invalid dict attribute")

    # ---- Implement ----

    @v_args(meta=True)
    def implement_def_simple(self, meta, items):
        # items: [IMPLEMENT_token, class_ref, USING_token, implement_ns_list_result]
        impl_token = items[0]
        class_ref = items[1]
        ns_list = items[3]
        inherit, implementations = ns_list
        when = Literal(True)
        result = DefineImplement(class_ref, implementations, when, inherit=inherit, comment=None)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        result.copy_location(when)
        return result

    @v_args(meta=True)
    def implement_def_comment(self, meta, items):
        # items: [IMPLEMENT_token, class_ref, USING_token, implement_ns_list_result, MLS_token]
        impl_token = items[0]
        class_ref = items[1]
        ns_list = items[3]
        mls_token = items[4]
        inherit, implementations = ns_list
        comment = str(self._process_mls(mls_token))
        when = Literal(True)
        result = DefineImplement(class_ref, implementations, when, inherit=inherit, comment=comment)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        result.copy_location(when)
        return result

    @v_args(meta=True)
    def implement_def_when(self, meta, items):
        # items: [IMPLEMENT_token, class_ref, USING_token, impl_ns_list, WHEN_token, expression]
        impl_token = items[0]
        class_ref = items[1]
        ns_list = items[3]
        expression = items[5]
        inherit, implementations = ns_list
        result = DefineImplement(class_ref, implementations, expression, inherit=inherit, comment=None)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def implement_def_when_comment(self, meta, items):
        # items: [IMPLEMENT_token, class_ref, USING_token, impl_ns_list, WHEN_token, expression, MLS_token]
        impl_token = items[0]
        class_ref = items[1]
        ns_list = items[3]
        expression = items[5]
        mls_token = items[6]
        inherit, implementations = ns_list
        comment = str(self._process_mls(mls_token))
        result = DefineImplement(class_ref, implementations, expression, inherit=inherit, comment=comment)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        return result

    def implement_ns_list(self, items):
        # items: list of _ImplementNsItem
        has_parents = any(item.inherit_parents for item in items)
        ns_refs = [item.ns_ref for item in items if not item.inherit_parents and item.ns_ref is not None]
        return (has_parents, ns_refs)

    def impl_ns_ref(self, items):
        # items: [ns_ref_result]
        return _ImplementNsItem(inherit_parents=False, ns_ref=items[0])

    def impl_parents(self, items):
        # items: [PARENTS_token]
        return _ImplementNsItem(inherit_parents=True, ns_ref=None)

    # ---- Implementation definition ----

    def impl_header_plain(self, items):
        # No MLS doc comment: return None
        return None

    def impl_header_doc(self, items):
        # items: [MLS_token]
        return self._process_mls(items[0])

    @v_args(meta=True)
    def implementation_def(self, meta, items):
        # Grammar: IMPLEMENTATION ID FOR class_ref ":" impl_header stmt_list END
        # items: [IMPLEMENTATION_token, ID_token, FOR_token, class_ref, impl_header_result, stmt_list_result, END_token]
        impl_token = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        class_ref = items[3]
        docstr = items[4]   # None or LocatableString from impl_header
        stmts = items[5]
        id_ls = self._locatable(id_token)
        result = DefineImplementation(self.namespace, id_ls, class_ref, BasicBlock(self.namespace, stmts), docstr)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        return result

    # ---- Relations ----

    def relation_no_comment(self, items):
        return items[0]

    def relation_comment(self, items):
        # items: [relation_def_result, MLS_token]
        rel = items[0]
        rel.comment = str(self._process_mls(items[1]))
        return rel

    @v_args(meta=True)
    def relation_bidir(self, meta, items):
        # items: [class_ref, "."(filtered), ID_token, multi, REL_token, class_ref2, "."(filtered), ID_token2, multi2]
        # "." is anonymous => filtered
        # items: [class_ref, ID_token, multi, REL_token, class_ref2, ID_token2, multi2]
        left_class = items[0]
        self._validate_id(items[1])
        left_attr = self._locatable(items[1])
        left_multi = items[2]
        rel_token = items[3]
        right_class = items[4]
        self._validate_id(items[5])
        right_attr = self._locatable(items[5])
        right_multi = items[6]
        result = DefineRelation((left_class, right_attr, right_multi), (right_class, left_attr, left_multi))
        self._attach(result, self._loc(rel_token), getattr(rel_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def relation_unidir(self, meta, items):
        # items: [class_ref, ID_token, multi, REL_token, class_ref2]
        left_class = items[0]
        self._validate_id(items[1])
        left_attr = self._locatable(items[1])
        left_multi = items[2]
        rel_token = items[3]
        right_class = items[4]
        result = DefineRelation((left_class, None, None), (right_class, left_attr, left_multi))
        self._attach(result, self._loc(rel_token), getattr(rel_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def relation_annotated_bidir(self, meta, items):
        # items: [class_ref, ID_token, multi, annotation_list, class_ref2, ID_token2, multi2]
        left_class = items[0]
        self._validate_id(items[1])
        left_attr = self._locatable(items[1])
        left_multi = items[2]
        annotations = items[3]
        right_class = items[4]
        self._validate_id(items[5])
        right_attr = self._locatable(items[5])
        right_multi = items[6]
        result = DefineRelation((left_class, right_attr, right_multi), (right_class, left_attr, left_multi), annotations)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def relation_annotated_unidir(self, meta, items):
        # items: [class_ref, ID_token, multi, annotation_list, class_ref2]
        left_class = items[0]
        self._validate_id(items[1])
        left_attr = self._locatable(items[1])
        left_multi = items[2]
        annotations = items[3]
        right_class = items[4]
        result = DefineRelation((left_class, None, None), (right_class, left_attr, left_multi), annotations)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def annotation_list(self, items):
        return list(items)

    def multi_exact(self, items):
        # items: [INT_token]
        n = int(items[0])
        return (n, n)

    def multi_lower_bound(self, items):
        # items: [INT_token]  (":" filtered)
        n = int(items[0])
        return (n, None)

    def multi_range(self, items):
        # items: [INT_token, INT_token]  (":" filtered)
        n = int(items[0])
        m = int(items[1])
        return (n, m)

    def multi_upper_bound(self, items):
        # items: [INT_token]  (":" filtered)
        n = int(items[0])
        return (0, n)

    # ---- Typedef ----

    def typedef_no_comment(self, items):
        return items[0]

    def typedef_comment(self, items):
        # items: [typedef_inner_result, MLS_token]
        tdef = items[0]
        tdef.comment = str(self._process_mls(items[1]))
        return tdef

    @v_args(meta=True)
    def typedef_matching(self, meta, items):
        # items: [TYPEDEF_token, ID_token, AS_token, ns_ref, MATCHING_token, expression]
        id_token = items[1]
        self._validate_id(id_token)
        ns_ref = items[3]
        expression = items[5]
        id_ls = self._locatable(id_token)
        result = DefineTypeConstraint(self.namespace, id_ls, ns_ref, expression)
        self._attach_from_string(result, id_ls)
        return result

    @v_args(meta=True)
    def typedef_regex(self, meta, items):
        # items: [TYPEDEF_token, ID_token, AS_token, ns_ref, REGEX_token]
        id_token = items[1]
        self._validate_id(id_token)
        ns_ref = items[3]
        regex_token = items[4]
        id_ls = self._locatable(id_token)
        # Process the REGEX token into a Regex expression
        regex_expr = self._process_regex_token(regex_token)
        result = DefineTypeConstraint(self.namespace, id_ls, ns_ref, regex_expr)
        self._attach_from_string(result, id_ls)
        return result

    def typedef_cls_err(self, items):
        # items: [TYPEDEF_token, CID_token, AS_token, constructor]
        cid_token = items[1]
        cid_ls = self._locatable(cid_token)
        raise ParserException(cid_ls.location, str(cid_ls), "The use of default constructors is no longer supported")

    def _process_regex_token(self, token: Token):
        """Process a REGEX token (matching /.../) into a Regex expression."""
        from inmanta.ast.constraint.expression import Regex
        from inmanta.ast.variables import Reference

        raw = str(token)
        # Find first slash
        idx = raw.index("/")
        part_before = raw[:idx]
        regex_with_slashes = raw[idx:]
        regex_str = regex_with_slashes[1:-1]
        value = Reference("self")  # anonymous value
        try:
            expr = Regex(value, regex_str)
            return expr
        except RegexError as error:
            end_col = token.column + len(raw)
            start_col = token.column + idx
            r = Range(self.file, token.line, start_col, token.line, end_col)
            raise ParserException(r, regex_with_slashes, f"Regex error in {regex_with_slashes}: '{error}'")

    # ---- Index ----

    @v_args(meta=True)
    def index(self, meta, items):
        # items: [INDEX_token, class_ref, id_list_result]
        index_token = items[0]
        class_ref = items[1]
        id_list = items[2]
        result = DefineIndex(class_ref, id_list)
        self._attach(result, self._loc(index_token), getattr(index_token, "pos_in_stream", 0) or 0)
        return result

    def id_list(self, items):
        # items: [ID_token, ...]  (commas filtered)
        result = []
        for t in items:
            if isinstance(t, Token):
                self._validate_id(t)
                result.append(self._locatable(t))
        return result

    # ---- Expressions ----

    @v_args(meta=True)
    def ternary_expr(self, meta, items):
        # items: [condition, "?"(filtered), true_expr, ":"(filtered), false_expr]
        # Actually: [or_expr_result, expression_result, ternary_expr_result]
        cond = items[0]
        true_val = items[1]
        false_val = items[2]
        result = ConditionalExpression(cond, true_val, false_val)
        if hasattr(cond, "location"):
            self._attach_from_string(result, cond) if isinstance(cond, LocatableString) else None
            if hasattr(cond, "location"):
                result.location = cond.location
                result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def or_expr(self, meta, items):
        # items: [left, OR_token, right]
        left, op_token, right = items
        operator = Operator.get_operator_class("or")
        result = operator(left, right)
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def and_expr(self, meta, items):
        # items: [left, AND_token, right]
        left, op_token, right = items
        operator = Operator.get_operator_class("and")
        result = operator(left, right)
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def not_expr(self, meta, items):
        # items: [NOT_token, expr]
        not_token, expr = items
        result = Not(expr)
        self._attach(result, self._loc(not_token), getattr(not_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def is_defined_attr(self, meta, items):
        # items: [attr_ref_result, IS_token, DEFINED_token]
        attr_ref = items[0]
        is_token = items[1]
        result = IsDefined(attr_ref.instance, attr_ref.attribute)
        self._attach(result, self._loc(is_token), getattr(is_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def is_defined_id(self, meta, items):
        # items: [ID_token, IS_token, DEFINED_token]
        id_token = items[0]
        is_token = items[1]
        id_ls = self._locatable(id_token)
        result = IsDefined(None, id_ls)
        self._attach(result, self._loc(is_token), getattr(is_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def is_defined_map(self, meta, items):
        # items: [map_lookup_result, IS_token, DEFINED_token]
        # syntactic sugar: expands to (key in dict) and (dict[key] != null) and (dict[key] != [])
        map_lk = items[0]
        is_token = items[1]
        location = self._loc(is_token)
        lexpos = getattr(is_token, "pos_in_stream", 0) or 0

        def attach(inp):
            inp.location = location
            inp.namespace = self.namespace
            inp.lexpos = lexpos
            return inp

        key_in_dict = attach(In(map_lk.key, map_lk.themap))
        not_none = attach(NotEqual(map_lk, attach(Literal(NoneValue()))))
        not_empty_list = attach(NotEqual(map_lk, attach(CreateList(list()))))
        out = attach(And(attach(And(key_in_dict, not_none)), not_empty_list))
        return out

    @v_args(meta=True)
    def cmp_expr(self, meta, items):
        # items: [left, CMP_OP_token, right]
        left, op_token, right = items
        operator = Operator.get_operator_class(str(op_token))
        if operator is None:
            raise ParserException(
                left.location if hasattr(left, "location") else self._meta_range(meta),
                str(op_token),
                f"Invalid operator {str(op_token)}",
            )
        result = operator(left, right)
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def in_expr(self, meta, items):
        # items: [left, IN_token, right]
        left, op_token, right = items
        operator = Operator.get_operator_class("in")
        result = operator(left, right)
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def not_in_expr(self, meta, items):
        # items: [left, NOT_token, IN_token, right]
        left, not_token, in_token, right = items
        result = Not(In(left, right))
        self._attach(result, self._loc(not_token), getattr(not_token, "pos_in_stream", 0) or 0)
        return result

    def _binary_op(self, items, op_str: str):
        left, op_token, right = items
        operator = Operator.get_operator_class(op_str)
        if operator is None:
            raise ParserException(
                self._range(op_token), str(op_token), f"Invalid operator {op_str}"
            )
        result = operator(left, right)
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def add_expr(self, meta, items):
        return self._binary_op(items, "+")

    @v_args(meta=True)
    def sub_expr(self, meta, items):
        return self._binary_op(items, "-")

    @v_args(meta=True)
    def mul_expr(self, meta, items):
        return self._binary_op(items, "*")

    @v_args(meta=True)
    def div_expr(self, meta, items):
        return self._binary_op(items, "/")

    @v_args(meta=True)
    def mod_expr(self, meta, items):
        return self._binary_op(items, "%")

    @v_args(meta=True)
    def pow_expr(self, meta, items):
        return self._binary_op(items, "**")

    def paren_expr(self, items):
        # items: [expression_result]  ("(" and ")" are anonymous => filtered)
        return items[0]

    # ---- Map lookup ----

    @v_args(meta=True)
    def map_lookup(self, meta, items):
        # items: [var_ref_or_map_lookup, operand]  ("[" and "]" filtered)
        themap = items[0]
        key = items[1]
        result = MapLookup(themap, key)
        return result

    # ---- Constructors and function calls ----

    @v_args(meta=True)
    def constructor(self, meta, items):
        # items: [class_ref, param_list_result]  ("(" and ")" filtered)
        class_ref = items[0]
        params = items[1]  # list of _ParamListElement
        kwargs = [(e.key, e.value) for e in params if e.key is not None]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = Constructor(class_ref, kwargs, wrapped, self._meta_loc(meta), self.namespace)
        return result

    @v_args(meta=True)
    def function_call(self, meta, items):
        # items: [ns_ref_result, function_param_list_result]
        ns_ref = items[0]
        fparams = items[1]  # list of _FunctionParamElement
        args = [e.arg for e in fparams if e.arg is not None]
        kwargs = [(e.key, e.value) for e in fparams if e.key is not None]
        wrapped = [e.wrapped_kwargs for e in fparams if e.wrapped_kwargs is not None]
        result = FunctionCall(ns_ref, args, kwargs, wrapped, self.namespace)
        return result

    def function_call_err_dot(self, items):
        # items: [attr_ref_result, function_param_list_result]
        attr_ref = items[0]
        raise InvalidNamespaceAccess(attr_ref.locatable_name)

    # ---- Index lookup ----

    @v_args(meta=True)
    def index_lookup_class(self, meta, items):
        # items: [class_ref, param_list_result]
        class_ref = items[0]
        params = items[1]
        kwargs = [(e.key, e.value) for e in params if e.key is not None]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = IndexLookup(class_ref, kwargs, wrapped)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def index_lookup_attr(self, meta, items):
        # items: [attr_ref_result, param_list_result]
        attr_ref = items[0]
        params = items[1]
        kwargs = [(e.key, e.value) for e in params if e.key is not None]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = ShortIndexLookup(attr_ref.instance, attr_ref.attribute, kwargs, wrapped)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    # ---- Lists ----

    @v_args(meta=True)
    def list_def(self, meta, items):
        # items: [operand_list_result]  ("[" and "]" filtered)
        operands = items[0]
        node = CreateList(operands)
        try:
            node = Literal(node.as_constant())
        except RuntimeException:
            pass
        node.location = self._meta_loc(meta)
        node.namespace = self.namespace
        node.lexpos = meta.column if hasattr(meta, "column") else 0
        return node

    @v_args(meta=True)
    def list_comprehension(self, meta, items):
        # items: [value_expr, for_clause1, ..., guard_clause1, ...]
        # The grammar ensures for_clauses come before guard_clauses
        value_expr = items[0]
        for_clauses = [item for item in items[1:] if isinstance(item, _ForClause)]
        guard_clauses = [item.condition for item in items[1:] if isinstance(item, _GuardClause)]

        # Combine guard clauses with AND
        combined_guard: Optional[ExpressionStatement] = None
        for g in guard_clauses:
            if combined_guard is None:
                combined_guard = g
            else:
                and_node = And(combined_guard, g)
                and_node.location = g.location if hasattr(g, "location") else self._meta_loc(meta)
                and_node.namespace = self.namespace
                combined_guard = and_node

        # PLY collects for_clauses in reverse (innermost first) and then uses functools.reduce
        # Our for_clauses are in order (outermost first), so we reverse them
        reversed_clauses = list(reversed(for_clauses))
        # Set guard on the innermost (first in reversed list)
        if reversed_clauses:
            reversed_clauses[0].guard = combined_guard

        def create_list_comprehension(value: ExpressionStatement, clause: _ForClause) -> ListComprehension:
            result = ListComprehension(value, clause.variable, clause.iterable, clause.guard)
            result.location = self._meta_loc(meta)
            result.namespace = self.namespace
            result.lexpos = 0
            return result

        result = functools.reduce(
            lambda acc, clause: create_list_comprehension(value=acc, clause=clause),
            reversed_clauses,
            value_expr,
        )
        return result

    @v_args(meta=True)
    def for_clause(self, meta, items):
        # items: [FOR_token, ID_token, IN_token, expression]
        id_token = items[1]
        self._validate_id(id_token)
        expression = items[3]
        id_ls = self._locatable(id_token)
        return _ForClause(variable=id_ls, iterable=expression)

    @v_args(meta=True)
    def guard_clause(self, meta, items):
        # items: [IF_token, expression]
        return _GuardClause(condition=items[1])

    def operand_list(self, items):
        return list(items)

    # ---- Map def ----

    @v_args(meta=True)
    def map_def(self, meta, items):
        # items: [pair_list_result]  ("{" and "}" filtered)
        pairs = items[0]
        node = CreateDict(pairs)
        try:
            node = Literal({k: v.as_constant() for k, v in pairs})
        except RuntimeException:
            pass
        node.location = self._meta_loc(meta)
        node.namespace = self.namespace
        return node

    def pair_list(self, items):
        # items: list of pair_item results (each is (key, value) tuple)
        return [item for item in items if isinstance(item, tuple)]

    def pair_item(self, items):
        # items: [dict_key_result, operand_result]  (":" filtered)
        key = items[0]
        value = items[1]
        return (key, value)

    def dict_key_string(self, items):
        # items: [STRING_token]
        token = items[0]
        raw = str(token)
        # Strip quotes and decode
        content = raw[1:-1]
        loc = Location(self.file, token.line)
        decoded = _safe_decode(content, "Invalid escape sequence in string.", loc)
        # Check for format strings in dict keys
        match_obj = _format_regex_compiled.findall(decoded)
        if len(match_obj) != 0:
            ls = self._locatable(token)
            ls = LocatableString(decoded, ls.location, ls.lexpos, ls.namespace)
            raise ParserException(
                ls.location,
                decoded,
                "String interpolation is not supported in dictionary keys. "
                "Use raw string to use a key containing double curly brackets",
            )
        return decoded

    def dict_key_rstring(self, items):
        # items: [RSTRING_token]
        token = items[0]
        raw = str(token)
        # Strip r" prefix and " suffix
        content = raw[2:-1]
        return content

    # ---- Param lists ----

    def param_list(self, items):
        return [item for item in items if isinstance(item, _ParamListElement)]

    def param_explicit(self, items):
        # items: [ID_token, operand_result]  ("=" filtered)
        id_token = items[0]
        self._validate_id(id_token)
        value = items[1]
        id_ls = self._locatable(id_token)
        return _ParamListElement(key=id_ls, value=value)

    def param_wrapped_kwargs(self, items):
        # items: [DOUBLE_STAR_token, operand_result]
        ds_token = items[0]
        value = items[1]
        wk = WrappedKwargs(value)
        self._attach(wk, self._loc(ds_token), getattr(ds_token, "pos_in_stream", 0) or 0)
        return _ParamListElement(key=None, value=None, wrapped_kwargs=wk)

    def function_param_list(self, items):
        return [item for item in items if isinstance(item, _FunctionParamElement)]

    def func_arg(self, items):
        # items: [operand_result]
        return _FunctionParamElement(arg=items[0])

    def func_kwarg(self, items):
        # items: [ID_token, operand_result]  ("=" filtered)
        id_token = items[0]
        self._validate_id(id_token)
        value = items[1]
        id_ls = self._locatable(id_token)
        return _FunctionParamElement(key=id_ls, value=value)

    def func_wrapped_kwargs(self, items):
        # items: [DOUBLE_STAR_token, operand_result]
        ds_token = items[0]
        value = items[1]
        wk = WrappedKwargs(value)
        self._attach(wk, self._loc(ds_token), getattr(ds_token, "pos_in_stream", 0) or 0)
        return _FunctionParamElement(wrapped_kwargs=wk)

    # ---- Variable and attribute references ----

    def var_ref_ns(self, items):
        # items: [ns_ref_result]
        ns = items[0]
        result = Reference(ns)
        self._attach_from_string(result, ns)
        return result

    @v_args(meta=True)
    def attr_ref(self, meta, items):
        # items: [var_ref_result, ID_token]  ("." filtered)
        var_ref = items[0]
        id_token = items[1]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = AttributeReference(var_ref, id_ls)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    # ---- Namespace and class references ----

    def ns_ref_id(self, items):
        # items: [ID_token]
        self._validate_id(items[0])
        return self._locatable(items[0])

    def ns_ref_sep(self, items):
        # items: [ns_ref_result, SEP_token, ID_token]
        left = items[0]
        sep_token = items[1]
        id_token = items[2]
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        merged_value = f"{str(left)}::{str(id_ls)}"
        if isinstance(left, LocatableString):
            r = self._expand_range(left.location, id_ls.location)
        else:
            r = id_ls.location
        return LocatableString(merged_value, r, id_ls.lexpos, self.namespace)

    def class_ref_cid(self, items):
        # items: [CID_token]
        return self._locatable(items[0])

    def class_ref_ns(self, items):
        # items: [ns_ref_result, SEP_token, CID_token]
        left = items[0]
        sep_token = items[1]
        cid_token = items[2]
        cid_ls = self._locatable(cid_token)
        merged_value = f"{str(left)}::{str(cid_ls)}"
        if isinstance(left, LocatableString):
            r = self._expand_range(left.location, cid_ls.location)
        else:
            r = cid_ls.location
        return LocatableString(merged_value, r, cid_ls.lexpos, self.namespace)

    def class_ref_err_dot(self, items):
        # items: [var_ref_result, CID_token]
        var_ref = items[0]
        cid_token = items[1]
        cid_ls = self._locatable(cid_token)

        if isinstance(var_ref, LocatableString):
            var_str = var_ref
        elif isinstance(var_ref, Reference):
            var_str = var_ref.locatable_name
        else:
            var_str = cid_ls

        full_string = LocatableString(
            f"{var_str}.{cid_ls}",
            self._expand_range(var_str.location, cid_ls.location),
            var_str.lexpos,
            self.namespace,
        )
        raise InvalidNamespaceAccess(full_string)

    def class_ref_list(self, items):
        return list(items)

    # ---- Constants ----

    @v_args(meta=True)
    def const_int(self, meta, items):
        # items: [INT_token]
        token = items[0]
        result = Literal(int(str(token)))
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def const_float(self, meta, items):
        # items: [FLOAT_token]
        token = items[0]
        result = Literal(float(str(token)))
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def const_null(self, meta, items):
        # items: [NULL_token]
        token = items[0]
        return self._make_none(self._loc(token), getattr(token, "pos_in_stream", 0) or 0)

    @v_args(meta=True)
    def const_regex(self, meta, items):
        # items: [REGEX_token]
        token = items[0]
        expr = self._process_regex_token(token)
        expr.location = self._loc(token)
        expr.namespace = self.namespace
        return expr

    @v_args(meta=True)
    def const_true(self, meta, items):
        # items: [TRUE_token]
        token = items[0]
        result = Literal(True)
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def const_false(self, meta, items):
        # items: [FALSE_token]
        token = items[0]
        result = Literal(False)
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True)
    def const_string(self, meta, items):
        # items: [STRING_token]
        token = items[0]
        raw = str(token)
        content = raw[1:-1]
        loc = Location(self.file, token.line)
        decoded = _safe_decode(content, "Invalid escape sequence in string.", loc)
        ls = LocatableString(decoded, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = _get_string_ast_node(ls, False)
        result.location = self._loc(token)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def const_fstring(self, meta, items):
        # items: [FSTRING_token]
        token = items[0]
        raw = str(token)
        # Strip f" prefix and " suffix
        content = raw[2:-1]
        loc = Location(self.file, token.line)
        decoded = _safe_decode(content, "Invalid escape sequence in f-string.", loc)
        ls = LocatableString(decoded, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = _process_fstring(ls)
        result.location = self._range(token)  # mirrors PLY's attach_from_string (copies Range with column info)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def const_rstring(self, meta, items):
        # items: [RSTRING_token]
        token = items[0]
        raw = str(token)
        content = raw[2:-1]
        ls = LocatableString(content, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = Literal(str(ls))
        self._attach_from_string(result, ls)
        return result

    @v_args(meta=True)
    def const_mls(self, meta, items):
        # items: [MLS_token]
        token = items[0]
        ls = self._process_mls(token)
        result = _get_string_ast_node(ls, True)
        result.location = self._range(token)  # mirrors PLY's attach_from_string (copies Range with column info)
        result.namespace = self.namespace
        return result

    @v_args(meta=True)
    def const_neg_int(self, meta, items):
        # items: [MINUS_OP_token, INT_token]
        int_token = items[1]
        result = Literal(-int(str(int_token)))
        self._attach(result, self._meta_loc(meta), 0)
        return result

    @v_args(meta=True)
    def const_neg_float(self, meta, items):
        # items: [MINUS_OP_token, FLOAT_token]
        float_token = items[1]
        result = Literal(-float(str(float_token)))
        self._attach(result, self._meta_loc(meta), 0)
        return result

    @v_args(meta=True)
    def constant_list(self, meta, items):
        # items: [constants_result]  ("[" and "]" filtered)
        consts = items[0]
        result = CreateList(consts)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def constants(self, items):
        return list(items)


# ---- String processing helpers (mirrors PLY parser) ----


def _get_string_ast_node(string_ast: LocatableString, mls: bool) -> Union[Literal, StringFormat]:
    """Process a string for interpolation (mirrors PLY's get_string_ast_node)."""
    matches: list[re.Match] = list(_format_regex_compiled.finditer(str(string_ast)))
    if len(matches) == 0:
        return Literal(str(string_ast))

    start_lnr = string_ast.location.lnr
    start_char_pos = string_ast.location.start_char
    whole_string = str(string_ast)
    mls_offset: int = 3 if mls else 1

    def char_count_to_lnr_char(position: int):
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

    return StringFormat(str(string_ast), _convert_to_references(locatable_matches, string_ast.namespace))


def _process_fstring(string_ast: LocatableString) -> Union[StringFormatV2, Literal]:
    """Process an f-string for interpolation (mirrors PLY's p_constant_fstring)."""
    formatter = string.Formatter()
    try:
        parsed = list(formatter.parse(str(string_ast)))
    except ValueError as e:
        raise ParserException(string_ast.location, str(string_ast), f"Invalid f-string: {e}")

    start_lnr = string_ast.location.lnr
    start_char_pos = string_ast.location.start_char + 2  # f" or f' prefix

    locatable_matches: list[tuple[str, LocatableString]] = []

    def locate_match(match, scp: int, end_char: int) -> None:
        assert match[1]
        r: Range = Range(string_ast.location.file, start_lnr, scp, start_lnr, end_char)
        locatable_string = LocatableString(match[1], r, string_ast.lexpos, string_ast.namespace)
        locatable_matches.append((match[1], locatable_string))

    cur_pos = start_char_pos
    for match in parsed:
        if not match[1]:
            break
        lit_len = len(match[0])
        field_len = len(match[1])
        brack_len = 1 if field_len else 0
        cur_pos += lit_len + brack_len
        end_char = cur_pos + field_len
        locate_match(match, cur_pos, end_char)
        cur_pos += field_len

        if match[2]:
            cur_pos += 1
            sub_parsed = formatter.parse(match[2])
            for submatch in sub_parsed:
                if not submatch[1]:
                    break
                slit_len = len(submatch[0])
                sfield_len = len(submatch[1])
                sbrack_len = 1 if sfield_len else 0
                cur_pos += slit_len + sbrack_len
                end_char = cur_pos + sfield_len
                locate_match(submatch, cur_pos, end_char)
                cur_pos += sfield_len + sbrack_len

        cur_pos += brack_len

    return StringFormatV2(str(string_ast), _convert_to_references(locatable_matches, string_ast.namespace))


def _convert_to_references(
    variables: list[tuple[str, LocatableString]], namespace: Namespace
) -> list[tuple["Reference", str]]:
    """Convert variable name strings to References (mirrors PLY's convert_to_references)."""

    def normalize(variable: str, locatable: LocatableString, offset: int = 0) -> LocatableString:
        start_char = locatable.location.start_char + offset
        end_char = start_char + len(variable)
        var_left_trim = variable.lstrip()
        left_spaces = len(variable) - len(var_left_trim)
        var_full_trim = var_left_trim.rstrip()
        right_spaces = len(var_left_trim) - len(var_full_trim)
        r: Range = Range(
            locatable.location.file,
            locatable.location.lnr,
            start_char + left_spaces,
            locatable.location.lnr,
            end_char - right_spaces,
        )
        return LocatableString(var_full_trim, r, locatable.lexpos, locatable.namespace)

    _vars: list[tuple[Reference, str]] = []
    for match, var in variables:
        var_name: str = str(var)
        var_parts: list[str] = var_name.split(".")
        ref_ls: LocatableString = normalize(var_parts[0], var)
        ref = Reference(ref_ls)
        ref.location = ref_ls.location
        ref.namespace = namespace
        if len(var_parts) > 1:
            offset = len(var_parts[0]) + 1
            for attr in var_parts[1:]:
                attr_ls: LocatableString = normalize(attr, var, offset=offset)
                ref = AttributeReference(ref, attr_ls)
                ref.location = attr_ls.location
                ref.namespace = namespace
                offset += len(attr) + 1
        _vars.append((ref, match))
    return _vars


# ---- Error handling ----


def _convert_lark_error(e: UnexpectedInput, tfile: str) -> ParserException:
    """Convert a Lark parse error to a ParserException."""
    line = getattr(e, "line", 1) or 1
    col = getattr(e, "column", 1) or 1
    r = Range(tfile, line, col, line, col + 1)

    if isinstance(e, UnexpectedEOF):
        return ParserException(r, None, "Unexpected end of file")

    if isinstance(e, UnexpectedCharacters):
        char = getattr(e, "char", "?")
        return ParserException(r, char, f"Illegal character '{char}'")

    if isinstance(e, UnexpectedToken):
        token = getattr(e, "token", None)
        if token is not None:
            token_str = str(token)
            # Check if it's a reserved keyword used as identifier
            from inmanta.parser.plyInmantaLex import reserved

            if token.type in reserved.values() or token.type in [k.upper() for k in reserved]:
                return ParserException(r, token_str, f"invalid identifier, {token_str} is a reserved keyword")
            return ParserException(r, token_str)
        return ParserException(r, None, "Unexpected token")

    return ParserException(r, str(e), f"Parse error: {e}")


# ---- Parse entry point ----


def base_parse(ns: Namespace, tfile: str, content: Optional[str]) -> list[Statement]:
    """Parse Inmanta DSL content and return a list of AST statements."""
    if content is None:
        with open(tfile, encoding="utf-8") as f:
            data = f.read()
    else:
        data = content

    if len(data) == 0:
        return []

    # Add trailing newline to prevent issues with EOF
    data = data + "\n"

    try:
        tree = _lark_parser.parse(data)
    except UnexpectedInput as e:
        raise _convert_lark_error(e, tfile) from e
    except Exception as e:
        r = Range(tfile, 1, 1, 1, 1)
        raise ParserException(r, str(e), f"Parse error: {e}") from e

    transformer = InmantaTransformer(tfile, ns)
    try:
        result = transformer.transform(tree)
    except ParserException:
        raise
    except VisitError as e:
        # Lark wraps exceptions from transformer methods in VisitError.
        # Always unwrap to propagate the original exception unchanged.
        raise e.orig_exc from e
    except Exception as e:
        r = Range(tfile, 1, 1, 1, 1)
        raise ParserException(r, str(e), f"Transform error: {e}") from e

    if result is None:
        return []
    return result


_cache_manager = CacheManager()

# Public alias expected by module.py
cache_manager = _cache_manager


def parse(namespace: Namespace, filename: str, content: Optional[str] = None) -> list[Statement]:
    """Parse an Inmanta file, using cache if available."""
    statements = _cache_manager.un_cache(namespace, filename)
    if statements is not None:
        return statements
    statements = base_parse(namespace, filename, content)
    _cache_manager.cache(namespace, filename, statements)
    return statements
