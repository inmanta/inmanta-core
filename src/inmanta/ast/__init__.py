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

from inmanta import util

from typing import Dict, Sequence, List, Optional, Union  # noqa: F401
from abc import abstractmethod


try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    import inmanta.ast.statements  # noqa: F401
    from inmanta.ast.type import Type, NamedType  # noqa: F401
    from inmanta.execute.runtime import ExecutionContext, Instance  # noqa: F401
    from inmanta.ast.statements import Statement  # noqa: F401
    from inmanta.ast.entity import Entity  # noqa: F401
    from inmanta.ast.statements.define import DefineImport  # noqa: F401


class Location(object):

    def __init__(self, file: str, lnr: int) -> None:
        self.file = file
        self.lnr = lnr

    def __str__(self) -> str:
        return "%s:%d" % (self.file, self.lnr)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return False
        return self.file == other.file and self.lnr == other.lnr

    def merge(self, other):
        if other is None:
            return self

        assert isinstance(other, Location)
        assert self.file == other.file

        return Location(self.file, min(self.lnr, other.lnr))


class Range(Location):

    def __init__(self, file: str, start_lnr: int, start_char: int, end_lnr: int, end_char: int) -> None:
        Location.__init__(self, file, start_lnr)
        self.start_char = start_char
        self.end_lnr = end_lnr
        self.end_char = end_char

    def merge(self, other):
        if other is None:
            return self

        assert isinstance(other, Location)
        assert self.file == other.file

        if isinstance(other, Location):
            return Location(self.file, min(self.lnr, other.lnr))
        else:
            if other.lnr < self.lnr:
                lnr = other.lnr
                start_char = other.start_char
            elif other.lnr == self.lnr:
                lnr = other.lnr
                start_char = min(self.start_char, other.start_char)
            else:
                lnr = self.lnr
                start_char = self.start_char

            if other.end_lnr > self.end_lnr:
                end_lnr = other.end_lnr
                end_char = other.end_char
            elif other.end_lnr == self.end_lnr:
                end_lnr = other.end_lnr
                end_char = max(self.end_char, other.end_char)
            else:
                end_lnr = self.lnr
                end_char = self.end_char
            return Range(self.file, lnr, start_char, end_lnr, end_char)

    def __str__(self) -> str:
        return "%s:%d:%d" % (self.file, self.lnr, self.start_char)


class Locatable(object):

    def __init__(self):
        self._location = None  # type: Location

    def set_location(self, location: Location):
        assert location is not None and location.lnr > 0
        self._location = location

    def get_location(self) -> Location:
        assert self._location is not None
        return self._location

    location = property(get_location, set_location)


class LocatableString(object):
    """
        A string with an attached source location.

        It is not a subtype of str, as str is not a normal class
        As such, it is very important to unwrap strings ad this object is not an actual string.

        All identifiers produced by the parser are of this type.

        The unwrapping should be done in
        1. anywhere in DefinitionStatements
        2. in the constructors of other statements
    """

    def __init__(self, value, location: Range, lexpos, namespace):
        self.value = value
        self.location = location

        self.lnr = location.lnr
        self.elnr = location.end_lnr
        self.end = location.end_char
        self.start = location.start_char

        self.lexpos = lexpos
        self.namespace = namespace

    def get_value(self):
        return self.value

    def get_location(self):
        return self.location

    def __str__(self):
        return self.value


class Anchor(object):

    def __init__(self, range: Range):
        self.range = range

    def get_range(self) -> Range:
        return self.range

    def get_location(self) -> Range:
        return self.range

    @abstractmethod
    def resolve(self):
        raise NotImplementedError()


class TypeReferenceAnchor(Anchor):

    def __init__(self, range: Range, namespace: "Namespace", type: str):
        Anchor.__init__(self, range=range)
        self.namespace = namespace
        self.type = type

    def resolve(self):
        t = self.namespace.get_type(self.type)
        return t.get_location()


