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

import traceback
from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from inmanta import warnings
from inmanta.ast import export
from inmanta.execute.util import Unknown
from inmanta.stable_api import stable_api
from inmanta.types import DataclassProtocol
from inmanta.warnings import InmantaWarning

if TYPE_CHECKING:
    from inmanta import references
    from inmanta.ast.attribute import Attribute  # noqa: F401
    from inmanta.ast.entity import Entity
    from inmanta.ast.statements import Statement  # noqa: F401
    from inmanta.ast.statements.define import DefineEntity, DefineImport  # noqa: F401
    from inmanta.ast.type import NamedType, Type  # noqa: F401
    from inmanta.compiler import Compiler
    from inmanta.execute.runtime import DelayedResultVariable, ExecutionContext, Instance, ResultVariable  # noqa: F401


class TypeDeprecationWarning(InmantaWarning):
    pass


class Location(export.Exportable):
    __slots__ = ("file", "lnr")

    def __init__(self, file: str, lnr: int) -> None:
        self.file = file
        self.lnr = lnr

    def __str__(self) -> str:
        return "%s:%d" % (self.file, self.lnr)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return False
        return self.file == other.file and self.lnr == other.lnr

    def merge(self, other: "Location") -> "Location":
        if other is None:
            return self

        assert isinstance(other, Location)
        assert self.file == other.file

        return Location(self.file, min(self.lnr, other.lnr))

    def export(self) -> export.Location:
        # Location is 1-based, export.Position spec is 0-based
        # whole line: range from line:0 to line+1:0
        range_start: export.Position = export.Position(line=self.lnr - 1, character=0)
        range_end: export.Position = export.Position(line=self.lnr, character=0)
        return export.Location(uri=self.file, range=export.Range(start=range_start, end=range_end))


class Range(Location):
    __slots__ = ("start_char", "end_lnr", "end_char")

    def __init__(self, file: str, start_lnr: int, start_char: int, end_lnr: int, end_char: int) -> None:
        """
        Create a new Range instance.
        :param file: the file this Range is in
        :param start_lnr: the line number this Range starts on, 1-based
        :param start_char: the start character number of the Range, 1-based
        :param end_lnr: the line number this Range ends on, 1-based
        :param end_char: the end character number of the Range, exclusive, 1-based
        """
        Location.__init__(self, file, start_lnr)
        self.start_char = start_char
        self.end_lnr = end_lnr
        self.end_char = end_char

    def merge(self, other: Location) -> Location:
        if other is None:
            return self

        assert isinstance(other, Location)
        assert self.file == other.file

        if not isinstance(other, Range):
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

    def export(self) -> export.Location:
        range_start: export.Position = export.Position(line=self.lnr - 1, character=self.start_char - 1)
        range_end: export.Position = export.Position(line=self.end_lnr - 1, character=self.end_char - 1)
        result: export.Location = super().export()
        result.range = export.Range(start=range_start, end=range_end)
        return result

    def __str__(self) -> str:
        return "%s:%d:%d" % (self.file, self.lnr, self.start_char)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Range):
            return (
                self.file == other.file
                and self.lnr == other.lnr
                and self.start_char == other.start_char
                and self.end_lnr == other.end_lnr
                and self.end_char == other.end_char
            )
        return False


class AnchorTarget:
    """AnchorTarget is used purely at the periphery of the compiler"""

    __slots__ = ("location", "docstring")

    def __init__(
        self,
        location: Location,
        docstring: Optional[str] = None,
    ) -> None:
        """
        Create a new AnchorTarget instance.
        :param location: the location of the target of the anchor
        :param docstring: the docstring attached to the target
        """
        self.location = location
        self.docstring = docstring


class WithComment:
    """
    Mixin class for AST nodes that can have a comment attached to them.
    """

    comment: Optional[str] = None


class Locatable:
    __slots__ = ("_location",)

    def __init__(self) -> None:
        self._location: Optional[Location] = None

    def set_location(self, location: Location) -> None:
        assert location is not None and location.lnr > 0
        self._location = location

    def get_location(self) -> Optional[Location]:
        assert self._location is not None
        return self._location

    def copy_location(self, other: "Locatable") -> None:
        """
        Copy the location of this locatable to the given locatable
        """
        other.set_location(self.location)

    location = property(get_location, set_location)


