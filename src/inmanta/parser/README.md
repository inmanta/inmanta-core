# Inmanta DSL Parser

This directory contains the parser for the Inmanta DSL (Domain Specific Language).

## Overview

The parser converts `.cf` (Inmanta configuration) source files into an AST (Abstract Syntax
Tree) of statement objects that the compiler then normalizes and executes.

## Files

| File | Description |
|---|---|
| `larkInmanta.lark` | Lark grammar definition for the Inmanta DSL |
| `larkInmantaParser.py` | Lark-based parser and transformer (active parser) |
| `plyInmantaParser.py` | Legacy PLY-based parser (delegates to Lark at runtime) |
| `plyInmantaLex.py` | PLY lexer (still used for the `reserved` keyword map) |
| `cache.py` | Parse result caching (avoids re-parsing unchanged files) |
| `pickle.py` | Pickle-based cache serialization |

## Architecture

### Active Parser: Lark

The active parser is implemented using [Lark](https://lark-parser.readthedocs.io/), a Python
parsing library. It uses an LALR(1) parser with a contextual lexer.

**Entry point**: `larkInmantaParser.parse(namespace, filename, content)` returns a list of
`Statement` AST nodes.

**Grammar**: `larkInmanta.lark` defines the full Inmanta DSL grammar. Key design decisions:

- **Keyword terminals use regex with negative lookahead** (`/in(?![a-zA-Z0-9_-])/`). Inmanta
  identifiers can contain hyphens, so `"in"` as a plain string literal would incorrectly match
  the prefix of identifiers like `int_value` or `index`. The `(?![a-zA-Z0-9_-])` lookahead
  prevents this.

- **Named operator terminals** (`MUL_OP`, `MOD_OP`, `DIVISION_OP`, etc.). Anonymous inline
  string literals (`"*"`, `"%"`) are filtered from Lark transformer items, but we need the
  token present in the transformer to build the correct binary operator. Named terminals are
  retained.

- **`stmt_list` reversal**: The PLY grammar rule `stmt_list : statement stmt_list` is
  right-recursive and produces statements in **reverse** source order (the first statement in
  source ends up last in the list). The Lark transformer mirrors this with
  `list(reversed(items))` to preserve execution ordering semantics that the compiler relies on.

- **`map_lookup` covers `attr_ref`**: `t.a["key"]` is a map lookup, not an index lookup.
  The grammar has an explicit `attr_ref "[" operand "]"` alternative in `map_lookup`.

**Transformer**: `InmantaTransformer` (in `larkInmantaParser.py`) is a Lark `Transformer`
subclass. Each grammar rule has a corresponding method that builds the AST node. Position
information (`propagate_positions=True`) is used to set `location` on every AST node so that
error messages reference the correct source file/line/column.

### Legacy: PLY

`plyInmantaParser.py` and `plyInmantaLex.py` contain the original PLY-based parser. At
runtime, `plyInmantaParser.py` re-exports `cache_manager` from `larkInmantaParser` so that
existing code importing `plyInmantaParser.cache_manager` sees the correct statistics.

`plyInmantaLex.py` is still used at runtime for the `reserved` keyword dictionary, which maps
keyword strings (e.g. `"in"`) to their token type names (e.g. `"IN"`). This mapping is used by
the Lark error converter to produce user-friendly error messages like "invalid identifier,
`index` is a reserved keyword".

## Error Handling

Parse errors from Lark (`UnexpectedToken`, `UnexpectedCharacters`, `UnexpectedEOF`) are
converted to `ParserException` by `_convert_lark_error`. This function inspects Lark's parser
state (via `UnexpectedToken.state.value_stack`) to produce error messages that match the PLY
parser's output:

- **Reserved keyword used as identifier** (`index = ""`): detects a keyword token on top of
  the value stack and reports "invalid identifier, `<kw>` is a reserved keyword".

- **Lowercase entity name in `extends`** (`entity Test extends test:`): detects the pattern
  `EXTENDS ... ns_ref COLON` on the value stack and reports "Invalid identifier: Entity names
  must start with a capital".

## Caching

`CacheManager` (in `cache.py`) caches parsed AST lists keyed by `(namespace, filename)`.
The cache avoids re-parsing files that have not changed between compilation runs within the
same process lifetime.

## Why Lark?

The PLY parser had several limitations:

1. **Maintenance**: PLY is no longer actively maintained and uses a C-extension based lexer
   that is harder to extend and debug.

2. **Grammar readability**: Lark's grammar syntax is more readable and closer to standard BNF,
   making it easier to reason about and modify.

3. **Error recovery**: Lark's contextual lexer provides better token disambiguation and
   `propagate_positions=True` gives accurate source positions for all tree nodes without
   needing manual position tracking in every grammar rule.

4. **Python ecosystem**: Lark is a pure-Python library with active maintenance and good
   documentation.
