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

import difflib
import os

from inmanta.formatter.comments import extract_comments, extract_fmt_regions
from inmanta.formatter.config import FormatConfig
from inmanta.formatter.cst_printer import CSTPrinter, parse_to_cst


class FormatterError(Exception):
    """Raised when the formatter produces output that changes the AST."""


def format_string(source: str, *, config: FormatConfig | None = None, filename: str = "<stdin>") -> str:
    """Format Inmanta DSL source code and return the formatted result.

    Raises :class:`FormatterError` if formatting would change the AST (safety check).
    """
    if config is None:
        config = FormatConfig()

    if not source or not source.strip():
        return source

    comment_map = extract_comments(source)
    fmt_regions = extract_fmt_regions(source)
    try:
        cst = parse_to_cst(source)
    except Exception as e:
        raise FormatterError(f"cannot parse {filename}: {e}") from e
    printer = CSTPrinter(source, comment_map, config, fmt_regions)
    formatted = printer.format(cst)

    # Safety check: AST equivalence (like Black)
    _assert_ast_equivalent(source, formatted, filename)

    return formatted


def format_file(path: str, *, config: FormatConfig | None = None, write: bool = True) -> tuple[str, bool]:
    """Format a ``.cf`` file.

    Returns ``(formatted_source, changed)``.  If *write* is ``True`` and the file
    changed, the formatted content is written back to *path*.
    """
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    formatted = format_string(source, config=config, filename=path)
    changed = formatted != source

    if changed and write:
        with open(path, "w", encoding="utf-8") as f:
            f.write(formatted)

    return formatted, changed


def check_file(path: str, *, config: FormatConfig | None = None) -> bool:
    """Return ``True`` if *path* is already formatted, ``False`` otherwise."""
    _, changed = format_file(path, config=config, write=False)
    return not changed


def diff_file(path: str, *, config: FormatConfig | None = None) -> str:
    """Return a unified diff of the formatting changes for *path*, or empty string if no changes."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    formatted = format_string(source, config=config, filename=path)
    if formatted == source:
        return ""

    name = os.path.relpath(path)
    return "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )


def _assert_ast_equivalent(original: str, formatted: str, filename: str) -> None:
    """Parse both original and formatted source, compare ASTs structurally.

    This is the core safety guarantee — identical to Black's approach:
    if formatting changes the AST, something is wrong with the formatter.
    """
    # Import AST modules in dependency order to avoid circular import:
    # generator.py -> entity.py -> generator.py cycle.
    import inmanta.ast.entity  # noqa: F401 — resolve circular import
    from inmanta.ast import Namespace
    from inmanta.parser.lark_parser import base_parse

    ns_orig = Namespace("__config__")
    ns_fmt = Namespace("__config__")

    try:
        ast_orig = base_parse(ns_orig, filename, original)
    except Exception:
        # If the original doesn't parse, we can't compare — just return
        return

    try:
        ast_fmt = base_parse(ns_fmt, filename, formatted)
    except Exception as e:
        raise FormatterError(
            f"Formatted output does not parse: {e}\n"
            f"This is a bug in the formatter. Original file: {filename}"
        ) from e

    # Structural comparison: compare the string representations of both ASTs.
    # This ignores source positions (which change after formatting) but catches
    # any semantic differences.
    orig_repr = _ast_repr(ast_orig)
    fmt_repr = _ast_repr(ast_fmt)

    if orig_repr != fmt_repr:
        raise FormatterError(
            f"Formatting changed the AST for {filename}.\n"
            f"This is a bug in the formatter.\n"
            f"Original AST:\n{orig_repr[:500]}\n"
            f"Formatted AST:\n{fmt_repr[:500]}"
        )


def _ast_repr(statements: list) -> str:
    """Generate a position-independent representation of an AST for comparison."""
    parts: list[str] = []
    for stmt in statements:
        parts.append(_stmt_repr(stmt))
    return "\n".join(parts)


def _stmt_repr(node: object) -> str:
    """Recursively represent an AST node, ignoring source positions."""
    if node is None:
        return "None"
    if isinstance(node, (str, int, float, bool)):
        return repr(node)
    if isinstance(node, list):
        return f"[{', '.join(_stmt_repr(item) for item in node)}]"
    if isinstance(node, tuple):
        return f"({', '.join(_stmt_repr(item) for item in node)})"

    # Skip Location and Range objects entirely — formatting changes positions
    from inmanta.ast import Location

    if isinstance(node, Location):
        return "Location(...)"

    cls_name = type(node).__name__

    # Collect attribute names from __slots__ (AST nodes use slots) and __dict__
    # Skip all position/location-related fields — formatting changes line numbers
    skip = {
        "location", "namespace", "lexpos", "lnr", "elnr", "start", "end",
        "start_pos", "end_pos", "entity_location",
    }
    attr_names: list[str] = []
    for cls in type(node).__mro__:
        for name in getattr(cls, "__slots__", ()):
            if not name.startswith("_") and name not in skip and name not in attr_names:
                attr_names.append(name)
    if hasattr(node, "__dict__"):
        for name in node.__dict__:
            if not name.startswith("_") and name not in skip and name not in attr_names:
                attr_names.append(name)

    attr_names.sort()
    attrs: dict[str, str] = {}
    for key in attr_names:
        try:
            val = getattr(node, key)
        except AttributeError:
            continue
        if callable(val):
            continue
        attrs[key] = _stmt_repr(val)

    if attrs:
        attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
        return f"{cls_name}({attr_str})"
    return cls_name
