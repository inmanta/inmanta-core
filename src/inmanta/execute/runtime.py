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

from abc import abstractmethod
from collections.abc import Hashable, Sequence, Set
from typing import TYPE_CHECKING, Deque, Generic, List, Literal, NewType, Optional, TypeVar, Union, cast

import inmanta.ast
import inmanta.ast.attribute  # noqa: F401 (pyflakes does not recognize partially qualified access ast.attribute)
from inmanta import ast, references
from inmanta.ast import (
    AttributeException,
    CompilerException,
    DoubleSetException,
    Locatable,
    Location,
    ModifiedAfterFreezeException,
    Namespace,
    NotFoundException,
    OptionalValueException,
    RuntimeException,
)
from inmanta.ast.type import Type
from inmanta.execute import dataflow
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.util import NoneValue, Unknown

if TYPE_CHECKING:
    from inmanta.ast.blocks import BasicBlock
    from inmanta.ast.entity import Entity, Implementation
    from inmanta.ast.statements import RawResumer, RequiresEmitStatement, Resumer, Statement
    from inmanta.compiler import Compiler
    from inmanta.execute.scheduler import PrioritisedDelayedResultVariableQueue


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


class ResultCollector(Generic[T_contra]):
    """
    Helper interface for gradual execution. Should be attached as a listener to a ResultVariable, which will then call
    receive_result whenever it receives a new value.
    """

    __slots__ = ()

    def pure_gradual(self) -> bool:
        """
        Returns true iff this result collector represents pure gradual execution, i.e. all progress comes from new values and
        no progress is expected as a result of the variable being frozen.

        This is a static property of a result collector, i.e. this method will always have the same result at any point within
        the lifetime of the instance.
        """
        return True

    def receive_result(self, value: T_contra, location: Location) -> bool:
        """
        Receive a single value for gradual execution. Called once for each value that is part of the result. May be `null` or
        Unknown. Does not distinguish between Unknown as an element of a list and Unknown as a top-level value.

        :return: Whether this collector is complete, i.e. it does not need to receive any further results and its associated
            waiter will no longer cause progress. Once this is signalled, this instance should get no further results.
        """
        raise NotImplementedError()

    def receive_result_flatten(self, value: Union[T_contra, Sequence[T_contra]], location: Location) -> bool:
        """
        Receive one or more values for gradual execution. When a list is passed, its values will be passed to receive_result
        one by one. Otherwise the value itself is passed unmodified.

        :return: Whether this collector is complete, i.e. it does not need to receive any further results and its associated
            waiter will no longer cause progress. Once this is signalled, this instance should get no further results.
        """
        for subvalue in value if isinstance(value, list) else [value]:
            done: bool = self.receive_result(subvalue, location)
            if done:
                return True
        return False


class IPromise:
    """
    A promise to the owner to provide a value or progression towards a value in some way, either directly or indirectly.
    To provide strict provider tracking, overpromising is allowed in case of uncertainty as to whether progression towards
    a value will be made, as long as progression towards certainty is made.
    """

    __slots__ = ()


class ISetPromise(IPromise, Generic[T]):
    """
    A promise to the owner to set a value.
    """

    __slots__ = ()

    @abstractmethod
    def set_value(self, value: T, location: Location) -> None:
        """
        Fulfills this promise by setting the owner's value and notifying the owner of the promise's completion.
        """


class ProgressionPromise(IPromise):
    """
    A promise from a provider to the owner to progress towards setting a value, for example by emitting additional statements.
    """

    __slots__ = ("provider", "owner")

    def __init__(self, owner: "ResultVariable[T]", provider: "Statement") -> None:
        self.owner: ResultVariable[T] = owner
        self.provider: Statement = provider

    def fulfill(self) -> None:
        """
        Fulfills this promise by notifying the owner. No further progression is expected. Idempotent.
        """
        self.owner.fulfill(self)


class VariableABC(Generic[T_co]):
    """
    Abstract base class for variables that get passed around the AST nodes' methods via waiters.
    """

    __slots__ = ()

    def is_ready(self) -> bool:
        """
        Returns true iff this variable does not expect any more values.
        """
        raise NotImplementedError()

    def get_value(self) -> T_co:
        """
        Returns the value object for this variable

        :raises OptionalValueException: This is an optional variable that has not received a value (or explicit `null`).
        """
        raise NotImplementedError()

    def listener(self, resultcollector: ResultCollector[T_co], location: Location) -> bool:
        """
        Add a listener to report new values to. If the variable already has a value, this is reported immediately. Explicit
        assignments of `null` will not be reported.

        Each listener is expected to register one associated waiter to track completeness. The progress potential implementation
        is based on this invariant.

        :param resultcollector: The collector for the values of this variable.
        :param location: The location associated with this listener.
        :return: True iff this variable will report values to the listener. Simple variables may not implement the listen
            capability and will return False. A variable will always return the same value regardless of the parameters.
        """
        return False

    def waitfor(self, waiter: "Waiter") -> None:
        """
        Informs this variable that a waiter waits on its value. Once the variable receives a value, it should inform the waiter.
        """
        raise NotImplementedError()

    def get_progression_promise(self, provider: "Statement") -> Optional[ProgressionPromise]:
        """
        Acquires a promise to progress this variable without necessarily setting a value. It is allowed to acquire a progression
        promise greedily (overpromise) when a provider is likely to produce progress. The promise should then be fulfilled as
        soon as it is known that no further progress will be made.

        Returns None if this variable does not track progression promises.

        e.g. a progression promise could be acquired by a conditional statement that might emit a new assignment statement for
        this variable. As soon as the condition is evaluated this promise should be fulfilled.

        This overpromising semantics allows for more strict promise tracking, providing more certainty on variable completeness
        at the cost of disallowing circular logic.
        """
        return None


