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

# pylint: disable-msg=W0613,R0201

import itertools
import logging
import uuid
from collections import abc
from collections.abc import Iterator
from itertools import chain
from typing import Optional, Union

import inmanta.ast.entity
import inmanta.ast.type as inmanta_type
import inmanta.execute.dataflow as dataflow
from inmanta.ast import (
    AmbiguousTypeException,
    AttributeReferenceAnchor,
    DuplicateException,
    InvalidCompilerState,
    Locatable,
    LocatableString,
    Location,
    Namespace,
    NotFoundException,
    Range,
    RuntimeException,
    TypeNotFoundException,
    TypeReferenceAnchor,
    TypingException,
)
from inmanta.ast.attribute import Attribute, RelationAttribute
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import (
    AttributeAssignmentLHS,
    ExpressionStatement,
    Literal,
    RawResumer,
    RequiresEmitStatement,
    StaticEagerPromise,
)
from inmanta.ast.statements.assign import GradualSetAttributeHelper, SetAttributeHelper
from inmanta.ast.variables import Reference
from inmanta.const import LOG_LEVEL_TRACE
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    ExecutionContext,
    ExecutionUnit,
    Instance,
    ListElementVariable,
    QueueScheduler,
    RawUnit,
    Resolver,
    ResultCollector,
    ResultVariable,
    VariableABC,
    VariableResolver,
    WrappedValueVariable,
)
from inmanta.execute.tracking import ImplementsTracker
from inmanta.execute.util import Unknown

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.entity import Entity, Implement  # noqa: F401

LOGGER = logging.getLogger(__name__)


class SubConstructor(RequiresEmitStatement):
    """
    This statement selects an implementation for a given object and
    imports the statements

    :ivar type: The specific entity type of an instance this subconstructor applies to, i.e. the actual instance type, not a
        supertype.
    """

    __slots__ = ("type", "location", "implements")

    def __init__(self, instance_type: "Entity", implements: "Implement") -> None:
        super().__init__()
        self.type = instance_type
        self.implements = implements
        self.location = self.implements.get_location()

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        # Only track promises for implementations when they get emitted, because of limitation of current static normalization
        # order: implementation blocks have not normalized at this point, so with the current mechanism we can't fetch eager
        # promises yet. Normalization order can not just be reversed because implementation bodies might contain constructor
        # calls (even for the same type), which would require this instance to be normalized first, resulting in a loop.
        self._own_eager_promises = []
        # injected_variables: Set[str] = {"self"}.union(self.type.get_all_attribute_names())
        # self._own_eager_promises = [
        #     # implementations live in the namespace's context rather than the constructor's context so for promises that cross
        #     # the boundary we translate references so that they are resolved correctly in any context wrapping the constructor
        #     dataclasses.replace(promise, instance=promise.instance.fully_qualified())
        #     for implementation in self.implements.implementations
        #     for promise in implementation.statements.get_eager_promises()
        #     if promise.get_root_variable() not in injected_variables
        # ]

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)
        try:
            resv = resolver.for_namespace(self.implements.constraint.namespace)
            requires.update(self.implements.constraint.requires_emit(resv, queue))
            return requires
        except NotFoundException as e:
            e.set_statement(self.implements)
            raise e

    def execute(self, requires: dict[object, object], instance: Instance, queue: QueueScheduler) -> object:
        """
        Evaluate this statement
        """
        LOGGER.log(LOG_LEVEL_TRACE, "executing subconstructor for %s implement %s", self.type, self.implements.location)
        super().execute(requires, instance, queue)
        # this assertion is because the typing of this method is not correct
        # it should logically always hold, but we can't express this as types yet
        assert isinstance(instance, Instance)
        condition = self.implements.constraint.execute(requires, instance, queue)
        try:
            inmanta_type.Bool().validate(condition)
        except RuntimeException as e:
            e.set_statement(self.implements)
            e.msg = (
                "Invalid value `%s`: the condition for a conditional implementation can only be a boolean expression"
                % condition
            )
            raise e
        if not condition:
            return None

        myqueue = queue.for_tracker(ImplementsTracker(self, instance))

        implementations = self.implements.implementations

        for impl in implementations:
            if instance.add_implementation(impl):
                # generate a subscope/namespace for each loop
                xc = ExecutionContext(impl.statements, instance.for_namespace(impl.statements.namespace))
                xc.emit(myqueue)

        return None

    def pretty_print(self) -> str:
        return "implement {} using {} when {}".format(
            self.type,
            ",".join(i.name for i in self.implements.implementations),
            self.implements.constraint.pretty_print(),
        )

    def __str__(self) -> str:
        return self.pretty_print()

    def __repr__(self) -> str:
        return "SubConstructor(%s)" % self.type


class GradualFor(ResultCollector[object]):
    # this class might be unnecessary if receive-result is always called and exactly once

    def __init__(self, stmt: "For", resolver: Resolver, queue: QueueScheduler) -> None:
        self.resolver = resolver
        self.queue = queue
        self.stmt = stmt
        self.seen: set[int] = set()

    def receive_result(self, value: object, location: Location) -> bool:
        if isinstance(value, Unknown):
            # skip unknowns
            return False
        if id(value) in self.seen:
            return False
        self.seen.add(id(value))

        xc = ExecutionContext(self.stmt.module, self.resolver.for_namespace(self.stmt.module.namespace))
        loopvar = xc.lookup(self.stmt.loop_var)
        # this assertion is because the typing of this method is not correct
        # it should logically always hold, but we can't express this as types yet
        assert isinstance(loopvar, ResultVariable)
        loopvar.set_value(value, self.stmt.location)
        xc.emit(self.queue)
        return False


