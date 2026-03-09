# Inmanta DSL Parser

This directory contains the parser for the Inmanta DSL (Domain Specific Language).

## Overview

The parser converts `.cf` (Inmanta configuration) source files into an AST (Abstract Syntax
Tree) of statement objects that the compiler then normalizes and executes.

## Files

| File                   | Description                                                                |
| ---------------------- | -------------------------------------------------------------------------- |
| `larkInmanta.lark`     | Lark grammar definition for the Inmanta DSL                                |
| `larkInmantaParser.py` | Lark-based parser and transformer (active parser)                          |
| `cache.py`             | Per-file AST cache manager (`CacheManager`)                                |
| `pickle.py`            | Custom pickler/unpickler for AST objects (handles `Namespace` replacement) |

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

- **Filtered keyword terminals**: Many keyword terminals are renamed with a `_` prefix (e.g.
  `_TYPEDEF`, `_AS`, `_END`) so Lark's contextual lexer auto-filters them from the transformer
  arguments, reducing per-call overhead. The exceptions are `FOR` and `IF`, which are kept
  unfiltered because their token is used as the source position for the enclosing statement.

- **Transparent rules**: Several intermediate grammar rules are marked `?` (e.g. `?statement`,
  `?operand`, `?relation`) so Lark inlines the single child directly without creating a Tree
  node, avoiding unnecessary transformer dispatch.

**Transformer**: `InmantaTransformer` (in `larkInmantaParser.py`) is a Lark `Transformer`
subclass decorated with `@v_args(inline=True)` so every rule callback receives its children as
individual positional arguments. Position information is derived directly from token attributes
(`token.line`, `token.start_pos`) rather than from `propagate_positions`, which avoids the
overhead of Lark annotating every tree node.

The transformer builds a pre-computed dispatch dict at construction time (`_call_dispatch`) by
walking the class MRO and binding `_VArgsWrapper.base_func` methods directly. The overridden
`_call_userfunc` uses this dict for O(1) dispatch, bypassing the per-call `__get__` overhead
from the default Lark implementation.

### Legacy: PLY (removed)

`plyInmantaParser.py` and `plyInmantaLex.py` have been removed. The reserved keyword set
previously provided by `plyInmantaLex.py`'s `reserved` dict is now defined directly in
`larkInmantaParser.py` as `_RESERVED_KEYWORDS_UPPER` (derived from `_RESERVED_KEYWORDS`).
The `ply` pip dependency has been removed from `setup.py`.

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

The parser uses two levels of caching:

**Lark grammar cache** (`attach_to_project` / `detach_from_project` in `larkInmantaParser.py`):
When a project is loaded, `attach_to_project(project_dir)` builds the Lark parser with
`cache=<path>`, pointing to `.cfcache/lark_grammar.cache` inside the project directory. This
caches the compiled LALR parser tables (grammar → state machines) to disk so that repeated
`Lark(...)` constructor calls across processes are fast. Lark handles cache invalidation
automatically via a SHA-256 hash of the grammar content, Lark version, and Python version
embedded in the cache file. `detach_from_project()` resets the parser to uncached mode.

**Per-file AST cache** (`cache.py` / `pickle.py`): Each `.cf` file's parsed AST statements are
cached in `.cfcache/` as versioned `.cfc` files. On subsequent compilations, `CacheManager.un_cache`
checks if the cached file exists and its source file hasn't been modified (mtime comparison). Cache
hits skip parsing entirely. `ASTPickler` uses a `dispatch_table` (C-level type dispatch) to replace
`Namespace` objects with their fully-qualified name during pickling; `ASTUnpickler` restores them
from a thread-local context. The cache is controlled by the `compiler.cache` config option and can
be disabled with `--no-cache`.

## Performance

### Benchmark: juniper-mx v23 (16803 .cf files)

Full `inmanta compile` on a project that includes all files from the juniper-mx v23 module:

| Parser                           | Parsing | Total compile | User wall clock time |
| -------------------------------- | ------- | ------------- | -------------------- |
| PLY with cold cache              | 131.7s  | 146.7s        | 193.5s               |
| PLY with warm cache              | 67.7s   | 84.7s         | 134.5s               |
| Lark without cache               | 125.1s  | 138.7s        | 181.8s               |
| Lark with cold cache             | 154.1s  | 168.7s        | 215.3s               |
| Lark with warm cache             | 48.8s   | 62.4s         | 110.9s               |
| Lark with cold cache + fast exit | 147.8s  | 163.4s        | 156.9s               |
| Lark with warm cache + fast exit | 45.3s   | 58.5s         | 55.5s                |

Lark is **5% faster** than PLY for raw parsing (no cache on either side). With a warm AST cache,
Lark is **28% faster** than PLY with warm cache (48.8s vs 67.7s parsing, 110.9s vs 134.5s total).
Cold cache adds overhead from pickling the AST on the first run, but subsequent runs benefit from
the cached AST. The "fast exit" rows show timings when the process exits immediately after
compilation (avoiding GC teardown overhead on the large AST object graph).

### Optimizations applied

The following optimizations were applied to close the initial 3× gap between Lark and PLY:

| Optimization                     | Effect                                                                 |
| -------------------------------- | ---------------------------------------------------------------------- |
| Transparent rules (`?` prefix)   | Fewer tree nodes to allocate and transform                             |
| Filtered terminals (`_KEYWORD`)  | Keywords auto-removed from transformer args                            |
| Custom `_transform_tree` loop    | Replaces Lark's 4-function dispatch chain with a single recursive loop |
| Pre-built dispatch dict          | O(1) method lookup per rule, bypasses `_VArgsWrapper.__get__`          |
| Friedl-unrolled string regexes   | ~46% faster lexing of STRING/RSTRING/FSTRING                           |
| `propagate_positions` removal    | Positions derived from tokens directly (~2s saving)                    |
| `_lark_parser_default` singleton | Build LALR tables once per process                                     |
| Grammar hash cache filename      | Automatic stale-cache eviction on grammar changes                      |
| `dispatch_table` for pickle      | 10× faster AST serialization (C-level type check)                      |
| `_safe_decode` fast path         | 57× faster string literal decoding (skip backslash-free strings)       |

## Why Lark?

The PLY parser had several limitations:

1. **Maintenance**: PLY is no longer actively maintained and uses a C-extension based lexer
   that is harder to extend and debug.

2. **Grammar readability**: Lark's grammar syntax is more readable and closer to standard BNF,
   making it easier to reason about and modify.

3. **Python ecosystem**: Lark is a pure-Python library with active maintenance and good
   documentation.
