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
import logging
import os
import typing

import pytest

import inmanta.compiler as compiler
from inmanta.ast import CompilerException, ModifiedAfterFreezeException
from inmanta.module import RelationPrecedenceRule
from utils import log_contains, log_doesnt_contain

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest


# Host.rules receives contributions from a top-level statement and from the app_rule
# implementation of the App instances. The App instances are only constructed once
# Registry.sources is frozen (std::count over it gates the if statement). The plugin calls
# over host.rules (std::key_sort and std::count) are non-gradual waiters, so they give
# host.rules progress potential (ListVariable.get_progress_potential).
#
# When the scheduler runs out of executable statements, both Host.rules and
# Registry.sources are freeze candidates: zero waiting providers, positive progress
# potential. Freezing Registry.sources first completes the model: it unblocks the if
# statement, which constructs the Apps that provide the remaining Host.rules entries.
# But Scheduler.run freezes greedily in waitqueue order (FIFO for relations without
# precedence rules, see PrioritisedDelayedResultVariableQueue) and Host.rules is queued
# first, so it is frozen before the Apps exist and their contributions fail with
# List modified after freeze. Progress potential is purely local: the scheduler does
# not consider that freezing one candidate can add providers to another.
#
# The compile as a whole still succeeds: do_compile detects the modified-after-freeze
# failure and recompiles with Host.rules frozen as late as possible.
MODEL_PLUGIN_CONSUMERS: str = """
entity Host: end
entity Rule:
    string name
end
entity Tunnel: end
entity Source:
    string name
end
entity Registry: end
entity App:
    string name
end

Host.rules [0:] -- Rule
Tunnel.ingress [0:] -- Rule
Registry.sources [0:] -- Source
App.host [1] -- Host.apps [0:]

implementation app_rule for App:
    self.host.rules += Rule(name=self.name)
end

implement Host using std::none
implement Rule using std::none
implement Tunnel using std::none
implement Source using std::none
implement Registry using std::none
implement App using app_rule

host = Host()
host.rules += Rule(name="static")

# Non-gradual consumers: plugin calls give host.rules progress potential and put it
# in the waitqueue before Registry.sources.
tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))
rule_count = std::count(host.rules)

registry = Registry()
registry.sources += Source(name="one")
registry.sources += Source(name="two")

# Apps (which each contribute a rule) are only created once registry.sources
# is complete: std::count is a plugin, so it waits for the frozen list.
if std::count(registry.sources) > 0:
    App(host=host, name="one")
    App(host=host, name="two")
end
"""


# Every freeze order fails for this model: freezing either list unblocks the if statement
# that contributes to the other list, which at that point is either already frozen or
# freezes before the contribution arrives, closing the cycle in the other direction.
MODEL_FREEZE_ORDER_CYCLE: str = """
entity A: end
entity Item:
    string name
end

A.alist [0:] -- Item
A.blist [0:] -- Item

implement A using std::none
implement Item using std::none

a = A()
a.alist += Item(name="seed_a")
a.blist += Item(name="seed_b")

if std::count(a.alist) > 0:
    a.blist += Item(name="from_a")
end

if std::count(a.blist) > 0:
    a.alist += Item(name="from_b")
end
"""


def test_freeze_order_with_plugin_consumers(
    snippetcompiler: "SnippetCompilationTest", caplog: pytest.LogCaptureFixture
) -> None:
    """
    Verify that a model that has a valid freeze order (Registry.sources before Host.rules) compiles even though
    the scheduler's greedy freeze choice picks Host.rules first: the compile is retried with Host.rules frozen
    as late as possible, see the comment on MODEL_PLUGIN_CONSUMERS.
    """
    snippetcompiler.setup_for_snippet(MODEL_PLUGIN_CONSUMERS, autostd=True)
    with caplog.at_level(logging.WARNING):
        types, _ = compiler.do_compile()
    host = types["__config__::Host"].get_all_instances()[0]
    rules = host.get_attribute("rules").get_value()
    assert sorted(rule.get_attribute("name").get_value() for rule in rules) == ["one", "static", "two"]
    # the model compiled through the recovery path, not by a lucky freeze order
    log_contains(
        caplog,
        "inmanta.compiler",
        logging.WARNING,
        "relations were frozen before all their contributions were known: __config__::Host.rules",
    )


