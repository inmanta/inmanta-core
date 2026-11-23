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

import dataclasses
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from itertools import chain
from typing import Optional, Union

from inmanta.ast import Locatable, Location, ModifiedAfterFreezeException
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.constraint.expression import IsDefined
from inmanta.ast.entity import Entity, Implement, Implementation
from inmanta.ast.statements import (
    DynamicStatement,
    ExpressionStatement,
    Literal,
    ReferenceStatement,
    Statement,
    VariableReferenceHook,
)
from inmanta.ast.statements.assign import Assign
from inmanta.ast.statements.call import FunctionCall, FunctionUnit
from inmanta.ast.statements.generator import (
    ConditionalExpression,
    ConditionalExpressionResumer,
    Constructor,
    For,
    If,
    ListComprehension,
    ListComprehensionCollector,
)
from inmanta.ast.type import Type
from inmanta.ast.variables import AttributeReference, IsDefinedGradual, Reference, VariableReader
from inmanta.execute.runtime import (
    DelayedResultVariable,
    ExecutionContext,
    ExecutionUnit,
    HangUnit,
    Instance,
    IPromise,
    NamespaceResolver,
    ProgressionPromise,
    RawUnit,
    RelationAttributeVariable,
    Resolver,
    ResultVariable,
    ResultVariableProxy,
    SetPromise,
    VariableABC,
    VariableResolver,
    Waiter,
    WaiterSet,
    WrappedValueVariable,
)

# Bound on the number of waiters visited while looking for the relation a pending contribution depends on
MAX_VISITED_WAITERS = 5000

# Cache of the wait chains found for a frozen relation given the set of candidate relations, see explain_speculative_freeze
WaitChainCache = dict[
    tuple[int, frozenset[int]], tuple[Sequence["WaitStep"], Optional[DelayedResultVariable[object]], Sequence["WaitStep"]]
]

# The AST node a waiter executes, as far as it is meaningful to a model developer
WaiterStatement = Union[Statement, VariableReferenceHook]


@dataclasses.dataclass(frozen=True, slots=True)
class WaitStep:
    """
    One link in the chain of statements that kept a pending contribution from executing: statement could not run
    because it was waiting for waiting_for. The statement is None for internal waiters. A stalled step waits for a
    relation that had all its values but that the scheduler had not concluded complete because nothing needed it complete.
    """

    statement: Optional[WaiterStatement]
    waiting_for: Union[VariableABC[object], VariableReferenceHook]
    stalled: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class CandidateRelation:
    """
    A relation the scheduler could have chosen to consider complete: the number of its instances among the candidates
    and the statements that needed it complete, most informative first.
    """

    attribute: RelationAttribute
    instances: int
    consumers: Sequence[WaiterStatement]


@dataclasses.dataclass(frozen=True, slots=True)
class SpeculativeFreeze:
    """
    Why the scheduler considered a relation complete while statements still promised to contribute to it: it could not
    make progress otherwise and had to pick one of the candidate relations. Recorded by Scheduler.find_wait_cycle and
    attached to the ModifiedAfterFreezeException when the choice turns out to be wrong.

    :param variable: The relation variable that was frozen.
    :param consumers: The statements that needed the variable to be complete.
    :param pending: The statements that still promised to contribute to the variable.
    :param candidates: All relations that were candidates to be frozen, including the frozen one.
    :param chain: The chain of waiting statements from one of the pending statements to unblocked_by.
    :param unblocked_by: The other candidate the pending statement transitively waited for, if one was found.
    :param other_pending: Why unblocked_by could not be considered complete either: its pending statement and what that
        was waiting for, in turn.
    """

    variable: DelayedResultVariable[object]
    consumers: Sequence[WaiterStatement]
    pending: Sequence[Statement]
    candidates: Sequence[CandidateRelation]
    chain: Sequence[WaitStep]
    unblocked_by: Optional[DelayedResultVariable[object]]
    other_pending: Sequence[WaitStep]


