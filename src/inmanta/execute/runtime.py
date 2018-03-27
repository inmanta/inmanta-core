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

from inmanta.execute.util import Unknown
from inmanta.execute.proxy import UnsetException
from inmanta.ast import RuntimeException, NotFoundException, DoubleSetException, OptionalValueException, AttributeException, \
    Locatable, Location
from inmanta.ast.type import Type
from typing import Dict, Any


class ResultCollector(object):
    """
        Helper interface for gradual execution
    """

    def receive_result(self, value, location):
        """
            receive a possibly partial result
        """
        raise Exception("Not Implemented" + str(type(self)))


class ResultVariable(ResultCollector):
    """
        A ResultVariable is like a future
         - it has a list of waiters
         - when a value is set, the waiters are notified,
            they decrease their wait count and
            queue themselves when their wait count becomes 0

        If a type is set on a result variable, setting a value of another type will produce an exception.

        In order to assist heuristic evaluation, result variables keep track of any statement that will assign a value to it
    """

    def __init__(self, value: object=None):
        self.provider = None
        self.waiters = []
        self.value = value
        self.hasValue = False
        self.type = None

    def set_type(self, mytype: Type):
        self.type = mytype

    def set_provider(self, provider):
        # no checking for double set, this is done in the actual assignment
        self.provider = provider

    def get_promise(self, provider):
        """Alternative for set_provider for better handling of ListVariables."""
        self.provider = provider
        return self

    def is_ready(self):
        return self.hasValue

    def await(self, waiter):
        if self.is_ready():
            waiter.ready(self)
        else:
            self.waiters.append(waiter)

    def set_value(self, value, location, recur=True):
        if self.hasValue:
            if self.value != value:
                raise DoubleSetException(None, self.value, self.location, value, location)
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
        self.location = location
        self.hasValue = True
        for waiter in self.waiters:
            waiter.ready(self)

    def get_value(self):
        if not self.hasValue:
            raise UnsetException("Value not available", self)

        return self.value

    def can_get(self):
        return self.hasValue

    def freeze(self):
        pass

    def receive_result(self, value, location):
        pass

    def listener(self, resulcollector, location):
        """
            add a listener to report new values to, only for lists
        """
        pass

    def is_multi(self):
        return False


class AttributeVariable(ResultVariable):
    """
        a result variable for a relation with arity 1

        when assigned a value, it will also assign a value to its inverse relation
    """

    def __init__(self, attribute, instance):
        self.attribute = attribute
        self.myself = instance
        ResultVariable.__init__(self)

    def set_value(self, value, location, recur=True):
        if self.hasValue:
            if self.value != value:
                raise DoubleSetException(None, self.value, self.location, value, location)
            else:
                return
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
        self.location = location
        self.hasValue = True
        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, location, False)
        for waiter in self.waiters:
            waiter.ready(self)


class DelayedResultVariable(ResultVariable):
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

    def __init__(self, queue: "QueueScheduler", value=None):
        ResultVariable.__init__(self, value)
        self.queued = False
        self.queues = queue
        if self.can_get():
            self.queue()

    def freeze(self):
        if self.hasValue:
            return
        self.hasValue = True
        for waiter in self.waiters:
            waiter.ready(self)

    def queue(self):
        if self.queued:
            return
        self.queued = True
        self.queues.add_possible(self)

    def unqueue(self):
        self.queued = False

    def get_waiting_providers(self):
        raise NotImplementedError()


class Promise(object):

    def __init__(self, owner, provider):
        self.provider = provider
        self.owner = owner

    def set_value(self, value, location, recur=True):
        self.owner.set_promised_value(self, value, location, recur)