class LocatableString:
    """
    A string with an attached source location.

    It is not a subtype of str, as str is not a normal class
    As such, it is very important to unwrap strings as this object is not an actual string.

    All identifiers produced by the parser are of this type.

    The unwrapping should be done in
    1. anywhere in DefinitionStatements
    2. in the constructors of other statements
    """

    def __init__(self, value: str, location: Range, lexpos: int, namespace: "Namespace") -> None:
        self.value = value
        self.location = location

        self.lnr = location.lnr
        self.elnr = location.end_lnr
        self.end = location.end_char
        self.start = location.start_char

        self.lexpos = lexpos
        self.namespace = namespace

    def get_value(self) -> str:
        return self.value

    def get_location(self) -> Range:
        return self.location

    def __str__(self) -> str:
        return self.value


class Anchor:
    def __init__(self, range: Range) -> None:
        self.range = range

    def get_range(self) -> Range:
        return self.range

    def get_location(self) -> Range:
        return self.range

    @abstractmethod
    def resolve(self) -> Optional[AnchorTarget]:
        raise NotImplementedError()


class TypeReferenceAnchor(Anchor):
    def __init__(self, namespace: "Namespace", type: LocatableString) -> None:
        Anchor.__init__(self, range=type.get_location())
        self.namespace = namespace
        self.type = type

    def resolve(self) -> Optional[AnchorTarget]:
        t = self.namespace.get_type(self.type)
        location = t.get_location()
        docstring = t.comment if isinstance(t, WithComment) else None
        if not location:
            return None
        return AnchorTarget(location=location, docstring=docstring)


class TypeAnchor(Anchor):
    """Reference to a resolved type"""

    def __init__(self, reference: LocatableString, type: "Type") -> None:
        """
        :param reference: the location we are referencing from
        :param type: the type that is being referenced
        """
        Anchor.__init__(self, range=reference.get_location())
        self.type = type
        self.type.get_location()

    def resolve(self) -> Optional[AnchorTarget]:
        t = self.type
        location = t.get_location()
        docstring = t.comment if isinstance(t, WithComment) else None
        if not location:
            return None
        return AnchorTarget(location=location, docstring=docstring)


class AttributeAnchor(Anchor):
    def __init__(self, range: Range, attribute: "Attribute") -> None:
        Anchor.__init__(self, range=range)
        self.attribute = attribute

    def resolve(self) -> Optional[AnchorTarget]:
        location = self.attribute.get_location()
        docstring = self.attribute.comment if isinstance(self.attribute, WithComment) else None
        if not location:
            return None
        return AnchorTarget(location=location, docstring=docstring)


class Namespaced(Locatable):
    __slots__ = ()

    @abstractmethod
    def get_namespace(self) -> "Namespace":
        raise NotImplementedError()


class Named(Namespaced):
    @abstractmethod
    def get_full_name(self) -> str:
        raise NotImplementedError()


class Import(Locatable):
    def __init__(self, target: "Namespace") -> None:
        Locatable.__init__(self)
        self.target = target


class MockImport(Import):
    def __init__(self, target: "Namespace") -> None:
        Locatable.__init__(self)
        self.target = target


