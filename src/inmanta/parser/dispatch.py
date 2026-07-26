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

Parser backend dispatch.

Reads the INMANTA_PARSER environment variable (default: "ply") and re-exports
the public API from the selected backend. All consumers should import from
this module rather than directly from lark_parser or plyInmantaParser.
"""

import os
from typing import NoReturn, Optional

from inmanta.ast import Namespace
from inmanta.ast.statements import Statement

__all__ = ["active_backend", "attach_to_project", "base_parse", "cache_manager", "detach_from_project", "parse"]

_VALID_BACKENDS: tuple[str, ...] = ("ply", "lark")

# Resolve the backend once, at import time. An unset or empty value means the default.
_PARSER_BACKEND: str = (os.environ.get("INMANTA_PARSER") or "ply").lower()


def _unknown_backend_error(backend: str) -> ValueError:
    return ValueError(f"Unknown parser backend: {backend!r} (set INMANTA_PARSER to 'ply' or 'lark')")


def active_backend() -> str:
    """Return the resolved parser backend name ('ply' or 'lark'). Raises for an invalid value."""
    if _PARSER_BACKEND not in _VALID_BACKENDS:
        raise _unknown_backend_error(_PARSER_BACKEND)
    return _PARSER_BACKEND


if _PARSER_BACKEND == "lark":
    from inmanta.parser.lark_parser import (  # noqa: F401
        attach_to_project,
        base_parse,
        cache_manager,
        detach_from_project,
        parse,
    )
elif _PARSER_BACKEND == "ply":
    from inmanta.parser.plyInmantaParser import base_parse, cache_manager, parse  # noqa: F401

    def attach_to_project(project_dir: str) -> None:
        cache_manager.attach_to_project(project_dir)

    def detach_from_project() -> None:
        cache_manager.detach_from_project()

else:
    # Unknown backend value: do not crash at import time, which would break commands that
    # never parse (e.g. `inmanta --help`). Bind the public API to stubs that raise a clear
    # error only when the parser is actually used.
    from inmanta.parser.cache import CacheManager

    def _raise_unknown_backend() -> NoReturn:
        raise _unknown_backend_error(_PARSER_BACKEND)

    def parse(namespace: Namespace, filename: str, content: Optional[str] = None) -> list[Statement]:
        _raise_unknown_backend()

    def base_parse(ns: Namespace, tfile: str, content: Optional[str]) -> list[Statement]:
        _raise_unknown_backend()

    def attach_to_project(project_dir: str) -> None:
        _raise_unknown_backend()

    def detach_from_project() -> None:
        _raise_unknown_backend()

    # Never reached (parse/attach raise first); bound only so importing dispatch stays cheap.
    cache_manager = CacheManager(_PARSER_BACKEND)
