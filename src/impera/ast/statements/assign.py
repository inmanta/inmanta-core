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


class CreateList(ReferenceStatement):
    """
        Create list of values
    """
    def __init__(self, items):
        ReferenceStatement.__init__(self)
        self.items = items

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = []

        for i in range(len(self.items)):
            refs.append((str(i), self.items[i]))

        return refs

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        result = state.get_result_reference()
        actions = [("set", result)]

        for i in range(len(self.items)):
            ref = state.get_ref(str(i))
            actions.append(("get", ref))

        return actions

    def evaluate(self, state, local_scope):
        """
            Create this list
        """
        qlist = list()

        for i in range(len(self.items)):
            value = self.items[i]
            var = local_scope.resolve_reference(value)
            qlist.append(var.value)

        return qlist

    def __repr__(self):
        return "List()"


class GetAttribute(ReferenceStatement):
    """
        Get the value of an attribute
    """
    def __init__(self, instance_name, attribute_name):
        ReferenceStatement.__init__(self)
        self.instance_name = instance_name
        self.attribute_name = attribute_name

    def references(self):
        """
            @see DynamicStatement#references
        """
        return [("instance", self.instance_name)]

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        instance_ref = state.get_ref("instance")
        return [("get", AttributeVariable.create(instance_ref, self.attribute_name))]

    def evaluate(self, state, local_scope):
        """
            Retrieve the attribute value
        """
        instance_ref = state.get_ref("instance")
        value = getattr(instance_ref.value, self.attribute_name)
        state.graph.add_alias(AttributeVariable.create(instance_ref, self.attribute_name), value)
        return value

    def __repr__(self):
        return "Get(%s.%s)" % (self.instance_name, self.attribute_name)


class SetAttribute(GetAttribute):
    """
        Set an attribute of a given instance to a given value

        uses:          object, value
        provides:      object.attribute, other end
        contributes:   object.attribute, other end
    """
    def __init__(self, instance_name, attribute_name, value):
        GetAttribute.__init__(self, instance_name, attribute_name)
        self.value = value

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = GetAttribute.references(self)
        refs.append(("value_ref", self.value))

        return refs

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        value_ref = state.get_ref("value_ref")
        instance_ref = state.get_ref("instance")
        local_scope = state.get_local_scope()

        return self.build_action_list(local_scope, value_ref, instance_ref, state=state)

    def build_action_list(self, local_scope, value_ref, instance_ref, instance_type=None, state=None):
        if isinstance(instance_ref.value, list):
            raise Exception("Unable to set attribute on a list.")

        if instance_type is None:
            instance_type = instance_ref.value.__class__

        if isinstance(value_ref.value, list):
            actions = []
            list_refs = []

            if hasattr(self.value, "namespace"):
                namespace = self.value.namespace
            else:
                namespace = self.namespace

            if hasattr(namespace, "to_list"):
                namespace = namespace.to_list()

            for item_ref in value_ref.value:
                if not isinstance(item_ref, Reference):
                    # a direct value
                    item_value = Variable(item_ref)
                    list_refs.append(item_value)
                    actions.extend(self._generate_actions(instance_ref, instance_type, item_value))

                else:
                    if namespace == self.namespace.to_list():
                        ref = item_ref
                    else:
                        ref = Reference(item_ref.name, namespace)

                    list_refs.append(ref)
                    actions.extend(self._generate_actions(instance_ref, instance_type, local_scope.resolve_reference(ref)))

            if state is not None:
                state.set_attribute("list_refs", list_refs)
        else:
            actions = self._generate_actions(instance_ref, instance_type, value_ref)

        return actions

    def _generate_actions(self, ref, instance_type, value_ref):
        """
            Generate actions for the given value_ref
        """
        actions = []
        definition = instance_type.__definition__
        attr = definition.get_attribute(self.attribute_name)

        if attr is None:
            raise Exception("Attribute '%s' is not defined for entity '%s'" %
                            (self.attribute_name, definition.name))

        if hasattr(attr, "end"):
            # this side
            if attr.low == 1 and attr.high == 1:
                actions.append(("set", AttributeVariable.create(ref, self.attribute_name)))
            else:
                actions.append(("add", AttributeVariable.create(ref, self.attribute_name)))

            # the other side
            if attr.end.low == 1 and attr.end.high == 1:
                actions.append(("set", AttributeVariable.create(value_ref, attr.end.name)))
            else:
                actions.append(("add", AttributeVariable.create(value_ref, attr.end.name)))
        else:
            # there is only this side
            actions.append(("set", AttributeVariable.create(ref, self.attribute_name)))

        return actions

    def __setattr(self, obj, attr_name, value):
        """
            Set the given attribute to the given value
        """
        if isinstance(value.value, DynamicProxy):
            real_value = value.value._get_instance()

            value = Variable(real_value)

        if not isinstance(value.value, Optional):
            setattr(obj, attr_name, value)

    def evaluate(self, state, local_scope):
        """
            Set the attribute
        """
        value_ref = state.get_ref("value_ref")
        instance_ref = state.get_ref("instance")

        self.set_value(state, instance_ref.value, value_ref)

    def set_value(self, state, instance, value_ref):
        if isinstance(value_ref.value, list):
            for item_ref in value_ref.value:
                if isinstance(item_ref, Reference):
                    ref = state.get_local_scope().resolve_reference(item_ref)

                else:
                    ref = Variable(item_ref)

                self.__setattr(instance, self.attribute_name, ref)

        else:
            self.__setattr(instance, self.attribute_name, value_ref)

    def __repr__(self):
        return "%s.%s = %s" % (self.instance_name, self.attribute_name, self.value)