class WrappedValueVariable(VariableABC[T]):
    """
    Variable that holds a single value that is known at construction. Used to wrap values where a VariableABC is expected.
    """

    __slots__ = ("value",)

    def __init__(self, value: T) -> None:
        self.value: T = value

    def is_ready(self) -> bool:
        return True

    def get_value(self) -> T:
        return self.value

    def listener(self, resultcollector: ResultCollector[T], location: Location) -> Literal[True]:
        resultcollector.receive_result(self.value, location)
        return True

    def waitfor(self, waiter: "Waiter") -> None:
        waiter.ready(self)


class ResultVariable(VariableABC[T], ResultCollector[T], ISetPromise[T]):
    """
    A ResultVariable is like a future
     - it has a list of waiters
     - when a value is set, the waiters are notified,
        they decrease their wait count and
        queue themselves when their wait count becomes 0

    If a type is set on a result variable, setting a value of another type will produce an exception.

    In order to assist heuristic evaluation, result variables keep track of any statement that will assign a value to it
    """

    location: Location

    __slots__ = ("location", "provider", "waiters", "value", "hasValue", "type", "_node")

    def __init__(self, value: Optional[T] = None) -> None:
        self.waiters: "List[Waiter]" = []
        self.value: Optional[T] = value
        self.hasValue: bool = False
        self.type: Optional[Type] = None
        self._node: Optional[dataflow.AssignableNodeReference] = None

    def set_type(self, mytype: Type) -> None:
        self.type = mytype

    def get_promise(self, provider: "Statement") -> ISetPromise[T]:
        """
        Acquire a promise to set a value for this variable. To fulfill the promise and set the promised value for this
        variable, set the value on the promise object.
        """
        return self

    def fulfill(self, promise: IPromise) -> None:
        """
        Considers the given promise fulfilled. Idempotent. Should only be called with promises that were handed out by thie
        variable.
        """
        # plain ResultVariable does not track promises -> simply return

    def is_ready(self) -> bool:
        return self.hasValue

    def waitfor(self, waiter: "Waiter") -> None:
        if self.is_ready():
            waiter.ready(self)
        else:
            self.waiters.append(waiter)

    def set_value(self, value: T, location: Location, recur: bool = True) -> None:
        """
        Set the value for this result variable.

        :param recur: If True, recur on the other side of this variable if it is part of a bidirectional relation.
        """
        if self.hasValue:
            if self.value != value:
                raise DoubleSetException(self, None, value, location)
            else:
                return
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
        self.location = location
        self.hasValue = True
        for waiter in self.waiters:
            waiter.ready(self)

        # prevent memory leaks
        self.waiters = None

    def get_value(self) -> T:
        if not self.hasValue:
            raise inmanta.ast.UnsetException("Value not available", self)

        return self.value

    def can_get(self) -> bool:
        return self.hasValue

    def freeze(self) -> None:
        pass

    def receive_result(self, value: T, location: Location) -> bool:
        return True

    def is_multi(self) -> bool:
        return False

    def set_dataflow_node(self, node: dataflow.AssignableNodeReference) -> None:
        assert self._node is None or self._node == node
        self._node = node
        self._node.set_result_variable(self)

    def get_dataflow_node(self) -> dataflow.AssignableNodeReference:
        assert self._node is not None, "assertion error at %s.get_dataflow_node() in ResultVariable" % self
        return self._node


class ListElementVariable(ResultVariable[T]):
    """
    Variable representing a single value in a gradually executable list. Can be resolved immediately and allows attaching
    listeners who will receive this single value.
    """

    def __init__(self, value: T, location: Location) -> None:
        super().__init__()
        self.set_value(value, location)

    def listener(self, resultcollector: ResultCollector[T], location: Location) -> Literal[True]:
        assert self.value is not None
        resultcollector.receive_result(self.value, location)
        return True