class For(RequiresEmitStatement):
    """
    A for loop
    """

    __slots__ = ("base", "loop_var", "loop_var_loc", "module")

    def __init__(self, variable: ExpressionStatement, loop_var: LocatableString, module: BasicBlock) -> None:
        super().__init__()
        self.base: ExpressionStatement = variable
        self.loop_var = str(loop_var)
        self.loop_var_loc = loop_var.get_location()
        self.module = module

    def __repr__(self) -> str:
        return "For(%s)" % self.loop_var

    def normalize(self) -> None:
        self.base.normalize()
        # self.loop_var.normalize(resolver)
        self.module.normalize()
        self.anchors.extend(self.base.get_anchors())
        self.anchors.extend(self.module.get_anchors())
        self.module.add_var(self.loop_var, self)
        self._own_eager_promises = self.module.get_eager_promises()

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(super().get_all_eager_promises(), self.base.get_all_eager_promises())

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)

        # pass context via requires!
        helper = GradualFor(self, resolver, queue)
        requires[self] = WrappedValueVariable(helper)

        requires.update(self.base.requires_emit_gradual(resolver, queue, helper))

        return requires

    def execute(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        Evaluate this statement.
        """
        super().execute(requires, resolver, queue)
        var = self.base.execute(requires, resolver, queue)

        if not isinstance(var, (list, Unknown)):
            raise TypingException(self, "A for loop can only be applied to lists and relations")

        # we're done here: base's execute has reported results to helper
        return None

    def nested_blocks(self) -> Iterator["BasicBlock"]:
        yield self.module


class ListComprehension(RawResumer, ExpressionStatement):
    """
    A list comprehension expression, e.g. `["hello {{world}}" for world in worlds if world != "exclude"]`.
    """

    __slots__ = ("loop_var", "value_expression", "iterable", "guard")

    def __init__(
        self,
        value_expression: ExpressionStatement,
        loop_var: LocatableString,
        iterable: ExpressionStatement,
        guard: Optional[ExpressionStatement] = None,
    ) -> None:
        super().__init__()
        self.value_expression: ExpressionStatement = value_expression
        self.loop_var: LocatableString = loop_var
        self.iterable: ExpressionStatement = iterable
        self.guard: Optional[ExpressionStatement] = guard

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        self.value_expression.normalize(lhs_attribute=lhs_attribute)
        self.iterable.normalize()
        if self.guard is not None:
            self.guard.normalize()
        self.anchors.extend(
            itertools.chain(
                self.value_expression.get_anchors(),
                self.iterable.get_anchors(),
                (self.guard.get_anchors() if self.guard is not None else ()),
            )
        )

    def requires(self) -> list[str]:
        # exclude loop var, unless it shadows an occurrence in iterable
        return list(set(self.value_expression.requires()) - {str(self.loop_var)} | set(self.iterable.requires()))

    def requires_emit(
        self, resolver: Resolver, queue: QueueScheduler, *, lhs: Optional[ResultCollector[object]] = None
    ) -> dict[object, VariableABC[object]]:
        """
        Sets up gradual or non-gradual execution (depending on the lhs) of the list comprehension. Additionally sets up a
        resumer for when the iterable is complete. Returns as requires the (gradual) helper's result variable, which will be
        frozen by the resumer.

        Flow:
            `requires_emit()` -> set up helper, schedule resume and execute
            -> helper gradual execution (if lhs is not None)
            -> wait for iterable completion -> `resume()` -> finalize helper input
            -> wait for helper completion -> `execute()` -> return complete value
        """
        base_requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)

        # set up gradual execution
        collector_helper: ListComprehensionCollector = ListComprehensionCollector(
            statement=self,
            resolver=resolver,
            queue=queue,
            lhs=lhs,
        )
        self.copy_location(collector_helper)
        iterable_requires: dict[object, VariableABC[object]] = (
            # use helper strictly non-gradually when in a non-gradual context
            # => propagates progress potential to iterable expression's requires
            self.iterable.requires_emit(resolver, queue)
            if lhs is None
            else self.iterable.requires_emit_gradual(resolver, queue, collector_helper)
        )

        # non-gradual mode / finishing up: resume as soon as the iterable can be executed
        # pass helper to the resumer via the requires object
        wrapped_helper: VariableABC[ListComprehensionCollector] = WrappedValueVariable(collector_helper)
        requires: dict[object, VariableABC[object]] = base_requires | iterable_requires | {self: wrapped_helper}
        RawUnit(queue, resolver, requires, resumer=self)

        # Wait for resumer and helper to populate result.
        # No need to wait for iterable requires explicitly because resumer already does
        return base_requires | {self: collector_helper.final_result}

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector[object]
    ) -> dict[object, VariableABC[object]]:
        return self.requires_emit(resolver, queue, lhs=resultcollector)

    def resume(self, requires: dict[object, VariableABC[object]], resolver: Resolver, queue: QueueScheduler) -> None:
        """
        Resume when the iterable is fully ready for execution. Populates the helper's result variable and signals that no more
        values will be sent.
        """
        # fetch helper, passed via the requires object
        collector_helper: object = requires[self].get_value()
        assert isinstance(collector_helper, ListComprehensionCollector)

        # execute iterable so we have all values
        iterable: object = self.iterable.execute({k: v.get_value() for k, v in requires.items()}, resolver, queue)

        # indicate to helper that we're done
        if isinstance(iterable, Unknown):
            collector_helper.set_unknown()
        elif not isinstance(iterable, list):
            raise TypingException(
                self, f"A list comprehension can only be applied to lists and relations, got {type(iterable).__name__}"
            )
        else:
            collector_helper.complete(iterable, resolver, queue)

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # at this point the resumer signalled the helper we were done and the helper waited for all value expressions
        # => just fetch the result
        return requires[self]

    def execute_direct(self, requires: abc.Mapping[str, object]) -> Union[list[object], Unknown]:
        iterable: object = self.iterable.execute_direct(requires)
        if isinstance(iterable, Unknown):
            return Unknown(self)
        elif not isinstance(iterable, list):
            raise TypingException(
                self,
                f"A list comprehension in a direct execute context can only be applied to lists, got {type(iterable).__name__}",
            )

        def process(element: object) -> Optional[object]:
            """
            Execute the list comprehension for a single element of the iterable. Evaluates the guard expression if there is
            any and executes the value expression if the guard passes. Returns the result of the value expression if the
            guard passed, otherwise returns None.
            """
            extended_requires: abc.Mapping[str, object] = requires | {str(self.loop_var): element}

            guard_passed: bool
            if self.guard is None:
                guard_passed = True
            else:
                guard_value: object = self.guard.execute_direct(extended_requires)
                if isinstance(iterable, Unknown):
                    return Unknown(self)
                if not isinstance(guard_value, bool):
                    raise TypingException(
                        self,
                        (
                            f"Invalid value `{guard_value}`:"
                            " the guard condition for a list comprehension must be a boolean expression"
                        ),
                    )
                guard_passed = guard_value

            return self.value_expression.execute_direct(extended_requires) if guard_passed else None

        return [result for element in iterable if (result := process(element)) is not None]

    def pretty_print(self) -> str:
        return "[{} for {} in {}{}]".format(
            self.value_expression.pretty_print(),
            self.loop_var,
            self.iterable.pretty_print(),
            f" if {self.guard.pretty_print()}" if self.guard is not None else "",
        )

    def __str__(self) -> str:
        return self.pretty_print()

    def __repr__(self) -> str:
        return "ListComprehension(value_expression={}, loop_var={}, iterable={}, guard={})".format(
            repr(self.value_expression),
            repr(self.loop_var),
            repr(self.iterable),
            repr(self.guard),
        )


class ListComprehensionGuard(Literal):
    """
    Representation of the else expression for a list comprehension guard. This statement is an expression in the sense that
    it behaves like one but its return value represents that a subexpression should be filtered out rather than an actual
    DSL-compatible value. This special value must always be caught by the statement that creates the guard. This expression
    must never be exposed directly in the DSL.
    """

    __slots__ = ()

    GUARD = object()
    """
    Artificial value used in the else branch of the list comprehension guard's conditional expression. Indicates that the value
    expression for an element should not be executed because the element was filtered by the guard.
    """

    def __init__(self) -> None:
        super().__init__(self.GUARD)

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector[object]
    ) -> dict[object, VariableABC[object]]:
        # this statement represents the absence of a result => don't pass on resultcollector
        return self.requires_emit(resolver, queue)


class ListComprehensionCollector(RawResumer, ResultCollector[object]):
    """
    Result collector (gradual or otherwise) for the list comprehension statement. When it receives a
    result, it sets up appropriate (gradual or otherwise) execution for the value expression, with the lhs as final result
    collector. Finally, it collects all final results in its own result variable for non-gradual execution.

    This class has a gradual mode and a non-gradual mode depending on whether `lhs` is set. In non-gradual mode (lhs is None)
    it must not receive any gradual results. This allows the class to maintain ordering in non-gradual mode (if elements are
    received gradually each they arrive as soon as they can be resolved).

    Expects to receive each result once, either gradually or at execution-time. Clients should indicate completion by calling
    `complete()` or `set_unknown()`, after which no more values may be provided. This instance's `final_result` attribute
    will contain the final result. It will be only be set after the client declares completion, but not necessarily immediately
    after (we may have to wait for value expressions' requires).
    """

    __slots__ = ("statement", "resolver", "queue", "lhs", "_results", "_complete", "final_result")

    def __init__(
        self,
        statement: ListComprehension,
        resolver: Resolver,
        queue: QueueScheduler,
        lhs: Optional[ResultCollector[object]] = None,
    ) -> None:
        self.statement: ListComprehension = statement
        self.resolver: Resolver = resolver
        self.queue: QueueScheduler = queue
        self.lhs: Optional[ResultCollector[object]] = lhs
        # separately collect results for the value expression for each element of the iterable so we can wait for
        # each element's value expression to complete.
        self._results: list[VariableABC[object]] = []
        # have we received all elements?
        self._complete: bool = False
        # collector for the final result
        self.final_result: ResultVariable[object] = ResultVariable()

    def receive_result(self, value: object, location: Location) -> bool:
        """
        Receive an single element from the iterable and schedule execution of the associated value expression.
        """
        if self._complete:
            raise InvalidCompilerState(self, "list comprehension helper received gradual result after it was declared complete")

        # Use special result variable for a pre-known value with listener capabilities. Using a plain `ResultVariable` would
        # break gradual execution (e.g. `Reference.requires_emit_gradual` registers self.lhs as listener)
        value_wrapper: ListElementVariable[object] = ListElementVariable(value, location)
        value_resolver: VariableResolver = VariableResolver(
            parent=self.resolver,
            name=str(self.statement.loop_var),
            variable=value_wrapper,
        )

        result_variable: ResultVariable[object] = ResultVariable()
        self._results.append(result_variable)

        # propagate unknowns without executing value expression while still allowing to filter them out with the guard
        value_expression: ExpressionStatement
        if isinstance(value, Unknown):
            value_expression = Literal(value)
            self.statement.copy_location(value_expression)
        else:
            value_expression = self.statement.value_expression

        # execute the value expression and the guard
        guarded_expression: ExpressionStatement
        if self.statement.guard is None:
            guarded_expression = value_expression
        else:
            else_expression: ExpressionStatement = ListComprehensionGuard()
            guarded_expression = ConditionalExpression(
                condition=self.statement.guard,
                if_expression=value_expression,
                else_expression=else_expression,
            )
            self.statement.copy_location(else_expression)
            self.statement.copy_location(guarded_expression)

        requires: dict[object, VariableABC[object]] = (
            guarded_expression.requires_emit(value_resolver, self.queue)
            if self.lhs is None
            else guarded_expression.requires_emit_gradual(value_resolver, self.queue, self.lhs)
        )
        ExecutionUnit(
            self.queue,
            value_resolver,
            result_variable,
            requires,
            guarded_expression,
        )

        return False

    def set_unknown(self) -> None:
        """
        Set the final result to be an unknown. No elements should be gradually received in this case.
        Mutually exclusive with `complete`.
        """
        if self._results and not all(isinstance(result, Unknown) for result in self._results):
            raise InvalidCompilerState(
                self, "list comprehension helper got set_unknown after some (known) elements where received"
            )
        self.final_result.set_value(Unknown(self.statement), self.statement.location)

    def complete(self, all_values: abc.Sequence[object], resolver: Resolver, queue: QueueScheduler) -> None:
        """
        Indicate that all results have been received. No further calls to `receive_result` should be done after this.
        Mutually exclusive with `set_unknown`.
        """
        if self._results:
            if self.lhs is None:
                # We should only have received previous results in gradual mode, if any gradual results were received in
                # non-gradual mode, this indicates a bug in the compiler, likely in this class
                raise InvalidCompilerState(self, "list comprehension helper received gradual results in non-gradual mode")
            if len(self._results) != len(all_values):
                raise InvalidCompilerState(self, "list comprehension helper received some but not all values gradually")
        else:
            for value in all_values:
                self.receive_result(value, location=self.statement.location)

        RawUnit(queue, resolver, dict(enumerate(self._results)), resumer=self)

    def resume(self, requires: dict[object, VariableABC[object]], resolver: Resolver, queue: QueueScheduler) -> None:
        def get(variable: VariableABC[object]) -> Optional[abc.Sequence[object]]:
            value: object = variable.get_value()
            return None if value is ListComprehensionGuard.GUARD else value if isinstance(value, list) else [value]

        # collect all element value expressions' results and write them to the final result variable
        self.final_result.set_value(
            list(
                itertools.chain.from_iterable(value for variable in requires.values() if (value := get(variable)) is not None)
            ),
            self.statement.location,
        )


class If(RequiresEmitStatement):
    """
    An if Statement
    """

    __slots__ = ("condition", "if_branch", "else_branch")

    def __init__(self, condition: ExpressionStatement, if_branch: BasicBlock, else_branch: BasicBlock) -> None:
        super().__init__()
        self.condition: ExpressionStatement = condition
        self.if_branch: BasicBlock = if_branch
        self.else_branch: BasicBlock = else_branch

    def __repr__(self) -> str:
        return "If"

    def normalize(self) -> None:
        self.condition.normalize()
        self.if_branch.normalize()
        self.else_branch.normalize()
        self.anchors.extend(self.condition.get_anchors())
        self.anchors.extend(self.if_branch.get_anchors())
        self.anchors.extend(self.else_branch.get_anchors())
        self._own_eager_promises = [*self.if_branch.get_eager_promises(), *self.else_branch.get_eager_promises()]

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(super().get_all_eager_promises(), self.condition.get_all_eager_promises())

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)
        requires.update(self.condition.requires_emit(resolver, queue))
        return requires

    def execute(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        Evaluate this statement.
        """
        super().execute(requires, resolver, queue)
        cond: object = self.condition.execute(requires, resolver, queue)
        if isinstance(cond, Unknown):
            return None
        try:
            inmanta_type.Bool().validate(cond)
        except RuntimeException as e:
            e.set_statement(self)
            e.msg = "Invalid value `%s`: the condition for an if statement can only be a boolean expression" % cond
            raise e
        # schedule appropriate branch body
        branch: BasicBlock = self.if_branch if cond else self.else_branch
        xc = ExecutionContext(branch, resolver.for_namespace(branch.namespace))
        xc.emit(queue)
        return None

    def nested_blocks(self) -> Iterator["BasicBlock"]:
        yield self.if_branch
        yield self.else_branch


class ConditionalExpression(ExpressionStatement):
    """
    A conditional expression similar to Python's `x if c else y`.
    """

    __slots__ = ("condition", "if_expression", "else_expression")

    def __init__(
        self, condition: ExpressionStatement, if_expression: ExpressionStatement, else_expression: ExpressionStatement
    ) -> None:
        super().__init__()
        self.condition: ExpressionStatement = condition
        self.if_expression: ExpressionStatement = if_expression
        self.else_expression: ExpressionStatement = else_expression

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        self.condition.normalize()
        # pass on lhs_attribute to branches
        self.if_expression.normalize(lhs_attribute=lhs_attribute)
        self.else_expression.normalize(lhs_attribute=lhs_attribute)
        self.anchors.extend(self.condition.get_anchors())
        self.anchors.extend(self.if_expression.get_anchors())
        self.anchors.extend(self.else_expression.get_anchors())
        self._own_eager_promises = [
            *self.if_expression.get_all_eager_promises(),
            *self.else_expression.get_all_eager_promises(),
        ]

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(super().get_all_eager_promises(), self.condition.get_all_eager_promises())

    def requires(self) -> list[str]:
        return list(chain.from_iterable(sub.requires() for sub in [self.condition, self.if_expression, self.else_expression]))

    def requires_emit(
        self, resolver: Resolver, queue: QueueScheduler, *, lhs: Optional[ResultCollector[object]] = None
    ) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)

        # This ResultVariable will receive the result of this expression
        result: ResultVariable[object] = ResultVariable()

        # Schedule execution to resume when the condition can be executed
        resumer: RawResumer = ConditionalExpressionResumer(self, result, lhs=lhs)
        self.copy_location(resumer)
        RawUnit(queue, resolver, self.condition.requires_emit(resolver, queue), resumer)

        # Wait for the result variable to be populated
        requires[self] = result
        return requires

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector[object]
    ) -> dict[object, VariableABC[object]]:
        return self.requires_emit(resolver, queue, lhs=resultcollector)

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self]

    def execute_direct(self, requires: abc.Mapping[str, object]) -> object:
        condition_value: object = self.condition.execute_direct(requires)
        if isinstance(condition_value, Unknown):
            return Unknown(self)
        if not isinstance(condition_value, bool):
            raise RuntimeException(
                self, "Invalid value `%s`: the condition for a conditional expression must be a boolean expression"
            )
        return (self.if_expression if condition_value else self.else_expression).execute_direct(requires)

    def pretty_print(self) -> str:
        return "{} ? {} : {}".format(
            self.condition.pretty_print(),
            self.if_expression.pretty_print(),
            self.else_expression.pretty_print(),
        )

    def __repr__(self) -> str:
        return f"{self.condition} ? {self.if_expression} : {self.else_expression}"


