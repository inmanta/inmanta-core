"""
Copyright 2019 Inmanta

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

import pytest

from inmanta import compiler
from inmanta.ast import AttributeException
from inmanta.compiler.help.explainer import ExplainerFactory
from inmanta.module import RelationPrecedenceRule


def test_optional_loop_forward(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Thing:
    string name
end

implement Thing using none

Thing.other [0:1] -- Thing

implementation setother for Thing:
    self.other = Thing(name="it")
end

implement Thing using setother when not (other is defined)

Thing(name="a")

implementation none for Thing:
end
""")
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    assert ExplainerFactory().explain_and_format(e.value) == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:16) would never get a value assigned, but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was assigned at %(dir)s/main.cf:11

Why the compiler made this guess

The compiler considered __config__::Thing.other complete because no statement was known yet that would still assign it, while the following statement needed it complete:
  - other is defined (%(dir)s/main.cf:14)

The value was assigned by self.other = Thing(name='it') (%(dir)s/main.cf:11) in implementation setother of __config__::Thing, for __config__::Thing (instantiated at %(dir)s/main.cf:16). That statement was only scheduled afterwards, because it depends on:
  implement __config__::Thing using setother when (not other is defined) (%(dir)s/main.cf:14)
      which needs relation other of the same instance to be complete

The model is incorrect: the assignment is conditional on the relation it assigns to, so the relation can not be complete without the value and receive the value at the same time. Decide on a boolean attribute instead, or assign the relation unconditionally.
""" % {"dir": snippetcompiler.project_dir}  # noqa: E501


def test_optional_loop_forward_tty(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Thing:
    string name
end

implement Thing using none

Thing.other [0:1] -- Thing

implementation setother for Thing:
    self.other = Thing(name="it")
end

implement Thing using setother when not (other is defined)

Thing(name="a")

implementation none for Thing:
end
""")
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    value = ExplainerFactory().explain_and_format(e.value, plain=False)

    assert value == """
\033[1mException explanation
=====================\033[0m
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation '\033[4mother\033[0m' on the instance \033[4m__config__::Thing (instantiated at %(dir)s/main.cf:16)\033[0m would never get a value assigned, but the value \033[4m__config__::Thing (instantiated at %(dir)s/main.cf:11)\033[0m was assigned at \033[4m%(dir)s/main.cf:11\033[0m

\033[1mWhy the compiler made this guess\033[0m

The compiler considered \033[4m__config__::Thing.other\033[0m complete because no statement was known yet that would still assign it, while the following statement needed it complete:
  - other is defined (%(dir)s/main.cf:14)

The value was assigned by self.other = Thing(name='it') (%(dir)s/main.cf:11) in implementation setother of __config__::Thing, for __config__::Thing (instantiated at %(dir)s/main.cf:16). That statement was only scheduled afterwards, because it depends on:
  implement __config__::Thing using setother when (not other is defined) (%(dir)s/main.cf:14)
      which needs relation other of the same instance to be complete

The model is incorrect: the assignment is conditional on the relation it assigns to, so the relation can not be complete without the value and receive the value at the same time. Decide on a boolean attribute instead, or assign the relation unconditionally.
""" % {"dir": snippetcompiler.project_dir}  # noqa: E501


