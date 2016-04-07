"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

# pylint: disable-msg=W0613

from . import ReferenceStatement
from impera.ast.variables import Variable, AttributeVariable, Reference
from impera.execute.proxy import DynamicProxy
from impera.execute.util import Optional
from impera.ast.type import List
from impera.ast.statements import Statement, AssignStatement, ExpressionStatement
from impera.util import memoize
from impera.execute.runtime import ExecutionUnit, WaitUnit, ResultVariable, HangUnit
import impera.execute.scheduler
import random


class CreateList(ExpressionStatement):
    """
        Create list of values
    """

    def __init__(self, items):
        ExpressionStatement.__init__(self)
        self.items = items

    def normalize(self, resolver):
        for i in self.items:
            i.normalize(resolver)

    def requires(self):
        out = [req for i in self.items for req in i.requires()]
        return out

    def requires_emit(self, resolver, queue):
        out = {rk: rv for i in self.items for (rk, rv) in i.requires_emit(resolver, queue).items()}
        return out

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

        uses:          object, value
        provides:      object.attribute, other end
        contributes:   object.attribute, other end
    """

    def __init__(self, instance_name, attribute_name, value):
        AssignStatement.__init__(self, instance_name, value)
        if not isinstance(instance_name, Reference):
            raise Exception("assumed Reference")
        self.instance_name = instance_name
        self.attribute_name = attribute_name
        self.value = value
        self.token = random.randint(0, 2147483647)

    def normalize(self, resolver):
        self.value.normalize(resolver)

    def requires(self):
        out = self.value.requires()
        out.extend(self.instance_name.requires())
        return out

    def emit(self, resolver, queue):
        target = resolver.lookup(self.instance_name.name)
        WaitUnit(queue, resolver, target, self)

    def resume(self, target, resolver, queue):
        var = target.get_value().get_attribute(self.attribute_name)
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
        target = resolver.lookup(self.name.full_name)
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

    def normalize(self, resolver):
        ReferenceStatement.normalize(self, resolver)
        self.type = resolver.get_type(self.index_type.full_name)

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