class ConditionalExpressionResumer(RawResumer):
    __slots__ = ("expression", "condition_value", "result", "lhs")

    def __init__(
        self, expression: ConditionalExpression, result: ResultVariable, *, lhs: Optional[ResultCollector[object]] = None
    ) -> None:
        super().__init__()
        self.expression: ConditionalExpression = expression
        self.condition_value: Optional[bool] = None
        self.result: ResultVariable = result
        self.lhs: Optional[ResultCollector[object]] = lhs

    def resume(self, requires: dict[object, VariableABC[object]], resolver: Resolver, queue: QueueScheduler) -> None:
        if self.condition_value is None:
            condition_value: object = self.expression.condition.execute(
                {k: v.get_value() for k, v in requires.items()}, resolver, queue
            )
            if isinstance(condition_value, Unknown):
                self.result.set_value(Unknown(self), self.location)
                return
            if not isinstance(condition_value, bool):
                raise RuntimeException(
                    self, "Invalid value `%s`: the condition for a conditional expression must be a boolean expression"
                )
            self.condition_value = condition_value

            # Schedule execution of appropriate subexpression
            subexpression: ExpressionStatement = (
                self.expression.if_expression if self.condition_value else self.expression.else_expression
            )
            subexpression_requires: dict[object, VariableABC[object]] = (
                subexpression.requires_emit(resolver, queue)
                if self.lhs is None
                else subexpression.requires_emit_gradual(resolver, queue, self.lhs)
            )
            RawUnit(
                queue,
                resolver,
                subexpression_requires,
                self,
            )
        else:
            value: object = (
                self.expression.if_expression if self.condition_value else self.expression.else_expression
            ).execute({k: v.get_value() for k, v in requires.items()}, resolver, queue)
            self.result.set_value(value, self.location)