def test_optional_loop_reverse(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Thing:
    string name
end

implement Thing using none

Thing.other [0:1] -- Thing.that [0:]

implementation setother for Thing:
    t = Thing(name="it")
    t.that = self
end

implement Thing using setother when not (other is defined)

Thing(name="a")

implementation none for Thing:
end
""")
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    assert ExplainerFactory().explain_and_format(e.value) == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:17) would never get a value assigned, but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was assigned at %(dir)s/main.cf:12:14

Why the compiler made this guess

The compiler considered __config__::Thing.other complete because no statement was known yet that would still assign it, while the following statement needed it complete:
  - other is defined (%(dir)s/main.cf:15)

The value was assigned by t.that = self (%(dir)s/main.cf:12) in implementation setother of __config__::Thing, for __config__::Thing (instantiated at %(dir)s/main.cf:17). That statement was only scheduled afterwards, because it depends on:
  implement __config__::Thing using setother when (not other is defined) (%(dir)s/main.cf:15)
      which needs relation other of the same instance to be complete

The model is incorrect: the assignment is conditional on the relation it assigns to, so the relation can not be complete without the value and receive the value at the same time. Decide on a boolean attribute instead, or assign the relation unconditionally.
""" % {"dir": snippetcompiler.project_dir}  # noqa: E501


def test_optional_loop_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Thing:
    string name
end

implement Thing using std::none

Thing.other [0:] -- Thing.that [0:]

implementation setother for Thing:
    t = Thing(name="it")
    t.that = self
end

implement Thing using setother when std::count(other) == 1

t = Thing(name="a")
t.other = Thing(name="b")
""",
        autostd=True,
    )
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    print(ExplainerFactory().explain_and_format(e.value))
    assert ExplainerFactory().explain_and_format(e.value) == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects a relation to have all its elements.
In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:17) would be complete with the values [__config__::Thing (instantiated at %(dir)s/main.cf:18)], but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was added at %(dir)s/main.cf:12:14

Why the compiler made this guess

The compiler considered __config__::Thing.other complete because no statement was known yet that would still add values to it, while the following statement needed it complete:
  - std::count(other) (%(dir)s/main.cf:15)

The value was added by t.that = self (%(dir)s/main.cf:12) in implementation setother of __config__::Thing, for __config__::Thing (instantiated at %(dir)s/main.cf:17). That statement was only scheduled afterwards, because it depends on:
  implement __config__::Thing using setother when (std::count(other) == 1) (%(dir)s/main.cf:15)
      which needs relation other of the same instance to be complete

The model is incorrect: the statement is conditional on the relation it adds values to, so the relation can not be complete without the value and receive the value at the same time. Decide on a boolean attribute instead, or add the values unconditionally.
""" % {"dir": snippetcompiler.project_dir}  # noqa: E501


# The scheduler gets stuck with two freeze candidates that both still have pending contributions and both are read by a
# plugin (std::count), which needs them complete:
# - Spec.items: still being filled by the comprehension over cluster.vms, which nothing needs complete, so it is never
#   frozen before the scheduler gets stuck
# - Service.resources: collects Alloc.resources and Peering.resources, which only get their values once Spec.items is
#   complete (Alloc loops over it and Allocated is only constructed once std::count(self.spec.items) returns)
# The scheduler freezes Service.resources first, so Peering's contribution arrives after the freeze.
MODEL_WAIT_CYCLE: str = """
entity Item:
    string name
end
implement Item using std::none

entity Cluster:
    int count
end
Cluster.vms [0:] -- Item
implement Cluster using fill_vms

implementation fill_vms for Cluster:
    for i in std::sequence(self.count):
        self.vms += Item(name=f"vm-{i}")
    end
end

entity Spec:
end
Spec.items [0:] -- Item
implement Spec using std::none

entity Allocated:
end
Allocated.entries [0:] -- Item
implement Allocated using std::none

entity Alloc:
end
Alloc.spec [1] -- Spec
Alloc.allocated [1] -- Allocated
Alloc.resources [0:] -- Item
implement Alloc using allocate

implementation allocate for Alloc:
    size = std::count(self.spec.items)
    self.allocated = Allocated(entries=[Item(name=f"entry-{i}") for i in std::sequence(size)])
    for item in self.spec.items:
        self.resources += Item(name=f"res-{item.name}")
    end
end

entity Peering:
end
Peering.alloc [1] -- Alloc
Peering.resources [0:] -- Item
implement Peering using peer

implementation peer for Peering:
    for entry in self.alloc.allocated.entries:
        self.resources += Item(name=f"peer-{entry.name}")
    end
end

entity Service:
end
Service.resources [0:] -- Item
implement Service using build

implementation build for Service:
    cluster = Cluster(count=2)
    spec = Spec(items=[vm for vm in cluster.vms])
    alloc = Alloc(spec=spec)
    peering = Peering(alloc=alloc)
    self.resources += [alloc.resources, peering.resources]
    for vm in cluster.vms:
        self.resources += Item(name=f"port-{vm.name}")
    end
end

entity Reader:
end
Reader.service [1] -- Service
Reader.seen [0:] -- Item
implement Reader using read_impl

implementation read_impl for Reader:
    total = std::count(self.service.resources)
    self.seen += Item(name=f"seen-{total}")
end

for i in std::sequence(5):
    Reader(service=Service())
end
"""


def test_modified_after_freeze_explains_wait_cycle(snippetcompiler):
    """
    Verify that the explanation of a wrong speculative freeze names the candidates, the pending statements, the chain of
    dependencies to the other candidate and the relation precedence rule that would have avoided the error.
    """
    snippetcompiler.setup_for_snippet(MODEL_WAIT_CYCLE, autostd=True)
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()
    explanation = ExplainerFactory().explain_and_format(e.value)
    assert explanation is not None

    main_cf: str = os.path.join(snippetcompiler.project_dir, "main.cf")
    with open(main_cf, encoding="utf-8") as fh:
        lines: list[str] = fh.read().split("\n")

    def location(statement: str) -> str:
        return f"{main_cf}:{lines.index(statement) + 1}"

    assert (
        "The compiler could not execute any statement until it considered one of the following relations complete:\n"
        f"  - __config__::Service.resources (5 instances), needed by std::count(self.service.resources)"
        f" ({location('    total = std::count(self.service.resources)')})\n"
        f"  - __config__::Spec.items (5 instances), needed by std::count(self.spec.items)"
        f" ({location('    size = std::count(self.spec.items)')})\n"
    ) in explanation
    assert (
        "It chose __config__::Service.resources, although the following statements still had to add values to it:\n"
        f"  - for vm in cluster.vms ({location('    for vm in cluster.vms:')})\n"
        f"  - self.resources += [alloc.resources,peering.resources]"
        f" ({location('    self.resources += [alloc.resources, peering.resources]')})\n"
    ) in explanation
    assert (
        "These statements could not run yet because of this chain of dependencies:\n"
        f"  self.resources += [alloc.resources,peering.resources]"
        f" ({location('    self.resources += [alloc.resources, peering.resources]')})\n"
        f"      waiting for relation __config__::Alloc.resources of __config__::Alloc (instantiated at"
        f" {location('    alloc = Alloc(spec=spec)')}), which still had to be completed by\n"
        f"  for item in self.spec.items ({location('    for item in self.spec.items:')})\n"
        f"      waiting for relation __config__::Spec.items of __config__::Spec (instantiated at"
        f" {location('    spec = Spec(items=[vm for vm in cluster.vms])')}) to be complete\n"
    ) in explanation
    assert (
        "__config__::Spec.items could not simply be considered complete first either, because it was still waiting for:\n"
        f"  Spec(items=[vm for vm in cluster.vms]) ({location('    spec = Spec(items=[vm for vm in cluster.vms])')})\n"
        f"      waiting for relation __config__::Cluster.vms of __config__::Cluster (instantiated at"
        f" {location('    cluster = Cluster(count=2)')}) to be complete\n"
        "  That relation had all its values, but nothing needed it complete, so the compiler had not concluded that yet.\n"
    ) in explanation
    assert (
        "How to fix the model\n"
        "\n"
        "The compiler only has to guess because the following statements need a relation to be complete while it is"
        " still being filled. Changing one of them is usually enough:\n"
        f"  - std::count(self.service.resources) ({location('    total = std::count(self.service.resources)')})"
        " needs relation __config__::Service.resources to be complete.\n"
        "    If it only checks whether the relation is empty, use `self.service.resources is defined` instead, which the"
        " compiler evaluates as soon as a value arrives.\n"
        "    If the number itself is needed, derive it from the attributes that determine the content of the relation"
        " instead of from the relation.\n"
        f"  - std::count(self.spec.items) ({location('    size = std::count(self.spec.items)')})"
        " needs relation __config__::Spec.items to be complete.\n"
    ) in explanation
    # the for loop over Spec.items processes it gradually and is not something to change
    assert "for item in self.spec.items" not in explanation.split("How to fix the model")[1]
    assert (
        "Alternatively, keep the model as it is and tell the compiler to consider __config__::Spec.items complete before"
        " __config__::Service.resources by adding this relation precedence rule to the project.yml file:\n"
        "\n"
        "    relation_precedence_policy:\n"
        '      - "__config__::Spec.items before __config__::Service.resources"\n'
    ) in explanation
    assert "The model itself is most likely correct" in explanation
    assert "This can mean one of two things" not in explanation


def test_modified_after_freeze_suggested_fix_compiles(snippetcompiler):
    """
    Verify that the first fix suggested by test_modified_after_freeze_explains_wait_cycle, replacing the plugin call on
    Service.resources by an is defined check, makes the model compile.
    """
    model: str = MODEL_WAIT_CYCLE.replace(
        """    total = std::count(self.service.resources)
    self.seen += Item(name=f"seen-{total}")
""",
        """    if self.service.resources is defined:
        self.seen += Item(name="seen")
    end
""",
    )
    assert "std::count(self.service.resources)" not in model  # guard the replace against model refactoring
    snippetcompiler.setup_for_snippet(model, autostd=True)
    compiler.do_compile()


def test_modified_after_freeze_suggested_rule_compiles(snippetcompiler):
    """
    Verify that the relation precedence rule suggested by test_modified_after_freeze_explains_wait_cycle makes the model
    compile.
    """
    snippetcompiler.setup_for_snippet(
        MODEL_WAIT_CYCLE,
        autostd=True,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::Spec",
                first_relation_name="items",
                then_type="__config__::Service",
                then_relation_name="resources",
            )
        ],
    )
    compiler.do_compile()