class Assign(ReferenceStatement):
    """
        This class represents the assignment of a value to a variable -> alias

        @param name: The name of the value
        @param value: The value that is to be assigned to the variable

        uses:          value
        provides:      variable
    """
    def __init__(self, name, value):
        ReferenceStatement.__init__(self)
        self.name = name
        self.value = value

    def actions(self, state):
        """
            If ref is a literal this statement provides the required set
        """
        ref = state.get_ref("ref")

        if ref.__class__ == Variable:
            return [("set", ref)]

        return []

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        ref = state.get_ref("ref")
        local_scope.add_variable(self.name.name, ref)

    def references(self):
        """
            @see DynamicStatement#references
        """
        return [("ref", self.value), (self.name, None, "def")]

    def __repr__(self):
        return "Assign(%s, %s)" % (self.name, self.value)


class IndexLookup(ReferenceStatement):
    """
        Lookup a value in a dictionary
    """
    def __init__(self, index_type, query):
        ReferenceStatement.__init__(self)
        self.index_type = index_type
        self.query = query

    def types(self):
        """
            @see State#types
        """
        return [('index_type', self.index_type)]

    def references(self):
        """
            @see DynamicStatement#references
        """
        ref_list = []
        for name, value in self.query:
            ref_list.append((name, value))

        return ref_list

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        object_ref = state.get_result_reference()
        actions = [("set", object_ref)]

        for name, _value in self.query:
            ref = state.get_ref(name)
            actions.append(("get", ref))

        return actions

    def can_evaluate(self, state):
        """
            This statement can be evaluated when a variable of that type
            is available in the scope of this statement.
        """
        entity = state.get_type("index_type")

        query = []
        for name, _value in self.query:
            ref = state.get_ref(name)
            query.append((name, ref.value))

        if not hasattr(entity, "lookup_index"):
            raise Exception("Indexes can only be used on entities")

        instance = entity.lookup_index(query)

        if instance is not None:
            state.set_attribute("value", instance)
            return True

        return False

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement
        """
        return state.get_attribute("value")

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
        ReferenceStatement.__init__(self)
        self._format_string = format_string
        self._variables = variables

    def actions(self, state):
        """
            If ref is a literal this statement provides the required set
        """
        result = state.get_result_reference()
        actions = [("set", result)]

        for _var, str_id in self._variables:
            ref = state.get_ref(str_id)
            actions.append(("get", ref))

        return actions

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        result_string = self._format_string
        for _var, str_id in self._variables:
            ref = state.get_ref(str_id)
            value = ref.value
            if isinstance(value, float) and (value - int(value)) == 0:
                value = int(value)

            result_string = result_string.replace(str_id, str(value))

        return result_string

    def references(self):
        """
            @see DynamicStatement#references
        """
        ref_list = []
        for var, str_id in self._variables:
            ref_list.append((str_id, var))

        return ref_list

    def __repr__(self):
        return "Format(%s)" % self._format_string