class IndexAttributeMissingInConstructorException(TypingException):
    """
    Raised when an index attribute was not set in the constructor call for an entity.
    """

    def __init__(self, stmt: Optional[Locatable], entity: "Entity", unset_attributes: abc.Sequence[str]):
        if not unset_attributes:
            raise Exception("Argument `unset_attributes` should contain at least one element")
        error_message = self._get_error_message(entity, unset_attributes)
        super().__init__(stmt, error_message)

    def _get_error_message(self, entity: "Entity", unset_attributes: abc.Sequence[str]) -> str:
        exc_message = "Invalid Constructor call:"
        for attribute_name in unset_attributes:
            attribute: Optional[Attribute] = entity.get_attribute(attribute_name)
            assert attribute is not None  # Make mypy happy
            attribute_kind = "relation" if isinstance(attribute, RelationAttribute) else "attribute"
            exc_message += (
                f"\n\t* Missing {attribute_kind} '{attribute.name}'. "
                f"The {attribute_kind} {entity.get_full_name()}.{attribute.name} is part of an index."
            )
        return exc_message


class Constructor(ExpressionStatement):
    """
    This class represents the usage of a constructor to create a new object.

    :param class_type: The type of the object that is created by this
        constructor call.
    """

    __slots__ = (
        "class_type",
        "__attributes",
        "__attribute_locations",
        "__wrapped_kwarg_attributes",
        "location",
        "type",
        "_self_ref",
        "_lhs_attribute",
        "_required_dynamic_args",
        "_direct_attributes",
        "_indirect_attributes",
    )

    def __init__(
        self,
        class_type: LocatableString,
        attributes: list[tuple[LocatableString, ExpressionStatement]],
        wrapped_kwargs: list["WrappedKwargs"],
        location: Location,
        namespace: Namespace,
    ) -> None:
        super().__init__()
        self.class_type = class_type
        self.__attributes: dict[str, ExpressionStatement] = {}
        self.__attribute_locations: dict[str, LocatableString] = {}
        self.__wrapped_kwarg_attributes: list[WrappedKwargs] = wrapped_kwargs
        self.location = location
        self.namespace = namespace
        for a in attributes:
            self.add_attribute(a[0], a[1])
        self.type: Optional["Entity"] = None
        self._self_ref: "Reference" = Reference(
            LocatableString(str(uuid.uuid4()), Range("__internal__", 1, 1, 1, 1), -1, self.namespace)
        )
        self._lhs_attribute: Optional[AttributeAssignmentLHS] = None
        self._required_dynamic_args: list[str] = []  # index attributes required from kwargs or lhs_attribute

        self._direct_attributes: dict[str, ExpressionStatement] = {}
        self._indirect_attributes: dict[str, ExpressionStatement] = {}

    def pretty_print(self) -> str:
        return "{}({})".format(
            self.class_type,
            ",".join(
                chain(
                    (f"{k}={v.pretty_print()}" for k, v in self.attributes.items()),
                    ("**%s" % kwargs.pretty_print() for kwargs in self.wrapped_kwargs),
                )
            ),
        )

    def _normalize_rhs(self, index_attributes: abc.Set[str]) -> None:
        assert self.type is not None  # Make mypy happy
        for k, v in self.__attributes.items():
            attr = self.type.get_attribute(k)
            if attr is None:
                raise TypingException(self.__attribute_locations[k], f"no attribute {k} on type {self.type.get_full_name()}")
            type_hint = attr.get_type().get_base_type()
            # don't notify the rhs for index attributes because it won't be able to resolve the reference
            # (index attributes need to be resolved before the instance can be constructed)
            v.normalize(
                lhs_attribute=AttributeAssignmentLHS(self._self_ref, k, type_hint) if k not in index_attributes else None
            )
            self.anchors.extend(v.anchors)
        for wrapped_kwargs in self.wrapped_kwargs:
            wrapped_kwargs.normalize()

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        self.type = self._resolve_type(lhs_attribute)
        self.anchors.append(TypeReferenceAnchor(self.type.namespace, self.class_type))
        inindex: abc.MutableSet[str] = set()

        all_attributes = dict(self.type.get_default_values())
        all_attributes.update(self.__attributes)

        # now check that all variables that have indexes on them, are already
        # defined and add the instance to the index
        for index in self.type.get_indices():
            for attr in index:
                if attr not in all_attributes:
                    self._required_dynamic_args.append(attr)
                    continue
                inindex.add(attr)

        if self._required_dynamic_args:
            # Limit dynamic compile-time overhead: ignore lhs if this constructor doesn't need it for instantiation.
            # Concretely, only store it if not all index attributes are explicitly set in the constructor.
            self._lhs_attribute = lhs_attribute
            # raise an exception if there are more required dynamic arguments than could be provided by the kwargs and
            # lhs attribute. If this passes but the kwargs and/or lhs attribute don't in fact provide the required arguments,
            # an exception is raised during execution.
            if not self.wrapped_kwargs and (self._lhs_attribute is None or len(self._required_dynamic_args) > 1):
                raise IndexAttributeMissingInConstructorException(self, self.type, self._required_dynamic_args)

        self._normalize_rhs(inindex)

        for k, v in all_attributes.items():
            attribute = self.type.get_attribute(k)
            if attribute is None:
                raise TypingException(self.__attribute_locations[k], f"no attribute {k} on type {self.type.get_full_name()}")
            if k not in inindex:
                self._indirect_attributes[k] = v
            else:
                self._direct_attributes[k] = v

        self._own_eager_promises = list(
            chain.from_iterable(subconstructor.get_all_eager_promises() for subconstructor in self.type.get_sub_constructor())
        )

    def _resolve_type(self, lhs_attribute: Optional[AttributeAssignmentLHS]) -> "Entity":
        """Type hint handling"""

        # First normal resolution
        resolver_failure: Optional[TypeNotFoundException] = None
        local_type: "Optional[Entity]" = None
        try:
            tp = self.namespace.get_type(self.class_type)
            assert isinstance(
                tp, inmanta.ast.entity.Entity
            ), "Should not happen because all entity types start with a capital letter"
            local_type = tp
        except TypeNotFoundException as e:
            resolver_failure = e

        # Do we have hint context?
        # We only work with unqualified names for hinting
        if lhs_attribute is not None and lhs_attribute.type_hint is not None:
            # We can do type hinting here
            type_hint = lhs_attribute.type_hint
            if not isinstance(type_hint, inmanta.ast.entity.Entity):
                # This is a type error, we are a constructor for an entity but we should not be!
                raise TypingException(
                    self,
                    f"Can not assign a value of type {self.class_type} "
                    f"to a variable of type {str(lhs_attribute.type_hint)}",
                )
            elif local_type is not None:
                # always prefer local type, raise an exception if it is of an incorrect type
                if not type_hint.is_subclass(local_type, strict=False):
                    raise TypingException(
                        self,
                        f"Can not assign a value of type {str(local_type)} "
                        f"to a variable of type {str(lhs_attribute.type_hint)}",
                    )
                return local_type
            elif "::" not in str(self.class_type):
                # Consider the hint type
                base_types = [type_hint]
                # Find all correct types with the matching unqualified name
                candidates = {
                    entity
                    for entity in chain(base_types, type_hint.get_all_child_entities())
                    if entity.name == str(self.class_type)
                }
                if len(candidates) > 1:
                    # To many options, inheritance may cause this to break a working model due to dependency update
                    raise AmbiguousTypeException(self.class_type, list(candidates))
                elif len(candidates) == 1:
                    # One, nice
                    return next(iter(candidates))
        elif local_type is not None:
            return local_type

        # No matching types found: pretend nothing happened, reraise original exception
        assert resolver_failure is not None  # make mypy happy
        raise resolver_failure

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(
            super().get_all_eager_promises(),
            *(subexpr.get_all_eager_promises() for subexpr in chain(self.attributes.values(), self.wrapped_kwargs)),
        )

    def requires(self) -> list[str]:
        out = [req for (k, v) in self.__attributes.items() for req in v.requires()]
        out.extend(req for kwargs in self.__wrapped_kwarg_attributes for req in kwargs.requires())
        out.extend(req for (k, v) in self.get_default_values().items() for req in v.requires())
        return out

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)
        # direct
        direct = [x for x in self._direct_attributes.items()]

        direct_requires = {rk: rv for (k, v) in direct for (rk, rv) in v.requires_emit(resolver, queue).items()}
        direct_requires.update(
            {rk: rv for kwargs in self.__wrapped_kwarg_attributes for (rk, rv) in kwargs.requires_emit(resolver, queue).items()}
        )
        if self._lhs_attribute is not None:
            direct_requires.update(
                # if lhs_attribute is set, it is likely required for construction (only exception is if it is in kwargs)
                self._lhs_attribute.instance.requires_emit(resolver, queue)
            )
        LOGGER.log(
            LOG_LEVEL_TRACE, "emitting constructor for %s at %s with %s", self.class_type, self.location, direct_requires
        )
        requires.update(direct_requires)

        graph: Optional[DataflowGraph] = resolver.dataflow_graph
        if graph is not None:
            node: dataflow.InstanceNodeReference = self._register_dataflow_node(graph)
            # TODO: also add wrapped_kwargs
            for k, v in chain(self._direct_attributes.items(), self._indirect_attributes.items()):
                node.assign_attribute(k, v.get_dataflow_node(graph), self, graph)

        return requires

    def _collect_required_dynamic_arguments(
        self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler
    ) -> abc.Mapping[str, object]:
        """
        Part of the execute flow: returns values for kwargs and the inverse relation derived from the lhs for which this
        constructor is the rhs, if appliccable.
        """
        type_class = self.type
        assert type_class

        # kwargs
        kwarg_attrs: dict[str, object] = {}
        for kwargs in self.wrapped_kwargs:
            for k, v in kwargs.execute(requires, resolver, queue):
                if k in self.attributes or k in kwarg_attrs:
                    raise RuntimeException(
                        self, f"The attribute {k} is set twice in the constructor call of {self.class_type}."
                    )
                attribute = type_class.get_attribute(k)
                if attribute is None:
                    raise TypingException(self, f"no attribute {k} on type {type_class.get_full_name()}")
                kwarg_attrs[k] = v

        lhs_inverse_assignment: Optional[tuple[str, object]] = None
        # add inverse relation if it is part of an index
        if self._lhs_attribute is not None:
            lhs_instance: object = self._lhs_attribute.instance.execute(requires, resolver, queue)
            if not isinstance(lhs_instance, Instance):
                # bug in internal implementation
                raise Exception("Invalid state: received lhs_attribute that is not an instance")
            lhs_attribute: Optional[Attribute] = lhs_instance.get_type().get_attribute(self._lhs_attribute.attribute)
            if not isinstance(lhs_attribute, RelationAttribute):
                # bug in the model
                raise RuntimeException(
                    self,
                    (
                        f"Attempting to assign constructor of type {type_class} to attribute that is not a relation attribute:"
                        f" {lhs_attribute} on {lhs_instance}"
                    ),
                )
            inverse: Optional[RelationAttribute] = lhs_attribute.end
            if (
                inverse is not None
                and inverse.name not in self._direct_attributes
                # in case of a double set, prefer kwargs: double set will be raised when the bidirectional relation is set by
                # the LHS
                and inverse.name not in kwarg_attrs
                and inverse.name in chain.from_iterable(type_class.get_indices())
                and (inverse.entity == type_class or type_class.is_parent(inverse.entity))
            ):
                lhs_inverse_assignment = (inverse.name, lhs_instance)

        late_args = {**dict([lhs_inverse_assignment] if lhs_inverse_assignment is not None else []), **kwarg_attrs}
        missing_attrs: abc.Sequence[str] = [attr for attr in self._required_dynamic_args if attr not in late_args]
        if missing_attrs:
            raise IndexAttributeMissingInConstructorException(self, type_class, missing_attrs)
        return late_args

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> Instance:
        """
        Evaluate this statement.
        """
        LOGGER.log(LOG_LEVEL_TRACE, "executing constructor for %s at %s", self.class_type, self.location)

        # the type to construct
        type_class = self.type
        assert type_class

        # kwargs and implicit inverse from lhs
        late_args: abc.Mapping[str, object] = self._collect_required_dynamic_arguments(requires, resolver, queue)

        # Schedule all direct attributes for direct execution. The kwarg keys and the direct_attributes keys are disjoint
        # because a RuntimeException is raised above when they are not.
        direct_attributes: dict[str, object] = {
            k: v.execute(requires, resolver, queue) for (k, v) in self._direct_attributes.items()
        }
        direct_attributes.update(late_args)

        # Override defaults with kwargs. The kwarg keys and the indirect_attributes keys are disjoint because a RuntimeException
        # is raised above when they are not.
        indirect_attributes: dict[str, ExpressionStatement] = {
            k: v for k, v in self._indirect_attributes.items() if k not in late_args
        }

        # check if the instance already exists in the index (if there is one)
        instances: list[Instance] = []
        # register any potential index collision
        collisions: abc.MutableMapping[tuple[str, ...], Instance] = {}
        for index in type_class.get_indices():
            params = []
            for attr in index:
                params.append((attr, direct_attributes[attr]))

            obj: Optional[Instance] = type_class.lookup_index(params, self)

            if obj is not None:
                if obj.get_type() != type_class:
                    raise DuplicateException(self, obj, "Type found in index is not an exact match")
                instances.append(obj)
                collisions[tuple(index)] = obj

        object_instance: Instance
        graph: Optional[DataflowGraph] = resolver.dataflow_graph
        if len(instances) > 0:
            if graph is not None:
                graph.add_index_match(
                    chain(
                        [self.get_dataflow_node(graph)],
                        (i.instance_node for i in instances if i.instance_node is not None),
                    )
                )

            # ensure that instances are all the same objects
            first = instances[0]
            for i in instances[1:]:
                if i != first:
                    raise IndexCollisionException(
                        msg=("Inconsistent indexes detected!\n"),
                        constructor=self,
                        collisions=collisions,
                    )

            object_instance = first
            self.copy_location(object_instance)
            for k, v in direct_attributes.items():
                object_instance.set_attribute(k, v, self.location)
        else:
            # create the instance
            object_instance = type_class.get_instance(
                direct_attributes, resolver, queue, self.location, self.get_dataflow_node(graph) if graph is not None else None
            )

        # deferred execution for indirect attributes
        # inject implicit reference to this instance so attributes can resolve the lhs_attribute we promised in _normalize_rhs
        self_var: ResultVariable[Instance] = ResultVariable()
        self_var.set_value(object_instance, self.location)
        self_resolver: VariableResolver = VariableResolver(resolver, self._self_ref.name, self_var)
        for attributename, valueexpression in indirect_attributes.items():
            var = object_instance.get_attribute(attributename)
            if var.is_multi():
                # gradual only for multi
                # to preserve order on lists used in attributes
                # while allowing gradual execution on relations
                reqs = valueexpression.requires_emit_gradual(
                    self_resolver, queue, GradualSetAttributeHelper(self, object_instance, attributename, var)
                )
            else:
                reqs = valueexpression.requires_emit(self_resolver, queue)
            SetAttributeHelper(queue, self_resolver, var, reqs, valueexpression, self, object_instance, attributename)

        # generate an implementation
        for stmt in type_class.get_sub_constructor():
            stmt.emit(object_instance, queue)

        object_instance.trackers.append(queue.get_tracker())

        return object_instance

    def add_attribute(self, lname: LocatableString, value: ExpressionStatement) -> None:
        """
        Add an attribute to this constructor call
        """
        name = str(lname)
        if name not in self.__attributes:
            self.__attributes[name] = value
            self.__attribute_locations[name] = lname
            self.anchors.append(AttributeReferenceAnchor(lname.get_location(), lname.namespace, self.class_type, name))
            self.anchors.extend(value.get_anchors())
        else:
            raise RuntimeException(self, f"The attribute {name} in the constructor call of {self.class_type} is already set.")

    def get_attributes(self) -> dict[str, ExpressionStatement]:
        """
        Get the attribtues that are set for this constructor call
        """
        return self.__attributes

    def get_wrapped_kwargs(self) -> list["WrappedKwargs"]:
        """
        Get the wrapped kwargs that are set for this constructor call
        """
        return self.__wrapped_kwarg_attributes

    attributes = property(get_attributes)
    wrapped_kwargs = property(get_wrapped_kwargs)

    def _register_dataflow_node(self, graph: DataflowGraph) -> dataflow.InstanceNodeReference:
        """
        Registers the dataflow node for this constructor to the graph if it does not exist yet.
        Returns the node.
        """

        def get_new_node() -> dataflow.InstanceNode:
            assert self.type is not None
            return dataflow.InstanceNode(self.type.get_all_attribute_names())

        assert self.type is not None
        return graph.own_instance_node_for_responsible(self.type, self, get_new_node).reference()

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.InstanceNodeReference:
        return self._register_dataflow_node(graph)

    def __repr__(self) -> str:
        """
        The representation of the this statement
        """
        return "Construct(%s)" % (self.class_type)


