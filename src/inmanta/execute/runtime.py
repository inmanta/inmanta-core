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
from typing import Deque, Dict, Generic, Hashable, List, Optional, Set, TypeVar, Union, cast

import inmanta.warnings as inmanta_warnings
from inmanta.ast import (
    AttributeException,
    CompilerDeprecationWarning,
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
from inmanta.execute import dataflow, proxy
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.tracking import Tracker
from inmanta.execute.util import NoneValue, Unknown

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.attribute import Attribute, RelationAttribute
    from inmanta.ast.blocks import BasicBlock
    from inmanta.ast.entity import Default, Entity, EntityLike, Implement, Implementation  # noqa: F401
    from inmanta.ast.statements import ExpressionStatement, RawResumer, Resumer, Statement
    from inmanta.compiler import Compiler


T = TypeVar("T")


class ResultCollector(Generic[T]):
    """
    Helper interface for gradual execution
    """

    __slots__ = ()

    def receive_result(self, value: T, location: Location) -> None:
        """
        receive a possibly partial result
        """
        raise NotImplementedError()


class IPromise(Generic[T]):
    __slots__ = ()

    @abstractmethod
    def set_value(self, value: T, location: Location, recur: bool = True) -> None:
        pass


class ResultVariable(ResultCollector[T], IPromise[T]):
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
        self.provider: "Optional[Statement]" = None
        self.waiters: "List[Waiter]" = []
        self.value: Optional[T] = value
        self.hasValue: bool = False
        self.type: Optional[Type] = None
        self._node: Optional[dataflow.AssignableNodeReference] = None

    def set_type(self, mytype: Type) -> None:
        self.type = mytype

    def set_provider(self, provider: "Statement") -> None:
        # no checking for double set, this is done in the actual assignment
        self.provider = provider

    def get_promise(self, provider: "Statement") -> IPromise[T]:
        """Alternative for set_provider for better handling of ListVariables."""
        self.provider = provider
        return self

    def is_ready(self) -> bool:
        return self.hasValue

    def waitfor(self, waiter: "Waiter") -> None:
        if self.is_ready():
            waiter.ready(self)
        else:
            self.waiters.append(waiter)

    def set_value(self, value: T, location: Location, recur: bool = True) -> None:
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
            raise proxy.UnsetException("Value not available", self)

        return self.value

    def can_get(self) -> bool:
        return self.hasValue

    def freeze(self) -> None:
        pass

    def receive_result(self, value: T, location: Location) -> None:
        pass

    def listener(self, resulcollector: ResultCollector[T], location: Location) -> None:
        """
        add a listener to report new values to, only for lists
        """
        pass

    def is_multi(self) -> bool:
        return False

    def set_dataflow_node(self, node: dataflow.AssignableNodeReference) -> None:
        assert self._node is None or self._node == node
        self._node = node
        self._node.set_result_variable(self)

    def get_dataflow_node(self) -> dataflow.AssignableNodeReference:
        assert self._node is not None, "assertion error at %s.get_dataflow_node() in ResultVariable" % self
        return self._node


class AttributeVariable(ResultVariable["Instance"]):
    """
    a result variable for a relation with arity 1

    when assigned a value, it will also assign a value to its inverse relation
    """

    __slots__ = ("attribute", "myself")

    def __init__(self, attribute: "RelationAttribute", instance: "Instance"):
        self.attribute: "RelationAttribute" = attribute
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


class DelayedResultVariable(ResultVariable[T]):
    """
    DelayedResultVariable are ResultVariables of which it is unclear how many results will be set.

    i.e. there may be speculation about when they can be considered complete.

    When the freeze method is called, no more values will be accepted and
    the DelayedResultVariable will behave as a normal ResultVariable.

    When a DelayedResultVariable is definitely full, it is freeze itself.

    DelayedResultVariable are queued with the scheduler at the point at which they might be complete.
    The scheduler can decide when to freeze them. A DelayedResultVariable  can be complete when
      - it contains enough elements
      - there are no providers which still have to provide some values (tracked inexactly)
        (a queue variable can be dequeued by the scheduler when a provider is added)
    """

    __slots__ = ("queued", "queues", "listeners")

    def __init__(self, queue: "QueueScheduler", value: Optional[T] = None) -> None:
        ResultVariable.__init__(self, value)
        self.queued = False
        self.queues = queue
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
        self.listeners = None
        self.queues = None

    def queue(self) -> None:
        if self.queued:
            return
        self.queued = True
        self.queues.add_possible(self)

    def unqueue(self) -> None:
        self.queued = False

    def get_waiting_providers(self) -> int:
        """How many values are definitely still waiting for"""
        raise NotImplementedError()

    def get_progress_potential(self) -> int:
        """How many are actually waiting for us """
        return len(self.waiters)


ListValue = Union["Instance", List["Instance"]]


class Promise(IPromise[ListValue]):

    __slots__ = ("provider", "owner")

    def __init__(self, owner: "ListVariable", provider: "Statement"):
        self.provider: "Optional[Statement]" = provider
        self.owner: "ListVariable" = owner

    def set_value(self, value: ListValue, location: Location, recur: bool = True) -> None:
        self.owner.set_promised_value(self, value, location, recur)


class BaseListVariable(DelayedResultVariable[ListValue]):
    """
    List variable, but only the part that is independent of an instance
    """

    value: "List[Instance]"

    __slots__ = ("promisses", "done_promisses")

    def __init__(self, queue: "QueueScheduler") -> None:
        self.promisses: List[Promise] = []
        self.done_promisses: List[Promise] = []
        self.listeners: List[ResultCollector[ListValue]] = []
        super().__init__(queue, [])

    def get_promise(self, provider: "Statement") -> IPromise[ListValue]:
        out = Promise(self, provider)
        self.promisses.append(out)
        return out

    def set_promised_value(self, promis: Promise, value: ListValue, location: Location, recur: bool = True) -> None:
        self.done_promisses.append(promis)
        self.set_value(value, location, recur)

    def get_waiting_providers(self) -> int:
        # todo: optimize?
        out = len(self.promisses) - len(self.done_promisses)
        if out < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: provide count negative")
        return out

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

        for listener in self.listeners:
            listener.receive_result(value, location)

        return True

    def set_value(self, value: ListValue, location: Location, recur: bool = True) -> None:
        if not self._set_value(value, location, recur):
            return
        if self.can_get():
            self.queue()

    def can_get(self) -> bool:
        return self.get_waiting_providers() == 0

    def get_progress_potential(self) -> int:
        """How many are actually waiting for us """
        return len(self.waiters) - len(self.listeners)

    def receive_result(self, value: ListValue, location: Location) -> None:
        self.set_value(value, location)

    def listener(self, resultcollector: ResultCollector, location: Location) -> None:
        for value in self.value:
            resultcollector.receive_result(value, location)
        if not self.hasValue:
            self.listeners.append(resultcollector)

    def is_multi(self) -> bool:
        return True

    def __str__(self) -> str:
        return "BaseListVariable %s" % (self.value)


class TempListVariable(BaseListVariable):

    __slots__ = ()

    def set_promised_value(self, promis: Promise, value: ListValue, location: Location, recur: bool = True) -> None:
        super().set_promised_value(promis, value, location, recur)
        # 100% accurate promisse tracking
        if len(self.promisses) == len(self.done_promisses):
            self.freeze()


class ListVariable(BaseListVariable):

    value: "List[Instance]"

    __slots__ = ("attribute", "myself")

    def __init__(self, attribute: "RelationAttribute", instance: "Instance", queue: "QueueScheduler") -> None:
        self.attribute: "RelationAttribute" = attribute
        self.myself = instance
        super().__init__(queue)

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
                    None, "Exceeded relation arity on attribute '%s' of instance '%s'" % (self.attribute.name, self.myself)
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
        return "ListVariable %s %s = %s" % (self.myself, self.attribute, self.value)


class OptionVariable(DelayedResultVariable["Instance"]):

    __slots__ = ("attribute", "myself", "location")

    def __init__(self, attribute: "Attribute", instance: "Instance", queue: "QueueScheduler") -> None:
        DelayedResultVariable.__init__(self, queue)
        self.value = None
        self.attribute = attribute
        self.myself = instance
        self.location = None

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

    def get_waiting_providers(self) -> int:
        # todo: optimize?
        if self.provider is None:
            return 0
        if self.hasValue:
            return 0
        return 1

    def can_get(self) -> bool:
        return self.get_waiting_providers() == 0

    def get_value(self) -> "Instance":
        result = DelayedResultVariable.get_value(self)
        if result is None:
            raise OptionalValueException(self.myself, self.attribute)
        return result

    def __str__(self) -> str:
        return "OptionVariable %s %s = %s" % (self.myself, self.attribute, self.value)


class DeprecatedOptionVariable(OptionVariable):
    """
    Represents nullable attributes. In the future this class can be removed, and a standard
    ResultVariable with nullable type should be used.
    """

    def freeze(self) -> None:
        if self.value is None:
            warning: CompilerDeprecationWarning = CompilerDeprecationWarning(
                None,
                "No value for attribute %s.%s. Assign null instead of leaving unassigned." % (self.myself.type, self.attribute),
            )
            warning.set_location(self.myself.get_location())
            inmanta_warnings.warn(warning)
        super().freeze()

    def _get_null_value(self) -> object:
        return NoneValue()

    def _validate_value(self, value: object) -> None:
        if isinstance(value, Unknown):
            return
        if self.type is None:
            return
        self.type.validate(value)


class QueueScheduler(object):
    """
    Object representing the compiler to the AST nodes. It provides access to the queueing mechanism and the type system.

    MUTABLE!
    """

    __slots__ = ("compiler", "runqueue", "waitqueue", "types", "allwaiters")

    def __init__(
        self,
        compiler: "Compiler",
        runqueue: "Deque[Waiter]",
        waitqueue: Deque[DelayedResultVariable],
        types: Dict[str, Type],
        allwaiters: "Set[Waiter]",
    ) -> None:
        self.compiler = compiler
        self.runqueue = runqueue
        self.waitqueue = waitqueue
        self.types = types
        self.allwaiters = allwaiters

    def add_running(self, item: "Waiter") -> None:
        self.runqueue.append(item)

    def add_possible(self, rv: DelayedResultVariable) -> None:
        self.waitqueue.append(rv)

    def get_compiler(self) -> "Compiler":
        return self.compiler

    def get_types(self) -> Dict[str, Type]:
        return self.types

    def add_to_all(self, item: "Waiter") -> None:
        self.allwaiters.add(item)

    def remove_from_all(self, item: "Waiter") -> None:
        self.allwaiters.remove(item)

    def get_tracker(self) -> Optional[Tracker]:
        return None

    def for_tracker(self, tracer: Tracker) -> "QueueScheduler":
        return DelegateQueueScheduler(self, tracer)


class DelegateQueueScheduler(QueueScheduler):
    __slots__ = ("__delegate", "__tracker")

    def __init__(self, delegate: QueueScheduler, tracker: Tracker):
        self.__delegate = delegate
        self.__tracker = tracker

    def add_running(self, item: "Waiter") -> None:
        self.__delegate.add_running(item)

    def add_possible(self, rv: DelayedResultVariable) -> None:
        self.__delegate.add_possible(rv)

    def get_compiler(self) -> "Compiler":
        return self.__delegate.get_compiler()

    def get_types(self) -> Dict[str, Type]:
        return self.__delegate.get_types()

    def add_to_all(self, item: "Waiter") -> None:
        self.__delegate.add_to_all(item)

    def remove_from_all(self, item: "Waiter") -> None:
        self.__delegate.remove_from_all(item)

    def get_tracker(self) -> Tracker:
        return self.__tracker

    def for_tracker(self, tracer: Tracker) -> QueueScheduler:
        return DelegateQueueScheduler(self.__delegate, tracer)


class Waiter(object):
    """
    Waiters represent an executable unit, that can be executed the result variables they depend on have their values.
    """

    __slots__ = ("waitcount", "queue", "done", "requires")

    requires: Dict[object, ResultVariable]

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

    def waitfor(self, waitable: ResultVariable) -> None:
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
        result: ResultVariable,
        requires: Dict[object, ResultVariable],
        expression: "ExpressionStatement",
        owner: "Optional[Statement]" = None,
    ):
        Waiter.__init__(self, queue_scheduler)
        self.result = result.get_promise(expression)
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
            e.set_statement(self.owner)
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
        requires: Dict[object, ResultVariable],
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

    __slots__ = ("resolver", "resumer")

    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: "Resolver",
        requires: Dict[object, ResultVariable],
        resumer: "RawResumer",
    ) -> None:
        Waiter.__init__(self, queue_scheduler)
        self.resolver = resolver
        self.requires = requires
        self.resumer = resumer
        for r in requires.values():
            self.waitfor(r)
        self.ready(self)

    def execute(self) -> None:
        try:
            self.resumer.resume(self.requires, self.resolver, self.queue)
        except RuntimeException as e:
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