# The relation Host.rules is frozen through the scheduler's regular path: nothing is known to still add values to it,
# while plugin calls need it complete. The App instances that add rules are only constructed once the if statement can
# be evaluated, which needs Registry.sources complete, and the scheduler freezes Host.rules before Registry.sources.
# Taken from the test of PR #10548, which recovers from this by retrying with a learned freeze order.
MODEL_GATED_CONTRIBUTION: str = """
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

tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))
rule_count = std::count(host.rules)

registry = Registry()
registry.sources += Source(name="one")
registry.sources += Source(name="two")

if std::count(registry.sources) > 0:
    App(host=host, name="one")
    App(host=host, name="two")
end
"""


def test_modified_after_freeze_explains_gated_contribution(snippetcompiler):
    """
    Verify that the explanation of a relation frozen through the regular path names the statements that needed it
    complete, the statement that added the value afterwards, the condition that statement was gated on, the fix for that
    condition and the relation precedence rule that would have avoided the error.
    """
    snippetcompiler.setup_for_snippet(MODEL_GATED_CONTRIBUTION, autostd=True)
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()
    explanation = ExplainerFactory().explain_and_format(e.value)
    assert explanation is not None

    main_cf: str = os.path.join(snippetcompiler.project_dir, "main.cf")
    with open(main_cf, encoding="utf-8") as fh:
        lines: list[str] = fh.read().split("\n")

    def location(statement: str) -> str:
        return f"{main_cf}:{lines.index(statement) + 1}"

    assert (
        "The compiler considered __config__::Host.rules complete because no statement was known yet that would still add"
        " values to it, while the following statements needed it complete:\n"
    ) in explanation
    assert f"  - std::count(host.rules) ({location('rule_count = std::count(host.rules)')})\n" in explanation
    key_sort_location: str = location('tunnel = Tunnel(ingress=std::key_sort(host.rules, "name"))')
    assert f"  - std::key_sort(host.rules,'name') ({key_sort_location})\n" in explanation
    rule_location: str = location("    self.host.rules += Rule(name=self.name)")
    assert (
        f"The value was added by self.host.rules += Rule(name=self.name) ({rule_location})"
        " in implementation app_rule of __config__::App, for __config__::App (instantiated at"
    ) in explanation
    assert (
        "That statement was only scheduled afterwards, because it depends on:\n"
        f"  if (std::count(registry.sources) > 0) ({location('if std::count(registry.sources) > 0:')})\n"
        "      which needs relation registry.sources (__config__::Registry.sources) to be complete\n"
    ) in explanation
    assert (
        "How to fix the model\n"
        "\n"
        "The relation was considered complete before the statement that still adds to it was known. Changing one of the"
        " following statements is usually enough:\n"
        f"  - std::count(registry.sources) ({location('if std::count(registry.sources) > 0:')}) needs relation"
        " __config__::Registry.sources to be complete.\n"
        "    If it only checks whether the relation is empty, use `registry.sources is defined` instead, which the compiler"
        " evaluates as soon as a value arrives.\n"
    ) in explanation
    assert (
        f"  - std::count(host.rules) ({location('rule_count = std::count(host.rules)')}) needs relation __config__::Host.rules"
        " to be complete.\n"
    ) in explanation
    assert (
        "Alternatively, keep the model as it is and tell the compiler to consider __config__::Registry.sources complete"
        " before __config__::Host.rules by adding this relation precedence rule to the project.yml file:\n"
        "\n"
        "    relation_precedence_policy:\n"
        '      - "__config__::Registry.sources before __config__::Host.rules"\n'
    ) in explanation
    assert "The model is incorrect" not in explanation


def test_modified_after_freeze_gated_contribution_fix_compiles(snippetcompiler):
    """
    Verify that the fix suggested by test_modified_after_freeze_explains_gated_contribution, replacing the plugin call in
    the if condition by an is defined check, makes the model compile.
    """
    model: str = MODEL_GATED_CONTRIBUTION.replace("if std::count(registry.sources) > 0:", "if registry.sources is defined:")
    assert "std::count(registry.sources)" not in model  # guard the replace against model refactoring
    snippetcompiler.setup_for_snippet(model, autostd=True)
    compiler.do_compile()


def test_modified_after_freeze_gated_contribution_rule_compiles(snippetcompiler):
    """
    Verify that the relation precedence rule suggested by test_modified_after_freeze_explains_gated_contribution makes
    the model compile.
    """
    snippetcompiler.setup_for_snippet(
        MODEL_GATED_CONTRIBUTION,
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
    compiler.do_compile()
