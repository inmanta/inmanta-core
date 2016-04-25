"""
    Copyright 2016 Inmanta

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

from impera.execute.util import Unknown
from impera.execute.proxy import UnsetException
from impera.ast import Namespace, RuntimeException, NotFoundException


class ResultVariable(object):

    def __init__(self, value=[]):
        self.provider = None
        self.waiters = []
        self.value = value
        self.hasValue = False
        self.type = None

    def set_type(self, type):
        self.type = type

    def set_provider(self, provider):
        self.provider = provider

    def is_ready(self):
        return self.hasValue

    def await(self, waiter):
        if self.is_ready():
            waiter.ready(self)
        else:
            self.waiters.append(waiter)

    def set_value(self, value, recur=True):
        if self.hasValue:
            raise RuntimeException(None, "Value set twice")
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
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


class AttributeVariable(ResultVariable):

    def __init__(self, attribute, instance):
        self.attribute = attribute
        self.myself = instance
        ResultVariable.__init__(self)

    def set_value(self, value, recur=True):
        if self.hasValue:
            raise RuntimeException(None, "Value set twice")
        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)
        self.value = value
        self.hasValue = True
        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, False)
        for waiter in self.waiters:
            waiter.ready(self)


class DelayedResultVariable(ResultVariable):

    def __init__(self, queue, value=None):
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


class ListVariable(DelayedResultVariable):

    def __init__(self, attribute, instance, queue):
        self.attribute = attribute
        self.myself = instance
        DelayedResultVariable.__init__(self, queue, [])

    def set_value(self, value, recur=True):
        if self.hasValue:
            raise RuntimeException(None, "List modified after freeze")

        if isinstance(value, list):
            for v in value:
                self.set_value(v, recur)
            return

        if self.type is not None:
            self.type.validate(value)

        self.value.append(value)

        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, False)

        if self.attribute.high is not None:
            if self.attribute.high > len(self.value):
                raise RuntimeException(None, "List over full: max nr of items is %d, content is %s" %
                                       (self.attribute.high, self.value))

            if self.attribute.high > len(self.value):
                self.freeze()

        if self.can_get():
            self.queue()

    def can_get(self):
        return len(self.value) >= self.attribute.low


class OptionVariable(DelayedResultVariable):

    def __init__(self, attribute, instance, queue):
        DelayedResultVariable.__init__(self, queue)
        self.value = None
        self.attribute = attribute
        self.myself = instance
        self.queue()

    def set_value(self, value, recur=True):
        if self.hasValue:
            raise RuntimeException(None, "Option set after freeze %s.%s = %s / %s " %
                                   (self.myself, self.attribute, value, self.value))

        if not isinstance(value, Unknown) and self.type is not None:
            self.type.validate(value)

        # set counterpart
        if self.attribute.end and recur:
            value.set_attribute(self.attribute.end.name, self.myself, False)

        self.value = value
        self.freeze()

    def can_get(self):
        return True


class Waiter(object):

    def __init__(self, queue):
        self.waitcount = 1
        self.queue = queue

    def await(self, waitable):
        self.waitcount = self.waitcount + 1
        waitable.await(self)

    def ready(self, other):
        self.waitcount = self.waitcount - 1
        if self.waitcount == 0:
            self.queue.add_running(self)
        if self.waitcount < 0:
            raise Exception("SEVERE: COMPILER STATE CORRUPT: waitcount negative")


class QueueScheduler(object):

    def __init__(self, compiler, runqueue, waitqueue, types):
        self.compiler = compiler
        self.runqueue = runqueue
        self.waitqueue = waitqueue
        self.types = types

    def set_queue(self, name, queue):
        self.queues[name] = queue

    def add_running(self, item):
        return self.runqueue.append(item)

    def add_possible(self, rv):
        return self.waitqueue.append(rv)

    def get_compiler(self):
        return self.compiler

    def get_types(self):
        return self.types


class Resolver(object):

    def __init__(self, scopes):
        self.scopes = scopes

    def lookup(self, name):
        if "::" not in name:
            raise NotFoundException(None, name)

        parts = name.rsplit("::", 1)

        if parts[0] not in self.scopes:
            raise NotFoundException(None, name, "Namespace %s not found" % parts[0])

        return self.scopes[parts[0]].lookup(parts[1])

    def get_root_resolver(self):
        return self

    def for_namespace(self, namespace):
        return NamespaceResolver(self.scopes, namespace)


class NamespaceResolver(Resolver):

    def __init__(self, scopes, namespace):
        self.scopes = scopes
        # FIXME clean this up
        if isinstance(namespace, Namespace):
            namespace = namespace.get_full_name()
        self.scope = scopes[namespace]

    def lookup(self, name):
        return self.scope.lookup(name)

    def for_namespace(self, namespace):
        return NamespaceResolver(self.scopes, namespace)


class ExecutionContext(object):

    def __init__(self, block, resolver):
        self.block = block
        self.slots = {n: ResultVariable() for n in block.get_variables()}
        for (n, s) in self.slots.items():
            s.set_provider(self)
        self.resolver = resolver

    def lookup(self, name):
        if "::" in name:
            self.resolver.lookup(name)
        if name in self.slots:
            return self.slots[name]
        return self.resolver.lookup(name)

    def emit(self, queue):
        self.block.emit(self, queue)

    def get_root_resolver(self):
        return self.resolver.get_root_resolver()

    def for_namespace(self, namespace):
        return self.resolver.get_root_resolver().for_namespace(namespace)


class WaitUnit(Waiter):
    """
        Wait for either a single requirement or a map of requirements, call the resume method on the resumer
    """
    def __init__(self, queue_scheduler, resolver, require, resumer):
        Waiter.__init__(self, queue_scheduler)
        self.queue_scheduler = queue_scheduler
        self.resolver = resolver
        self.require = require
        self.resumer = resumer
        if isinstance(require, dict):
            for r in require.values():
                self.await(r)
        else:
            self.await(require)
        self.ready(self)

    def execute(self):
        try:
            requires = {k: v.get_value() for (k, v) in self.require.items()}
            self.resumer.resume(requires, self.resolver, self.queue_scheduler)
        except RuntimeException as e:
            e.set_statement(self.resumer)
            raise e


class HangUnit(Waiter):

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


class ExecutionUnit(Waiter):

    def __init__(self, queue_scheduler, resolver, result: ResultVariable, requires, expression):
        Waiter.__init__(self, queue_scheduler)
        self.result = result
        result.set_provider(self)
        self.requires = requires
        self.expression = expression
        self.resolver = resolver
        self.queue_scheduler = queue_scheduler
        for r in requires.values():
            self.await(r)
        self.ready(self)

    def execute(self):
        requires = {k: v.get_value() for (k, v) in self.requires.items()}
        try:
            value = self.expression.execute(requires, self.resolver, self.queue_scheduler)
            self.result.set_value(value)
        except RuntimeException as e:
            e.set_statement(self.expression)
            raise e

    def __repr__(self):
        return repr(self.expression)


class Instance(ExecutionContext):

    def __init__(self, type, resolver, queue):
        self.resolver = resolver.get_root_resolver()
        self.type = type
        self.slots = {n: type.get_attribute(n).get_new_Result_Variable(self, queue) for n in type.get_all_attribute_names()}
        self.slots["self"] = ResultVariable()
        self.slots["self"].set_value(self)
        self.sid = id(self)

    def get_type(self):
        return self.type

    def set_attribute(self, name, value, recur=True):
        if name not in self.slots:
            raise NotFoundException(None, name, "could not find attribute with name: %s in type %s" % (name, repr(self.type)))
        self.slots[name].set_value(value, recur)

    def get_attribute(self, name):
        try:
            return self.slots[name]
        except KeyError:
            raise NotFoundException(None, name, "could not find attribute with name: %s in type %s" % (name, self.type))

    def __repr__(self):
        return "%s %02x" % (self.type, self.sid)

    def final(self):
        """
            The object should be complete, freeze all attributes
        """
        for k, v in self.slots.items():
            if not v.is_ready():
                if v.can_get():
                    v.freeze()
                else:
                    attr = self.type.get_attribute(k)
                    raise RuntimeException(self, "The object %s is not complete: attribute %s (%s) is not set" %
                                           (self, k, attr.location))

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