class ResultVariableProxy(VariableABC[T]):
    """
    A proxy for a reading from a ResultVariable that implements the VariableABC interface. Allows for assignment between
    variables without resolving the right hand side at the time of assignment. Supports a single listener to be registered
    at construction. This class will ensure that the connected variable's value(s) is (are) reported to the listener, even if
    the variable itself does not support listeners.
    This class does not support setting values or related operations such as acquiring progression promises.
    """

    __slots__ = ("variable", "_listener", "_waiters", "_notify_listeners")

    def __init__(
        self, variable: Optional[VariableABC[T]] = None, listener: Optional[tuple[ResultCollector[T], Location]] = None
    ) -> None:
        self.variable: Optional[VariableABC[T]] = variable
        self._listener: Optional[tuple[ResultCollector[T], Location]] = listener
        self._waiters: Optional[list["Waiter"]] = []
        # are we responsible for notifying listeners ourselves?
        self._notify_listeners: bool = False

    def connect(self, variable: VariableABC[T]) -> None:
        """
        Connect this proxy to a variable. A proxy can only be connected to a single variable.
        """
        if self.variable is not None and self.variable != variable:
            raise Exception("Trying to connect a variable to a proxy that is already connected to another variable.")
        self.variable = variable
        assert self._waiters is not None  # only set to None after a variable is connected to prevent data leaks
        if self._listener is not None:
            registered_listener: bool = self.variable.listener(*self._listener)
            if registered_listener:
                # clear listener to prevent data leaks
                self._listener = None
            else:
                # variable does not support listeners, we'll have to notify the listener ourselves
                self._notify_listeners = True
        for waiter in self._waiters:
            self.variable.waitfor(waiter)
        # clear waiters to prevent data leaks
        self._waiters = None

    def is_ready(self) -> bool:
        return self.variable is not None and self.variable.is_ready()

    def get_value(self) -> T:
        """
        Returns the value object for this variable
        """
        if self.variable is None:
            raise Exception(
                "Trying to get value for proxy variable that has not been connected yet. Use `waitfor` to wait for a value."
            )
        value: T = self.variable.get_value()
        if self._notify_listeners:
            assert self._listener is not None
            listener, location = self._listener
            # simple case: single value. Multi-value variables implement their own listener functionality
            listener.receive_result_flatten(value, location)
            # clean up: prevent data leaks and ensure listener is only notified once
            self._listener = None
            self._notify_listeners = False
        return value

    def listener(self, resultcollector: ResultCollector[T], location: Location) -> Literal[False]:
        # no need for this right now and implementing it greatly complicates the logic of this class
        # a single listener can be registered at construction time
        return False

    def waitfor(self, waiter: "Waiter") -> None:
        """
        Informs this variable that a waiter waits on its value. Once the variable receives a value, it should inform the waiter.
        """
        if self.variable is None:
            assert self._waiters is not None  # only set to None after a variable is connected to prevent data leaks
            self._waiters.append(waiter)
        else:
            self.variable.waitfor(waiter)


class RelationAttributeVariable:
    """
    Abstract base class for variables associated with a relation attribute.
    """

    __slots__ = ()


class AttributeVariable(ResultVariable["Instance"], RelationAttributeVariable):
    """
    a result variable for a relation with arity 1

    when assigned a value, it will also assign a value to its inverse relation
    """

    __slots__ = ("attribute", "myself")

    def __init__(self, attribute: "ast.attribute.RelationAttribute", instance: "Instance"):
        self.attribute: ast.attribute.RelationAttribute = attribute
        self.myself: "Instance" = instance
        ResultVariable.__init__(self)

    def set_value(self, value: "Instance", location: Location, recur: bool = True) -> None:
        if self.hasValue:
            if self.value != value:
                raise DoubleSetException(self, None, value, location)
            else:
                return
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
        self.location = location
        self.hasValue = True
        # set counterpart
        if self.attribute.end and recur:
            assert isinstance(value, Instance)
            value.set_attribute(self.attribute.end.name, self.myself, location, False)
        for waiter in self.waiters:
            waiter.ready(self)
        self.waiters = None


class SetPromise(ISetPromise[T]):
    """
    A promise from a provider to the owner to set a value.
    """

    __slots__ = ("provider", "owner")

    def __init__(self, owner: "DelayedResultVariable[T]", provider: "Statement"):
        self.provider: "Optional[Statement]" = provider
        self.owner: DelayedResultVariable[T] = owner

    def set_value(self, value: T, location: Location) -> None:
        self.owner.set_value(value, location, recur=True)
        self.owner.fulfill(self)


class DelayedResultVariable(ResultVariable[T]):
    """
    DelayedResultVariable are ResultVariables of which it is unclear how many results will be set.

    i.e. there may be speculation about when they can be considered complete.

    When the freeze method is called, no more values will be accepted and
    the DelayedResultVariable will behave as a normal ResultVariable.

    When a DelayedResultVariable is definitely full, it freezes itself.

    DelayedResultVariable are queued with the scheduler at the point at which they might be complete.
    The scheduler can decide when to freeze them. A DelayedResultVariable  can be complete when
      - it contains enough elements
      - there are no providers which still have to provide some values (tracked inexactly)
        (a queue variable can be dequeued by the scheduler when a provider is added)
    """

    __slots__ = ("queued", "queues", "promises", "done_promises")

    def __init__(self, queue: "QueueScheduler", value: Optional[T] = None) -> None:
        ResultVariable.__init__(self, value)
        self.promises: Optional[list[IPromise]] = []
        self.done_promises: Optional[set[IPromise]] = set()
        self.queued = False
        self.queues = queue
        if self.can_get():
            self.queue()

    def get_promise(self, provider: "Statement") -> ISetPromise[T]:
        promise: ISetPromise[T] = SetPromise(self, provider)
        if self.promises is not None:
            # only track the promise if this variable has not been frozen yet.
            self.promises.append(promise)
        return promise

    def get_progression_promise(self, provider: "Statement") -> Optional[ProgressionPromise]:
        if self.promises is None:
            return None
        promise: ProgressionPromise = ProgressionPromise(self, provider)
        self.promises.append(promise)
        return promise

    def fulfill(self, promise: IPromise) -> None:
        if self.done_promises is None:
            # already frozen, no need to track promises anymore
            return
        self.done_promises.add(promise)
        if self.can_get():
            self.queue()

    def freeze(self) -> None:
        if self.hasValue:
            return
        self.queued = True
        self.hasValue = True
        for waiter in self.waiters:
            waiter.ready(self)
        # prevent memory leaks
        self.waiters = None
        self.queues = None
        self.promises = None
        self.done_promises = None

    def queue(self) -> None:
        if self.queued:
            return
        self.queued = True
        self.queues.add_possible(self)

    def unqueue(self) -> None:
        self.queued = False

    def get_waiting_providers(self) -> int:
        """How many values are definitely still waiting for"""
        if self.promises is None:
            # already frozen
            return 0
        # todo: optimize?
        assert self.done_promises is not None
        out = len(self.promises) - len(self.done_promises)
        if out < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: provide count negative")
        return out

    def get_progress_potential(self) -> int:
        """
        Returns the number of blocked waiters, meaning any waiters that may progress when this variable is frozen.
        """
        return len(self.waiters)