class Namespace(Namespaced):
    """
    This class models a namespace that contains defined types, modules, ...
    """

    __slots__ = ("__name", "__parent", "__children", "defines_types", "visible_namespaces", "primitives", "scope", "__path")

    def __init__(self, name: str, parent: "Optional[Namespace]" = None) -> None:
        Namespaced.__init__(self)
        self.__name = name
        self.__parent = parent
        self.__children = {}  # type: Dict[str,Namespace]
        self.defines_types = {}  # type: Dict[str,NamedType]
        self.visible_namespaces: dict[str, Import]
        if self.__parent is not None:
            self.visible_namespaces = {self.get_full_name(): MockImport(self)}
            self.__parent.add_child(self)
        else:
            self.visible_namespaces = {name: MockImport(self)}
        self.primitives = None  # type: Optional[Dict[str,Type]]
        self.scope = None  # type:  Optional[ExecutionContext]
        self.__path: list[str]

        if self.__parent is None or self.__parent.get_name() == "__root__":
            self.__path = [self.__name]
        else:
            self.__path = self.__parent.to_path() + [self.__name]

    def set_primitives(self, primitives: "Dict[str,Type]") -> None:
        self.primitives = primitives
        for child in self.children():
            child.set_primitives(primitives)

        std = self.get_ns_from_string("std")
        assert std is not None

        self.visible_namespaces["std"] = MockImport(std)

    def get_primitives(self) -> "Dict[str,Type]":
        assert self.primitives is not None
        return self.primitives

    def get_scope(self) -> "ExecutionContext":
        assert self.scope is not None
        return self.scope

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

    def lookup_namespace(self, name: str) -> Import:
        if name not in self.visible_namespaces:
            raise NotFoundException(None, name, f"Namespace {name} not found.\nTry importing it with `import {name}`")
        return self.visible_namespaces[name]

    def lookup(self, name: str) -> "Union[Type, ResultVariable]":
        if "::" not in name:
            return self.get_scope().direct_lookup(name)
        parts = name.rsplit("::", 1)
        return self.lookup_namespace(parts[0]).target.get_scope().direct_lookup(parts[1])

    def get_type(self, typ: LocatableString) -> "Type":
        name: str = str(typ)
        assert self.primitives is not None
        if "::" in name:
            parts = name.rsplit("::", 1)
            if parts[0] in self.visible_namespaces:
                ns = self.visible_namespaces[parts[0]].target
                if parts[1] in ns.defines_types:
                    return ns.defines_types[parts[1]]
                else:
                    raise TypeNotFoundException(typ, ns)
            else:
                raise MissingImportException(typ, self, parts, str(self.location.file))
        elif name in self.primitives:
            if name == "number":
                warnings.warn(TypeDeprecationWarning("Type 'number' is deprecated, use 'float' or 'int' instead"))
            return self.primitives[name]
        else:
            cns = self  # type: Optional[Namespace]
            while cns is not None:
                if name in cns.defines_types:
                    return cns.defines_types[name]
                cns = cns.get_parent()

            raise TypeNotFoundException(typ, self)

    def get_name(self) -> str:
        """
        Get the name of this namespace
        """
        return self.__name

    def get_full_name(self) -> str:
        """
        Get the fully qualified name of this namespace
        """
        if self.__parent is None:
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

    def get_parent(self) -> "Optional[Namespace]":
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

    def children(self, recursive: bool = False) -> "List[Namespace]":
        """
        Get the children of this namespace
        """
        children = list(self.__children.values())
        if not recursive:
            return children

        for child in self.__children.values():
            children.extend(child.children(recursive=True))

        return children

    def get_child(self, name: str) -> "Optional[Namespace]":
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
            preparent = self.get_root()._get_ns(name_parts[:-1])
            assert preparent is not None
            parent = preparent
        return parent.get_child_or_create(name_parts[-1])

    def get_ns_from_string(self, fqtn: str) -> "Optional[Namespace]":
        """
        Get the namespace that is referenced to in the given fully qualified
        type name.

        :param fqtn: The type name
        """
        name_parts = fqtn.split("::")
        return self.get_root()._get_ns(name_parts)

    def _get_ns(self, ns_parts: list[str]) -> "Optional[Namespace]":
        """
        Return the namespace indicated by the parts list. Each element of
        the array represents a level in the namespace hierarchy.
        """
        if len(ns_parts) == 0:
            return None
        elif len(ns_parts) == 1:
            return self.get_child(ns_parts[0])
        else:
            child = self.get_child(ns_parts[0])
            if child is None:
                return None
            return child._get_ns(ns_parts[1:])

    def to_path(self) -> list[str]:
        """
        Return a list with the namespace path elements in it.
        """
        return self.__path

    def get_namespace(self) -> "Namespace":
        return self

    def get_location(self) -> Location:
        return self.location