class AttributeReferenceAnchor(Anchor):

    def __init__(self, range: Range, namespace: "Namespace", type: str, attribute: str):
        Anchor.__init__(self, range=range)
        self.namespace = namespace
        self.type = type
        self.attribute = attribute

    def resolve(self):
        return self.namespace.get_type(self.type).get_attribute(self.attribute).get_location()


class Namespaced(Locatable):

    @abstractmethod
    def get_namespace(self) -> "Namespace":
        raise NotImplementedError()


class Named(Namespaced):

    @abstractmethod
    def get_full_name(self) -> str:
        raise NotImplementedError()


class MockImport(Locatable):

    def __init__(self, target: "Namespace") -> None:
        Locatable.__init__(self)
        self.target = target


class Namespace(Namespaced):
    """
        This class models a namespace that contains defined types, modules, ...
    """

    def __init__(self, name: str, parent: "Optional[Namespace]"=None) -> None:
        Namespaced.__init__(self)
        self.__name = name
        self.__parent = parent
        self.__children = {}  # type: Dict[str,Namespace]
        self.defines_types = {}  # type: Dict[str,NamedType]
        if self.__parent is not None:
            # type: Dict[str,Union[DefineImport, MockImport]]
            self.visible_namespaces = {self.get_full_name(): MockImport(self)}
            self.__parent.add_child(self)
        else:
            self.visible_namespaces = {name: MockImport(self)}
        self.primitives = None  # type: Dict[str,Type]
        self.scope = None  # type: ExecutionContext

    def set_primitives(self, primitives: "Dict[str,Type]") -> None:
        self.primitives = primitives
        for child in self.children():
            child.set_primitives(primitives)

        self.visible_namespaces["std"] = MockImport(self.get_ns_from_string("std"))

    def define_type(self, name: str, newtype: "NamedType") -> None:
        if name in self.defines_types:
            raise newtype.get_double_defined_exception(self.defines_types[name])
        self.defines_types[name] = newtype

    def import_ns(self, name: str, ns: "DefineImport") -> None:
        if name in self.visible_namespaces:
            other = self.visible_namespaces[name]
            if not isinstance(other, MockImport):
                raise DuplicateException(ns, self.visible_namespaces[name], "Two import statements have the same name")
        self.visible_namespaces[name] = ns

    def lookup(self, name: str) -> "Type":
        if "::" not in name:
            return self.scope.direct_lookup(name)

        parts = name.rsplit("::", 1)

        if parts[0] not in self.visible_namespaces:
            raise NotFoundException(None, name, "Variable %s not found" % parts[0])

        return self.visible_namespaces[parts[0]].target.scope.direct_lookup(parts[1])

    def get_type(self, name: str) -> "NamedType":
        if "::" in name:
            parts = name.rsplit("::", 1)
            if parts[0] in self.visible_namespaces:
                ns = self.visible_namespaces[parts[0]].target
                if parts[1] in ns.defines_types:
                    return ns.defines_types[parts[1]]
                else:
                    raise TypeNotFoundException(name, ns)
            else:
                raise TypeNotFoundException(name, self)
        elif name in self.primitives:
            return self.primitives[name]
        else:
            cns = self
            while cns is not None:
                if name in cns.defines_types:
                    return cns.defines_types[name]
                cns = cns.get_parent()
            raise TypeNotFoundException(name, self)

    def get_name(self) -> str:
        """
            Get the name of this namespace
        """
        return self.__name

    def get_full_name(self) -> str:
        """
            Get the fully qualified name of this namespace
        """
        if(self.__parent is None):
            raise Exception("Should not occur, compiler corrupt")
        if self.__parent.__parent is None:
            return self.get_name()
        return self.__parent.get_full_name() + "::" + self.get_name()

    name = property(get_name)

    def set_parent(self, parent: "Namespace") -> None:
        """
            Set the parent of this namespace. This namespace is also added to
            the child list of the parent.
        """
        self.__parent = parent
        self.__parent.add_child(self)

    def get_parent(self) -> "Namespace":
        """
            Get the parent namespace
        """
        return self.__parent

    parent = property(get_parent, set_parent)

    def get_root(self) -> "Namespace":
        """
            Get the root
        """
        if self.__parent is None:
            return self
        return self.__parent.get_root()

    def add_child(self, child_ns: "Namespace") -> None:
        """
            Add a child to the namespace.
        """
        self.__children[child_ns.get_name()] = child_ns

    def __repr__(self) -> str:
        """
            The representation of this object
        """
        if self.__parent is not None and self.__parent.get_name() != "__root__":
            return repr(self.__parent) + "::" + self.__name

        return self.__name

    def children(self, recursive: bool=False) -> "List[Namespace]":
        """
            Get the children of this namespace
        """
        children = list(self.__children.values())
        if not recursive:
            return children

        for child in self.__children.values():
            children.extend(child.children(recursive=True))

        return children

    def get_child(self, name: str) -> "Namespace":
        """
            Returns the child namespace with the given name or None if it does
            not exist.
        """
        if name in self.__children:
            return self.__children[name]
        return None

    def get_child_or_create(self, name: str) -> "Namespace":
        """
            Returns the child namespace with the given name or None if it does
            not exist.
        """
        if name in self.__children:
            return self.__children[name]
        out = Namespace(name, self)
        return out

    def get_ns_or_create(self, name: str) -> "Namespace":
        """
            Returns the child namespace with the given name or None if it does
            not exist.
        """
        name_parts = name.split("::")
        if len(name_parts) == 1:
            parent = self.get_root()
        else:
            parent = self.get_root()._get_ns(name_parts[:-1])
        return parent.get_child_or_create(name_parts[-1])

    def get_ns_from_string(self, fqtn: str) -> "Namespace":
        """
            Get the namespace that is referenced to in the given fully qualified
            type name.

            :param fqtn: The type name
        """
        name_parts = fqtn.split("::")
        return self.get_root()._get_ns(name_parts)

    def _get_ns(self, ns_parts: List[str]) -> "Namespace":
        """
            Return the namespace indicated by the parts list. Each element of
            the array represents a level in the namespace hierarchy.
        """
        if len(ns_parts) == 0:
            return None
        elif len(ns_parts) == 1:
            return self.get_child(ns_parts[0])
        else:
            return self.get_child(ns_parts[0])._get_ns(ns_parts[1:])

    @util.memoize
    def to_path(self) -> List[str]:
        """
            Return a list with the namespace path elements in it.
        """
        if self.__parent is None or self.__parent.get_name() == "__root__":
            return [self.__name]
        else:
            return self.__parent.to_path() + [self.__name]

    def get_namespace(self) -> "Namespace":
        return self

    def get_location(self) -> Location:
        return self.location