ListValue = Union["Instance", list["Instance"]]


class BaseListVariable(DelayedResultVariable[ListValue]):
    """
    List variable, but only the part that is independent of an instance
    """

    value: "List[Instance]"

    __slots__ = ("_listeners", "_nb_gradual_waiters")

    def __init__(self, queue: "QueueScheduler") -> None:
        # use dict for easy lookup with reliable ordering
        self._listeners: Optional[dict[ResultCollector["Instance"], None]] = {}
        # Cache count for waiters without progress potential. Meaning waiters associated with either a purely gradual
        # listener or with a listener that indicated it is done.
        self._nb_gradual_waiters: int = 0
        super().__init__(queue, [])

    def _set_value(self, value: ListValue, location: Location, recur: bool = True) -> bool:
        """
        First half of set_value, returns True if second half should run
        """
        if self.hasValue:
            if isinstance(value, list):
                if len(value) == 0:
                    # empty list terminates list addition
                    return False
                for subvalue in value:
                    if subvalue not in self.value:
                        raise ModifiedAfterFreezeException(
                            self,
                            instance=self.myself,
                            attribute=self.attribute,
                            value=value,
                            location=location,
                            reverse=not recur,
                        )
            elif value in self.value:
                return False
            else:
                raise ModifiedAfterFreezeException(
                    self, instance=self.myself, attribute=self.attribute, value=value, location=location, reverse=not recur
                )

        if isinstance(value, list):
            if len(value) == 0:
                # the values of empty lists need no processing,
                # but a set_value from an empty list may fulfill a promise, allowing this object to be queued
                if self.can_get():
                    self.queue()
            else:
                for v in value:
                    self.set_value(v, location, recur)
            return False

        if self.type is not None:
            self.type.validate(value)

        if value in self.value:
            # any set_value may fulfill a promise, allowing this object to be queued
            if self.can_get():
                self.queue()
            return False

        self.value.append(value)
        self._notify_listeners(value, location)

        return True

    def _notify_listeners(self, value: "Instance", location: Location) -> None:
        """
        Notifies all listeners about a new value. Deregisters any listeners that indicate they no longer wish to receive
        results.
        """
        assert self._listeners is not None
        for listener in list(self._listeners.keys()):
            done: bool = listener.receive_result(value, location)
            if done:
                if not listener.pure_gradual():
                    # listener used to have progress potential but not anymore
                    self._nb_gradual_waiters += 1
                # keep memory footprint minimal
                del self._listeners[listener]

    def set_value(self, value: ListValue, location: Location, recur: bool = True) -> None:
        if not self._set_value(value, location, recur):
            return
        if self.can_get():
            self.queue()

    def can_get(self) -> bool:
        return self.get_waiting_providers() == 0

    def receive_result(self, value: ListValue, location: Location) -> bool:
        self.set_value(value, location)
        return False

    def listener(self, resultcollector: ResultCollector["Instance"], location: Location) -> Literal[True]:
        for value in self.value:
            resultcollector.receive_result(value, location)
        if not self.hasValue:
            assert self._listeners is not None
            if resultcollector in self._listeners:
                # may happen in case of a duplicate assignment, e.g. `x.a = [y.a, y.a]`
                # consider the new one to have no progress potential because we don't track it separately
                self._nb_gradual_waiters += 1
                return True
            self._listeners[resultcollector] = None
            if resultcollector.pure_gradual():
                self._nb_gradual_waiters += 1
        return True

    def is_multi(self) -> bool:
        return True

    def get_progress_potential(self) -> int:
        # purely gradual waiters aren't blocked on this variable being frozen
        return len(self.waiters) - self._nb_gradual_waiters

    def freeze(self) -> None:
        super().freeze()
        # prevent memory leaks
        self._listeners = None

    def __str__(self) -> str:
        return "BaseListVariable %s" % (self.value)


