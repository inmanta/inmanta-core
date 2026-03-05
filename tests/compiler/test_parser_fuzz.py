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

Property-based fuzz tests for the Inmanta DSL parser.

Uses Hypothesis with the Lark grammar to generate syntactically valid and
corrupted programs, verifying the parser never crashes unexpectedly.

Example count is controlled via Hypothesis profiles registered in conftest.py:
  --fast: 200 examples per test
  default: 10000 examples per test
"""

import os

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.extra.lark import from_lark
from lark import Lark

from inmanta.ast import CompilerException, Namespace
from inmanta.parser import ParserException
from inmanta.parser.larkInmantaParser import base_parse

# Build a Lark instance from the grammar file for Hypothesis.
# This must be a fresh Lark (not the serialised singleton) because
# from_lark() needs access to the grammar rules.
_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), "../../src/inmanta/parser/larkInmanta.lark")
with open(_GRAMMAR_PATH) as _f:
    _fuzz_parser = Lark(_f.read(), parser="lalr", start="start")

_program_strategy = from_lark(_fuzz_parser)


def _make_namespace() -> Namespace:
    root = Namespace("__root__")
    ns = Namespace("__config__")
    ns.parent = root
    return ns


@given(program=_program_strategy)
@settings(deadline=5000, suppress_health_check=[HealthCheck.too_slow])
def test_valid_program_never_crashes(program: str) -> None:
    """Any syntactically valid program generated from the grammar should
    parse without raising an unhandled exception. ParserException and
    CompilerException are acceptable (Hypothesis may generate token
    sequences that are valid per the grammar but rejected by the
    transformer's semantic checks, e.g. hyphens in identifiers).
    """
    ns = _make_namespace()
    try:
        base_parse(ns, "fuzz.cf", program)
    except (ParserException, CompilerException):
        pass  # semantic rejection is fine


@given(
    program=_program_strategy,
    pos=st.integers(min_value=0),
    char=st.text(min_size=1, max_size=1),
)
@settings(deadline=5000, suppress_health_check=[HealthCheck.too_slow])
def test_corrupted_program_raises_clean_error(program: str, pos: int, char: str) -> None:
    """Inserting a random character into a valid program should either
    parse successfully (the corruption happened to be valid) or raise
    a clean ParserException/CompilerException — never an unhandled
    AttributeError, KeyError, IndexError, etc.
    """
    pos = pos % (len(program) + 1)
    corrupted = program[:pos] + char + program[pos:]
    ns = _make_namespace()
    try:
        base_parse(ns, "fuzz.cf", corrupted)
    except (ParserException, CompilerException):
        pass  # expected