@stable_api
class CompilerException(Exception, export.Exportable):
    """Base class for exceptions generated by the compiler"""

    def __init__(self, msg: str) -> None:
        Exception.__init__(self, msg)
        self.location = None  # type: Optional[Location]
        self.msg = msg
        # store root namespace so error reporters can inspect the compiler state
        self.root_ns: Optional[Namespace] = None

    def set_location(self, location: Location) -> None:
        if self.location is None:
            self.location = location

    def get_message(self) -> str:
        return self.msg

    def get_location(self) -> Optional[Location]:
        return self.location

    def get_causes(self) -> "List[CompilerException]":
        return []

    def format(self) -> str:
        """Make a string representation of this particular exception"""
        location = self.get_location()
        if location is not None:
            return f"{self.get_message()} ({location})"
        else:
            return self.get_message()

    def format_trace(self, indent: str = "", indent_level: int = 0) -> str:
        """Make a representation of this exception and its causes"""
        out = indent * indent_level + self.format()

        for cause in self.get_causes():
            part = cause.format_trace(indent=indent, indent_level=indent_level + 1)
            out += "\n" + indent * indent_level + "caused by:"
            out += "\n" + part

        return out

    def importantance(self) -> int:
        """
        Importance used to order exceptions when reporting multiple, lower is more important

        default is 100
        below 50 is for pure compiler errors (type, syntax)
        """
        return 100

    def attach_compile_info(self, compiler: "Compiler") -> None:
        self.root_ns = compiler.get_ns()

    def export(self) -> export.Error:
        location: Optional[Location] = self.get_location()
        module: Optional[str] = self.__class__.__module__
        name: str = self.__class__.__qualname__
        return export.Error(
            type=name if module is None else f"{module}.{name}",
            message=self.get_message(),
            location=location.export() if location is not None else None,
        )

    def __str__(self) -> str:
        return self.format()


@stable_api
class RuntimeException(CompilerException):
    """Baseclass for exceptions raised by the compiler after parsing is complete."""

    def __init__(self, stmt: "Optional[Locatable]", msg: str) -> None:
        CompilerException.__init__(self, msg)
        self.stmt = None
        if stmt is not None:
            self.set_location(stmt.get_location())
            self.stmt = stmt

    def set_statement(self, stmt: "Locatable", replace: bool = True) -> None:
        for cause in self.get_causes():
            if isinstance(cause, RuntimeException):
                cause.set_statement(stmt, replace)

        if replace or self.stmt is None:
            self.set_location(stmt.get_location())
            self.stmt = stmt

    def format(self) -> str:
        """Make a string representation of this particular exception"""
        if self.stmt is not None:
            return f"{self.get_message()} (reported in {self.stmt} ({self.get_location()}))"
        return super().format()


class InvalidCompilerState(RuntimeException):
    def __init__(self, stmt: "Optional[Locatable]", msg: str) -> None:
        super().__init__(stmt, "Invalid compiler state, this likely indicates a bug in the compiler. Details: %s" % msg)


class HyphenException(RuntimeException):
    def __init__(self, stmt: LocatableString) -> None:
        msg: str = "The use of '-' in identifiers is not allowed. please rename %s." % stmt.value
        RuntimeException.__init__(self, stmt, msg)


class CompilerRuntimeWarning(InmantaWarning, RuntimeException):
    """
    Baseclass for compiler warnings after parsing is complete.
    """

    def __init__(self, stmt: "Optional[Locatable]", msg: str) -> None:
        InmantaWarning.__init__(self)
        RuntimeException.__init__(self, stmt, msg)


class CompilerDeprecationWarning(CompilerRuntimeWarning):
    def __init__(self, stmt: Optional["Locatable"], msg: str) -> None:
        CompilerRuntimeWarning.__init__(self, stmt, msg)


class VariableShadowWarning(CompilerRuntimeWarning):
    def __init__(self, stmt: Optional["Locatable"], msg: str):
        CompilerRuntimeWarning.__init__(self, stmt, msg)


class TypeNotFoundException(RuntimeException):
    """Exception raised when a type is referenced that does not exist"""

    def __init__(self, type: LocatableString, ns: Namespace) -> None:
        RuntimeException.__init__(self, stmt=None, msg=f"could not find type {type} in namespace {ns}")
        self.type = type
        self.ns = ns
        self.set_location(type.get_location())

    def importantance(self) -> int:
        return 20