# known issue: typed as ResultVariable[ListValue] but is actually ResultVariable[object]
class ListLiteral(BaseListVariable):
    """
    Transient variable to represent a list (of either constants or instances) literal (not a variable).
    Requires all providers to acquire a promise before the first gets fulfilled and in return provides accurate promise
    tracking and freezing. Instances of this class should never require forceful freezing.
    """

    __slots__ = ()

    def fulfill(self, promise: IPromise) -> None:
        """
        Fulfill a promise with 100% accurate promise tracking. Because of this class' invariant that all promises are
        acquired before the first is fulfilled, the list can safely be frozen once all registered promises have been fulfilled.
        """
        super().fulfill(promise)
        # 100% accurate promisse tracking
        if self.get_waiting_providers() == 0:
            self.freeze()

    def __str__(self) -> str:
        return "TempListVariable %s" % (self.value)


class ListVariable(BaseListVariable, RelationAttributeVariable):
    """
    ResultVariable that represents a list of instances associated with a relation attribute.
    """

    value: "List[Instance]"

    __slots__ = ("attribute", "myself")

    def __init__(self, attribute: "ast.attribute.RelationAttribute", instance: "Instance", queue: "QueueScheduler") -> None:
        self.attribute: ast.attribute.RelationAttribute = attribute
        self.myself: "Instance" = instance
        BaseListVariable.__init__(self, queue)

    def set_value(self, value: ListValue, location: Location, recur: bool = True) -> None:
        if isinstance(value, NoneValue):
            if len(self.value) > 0:
                exception: CompilerException = RuntimeException(
                    None,
                    "Trying to set relation attribute `%s` of instance `%s` to null but it has values `%s` assigned already"
                    % (self.attribute.name, self.myself, ", ".join(str(v) for v in self.value)),
                )
                exception.set_location(location)
                raise exception
            self.freeze()
            return
        try:
            if not self._set_value(value, location, recur):
                return
        except ModifiedAfterFreezeException as e:
            if len(self.value) == self.attribute.high:
                new_exception: CompilerException = RuntimeException(
                    None, f"Exceeded relation arity on attribute '{self.attribute.name}' of instance '{self.myself}'"
                )
                new_exception.set_location(location)
                raise new_exception
            raise e
        # set counterpart
        if self.attribute.end is not None and recur:
            value.set_attribute(self.attribute.end.name, self.myself, location, False)

        if self.attribute.high is not None:
            if len(self.value) > self.attribute.high:
                raise RuntimeException(
                    None, "List over full: max nr of items is %d, content is %s" % (self.attribute.high, self.value)
                )

            if self.attribute.high == len(self.value):
                self.freeze()

        if self.can_get():
            self.queue()

    def can_get(self) -> bool:
        return len(self.value) >= self.attribute.low and self.get_waiting_providers() == 0

    def __str__(self) -> str:
        return f"ListVariable {self.myself} {self.attribute} = {self.value}"

    def get_progress_potential(self) -> int:
        # Ensure that relationships with a relation precedence rule cannot end up in the zerowaiters queue
        # of the scheduler. We know the order in which those types can be frozen safely.
        return super().get_progress_potential() + int(self.attribute.has_relation_precedence_rules())


class OptionVariable(DelayedResultVariable["Instance"], RelationAttributeVariable):
    """
    Variable to hold the value for an optional relation (arity [0:1])
    """

    __slots__ = ("attribute", "myself", "location")

    def __init__(self, attribute: "ast.attribute.Attribute", instance: "Instance", queue: "QueueScheduler") -> None:
        self.value = None
        self.attribute: ast.attribute.RelationAttribute = attribute
        self.myself: "Instance" = instance
        self.location = None
        # Only call super after initialization of the above-mentioned attributes
        # because the self.queue() operation in DelayedResultVariable requires
        # self.attribute and self.myself to be set.
        DelayedResultVariable.__init__(self, queue)

    def _get_null_value(self) -> object:
        return None

    def set_value(self, value: object, location: Location, recur: bool = True) -> None:
        assert location is not None
        if self.hasValue:
            if self.value is None:
                if isinstance(value, NoneValue):
                    return
                else:
                    raise ModifiedAfterFreezeException(
                        self, instance=self.myself, attribute=self.attribute, value=value, location=location, reverse=not recur
                    )
            elif self.value != value:
                raise DoubleSetException(self, None, value, location)

        self._validate_value(value)

        if isinstance(value, Instance):
            # set counterpart
            if self.attribute.end is not None and recur:
                value.set_attribute(self.attribute.end.name, self.myself, location, False)

        self.value = value if not isinstance(value, NoneValue) else self._get_null_value()
        self.location = location
        self.freeze()

    def _validate_value(self, value: object) -> None:
        if isinstance(value, Unknown):
            return
        if isinstance(value, NoneValue):
            return
        if self.type is None:
            return
        self.type.validate(value)

    def can_get(self) -> bool:
        return self.get_waiting_providers() == 0

    def get_value(self) -> "Instance":
        result = DelayedResultVariable.get_value(self)
        if result is None:
            raise OptionalValueException(self.myself, self.attribute)
        return result

    def __str__(self) -> str:
        return f"OptionVariable {self.myself} {self.attribute} = {self.value}"

    def get_progress_potential(self) -> int:
        return super().get_progress_potential() + int(self.attribute.has_relation_precedence_rules())