def waiter_statement(waiter: Waiter) -> Optional[WaiterStatement]:
    """
    Return the AST node that describes what a waiter executes, or None if it is an internal waiter.
    """
    node: object
    if isinstance(waiter, ExecutionUnit):
        node = waiter.owner
    elif isinstance(waiter, FunctionUnit):
        node = waiter.function
    elif isinstance(waiter, HangUnit):
        node = waiter.resumer
    elif isinstance(waiter, RawUnit):
        resumer = waiter.resumer
        if isinstance(resumer, ConditionalExpressionResumer):
            node = resumer.expression
        elif isinstance(resumer, ListComprehensionCollector):
            node = resumer.statement
        elif isinstance(resumer, IsDefinedGradual):
            node = resumer.owner
        else:
            node = resumer
    else:
        return None
    return node if isinstance(node, (Statement, VariableReferenceHook)) else None


def describe_statement(node: WaiterStatement) -> str:
    """
    Render a statement with its source location, e.g. `self.x += y (main.cf:12)`.
    """
    text: str
    if isinstance(node, VariableReferenceHook):
        text = f"{node.instance.pretty_print()}.{node.name}" if node.instance is not None else node.name
    else:
        text = node.pretty_print()
    location = node.get_location()
    return f"{text} ({location.file}:{location.lnr})" if location is not None else text


def describe_variable(variable: Union[VariableABC[object], VariableReferenceHook]) -> Optional[str]:
    """
    Render what a statement was waiting for, or None for an anonymous intermediate result.
    """
    if isinstance(variable, RelationAttributeVariable):
        return f"relation {variable.attribute} of {variable.myself}"
    if isinstance(variable, VariableReferenceHook):
        reference: str = (
            f"{variable.instance.pretty_print()}.{variable.name}" if variable.instance is not None else variable.name
        )
        return f"the value of {reference}"
    return None


def _resolve_proxy(variable: VariableABC[object]) -> Optional[VariableABC[object]]:
    """
    Unwrap proxy chains to the underlying variable. Returns None if a proxy in the chain is not connected yet.
    """
    result: Optional[VariableABC[object]] = variable
    while isinstance(result, ResultVariableProxy):
        result = result.variable
    return result


def _pending_promises(variable: DelayedResultVariable[object]) -> list[IPromise]:
    """
    Return the promises on a (not yet frozen) delayed variable that have not been fulfilled.
    """
    if variable.promises is None or variable.done_promises is None:
        return []
    return [promise for promise in variable.promises if promise not in variable.done_promises]


def _is_stalled(variable: VariableABC[object]) -> bool:
    """
    Return whether a variable has all its values but has not been concluded complete because nothing needs it complete.
    """
    return (
        isinstance(variable, DelayedResultVariable)
        and not _pending_promises(variable)
        and variable.get_progress_potential() == 0
    )


def _consumer_priority(waiter: Waiter) -> int:
    """
    Sort key for the waiters of a variable, most informative first: plugin calls, which can only run with the complete
    relation, before other statements.
    """
    return 0 if isinstance(waiter, FunctionUnit) else 1


def consumers_of(variable: DelayedResultVariable[object]) -> list[WaiterStatement]:
    """
    Return the statements that need the variable to be complete, most informative first, see _consumer_priority. For loops
    are left out: they process the relation gradually and only wait for its completion to finish.
    """
    return _unique(
        statement
        for waiter in sorted(variable.waiters, key=_consumer_priority)
        if not isinstance(statement := waiter_statement(waiter), For)
    )


def _unique(nodes: Iterable[Optional[WaiterStatement]]) -> list[WaiterStatement]:
    seen: set[int] = set()
    result: list[WaiterStatement] = []
    for node in nodes:
        if node is not None and id(node) not in seen:
            seen.add(id(node))
            result.append(node)
    return result


