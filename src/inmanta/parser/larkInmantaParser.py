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
import warnings
from dataclasses import dataclass
from re import error as RegexError
from typing import NoReturn, Optional, Union

from inmanta.ast import LocatableString, Location, Namespace, Range, RuntimeException
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.constraint.expression import And, In, IsDefined, Not, NotEqual, Operator
from inmanta.ast.statements import DynamicStatement, ExpressionStatement, Literal, Statement
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
from lark import Lark, Token, Transformer, UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, v_args
from lark.exceptions import UnexpectedToken, VisitError
from lark.tree import Meta

# ---- Grammar loading ----

_GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "larkInmanta.lark")

with open(_GRAMMAR_FILE, encoding="utf-8") as _f:
    _GRAMMAR = _f.read()

_lark_parser = Lark(
    _GRAMMAR,
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
    cache=True,
)


# ---- Format-string regex (same as PLY parser) ----

_format_regex = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
_format_regex_compiled = re.compile(_format_regex, re.MULTILINE | re.DOTALL)

# Set of reserved keywords – used to reject keywords used as identifiers.
# Lark's contextual lexer matches keywords as ID when ID is valid in the grammar,
# so we must validate at the transformer level.
_RESERVED_KEYWORDS: frozenset[str] = frozenset(
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


@v_args(inline=True)
class InmantaTransformer(Transformer[Token, list[Statement]]):
    """
    Transforms a Lark parse tree for the Inmanta DSL into the AST used by the compiler.

    This mirrors the p_* functions in the PLY-based parser.
    Each method corresponds to one grammar rule alias.

    The class-level @v_args(inline=True) decorator makes every rule callback receive
    its children as individual positional arguments (instead of a single list[object]).
    Methods that additionally need propagated position metadata use
    @v_args(meta=True, inline=True) which overrides the class-level decorator.
    """

    def __init__(self, tfile: str, namespace: Namespace) -> None:
        super().__init__()
        self.file = tfile
        self.namespace = namespace

    # ---- Position helpers ----

    def _loc(self, token: Token) -> Location:
        """Create a Location (file + line) from a Lark Token."""
        return Location(self.file, token.line or 1)

    def _range(self, token: Token) -> Range:
        """Create a Range from a Lark Token."""
        line = token.line or 1
        col = token.column or 1
        end_line = token.end_line if token.end_line is not None else line
        end_col = token.end_column if token.end_column is not None else (col + len(str(token)))
        return Range(self.file, line, col, end_line, end_col)

    def _locatable(self, token: Token) -> LocatableString:
        """Create a LocatableString from a Lark Token (ID, CID, or keyword token)."""
        return LocatableString(
            str(token),
            self._range(token),
            getattr(token, "pos_in_stream", 0) or 0,
            self.namespace,
        )

    def _meta_range(self, meta: Meta) -> Range:
        """Create a Range from a tree's meta (propagated positions)."""
        return Range(
            self.file,
            meta.line,
            meta.column,
            meta.end_line if meta.end_line is not None else meta.line,
            meta.end_column if meta.end_column is not None else meta.column,
        )

    def _meta_loc(self, meta: Meta) -> Location:
        return Location(self.file, meta.line)

    def _attach(self, node: object, location: Location, lexpos: int = 0) -> None:
        """Set location and namespace on an AST node (mirrors attach_lnr)."""
        node.location = location  # type: ignore[attr-defined]
        node.namespace = self.namespace  # type: ignore[attr-defined]
        node.lexpos = lexpos  # type: ignore[attr-defined]

    def _attach_from_string(self, node: object, ls: LocatableString) -> None:
        """Copy location and namespace from a LocatableString to a node (mirrors attach_from_string)."""
        node.location = ls.location  # type: ignore[attr-defined]
        node.namespace = ls.namespace  # type: ignore[attr-defined]

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

    def start(self, head: Optional[LocatableString], body: list[Statement]) -> list[Statement]:
        if head is not None:
            body.insert(0, head)  # type: ignore[arg-type]
        return body

    def head(self, *args: Token) -> Optional[LocatableString]:
        # Grammar: head: MLS?  →  0 or 1 items
        if not args:
            return None
        return self._locatable(args[0])

    def body(self, *stmts: Statement) -> list[Statement]:
        return list(stmts)

    # ---- Imports ----

    @v_args(meta=True, inline=True)
    def import_ns(self, meta: Meta, import_token: Token, ns_ref: LocatableString) -> DefineImport:
        result = DefineImport(ns_ref, ns_ref)
        self._attach(result, self._loc(import_token), getattr(import_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def import_as(self, meta: Meta, import_token: Token, ns_ref: LocatableString, _as: Token, id_token: Token) -> DefineImport:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineImport(ns_ref, id_ls)
        self._attach(result, self._loc(import_token), getattr(import_token, "pos_in_stream", 0) or 0)
        return result

    # ---- Statements ----

    def stmt_list(self, *stmts: Statement) -> list[Statement]:
        # PLY's right-recursive stmt_list rule builds statements in reverse order
        # (appends current statement at the end, so first stmt ends up last).
        # Mirror that behavior to preserve execution ordering semantics.
        return list(reversed(stmts))

    @v_args(meta=True, inline=True)
    def assign_eq(self, meta: Meta, var_ref: Reference, operand: ExpressionStatement) -> Statement:
        # "=" is anonymous => filtered; items = [var_ref, operand]
        result = var_ref.as_assign(operand)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def assign_plus_eq(self, meta: Meta, var_ref: Reference, peq_token: Token, operand: ExpressionStatement) -> Statement:
        result = var_ref.as_assign(operand, list_only=True)
        self._attach(result, self._loc(peq_token), getattr(peq_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def for_stmt(
        self,
        meta: Meta,
        for_token: Token,
        id_token: Token,
        _in: Token,
        operand: ExpressionStatement,
        stmts: list[Statement],
        _end: Token,
    ) -> For:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = For(operand, id_ls, BasicBlock(self.namespace, stmts))  # type: ignore[arg-type]
        self._attach(result, self._loc(for_token), getattr(for_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def if_stmt(self, meta: Meta, _if: Token, if_body: If, _end: Token) -> If:
        if_body.location = self._loc(_if)
        if_body.namespace = self.namespace
        return if_body

    @v_args(meta=True, inline=True)
    def if_body(
        self, meta: Meta, condition: ExpressionStatement, stmt_list: list[DynamicStatement], next_block: BasicBlock
    ) -> If:
        # ":" is anonymous => filtered
        result = If(condition, BasicBlock(self.namespace, stmt_list), next_block)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def if_next_empty(self) -> BasicBlock:
        return BasicBlock(self.namespace, [])

    def if_next_else(self, _else: Token, stmt_list: list[DynamicStatement]) -> BasicBlock:
        return BasicBlock(self.namespace, stmt_list)

    @v_args(meta=True, inline=True)
    def if_next_elif(self, meta: Meta, _elif: Token, if_body: If) -> BasicBlock:
        result = BasicBlock(self.namespace, [if_body])
        result.namespace = self.namespace
        return result

    # ---- Entity definitions ----

    @v_args(meta=True, inline=True)
    def entity_def(
        self,
        meta: Meta,
        entity_token: Token,
        cid_token: Token,
        body_outer: tuple[Optional[LocatableString], list[DefineAttribute]],
    ) -> DefineEntity:
        docstr, attrs = body_outer
        cid_ls = self._locatable(cid_token)
        result = DefineEntity(self.namespace, cid_ls, docstr, [], attrs)
        self._attach(result, self._loc(entity_token), getattr(entity_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def entity_def_extends(
        self,
        meta: Meta,
        entity_token: Token,
        cid_token: Token,
        _extends: Token,
        class_ref_list: list[LocatableString],
        body_outer: tuple[Optional[LocatableString], list[DefineAttribute]],
    ) -> DefineEntity:
        docstr, attrs = body_outer
        cid_ls = self._locatable(cid_token)
        result = DefineEntity(self.namespace, cid_ls, docstr, class_ref_list, attrs)
        self._attach(result, self._loc(entity_token), getattr(entity_token, "pos_in_stream", 0) or 0)
        return result

    def entity_def_err(self, *args: object) -> NoReturn:
        # Grammar: ENTITY ID ":" entity_body_outer  (multiple alternatives → *args)
        id_token = args[1]
        assert isinstance(id_token, Token)
        id_ls = self._locatable(id_token)
        raise ParserException(id_ls.location, str(id_ls), "Invalid identifier: Entity names must start with a capital")

    def entity_def_extends_err(self, *args: object) -> NoReturn:
        id_token = args[1]
        assert isinstance(id_token, Token)
        id_ls = self._locatable(id_token)
        raise ParserException(id_ls.location, str(id_ls), "Invalid identifier: Entity names must start with a capital")

    def entity_body_outer_mls(
        self, mls_token: Token, entity_body: list[DefineAttribute], _end: Token
    ) -> tuple[Optional[LocatableString], list[DefineAttribute]]:
        docstr = self._process_mls(mls_token)
        return (docstr, entity_body)

    def entity_body_outer_plain(self, entity_body: list[DefineAttribute], _end: Token) -> tuple[None, list[DefineAttribute]]:
        return (None, entity_body)

    def entity_body_outer_mls_only(
        self, mls_token: Token, _end: Token
    ) -> tuple[Optional[LocatableString], list[DefineAttribute]]:
        docstr = self._process_mls(mls_token)
        return (docstr, [])

    def entity_body_outer_empty(self, _end: Token) -> tuple[None, list[DefineAttribute]]:
        return (None, [])

    def entity_body(self, *attrs: DefineAttribute) -> list[DefineAttribute]:
        return list(attrs)

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
        line = token.line or 1
        col = token.column or 1
        loc = Location(self.file, line)
        decoded = _safe_decode(content, "Invalid escape sequence in multi-line string.", loc)
        # Calculate end position
        lines = raw.split("\n")
        end_line = line + len(lines) - 1
        end_col = len(lines[-1]) + 1
        r = Range(self.file, line, col, end_line, end_col)
        return LocatableString(decoded, r, getattr(token, "pos_in_stream", 0) or 0, self.namespace)

    # ---- Attributes ----

    def attr_base_type(self, ns_ref: LocatableString) -> TypeDeclaration:
        result = TypeDeclaration(ns_ref)
        self._attach_from_string(result, ns_ref)
        return result

    def attr_type_multi(self, base: TypeDeclaration) -> TypeDeclaration:
        # Grammar: attr_base_type "[" "]"  →  "[" and "]" filtered
        base.multi = True
        return base

    def attr_type_opt_multi(self, multi: TypeDeclaration) -> TypeDeclaration:
        # Grammar: attr_type_multi "?"  →  "?" filtered
        multi.nullable = True
        return multi

    def attr_type_opt_base(self, base: TypeDeclaration) -> TypeDeclaration:
        # Grammar: attr_base_type "?"  →  "?" filtered
        base.nullable = True
        return base

    def attr_simple(self, attr_type: TypeDeclaration, id_token: Token) -> DefineAttribute:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_cte(self, attr_type: TypeDeclaration, id_token: Token, constant: ExpressionStatement) -> DefineAttribute:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, constant)
        self._attach_from_string(result, id_ls)
        return result

    def attr_cte_list(self, attr_type: TypeDeclaration, id_token: Token, clist: ExpressionStatement) -> DefineAttribute:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, clist)
        self._attach_from_string(result, id_ls)
        return result

    def attr_undef(self, attr_type: TypeDeclaration, id_token: Token, _undef: Token) -> DefineAttribute:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(attr_type, id_ls, None, remove_default=True)
        self._attach_from_string(result, id_ls)
        return result

    def attr_err(self, *args: object) -> NoReturn:
        # Multiple alternatives use this alias (different arg counts)
        # Find CID token - it's always item at index 1
        cid_token = args[1]
        assert isinstance(cid_token, Token)
        cid_ls = self._locatable(cid_token)
        raise ParserException(
            cid_ls.location, str(cid_ls), "Invalid identifier: attribute names must start with a lower case character"
        )

    def _make_dict_type(self, dict_token: Token, nullable: bool = False) -> TypeDeclaration:
        """Create a TypeDeclaration for 'dict' from a DICT keyword token."""
        dict_ls = self._locatable(dict_token)
        return TypeDeclaration(dict_ls, nullable=nullable)

    def attr_dict(self, dict_token: Token, id_token: Token) -> DefineAttribute:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token), id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict(self, dict_token: Token, id_token: Token, map_def: ExpressionStatement) -> DefineAttribute:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token), id_ls, map_def)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_null_err(self, dict_token: Token, id_token: Token, null_token: Token) -> NoReturn:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        raise ParserException(
            id_ls.location, str(id_ls), 'null can not be assigned to dict, did you mean "dict? %s = null"' % id_ls
        )

    def attr_dict_nullable(self, dict_token: Token, id_token: Token) -> DefineAttribute:
        # "?" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, None)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_nullable(self, dict_token: Token, id_token: Token, map_def: ExpressionStatement) -> DefineAttribute:
        # "?" and "=" filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, map_def)
        self._attach_from_string(result, id_ls)
        return result

    def attr_list_dict_null(self, dict_token: Token, id_token: Token, null_token: Token) -> DefineAttribute:
        # "?" and "=" filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        none_val = self._make_none(self._loc(null_token), getattr(null_token, "pos_in_stream", 0) or 0)
        result = DefineAttribute(self._make_dict_type(dict_token, nullable=True), id_ls, none_val)
        self._attach_from_string(result, id_ls)
        return result

    def attr_dict_err(self, *args: object) -> NoReturn:
        # Multiple alternatives use this alias; find the CID token
        for t in args:
            if isinstance(t, Token) and t.type == "CID":
                cid_ls = self._locatable(t)
                raise ParserException(
                    cid_ls.location,
                    str(cid_ls),
                    "Invalid identifier: attribute names must start with a lower case character",
                )
        raise ParserException(Location(self.file, 1), "?", "Invalid dict attribute")

    # ---- Implement ----

    @v_args(meta=True, inline=True)
    def implement_def_simple(
        self,
        meta: Meta,
        impl_token: Token,
        class_ref: LocatableString,
        _using: Token,
        impl_ns_list: tuple[bool, list[LocatableString]],
    ) -> DefineImplement:
        inherit, implementations = impl_ns_list
        when = Literal(True)
        result = DefineImplement(class_ref, implementations, when, inherit=inherit, comment=None)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        result.copy_location(when)
        return result

    @v_args(meta=True, inline=True)
    def implement_def_comment(
        self,
        meta: Meta,
        impl_token: Token,
        class_ref: LocatableString,
        _using: Token,
        impl_ns_list: tuple[bool, list[LocatableString]],
        mls_token: Token,
    ) -> DefineImplement:
        inherit, implementations = impl_ns_list
        comment = self._process_mls(mls_token)
        when = Literal(True)
        result = DefineImplement(class_ref, implementations, when, inherit=inherit, comment=comment)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        result.copy_location(when)
        return result

    @v_args(meta=True, inline=True)
    def implement_def_when(
        self,
        meta: Meta,
        impl_token: Token,
        class_ref: LocatableString,
        _using: Token,
        impl_ns_list: tuple[bool, list[LocatableString]],
        _when: Token,
        expression: ExpressionStatement,
    ) -> DefineImplement:
        inherit, implementations = impl_ns_list
        result = DefineImplement(class_ref, implementations, expression, inherit=inherit, comment=None)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def implement_def_when_comment(
        self,
        meta: Meta,
        impl_token: Token,
        class_ref: LocatableString,
        _using: Token,
        impl_ns_list: tuple[bool, list[LocatableString]],
        _when: Token,
        expression: ExpressionStatement,
        mls_token: Token,
    ) -> DefineImplement:
        inherit, implementations = impl_ns_list
        comment = self._process_mls(mls_token)
        result = DefineImplement(class_ref, implementations, expression, inherit=inherit, comment=comment)
        self._attach(result, self._loc(impl_token), getattr(impl_token, "pos_in_stream", 0) or 0)
        return result

    def implement_ns_list(self, *items: _ImplementNsItem) -> tuple[bool, list[LocatableString]]:
        has_parents = any(item.inherit_parents for item in items)
        ns_refs = [item.ns_ref for item in items if not item.inherit_parents and item.ns_ref is not None]
        return (has_parents, ns_refs)

    def impl_ns_ref(self, ns_ref: LocatableString) -> _ImplementNsItem:
        return _ImplementNsItem(inherit_parents=False, ns_ref=ns_ref)

    def impl_parents(self, _parents: Token) -> _ImplementNsItem:
        return _ImplementNsItem(inherit_parents=True, ns_ref=None)

    # ---- Implementation definition ----

    def impl_header_plain(self) -> None:
        return None

    def impl_header_doc(self, mls_token: Token) -> LocatableString:
        return self._process_mls(mls_token)

    @v_args(meta=True, inline=True)
    def implementation_def(
        self,
        meta: Meta,
        impl_token: Token,
        id_token: Token,
        _for: Token,
        class_ref: LocatableString,
        docstr: Optional[LocatableString],
        stmts: list[DynamicStatement],
        _end: Token,
    ) -> DefineImplementation:
        # Grammar: IMPLEMENTATION ID FOR class_ref ":" impl_header stmt_list END
        # ":" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        block = BasicBlock(self.namespace, stmts)
        result = DefineImplementation(self.namespace, id_ls, class_ref, block, docstr)  # type: ignore[arg-type]
        # DefineImplementation.__init__ sets location from name.get_location() (a Range)
        # and namespace from TypeDefinitionStatement.__init__.
        # Do not call _attach here — it would overwrite the Range location with a bare Location.
        result.lexpos = getattr(impl_token, "pos_in_stream", 0) or 0
        return result

    # ---- Relations ----

    def relation_comment(self, relation_def: DefineRelation, mls_token: Token) -> DefineRelation:
        relation_def.comment = str(self._process_mls(mls_token))  # type: ignore[assignment]
        return relation_def

    @v_args(meta=True, inline=True)
    def relation_bidir(
        self,
        meta: Meta,
        left_class: LocatableString,
        left_id_token: Token,
        left_multi: tuple[int, Optional[int]],
        rel_token: Token,
        right_class: LocatableString,
        right_id_token: Token,
        right_multi: tuple[int, Optional[int]],
    ) -> DefineRelation:
        # "." is anonymous => filtered (two occurrences)
        self._validate_id(left_id_token)
        left_attr = self._locatable(left_id_token)
        self._validate_id(right_id_token)
        right_attr = self._locatable(right_id_token)
        result = DefineRelation((left_class, right_attr, right_multi), (right_class, left_attr, left_multi))
        self._attach(result, self._loc(rel_token), getattr(rel_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def relation_unidir(
        self,
        meta: Meta,
        left_class: LocatableString,
        left_id_token: Token,
        left_multi: tuple[int, Optional[int]],
        rel_token: Token,
        right_class: LocatableString,
    ) -> DefineRelation:
        # "." is anonymous => filtered
        self._validate_id(left_id_token)
        left_attr = self._locatable(left_id_token)
        result = DefineRelation((left_class, None, None), (right_class, left_attr, left_multi))
        self._attach(result, self._loc(rel_token), getattr(rel_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def relation_annotated_bidir(
        self,
        meta: Meta,
        left_class: LocatableString,
        left_id_token: Token,
        left_multi: tuple[int, Optional[int]],
        annotations: list[ExpressionStatement],
        right_class: LocatableString,
        right_id_token: Token,
        right_multi: tuple[int, Optional[int]],
    ) -> DefineRelation:
        # "." is anonymous => filtered (two occurrences)
        self._validate_id(left_id_token)
        left_attr = self._locatable(left_id_token)
        self._validate_id(right_id_token)
        right_attr = self._locatable(right_id_token)
        result = DefineRelation((left_class, right_attr, right_multi), (right_class, left_attr, left_multi), annotations)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def relation_annotated_unidir(
        self,
        meta: Meta,
        left_class: LocatableString,
        left_id_token: Token,
        left_multi: tuple[int, Optional[int]],
        annotations: list[ExpressionStatement],
        right_class: LocatableString,
    ) -> DefineRelation:
        # "." is anonymous => filtered
        self._validate_id(left_id_token)
        left_attr = self._locatable(left_id_token)
        result = DefineRelation((left_class, None, None), (right_class, left_attr, left_multi), annotations)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def annotation_list(self, *items: ExpressionStatement) -> list[ExpressionStatement]:
        return list(items)

    def multi_exact(self, int_token: Token) -> tuple[int, int]:
        # Grammar: "[" INT "]"  →  "[" and "]" filtered
        n = int(int_token)
        return (n, n)

    def multi_lower_bound(self, int_token: Token) -> tuple[int, Optional[int]]:
        # Grammar: "[" INT ":" "]"  →  "[", ":", "]" filtered
        n = int(int_token)
        return (n, None)

    def multi_range(self, int_token1: Token, int_token2: Token) -> tuple[int, int]:
        # Grammar: "[" INT ":" INT "]"  →  "[", ":", "]" filtered
        n = int(int_token1)
        m = int(int_token2)
        return (n, m)

    def multi_upper_bound(self, int_token: Token) -> tuple[int, int]:
        # Grammar: "[" ":" INT "]"  →  "[", ":", "]" filtered
        n = int(int_token)
        return (0, n)

    # ---- Typedef ----

    def typedef_comment(self, typedef_inner: DefineTypeConstraint, mls_token: Token) -> DefineTypeConstraint:
        typedef_inner.comment = str(self._process_mls(mls_token))
        return typedef_inner

    @v_args(meta=True, inline=True)
    def typedef_matching(
        self,
        meta: Meta,
        _typedef: Token,
        id_token: Token,
        _as: Token,
        ns_ref: LocatableString,
        _matching: Token,
        expression: ExpressionStatement,
    ) -> DefineTypeConstraint:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = DefineTypeConstraint(self.namespace, id_ls, ns_ref, expression)
        self._attach_from_string(result, id_ls)
        return result

    @v_args(meta=True, inline=True)
    def typedef_regex(
        self,
        meta: Meta,
        _typedef: Token,
        id_token: Token,
        _as: Token,
        ns_ref: LocatableString,
        regex_token: Token,
    ) -> DefineTypeConstraint:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        regex_expr = self._process_regex_token(regex_token)
        result = DefineTypeConstraint(self.namespace, id_ls, ns_ref, regex_expr)
        self._attach_from_string(result, id_ls)
        return result

    def typedef_cls_err(self, _typedef: Token, cid_token: Token, _as: Token, _constructor: object) -> NoReturn:
        cid_ls = self._locatable(cid_token)
        raise ParserException(cid_ls.location, str(cid_ls), "The use of default constructors is no longer supported")

    def _process_regex_token(self, token: Token) -> ExpressionStatement:
        """Process a REGEX token (matching /.../) into a Regex expression."""
        from inmanta.ast.constraint.expression import Regex

        raw = str(token)
        # Find first slash
        idx = raw.index("/")
        regex_with_slashes = raw[idx:]
        regex_str = regex_with_slashes[1:-1]
        value = Reference(LocatableString("self", self._range(token), 0, self.namespace))
        try:
            expr: ExpressionStatement = Regex(value, regex_str)
            return expr
        except RegexError as error:
            line = token.line or 1
            col = token.column or 1
            end_col = col + len(raw)
            start_col = col + idx
            r = Range(self.file, line, start_col, line, end_col)
            raise ParserException(r, regex_with_slashes, f"Regex error in {regex_with_slashes}: '{error}'")

    # ---- Index ----

    @v_args(meta=True, inline=True)
    def index(self, meta: Meta, index_token: Token, class_ref: LocatableString, id_list: list[LocatableString]) -> DefineIndex:
        # Grammar: INDEX class_ref "(" id_list ")"  →  "(" and ")" filtered
        result = DefineIndex(class_ref, id_list)
        self._attach(result, self._loc(index_token), getattr(index_token, "pos_in_stream", 0) or 0)
        return result

    def id_list(self, *tokens: Token) -> list[LocatableString]:
        # Grammar: ID ("," ID)*  →  commas filtered
        result: list[LocatableString] = []
        for t in tokens:
            self._validate_id(t)
            result.append(self._locatable(t))
        return result

    # ---- Expressions ----

    @v_args(meta=True, inline=True)
    def ternary_expr(
        self, meta: Meta, cond: ExpressionStatement, true_val: ExpressionStatement, false_val: ExpressionStatement
    ) -> ExpressionStatement:
        # "?" and ":" are anonymous => filtered
        result = ConditionalExpression(cond, true_val, false_val)
        if hasattr(cond, "location"):
            result.location = cond.location
            result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def or_expr(
        self, meta: Meta, left: ExpressionStatement, op_token: Token, right: ExpressionStatement
    ) -> ExpressionStatement:
        return self._binary_op(left, op_token, right, "or")

    @v_args(meta=True, inline=True)
    def and_expr(
        self, meta: Meta, left: ExpressionStatement, op_token: Token, right: ExpressionStatement
    ) -> ExpressionStatement:
        return self._binary_op(left, op_token, right, "and")

    @v_args(meta=True, inline=True)
    def not_expr(self, meta: Meta, not_token: Token, expr: ExpressionStatement) -> ExpressionStatement:
        result = Not(expr)  # type: ignore[no-untyped-call]
        self._attach(result, self._loc(not_token), getattr(not_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def is_defined_attr(self, meta: Meta, attr_ref: AttributeReference, is_token: Token, _defined: Token) -> IsDefined:
        result = IsDefined(attr_ref.instance, attr_ref.attribute)
        self._attach(result, self._loc(is_token), getattr(is_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def is_defined_id(self, meta: Meta, id_token: Token, is_token: Token, _defined: Token) -> IsDefined:
        id_ls = self._locatable(id_token)
        result = IsDefined(None, id_ls)
        self._attach(result, self._loc(is_token), getattr(is_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def is_defined_map(self, meta: Meta, map_lk: MapLookup, is_token: Token, _defined: Token) -> ExpressionStatement:
        # syntactic sugar: expands to (key in dict) and (dict[key] != null) and (dict[key] != [])
        location = self._loc(is_token)
        lexpos = getattr(is_token, "pos_in_stream", 0) or 0

        def attach(inp: ExpressionStatement) -> ExpressionStatement:
            inp.location = location
            inp.namespace = self.namespace
            inp.lexpos = lexpos
            return inp

        key_in_dict = attach(In(map_lk.key, map_lk.themap))
        not_none = attach(NotEqual(map_lk, attach(Literal(NoneValue()))))
        not_empty_list = attach(NotEqual(map_lk, attach(CreateList(list()))))
        out = attach(And(attach(And(key_in_dict, not_none)), not_empty_list))
        return out

    @v_args(meta=True, inline=True)
    def cmp_expr(
        self, meta: Meta, left: ExpressionStatement, op_token: Token, right: ExpressionStatement
    ) -> ExpressionStatement:
        operator = Operator.get_operator_class(str(op_token))
        if operator is None:
            raise ParserException(
                left.location if hasattr(left, "location") else self._meta_range(meta),
                str(op_token),
                f"Invalid operator {str(op_token)}",
            )
        result: ExpressionStatement = operator(left, right)  # type: ignore[arg-type]
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def in_expr(
        self, meta: Meta, left: ExpressionStatement, op_token: Token, right: ExpressionStatement
    ) -> ExpressionStatement:
        return self._binary_op(left, op_token, right, "in")

    @v_args(meta=True, inline=True)
    def not_in_expr(
        self, meta: Meta, left: ExpressionStatement, not_token: Token, _in: Token, right: ExpressionStatement
    ) -> ExpressionStatement:
        result = Not(In(left, right))  # type: ignore[no-untyped-call]
        self._attach(result, self._loc(not_token), getattr(not_token, "pos_in_stream", 0) or 0)
        return result

    def _binary_op(
        self, left: ExpressionStatement, op_token: Token, right: ExpressionStatement, op_str: str
    ) -> ExpressionStatement:
        operator = Operator.get_operator_class(op_str)
        if operator is None:
            raise ParserException(self._range(op_token), str(op_token), f"Invalid operator {op_str}")
        result: ExpressionStatement = operator(left, right)  # type: ignore[arg-type]
        self._attach(result, self._loc(op_token), getattr(op_token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def add_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "+")

    @v_args(meta=True, inline=True)
    def sub_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "-")

    @v_args(meta=True, inline=True)
    def mul_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "*")

    @v_args(meta=True, inline=True)
    def div_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "/")

    @v_args(meta=True, inline=True)
    def mod_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "%")

    @v_args(meta=True, inline=True)
    def pow_expr(self, meta: Meta, left: ExpressionStatement, op: Token, right: ExpressionStatement) -> ExpressionStatement:
        return self._binary_op(left, op, right, "**")

    # ---- Map lookup ----

    @v_args(meta=True, inline=True)
    def map_lookup(self, meta: Meta, themap: ExpressionStatement, key: ExpressionStatement) -> MapLookup:
        # "[" and "]" are anonymous => filtered
        return MapLookup(themap, key)

    # ---- Constructors and function calls ----

    @v_args(meta=True, inline=True)
    def constructor(self, meta: Meta, class_ref: LocatableString, params: list[_ParamListElement]) -> Constructor:
        # "(" and ")" are anonymous => filtered
        kwargs: list[tuple[LocatableString, ExpressionStatement]] = [
            (e.key, e.value) for e in params if e.key is not None  # type: ignore[misc]
        ]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = Constructor(class_ref, kwargs, wrapped, self._meta_loc(meta), self.namespace)
        return result

    @v_args(meta=True, inline=True)
    def function_call(self, meta: Meta, ns_ref: LocatableString, fparams: list[_FunctionParamElement]) -> FunctionCall:
        # "(" and ")" are anonymous => filtered
        args = [e.arg for e in fparams if e.arg is not None]
        kwargs: list[tuple[LocatableString, ExpressionStatement]] = [
            (e.key, e.value) for e in fparams if e.key is not None  # type: ignore[misc]
        ]
        wrapped = [e.wrapped_kwargs for e in fparams if e.wrapped_kwargs is not None]
        result = FunctionCall(ns_ref, args, kwargs, wrapped, self.namespace)
        return result

    def function_call_err_dot(self, attr_ref: AttributeReference, _fparams: list[_FunctionParamElement]) -> NoReturn:
        raise InvalidNamespaceAccess(attr_ref.locatable_name)

    # ---- Index lookup ----

    @v_args(meta=True, inline=True)
    def index_lookup_class(self, meta: Meta, class_ref: LocatableString, params: list[_ParamListElement]) -> IndexLookup:
        # "[" and "]" are anonymous => filtered
        kwargs: list[tuple[LocatableString, ExpressionStatement]] = [
            (e.key, e.value) for e in params if e.key is not None  # type: ignore[misc]
        ]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = IndexLookup(class_ref, kwargs, wrapped)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def index_lookup_attr(self, meta: Meta, attr_ref: AttributeReference, params: list[_ParamListElement]) -> ShortIndexLookup:
        # "[" and "]" are anonymous => filtered
        kwargs: list[tuple[LocatableString, ExpressionStatement]] = [
            (e.key, e.value) for e in params if e.key is not None  # type: ignore[misc]
        ]
        wrapped = [e.wrapped_kwargs for e in params if e.wrapped_kwargs is not None]
        result = ShortIndexLookup(attr_ref.instance, attr_ref.attribute, kwargs, wrapped)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    # ---- Lists ----

    @v_args(meta=True, inline=True)
    def list_def(self, meta: Meta, operands: list[ExpressionStatement]) -> Union[CreateList, Literal]:
        # "[" and "]" are anonymous => filtered
        node: Union[CreateList, Literal] = CreateList(operands)
        try:
            node = Literal(node.as_constant())
        except RuntimeException:
            pass
        node.location = self._meta_loc(meta)
        node.namespace = self.namespace
        node.lexpos = meta.column if hasattr(meta, "column") else 0
        return node

    @v_args(meta=True, inline=True)
    def list_comprehension(
        self,
        meta: Meta,
        value_expr: ExpressionStatement,
        *clauses: Union[_ForClause, _GuardClause],
    ) -> ExpressionStatement:
        # "[" and "]" are anonymous => filtered
        for_clauses = [item for item in clauses if isinstance(item, _ForClause)]
        guard_clauses = [item.condition for item in clauses if isinstance(item, _GuardClause)]

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

    @v_args(meta=True, inline=True)
    def for_clause(self, meta: Meta, _for: Token, id_token: Token, _in: Token, expression: ExpressionStatement) -> _ForClause:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        return _ForClause(variable=id_ls, iterable=expression)

    @v_args(meta=True, inline=True)
    def guard_clause(self, meta: Meta, _if: Token, expression: ExpressionStatement) -> _GuardClause:
        return _GuardClause(condition=expression)

    def operand_list(self, *items: ExpressionStatement) -> list[ExpressionStatement]:
        return list(items)

    # ---- Map def ----

    @v_args(meta=True, inline=True)
    def map_def(self, meta: Meta, pairs: list[tuple[str, ExpressionStatement]]) -> Union[CreateDict, Literal]:
        # "{" and "}" are anonymous => filtered
        node: Union[CreateDict, Literal] = CreateDict(pairs)  # type: ignore[arg-type]
        try:
            node = Literal({k: v.as_constant() for k, v in pairs})
        except RuntimeException:
            pass
        node.location = self._meta_loc(meta)
        node.namespace = self.namespace
        return node

    def pair_list(self, *items: tuple[str, ExpressionStatement]) -> list[tuple[str, ExpressionStatement]]:
        return list(items)

    def pair_item(self, key: str, value: ExpressionStatement) -> tuple[str, ExpressionStatement]:
        # ":" is anonymous => filtered
        return (key, value)

    def dict_key_string(self, token: Token) -> str:
        raw = str(token)
        # Strip quotes and decode
        content = raw[1:-1]
        loc = Location(self.file, token.line or 1)
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

    def dict_key_rstring(self, token: Token) -> str:
        raw = str(token)
        # Strip r" prefix and " suffix
        content = raw[2:-1]
        return content

    # ---- Param lists ----

    def param_list(self, *items: _ParamListElement) -> list[_ParamListElement]:
        return list(items)

    def param_explicit(self, id_token: Token, value: ExpressionStatement) -> _ParamListElement:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        return _ParamListElement(key=id_ls, value=value)

    def param_wrapped_kwargs(self, ds_token: Token, value: ExpressionStatement) -> _ParamListElement:
        wk = WrappedKwargs(value)
        self._attach(wk, self._loc(ds_token), getattr(ds_token, "pos_in_stream", 0) or 0)
        return _ParamListElement(key=None, value=None, wrapped_kwargs=wk)

    def function_param_list(self, *items: _FunctionParamElement) -> list[_FunctionParamElement]:
        return list(items)

    def func_arg(self, value: ExpressionStatement) -> _FunctionParamElement:
        return _FunctionParamElement(arg=value)

    def func_kwarg(self, id_token: Token, value: ExpressionStatement) -> _FunctionParamElement:
        # "=" is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        return _FunctionParamElement(key=id_ls, value=value)

    def func_wrapped_kwargs(self, ds_token: Token, value: ExpressionStatement) -> _FunctionParamElement:
        wk = WrappedKwargs(value)
        self._attach(wk, self._loc(ds_token), getattr(ds_token, "pos_in_stream", 0) or 0)
        return _FunctionParamElement(wrapped_kwargs=wk)

    # ---- Variable and attribute references ----

    def var_ref_ns(self, ns_ref: LocatableString) -> Reference:
        result = Reference(ns_ref)
        self._attach_from_string(result, ns_ref)
        return result

    @v_args(meta=True, inline=True)
    def attr_ref(self, meta: Meta, var_ref: Reference, id_token: Token) -> AttributeReference:
        # "." is anonymous => filtered
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        result = AttributeReference(var_ref, id_ls)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    # ---- Namespace and class references ----

    def ns_ref_id(self, token: Token) -> LocatableString:
        self._validate_id(token)
        return self._locatable(token)

    def ns_ref_sep(self, left: LocatableString, _sep: Token, id_token: Token) -> LocatableString:
        self._validate_id(id_token)
        id_ls = self._locatable(id_token)
        merged_value = f"{str(left)}::{str(id_ls)}"
        if isinstance(left, LocatableString):
            r = self._expand_range(left.location, id_ls.location)
        else:
            r = id_ls.location
        return LocatableString(merged_value, r, id_ls.lexpos, self.namespace)

    def class_ref_cid(self, cid_token: Token) -> LocatableString:
        return self._locatable(cid_token)

    def class_ref_ns(self, left: LocatableString, _sep: Token, cid_token: Token) -> LocatableString:
        cid_ls = self._locatable(cid_token)
        merged_value = f"{str(left)}::{str(cid_ls)}"
        if isinstance(left, LocatableString):
            r = self._expand_range(left.location, cid_ls.location)
        else:
            r = cid_ls.location
        return LocatableString(merged_value, r, cid_ls.lexpos, self.namespace)

    def class_ref_err_dot(self, var_ref: object, cid_token: Token) -> NoReturn:
        # "." is anonymous => filtered
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

    def class_ref_list(self, *items: LocatableString) -> list[LocatableString]:
        return list(items)

    # ---- Constants ----

    @v_args(meta=True, inline=True)
    def const_int(self, meta: Meta, token: Token) -> Literal:
        result = Literal(int(str(token)))
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def const_float(self, meta: Meta, token: Token) -> Literal:
        result = Literal(float(str(token)))
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def const_null(self, meta: Meta, token: Token) -> Literal:
        return self._make_none(self._loc(token), getattr(token, "pos_in_stream", 0) or 0)

    @v_args(meta=True, inline=True)
    def const_regex(self, meta: Meta, token: Token) -> ExpressionStatement:
        expr = self._process_regex_token(token)
        expr.location = self._loc(token)
        expr.namespace = self.namespace
        return expr

    @v_args(meta=True, inline=True)
    def const_true(self, meta: Meta, token: Token) -> Literal:
        result = Literal(True)
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def const_false(self, meta: Meta, token: Token) -> Literal:
        result = Literal(False)
        self._attach(result, self._loc(token), getattr(token, "pos_in_stream", 0) or 0)
        return result

    @v_args(meta=True, inline=True)
    def const_string(self, meta: Meta, token: Token) -> Union[Literal, StringFormat]:
        raw = str(token)
        content = raw[1:-1]
        loc = Location(self.file, token.line or 1)
        decoded = _safe_decode(content, "Invalid escape sequence in string.", loc)
        ls = LocatableString(decoded, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = _get_string_ast_node(ls, False)
        result.location = self._loc(token)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def const_fstring(self, meta: Meta, token: Token) -> Union[StringFormatV2, Literal]:
        raw = str(token)
        # Strip f" prefix and " suffix
        content = raw[2:-1]
        loc = Location(self.file, token.line or 1)
        decoded = _safe_decode(content, "Invalid escape sequence in f-string.", loc)
        ls = LocatableString(decoded, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = _process_fstring(ls)
        result.location = self._range(token)  # mirrors PLY's attach_from_string (copies Range with column info)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def const_rstring(self, meta: Meta, token: Token) -> Literal:
        raw = str(token)
        content = raw[2:-1]
        ls = LocatableString(content, self._range(token), getattr(token, "pos_in_stream", 0) or 0, self.namespace)
        result = Literal(str(ls))
        self._attach_from_string(result, ls)
        return result

    @v_args(meta=True, inline=True)
    def const_mls(self, meta: Meta, token: Token) -> Union[Literal, StringFormat]:
        ls = self._process_mls(token)
        result = _get_string_ast_node(ls, True)
        result.location = self._range(token)  # mirrors PLY's attach_from_string (copies Range with column info)
        result.namespace = self.namespace
        return result

    @v_args(meta=True, inline=True)
    def const_neg_int(self, meta: Meta, _minus: Token, int_token: Token) -> Literal:
        result = Literal(-int(str(int_token)))
        self._attach(result, self._meta_loc(meta), 0)
        return result

    @v_args(meta=True, inline=True)
    def const_neg_float(self, meta: Meta, _minus: Token, float_token: Token) -> Literal:
        result = Literal(-float(str(float_token)))
        self._attach(result, self._meta_loc(meta), 0)
        return result

    @v_args(meta=True, inline=True)
    def constant_list(self, meta: Meta, consts: list[ExpressionStatement]) -> CreateList:
        # "[" and "]" are anonymous => filtered
        result = CreateList(consts)
        result.location = self._meta_loc(meta)
        result.namespace = self.namespace
        return result

    def constants(self, *items: ExpressionStatement) -> list[ExpressionStatement]:
        return list(items)


# ---- String processing helpers (mirrors PLY parser) ----


def _get_string_ast_node(string_ast: LocatableString, mls: bool) -> Union[Literal, StringFormat]:
    """Process a string for interpolation (mirrors PLY's get_string_ast_node)."""
    matches: list[re.Match[str]] = list(_format_regex_compiled.finditer(str(string_ast)))
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

    def locate_match(match: tuple[str, Optional[str], Optional[str], Optional[str]], scp: int, end_char: int) -> None:
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


def _convert_to_references(variables: list[tuple[str, LocatableString]], namespace: Namespace) -> list[tuple["Reference", str]]:
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
        from inmanta.parser.plyInmantaLex import reserved

        # Inspect the parser value_stack to produce better error messages,
        # mirroring PLY's p_error heuristics.
        vs = getattr(getattr(e, "state", None), "value_stack", None) or []

        # Case 1: a reserved keyword is on top of the stack (e.g. "index = ...")
        # mirrors PLY: if parser.symstack[-1].type in reserved.values(): ...
        if vs:
            top = vs[-1]
            if isinstance(top, Token) and top.type in reserved.values():
                kw_r = Range(tfile, top.line or line, top.column or col, top.line or line, (top.column or col) + len(str(top)))
                return ParserException(kw_r, str(top), f"invalid identifier, {str(top)} is a reserved keyword")

        # Case 2: lowercase class name used in 'extends' (e.g. "entity Test extends test:")
        # mirrors PLY's p_class_ref_list_term_err grammar rule.
        if token is not None and token.type == "COLON" and vs:
            top = vs[-1]
            has_extends = any(isinstance(item, Token) and item.type == "EXTENDS" for item in vs)
            if has_extends:
                if hasattr(top, "data") and top.data.startswith("ns_ref"):
                    # Tree-based: extract the last ID token from the ns_ref tree
                    id_tokens = [t for t in top.children if isinstance(t, Token)]
                    if id_tokens:
                        id_tok = id_tokens[-1]
                        id_r = Range(
                            tfile,
                            id_tok.line or line,
                            id_tok.column or col,
                            id_tok.line or line,
                            (id_tok.column or col) + len(str(id_tok)),
                        )
                        return ParserException(id_r, str(id_tok), "Invalid identifier: Entity names must start with a capital")
                elif isinstance(top, LocatableString):
                    # Inline transformer: top is already the LocatableString from ns_ref
                    return ParserException(top.location, str(top), "Invalid identifier: Entity names must start with a capital")

        if token is not None:
            token_str = str(token)
            # Failing token itself is a reserved keyword (rarely needed after above checks)
            if token.type in reserved.values():
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
