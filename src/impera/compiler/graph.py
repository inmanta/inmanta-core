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

    Contect: bart@impera.io
"""

# pylint: disable-msg=R0904,R0201,W0612,C0103

from impera.ast.variables import AttributeVariable, Variable

import logging

LOGGER = logging.getLogger(__name__)


class ObjectActions(object):
    """
        This class represents actions on an object
    """
    def __init__(self, obj):
        self.object = obj
        self.aliases = []

        self._add = set()
        self._get = set()
        self._set = set()

    def add_alias(self, obj):
        """
            An alias
        """
        self.aliases.append(obj)

    def add_operation(self, operation, statement):
        """
            Add an operation
        """
        if False:
            print("%s on |%s| by |%s| (%s)" % (operation, self.object, statement, self))
            print("\t%s" % self.aliases)
            print("\t%s %s" % (self.object.__class__, hex(id(self.object))))

        if operation == "add":
            for get in self._get:
                if get.evaluated:
                    raise Exception("%s can not add an other value to %s" % (statement, self.object))

            self._add.add(statement)

        elif operation == "get":
            self._get.add(statement)

        elif operation == "set":
            self._set.add(statement)

        if len(self._add) > 0 and len(self._set) > 0:
            raise Exception("Impossible to add and set to the same object")

    def can_evaluate(self, statement):
        """
            Can the given statement be evaluated based on the operations it
            performs on the object
        """
        if self.object.__class__.__name__ == "Variable":
            return True

        if self.does_add_or_set(statement):
            return True

        # there should be at least one set or add
        if len(self._add) == 0 and len(self._set) == 0:
            # ## if a value is available and it is not a statement that can be
            # ## contributed to, the evaluation may pass
            # ##if isinstance(self.object, (EntityType, list, tuple)):
            # # -> solved by assign providing "set" for literals
            LOGGER.debug("Detected a value that is read but is not set (object: %s)" % self.object)
            return False

        # it is a get operation, it can only be executed of the statement in
        # the other operation sets are finished
        for stmt in self._add:
            if not stmt.evaluated:
                return False

        for stmt in self._set:
            if not stmt.evaluated:
                return False

        return True

    def does_read(self, statement):
        """
            Does the given statement inspect the state of this object?
        """
        if statement in self._get:
            return True

        return False

    def is_list(self):
        """
            Returns true if the "object" is a list. For now an object is a
            list if an add operations exists.
        """
        return len(self._add) > 0

    def does_add_or_set(self, statement):
        """
            Does the given statement an add or a set on this object?
        """
        return statement in self._add or statement in self._set

    def all_get_statements(self):
        """
            Get a set of "get" statements
        """
        return self._get


class Graph(object):
    """
        Functions that add entities of the execution to a graph
    """
    def __init__(self):
        self.root_scope = None

        self._objects = {}
        self._statements = {}
        self._refs = {}
        self._key_hash = {}

        self._statement_list = []

        self._to_compare = {}

    def add_namespace(self, namespace, parent=None):
        """
            Add a new namespace to the self with an optional parent
        """

    def add_statement(self, statement):
        """
            Add a statement that is defined a namespace
        """
        self._statement_list.append(statement)

    def get_statements(self):
        """
            Return a list of all statement in the graph
        """
        return self._statement_list

    def add_alias(self, obj, alias):
        """
            Add an alias for an object
        """
        key = self.find_object(obj)
        if key is None:
            raise Exception("Object does not exist, unable to add alias")

        action = self._objects[key]
        action.add_alias(alias)

        self.add_key(alias, action)

    def add_key(self, key, action):
        """
            Add a key and associated action
        """
        self._objects[key] = action

        compare_key = key.compare_key()
        if compare_key not in self._key_hash:
            self._key_hash[compare_key] = []

        self._key_hash[compare_key].append(key)

    def find_object(self, obj):
        """
            Find the object that matches this one
        """
        if obj in self._objects:
            return obj

        # do a compare
        compare_key = obj.compare_key()
        if compare_key not in self._key_hash:
            return None

        for key in self._key_hash[compare_key]:
            if key == obj:
                return key

        return None

    def find_object_action(self, obj):
        """
            Search if the same object already exists
        """
        key = self.find_object(obj)
        if key is not None:
            oa = self._objects[key]
            self.add_key(obj, oa)
            return oa

        oa = ObjectActions(obj)
        # self.add_node(oa, type = "object", label = str(obj))
        self.add_key(obj, oa)
        return oa

    def _pre_process_action(self, actions, op, obj):
        """
            Do some preprocessing on actions
        """
        if hasattr(obj, "instance") and hasattr(obj.instance, "instance"):
            # unpack nested attributes
            instance = Variable(obj.instance.value)
            actions.append((op, AttributeVariable.create(instance, obj.attribute)))
        else:
            actions.append((op, obj))

    def add_actions(self, statement, actions):
        """
            Add actions
        """
        new_list = []
        for op, obj in actions:
            self._pre_process_action(new_list, op, obj)

        for action in new_list:
            self.add_action(statement, action)
            continue
            if action[1].can_compare():
                self.add_action(statement, action)
            else:
                self._to_compare[action] = statement

    def add_action(self, statement, action):
        """
            Add an action
        """
        obj_action = self.find_object_action(action[1])
        obj_action.add_operation(action[0], statement)

        if statement not in self._statements:
            self._statements[statement] = []

        self._statements[statement].append(obj_action)

    def process_un_compared(self):
        """
            Compare uncompared objects
        """
        to_remove = []

        for obj, statement in self._to_compare.items():
            if obj[1].get_version() > 0:
                to_remove.append(obj)
                self.add_action(statement, obj)

        for obj in to_remove:
            del self._to_compare[obj]

    def can_evaluate(self, statement):
        """
            Can the given statement evaluate?
        """
        if statement not in self._statements:
            return True

        for action in self._statements[statement]:
            if not action.can_evaluate(statement):
                return False

        return True

    def is_write_only(self, statement):
        """
            This method returns true if the given statement only changes state
            and does not read any state.
        """
        if statement not in self._statements:
            return True

        for action in self._statements[statement]:
            if action.does_read(statement):
                return False

        return True

    def uses_list(self, statement):
        """
            This method returns true if the given statement uses a value (get)
            that is a list (there are add actions or we know it is a list)
        """
        if statement not in self._statements:
            return False

        oa_list = self._statements[statement]

        for oa in oa_list:
            if oa.is_list() and oa.does_read(statement):
                return True

        return False