class CompilerException(Exception):

    def __init__(self, msg: str=None) -> None:
        Exception.__init__(self, msg)
        self.location = None  # type: Location

    def set_location(self, location: Location) -> None:
        if self.location is None:
            self.location = location


class RuntimeException(CompilerException):

    def __init__(self, stmt: "Optional[Locatable]", msg: str, root_cause_chance=10) -> None:
        CompilerException.__init__(self)
        self.stmt = None
        if stmt is not None:
            self.set_location(stmt.get_location())
            self.stmt = stmt
        self.msg = msg
        self.root_cause_chance = root_cause_chance

    def set_statement(self, stmt: "Locatable"):
        self.set_location(stmt.get_location())
        self.stmt = stmt

    def __str__(self) -> str:
        if self.stmt is None and self.location is None:
            return self.msg
        else:
            return "%s (reported in %s (%s))" % (self.msg, self.stmt, self.location)

    def __le__(self, other) -> bool:
        return self.root_cause_chance < other.root_cause_chance


class TypeNotFoundException(RuntimeException):

    def __init__(self, type: str, ns: Namespace) -> None:
        RuntimeException.__init__(self, stmt=None, msg="could not find type %s in namespace %s" % (type, ns))
        self.type = type
        self.ns = ns


def stringify_exception(exn: Exception) -> str:
    if isinstance(exn, CompilerException):
        return str(exn)
    return "%s: %s" % (exn.__class__.__name__, str(exn))


