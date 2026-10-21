"""
Copyright 2017 Inmanta

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

from importlib.resources import files


def _read_opa_version() -> str:
    """
    Read the OPA version from the FROM line of protocol/auth/Dockerfile, which Dependabot keeps up to date.
    """
    # files(__name__) avoids importing inmanta.protocol, which would be a circular import here
    dockerfile = files(__name__) / "protocol" / "auth" / "Dockerfile"
    try:
        content = dockerfile.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Unable to read the OPA version from {dockerfile}: {e}") from e
    for line in content.splitlines():
        if line.strip().upper().startswith("FROM "):
            version = line.rsplit(":", maxsplit=1)[-1].strip()
            if ":" in line and version:
                return version
            break
    raise RuntimeError(
        f"Unable to parse the OPA version from {dockerfile}: expected a line 'FROM openpolicyagent/opa:<version>'"
    )


OPA_VERSION: str = _read_opa_version()
# This version is managed by bumpversion. Should you ever update it manually, make sure to consistently update it everywhere
# (See the bumpversion.cfg file for relevant locations).
__version__ = "18.4.1"

RUNNING_TESTS = False
"""
    This is enabled/disabled by the test suite when tests are run.
    This variable is used to disable certain features that shouldn't run during tests.
"""

if __name__ == "__main__":
    import inmanta.app

    inmanta.app.app()
