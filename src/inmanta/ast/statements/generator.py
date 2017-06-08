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

from . import GeneratorStatement
from inmanta.execute.util import Unknown
from inmanta.execute.runtime import ExecutionContext, Resolver, QueueScheduler, ResultVariable
from inmanta.ast import RuntimeException, TypingException, NotFoundException, Location, Namespace
from inmanta.execute.tracking import ImplementsTracker
from typing import List, Dict, Tuple
from inmanta.ast.statements import ExpressionStatement
from inmanta.ast.blocks import BasicBlock

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.entity import Entity, Implement  # noqa: F401


class SubConstructor(GeneratorStatement):
    """
        This statement selects an implementation for a given object and
        imports the statements
    """

    def __init__(self, instance_type: "", implements: "Implement") -> None:
        GeneratorStatement.__init__(self)
        self.type = instance_type
        self.implements = implements

    def normalize(self) -> None:
        # done in define type
        pass

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        try:
            resv = resolver.for_namespace(self.implements.constraint.namespace)
            return self.implements.constraint.requires_emit(resv, queue)
        except NotFoundException as e:
            e.set_statement(self.implements)
            raise e

    def execute(self, requires: Dict[object, ResultVariable], instance: Resolver, queue: QueueScheduler) -> object:
        """
            Evaluate this statement
        """
        expr = self.implements.constraint
        if not expr.execute(requires, instance, queue):
            return None

        myqueue = queue.for_tracker(ImplementsTracker(self, instance))

        implementations = self.implements.implementations

        for impl in implementations:
            if instance.add_implementation(impl):
                # generate a subscope/namespace for each loop
                xc = ExecutionContext(impl.statements, instance.for_namespace(impl.statements.namespace))
                xc.emit(myqueue)

        return None

    def __repr__(self) -> str:
        return "SubConstructor(%s)" % self.type


class For(GeneratorStatement):
    """
        A for loop
    """

    def __init__(self, variable: ExpressionStatement, loop_var: str, module: BasicBlock) -> None:
        GeneratorStatement.__init__(self)
        self.base = variable
        self.loop_var = loop_var
        self.module = module

    def __repr__(self) -> str:
        return "For(%s)" % self.loop_var

    def normalize(self) -> None:
        self.base.normalize()
        # self.loop_var.normalize(resolver)
        self.module.normalize()
        self.module.add_var(self.loop_var)

    def requires(self) -> List[str]:
        base = self.base.requires()
        var = self.loop_var
        ext = self.module.requires
        return list(set(base).union(ext) - set(var))

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return self.base.requires_emit(resolver, queue)

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        """
            Evaluate this statement.
        """
        var = self.base.execute(requires, resolver, queue)

        if isinstance(var, Unknown):
            return None

        for loop_var in var:
            # generate a subscope/namespace for each loop
            xc = ExecutionContext(self.module, resolver.for_namespace(self.module.namespace))
            loopvar = xc.lookup(self.loop_var)
            loopvar.set_provider(self)
            loopvar.set_value(loop_var, self.location)
            xc.emit(queue)

        return None


class Constructor(GeneratorStatement):
    """
        This class represents the usage of a constructor to create a new object.

        @param class_type: The type of the object that is created by this
            constructor call.
    """

    def __init__(self,
                 class_type: str,
                 attributes: List[Tuple[str, ExpressionStatement]],
                 location: Location,
                 namespace: Namespace) -> None:
        GeneratorStatement.__init__(self)
        self.class_type = class_type
        self.__attributes = {}
        self.implemented = False
        self.register = False
        self.location = location
        self.namespace = namespace
        for a in attributes:
            self.add_attribute(a[0], a[1])

    def normalize(self) -> None:
        self.type = self.namespace.get_type(self.class_type)
        for (k, v) in self.__attributes.items():
            v.normalize()

        # now check that all variables that have indexes on them, are already
        # defined and add the instance to the index
        for index in self.type.get_entity().get_indices():
            for attr in index:
                if attr not in self.attributes:
                    raise TypingException(self, "%s is part of an index and should be set in the constructor." % attr)

    def requires(self) -> List[str]:
        out = [req for (k, v) in self.__attributes.items() for req in v.requires()]
        out.extend([req for (k, v) in self.type.get_defaults().items() for req in v.requires()])
        out.extend([req for (k, v) in self.type.get_entity().get_default_values().items() for req in v.requires()])

        return out

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        preout = [x for x in self.__attributes.items()]
        preout.extend([x for x in self.type.get_entity().get_default_values().items()])

        out2 = {rk: rv for (k, v) in self.type.get_defaults().items()
                for (rk, rv) in v.requires_emit(resolver.for_namespace(v.get_namespace()), queue).items()}

        out = {rk: rv for (k, v) in preout for (rk, rv) in v.requires_emit(resolver, queue).items()}
        out.update(out2)
        return out

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler):
        """
            Evaluate this statement.
        """
        # the type to construct
        type_class = self.type.get_entity()

        # the attributes
        attributes = {k: v.execute(requires, resolver, queue) for (k, v) in self.__attributes.items()}

        for (k, v) in self.type.get_defaults().items():
            if(k not in attributes):
                attributes[k] = v.execute(requires, resolver, queue)

        for (k, v) in type_class.get_default_values().items():
            if(k not in attributes):
                attributes[k] = v.execute(requires, resolver, queue)

        # check if the instance already exists in the index (if there is one)
        instances = []
        for index in type_class._index_def:
            params = []
            for attr in index:
                params.append((attr, attributes[attr]))

            obj = type_class.lookup_index(params, self)
            if obj is not None:
                instances.append(obj)

        if len(instances) > 0:
            # ensure that instances are all the same objects
            first = instances[0]
            for i in instances[1:]:
                if i != first:
                    raise Exception("Inconsistent indexes detected!")

            object_instance = first
            for k, v in attributes.items():
                object_instance.set_attribute(k, v, self.location)

        else:
            # create the instance
            object_instance = type_class.get_instance(attributes, resolver, queue, self.location)
            self.copy_location(object_instance)

        # add anonymous implementations
        if self.implemented:
            # generate an import for the module
            raise Exception("don't know this feature")

        else:
            # generate an implementation
            for stmt in type_class.get_sub_constructor():
                stmt.emit(object_instance, queue)

        if self.register:
            raise Exception("don't know this feature")

        object_instance.trackers.append(queue.get_tracker())

        return object_instance

    def add_attribute(self, name: str, value: object):
        """
            Add an attribute to this constructor call
        """
        if name not in self.__attributes:
            self.__attributes[name] = value
        else:
            raise RuntimeException(self, "The attribute %s in the constructor call of %s is already set."
                                   % (name, self.class_type))

    def get_attributes(self) -> Dict[str, ExpressionStatement]:
        """
            Get the attribtues that are set for this constructor call
        """
        return self.__attributes

    attributes = property(get_attributes)

    def __repr__(self) -> str:
        """
            The representation of the this statement
        """
        return "Construct(%s)" % (self.class_type)
