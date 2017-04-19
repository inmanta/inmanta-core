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

from inmanta import util


class Location(object):

    def __init__(self, file, lnr):
        self.file = file
        self.lnr = lnr

    def __str__(self, *args, **kwargs):
        return "%s:%d" % (self.file, self.lnr)

    def __eq__(self, other):
        return self.file == other.file and self.lnr == other.lnr


class MockImport(object):

    def __init__(self, target):
        self.target = target


class Namespace(object):
    """
        This class models a namespace that contains defined types, modules, ...
    """

    def __init__(self, name, parent=None):
        self.__name = name
        self.__parent = parent
        self.__children = {}
        self.unit = None
        self.defines_types = {}
        if self.__parent is not None:
            self.visible_namespaces = {self.get_full_name(): MockImport(self)}
            self.__parent.add_child(self)
        else:
            self.visible_namespaces = {name: MockImport(self)}
        self.primitives = None
        self.scope = None

    def set_primitives(self, primitives):
        self.primitives = primitives
        for child in self.children():
            child.set_primitives(primitives)

        self.visible_namespaces["std"] = MockImport(self.get_ns_from_string("std"))

    def define_type(self, name, newtype: "Namespaced"):
        if name in self.defines_types:
            raise newtype.get_double_defined_exception(self.defines_types[name])
        self.defines_types[name] = newtype

    def import_ns(self, name, ns):
        if name in self.visible_namespaces and not isinstance(self.visible_namespaces[name], MockImport):
            raise DuplicateException(ns, self.visible_namespaces[name], "Two import statements have the same name")
        self.visible_namespaces[name] = ns

    def lookup(self, name):
        if "::" not in name:
            return self.scope.direct_lookup(name)

        parts = name.rsplit("::", 1)

        if parts[0] not in self.visible_namespaces:
            raise NotFoundException(None, name, "Variable %s not found" % parts[0])

        return self.visible_namespaces[parts[0]].target.scope.direct_lookup(parts[1])

    def get_type(self, name):
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

    def get_name(self):
        """
            Get the name of this namespace
        """
        return self.__name

    def get_full_name(self):
        """
            Get the name of this namespace
        """
        if(self.__parent is None):
            raise Exception("Should not occur, compiler corrupt")
        if self.__parent.__parent is None:
            return self.get_name()
        return self.__parent.get_full_name() + "::" + self.get_name()

    name = property(get_name)

    def set_parent(self, parent):
        """
            Set the parent of this namespace. This namespace is also added to
            the child list of the parent.
        """
        self.__parent = parent
        self.__parent.add_child(self)

    def get_parent(self):
        """
            Get the parent namespace
        """
        return self.__parent

    parent = property(get_parent, set_parent)

    def get_root(self):
        """
            Get the root
        """
        if self.__parent is None:
            return self
        return self.__parent.get_root()

    def add_child(self, child_ns):
        """
            Add a child to the namespace.
        """
        self.__children[child_ns.get_name()] = child_ns

    def __repr__(self):
        """
            The representation of this object
        """
        if self.parent is not None and self.parent.name != "__root__":
            return repr(self.parent) + "::" + self.name

        return self.name

    def children(self):
        """
            Get the children of this namespace
        """
        return self.__children.values()

    def to_list(self):
        """
            Convert to a list
        """
        ns_list = [self.name]
        for child in self.children():
            ns_list.extend(child.to_list())
        return ns_list

    def get_child(self, name):
        """
            Returns the child namespace with the given name or None if it does
            not exist.
        """
        if name in self.__children:
            return self.__children[name]
        return None

    def get_child_or_create(self, name):
        """
            Returns the child namespace with the given name or None if it does
            not exist.
        """
        if name in self.__children:
            return self.__children[name]
        out = Namespace(name, self)
        return out

    def get_ns_or_create(self, name):
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

    def get_ns_from_string(self, fqtn):
        """
            Get the namespace that is referenced to in the given fully qualified
            type name.

            :param fqtn: The type name
        """
        name_parts = fqtn.split("::")
        return self.get_root()._get_ns(name_parts)

    def _get_ns(self, ns_parts):
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
    def to_path(self):
        """
            Return a list with the namespace path elements in it.
        """
        if self.parent is None or self.parent.name == "__root__":
            return [self.name]
        else:
            return self.parent.to_path() + [self.name]