class MissingImportException(TypeNotFoundException):
    """Exception raised when a referenced type's module is missing from the namespace"""

    def __init__(
        self, type: LocatableString, ns: Namespace, parts: Optional[list[str]] = None, file: Optional[str] = None
    ) -> None:
        suggest_importing: str = ""
        suggest_file = ""
        if file:
            suggest_file = f" in {file}"
        if parts:
            suggest_importing = f".\nTry importing the module with `import {parts[0]}`{suggest_file}"
        super().__init__(type, ns)
        self.msg += suggest_importing


class AmbiguousTypeException(TypeNotFoundException):
    """
    Exception raised when a type is referenced in an unqualified manner in a context where it can not be unambiguously resolved.
    """

    def __init__(self, type: LocatableString, candidates: list["Entity"]) -> None:
        candidates = sorted(candidates, key=lambda x: x.get_full_name())
        RuntimeException.__init__(
            self,
            stmt=None,
            msg="Could not determine namespace for type %s. %d possible candidates exists: [%s]."
            " To resolve this, use the fully qualified name instead of the short name."
            % (type, len(candidates), ", ".join([x.get_full_name() for x in candidates])),
        )
        self.candidates = candidates
        self.type = type
        self.set_location(type.get_location())


def stringify_exception(exn: Exception) -> str:
    if isinstance(exn, CompilerException):
        return str(exn)
    return f"{exn.__class__.__name__}: {exn}"


@stable_api
class ExternalException(RuntimeException):
    """
    When a plugin call produces an exception that is not a :py:class:`RuntimeException`,
    it is wrapped in an ExternalException to make it conform to the expected interface
    """

    def __init__(self, stmt: Optional[Locatable], msg: str, cause: Exception) -> None:
        RuntimeException.__init__(self, stmt=stmt, msg=msg)

        self.__cause__ = cause

    def get_causes(self) -> list[CompilerException]:
        return []

    def format_trace(self, indent: str = "", indent_level: int = 0) -> str:
        """Make a representation of this exception and its causes"""

        out = indent * indent_level + self.format().replace("\n", "\n" + indent * indent_level)

        part = traceback.format_exception_only(self.__cause__.__class__, self.__cause__)
        out += "\n" + indent * indent_level + "caused by:\n"
        for line in part:
            out += indent * (indent_level + 1) + line

        return out

    def importantance(self) -> int:
        return 60


@stable_api
class ExplicitPluginException(ExternalException):
    """
    Base exception for wrapping an explicit :py:class:`inmanta.plugins.PluginException` raised from a plugin call.
    """

    def __init__(self, stmt: "Optional[Locatable]", msg: str, cause: "PluginException") -> None:
        ExternalException.__init__(self, stmt, msg, cause)
        self.__cause__: PluginException

    def export(self) -> export.Error:
        location: Optional[Location] = self.get_location()
        module: Optional[str] = self.__cause__.__class__.__module__
        name: str = self.__cause__.__class__.__qualname__
        return export.Error(
            type=name if module is None else f"{module}.{name}",
            message=self.__cause__.message,
            location=location.export() if location is not None else None,
            category=export.ErrorCategory.plugin,
        )

    def get_message(self) -> str:
        return self.msg + "\n" + self.__cause__.message


class WrappingRuntimeException(RuntimeException):
    """Baseclass for RuntimeExceptions wrapping other CompilerException"""

    def __init__(self, stmt: "Optional[Locatable]", msg: str, cause: CompilerException) -> None:
        if stmt is None and isinstance(cause, RuntimeException):
            stmt = cause.stmt

        RuntimeException.__init__(self, stmt=stmt, msg=msg)

        self.__cause__ = cause  # type: CompilerException

    def get_causes(self) -> list[CompilerException]:
        return [self.__cause__]

    def importantance(self) -> int:
        # less likely to be the cause then out child
        return self.__cause__.importantance() + 1


