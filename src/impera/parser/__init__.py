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

import re

import antlr3
from impera.ast.constraint.expression import Operator
from impera.ast.constraint.expression import Regex as RegexOp
from impera.ast.statements.assign import SetAttribute, Assign, CreateList, IndexLookup, StringFormat
from impera.ast.statements.call import FunctionCall
from impera.ast.statements.define import DefineEntity, DefineTypeDefault, DefineImplementation, DefineTypeConstraint
from impera.ast.statements.define import DefineImplement, DefineRelation, DefineIndex
from impera.ast.statements.generator import Constructor, For
from impera.ast.statements import Literal
from impera.ast.type import TYPES, Bool, Number
from impera.ast.variables import Reference, AttributeVariable
from . import imperaLexer
from . import imperaParser
from impera.ast.blocks import BasicBlock


class action(object):
    """
        Decorator to associate a method with a compiler token
    """
    __mapping = {}

    def __init__(self, token):
        self.token = token

    def __call__(self, method):
        """
            Here the magic happens
        """
        action.__mapping[self.token] = method
        return method

    @classmethod
    def get(cls, token):
        """
            Get the action for the give token
        """
        if token.type in cls.__mapping:
            return cls.__mapping[token.type]

        return None


class Parser(object):
    """
        This class parses the a file and generates the statements
    """

    def __init__(self):
        self._stack = []
        self._current_namespace = None
        self._filename = None

    @action(imperaParser.INDEX)
    def create_index(self, node):
        """
            Create an index
        """
        type_ref = self._handle_node(node.children[0])

        attributes = [x.text for x in node.children[1].children]

        index = DefineIndex(type_ref, attributes)
        return index

    @action(imperaParser.REF)
    def create_ref(self, node):
        """
            Create a reference
        """
        to_list = [str(x.text) for x in node.children]
        # FIX: cleanup namespaces in refs

        ref = Reference(to_list[-1], to_list[:-1])
        ref.onamespace = self._current_namespace

        return ref

    @action(imperaParser.CLASS_REF)
    def create_class_ref(self, node):
        """
            Create a class reference
        """
        to_list = [str(x.text) for x in node.children[0].children]
        ref = Reference(node.children[1].text, to_list)

        if len(node.children) == 3 and node.children[2].text == "@":
            return ["@", ref]

        return ref

    @action(imperaParser.VAR_REF)
    def create_var_ref(self, node):
        """
            Create a variable reference
        """
        to_list = [str(x.text) for x in node.children[0].children]
        ref = Reference(str(node.children[1].text), to_list)
        ref.line = node.children[1].line
        ref.onamespace = self._current_namespace

        if len(node.children[2].children) > 0:
            var = ref
            for attr in node.children[2].children:
                var = AttributeVariable.create(var, str(attr.text))
                var.line = attr.line

            return var
        else:
            return ref

    @action(imperaParser.OP)
    def create_op_expression(self, node):
        """
            Create an expression that accepts two operands
        """
        if len(node.children) == 1:
            if node.children[0].text == "CALL":
                left = self._handle_node(node.children[0])
                operator = Operator.get_operator_class("==")
                return operator(left, Literal(True))
            else:
                # lift it
                node = node.children[0]

        op = str(node.children[0].text)
        left = self._handle_node(node.children[1])
        right = self._handle_node(node.children[2])

        operator = Operator.get_operator_class(op)
        expr = operator(left, right)
        return expr

    @action(imperaParser.REGEX)
    def create_regex(self, node):
        """
            Return a regular expression
        """
        value = Reference("self")  # anonymous value
        value.onamespace = self._current_namespace
        expr = RegexOp(value, str(node.text)[1:-1])
        return expr

    @action(imperaParser.DEF_TYPE)
    def create_typedef(self, node):
        """
            Create a typedef
        """
        name = str(node.children[0].text)
        base = self._handle_node(node.children[1])
        define = DefineTypeConstraint(self._current_namespace, name, base)
        define.expression = self._handle_node(node.children[2])

        return define

    @action(imperaParser.DEF_DEFAULT)
    def create_default(self, node):
        """
            Create a default constructor
        """
        name = str(node.children[0].text)
        ctor = self._handle_node(node.children[1])

        return DefineTypeDefault(self._current_namespace, name, ctor)

    @action(imperaParser.DEF_ENTITY)
    def create_entity(self, node):
        """
            Create an entity
        """
        comment = None
        if len(node.children) == 4:
            comment = self._handle_node(node.children[3])

        parents = node.children[1].children
        parents = [self._handle_node(x) for x in parents]

        interf = DefineEntity(self._current_namespace, str(node.children[0].text), comment, parents)

        attributes = node.children[2].children
        for attribute in attributes:
            type_ref = self._handle_node(attribute.children[0])
            name = str(attribute.children[1].text)

            default_value = None
            if len(attribute.children) > 2:
                default_value = self._handle_node(attribute.children[2])

            interf.add_attribute(type_ref, name, default_value)

        return interf

    @action(imperaParser.DEF_IMPLEMENT)
    def create_implements(self, node):
        """
            Define an implementation
        """
        name = self._handle_node(node.children[0])

        implementations = [self._handle_node(x) for x in node.children[1].children]

        expression = BasicBlock(self._current_namespace)

        if len(node.children) == 3:
            expression.add(self._handle_node(node.children[2]))
        else:
            expression.add(Literal(True))

        impl_definition = DefineImplement(name, implementations, expression)

        # steal the line number from one of its children because virtual tokens
        # do not get a line number
        impl_definition.line = node.children[1].line

        return impl_definition

    @action(imperaParser.DEF_IMPLEMENTATION)
    def create_implementation(self, node):
        """
            Create an implementation
        """
        impl = DefineImplementation(self._current_namespace, str(node.children[0].text))

        for stmt in node.children[1].children:
            impl.add_statement(self._handle_node(stmt))

        if len(node.children) > 2:
            impl.entity = self._handle_node(node.children[2])

        return impl

    @action(imperaParser.CALL)
    def create_func_call(self, node):
        """
            Create a function call
        """
        func_name = self._handle_node(node.children[0])
        if func_name.namespace is None and len(func_name.namespace) == 0:
            func_name.namespace = ["__plugins__"]

        if len(node.children) > 1:
            arg = node.children[1]
            if arg.type == imperaParser.LIST:
                arguments = [self._handle_node(x) for x in node.children[1].children]
            else:
                arguments = [self._handle_node(arg)]
        else:
            arguments = []

        fnc = FunctionCall(func_name, arguments)
        return fnc

    @action(imperaParser.METHOD)
    def create_method_call(self, node):
        """
            This is a chained call that has a root and one or more function.
        """
        var = self._handle_node(node.children[0])

        return_call = self._handle_node(node.children[1])
        return_call.arguments.insert(0, var)

        if len(node.children) > 2:
            calls = node.children[2:]
            for call in calls:
                fn_call = self._handle_node(call)
                fn_call.arguments.insert(0, return_call)
                return_call = fn_call

        return return_call

    @action(imperaParser.LIST)
    def create_list(self, node):
        """
            Create a list of the given list items
        """
        qlist = []

        for item in node.children:
            qlist.append(self._handle_node(item))

        stmt = CreateList(qlist)
        return stmt

    @action(imperaParser.CONSTRUCT)
    def create_constructor(self, node):
        """
            A constructor call
        """
        class_ref = self._handle_node(node.children[0])
        name = class_ref

        ctor = Constructor(name)

        if len(node.children) > 1:
            for param in node.children[1].children:
                name = str(param.children[0].text)
                value = self._handle_node(param.children[1])
                ctor.add_attribute(name, value)

        ctor.line = node.children[0].line
        return ctor

    @action(imperaParser.ASSIGN)
    def create_assign(self, node):
        """
            Create an assignment
        """
        rhs = self._handle_node(node.children[1])
        var = self._handle_node(node.children[0])

        if isinstance(var, AttributeVariable):
            stmt = SetAttribute(var.instance, var.attribute, rhs)
        else:
            stmt = Assign(var, rhs)

        stmt.line = var.line
        return stmt

    @action(imperaParser.ORPHAN)
    def handle_orphan(self, node):
        """
            This is a statement that needs  to be registered in the scope so
            it requires an assignment
        """
        return self._handle_node(node.children[0])

    @action(imperaParser.TRUE)
    def create_true(self, node):
        """
            Return true
        """
        Bool.validate(str(node.text))
        return Literal(True)

    @action(imperaParser.FALSE)
    def create_false(self, node):
        """
            Return false
        """
        Bool.validate(str(node.text))
        return Literal(False)

    @action(imperaParser.FLOAT)
    def create_float(self, node):
        """
            Return float
        """
        value = str(node.text)
        Number.validate(value)
        return Literal(Number.cast(value))

    @action(imperaParser.ANON)
    def create_anonymous_implementation(self, node):
        """
            Add an "anonymous" class definition to the specific instance of an entity.
        """
        ctor = self._handle_node(node.children[0])

        if len(node.children) == 1:
            return ctor

        # create a module for this constructor
        module_def = DefineImplementation(hex(id(ctor)))
        module_def.namespace = self._current_namespace
        for stmt in node.children[1].children:
            module_def.add_statement(self._handle_node(stmt))

        ctor.implemented = True
        self._stack.append(module_def)

        return ctor

    @action(imperaParser.HASH)
    def create_hash_lookup(self, node):
        """
            Create a lookup of a value in a hash
        """
        class_ref = self._handle_node(node.children[0])

        params = [(x.children[0].text, self._handle_node(x.children[1])) for x in node.children[1].children]
        return IndexLookup(class_ref, params)

    @action(imperaParser.DEF_RELATION)
    def create_relation(self, node):
        """
            Create a relation definition
        """
        link = str(node.children[0].text)

        def return_side(nodes):
            if len(nodes) == 3:
                return [self._handle_node(nodes[0]), str(nodes[1].text),
                        self._handle_node(nodes[2]), False]
            elif len(nodes) == 4:
                return [self._handle_node(nodes[0]), str(nodes[1].text),
                        self._handle_node(nodes[3]), True]

        left = return_side(node.children[1].children)
        right = return_side(node.children[2].children)

        rel = DefineRelation(left, right)

        if link == '--':
            pass

        elif link == '<-':
            # right requires left
            rel.requires = "<"

        elif link == '->':
            # left requires right
            rel.requires = ">"

        return rel

    @action(imperaParser.MULT)
    def create_multiplicity(self, node):
        """
            Normalize a multiplicity definition
        """
        ret = []
        for x in node.children:
            if x.type == imperaParser.NONE:
                ret.append(None)
            else:
                ret.append(int(x.text))

        if len(ret) == 1:
            ret.append(ret[0])

        return ret

    @action(imperaParser.EXPRESSION)
    def create_expression(self, node):
        """
            Create an expression that can be evaluated
        """
        if len(node.children) == 0:
            return None

        expr = self._handle_node(node.children[0])
        return BooleanExpression(expr, None)

    def create_string_format(self, format_string, variables):
        """
            Create a string interpolation statement
        """
        _vars = []
        for var_str in variables:
            var_parts = var_str[1].split(".")
            ref = Reference(var_parts[0], [])
            ref.onamespace = self._current_namespace

            if len(var_parts) > 1:
                var = ref
                for attr in var_parts[1:]:
                    var = AttributeVariable.create(var, attr)

                _vars.append((var, var_str[0]))
            else:
                _vars.append((ref, var_str[0]))

        return StringFormat(format_string, _vars)

    @action(imperaParser.STRING)
    def create_string(self, node):
        """
            Create a string
        """
        # strip quotes
        value = str(node.text)
        value = value[1:-1]

        rawstr = r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})"""
        compile_obj = re.compile(rawstr, re.MULTILINE | re.DOTALL)
        match_obj = compile_obj.findall(value)

        if len(match_obj) > 0:
            return self.create_string_format(value, match_obj)

        return Literal(value)

    @action(imperaParser.INT)
    def create_integer(self, node):
        """
            Create an integer
        """
        value = str(node.text)
        if not Number.validate(value):
            raise Exception("Value does is not a valid integer")

        return Literal(Number.cast(value))

    @action(imperaParser.STATEMENT)
    def handle_statement(self, node):
        """
            Unpack a statement
        """
        return self._handle_node(node.children[0])

    @action(imperaParser.INCLUDE)
    def create_import(self, node):
        """
            Create an import statement
        """
        imp = Import(self._handle_node(node.children[0]))
        return imp

    @action(imperaParser.LAMBDA)
    def create_lambda(self, node):
        """
            Create a lambda expression
        """
        arg = str(node.children[0])
        if node.children[1].type == imperaParser.ORPHAN:
            expr = self._handle_node(node.children[1].children[0])
            expr.register = True
        else:
            expr = self._handle_node(node.children[1])

        return BooleanExpression(expr, [arg])

    @action(imperaParser.ML_STRING)
    def create_mlstring(self, node):
        """
            Create a multiline string
        """
        # strip quotes
        value = str(node.text)
        return Literal(value[3:-3])

    @action(imperaParser.FOR)
    def create_for(self, node):
        """
            Create a for statement
        """
        loop_var = str(node.children[0])
        var = self._handle_node(node.children[1])
       
        module_def = BasicBlock(self._current_namespace)
        module_def.line = node.line
        module_def.filename = self._filename
        for stmt in node.children[2].children:
            module_def.add(self._handle_node(stmt))

        for_stmt = For(var, loop_var, module_def)
        
        return for_stmt

    def _handle_node(self, node):
        """
            Handle the given node
        """
        create_func = action.get(node)
        if create_func is None:
            raise Exception("Unable to handle statement %s (%d)" % (node, node.type))

        ast_node = create_func(self, node)
        if hasattr(ast_node, "namespace") and ast_node.namespace is None:
            ast_node.namespace = self._current_namespace

        if hasattr(ast_node, "line") and ast_node.line <= 0:
            ast_node.line = node.line

        if hasattr(ast_node, "filename"):
            ast_node.filename = self._filename

        return ast_node

    def parse(self, namespace, filename=None, content=None):
        self._stack = []
        self._current_namespace = namespace
        self._filename = filename

        if content is None:
            with open(filename, "r") as fd:
                content = fd.read()

        char_stream = antlr3.ANTLRStringStream(content)

        lexer = imperaLexer.imperaLexer(char_stream)
        tokens = antlr3.CommonTokenStream(lexer)
        parser = imperaParser.imperaParser(tokens)

        main_token = parser.main()

        statements = []
        if main_token.tree is not None:
            for node in main_token.tree.children:
                statements.append(self._handle_node(node))

                if len(self._stack) > 0:
                    statements.extend(self._stack)
                    self._stack = []

        self._current_namespace = None

        # self.cache(filename, statements)
        return statements