def test_freeze_order_gradual_consumers_only(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Control for test_freeze_order_with_plugin_consumers: the same model compiles in a single attempt when the
    relation is assigned directly instead of being consumed by plugins. Relation assignment is a gradual union,
    so it does not give host.rules progress potential and the scheduler freezes it last, after the App instances
    have contributed their rules.
    """
    model: str = MODEL_PLUGIN_CONSUMERS.replace(
        'tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))\nrule_count = std::count(host.rules)',
        "tunnel = Tunnel(ingress=host.rules)",
    )
    assert "key_sort" not in model  # guard the replace against model refactoring
    snippetcompiler.setup_for_snippet(model, autostd=True)
    compiler.do_compile()


def test_freeze_order_hints_cached_across_compiles(
    snippetcompiler: "SnippetCompilationTest", caplog: pytest.LogCaptureFixture
) -> None:
    """
    Verify that the relations learned by the retry are cached in the project's cf cache directory and that a
    subsequent compile seeds the freeze order from that cache, compiling the model in a single attempt.
    """
    project = snippetcompiler.setup_for_snippet(MODEL_PLUGIN_CONSUMERS, autostd=True)
    with caplog.at_level(logging.WARNING):
        compiler.do_compile()
    log_contains(caplog, "inmanta.compiler", logging.WARNING, "relations were frozen before all their contributions")
    with open(compiler._freeze_order_hints_cache_path(project), encoding="utf-8") as fh:
        assert json.load(fh) == [["__config__::Host", "rules"]]

    caplog.clear()
    project.invalidate_state()
    with caplog.at_level(logging.WARNING):
        types, _ = compiler.do_compile()
    log_doesnt_contain(caplog, "inmanta.compiler", logging.WARNING, "relations were frozen before all their contributions")
    host = types["__config__::Host"].get_all_instances()[0]
    assert len(host.get_attribute("rules").get_value()) == 3


def test_freeze_order_hints_cache_pruned(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Verify that cached freeze-order hints that no longer resolve to a relation of the model are dropped from the
    cache by a successful compile.
    """
    model: str = MODEL_PLUGIN_CONSUMERS.replace(
        'tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))\nrule_count = std::count(host.rules)',
        "tunnel = Tunnel(ingress=host.rules)",
    )
    project = snippetcompiler.setup_for_snippet(model, autostd=True)
    cache_path: str = compiler._freeze_order_hints_cache_path(project)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump([["__config__::DoesNotExist", "rules"], ["__config__::Host", "gone"]], fh)
    compiler.do_compile()
    with open(cache_path, encoding="utf-8") as fh:
        assert json.load(fh) == []


def test_freeze_order_hint_defers_to_precedence_policy(
    snippetcompiler: "SnippetCompilationTest", caplog: pytest.LogCaptureFixture
) -> None:
    """
    Verify that a relation with an explicit relation precedence rule is scheduled by that rule, even when a
    cached freeze-order hint names the same relation: the rule already freezes it in a valid order, so the
    model compiles in a single attempt.
    """
    project = snippetcompiler.setup_for_snippet(
        MODEL_PLUGIN_CONSUMERS,
        autostd=True,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::Registry",
                first_relation_name="sources",
                then_type="__config__::Host",
                then_relation_name="rules",
            )
        ],
    )
    cache_path: str = compiler._freeze_order_hints_cache_path(project)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump([["__config__::Host", "rules"]], fh)
    with caplog.at_level(logging.WARNING):
        compiler.do_compile()
    log_doesnt_contain(caplog, "inmanta.compiler", logging.WARNING, "relations were frozen before all their contributions")


def test_freeze_order_retry_calls_finalizers_once(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Verify that a finalizer is called exactly once when the compile is retried: the finalizers of a
    discarded attempt must not survive into, and be called again by, later attempts.
    """
    calls: list[int] = []
    compiler.Finalizers.add_function(lambda: calls.append(1))
    snippetcompiler.setup_for_snippet(MODEL_PLUGIN_CONSUMERS, autostd=True)
    compiler.do_compile()
    assert len(calls) == 1


def test_freeze_order_cycle_still_fails(snippetcompiler: "SnippetCompilationTest", caplog: pytest.LogCaptureFixture) -> None:
    """
    Verify that a model without any valid freeze order still fails with the modified-after-freeze error: the
    retry mechanism gives up after the first compile attempt that does not learn any new relation to freeze
    late, plus the single allowed retry without progress.
    """
    snippetcompiler.setup_for_snippet(MODEL_FREEZE_ORDER_CYCLE, autostd=True)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(CompilerException) as exc_info:
            compiler.do_compile()
    assert len([record for record in caplog.records if "Retrying one more time" in record.message]) == 1
    exceptions: list[CompilerException] = [exc_info.value]
    freeze_exceptions: list[ModifiedAfterFreezeException] = []
    while exceptions:
        current = exceptions.pop()
        if isinstance(current, ModifiedAfterFreezeException):
            freeze_exceptions.append(current)
        exceptions.extend(current.get_causes())
    assert freeze_exceptions, f"Expected a ModifiedAfterFreezeException, got {exc_info.value.format_trace()}"
    assert "List modified after freeze" in freeze_exceptions[0].get_message()
