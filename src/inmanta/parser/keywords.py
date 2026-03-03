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

Canonical list of reserved keywords in the Inmanta DSL.

Kept in a separate lightweight module so it can be imported without pulling in
the full parser or AST infrastructure (avoids circular-import issues).
"""

from collections.abc import Sequence

RESERVED_KEYWORDS: Sequence[str] = [
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