WaiterSet = NewType("WaiterSet", Set["Waiter"])
"""
Set-like object with deterministic iteration order (maintains insert order).

Declared as NewType rather than an implementation of MutableSet for performance reasons (one order of magnitude).
Constructor is responsible for upholding the type's semantics.
"""


class QueueScheduler:
    """
    Object representing the compiler to the AST nodes. It provides access to the queueing mechanism and the type system.

    MUTABLE!
    """

    __slots__ = ("compiler", "runqueue", "waitqueue", "types", "_allwaiters")

    def __init__(
        self,
        compiler: "Compiler",
        runqueue: "Deque[Waiter]",
        waitqueue: "PrioritisedDelayedResultVariableQueue",
        types: dict[str, Type],
    ) -> None:
        self.compiler = compiler
        self.runqueue = runqueue
        self.waitqueue = waitqueue
        self.types = types
        # store internally as dict rather than set to achieve deterministic iteration order
        self._allwaiters: dict[Waiter, None] = {}

    @property
    def allwaiters(self) -> WaiterSet:
        return WaiterSet(self._allwaiters.keys())

    def add_running(self, item: "Waiter") -> None:
        self.runqueue.append(item)

    def add_possible(self, rv: DelayedResultVariable) -> None:
        self.waitqueue.append(rv)

    def get_compiler(self) -> "Compiler":
        return self.compiler

    def get_types(self) -> dict[str, Type]:
        return self.types

    def add_to_all(self, item: "Waiter") -> None:
        self._allwaiters[item] = None

    def remove_from_all(self, item: "Waiter") -> None:
        del self._allwaiters[item]


class Waiter:
    """
    Waiters represent an executable unit, that can be executed the result variables they depend on have their values.
    """

    __slots__ = ("waitcount", "queue", "done", "requires")

    requires: dict[object, VariableABC]

    def __init__(self, queue: QueueScheduler):
        self.waitcount = 1
        self.queue = queue
        self.queue.add_to_all(self)
        self.done = False

    def requeue_with_additional_requires(self, key: Hashable, waitable: ResultVariable) -> None:
        """
        Re-queue with an additional requirement
        """
        self.requires[key] = waitable
        self.waitfor(waitable)

    def waitfor(self, waitable: VariableABC[object]) -> None:
        self.waitcount = self.waitcount + 1
        waitable.waitfor(self)

    def ready(self, other: Union[ResultVariable, "Waiter"]) -> None:
        self.waitcount = self.waitcount - 1
        if self.waitcount == 0:
            self.queue.add_running(self)
        if self.waitcount < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: waitcount negative")

    def execute(self) -> None:
        pass


class ExecutionUnit(Waiter):
    """
    Basic assign statement:
     - Wait for a dict of requirements
     - Call the execute method on the expression, with a map of the resulting values
     - Assign the resulting value to the result variable

     @param provides: Whether to register this XU as provider to the result variable
    """

    __slots__ = ("result", "expression", "resolver", "queue_scheduler", "owner")

    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: "Resolver",
        result: ResultVariable[object],
        requires: dict[object, VariableABC],
        expression: "RequiresEmitStatement",
        owner: "Optional[Statement]" = None,
    ):
        Waiter.__init__(self, queue_scheduler)
        self.result: ISetPromise[object] = result.get_promise(expression)
        self.requires = requires
        self.expression = expression
        self.resolver = resolver
        self.queue_scheduler = queue_scheduler
        for r in requires.values():
            self.waitfor(r)
        self.ready(self)
        if owner is not None:
            self.owner = owner
        else:
            self.owner = expression

    def _unsafe_execute(self) -> None:
        requires = {k: v.get_value() for (k, v) in self.requires.items()}
        value = self.expression.execute(requires, self.resolver, self.queue_scheduler)
        self.result.set_value(value, self.expression.location)
        self.done = True

    def execute(self) -> None:
        try:
            self._unsafe_execute()
        except RuntimeException as e:
            e.set_statement(self.owner, False)
            raise e

    def __repr__(self) -> str:
        return repr(self.expression)


class HangUnit(Waiter):
    """
    Wait for a dict of requirements, call the resume method on the resumer, with a map of the resulting values
    """

    __slots__ = ("resolver", "resumer", "target")

    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: "Resolver",
        requires: dict[object, VariableABC],
        target: Optional[ResultVariable],
        resumer: "Resumer",
    ) -> None:
        Waiter.__init__(self, queue_scheduler)
        self.resolver = resolver
        self.requires = requires
        self.resumer = resumer
        self.target = target
        for r in requires.values():
            self.waitfor(r)
        self.ready(self)

    def execute(self) -> None:
        try:
            self.resumer.resume({k: v.get_value() for (k, v) in self.requires.items()}, self.resolver, self.queue, self.target)
        except RuntimeException as e:
            e.set_statement(self.resumer)
            raise e
        self.done = True