@stable_api
class AttributeException(WrappingRuntimeException):
    """Exception raise when an attribute could not be set, always wraps another exception"""

    def __init__(self, stmt: "Locatable", instance: "Instance", attribute: str, cause: RuntimeException) -> None:
        WrappingRuntimeException.__init__(
            self, stmt=stmt, msg=f"Could not set attribute `{attribute}` on instance `{instance}`", cause=cause
        )
        self.attribute = attribute
        self.instance = instance


class PluginTypeException(WrappingRuntimeException):
    """
    Raised when an argument or return value of a plugin is not in-line with the type
    annotation of that plugin. Wraps the validation error.
    """

    pass


class OptionalValueException(RuntimeException):
    """Exception raised when an optional value is accessed that has no value (and is frozen)"""

    def __init__(self, instance: "Instance", attribute: "Attribute") -> None:
        RuntimeException.__init__(
            self, None, f"Optional variable accessed that has no value (attribute `{attribute}` of `{instance}`)"
        )
        self.instance = instance
        self.attribute = attribute

    def importantance(self) -> int:
        return 61


class IndexException(RuntimeException):
    """Exception raised when an index definition is invalid"""

    def importantance(self) -> int:
        return 10


class TypingException(RuntimeException):
    """Base class for exceptions raised during the typing phase of compilation"""

    def importantance(self) -> int:
        return 10


class InvalidTypeAnnotation(TypingException):
    """
    Invalid type annotation, e.g. for a plugin.
    """


class DirectExecuteException(TypingException):
    """Exception raised when direct execute is called on a wrong object"""

    def importantance(self) -> int:
        return 11


class DataClassException(TypingException):
    """Exception in relation to dataclasses"""

    def __init__(self, entity: "Entity", msg: str) -> None:
        super().__init__(entity, msg)
        self.entity = entity

    def importantance(self) -> int:
        return 9


class DataClassMismatchException(DataClassException):
    """
    Exception due to a mismatch between both version of a dataclass

    """

    def __init__(
        self,
        entity: "Entity",
        dataclass: DataclassProtocol | None,
        dataclass_python_name: str,
        msg: str,
    ) -> None:
        """
        :param dataclass python dataclass, None if absent
        """
        super().__init__(entity, msg)
        self.dataclass = dataclass
        self.dataclass_python_name = dataclass_python_name


class KeyException(RuntimeException):
    pass

    def importantance(self) -> int:
        return 70


class CycleException(TypingException):
    """Exception raised when a type is its own parent (type cycle)"""

    def __init__(self, first_type: "DefineEntity", final_name: str) -> None:
        super().__init__(first_type, "")
        self.types = []  # type: List[DefineEntity]
        self.complete = False
        self.final_name = final_name

    def add(self, element: "DefineEntity") -> None:
        """Collect parent entities while traveling up the stack"""
        if self.complete:
            return
        if element.get_full_name() == self.final_name:
            self.complete = True
        self.types.append(element)

    def get_message(self) -> str:
        trace = ",".join([x.get_full_name() for x in self.types])
        return "Entity can not be its own parent %s" % (trace)


class NotFoundException(RuntimeException):
    def __init__(self, stmt: "Optional[Statement]", name: str, msg: "Optional[str]" = None) -> None:
        if msg is None:
            msg = "could not find value %s" % name
        RuntimeException.__init__(self, stmt, msg)
        self.name = name

    def importantance(self) -> int:
        return 20


@stable_api
class DoubleSetException(RuntimeException):
    def __init__(
        self, variable: "ResultVariable", stmt: "Optional[Statement]", newvalue: object, newlocation: Location
    ) -> None:
        self.variable: "ResultVariable" = variable
        self.newvalue = newvalue  # type: object
        self.newlocation = newlocation
        msg = "value set twice:\n\told value: {}\n\t\tset at {}\n\tnew value: {}\n\t\tset at {}\n".format(
            self.variable.value,
            self.variable.location,
            self.newvalue,
            self.newlocation,
        )
        RuntimeException.__init__(self, stmt, msg)

    def importantance(self) -> int:
        return 51


