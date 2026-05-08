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
from dataclasses import dataclass, field, fields

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


# Mapping from pyproject.toml key (kebab-case) to FormatConfig field (snake_case)
_TOML_KEY_MAP: dict[str, str] = {}


@dataclass(frozen=True)
class FormatConfig:
    """Configuration for the Inmanta DSL formatter.

    All settings can be specified in ``pyproject.toml`` under ``[tool.inmanta-format]``.
    Boolean rules can be disabled by setting them to ``false``.
    """


    line_length: int = 120
    indent_width: int = 4


    blank_lines_between_top_level: int = 2
    blank_lines_after_imports: int = 2

    # Spacing rules (disable with false)
    normalize_quotes: bool = True
    magic_trailing_comma: bool = True
    trailing_comma_in_expansion: bool = True
    spaces_around_assignment: bool = True
    no_spaces_in_kwarg: bool = True
    no_spaces_in_default: bool = True
    spaces_around_binary_op: bool = True
    space_after_comma: bool = True

    # Entity formatting
    group_annotations: bool = True

    @staticmethod
    def from_pyproject(path: str | None = None) -> "FormatConfig":
        """Load configuration from ``pyproject.toml``.

        Searches the current directory and parent directories for ``pyproject.toml``
        if *path* is not given.  Returns default config if no file is found.
        """
        if path is None:
            path = _find_pyproject()
        if path is None:
            return FormatConfig()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        section = data.get("tool", {}).get("inmanta-format", {})
        if not section:
            return FormatConfig()

        kwargs: dict[str, object] = {}
        for f_info in fields(FormatConfig):
            toml_key = f_info.name.replace("_", "-")
            if toml_key in section:
                kwargs[f_info.name] = section[toml_key]
        return FormatConfig(**kwargs)


def _find_pyproject() -> str | None:
    """Search current directory and parents for ``pyproject.toml``."""
    current = os.getcwd()
    while True:
        candidate = os.path.join(current, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