class RawUnit(Waiter):
    """
    Wait for a map of requirements, call the resume method on the resumer,
    but with a map of ResultVariables instead of their values
    """

    __slots__ = ("resolver", "resumer", "override_exception_location")

    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: "Resolver",
        requires: dict[object, VariableABC],
        resumer: "RawResumer",
        override_exception_location: bool = True,
    ) -> None:
        Waiter.__init__(self, queue_scheduler)
        self.resolver = resolver
        self.requires = requires
        self.resumer = resumer
        self.override_exception_location: bool = override_exception_location
        for r in requires.values():
            self.waitfor(r)
        self.ready(self)

    def execute(self) -> None:
        try:
            self.resumer.resume(self.requires, self.resolver, self.queue)
        except RuntimeException as e:
            if self.override_exception_location:
                e.set_statement(self.resumer)
                e.location = self.resumer.location
            raise e
        self.done = True


"""
Resolution

 - lexical scope (module it is in, then parent modules)
   - handled in NS and direct_lookup on XU
 - dynamic scope (entity, for loop,...)
   - resolvers
   - lex scope as arg or root

resolution
 - FQN:  to lexical scope (via parents) -> to its  NS (imports) -> to target NS -> directLookup
 - N: to resolver -> to parents -> to NS (lex root) -> directlookup

"""

Typeorvalue = Union[Type, ResultVariable]


class Resolver:
    __slots__ = ("namespace", "dataflow_graph")

    def __init__(self, namespace: Namespace, enable_dataflow_graph: bool = False) -> None:
        self.namespace = namespace
        self.dataflow_graph: Optional[DataflowGraph] = DataflowGraph(self) if enable_dataflow_graph else None

    def lookup(self, name: str, root: Optional[Namespace] = None) -> Typeorvalue:
        # override lexial root
        # i.e. delegate to parent, until we get to the root, then either go to our root or lexical root of our caller
        if root is not None:
            ns = root
        else:
            ns = self.namespace

        return ns.lookup(name)

    def get_root_resolver(self) -> "Resolver":
        return self

    def for_namespace(self, namespace: Namespace) -> "Resolver":
        return NamespaceResolver(self, namespace)

    def get_dataflow_node(self, name: str) -> "dataflow.AssignableNodeReference":
        try:
            result_variable: Typeorvalue = self.lookup(name)
            assert isinstance(result_variable, ResultVariable)
            return result_variable.get_dataflow_node()
        except NotFoundException:
            # This block is only executed if the model contains a reference to an undefined variable.
            # Since we don't know in which scope it should be defined, we assume top scope.
            root_graph: Optional[DataflowGraph] = self.get_root_resolver().dataflow_graph
            assert root_graph is not None
            return root_graph.get_own_variable(name)


class VariableResolver(Resolver):
    """
    Resolver that resolves a single variable to a value, and delegates the rest to its parent resolver.
    """

    __slots__ = (
        "parent",
        "name",
        "variable",
    )

    def __init__(self, parent: Resolver, name: str, variable: ResultVariable[T]) -> None:
        self.parent: Resolver = parent
        self.name: str = name
        self.variable: ResultVariable[T] = variable
        self.dataflow_graph = (
            DataflowGraph(self, parent=self.parent.dataflow_graph) if self.parent.dataflow_graph is not None else None
        )

    def lookup(self, name: str, root: Optional[Namespace] = None) -> Typeorvalue:
        if root is None and name == self.name:
            return self.variable
        return self.parent.lookup(name, root)

    def get_root_resolver(self) -> "Resolver":
        return self.parent.get_root_resolver()


class NamespaceResolver(Resolver):
    __slots__ = ("parent", "root")

    def __init__(self, parent: Resolver, lecial_root: Namespace) -> None:
        self.parent = parent
        self.root = lecial_root
        self.dataflow_graph: Optional[DataflowGraph] = None
        if parent.dataflow_graph is not None:
            self.dataflow_graph = DataflowGraph(self, parent.dataflow_graph)

    def lookup(self, name: str, root: Optional[Namespace] = None) -> Typeorvalue:
        if root is not None:
            return self.parent.lookup(name, root)
        return self.parent.lookup(name, self.root)

    def for_namespace(self, namespace: Namespace) -> "Resolver":
        return NamespaceResolver(self, namespace)

    def get_root_resolver(self) -> "Resolver":
        return self.parent.get_root_resolver()


class ExecutionContext(Resolver):
    __slots__ = ("block", "slots", "resolver")

    def __init__(self, block: "BasicBlock", resolver: Resolver):
        self.block = block
        self.slots: dict[str, ResultVariable] = {n: ResultVariable() for n in block.get_variables()}
        self.resolver = resolver
        self.dataflow_graph: Optional[DataflowGraph] = None
        if resolver.dataflow_graph is not None:
            self.dataflow_graph = DataflowGraph(self, resolver.dataflow_graph)
            for name, var in self.slots.items():
                node_ref: dataflow.AssignableNodeReference = dataflow.AssignableNode(name).reference()
                var.set_dataflow_node(node_ref)

    def lookup(self, name: str, root: Optional[Namespace] = None) -> Typeorvalue:
        if "::" in name:
            return self.resolver.lookup(name, root)
        if name in self.slots:
            return self.slots[name]
        return self.resolver.lookup(name, root)

    def direct_lookup(self, name: str) -> ResultVariable:
        if name in self.slots:
            return self.slots[name]
        else:
            raise NotFoundException(None, name, "variable %s not found" % name)

    def emit(self, queue: QueueScheduler) -> None:
        self.block.emit(self, queue)

    def get_root_resolver(self) -> Resolver:
        return self.resolver.get_root_resolver()

    def for_namespace(self, namespace: Namespace) -> Resolver:
        return NamespaceResolver(self, namespace)