class ModifiedAfterFreezeException(RuntimeException):
    def __init__(
        self,
        rv: "DelayedResultVariable",
        instance: "Instance",
        attribute: "Attribute",
        value: object,
        location: Location,
        reverse: bool,
    ) -> None:
        RuntimeException.__init__(self, None, "List modified after freeze")
        self.instance = instance
        self.attribute = attribute
        self.value = value
        self.location = location
        self.resultvariable = rv
        self.reverse = reverse

    def importantance(self) -> int:
        return 50


class DuplicateException(TypingException):
    """Exception raise when something is defined twice"""

    def __init__(self, stmt: Locatable, other: Locatable, msg: str) -> None:
        TypingException.__init__(self, stmt, msg)
        self.other = other

    def format(self) -> str:
        return f"{self.get_message()} (original at ({self.location})) (duplicate at ({self.other.get_location()}))"

    def importantance(self) -> int:
        return 40


class CompilerError(Exception):
    pass


class MultiException(CompilerException):
    """A single exception collecting multiple CompilerExceptions"""

    def __init__(self, others: list[CompilerException]) -> None:
        CompilerException.__init__(self, "")
        self.others = others

    def get_causes(self) -> list[CompilerException]:
        def sortkey(item: CompilerException):
            location = item.get_location()
            if not location:
                file = ""
                line = 0
            else:
                file = location.file
                line = location.lnr

            return (item.importantance(), file, line)

        return sorted(self.others, key=sortkey)

    def format(self) -> str:
        return "Reported %d errors" % len(self.others)

    def __str__(self) -> str:
        return "Reported %d errors:\n\t" % len(self.others) + "\n\t".join([str(e) for e in self.others])

    def format_trace(self, indent: str = "", indent_level: int = 0) -> str:
        """Make a representation of this exception and its causes"""
        out = indent * indent_level + self.format()

        for i, cause in enumerate(self.get_causes()):
            part = cause.format_trace(indent=indent, indent_level=indent_level + 1)
            out += "\n" + indent * indent_level + f"error {i}:"
            out += "\n" + part

        return out


class UnsetException(RuntimeException):
    """
    This exception is thrown when an attribute is accessed that was not yet
    available (i.e. it has not been frozen yet).
    """

    def __init__(self, msg: str, instance: Optional["Instance"] = None, attribute: Optional["Attribute"] = None) -> None:
        RuntimeException.__init__(self, None, msg)
        self.instance: Optional["Instance"] = instance
        self.attribute: Optional["Attribute"] = attribute
        self.msg = msg

    def get_result_variable(self) -> Optional["Instance"]:
        return self.instance


class MultiUnsetException(RuntimeException):
    """
    This exception is thrown when multiple attributes are accessed that were not yet
    available (i.e. it has not been frozen yet).
    """

    def __init__(self, msg: str, result_variables: "list[ResultVariable[object]]") -> None:
        RuntimeException.__init__(self, None, msg)
        self.result_variables = result_variables


class UnknownException(Exception):
    """
    This exception is thrown when code tries to access a value that is
    unknown and cannot be determined during this evaluation. The code
    receiving this exception is responsible for invalidating any results
    depending on this value by return an instance of Unknown as well.
    """

    def __init__(self, unknown: Unknown):
        super().__init__()
        self.unknown = unknown


class AttributeNotFound(NotFoundException, AttributeError):
    """
    Exception used for backwards compatibility with try-except blocks around some_proxy.some_attr.
    This previously raised `NotFoundException` which is currently deprecated in this context.
    Its new behavior is to raise an AttributeError for compatibility with Python's builtin `hasattr`.
    """


# custom class to enable clean wrapping on the plugin boundary
class UnexpectedReference(RuntimeException):
    """
    Unexpected (undeclared) reference encountered during compiler or plugin execution.
    """

    def __init__(
        self, *, stmt: Optional[Locatable] = None, reference: "references.Reference[references.RefValue]", message: str
    ) -> None:
        RuntimeException.__init__(self, stmt, message)
        self.reference: references.Reference[references.RefValue] = reference


@stable_api
class PluginException(Exception):
    """
    Base class for custom exceptions raised from a plugin.
    """

    def __init__(self, message: str) -> None:
        self.message = message
