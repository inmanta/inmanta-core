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

import subprocess
import sys

# Packages a compile must not load. Each one was taken off the import path deliberately, and each is cheap to put back by
# accident, because a single module scope import anywhere in the reachable graph is enough.
#
# inmanta.data                the database access layer, which drags sqlalchemy and the DAO with it
# sqlalchemy                  only reachable through inmanta.data
# inmanta.agent.agent_new     the scheduler entry point, which reaches inmanta.data
# inmanta.server.bootloader   the server, which reaches inmanta.data through server.extensions
# strawberry                  a graphql annotation in inmanta/graphql/result.py used to pull this in
# cookiecutter                only used by the project and module scaffolding commands
FORBIDDEN_ON_COMPILE_PATH = (
    "inmanta.data",
    "sqlalchemy",
    "inmanta.agent.agent_new",
    "inmanta.server.bootloader",
    "strawberry",
    "cookiecutter",
)

DUMP_LOADED_MODULES = "import sys; import inmanta.app; print('\\n'.join(sys.modules))"


def test_compile_path_does_not_load_the_database_or_the_server() -> None:
    """
    Importing the CLI entry point must not load the database access layer, the server or the scheduler.

    A compile needs none of them, but they sit one module scope import away: the compiler imports the protocol layer for
    Context.get_client(), and the handler API for the Commander registry. Both used to reach inmanta.data.

    Run in a subprocess, because by the time this test executes the pytest process has imported most of the code base.
    """
    result = subprocess.run(
        [sys.executable, "-c", DUMP_LOADED_MODULES],
        capture_output=True,
        text=True,
        check=True,
    )
    loaded: set[str] = set(result.stdout.split())
    assert "inmanta.app" in loaded, f"the subprocess did not import inmanta.app: {result.stderr}"

    found = [
        package
        for package in FORBIDDEN_ON_COMPILE_PATH
        if any(module == package or module.startswith(f"{package}.") for module in loaded)
    ]
    assert not found, (
        f"{', '.join(found)} is loaded by importing inmanta.app."
        " Something gained a module scope import of it; move that import into the function that needs it,"
        f" or under TYPE_CHECKING if it is only an annotation. See {__file__} for why each entry is listed."
    )