# also extends locatable
class Instance(ExecutionContext, references.MaybeReference):
    def set_location(self, location: Location) -> None:
        Locatable.set_location(self, location)
        self.locations.append(location)

    def get_location(self) -> Optional[Location]:
        return Locatable.get_location(self)

    location = property(get_location, set_location)

    __slots__ = (
        "_location",
        "resolver",
        "type",
        "sid",
        "implementations",
        "locations",
        "instance_node",
        "dataclass_self",
    )

    def __init__(
        self,
        mytype: "Entity",
        resolver: Resolver,
        queue: QueueScheduler,
        node: Optional["dataflow.InstanceNodeReference"] = None,
    ) -> None:
        Locatable.__init__(self)
        # ExecutionContext, Resolver -> this class only uses it as an "interface", so no constructor call!
        self.resolver = resolver.get_root_resolver()
        self.type = mytype
        self.slots: dict[str, ResultVariable] = {}
        for attr_name in mytype.get_all_attribute_names():
            if attr_name in self.slots:
                # prune duplicates because get_new_result_variable() has side effects
                # don't use set for pruning because side effects drive control flow and set iteration is nondeterministic
                continue
            attribute = mytype.get_attribute(attr_name)
            assert attribute is not None  # Make mypy happy
            self.slots[attr_name] = attribute.get_new_result_variable(self, queue)
        # TODO: this is somewhat ugly. Is there a cleaner way to enforce this constraint
        assert (resolver.dataflow_graph is None) == (node is None)
        self.dataflow_graph: Optional[DataflowGraph] = None
        self.instance_node: Optional[dataflow.InstanceNodeReference] = node
        if self.instance_node is not None:
            self.dataflow_graph = DataflowGraph(self, resolver.dataflow_graph)
            for name, var in self.slots.items():
                var.set_dataflow_node(dataflow.InstanceAttributeNodeReference(self.instance_node.top_node(), name))

        self.slots["self"] = ResultVariable()
        self.slots["self"].set_value(self, None)
        if self.instance_node is not None:
            self_var_node: dataflow.AssignableNodeReference = dataflow.AssignableNode("__self__").reference()
            self_var_node.assign(self.instance_node, self, cast(DataflowGraph, self.dataflow_graph))
            self.slots["self"].set_dataflow_node(self_var_node)

        self.sid = id(self)
        self.implementations: "set[Implementation]" = set()

        self.locations: list[Location] = []
        # may also be a reference to a dataclass
        self.dataclass_self: object | references.Reference[references.RefValue] | None = None

    def get_type(self) -> "Entity":
        return self.type

    def unwrap_reference(self) -> Optional[references.Reference[references.RefValue]]:
        return (
            self.dataclass_self
            if self.dataclass_self is not None and isinstance(self.dataclass_self, references.Reference)
            else None
        )

    def set_attribute(self, name: str, value: object, location: Location, recur: bool = True) -> None:
        if name not in self.slots:
            raise NotFoundException(None, name, f"cannot set attribute with name {name} on type {self.type}")
        try:
            self.slots[name].set_value(value, location, recur)
        except RuntimeException as e:
            raise AttributeException(self, self, name, cause=e)

    def get_attribute(self, name: str) -> ResultVariable:
        try:
            return self.slots[name]
        except KeyError:
            raise NotFoundException(None, name, f"could not find attribute with name: {name} in type {self.type}")

    def __repr__(self) -> str:
        return f"{self.type} {self.sid:02x}"

    def __str__(self) -> str:
        return "{} (instantiated at {})".format(self.type, ",".join([str(location) for location in self.get_locations()]))

    def add_implementation(self, impl: "Implementation") -> bool:
        if impl in self.implementations:
            return False
        self.implementations.add(impl)
        return True

    def final(self, excns: list[CompilerException]) -> None:
        """
        The object should be complete, freeze all attributes
        """
        if len(self.implementations) == 0:
            excns.append(RuntimeException(self, "Unable to select implementation for entity %s" % self.type.name))

        for k, v in self.slots.items():
            if not v.is_ready():
                if v.can_get():
                    v.freeze()
                else:
                    attr = self.type.get_attribute(k)
                    assert attr is not None  # Make mypy happy
                    if isinstance(attr, ast.attribute.RelationAttribute) and attr.is_multi():
                        low = attr.low
                        # none for list attributes
                        # list for n-ary relations
                        length = 0 if v.value is None else len(v.value)
                        excns.append(
                            inmanta.ast.UnsetException(
                                "The object %s is not complete: attribute %s (%s) requires %d values but only %d are set"
                                % (self, k, attr.location, low, length),
                                self,
                                attr,
                            )
                        )
                    else:
                        excns.append(
                            inmanta.ast.UnsetException(
                                f"The object {self} is not complete: attribute {k} ({attr.location}) is not set",
                                self,
                                attr,
                            )
                        )

    def verify_done(self) -> bool:
        for v in self.slots.values():
            if not v.can_get():
                return False
        return True

    def get_locations(self) -> list[Location]:
        return self.locations