class Resolver(object):

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
        self.slots: Dict[str, ResultVariable] = {n: ResultVariable() for n in block.get_variables()}
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
class Instance(ExecutionContext):
    def set_location(self, location: Location) -> None:
        Locatable.set_location(self, location)
        self.locations.append(location)

    def get_location(self) -> Location:
        return Locatable.get_location(self)

    location = property(get_location, set_location)

    __slots__ = (
        "_location",
        "resolver",
        "type",
        "sid",
        "implementations",
        "trackers",
        "locations",
        "instance_node",
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
        self.slots: Dict[str, ResultVariable] = {}
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
        self.implementations: "Set[Implementation]" = set()

        # see inmanta.ast.execute.scheduler.QueueScheduler
        self.trackers: List[Tracker] = []

        self.locations: List[Location] = []

    def get_type(self) -> "Entity":
        return self.type

    def set_attribute(self, name: str, value: object, location: Location, recur: bool = True) -> None:
        if name not in self.slots:
            raise NotFoundException(None, name, "cannot set attribute with name %s on type %s" % (name, str(self.type)))
        try:
            self.slots[name].set_value(value, location, recur)
        except RuntimeException as e:
            raise AttributeException(self, self, name, cause=e)

    def get_attribute(self, name: str) -> ResultVariable:
        try:
            return self.slots[name]
        except KeyError:
            raise NotFoundException(None, name, "could not find attribute with name: %s in type %s" % (name, self.type))

    def __repr__(self) -> str:
        return "%s %02x" % (self.type, self.sid)

    def __str__(self) -> str:
        return "%s (instantiated at %s)" % (self.type, ",".join([str(location) for location in self.get_locations()]))

    def add_implementation(self, impl: "Implementation") -> bool:
        if impl in self.implementations:
            return False
        self.implementations.add(impl)
        return True

    def final(self, excns: List[CompilerException]) -> None:
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
                    if attr.is_multi():
                        low = attr.low
                        # none for list attributes
                        # list for n-ary relations
                        length = 0 if v.value is None else len(v.value)
                        excns.append(
                            proxy.UnsetException(
                                "The object %s is not complete: attribute %s (%s) requires %d values but only %d are set"
                                % (self, k, attr.location, low, length),
                                self,
                                attr,
                            )
                        )
                    else:
                        excns.append(
                            proxy.UnsetException(
                                "The object %s is not complete: attribute %s (%s) is not set" % (self, k, attr.location),
                                self,
                                attr,
                            )
                        )

    def dump(self) -> None:
        print("------------ ")
        print(str(self))
        print("------------ ")
        for (n, v) in self.slots.items():
            if v.can_get():

                value = v.value
                print("%s\t\t%s" % (n, value))
            else:
                print("BAD: %s\t\t%s" % (n, v.provider))

    def verify_done(self) -> bool:
        for v in self.slots.values():
            if not v.can_get():
                return False
        return True

    def get_locations(self) -> List[Location]:
        return self.locations
