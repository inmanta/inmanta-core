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

import logging
from itertools import chain
from typing import Dict, Iterator, List, Optional, Set, Tuple  # noqa: F401

from inmanta.ast import (
    AttributeReferenceAnchor,
    DuplicateException,
    LocatableString,
    Location,
    Namespace,
    NotFoundException,
    RuntimeException,
    TypeReferenceAnchor,
    TypingException,
)
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import DynamicStatement, ExpressionStatement
from inmanta.ast.statements.assign import SetAttributeHelper
from inmanta.ast.type import Type as InmantaType
from inmanta.const import LOG_LEVEL_TRACE
from inmanta.execute.runtime import ExecutionContext, ExecutionUnit, QueueScheduler, Resolver, ResultCollector, ResultVariable
from inmanta.execute.tracking import ImplementsTracker
from inmanta.execute.util import Unknown

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.entity import Default, Entity, Implement, EntityLike  # noqa: F401

LOGGER = logging.getLogger(__name__)


class SubConstructor(ExpressionStatement):
    """
        This statement selects an implementation for a given object and
        imports the statements
    """

    def __init__(self, instance_type: "Entity", implements: "Implement") -> None:
        super().__init__()
        self.type = instance_type
        self.location = instance_type.get_location()
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

    def execute(self, requires: Dict[object, object], instance: Resolver, queue: QueueScheduler) -> object:
        """
            Evaluate this statement
        """
        LOGGER.log(LOG_LEVEL_TRACE, "executing subconstructor for %s implement %s", self.type, self.implements.location)
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


class GradualFor(ResultCollector):
    # this class might be unnecessary if receive-result is always called and exactly once

    def __init__(self, stmt: "For", resolver: Resolver, queue: QueueScheduler):
        self.resolver = resolver
        self.queue = queue
        self.stmt = stmt
        self.seen = set()  # type: Set[int]

    def receive_result(self, value, location):
        if id(value) in self.seen:
            return
        self.seen.add(id(value))

        xc = ExecutionContext(self.stmt.module, self.resolver.for_namespace(self.stmt.module.namespace))
        loopvar = xc.lookup(self.stmt.loop_var)
        loopvar.set_provider(self.stmt)
        loopvar.set_value(value, self.stmt.location)
        xc.emit(self.queue)


class For(DynamicStatement):
    """
        A for loop
    """

    def __init__(self, variable: ExpressionStatement, loop_var: LocatableString, module: BasicBlock) -> None:
        super().__init__()
        self.base = variable
        self.loop_var = str(loop_var)
        self.loop_var_loc = loop_var.get_location()
        self.module = module
        self.anchors.extend(module.get_anchors())
        self.anchors.extend(variable.get_anchors())

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

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        target = ResultVariable()
        reqs = self.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        """Not an actual expression, but following the pattern"""

        # pass context via requires!
        helper = GradualFor(self, resolver, queue)

        helperwrapped = ResultVariable()
        helperwrapped.set_value(helper, self.location)

        basereq = self.base.requires_emit_gradual(resolver, queue, helper)
        basereq[self] = helperwrapped

        return basereq

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
            Evaluate this statement.
        """
        var = self.base.execute(requires, resolver, queue)

        if isinstance(var, Unknown):
            return None

        if not isinstance(var, list):
            raise TypingException(self, "A for loop can only be applied to lists and relations")

        helper = requires[self]

        for loop_var in var:
            # generate a subscope/namespace for each loop
            helper.receive_result(loop_var, self.location)

        return None


class If(ExpressionStatement):
    """
        An if Statement
    """

    def __init__(self, condition: ExpressionStatement, if_branch: BasicBlock, else_branch: BasicBlock) -> None:
        super().__init__()
        self.condition: ExpressionStatement = condition
        self.if_branch: BasicBlock = if_branch
        self.else_branch: BasicBlock = else_branch
        self.anchors.extend(condition.get_anchors())
        self.anchors.extend(if_branch.get_anchors())
        self.anchors.extend(else_branch.get_anchors())

    def __repr__(self) -> str:
        return "If"

    def normalize(self) -> None:
        self.condition.normalize()
        self.if_branch.normalize()
        self.else_branch.normalize()

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return self.condition.requires_emit(resolver, queue)

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
            Evaluate this statement.
        """
        cond: object = self.condition.execute(requires, resolver, queue)
        if isinstance(cond, Unknown):
            return None
        if not isinstance(cond, bool):
            raise TypingException(self, "The condition for an if statement can only be a boolean expression")
        branch: BasicBlock = self.if_branch if cond else self.else_branch
        xc = ExecutionContext(branch, resolver.for_namespace(branch.namespace))
        xc.emit(queue)
        return None