class _WaiterIndex:
    """
    Index of the waiters that are still pending, by what they produce: the promise or the variable they will set, the
    statement they execute and the proxy variable they will connect.
    """

    def __init__(self, allwaiters: WaiterSet) -> None:
        self.by_promise: dict[IPromise, Waiter] = {}
        self.by_statement: dict[int, list[Waiter]] = {}
        self.by_target: dict[int, list[Waiter]] = {}
        self.by_proxy: dict[int, Waiter] = {}
        for waiter in allwaiters:
            if isinstance(waiter, ExecutionUnit):
                if isinstance(waiter.result, SetPromise):
                    self.by_promise[waiter.result] = waiter
                elif isinstance(waiter.result, ResultVariable):
                    self._add_target(waiter.result, waiter)
                self._add_statement(waiter.owner, waiter)
                if waiter.expression is not waiter.owner:
                    self._add_statement(waiter.expression, waiter)
            elif isinstance(waiter, FunctionUnit):
                self._add_target(waiter.result, waiter)
            elif isinstance(waiter, HangUnit):
                if waiter.target is not None:
                    self._add_target(waiter.target, waiter)
                self._add_statement(waiter.resumer, waiter)
            elif isinstance(waiter, RawUnit):
                resumer = waiter.resumer
                self._add_statement(resumer, waiter)
                target: Optional[VariableABC[object]] = None
                if isinstance(resumer, ConditionalExpressionResumer):
                    target = resumer.result
                elif isinstance(resumer, ListComprehensionCollector):
                    target = resumer.final_result
                elif isinstance(resumer, ListComprehension):
                    # the comprehension passes its collector, which owns the final result, to itself via the requires
                    wrapped = waiter.requires.get(resumer)
                    if isinstance(wrapped, WrappedValueVariable) and isinstance(wrapped.value, ListComprehensionCollector):
                        target = wrapped.value.final_result
                elif isinstance(resumer, IsDefinedGradual):
                    target = resumer.target
                elif isinstance(resumer, VariableReferenceHook) and isinstance(resumer.variable_resumer, VariableReader):
                    self.by_proxy[id(resumer.variable_resumer.target)] = waiter
                if target is not None:
                    self._add_target(target, waiter)

    def _add_target(self, variable: VariableABC[object], waiter: Waiter) -> None:
        self.by_target.setdefault(id(variable), []).append(waiter)

    def _add_statement(self, statement: object, waiter: Waiter) -> None:
        self.by_statement.setdefault(id(statement), []).append(waiter)

    def providers(self, variable: VariableABC[object]) -> list[Waiter]:
        """
        Return the pending waiters that will set (or contribute to) a variable.
        """
        if isinstance(variable, DelayedResultVariable):
            return self.waiters_for_promises(_pending_promises(variable))
        return self.by_target.get(id(variable), [])

    def waiters_for_promises(self, promises: Iterable[IPromise]) -> list[Waiter]:
        result: list[Waiter] = []
        for promise in promises:
            if isinstance(promise, SetPromise):
                waiter: Optional[Waiter] = self.by_promise.get(promise)
                if waiter is not None:
                    result.append(waiter)
            elif isinstance(promise, ProgressionPromise):
                result.extend(self.by_statement.get(id(promise.provider), []))
        return result


def _blocking_requirements(waiter: Waiter, index: _WaiterIndex) -> list[tuple[WaitStep, list[Waiter]]]:
    """
    Return, for each requirement of the waiter that is not available yet, the wait step it represents and the pending
    waiters that will provide it.
    """
    statement: Optional[WaiterStatement] = waiter_statement(waiter)
    result: list[tuple[WaitStep, list[Waiter]]] = []
    for required in waiter.requires.values():
        resolved: Optional[VariableABC[object]] = _resolve_proxy(required)
        if resolved is None:
            # not connected yet: the waiter that will connect it is the one resolving the attribute reference
            hook_waiter: Optional[Waiter] = index.by_proxy.get(id(required))
            hook = hook_waiter.resumer if isinstance(hook_waiter, RawUnit) else None
            step = WaitStep(statement, hook if isinstance(hook, VariableReferenceHook) else required)
            result.append((step, [hook_waiter] if hook_waiter is not None else []))
        elif not resolved.is_ready():
            providers: list[Waiter] = index.providers(resolved)
            result.append((WaitStep(statement, resolved, stalled=not providers and _is_stalled(resolved)), providers))
    return result


