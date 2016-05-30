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

# pylint: disable-msg=W0613

from . import ReferenceStatement
from impera.ast.type import List
from impera.ast.statements import AssignStatement
from impera.execute.runtime import ExecutionUnit, WaitUnit, ResultVariable, HangUnit


class CreateList(ReferenceStatement):
    """
        Create list of values
    """

    def __init__(self, items):
        ReferenceStatement.__init__(self, items)
        self.items = items

    def execute(self, requires, resolver, queue):
        """
            Create this list
        """
        qlist = List()

        for i in range(len(self.items)):
            value = self.items[i]
            qlist.append(value.execute(requires, resolver, queue))

        return qlist

    def __repr__(self):
        return "List()"


class SetAttribute(AssignStatement):
    """
        Set an attribute of a given instance to a given value
    """

    def __init__(self, instance, attribute_name, value):
        AssignStatement.__init__(self, instance, value)
        self.instance = instance
        self.attribute_name = attribute_name
        self.value = value

    def emit(self, resolver, queue):
        reqs = self.instance.requires_emit(resolver, queue)
        WaitUnit(queue, resolver, reqs, self)

    def resume(self, requires, resolver, queue):
        var = self.instance.execute(requires, resolver, queue).get_attribute(self.attribute_name)
        reqs = self.value.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, var, reqs, self.value)


class Assign(AssignStatement):
    """
        This class represents the assignment of a value to a variable -> alias

        @param name: The name of the value
        @param value: The value that is to be assigned to the variable

        uses:          value
        provides:      variable
    """

    def __init__(self, name, value):
        AssignStatement.__init__(self, name, value)
        self.name = name
        self.value = value

    def requires(self):
        return self.value.requires()

    def emit(self, resolver, queue):
        target = resolver.lookup(self.name)
        reqs = self.value.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self.value)

    def __repr__(self):
        return "Assign(%s, %s)" % (self.name, self.value)


class IndexLookup(ReferenceStatement):
    """
        Lookup a value in a dictionary
    """

    def __init__(self, index_type, query):
        ReferenceStatement.__init__(self, [v for (k, v) in query])
        self.index_type = index_type
        self.query = query

    def normalize(self):
        ReferenceStatement.normalize(self)
        self.type = self.namespace.get_type(self.index_type)

    def requires_emit(self, resolver, queue):
        sub = ReferenceStatement.requires_emit(self, resolver, queue)
        temp = ResultVariable()
        temp.set_provider(self)
        temp.set_type(self.type)
        HangUnit(queue, resolver, sub, temp, self)
        return {self: temp}

    def resume(self, requires, resolver, queue, target):
        self.type.lookup_index([(k, v.execute(requires, resolver, queue)) for (k, v) in self.query], target)

    def execute(self, requires, resolver, queue):
        return requires[self]

    def __repr__(self):
        """
            The representation of this statement
        """
        return "%s[%s]" % (self.index_type, self.query)


class StringFormat(ReferenceStatement):
    """
        Create a new string by doing a string interpolation
    """

    def __init__(self, format_string, variables):
        ReferenceStatement.__init__(self, [k for (k, v) in variables])
        self._format_string = format_string
        self._variables = variables

    def execute(self, requires, resolver, queue):
        result_string = self._format_string
        for _var, str_id in self._variables:
            value = _var.execute(requires, resolver, queue)
            if isinstance(value, float) and (value - int(value)) == 0:
                value = int(value)

            result_string = result_string.replace(str_id, str(value))

        return result_string

    def __repr__(self):
        return "Format(%s)" % self._format_string
