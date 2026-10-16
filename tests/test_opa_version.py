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
import re

import inmanta


def test_opa_version_matches_dockerfile() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", inmanta.OPA_VERSION)
    dockerfile = os.path.join(os.path.dirname(inmanta.__file__), "protocol", "auth", "Dockerfile")
    with open(dockerfile) as fh:
        assert fh.read().strip() == f"FROM openpolicyagent/opa:{inmanta.OPA_VERSION}"