def _trace_pending(variable: DelayedResultVariable[object], index: _WaiterIndex, max_depth: int = 6) -> list[WaitStep]:
    """
    Follow what the pending contribution to variable is waiting for, one requirement per level, until nothing is found.
    """
    steps: list[WaitStep] = []
    waiters: list[Waiter] = index.waiters_for_promises(_pending_promises(variable))
    visited: set[Waiter] = set()
    while waiters and waiters[0] not in visited and len(steps) < max_depth:
        waiter: Waiter = waiters[0]
        visited.add(waiter)
        blocking: list[tuple[WaitStep, list[Waiter]]] = _blocking_requirements(waiter, index)
        if not blocking:
            break
        step, waiters = blocking[0]
        steps.append(step)
    return steps


def _find_wait_chain(
    pending: Sequence[IPromise], targets: set[DelayedResultVariable[object]], allwaiters: WaiterSet
) -> tuple[list[WaitStep], Optional[DelayedResultVariable[object]], list[WaitStep]]:
    """
    Breadth-first search from the waiters that hold the pending promises, along what they wait for, to one of the target
    variables. Returns the chain of wait steps to the target, the target and what the target's own pending contribution was
    waiting for. The chain is empty if no target is reachable.
    """
    index = _WaiterIndex(allwaiters)
    queue: deque[tuple[Waiter, list[WaitStep]]] = deque((waiter, []) for waiter in index.waiters_for_promises(pending))
    visited: set[Waiter] = {waiter for waiter, _ in queue}
    while queue and len(visited) <= MAX_VISITED_WAITERS:
        waiter, path = queue.popleft()
        for step, next_waiters in _blocking_requirements(waiter, index):
            if isinstance(step.waiting_for, DelayedResultVariable) and step.waiting_for in targets:
                return path + [step], step.waiting_for, _trace_pending(step.waiting_for, index)
            for next_waiter in next_waiters:
                if next_waiter not in visited:
                    visited.add(next_waiter)
                    queue.append((next_waiter, path + [step]))
    return [], None, []