class WrappedKwargs(ExpressionStatement):
    """
    Keyword arguments wrapped in a dictionary.
    Separate AST node for the type check it provides in the execute method.
    """

    __slots__ = ("dictionary",)

    def __init__(self, dictionary: ExpressionStatement) -> None:
        super().__init__()
        self.dictionary: ExpressionStatement = dictionary

    def __repr__(self) -> str:
        return "**%s" % repr(self.dictionary)

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        self.dictionary.normalize()

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(super().get_all_eager_promises(), self.dictionary.get_all_eager_promises())

    def requires(self) -> list[str]:
        return self.dictionary.requires()

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC[object]] = super().requires_emit(resolver, queue)
        requires.update(self.dictionary.requires_emit(resolver, queue))
        return requires

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> list[tuple[str, object]]:
        dct: object = self.dictionary.execute(requires, resolver, queue)
        if not isinstance(dct, dict):
            raise TypingException(self, "The ** operator can only be applied to dictionaries")
        return list(dct.items())


class IndexCollisionException(RuntimeException):
    """Exception raised when an index collision is detected"""

    def __init__(
        self,
        msg: str,
        collisions: abc.Mapping[tuple[str, ...], Instance],
        constructor: Constructor,
    ) -> None:
        super().__init__(stmt=constructor, msg=msg)
        self.collisions: abc.Mapping[tuple[str, ...], Instance] = collisions
        self.constructor: Constructor = constructor

    def importantance(self) -> int:
        return 10