class ListVariable(DelayedResultVariable):

    def __init__(self, attribute, instance, queue: "QueueScheduler"):
        self.attribute = attribute
        self.myself = instance
        self.promisses = []
        self.done_promisses = []
        self.listeners = []
        DelayedResultVariable.__init__(self, queue, [])

    def get_promise(self, provider):
        out = Promise(self, provider)
        self.promisses.append(out)
        return out

    def set_promised_value(self, promis, value, location, recur=True):
        self.done_promisses.append(promis)
        self.set_value(value, location, recur)

    def get_waiting_providers(self):
        # todo: optimize?
        out = len(self.promisses) - len(self.done_promisses)
        if out < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: provide count negative")
        return out

    def set_value(self, value, location, recur=True):
        if self.hasValue:
            if value in self.value:
                return
            else:
                raise RuntimeException(None, "List modified after freeze")

        if isinstance(value, list):
            if len(value) == 0:
                # the values of empty lists need no processing,
                # but a set_value from an empty list may fulfill a promise, allowing this object to be queued
                if self.can_get():
                    self.queue()
            else:
                for v in value:
                    self.set_value(v, recur, location)
            return

        if self.type is not None:
            self.type.validate(value)

        if value in self.value:
            # any set_value may fulfill a promise, allowing this object to be queued
            if self.can_get():
                self.queue()
            return

        self.value.append(value)

        for l in self.listeners:
            l.receive_result(value, location)

        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, location, False)

        if self.attribute.high is not None:
            if self.attribute.high > len(self.value):
                raise RuntimeException(None, "List over full: max nr of items is %d, content is %s" %
                                       (self.attribute.high, self.value))

            if self.attribute.high > len(self.value):
                self.freeze()

        if self.can_get():
            self.queue()

    def can_get(self):
        return len(self.value) >= self.attribute.low and self.get_waiting_providers() == 0

    def __str__(self):
        return "ListVariable %s %s = %s" % (self.myself, self.attribute, self.value)

    def receive_result(self, value, location):
        self.set_value(value, location)

    def listener(self, resultcollector, location):
        for value in self.value:
            resultcollector.receive_result(value, location)
        self.listeners.append(resultcollector)

    def is_multi(self):
        return True


class OptionVariable(DelayedResultVariable):

    def __init__(self, attribute, instance, queue: "QueueScheduler"):
        DelayedResultVariable.__init__(self, queue)
        self.value = None
        self.attribute = attribute
        self.myself = instance

    def set_value(self, value, location, recur=True):
        if self.hasValue:
            if self.value != value:
                raise DoubleSetException(None, self.value, self.location, value, location)

        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)

        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, location, False)

        self.value = value
        self.location = location
        self.freeze()

    def get_waiting_providers(self):
        # todo: optimize?
        if self.provider is None:
            return 0
        if self.hasValue:
            return 0
        return 1

    def can_get(self):
        return self.get_waiting_providers() == 0

    def get_value(self):
        result = DelayedResultVariable.get_value(self)
        if result is None:
            raise OptionalValueException(self.myself, self.attribute)
        return result

    def __str__(self):
        return "OptionVariable %s %s = %s" % (self.myself, self.attribute, self.value)


class QueueScheduler(object):
    """
        Object representing the compiler to the AST nodes. It provides access to the queueing mechanism and the type system.

        MUTABLE!
    """

    def __init__(self, compiler, runqueue, waitqueue, types, allwaiters):
        self.compiler = compiler
        self.runqueue = runqueue
        self.waitqueue = waitqueue
        self.types = types
        self.allwaiters = allwaiters

    def add_running(self, item: "Waiter"):
        return self.runqueue.append(item)

    def add_possible(self, rv: ResultVariable):
        return self.waitqueue.append(rv)

    def get_compiler(self):
        return self.compiler

    def get_types(self):
        return self.types

    def add_to_all(self, item):
        self.allwaiters.append(item)

    def get_tracker(self):
        return None

    def for_tracker(self, tracer):
        return DelegateQueueScheduler(self, tracer)