class Constructor(ExpressionStatement):
    """
        This class represents the usage of a constructor to create a new object.

        :param class_type: The type of the object that is created by this
            constructor call.
    """

    def __init__(
        self,
        class_type: LocatableString,
        attributes: List[Tuple[LocatableString, ExpressionStatement]],
        wrapped_kwargs: List["WrappedKwargs"],
        location: Location,
        namespace: Namespace,
    ) -> None:
        super().__init__()
        self.class_type = class_type
        self.__attributes = {}  # type: Dict[str,ExpressionStatement]
        self.__wrapped_kwarg_attributes: List[WrappedKwargs] = wrapped_kwargs
        self.location = location
        self.namespace = namespace
        self.anchors.append(TypeReferenceAnchor(namespace, class_type))
        for a in attributes:
            self.add_attribute(a[0], a[1])
        self.type: Optional["EntityLike"] = None
        self.required_kwargs: List[str] = []

        self._direct_attributes = {}  # type: Dict[str,ExpressionStatement]
        self._indirect_attributes = {}  # type: Dict[str,ExpressionStatement]

    def pretty_print(self) -> str:
        return "%s(%s)" % (
            self.class_type,
            ",".join(
                chain(
                    ("%s=%s" % (k, v.pretty_print()) for k, v in self.attributes.items()),
                    ("**%s" % kwargs.pretty_print() for kwargs in self.wrapped_kwargs),
                )
            ),
        )

    def normalize(self) -> None:
        mytype: "EntityLike" = self.namespace.get_type(self.class_type)
        self.type = mytype

        for (k, v) in self.__attributes.items():
            v.normalize()

        for wrapped_kwargs in self.wrapped_kwargs:
            wrapped_kwargs.normalize()

        inindex = set()

        all_attributes = dict(self.type.get_default_values())
        all_attributes.update(self.__attributes)

        # now check that all variables that have indexes on them, are already
        # defined and add the instance to the index
        for index in self.type.get_entity().get_indices():
            for attr in index:
                if attr not in all_attributes:
                    self.required_kwargs.append(attr)
                    continue
                inindex.add(attr)
        if self.required_kwargs and not self.wrapped_kwargs:
            raise TypingException(
                self,
                "attributes %s are part of an index and should be set in the constructor." % ",".join(self.required_kwargs),
            )

        for (k, v) in all_attributes.items():
            attribute = self.type.get_entity().get_attribute(k)
            if attribute is None:
                raise TypingException(self, "no attribute %s on type %s" % (k, self.type.get_full_name()))
            if k not in inindex:
                self._indirect_attributes[k] = v
            else:
                self._direct_attributes[k] = v

    def requires(self) -> List[str]:
        out = [req for (k, v) in self.__attributes.items() for req in v.requires()]
        out.extend(req for kwargs in self.__wrapped_kwarg_attributes for req in kwargs.requires())
        out.extend(req for (k, v) in self.get_default_values().items() for req in v.requires())
        return out

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        # direct
        direct = [x for x in self._direct_attributes.items()]

        direct_requires = {rk: rv for (k, v) in direct for (rk, rv) in v.requires_emit(resolver, queue).items()}
        direct_requires.update(
            {rk: rv for kwargs in self.__wrapped_kwarg_attributes for (rk, rv) in kwargs.requires_emit(resolver, queue).items()}
        )
        LOGGER.log(
            LOG_LEVEL_TRACE, "emitting constructor for %s at %s with %s", self.class_type, self.location, direct_requires
        )

        return direct_requires

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler):
        """
            Evaluate this statement.
        """
        LOGGER.log(LOG_LEVEL_TRACE, "executing constructor for %s at %s", self.class_type, self.location)

        # the type to construct
        type_class = self.type.get_entity()

        # kwargs
        kwarg_attrs: Dict[str, InmantaType] = {}
        for kwargs in self.wrapped_kwargs:
            for (k, v) in kwargs.execute(requires, resolver, queue):
                if k in self.attributes or k in kwarg_attrs:
                    raise RuntimeException(
                        self, "The attribute %s is set twice in the constructor call of %s." % (k, self.class_type)
                    )
                attribute = self.type.get_entity().get_attribute(k)
                if attribute is None:
                    raise TypingException(self, "no attribute %s on type %s" % (k, self.type.get_full_name()))
                kwarg_attrs[k] = v

        missing_attrs: List[str] = [attr for attr in self.required_kwargs if attr not in kwarg_attrs]
        if missing_attrs:
            raise TypingException(
                self, "attributes %s are part of an index and should be set in the constructor." % ",".join(missing_attrs)
            )

        # the attributes
        attributes = {k: v.execute(requires, resolver, queue) for (k, v) in self._direct_attributes.items()}
        attributes.update(kwarg_attrs)

        # check if the instance already exists in the index (if there is one)
        instances = []
        for index in type_class.get_indices():
            params = []
            for attr in index:
                params.append((attr, attributes[attr]))

            obj = type_class.lookup_index(params, self)

            if obj is not None:
                if obj.get_type().get_entity() != type_class:
                    raise DuplicateException(self, obj, "Type found in index is not an exact match")
                instances.append(obj)

        if len(instances) > 0:
            # ensure that instances are all the same objects
            first = instances[0]
            for i in instances[1:]:
                if i != first:
                    raise Exception("Inconsistent indexes detected!")

            object_instance = first
            self.copy_location(object_instance)
            for k, v in attributes.items():
                object_instance.set_attribute(k, v, self.location)
        else:
            # create the instance
            object_instance = type_class.get_instance(attributes, resolver, queue, self.location)

        # deferred execution for indirect attributes
        for attributename, valueexpression in self._indirect_attributes.items():
            var = object_instance.get_attribute(attributename)
            if var.is_multi():
                # gradual only for multi
                # to preserve order on lists used in attributes
                # while allowing gradual execution on relations
                reqs = valueexpression.requires_emit_gradual(resolver, queue, var)
            else:
                reqs = valueexpression.requires_emit(resolver, queue)
            SetAttributeHelper(queue, resolver, var, reqs, valueexpression, self, object_instance, attributename)

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
            self.anchors.append(AttributeReferenceAnchor(lname.get_location(), lname.namespace, self.class_type, name))
            self.anchors.extend(value.get_anchors())
        else:
            raise RuntimeException(
                self, "The attribute %s in the constructor call of %s is already set." % (name, self.class_type)
            )

    def get_attributes(self) -> Dict[str, ExpressionStatement]:
        """
            Get the attribtues that are set for this constructor call
        """
        return self.__attributes

    def get_wrapped_kwargs(self) -> List["WrappedKwargs"]:
        """
            Get the wrapped kwargs that are set for this constructor call
        """
        return self.__wrapped_kwarg_attributes

    attributes = property(get_attributes)
    wrapped_kwargs = property(get_wrapped_kwargs)

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

    def __init__(self, dictionary: ExpressionStatement) -> None:
        super().__init__()
        self.dictionary: ExpressionStatement = dictionary

    def __repr__(self) -> str:
        return "**%s" % repr(self.dictionary)

    def normalize(self) -> None:
        self.dictionary.normalize()

    def requires(self) -> List[str]:
        return self.dictionary.requires()

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return self.dictionary.requires_emit(resolver, queue)

    def execute(
        self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler
    ) -> List[Tuple[str, InmantaType]]:
        dct: object = self.dictionary.execute(requires, resolver, queue)
        if not isinstance(dct, Dict):
            raise TypingException(self, "The ** operator can only be applied to dictionaries")
        return list(dct.items())