def explain_speculative_freeze(
    variable: DelayedResultVariable[object],
    candidates: Sequence[DelayedResultVariable[object]],
    allwaiters: WaiterSet,
    chain_cache: WaitChainCache,
) -> SpeculativeFreeze:
    """
    Record why the scheduler is about to freeze variable to break a wait cycle. Must be called before the variable is
    frozen, while its promises and waiters are still known.

    Finding the wait chain requires a pass over all pending waiters, so it is done once per combination of frozen relation
    and candidate relations: the chain consists of statements and relations, which the other instances of the same
    relation share, only the instances mentioned in it differ.

    :param candidates: All variables that were candidates to be frozen, possibly with duplicates.
    :param allwaiters: All pending waiters of the scheduler.
    :param chain_cache: The wait chains found so far in this compile, extended by this call.
    """
    pending_promises: list[IPromise] = _pending_promises(variable)
    unique_candidates: list[DelayedResultVariable[object]] = list({id(c): c for c in candidates}.values())
    by_attribute: dict[RelationAttribute, list[DelayedResultVariable[object]]] = {}
    for candidate in unique_candidates:
        if isinstance(candidate, RelationAttributeVariable):
            by_attribute.setdefault(candidate.attribute, []).append(candidate)
    candidate_relations: list[CandidateRelation] = [
        CandidateRelation(
            attribute=attribute,
            instances=len(variables),
            consumers=consumers_of(variables[0])[:3],
        )
        for attribute, variables in by_attribute.items()
    ]

    chain: Sequence[WaitStep] = []
    unblocked_by: Optional[DelayedResultVariable[object]] = None
    other_pending: Sequence[WaitStep] = []
    if len(by_attribute) > 1 and isinstance(variable, RelationAttributeVariable):
        cache_key = (id(variable.attribute), frozenset(id(attribute) for attribute in by_attribute))
        if cache_key in chain_cache:
            chain, unblocked_by, other_pending = chain_cache[cache_key]
        else:
            # only relations other than the frozen one can be scheduled differently by a relation precedence rule
            targets: set[DelayedResultVariable[object]] = {
                candidate
                for attribute, variables in by_attribute.items()
                if attribute is not variable.attribute
                for candidate in variables
            }
            chain, unblocked_by, other_pending = _find_wait_chain(pending_promises, targets, allwaiters)
            chain_cache[cache_key] = (chain, unblocked_by, other_pending)

    return SpeculativeFreeze(
        variable=variable,
        consumers=consumers_of(variable),
        pending=[
            promise.provider
            for promise in pending_promises
            if isinstance(promise, (SetPromise, ProgressionPromise)) and isinstance(promise.provider, Statement)
        ],
        candidates=candidate_relations,
        chain=chain,
        unblocked_by=unblocked_by,
        other_pending=other_pending,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class RelationRead:
    """
    A read of a relation in a condition, which needs the relation to be complete before the condition can be evaluated.

    :param node: The plugin call or is defined check that reads the relation.
    :param reference: The relation as written in the model, e.g. registry.sources.
    :param attribute: The relation attribute, if the type of the reference could be determined.
    :param on_self: Whether the reference is to a relation of the instance that evaluates the condition.
    """

    node: WaiterStatement
    reference: str
    attribute: Optional[RelationAttribute]
    on_self: bool


@dataclasses.dataclass(frozen=True, slots=True)
class Gate:
    """
    A condition that had to be evaluated before a statement was scheduled: an if statement, a for loop or an implement
    when clause.

    :param statement: The if, for or implement statement.
    :param description: The condition as written in the model.
    :param reads: The relation reads in the condition.
    :param self_instance: The instance that self refers to in the condition, if known.
    """

    statement: Locatable
    description: str
    reads: Sequence[RelationRead]
    self_instance: Optional[Instance]


@dataclasses.dataclass(frozen=True, slots=True)
class LateContribution:
    """
    Why a statement that adds a value to a relation was not known yet when the scheduler froze the relation through its
    regular path: the statement, the instance whose implementation ran it, and the conditions that had to be evaluated
    before it was scheduled. Attached to the ModifiedAfterFreezeException by the scheduler.

    :param statement: The statement that added the value.
    :param instance: The instance whose implementation ran the statement, if any.
    :param implementation: That implementation, if any.
    :param gates: The conditions the statement was waiting on, innermost first.
    :param consumers: Statements that need the frozen relation to be complete, sampled over the instances of its
        relation attribute.
    """

    statement: Optional[Locatable]
    instance: Optional[Instance]
    implementation: Optional[Implementation]
    gates: Sequence[Gate]
    consumers: Sequence[WaiterStatement]


def enclosing_instance(resolver: Optional[Resolver]) -> Optional[Instance]:
    """
    Return the instance whose implementation a resolver belongs to, or None for a top level resolver.
    """
    current: Optional[Resolver] = resolver
    for _ in range(100):
        if current is None:
            return None
        if isinstance(current, Instance):
            return current
        if isinstance(current, (NamespaceResolver, VariableResolver)):
            current = current.parent
        elif isinstance(current, ExecutionContext):
            current = current.resolver
        else:
            return None
    return None


class ModelIndex:
    """
    Index of the model's blocks: the block that holds each statement, the statement or implementation that owns each
    block, the statements per source line and the implement statements that select each implementation.
    """

    def __init__(self, blocks: Iterable[BasicBlock], types: Mapping[str, Type]) -> None:
        self.block_of: dict[int, BasicBlock] = {}
        self.owner_of: dict[int, Union[DynamicStatement, Implementation]] = {}
        self.by_line: dict[tuple[str, int], list[DynamicStatement]] = {}
        self.selectors: dict[int, list[tuple[Entity, Implement]]] = {}
        self.top_blocks: list[BasicBlock] = list(blocks)
        for block in self.top_blocks:
            self._index_block(block)
        for entity in types.values():
            if not isinstance(entity, Entity):
                continue
            for implementation in entity.implementations:
                self.owner_of[id(implementation.statements)] = implementation
                self._index_block(implementation.statements)
            for implement in entity.implements:
                for implementation in implement.implementations:
                    self.selectors.setdefault(id(implementation), []).append((entity, implement))

    def _index_block(self, block: BasicBlock) -> None:
        for statement in block.get_stmts():
            self.block_of[id(statement)] = block
            location: Optional[Location] = statement.get_location()
            if location is not None:
                self.by_line.setdefault((location.file, location.lnr), []).append(statement)
            for nested in statement.nested_blocks():
                self.owner_of[id(nested)] = statement
                self._index_block(nested)

    def statement_at(self, locations: Iterable[Location]) -> Optional[DynamicStatement]:
        """
        Return the first block level statement on any of the given source lines.
        """
        for location in locations:
            statements: list[DynamicStatement] = self.by_line.get((location.file, location.lnr), [])
            if statements:
                return statements[0]
        return None

    def enclosing_blocks(self, block: Optional[BasicBlock]) -> Iterable[BasicBlock]:
        """
        Yield a block and the blocks it is nested in, up to and including the implementation or top level block. Variables
        of the top level blocks are visible everywhere, so those are yielded last.
        """
        current: Optional[BasicBlock] = block
        for _ in range(100):
            if current is None:
                break
            yield current
            owner = self.owner_of.get(id(current))
            current = self.block_of.get(id(owner)) if isinstance(owner, DynamicStatement) else None
        yield from self.top_blocks


def _walk_expression(expression: ExpressionStatement) -> Iterable[ExpressionStatement]:
    yield expression
    if isinstance(expression, ConditionalExpression):
        children: Iterable[ExpressionStatement] = (
            expression.condition,
            expression.if_expression,
            expression.else_expression,
        )
    elif isinstance(expression, ReferenceStatement):
        children = expression.children
    else:
        return
    for child in children:
        yield from _walk_expression(child)


def _entity_of_reference(
    reference: Optional[Reference], index: ModelIndex, scope: Optional[BasicBlock], self_entity: Optional[Entity]
) -> tuple[Optional[Entity], bool]:
    """
    Determine the entity an instance reference refers to, statically. Returns the entity (None if it could not be
    determined) and whether the reference is to self.
    """
    if reference is None or (not isinstance(reference, AttributeReference) and reference.name == "self"):
        return self_entity, True
    if isinstance(reference, AttributeReference):
        base, _ = _entity_of_reference(reference.instance, index, scope, self_entity)
        attribute = base.get_attribute(str(reference.attribute)) if base is not None else None
        if isinstance(attribute, RelationAttribute) and isinstance(attribute.type, Entity):
            return attribute.type, False
        return None, False
    for block in index.enclosing_blocks(scope):
        for statement in block.get_stmts():
            if (
                isinstance(statement, Assign)
                and str(statement.name) == reference.name
                and isinstance(statement.value, Constructor)
            ):
                return statement.value.type, False
    return None, False


def _relation_reads(
    condition: ExpressionStatement, index: ModelIndex, scope: Optional[BasicBlock], self_entity: Optional[Entity]
) -> list[RelationRead]:
    """
    Return the relation reads in a condition: relations passed to plugin calls and relations checked with is defined.
    """
    reads: list[RelationRead] = []

    def add(node: WaiterStatement, instance: Optional[Reference], name: str, reference: str) -> None:
        entity, on_self = _entity_of_reference(instance, index, scope, self_entity)
        attribute = entity.get_attribute(name) if entity is not None else None
        if entity is None or isinstance(attribute, RelationAttribute):
            reads.append(
                RelationRead(node, reference, attribute if isinstance(attribute, RelationAttribute) else None, on_self)
            )

    for node in _walk_expression(condition):
        if isinstance(node, FunctionCall):
            for argument in chain(node.arguments, node.kwargs.values()):
                if isinstance(argument, AttributeReference):
                    add(node, argument.instance, str(argument.attribute), argument.pretty_print())
                elif isinstance(argument, Reference) and self_entity is not None and argument.name != "self":
                    # a bare name in an implement when clause is an attribute of the instance
                    if isinstance(self_entity.get_attribute(argument.name), RelationAttribute):
                        add(node, None, argument.name, argument.name)
        elif isinstance(node, IsDefined):
            reference: str = f"{node.attr.pretty_print()}.{node.name}" if node.attr is not None else node.name
            add(node, node.attr, node.name, reference)
    return reads


def _implement_description(entity: Entity, implement: Implement) -> str:
    names: str = ", ".join(implementation.name for implementation in implement.implementations)
    return f"implement {entity.get_full_name()} using {names} when {implement.constraint.pretty_print()}"


def explain_late_contribution(
    exception: ModifiedAfterFreezeException,
    waiter: Optional[Waiter],
    index: ModelIndex,
    consumers: Sequence[WaiterStatement],
) -> LateContribution:
    """
    Explain why the statement that added a value to a frozen relation was not known to the scheduler when it froze the
    relation: walk up from the statement through the blocks it is nested in, the implement clause that selected its
    implementation and the constructor of the instance that implementation ran for, collecting the conditions on the way.

    :param waiter: The waiter that executed the statement, to find the instance it ran for.
    :param index: The index of the model.
    :param consumers: The statements that need the frozen relation complete.
    """
    statement: Optional[Locatable] = exception.stmt
    resolver: Optional[Resolver] = (
        waiter.resolver if isinstance(waiter, (ExecutionUnit, HangUnit, RawUnit, FunctionUnit)) else None
    )
    instance: Optional[Instance] = enclosing_instance(resolver)
    late_instance: Optional[Instance] = instance
    implementation: Optional[Implementation] = None
    gates: list[Gate] = []
    block: Optional[BasicBlock] = index.block_of.get(id(statement)) if statement is not None else None
    if block is None and statement is not None:
        # the statement is an expression nested in a block level statement, e.g. a constructor in an assignment
        location: Optional[Location] = statement.get_location()
        enclosing: Optional[DynamicStatement] = index.statement_at([location]) if location is not None else None
        block = index.block_of.get(id(enclosing)) if enclosing is not None else None
    self_entity: Optional[Entity] = instance.type if instance is not None else None
    for _ in range(50):
        if block is None:
            break
        owner = index.owner_of.get(id(block))
        if owner is None:
            break
        if isinstance(owner, Implementation):
            if implementation is None:
                implementation = owner
            for entity, implement in index.selectors.get(id(owner), []):
                if instance is not None and not (instance.type is entity or instance.type.is_subclass(entity)):
                    continue
                if isinstance(implement.constraint, Literal) and implement.constraint.value is True:
                    continue
                gates.append(
                    Gate(
                        implement,
                        _implement_description(entity, implement),
                        _relation_reads(implement.constraint, index, block, instance.type if instance else entity),
                        instance,
                    )
                )
            # continue at the constructor of the instance, whose own context is not known from here on
            constructor: Optional[DynamicStatement] = (
                index.statement_at(instance.get_locations()) if instance is not None else None
            )
            block = index.block_of.get(id(constructor)) if constructor is not None else None
            instance = None
            self_entity = None
            continue
        if isinstance(owner, If):
            gates.append(
                Gate(
                    owner,
                    f"if {owner.condition.pretty_print()}",
                    _relation_reads(owner.condition, index, block, self_entity),
                    instance,
                )
            )
        elif isinstance(owner, For):
            gates.append(Gate(owner, owner.pretty_print(), _relation_reads(owner.base, index, block, self_entity), instance))
        block = index.block_of.get(id(owner))
    return LateContribution(statement, late_instance, implementation, gates, consumers)