class WrappingRuntimeException(RuntimeException):

    def __init__(self, stmt: Locatable, msg: str, cause: Exception) -> None:
        if stmt is None:
            if isinstance(cause, RuntimeException):
                stmt = cause.stmt
        longmsg = "%s caused by %s" % (msg, stringify_exception(cause))
        RuntimeException.__init__(self, stmt=stmt, msg=longmsg)
        self.__cause__ = cause


class AttributeException(WrappingRuntimeException):

    def __init__(self, stmt: "Statement", entity: "Instance", attribute: str, cause: Exception) -> None:
        WrappingRuntimeException.__init__(
            self, stmt=stmt, msg="Could not set attribute `%s` on instance `%s`" % (attribute, str(entity)), cause=cause)
        self.attribute = attribute
        self.entity = entity


class OptionalValueException(RuntimeException):

    def __init__(self, instance: "Instance", attribute: str) -> None:
        RuntimeException.__init__(self, None, "Optional variable accessed that has no value (%s.%s)" % (instance, attribute))
        self.instance = instance
        self.attribute = attribute


class TypingException(RuntimeException):
    pass


class KeyException(RuntimeException):
    pass


class CycleExcpetion(TypingException):

    def __init__(self, first_type, final_name):
        super(CycleExcpetion, self).__init__(first_type, None)
        self.types = []
        self.complete = False
        self.final_name = final_name

    def add(self, element):
        if(self.complete):
            return
        if element.get_full_name() == self.final_name:
            self.complete = True
        self.types.append(element)

    def __str__(self, *args, **kwargs):
        trace = ",".join([x.get_full_name() for x in self.types])
        return "Entity can not be its own parent %s (reported in %s (%s))" % (trace, self.stmt, self.location)


class ModuleNotFoundException(RuntimeException):

    def __init__(self, name: str, stmt: "Statement", msg: str=None) -> None:
        if msg is None:
            msg = "could not find module %s" % name
        RuntimeException.__init__(self, stmt, msg)
        self.name = name


class NotFoundException(RuntimeException):

    def __init__(self, stmt: "Statement", name: str, msg: "Optional[str]"=None) -> None:
        if msg is None:
            msg = "could not find value %s" % name
        RuntimeException.__init__(self, stmt, msg)
        self.name = name


class DoubleSetException(RuntimeException):

    def __init__(self, stmt: "Statement", value: object, location: Location, newvalue: object, newlocation: Location) -> None:
        self.value = value  # type: object
        self.location = location
        self.newvalue = newvalue  # type: object
        self.newlocation = newlocation
        msg = ("value set twice: \n\told value: %s\n\t\tset at %s\n\tnew value: %s\n\t\tset at %s\n"
               % (self.value, self.location, self.newvalue, self.newlocation))
        RuntimeException.__init__(self, stmt, msg)


class DuplicateException(TypingException):

    def __init__(self, stmt: Locatable, other: Locatable, msg: str) -> None:
        TypingException.__init__(self, stmt, msg)
        self.other = other

    def __str__(self) -> str:
        return "%s (reported at (%s)) (duplicate at (%s))" % (self.msg, self.location, self.other.get_location())


class CompilerError(Exception):

    pass


class MultiException(CompilerException):

    def __init__(self, others: List[Exception]) -> None:
        self.others = others

    def __str__(self) -> str:
        return "Reported %d errors:\n\t" % len(self.others) + '\n\t'.join([str(e) for e in self.others])