class DelegateQueueScheduler(QueueScheduler):

    def __init__(self, delegate, tracker):
        self.__delegate = delegate
        self.__tracker = tracker

    def add_running(self, item: "Waiter"):
        return self.__delegate.add_running(item)

    def add_possible(self, rv: ResultVariable):
        return self.__delegate.add_possible(rv)

    def get_compiler(self):
        return self.__delegate.get_compiler()

    def get_types(self):
        return self.__delegate.get_types()

    def add_to_all(self, item):
        self.__delegate.add_to_all(item)

    def get_tracker(self):
        return self.__tracker

    def for_tracker(self, tracer):
        return DelegateQueueScheduler(self.__delegate, tracer)


class Waiter(object):
    """
        Waiters represent an executable unit, that can be executed the result variables they depend on have their values.
    """

    def __init__(self, queue: QueueScheduler):
        self.waitcount = 1
        self.queue = queue
        self.queue.add_to_all(self)
        self.done = False

    def await(self, waitable):
        self.waitcount = self.waitcount + 1
        waitable.await(self)

    def ready(self, other):
        self.waitcount = self.waitcount - 1
        if self.waitcount == 0:
            self.queue.add_running(self)
        if self.waitcount < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: waitcount negative")

    def execute(self):
        pass


class ExecutionUnit(Waiter):
    """
       Basic assign statement:
        - Wait for a dict of requirements
        - Call the execute method on the expression, with a map of the resulting values
        - Assign the resulting value to the result variable

        @param provides: Whether to register this XU as provider to the result variable
    """

    def __init__(self, queue_scheduler, resolver, result: ResultVariable, requires: Dict[Any, ResultVariable], expression):
        Waiter.__init__(self, queue_scheduler)
        self.result = result.get_promise(expression)
        self.requires = requires
        self.expression = expression
        self.resolver = resolver
        self.queue_scheduler = queue_scheduler
        for r in requires.values():
            self.await(r)
        self.ready(self)

    def execute(self):
        try:
            requires = {k: v.get_value() for (k, v) in self.requires.items()}
            value = self.expression.execute(requires, self.resolver, self.queue_scheduler)
            self.result.set_value(value, self.expression.location)
        except RuntimeException as e:
            e.set_statement(self.expression)
            raise e
        self.done = True

    def __repr__(self):
        return repr(self.expression)


class HangUnit(Waiter):
    """
        Wait for a dict of requirements, call the resume method on the resumer, with a map of the resulting values
    """

    def __init__(self, queue_scheduler, resolver, requires, target, resumer):
        Waiter.__init__(self, queue_scheduler)
        self.queue_scheduler = queue_scheduler
        self.resolver = resolver
        self.requires = requires
        self.resumer = resumer
        self.target = target
        for r in requires.values():
            self.await(r)
        self.ready(self)

    def execute(self):
        try:
            self.resumer.resume({k: v.get_value()
                                 for (k, v) in self.requires.items()}, self.resolver, self.queue_scheduler, self.target)
        except RuntimeException as e:
            e.set_statement(self.resumer)
            raise e
        self.done = True


class RawUnit(Waiter):
    """
        Wait for a map of requirements, call the resume method on the resumer,
        but with a map of ResultVariables instead of their values
    """

    def __init__(self, queue_scheduler, resolver, requires, resumer):
        Waiter.__init__(self, queue_scheduler)
        self.queue_scheduler = queue_scheduler
        self.resolver = resolver
        self.requires = requires
        self.resumer = resumer
        for r in requires.values():
            self.await(r)
        self.ready(self)

    def execute(self):
        try:
            self.resumer.resume(self.requires, self.resolver, self.queue_scheduler)
        except RuntimeException as e:
            e.set_statement(self.resumer)
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


class Resolver(object):

    def __init__(self, namespace):
        self.namespace = namespace

    def lookup(self, name, root=None) -> ResultVariable:
        # override lexial root
        # i.e. delegate to parent, until we get to the root, then either go to our root or lexical root of our caller
        if root is not None:
            ns = root
        else:
            ns = self.namespace

        return ns.lookup(name)

    def get_root_resolver(self):
        return self

    def for_namespace(self, namespace):
        return NamespaceResolver(self, namespace)


