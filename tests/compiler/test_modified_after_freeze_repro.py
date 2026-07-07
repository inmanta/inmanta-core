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

import typing

import inmanta.compiler as compiler

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
# The choice is order-sensitive, not semantic: moving the registry/if statements in
# front of the tunnel/rule_count statements flips the waitqueue order and the exact
# same model compiles successfully.
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


def test_freeze_order_with_plugin_consumers(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    A valid freeze order exists for this model (Registry.sources before Host.rules), so it should compile.

    Currently fails with List modified after freeze because the scheduler freezes Host.rules first,
    see the comment on MODEL_PLUGIN_CONSUMERS.
    """
    snippetcompiler.setup_for_snippet(MODEL_PLUGIN_CONSUMERS, autostd=True)
    types, _ = compiler.do_compile()
    host = types["__config__::Host"].get_all_instances()[0]
    rules = host.get_attribute("rules").get_value()
    assert sorted(rule.get_attribute("name").get_value() for rule in rules) == ["one", "static", "two"]


def test_freeze_order_gradual_consumers_only(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Control for test_freeze_order_with_plugin_consumers: the same model compiles when the relation is
    assigned directly instead of being consumed by plugins. Relation assignment is a gradual union, so
    it does not give host.rules progress potential and the scheduler freezes it last, after the App
    instances have contributed their rules.
    """
    model: str = MODEL_PLUGIN_CONSUMERS.replace(
        'tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))\nrule_count = std::count(host.rules)',
        "tunnel = Tunnel(ingress=host.rules)",
    )
    assert "key_sort" not in model  # guard the replace against model refactoring
    snippetcompiler.setup_for_snippet(model, autostd=True)
    compiler.do_compile()
