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

import json
from pathlib import Path

import inmanta.compiler as compiler
from inmanta.config import Config
from inmanta.execute.scheduler import ProgressSource

# A model that forces the scheduler to speculate: the two hosts relations feed into each other, so neither
# can be proven complete (each has an outstanding provider promise on the other). The std::count plugin does
# not support gradual execution, so it adds progress potential on hg1.hosts without being able to execute.
# This deadlock is broken by a speculative freeze (find_wait_cycle).
SPECULATING_MODEL = """
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg1 = Hg()
hg2 = Hg()

hg1.hosts = std::Host(name="test1", os=std::unix)
hg1.hosts = hg2.hosts
hg2.hosts = hg1.hosts

n = std::count(hg1.hosts)
"""


def test_speculation_tracing(snippetcompiler, tmp_path: Path) -> None:
    """
    Verify the structure of the speculation log written when the compiler.speculation_log_file option is set.
    """
    log_file: Path = tmp_path / "speculation.json"
    Config.set("compiler", "speculation_log_file", str(log_file))
    snippetcompiler.setup_for_snippet(SPECULATING_MODEL)
    compiler.do_compile()

    records = json.loads(log_file.read_text())
    assert len(records) > 0
    valid_progress_sources = {source.value for source in ProgressSource}
    for record in records:
        assert record["progress_source"] in valid_progress_sources

    freezes = [record["freeze"] for record in records if record["freeze"] is not None]
    assert len(freezes) > 0
    speculative_records = [record for record in records if record["progress_source"] == "find_wait_cycle"]
    assert len(speculative_records) == len(freezes)
    frozen_relations = [freeze["relation"] for freeze in freezes if freeze["relation"] is not None]
    assert any(relation["attribute"] == "__config__::Hg.hosts" for relation in frozen_relations)


def test_speculation_tracing_disabled(snippetcompiler, tmp_path: Path) -> None:
    """
    Verify that no speculation log is written when the compiler.speculation_log_file option is not set.
    """
    log_file: Path = tmp_path / "speculation.json"
    snippetcompiler.setup_for_snippet(SPECULATING_MODEL)
    compiler.do_compile()
    assert not log_file.exists()