class NamespaceResolver(Resolver):

    def __init__(self, parent, lecial_root):
        self.parent = parent
        self.root = lecial_root

    def lookup(self, name, root=None):
        if root is not None:
            return self.parent.lookup(name, root)
        return self.parent.lookup(name, self.root)

    def for_namespace(self, namespace):
        return NamespaceResolver(self, namespace)

    def get_root_resolver(self):
        return self.parent.get_root_resolver()


class ExecutionContext(object):

    def __init__(self, block, resolver):
        self.block = block
        self.slots = {n: ResultVariable() for n in block.get_variables()}
        self.resolver = resolver

    def lookup(self, name, root=None):
        if "::" in name:
            return self.resolver.lookup(name, root)
        if name in self.slots:
            return self.slots[name]
        return self.resolver.lookup(name, root)

    def direct_lookup(self, name: str) -> "Type":
        if name in self.slots:
            return self.slots[name]
        else:
            raise NotFoundException(None, name, "variable %s not found" % name)

    def emit(self, queue):
        self.block.emit(self, queue)

    def get_root_resolver(self):
        return self.resolver.get_root_resolver()

    def for_namespace(self, namespace):
        return NamespaceResolver(self, namespace)


class Instance(ExecutionContext, Locatable, Resolver):

    def __init__(self, mytype, resolver, queue):
        Locatable.__init__(self)
        # ExecutionContext, Resolver -> this class only uses it as an "interface", so no constructor call!
        self.resolver = resolver.get_root_resolver()
        self.type = mytype
        self.slots = {n: mytype.get_attribute(n).get_new_result_variable(self, queue) for n in mytype.get_all_attribute_names()}
        self.slots["self"] = ResultVariable()
        self.slots["self"].set_value(self, None)
        self.sid = id(self)
        self.implemenations = set()

        # see inmanta.ast.execute.scheduler.QueueScheduler
        self.trackers = []

    def get_type(self):
        return self.type

    def set_attribute(self, name, value, location, recur=True):
        if name not in self.slots:
            raise NotFoundException(None, name, "cannot set attribute with name %s on type %s" % (name, str(self.type)))
        try:
            self.slots[name].set_value(value, location, recur)
        except RuntimeException as e:
            raise AttributeException(None, self, name, cause=e)

    def get_attribute(self, name) -> ResultVariable:
        try:
            return self.slots[name]
        except KeyError:
            raise NotFoundException(None, name, "could not find attribute with name: %s in type %s" % (name, self.type))

    def __repr__(self):
        return "%s %02x" % (self.type, self.sid)

    def __str__(self):
        return "%s (instantiated at %s)" % (self.type, self.location)

    def add_implementation(self, impl):
        if impl in self.implemenations:
            return False
        self.implemenations.add(impl)
        return True

    def final(self, excns):
        """
            The object should be complete, freeze all attributes
        """
        if len(self.implemenations) == 0:
            excns.append(RuntimeException(self, "Unable to select implementation for entity %s" %
                                          self.type.name))

        for k, v in self.slots.items():
            if not v.is_ready():
                if v.can_get():
                    v.freeze()
                else:
                    attr = self.type.get_attribute(k)
                    if attr.is_multi():
                        low = attr.low
                        length = len(v.value)
                        excns.append(UnsetException(
                            "The object %s is not complete: attribute %s (%s) requires %d values but only %d are set" %
                            (self, k, attr.location, low, length), self, attr))
                    else:
                        excns.append(UnsetException("The object %s is not complete: attribute %s (%s) is not set" %
                                                    (self, k, attr.location), self, attr))

    def dump(self):
        print("------------ ")
        print(str(self))
        print("------------ ")
        for (n, v) in self.slots.items():
            if(v.can_get()):

                value = v.value
                print("%s\t\t%s" % (n, value))
            else:
                print("BAD: %s\t\t%s" % (n, v.provider))

    def verify_done(self):
        for v in self.slots.values():
            if not v.can_get():
                return False
        return True

    def get_location(self) -> Location:
        return self.location