class CompilerException(Exception):

    def __init__(self, msg=None):
        Exception.__init__(self, msg)
        self.location = None

    def set_location(self, location):
        if self.location is None:
            self.location = location


class RuntimeException(CompilerException):

    def __init__(self, stmt, msg, root_cause_chance=10):
        CompilerException.__init__(self)
        self.stmt = None
        if stmt is not None:
            self.set_location(stmt.location)
            self.stmt = stmt
        self.msg = msg
        self.root_cause_chance = root_cause_chance

    def set_statement(self, stmt):
        self.set_location(stmt.location)
        self.stmt = stmt

    def __str__(self, *args, **kwargs):
        if self.stmt is None and self.location is None:
            return self.msg
        else:
            return "%s (reported in %s (%s))" % (self.msg, self.stmt, self.location)

    def __le__(self, other):
        return self.root_cause_chance < other.root_cause_chance


class TypeNotFoundException(RuntimeException):

    def __init__(self, type, ns):
        RuntimeException.__init__(self, stmt=None, msg="could not find type %s in namespace %s" % (type, ns))
        self.type = type
        self.ns = ns


def stringify_exception(exn: Exception):
    if isinstance(exn, CompilerException):
        return str(exn)
    return "%s: %s" % (exn.__class__.__name__, str(exn))


class WrappingRuntimeException(RuntimeException):

    def __init__(self, stmt, msg, cause):
        if stmt is None:
            if isinstance(cause, RuntimeException):
                stmt = cause.stmt
        longmsg = "%s caused by %s" % (msg, stringify_exception(cause))
        RuntimeException.__init__(self, stmt=stmt, msg=longmsg)
        self.__cause__ = cause


class AttributeException(WrappingRuntimeException):

    def __init__(self, stmt, entity, attribute, cause):
        WrappingRuntimeException.__init__(
            self, stmt=stmt, msg="Could not set attribute `%s` on instance `%s`" % (attribute, str(entity)), cause=cause)
        self.attribute = attribute
        self.entity = entity


class OptionalValueException(RuntimeException):

    def __init__(self, instance, attribute):
        RuntimeException.__init__(self, None, "Optional variable accessed that has no value (%s.%s)" % (instance, attribute))
        self.instance = instance
        self.attribute = attribute


class TypingException(RuntimeException):
    pass


class ModuleNotFoundException(RuntimeException):

    def __init__(self, name, stmt, msg=None):
        if msg is None:
            msg = "could not find module %s" % name
        RuntimeException.__init__(self, stmt, msg)
        self.name = name


class NotFoundException(RuntimeException):

    def __init__(self, stmt, name, msg=None):
        if msg is None:
            msg = "could not find value %s" % name
        RuntimeException.__init__(self, stmt, msg)
        self.name = name


class DoubleSetException(RuntimeException):

    def __init__(self, stmt, value, location, newvalue, newlocation):
        self.value = value
        self.location = location
        self.newvalue = newvalue
        self.newlocation = newlocation
        msg = ("Value set twice: old value: %s (set at (%s)), new value: %s (set at (%s))"
               % (self.value, self.location, self.newvalue, self.newlocation))
        RuntimeException.__init__(self, stmt, msg)


class DuplicateException(TypingException):

    def __init__(self, stmt, other, msg):
        TypingException.__init__(self, stmt, msg)
        self.other = other

    def __str__(self, *args, **kwargs):
        return "%s (reported at (%s)) (duplicate at (%s))" % (self.msg, self.location, self.other.location)


class CompilerError(Exception):

    pass


class MultiException(CompilerException):

    def __init__(self, others):
        self.others = others

    def __str__(self):
        return "Reported %d errors:\n\t" % len(self.others) + '\n\t'.join([str(e) for e in self.others])
