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

_PARSER_BACKEND: str = os.environ.get("INMANTA_PARSER", "ply").lower()

if _PARSER_BACKEND == "lark":
    from inmanta.parser.lark_parser import (  # noqa: F401
        attach_to_project,
        base_parse,
        cache_manager,
        detach_from_project,
        parse,
    )
elif _PARSER_BACKEND == "ply":
    from inmanta.parser.plyInmantaParser import (  # noqa: F401
        base_parse,
        cache_manager,
        parse,
    )

    def attach_to_project(project_dir: str) -> None:
        cache_manager.attach_to_project(project_dir)

    def detach_from_project() -> None:
        cache_manager.detach_from_project()

else:
    raise ValueError(f"Unknown parser backend: {_PARSER_BACKEND!r} (set INMANTA_PARSER to 'ply' or 'lark')")
