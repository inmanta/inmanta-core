"""
Copyright 2025 Inmanta

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

Backwards-compatibility shim.

The PLY-based lexer (plyInmantaLex) has been removed in favour of the Lark-based parser.
This module exists solely to preserve the public API that external code may import, in
particular ``keyworldlist`` and ``reserved``.
"""

# The canonical list of reserved keywords in the Inmanta DSL.  Kept in sync with the
# Lark grammar (larkInmanta.lark) and _RESERVED_KEYWORDS in larkInmantaParser.py.
keyworldlist: list[str] = [
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

# Map keyword → upper-case token name, mirroring the PLY lexer's ``reserved`` dict.
reserved: dict[str, str] = {k: k.upper() for k in keyworldlist}
