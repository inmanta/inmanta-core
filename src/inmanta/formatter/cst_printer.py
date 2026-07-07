"""
Copyright 2026 Inmanta

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

import os

from lark import Lark, Token, Tree

from inmanta.formatter.comments import CommentMap, FmtOffRegions
from inmanta.formatter.config import FormatConfig

# Build a formatter-specific parser with keep_all_tokens=True so that anonymous
# punctuation tokens ("(", ")", "=", ":", etc.) and underscore-prefixed keyword
# tokens (_END, _EXTENDS, etc.) are preserved in the parse tree.
_FORMATTER_DIR = os.path.dirname(os.path.abspath(__file__))
_PARSER_DIR = os.path.join(os.path.dirname(_FORMATTER_DIR), "parser")

with open(os.path.join(_PARSER_DIR, "inmanta.lark"), "r", encoding="utf-8") as f:
    _GRAMMAR = f.read()

_parser: Lark | None = None


def _get_parser() -> Lark:
    global _parser
    if _parser is None:
        _parser = Lark(_GRAMMAR, parser="lalr", keep_all_tokens=True, maybe_placeholders=False)
    return _parser


def parse_to_cst(source: str) -> Tree:
    """Parse Inmanta source to a concrete syntax tree (all tokens preserved)."""
    return _get_parser().parse(source)


class CSTPrinter:
    """Formats an Inmanta .cf file from its Lark parse tree (CST)."""

    def __init__(
        self,
        source: str,
        comment_map: CommentMap,
        config: FormatConfig,
        fmt_regions: FmtOffRegions | None = None,
    ) -> None:
        self._source = source
        self._source_lines = source.splitlines(keepends=True)
        self._comments = comment_map
        self._config = config
        self._fmt_regions = fmt_regions or FmtOffRegions()
        self._indent = 0
        self._lines: list[str] = []

    def format(self, tree: Tree) -> str:
        """Format the entire file from the ``start`` tree node."""
        self._format_start(tree)
        # Emit any comments not yet consumed (e.g., at end of file)
        for c in self._comments.get_remaining():
            self._emit(c.text)
        return self._finalize()

    # Output helpers

    def _finalize(self) -> str:
        while self._lines and self._lines[-1] == "":
            self._lines.pop()
        if not self._lines:
            return ""
        return "\n".join(self._lines) + "\n"

    def _emit(self, text: str) -> None:
        prefix = " " * (self._indent * self._config.indent_width)
        if "\n" not in text:
            self._lines.append(prefix + text if text else "")
        else:
            # Multi-line text from expanded expressions: first line gets the prefix,
            # subsequent lines already carry absolute indentation from the expander.
            parts = text.split("\n")
            self._lines.append(prefix + parts[0])
            for part in parts[1:]:
                self._lines.append(part)

    def _line_width(self, text: str) -> int:
        """Compute the full width of a line including current indentation."""
        return self._indent * self._config.indent_width + len(text)

    def _emit_blank(self) -> None:
        self._lines.append("")

    def _emit_verbatim(self, start_line: int, end_line: int) -> None:
        """Emit original source lines verbatim (for ``# fmt: off`` regions).

        *start_line* and *end_line* are 1-based inclusive line numbers.
        """
        for i in range(start_line - 1, min(end_line, len(self._source_lines))):
            self._lines.append(self._source_lines[i].rstrip("\n"))
        # Consume all comments in this range so they don't get re-emitted
        self._consume_range(start_line, end_line)

    def _is_fmt_off(self, node: Tree | Token) -> bool:
        """Check if a node falls within a ``# fmt: off`` region or has ``# fmt: skip``."""
        first = self._first_line(node)
        last = self._last_line(node)
        if first and self._fmt_regions.is_off(first):
            return True
        if first and last and self._fmt_regions.is_off_range(first, last):
            return True
        return False

    # Source position helpers

    @staticmethod
    def _first_line(node: Tree | Token) -> int:
        if isinstance(node, Token):
            return node.line
        for child in node.children:
            r = CSTPrinter._first_line(child)
            if r:
                return r
        return 0

    @staticmethod
    def _last_line(node: Tree | Token) -> int:
        if isinstance(node, Token):
            return getattr(node, "end_line", None) or node.line
        for child in reversed(node.children):
            r = CSTPrinter._last_line(child)
            if r:
                return r
        return 0

    # Comment helpers

    def _emit_leading_comments(self, node: Tree | Token) -> None:
        line = self._first_line(node)
        if line:
            for c in self._comments.get_leading(line):
                self._emit(c.text)

    def _trailing_comment_str(self, node: Tree | Token) -> str:
        """Get trailing comment on the first source line of a node."""
        line = self._first_line(node)
        if line:
            c = self._comments.get_trailing(line)
            if c:
                return f"  {c.text}"
        return ""

    def _all_comments_in_range(self, start: int, end: int) -> list["Comment"]:
        """Get all unconsumed comments within a source line range [start, end]."""
        from inmanta.formatter.comments import Comment

        result: list[Comment] = []
        for line_nr in range(start, end + 1):
            c = self._comments._by_line.get(line_nr)
            if c is not None and line_nr not in self._comments._consumed:
                result.append(c)
        return result

    def _consume_range(self, start: int, end: int) -> None:
        """Mark all comments in a source line range as consumed."""
        for line_nr in range(start, end + 1):
            if line_nr in self._comments._by_line:
                self._comments._consumed.add(line_nr)

    def _emit_orphans_between(self, prev: Tree | Token, nxt: Tree | Token) -> None:
        after = self._last_line(prev)
        before = self._first_line(nxt)
        if after and before:
            for c in self._comments.get_orphans(after, before):
                self._emit(c.text)

    # Child extraction helpers

    @staticmethod
    def _subtrees(tree: Tree) -> list[Tree]:
        return [c for c in tree.children if isinstance(c, Tree)]

    @staticmethod
    def _find_token(tree: Tree, token_type: str) -> Token | None:
        for c in tree.children:
            if isinstance(c, Token) and c.type == token_type:
                return c
        return None

    @staticmethod
    def _find_all_tokens(tree: Tree, token_type: str) -> list[Token]:
        return [c for c in tree.children if isinstance(c, Token) and c.type == token_type]

    @staticmethod
    def _has_trailing_comma(tree: Tree) -> bool:
        for c in reversed(tree.children):
            if isinstance(c, Token):
                return str(c) == ","
            break
        return False

    # Top-level

    def _format_start(self, tree: Tree) -> None:
        head = tree.children[0]
        body = tree.children[1]

        # head: MLS?
        mls_tokens = [c for c in head.children if isinstance(c, Token) and c.type == "MLS"]
        if mls_tokens:
            self._emit(self._format_mls(mls_tokens[0]))
            self._emit_blank()

        stmts = self._subtrees(body)
        prev: Tree | None = None
        for stmt in stmts:
            if prev is not None:
                blanks = self._blanks_between(prev, stmt)
                for _ in range(blanks):
                    self._emit_blank()
                self._emit_orphans_between(prev, stmt)
            self._emit_leading_comments(stmt)
            self._format_top_stmt(stmt)
            prev = stmt

    _BLOCK_DEFINITION_DATA = frozenset({
        "entity_def", "entity_def_extends", "entity_def_err", "entity_def_extends_err",
        "implementation_def",
        "typedef_matching", "typedef_regex", "typedef_cls_err", "typedef_comment",
    })

    _IMPORT_DATA = frozenset({"import_ns", "import_as"})

    _RELATION_DATA = frozenset({
        "relation_bidir", "relation_unidir", "relation_annotated_bidir", "relation_annotated_unidir",
        "relation_comment",
    })

    _IMPLEMENT_DATA = frozenset({
        "implement_def_simple", "implement_def_comment", "implement_def_when", "implement_def_when_comment",
    })

    _INDEX_DATA = frozenset({"index"})

    # Categories that group together without blank lines between them
    _GROUPABLE = frozenset({"import", "relation", "implement", "index"})

    def _original_gap(self, prev: Tree | Token, nxt: Tree | Token) -> int:
        """Count blank lines between two nodes in the original source."""
        prev_end = self._last_line(prev)
        nxt_start = self._first_line(nxt)
        if not prev_end or not nxt_start:
            return 0
        # Gap = lines between prev_end and nxt_start, minus 1 (the line-break itself)
        gap = nxt_start - prev_end - 1
        return max(0, gap)

    def _blanks_between(self, prev: Tree, nxt: Tree) -> int:
        pk = self._stmt_category(prev)
        nk = self._stmt_category(nxt)
        top = self._config.blank_lines_between_top_level
        after_imports = self._config.blank_lines_after_imports

        # Enforce minimum blank lines by category
        if pk == "import" and nk != "import":
            minimum = after_imports
        elif pk == "block_definition" or nk == "block_definition":
            minimum = top
        elif (pk in self._GROUPABLE or nk in self._GROUPABLE) and pk != nk:
            minimum = top
        elif pk == nk and pk in self._GROUPABLE:
            minimum = 0
        else:
            minimum = 0

        # Preserve original blank lines: if the author had a blank line, keep 1
        original = self._original_gap(prev, nxt)
        preserved = min(original, 1)  # collapse multiple blank lines to 1

        return max(minimum, preserved)

    def _stmt_category(self, tree: Tree) -> str:
        if tree.data in self._IMPORT_DATA:
            return "import"
        if tree.data in self._RELATION_DATA:
            return "relation"
        if tree.data in self._IMPLEMENT_DATA:
            return "implement"
        if tree.data in self._INDEX_DATA:
            return "index"
        if tree.data in self._BLOCK_DEFINITION_DATA:
            return "block_definition"
        return "statement"

    def _format_top_stmt(self, tree: Tree) -> None:
        # fmt: off/skip — emit original source verbatim
        if self._is_fmt_off(tree):
            self._emit_verbatim(self._first_line(tree), self._last_line(tree))
            return
        handler = getattr(self, f"_fmt_{tree.data}", None)
        if handler:
            handler(tree)
        else:
            tc = self._trailing_comment_str(tree)
            available = self._config.line_length - self._indent * self._config.indent_width
            self._emit(self._format_expr(tree, available_width=available) + tc)

    # Imports

    def _fmt_import_ns(self, tree: Tree) -> None:
        ns = self._subtrees(tree)[0]
        tc = self._trailing_comment_str(tree)
        self._emit(f"import {self._format_expr(ns)}{tc}")

    def _fmt_import_as(self, tree: Tree) -> None:
        ns = self._subtrees(tree)[0]
        ids = self._find_all_tokens(tree, "ID")
        alias = str(ids[-1]) if ids else "?"
        tc = self._trailing_comment_str(tree)
        self._emit(f"import {self._format_expr(ns)} as {alias}{tc}")

    # Entity

    def _fmt_entity_def(self, tree: Tree) -> None:
        name = self._find_token(tree, "CID")
        body_outer = self._subtrees(tree)[0]
        tc = self._trailing_comment_str(tree)
        self._emit(f"entity {name}:{tc}")
        self._indent += 1
        self._format_entity_body_outer(body_outer)
        self._indent -= 1
        self._emit("end")

    def _fmt_entity_def_extends(self, tree: Tree) -> None:
        name = self._find_token(tree, "CID")
        subtrees = self._subtrees(tree)
        class_ref_list = subtrees[0]
        body_outer = subtrees[1]
        tc = self._trailing_comment_str(tree)
        self._emit(f"entity {name} extends {self._format_class_ref_list(class_ref_list)}:{tc}")
        self._indent += 1
        self._format_entity_body_outer(body_outer)
        self._indent -= 1
        self._emit("end")

    def _fmt_entity_def_err(self, tree: Tree) -> None:
        name = self._find_token(tree, "ID")
        body_outer = self._subtrees(tree)[0]
        tc = self._trailing_comment_str(tree)
        self._emit(f"entity {name}:{tc}")
        self._indent += 1
        self._format_entity_body_outer(body_outer)
        self._indent -= 1
        self._emit("end")

    def _fmt_entity_def_extends_err(self, tree: Tree) -> None:
        name = self._find_token(tree, "ID")
        subtrees = self._subtrees(tree)
        class_ref_list = subtrees[0]
        body_outer = subtrees[1]
        tc = self._trailing_comment_str(tree)
        self._emit(f"entity {name} extends {self._format_class_ref_list(class_ref_list)}:{tc}")
        self._indent += 1
        self._format_entity_body_outer(body_outer)
        self._indent -= 1
        self._emit("end")

    def _format_entity_body_outer(self, tree: Tree) -> None:
        data = tree.data
        if data == "entity_body_outer_empty":
            pass
        elif data == "entity_body_outer_mls_only":
            mls = self._find_token(tree, "MLS")
            self._emit(self._format_mls(mls))
        elif data == "entity_body_outer_plain":
            self._format_entity_body(self._subtrees(tree)[0])
        elif data == "entity_body_outer_mls":
            mls = self._find_token(tree, "MLS")
            self._emit(self._format_mls(mls))
            self._format_entity_body(self._subtrees(tree)[0])

    def _format_entity_body(self, tree: Tree) -> None:
        attrs = self._subtrees(tree)
        # When group-annotations is enabled, insert blank lines between attribute
        # groups.  A "group" is a base attribute followed by its __ annotations
        # (e.g. name, name__modifier, name__annotations).
        group = self._config.group_annotations and any(
            (n := self._attr_name(a)) is not None and "__" in n for a in attrs
        )

        for i, attr in enumerate(attrs):
            attr_name = self._attr_name(attr)
            is_annotation = "__" in attr_name if attr_name else False

            if group and i > 0 and not is_annotation:
                self._emit_blank()

            self._emit_leading_comments(attr)
            tc = self._trailing_comment_str(attr)
            self._emit(self._format_attr(attr) + tc)

    @staticmethod
    def _attr_name(attr_tree: Tree) -> str | None:
        """Extract the attribute name (ID or CID) from an attr tree."""
        # Try ID first (normal case), then CID (error case)
        for c in attr_tree.children:
            if isinstance(c, Token) and c.type in ("ID", "CID"):
                return str(c)
        return None

    # Attributes

    def _format_attr(self, tree: Tree) -> str:
        data = tree.data
        subtrees = self._subtrees(tree)

        if data == "attr_simple":
            return f"{self._format_attr_type(subtrees[0])} {self._find_token(tree, 'ID')}"

        if data == "attr_cte":
            prefix = f"{self._format_attr_type(subtrees[0])} {self._find_token(tree, 'ID')}="
            available = self._config.line_length - self._indent * self._config.indent_width - len(prefix)
            return f"{prefix}{self._format_expr(subtrees[1], available_width=available)}"

        if data == "attr_cte_list":
            prefix = f"{self._format_attr_type(subtrees[0])} {self._find_token(tree, 'ID')}="
            available = self._config.line_length - self._indent * self._config.indent_width - len(prefix)
            return f"{prefix}{self._format_expr(subtrees[1], available_width=available)}"

        if data == "attr_undef":
            return f"{self._format_attr_type(subtrees[0])} {self._find_token(tree, 'ID')}=undef"

        if data == "attr_dict":
            return f"dict {self._find_token(tree, 'ID')}"

        if data == "attr_list_dict":
            prefix = f"dict {self._find_token(tree, 'ID')}="
            available = self._config.line_length - self._indent * self._config.indent_width - len(prefix)
            return f"{prefix}{self._format_expr(subtrees[0], available_width=available)}"

        if data == "attr_list_dict_null_err":
            return f"dict {self._find_token(tree, 'ID')}=null"

        if data == "attr_dict_nullable":
            return f"dict? {self._find_token(tree, 'ID')}"

        if data == "attr_list_dict_nullable":
            prefix = f"dict? {self._find_token(tree, 'ID')}="
            available = self._config.line_length - self._indent * self._config.indent_width - len(prefix)
            return f"{prefix}{self._format_expr(subtrees[0], available_width=available)}"

        if data == "attr_list_dict_null":
            return f"dict? {self._find_token(tree, 'ID')}=null"

        # Error / fallback cases
        return self._reconstruct(tree)

    def _format_attr_type(self, tree: Tree) -> str:
        data = tree.data
        if data == "attr_base_type":
            return self._format_expr(self._subtrees(tree)[0])
        if data == "attr_type_multi":
            return f"{self._format_attr_type(self._subtrees(tree)[0])}[]"
        if data == "attr_type_opt_multi":
            return f"{self._format_attr_type(self._subtrees(tree)[0])}?"
        if data == "attr_type_opt_base":
            return f"{self._format_attr_type(self._subtrees(tree)[0])}?"
        return self._format_expr(tree)

    # Implement

    def _fmt_implement_def_simple(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        tc = self._trailing_comment_str(tree)
        self._emit(
            f"implement {self._format_expr(subtrees[0])}"
            f" using {self._format_implement_ns_list(subtrees[1])}{tc}"
        )

    def _fmt_implement_def_comment(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        mls = self._find_token(tree, "MLS")
        tc = self._trailing_comment_str(tree)
        self._emit(
            f"implement {self._format_expr(subtrees[0])}"
            f" using {self._format_implement_ns_list(subtrees[1])}{tc}"
        )
        self._emit(self._format_mls(mls))

    def _fmt_implement_def_when(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        tc = self._trailing_comment_str(tree)
        self._emit(
            f"implement {self._format_expr(subtrees[0])}"
            f" using {self._format_implement_ns_list(subtrees[1])}"
            f" when {self._format_expr(subtrees[2])}{tc}"
        )

    def _fmt_implement_def_when_comment(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        mls = self._find_token(tree, "MLS")
        tc = self._trailing_comment_str(tree)
        self._emit(
            f"implement {self._format_expr(subtrees[0])}"
            f" using {self._format_implement_ns_list(subtrees[1])}"
            f" when {self._format_expr(subtrees[2])}{tc}"
        )
        self._emit(self._format_mls(mls))

    def _format_implement_ns_list(self, tree: Tree) -> str:
        items = self._subtrees(tree)
        parts: list[str] = []
        for item in items:
            if item.data == "impl_parents":
                parts.append("parents")
            else:
                parts.append(self._format_expr(self._subtrees(item)[0]))
        return ", ".join(parts)

    # Implementation

    def _fmt_implementation_def(self, tree: Tree) -> None:
        name = self._find_token(tree, "ID")
        subtrees = self._subtrees(tree)
        class_ref = subtrees[0]
        impl_header = subtrees[1]
        stmt_list = subtrees[2]
        end_token = self._find_token(tree, "_END")
        end_line = end_token.line if end_token else 0
        tc = self._trailing_comment_str(tree)
        impl_token = self._find_token(tree, "IMPLEMENTATION")
        start_line = impl_token.line if impl_token else 0
        self._emit(f"implementation {name} for {self._format_expr(class_ref)}:{tc}")
        self._indent += 1
        if impl_header.data == "impl_header_doc":
            mls = self._find_token(impl_header, "MLS")
            self._emit(self._format_mls(mls))
        self._format_stmt_list(stmt_list, start_line=start_line, end_line=end_line)
        self._indent -= 1
        self._emit("end")

    # Relation

    def _fmt_relation_comment(self, tree: Tree) -> None:
        rel_def = self._subtrees(tree)[0]
        mls = self._find_token(tree, "MLS")
        self._format_relation_def(rel_def)
        self._emit(self._format_mls(mls))

    def _fmt_relation_bidir(self, tree: Tree) -> None:
        self._format_relation_def(tree)

    def _fmt_relation_unidir(self, tree: Tree) -> None:
        self._format_relation_def(tree)

    def _fmt_relation_annotated_bidir(self, tree: Tree) -> None:
        self._format_relation_def(tree)

    def _fmt_relation_annotated_unidir(self, tree: Tree) -> None:
        self._format_relation_def(tree)

    def _format_relation_def(self, tree: Tree) -> None:
        data = tree.data
        subtrees = self._subtrees(tree)
        ids = self._find_all_tokens(tree, "ID")
        rel = self._find_token(tree, "REL")
        rel_op = str(rel) if rel else "--"
        tc = self._trailing_comment_str(tree)

        if data == "relation_bidir":
            # subtrees: [class_ref, multi, class_ref, multi]
            self._emit(
                f"{self._format_expr(subtrees[0])}.{ids[0]}"
                f" {self._format_multi(subtrees[1])}"
                f" {rel_op}"
                f" {self._format_expr(subtrees[2])}.{ids[1]}"
                f" {self._format_multi(subtrees[3])}{tc}"
            )
        elif data == "relation_unidir":
            # subtrees: [class_ref, multi, class_ref]
            self._emit(
                f"{self._format_expr(subtrees[0])}.{ids[0]}"
                f" {self._format_multi(subtrees[1])}"
                f" {rel_op}"
                f" {self._format_expr(subtrees[2])}{tc}"
            )
        elif data == "relation_annotated_bidir":
            # subtrees: [class_ref, multi, annotation_list, class_ref, multi]
            annotations = ", ".join(
                self._format_expr_compact(a) for a in self._subtrees(subtrees[2])
            )
            self._emit(
                f"{self._format_expr(subtrees[0])}.{ids[0]}"
                f" {self._format_multi(subtrees[1])}"
                f" {annotations}"
                f" {self._format_expr(subtrees[3])}.{ids[1]}"
                f" {self._format_multi(subtrees[4])}{tc}"
            )
        elif data == "relation_annotated_unidir":
            # subtrees: [class_ref, multi, annotation_list, class_ref]
            annotations = ", ".join(
                self._format_expr_compact(a) for a in self._subtrees(subtrees[2])
            )
            self._emit(
                f"{self._format_expr(subtrees[0])}.{ids[0]}"
                f" {self._format_multi(subtrees[1])}"
                f" {annotations}"
                f" {self._format_expr(subtrees[2 + 1])}{tc}"
            )
        else:
            self._emit(self._reconstruct(tree) + tc)

    # Typedef

    def _fmt_typedef_comment(self, tree: Tree) -> None:
        inner = self._subtrees(tree)[0]
        mls = self._find_token(tree, "MLS")
        self._format_typedef_inner(inner)
        self._emit(self._format_mls(mls))

    def _fmt_typedef_matching(self, tree: Tree) -> None:
        self._format_typedef_inner(tree)

    def _fmt_typedef_regex(self, tree: Tree) -> None:
        self._format_typedef_inner(tree)

    def _fmt_typedef_cls_err(self, tree: Tree) -> None:
        self._format_typedef_inner(tree)

    def _format_typedef_inner(self, tree: Tree) -> None:
        data = tree.data
        tc = self._trailing_comment_str(tree)
        if data == "typedef_matching":
            name = self._find_token(tree, "ID")
            subtrees = self._subtrees(tree)
            base_type = self._format_expr_compact(subtrees[0])
            prefix = f"typedef {name} as {base_type} matching "
            prefix_len = self._indent * self._config.indent_width + len(prefix)
            available = self._config.line_length - prefix_len
            matching_expr = self._format_expr(subtrees[1], available_width=available)
            self._emit(f"{prefix}{matching_expr}{tc}")
        elif data == "typedef_regex":
            name = self._find_token(tree, "ID")
            ns = self._subtrees(tree)[0]
            regex = self._find_token(tree, "REGEX")
            self._emit(f"typedef {name} as {self._format_expr(ns)} {regex}{tc}")
        elif data == "typedef_cls_err":
            cid = self._find_token(tree, "CID")
            constructor = self._subtrees(tree)[0]
            self._emit(f"typedef {cid} as {self._format_expr(constructor)}{tc}")

    # Index

    def _fmt_index(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        class_ref = subtrees[0]
        id_list = subtrees[1]
        ids = self._find_all_tokens(id_list, "ID")
        tc = self._trailing_comment_str(tree)
        self._emit(f"index {self._format_expr(class_ref)}({', '.join(str(i) for i in ids)}){tc}")

    # Statements (inside blocks)

    def _format_stmt_list(self, tree: Tree, start_line: int = 0, end_line: int = 0) -> None:
        """Format a statement list.

        *start_line* is the source line of the opening keyword (``for``, ``if``, etc.),
        used to find comments in empty blocks.
        *end_line* is the source line of the closing ``end``/``else``/``elif`` keyword.
        """
        stmts = self._subtrees(tree)
        prev: Tree | None = None
        for stmt in stmts:
            if prev is not None:
                # Preserve single blank lines between block-level statements
                if self._original_gap(prev, stmt) >= 1:
                    self._emit_blank()
                self._emit_orphans_between(prev, stmt)
            self._emit_leading_comments(stmt)
            self._format_statement(stmt)
            prev = stmt
        # Emit comments between the last statement (or block start) and the closing keyword
        if end_line:
            after = self._last_line(prev) if prev is not None else start_line
            if after:
                for c in self._comments.get_orphans(after, end_line):
                    self._emit(c.text)

    def _format_statement(self, tree: Tree) -> None:
        # fmt: off/skip — emit original source verbatim
        if self._is_fmt_off(tree):
            self._emit_verbatim(self._first_line(tree), self._last_line(tree))
            return
        handler = getattr(self, f"_fmt_{tree.data}", None)
        if handler:
            handler(tree)
        else:
            tc = self._trailing_comment_str(tree)
            available = self._config.line_length - self._indent * self._config.indent_width
            self._emit(self._format_expr(tree, available_width=available) + tc)

    def _fmt_assign_eq(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        tc = self._trailing_comment_str(tree)
        lhs = self._format_expr_compact(subtrees[0])
        prefix_len = self._indent * self._config.indent_width + len(lhs) + 3  # " = "
        available = self._config.line_length - prefix_len
        rhs = self._format_expr(subtrees[1], available_width=available)
        self._emit(f"{lhs} = {rhs}{tc}")

    def _fmt_assign_plus_eq(self, tree: Tree) -> None:
        subtrees = self._subtrees(tree)
        tc = self._trailing_comment_str(tree)
        lhs = self._format_expr_compact(subtrees[0])
        prefix_len = self._indent * self._config.indent_width + len(lhs) + 4  # " += "
        available = self._config.line_length - prefix_len
        rhs = self._format_expr(subtrees[1], available_width=available)
        self._emit(f"{lhs} += {rhs}{tc}")

    def _fmt_for_stmt(self, tree: Tree) -> None:
        name = self._find_token(tree, "ID")
        subtrees = self._subtrees(tree)
        stmt_list = next(s for s in subtrees if s.data == "stmt_list")
        operand = next(s for s in subtrees if s.data != "stmt_list")
        for_token = self._find_token(tree, "FOR")
        start_line = for_token.line if for_token else 0
        end_token = self._find_token(tree, "_END")
        end_line = end_token.line if end_token else 0
        tc = self._trailing_comment_str(tree)
        self._emit(f"for {name} in {self._format_expr(operand)}:{tc}")
        self._indent += 1
        self._format_stmt_list(stmt_list, start_line=start_line, end_line=end_line)
        self._indent -= 1
        self._emit("end")

    def _fmt_if_stmt(self, tree: Tree) -> None:
        if_body = self._subtrees(tree)[0]
        if_token = self._find_token(tree, "IF")
        start_line = if_token.line if if_token else 0
        end_token = self._find_token(tree, "_END")
        end_line = end_token.line if end_token else 0
        tc = self._trailing_comment_str(tree)
        self._format_if_body(if_body, "if", tc, start_line=start_line, end_line=end_line)
        self._emit("end")

    def _format_if_body(self, tree: Tree, keyword: str, tc: str = "",
                        start_line: int = 0, end_line: int = 0) -> None:
        subtrees = self._subtrees(tree)
        expr = subtrees[0]
        stmt_list = next(s for s in subtrees if s.data == "stmt_list")
        if_next = next(s for s in subtrees if s.data.startswith("if_next_"))
        # The stmt_list ends where the if_next (or end keyword) begins
        next_line = self._first_line(if_next) if if_next.data != "if_next_empty" else end_line
        # start_line for the body is the line with the keyword (if/elif)
        body_start = start_line or self._first_line(expr)
        self._emit(f"{keyword} {self._format_expr(expr)}:{tc}")
        self._indent += 1
        self._format_stmt_list(stmt_list, start_line=body_start, end_line=next_line)
        self._indent -= 1
        self._format_if_next(if_next, end_line=end_line)

    def _format_if_next(self, tree: Tree, end_line: int = 0) -> None:
        data = tree.data
        if data == "if_next_empty":
            return
        if data == "if_next_else":
            stmt_list = self._subtrees(tree)[0]
            else_token = self._find_token(tree, "_ELSE")
            else_line = else_token.line if else_token else 0
            self._emit("else:")
            self._indent += 1
            self._format_stmt_list(stmt_list, start_line=else_line, end_line=end_line)
            self._indent -= 1
        elif data == "if_next_elif":
            if_body = self._subtrees(tree)[0]
            elif_token = self._find_token(tree, "_ELIF")
            elif_line = elif_token.line if elif_token else 0
            self._format_if_body(if_body, "elif", start_line=elif_line, end_line=end_line)

    # Expression formatting (returns string)

    def _format_expr(self, node: Tree | Token, available_width: int | None = None) -> str:
        """Format an expression. If *available_width* is given and the compact
        form exceeds it, try expanding into multi-line form."""
        if isinstance(node, Token):
            return self._format_token(node)

        # If the expression spans multiple source lines and contains comments,
        # preserve the original source verbatim — compacting would lose the comments.
        if self._has_internal_comments(node):
            return self._verbatim_expr(node)

        handler = getattr(self, f"_expr_{node.data}", None)
        if handler is None:
            return self._reconstruct(node)

        compact = handler(node)

        # Magic trailing comma: always expand regardless of width
        if self._should_force_expand(node):
            expanded = self._try_expand(node, self._indent)
            if expanded is not None:
                return expanded

        # Check if expansion is needed due to line width
        if available_width is not None and len(compact) > available_width:
            expanded = self._try_expand(node, self._indent)
            if expanded is not None:
                return expanded

        # Compact form is used — consume any comments inside this node's range
        # so they don't get dumped at end of file.  (The expanded path handles
        # its own comments via _expand_call.)
        if node.data in self._EXPANDABLE:
            self._consume_range(self._first_line(node), self._last_line(node))

        return compact

    def _format_expr_compact(self, node: Tree | Token) -> str:
        """Always return the compact (single-line) form of an expression."""
        if isinstance(node, Token):
            return self._format_token(node)
        handler = getattr(self, f"_expr_{node.data}", None)
        if handler:
            return handler(node)
        return self._reconstruct(node)

    def _has_internal_comments(self, node: Tree | Token) -> bool:
        """Check if a node spans multiple source lines and contains comments."""
        if isinstance(node, Token):
            return False
        first = self._first_line(node)
        last = self._last_line(node)
        if not first or not last or first == last:
            return False
        return bool(self._all_comments_in_range(first, last))

    def _verbatim_expr(self, node: Tree | Token) -> str:
        """Return the original source text for a node, re-indented to the current level.

        Uses the first token's column position to extract only the expression
        portion of the first line (which may also contain the LHS of an assignment).
        """
        first = self._first_line(node)
        last = self._last_line(node)
        if not first or not last:
            return self._reconstruct(node)

        # Find the column where the expression starts (0-based)
        first_col = self._first_column(node)

        # Extract original lines and consume any comments in range
        orig_lines: list[str] = []
        for i in range(first - 1, min(last, len(self._source_lines))):
            orig_lines.append(self._source_lines[i].rstrip("\n"))
        self._consume_range(first, last)

        if not orig_lines:
            return self._reconstruct(node)

        # First line: take only from the expression start column
        first_line_text = orig_lines[0][first_col:] if first_col else orig_lines[0].lstrip()
        # Determine base indentation from the second line (continuation lines)
        if len(orig_lines) > 1:
            second = orig_lines[1]
            base_indent = len(second) - len(second.lstrip()) if second.strip() else 0
        else:
            base_indent = 0

        # Re-indent continuation lines: shift each by (target - base_indent), preserving
        # relative indentation. Clamp at 0 so lines dedented below the first continuation
        # line - typically the closing bracket, aligned with the statement - are not
        # over-indented (previously such lines were pushed one level too deep).
        shift = (self._indent + 1) * self._config.indent_width - base_indent
        result_lines: list[str] = [first_line_text]
        for line in orig_lines[1:]:
            if not line.strip():
                result_lines.append("")
                continue
            orig_indent = len(line) - len(line.lstrip())
            result_lines.append(" " * max(0, orig_indent + shift) + line.lstrip())
        return "\n".join(result_lines)

    @staticmethod
    def _first_column(node: Tree | Token) -> int:
        """Get the 0-based column of the first token in a node."""
        if isinstance(node, Token):
            return (node.column or 1) - 1  # Lark columns are 1-based
        for child in node.children:
            r = CSTPrinter._first_column(child)
            if r >= 0:
                return r
        return 0

    def _format_token(self, token: Token) -> str:
        if token.type == "STRING" and self._config.normalize_quotes:
            return self._normalize_string_quotes(str(token))
        return str(token)

    @staticmethod
    def _normalize_string_quotes(s: str) -> str:
        if s.startswith('"'):
            return s
        if not s.startswith("'") or not s.endswith("'"):
            return s
        inner = s[1:-1]
        # Check for unescaped double quotes
        i = 0
        while i < len(inner):
            if inner[i] == "\\" and i + 1 < len(inner):
                i += 2
                continue
            if inner[i] == '"':
                return s
            i += 1
        inner = inner.replace("\\'", "'")
        return f'"{inner}"'

    # References

    def _expr_ns_ref_id(self, tree: Tree) -> str:
        return str(self._find_token(tree, "ID"))

    def _expr_ns_ref_sep(self, tree: Tree) -> str:
        ns = self._subtrees(tree)[0]
        ids = self._find_all_tokens(tree, "ID")
        return f"{self._format_expr(ns)}::{ids[-1]}"

    def _expr_var_ref_ns(self, tree: Tree) -> str:
        return self._format_expr(self._subtrees(tree)[0])

    def _expr_attr_ref(self, tree: Tree) -> str:
        var = self._subtrees(tree)[0]
        ids = self._find_all_tokens(tree, "ID")
        return f"{self._format_expr(var)}.{ids[-1]}"

    def _expr_class_ref_cid(self, tree: Tree) -> str:
        return str(self._find_token(tree, "CID"))

    def _expr_class_ref_ns(self, tree: Tree) -> str:
        ns = self._subtrees(tree)[0]
        cid = self._find_token(tree, "CID")
        return f"{self._format_expr(ns)}::{cid}"

    def _expr_class_ref_err_dot(self, tree: Tree) -> str:
        var = self._subtrees(tree)[0]
        cid = self._find_token(tree, "CID")
        return f"{self._format_expr(var)}.{cid}"

    def _format_class_ref_list(self, tree: Tree) -> str:
        return ", ".join(self._format_expr(c) for c in self._subtrees(tree))

    # Constants

    def _expr_const_int(self, tree: Tree) -> str:
        return str(self._find_token(tree, "INT"))

    def _expr_const_float(self, tree: Tree) -> str:
        return str(self._find_token(tree, "FLOAT"))

    def _expr_const_null(self, tree: Tree) -> str:
        return "null"

    def _expr_const_regex(self, tree: Tree) -> str:
        return str(self._find_token(tree, "REGEX"))

    def _expr_const_true(self, tree: Tree) -> str:
        return "true"

    def _expr_const_false(self, tree: Tree) -> str:
        return "false"

    def _expr_const_string(self, tree: Tree) -> str:
        return self._format_token(self._find_token(tree, "STRING"))

    def _expr_const_fstring(self, tree: Tree) -> str:
        return str(self._find_token(tree, "FSTRING"))

    def _expr_const_rstring(self, tree: Tree) -> str:
        return str(self._find_token(tree, "RSTRING"))

    def _expr_const_mls(self, tree: Tree) -> str:
        return str(self._find_token(tree, "MLS"))

    def _expr_const_neg_int(self, tree: Tree) -> str:
        return f"-{self._find_token(tree, 'INT')}"

    def _expr_const_neg_float(self, tree: Tree) -> str:
        return f"-{self._find_token(tree, 'FLOAT')}"

    def _expr_constant_list(self, tree: Tree) -> str:
        constants = self._subtrees(tree)[0]
        items = self._subtrees(constants)
        if not items:
            return "[]"
        return f"[{', '.join(self._format_expr(c) for c in items)}]"

    # Binary / unary operators

    def _expr_or_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} or {self._format_expr(t[1])}"

    def _expr_and_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} and {self._format_expr(t[1])}"

    def _expr_not_expr(self, tree: Tree) -> str:
        return f"not {self._format_expr(self._subtrees(tree)[0])}"

    def _expr_cmp_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        op = self._find_token(tree, "CMP_OP")
        return f"{self._format_expr(t[0])} {op} {self._format_expr(t[1])}"

    def _expr_in_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} in {self._format_expr(t[1])}"

    def _expr_not_in_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} not in {self._format_expr(t[1])}"

    def _expr_add_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} + {self._format_expr(t[1])}"

    def _expr_sub_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} - {self._format_expr(t[1])}"

    def _expr_mul_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} * {self._format_expr(t[1])}"

    def _expr_div_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} / {self._format_expr(t[1])}"

    def _expr_mod_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} % {self._format_expr(t[1])}"

    def _expr_pow_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} ** {self._format_expr(t[1])}"

    def _expr_ternary_expr(self, tree: Tree) -> str:
        t = self._subtrees(tree)
        return f"{self._format_expr(t[0])} ? {self._format_expr(t[1])} : {self._format_expr(t[2])}"

    # Is defined

    def _expr_is_defined_attr(self, tree: Tree) -> str:
        return f"{self._format_expr(self._subtrees(tree)[0])} is defined"

    def _expr_is_defined_id(self, tree: Tree) -> str:
        return f"{self._find_token(tree, 'ID')} is defined"

    def _expr_is_defined_map(self, tree: Tree) -> str:
        return f"{self._format_expr(self._subtrees(tree)[0])} is defined"

    # Parenthesized expression

    def _expr_primary(self, tree: Tree) -> str:
        # With keep_all_tokens, ?primary creates a tree only for "(" expr ")"
        inner = self._subtrees(tree)
        if inner:
            return f"({self._format_expr(inner[0])})"
        return self._reconstruct(tree)

    # Constructor / function call

    def _expr_constructor(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr_compact(subtrees[0])}({self._format_param_list(subtrees[1])})"

    def _expr_function_call(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr_compact(subtrees[0])}({self._format_function_param_list(subtrees[1])})"

    def _expr_function_call_err_dot(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr_compact(subtrees[0])}({self._format_function_param_list(subtrees[1])})"

    # Param lists

    def _format_param_list(self, tree: Tree) -> str:
        """Format param list in compact (single-line) form. Trailing commas are
        stripped — they only appear in the expanded multi-line form."""
        items = self._subtrees(tree)
        if not items:
            return ""
        return ", ".join(self._format_param_element_compact(item) for item in items)

    def _format_function_param_list(self, tree: Tree) -> str:
        """Format function param list in compact (single-line) form. Trailing commas
        are stripped — they only appear in the expanded multi-line form."""
        items = self._subtrees(tree)
        if not items:
            return ""
        return ", ".join(self._format_function_param_element_compact(item) for item in items)

    # Lists / maps

    def _expr_list_def(self, tree: Tree) -> str:
        """Compact single-line form. Trailing commas stripped (they trigger expansion)."""
        operand_list = self._subtrees(tree)[0]
        items = self._subtrees(operand_list)
        if not items:
            return "[]"
        return "[" + ", ".join(self._format_expr_compact(i) for i in items) + "]"

    def _expr_list_comprehension(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        expr = subtrees[0]
        for_clauses = [s for s in subtrees if s.data == "for_clause"]
        guard_clauses = [s for s in subtrees if s.data == "guard_clause"]
        result = f"[{self._format_expr(expr)}"
        for fc in for_clauses:
            fc_id = self._find_token(fc, "ID")
            fc_expr = self._subtrees(fc)[0]
            result += f" for {fc_id} in {self._format_expr(fc_expr)}"
        for gc in guard_clauses:
            gc_expr = self._subtrees(gc)[0]
            result += f" if {self._format_expr(gc_expr)}"
        return result + "]"

    def _expr_map_def(self, tree: Tree) -> str:
        """Compact single-line form. Trailing commas stripped (they trigger expansion)."""
        pair_list = self._subtrees(tree)[0]
        items = self._subtrees(pair_list)
        if not items:
            return "{}"
        parts: list[str] = []
        for item in items:
            st = self._subtrees(item)
            key = self._format_expr_compact(st[0])
            val = self._format_expr_compact(st[1])
            parts.append(f"{key}: {val}")
        return "{" + ", ".join(parts) + "}"

    def _expr_map_lookup(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr(subtrees[0])}[{self._format_expr(subtrees[1])}]"

    # Index lookup

    def _expr_index_lookup_class(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr(subtrees[0])}[{self._format_param_list(subtrees[1])}]"

    def _expr_index_lookup_attr(self, tree: Tree) -> str:
        subtrees = self._subtrees(tree)
        return f"{self._format_expr(subtrees[0])}[{self._format_param_list(subtrees[1])}]"

    # Dict key

    def _expr_dict_key_string(self, tree: Tree) -> str:
        return self._format_token(self._find_token(tree, "STRING"))

    def _expr_dict_key_rstring(self, tree: Tree) -> str:
        return str(self._find_token(tree, "RSTRING"))

    # Multiplicity

    def _format_multi(self, tree: Tree) -> str:
        data = tree.data
        ints = self._find_all_tokens(tree, "INT")
        if data == "multi_exact":
            return f"[{ints[0]}]"
        if data == "multi_lower_bound":
            return f"[{ints[0]}:]"
        if data == "multi_range":
            return f"[{ints[0]}:{ints[1]}]"
        if data == "multi_upper_bound":
            return f"[:{ints[0]}]"
        return self._reconstruct(tree)

    # MLS / docstring

    @staticmethod
    def _format_mls(token: Token) -> str:
        value = str(token)
        n_open = 0
        while n_open < len(value) and value[n_open] == '"':
            n_open += 1
        n_close = 0
        while n_close < len(value) and value[-(n_close + 1)] == '"':
            n_close += 1
        content = value[n_open : len(value) - n_close]
        return f'"""{content}"""'

    # Line splitting / expansion

    _EXPANDABLE = frozenset({
        "constructor", "function_call", "function_call_err_dot",
        "list_def", "map_def",
        "primary", "in_expr", "not_in_expr",
    })

    def _should_force_expand(self, node: Tree) -> bool:
        """Check if a magic trailing comma forces multi-line expansion."""
        if node.data == "constructor":
            param_tree = self._subtrees(node)[1]
            return self._has_trailing_comma(param_tree) and bool(self._subtrees(param_tree))
        if node.data in ("function_call", "function_call_err_dot"):
            param_tree = self._subtrees(node)[1]
            return self._has_trailing_comma(param_tree) and bool(self._subtrees(param_tree))
        if node.data == "list_def":
            op_list = self._subtrees(node)[0]
            return self._has_trailing_comma(op_list) and bool(self._subtrees(op_list))
        if node.data == "map_def":
            pair_list = self._subtrees(node)[0]
            return self._has_trailing_comma(pair_list) and bool(self._subtrees(pair_list))
        return False

    def _try_expand(self, node: Tree, indent_level: int) -> str | None:
        """Try to expand *node* into multi-line form.

        Returns a string where the first line has no indentation (the caller
        handles it) and subsequent lines have absolute indentation.
        Returns ``None`` if expansion is not applicable.
        """
        handler = getattr(self, f"_expand_{node.data}", None)
        if handler:
            return handler(node, indent_level)
        return None

    def _indent_str(self, level: int) -> str:
        return " " * (level * self._config.indent_width)

    # — Constructor / function call expansion —

    def _expand_constructor(self, tree: Tree, indent_level: int) -> str:
        subtrees = self._subtrees(tree)
        name = self._format_expr_compact(subtrees[0])
        return self._expand_call(name, subtrees[1], indent_level, is_constructor=True)

    def _expand_function_call(self, tree: Tree, indent_level: int) -> str:
        subtrees = self._subtrees(tree)
        name = self._format_expr_compact(subtrees[0])
        return self._expand_call(name, subtrees[1], indent_level, is_constructor=False)

    def _expand_function_call_err_dot(self, tree: Tree, indent_level: int) -> str:
        subtrees = self._subtrees(tree)
        name = self._format_expr_compact(subtrees[0])
        return self._expand_call(name, subtrees[1], indent_level, is_constructor=False)

    def _expand_call(self, name: str, param_tree: Tree, indent_level: int, *, is_constructor: bool) -> str:
        """Expand a call expression with one argument per line.

        Inline comments from the original source are preserved on their
        corresponding argument lines.  Standalone comments between arguments
        are emitted as separate lines.
        """
        items = self._subtrees(param_tree)
        if not items:
            return f"{name}()"

        inner = self._indent_str(indent_level + 1)
        close = self._indent_str(indent_level)
        max_w = self._config.line_length

        lines = [f"{name}("]
        prev_end = self._first_line(param_tree)  # opening paren line
        for item in items:
            item_start = self._first_line(item)
            item_end = self._last_line(item)

            # Emit standalone comments between the previous arg and this one
            if prev_end and item_start:
                for c in self._comments.get_orphans(prev_end, item_start):
                    lines.append(f"{inner}{c.text}")

            # Emit leading comments for this argument
            if item_start:
                for c in self._comments.get_leading(item_start):
                    lines.append(f"{inner}{c.text}")

            if is_constructor:
                elem = self._format_param_element_compact(item)
            else:
                elem = self._format_function_param_element_compact(item)
            # Check if this element itself is too long and try to expand the value
            if len(inner) + len(elem) + 1 > max_w:  # +1 for trailing comma
                expanded_elem = self._try_expand_element(item, indent_level + 1, is_constructor)
                if expanded_elem is not None:
                    elem = expanded_elem

            # Check for trailing (inline) comment on any line within this arg's range
            tc = ""
            if item_start and item_end:
                for ln in range(item_start, item_end + 1):
                    c = self._comments.get_trailing(ln)
                    if c:
                        tc = f"  {c.text}"
                        break

            lines.append(f"{inner}{elem},{tc}")
            prev_end = item_end or prev_end

        # Comments between last arg and closing paren
        close_line = self._last_line(param_tree)
        if prev_end and close_line:
            for c in self._comments.get_orphans(prev_end, close_line):
                lines.append(f"{inner}{c.text}")

        lines.append(f"{close})")
        return "\n".join(lines)

    def _try_expand_element(self, item: Tree, indent_level: int, is_constructor: bool) -> str | None:
        """Try to expand a parameter element's value."""
        if is_constructor:
            if item.data == "param_explicit":
                name = self._find_token(item, "ID")
                val_tree = self._subtrees(item)[0]
                expanded_val = self._try_expand(val_tree, indent_level)
                if expanded_val is not None:
                    return f"{name}={expanded_val}"
        else:
            if item.data == "func_arg":
                child = self._subtrees(item)
                if child:
                    expanded = self._try_expand(child[0], indent_level)
                    if expanded is not None:
                        return expanded
            elif item.data == "func_kwarg":
                name = self._find_token(item, "ID")
                val_tree = self._subtrees(item)[0]
                expanded_val = self._try_expand(val_tree, indent_level)
                if expanded_val is not None:
                    return f"{name}={expanded_val}"
        return None

    def _format_param_element_compact(self, item: Tree) -> str:
        if item.data == "param_explicit":
            name = self._find_token(item, "ID")
            val = self._subtrees(item)[0]
            return f"{name}={self._format_expr_compact(val)}"
        if item.data == "param_wrapped_kwargs":
            val = self._subtrees(item)[0]
            return f"**{self._format_expr_compact(val)}"
        return self._reconstruct(item)

    def _format_function_param_element_compact(self, item: Tree) -> str:
        if item.data == "func_arg":
            child = self._subtrees(item)
            if child:
                return self._format_expr_compact(child[0])
            if item.children:
                return self._format_expr_compact(item.children[0])
            return ""
        if item.data == "func_kwarg":
            name = self._find_token(item, "ID")
            val = self._subtrees(item)[0]
            return f"{name}={self._format_expr_compact(val)}"
        if item.data == "func_wrapped_kwargs":
            val = self._subtrees(item)[0]
            return f"**{self._format_expr_compact(val)}"
        return self._reconstruct(item)

    # — List / dict expansion —

    def _expand_list_def(self, tree: Tree, indent_level: int) -> str:
        operand_list = self._subtrees(tree)[0]
        items = self._subtrees(operand_list)
        if not items:
            return "[]"

        inner = self._indent_str(indent_level + 1)
        close = self._indent_str(indent_level)
        max_w = self._config.line_length

        lines = ["["]
        prev_end = self._first_line(operand_list)
        for item in items:
            item_start = self._first_line(item)
            item_end = self._last_line(item)
            if prev_end and item_start:
                for c in self._comments.get_orphans(prev_end, item_start):
                    lines.append(f"{inner}{c.text}")
                for c in self._comments.get_leading(item_start):
                    lines.append(f"{inner}{c.text}")
            elem = self._format_expr_compact(item)
            if len(inner) + len(elem) + 1 > max_w:
                expanded = self._try_expand(item, indent_level + 1)
                if expanded is not None:
                    elem = expanded
            tc = ""
            if item_end:
                c = self._comments.get_trailing(item_end)
                if c:
                    tc = f"  {c.text}"
            lines.append(f"{inner}{elem},{tc}")
            prev_end = item_end or prev_end
        lines.append(f"{close}]")
        return "\n".join(lines)

    def _expand_map_def(self, tree: Tree, indent_level: int) -> str:
        pair_list = self._subtrees(tree)[0]
        items = self._subtrees(pair_list)
        if not items:
            return "{}"

        inner = self._indent_str(indent_level + 1)
        close = self._indent_str(indent_level)

        lines = ["{"]
        prev_end = self._first_line(pair_list)
        for item in items:
            item_start = self._first_line(item)
            item_end = self._last_line(item)
            if prev_end and item_start:
                for c in self._comments.get_orphans(prev_end, item_start):
                    lines.append(f"{inner}{c.text}")
                for c in self._comments.get_leading(item_start):
                    lines.append(f"{inner}{c.text}")
            st = self._subtrees(item)
            key = self._format_expr_compact(st[0])
            val = self._format_expr_compact(st[1])
            tc = ""
            if item_end:
                c = self._comments.get_trailing(item_end)
                if c:
                    tc = f"  {c.text}"
            lines.append(f"{inner}{key}: {val},{tc}")
            prev_end = item_end or prev_end
        lines.append(f"{close}" + "}")
        return "\n".join(lines)

    # Parenthesized expression expansion

    def _expand_primary(self, tree: Tree, indent_level: int) -> str:
        """Expand ``(expr)`` with the inner expression on indented continuation lines."""
        inner_trees = self._subtrees(tree)
        if not inner_trees:
            return None
        inner_expr = inner_trees[0]
        inner = self._indent_str(indent_level + 1)
        close = self._indent_str(indent_level)
        # Format the inner expression, potentially splitting it further
        inner_text = self._format_expr_compact(inner_expr)
        # For long inner expressions, try to split on binary operators
        inner_lines = self._split_binary_chain(inner_expr, indent_level + 1)
        if inner_lines:
            lines = ["("]
            lines.extend(inner_lines)
            lines.append(f"{close})")
            return "\n".join(lines)
        # Simple case: just indent the whole expression
        lines = ["(", f"{inner}{inner_text}", f"{close})"]
        return "\n".join(lines)

    def _split_binary_chain(self, node: Tree | Token, indent_level: int) -> list[str] | None:
        """Try to split a chain of binary operators (and/or) into separate lines."""
        if isinstance(node, Token):
            return None
        op_map = {
            "or_expr": "or",
            "and_expr": "and",
        }
        op_word = op_map.get(node.data)
        if not op_word:
            return None
        # Collect all terms in the chain
        terms: list[Tree | Token] = []
        self._collect_binary_chain(node, node.data, terms)
        if len(terms) < 2:
            return None
        indent = self._indent_str(indent_level)
        lines: list[str] = []
        for i, term in enumerate(terms):
            text = self._format_expr_compact(term)
            if i == 0:
                lines.append(f"{indent}{text}")
            else:
                lines.append(f"{indent}{op_word} {text}")
        return lines

    def _collect_binary_chain(self, node: Tree, op_data: str, terms: list) -> None:
        """Recursively collect terms from a left-associative binary operator chain."""
        if isinstance(node, Token) or node.data != op_data:
            terms.append(node)
            return
        subtrees = self._subtrees(node)
        self._collect_binary_chain(subtrees[0], op_data, terms)
        terms.append(subtrees[1])

    # in_expr / not_in_expr expansion

    def _expand_in_expr(self, tree: Tree, indent_level: int) -> str | None:
        """Expand ``x in [long list]`` by expanding the list."""
        subtrees = self._subtrees(tree)
        if len(subtrees) < 2:
            return None
        lhs = self._format_expr_compact(subtrees[0])
        rhs = subtrees[1]
        expanded_rhs = self._try_expand(rhs, indent_level)
        if expanded_rhs is not None:
            return f"{lhs} in {expanded_rhs}"
        return None

    def _expand_not_in_expr(self, tree: Tree, indent_level: int) -> str | None:
        """Expand ``x not in [long list]`` by expanding the list."""
        subtrees = self._subtrees(tree)
        if len(subtrees) < 2:
            return None
        lhs = self._format_expr_compact(subtrees[0])
        rhs = subtrees[1]
        expanded_rhs = self._try_expand(rhs, indent_level)
        if expanded_rhs is not None:
            return f"{lhs} not in {expanded_rhs}"
        return None

    # Fallback reconstruction

    def _reconstruct(self, tree: Tree) -> str:
        parts: list[str] = []
        for c in tree.children:
            if isinstance(c, Token):
                parts.append(str(c))
            else:
                parts.append(self._format_expr(c))
        return " ".join(parts)
