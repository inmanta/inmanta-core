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

import inspect
import subprocess
import os

from inmanta.execute.proxy import DynamicProxy
from inmanta.execute.util import Unknown
from inmanta.ast import Namespace, CompilerException, TypeNotFoundException
from inmanta.execute.runtime import ExecutionUnit


class Context(object):
    """
        An instance of this class is used to pass context to the plugin
    """
    __client = None

    @classmethod
    def __get_client(cls):
        if cls.__client is None:
            from inmanta import protocol
            cls.__client = protocol.Client("compiler")
        return cls.__client

    def __init__(self, resolver, queue, owner, result):
        self.resolver = resolver
        self.queue = queue
        self.owner = owner
        self.result = result
        self.compiler = queue.get_compiler()

    def emit_expression(self, stmt):
        """
            Add a new statement
        """
        self.owner.copy_location(stmt)
        stmt.normalize(self.resolver)
        reqs = stmt.requires_emit(self.resolver, self.queue)
        ExecutionUnit(self.queue, self.resolver, self.result, reqs, stmt, provides=False)

    def get_resolver(self):
        return self.resolver

    def get_type(self, name):
        try:
            return self.queue.get_types()[name]
        except KeyError:
            raise TypeNotFoundException(name, self.owner.namespace)

    def get_queue_scheduler(self):
        return self.queue

    def get_compiler(self):
        return self.queue.get_compiler()

    def get_data_dir(self):
        """
            Get the path to the data dir (and create if it does not exist yet
        """
        data_dir = os.path.join("data", self.owner.function.namespace.get_full_name())

        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        return data_dir

    def get_client(self):
        return self.__class__.__get_client()

    def run_sync(self, function):
        from tornado.ioloop import IOLoop, TimeoutError
        try:
            return IOLoop.current().run_sync(function, 5)
        except TimeoutError:
            raise ConnectionRefusedError()


class PluginMeta(type):
    """
        A metaclass that registers subclasses in the parent class.
    """
    def __new__(cls, name, bases, dct):
        subclass = type.__new__(cls, name, bases, dct)
        if hasattr(subclass, "__function_name__"):
            cls.add_function(subclass)
        return subclass

    __functions = {}

    @classmethod
    def add_function(cls, plugin_class):
        """
            Add a function plugin class
        """
        name = plugin_class.__function_name__
        ns_parts = str(plugin_class.__module__).split(".")
        ns_parts.append(name)
        if ns_parts[0] != "inmanta_plugins":
            raise Exception(
                "All plugin modules should be loaded in the inmanta_plugins package")

        name = "::".join(ns_parts[1:])
        cls.__functions[name] = plugin_class

    @classmethod
    def get_functions(cls):
        """
            Get all functions that are registered
        """
        return cls.__functions

    @classmethod
    def clear(cls):
        cls.__functions = {}


class Plugin(object, metaclass=PluginMeta):
    """
        This class models a plugin that can be called from the language.
    """

    def __init__(self, namespace: Namespace):
        self.ns = namespace

        self._context = -1
        self._return = None

        if hasattr(self.__class__, "__function__"):
            self.arguments = self._load_signature(self.__class__.__function__)
        else:
            self.arguments = []

        self.new_statement = None

    def normalize(self):
        self.resolver = self.namespace
        self.argtypes = [self.to_type(x[1], self.namespace) for x in self.arguments]
        self.returntype = self.to_type(self._return, self.namespace)

        # pass

    def _load_signature(self, function):
        """
            Load the signature from the given python function
        """
        arg_spec = inspect.getfullargspec(function)
        if arg_spec.defaults is not None:
            default_start = len(arg_spec.args) - len(arg_spec.defaults)
        else:
            default_start = None

        arguments = []
        for i in range(len(arg_spec.args)):
            arg = arg_spec.args[i]

            if arg not in arg_spec.annotations:
                raise Exception(
                    "All arguments of plugin '%s' should be annotated" % function.__name__)

            spec_type = arg_spec.annotations[arg]
            if spec_type == Context:
                self._context = i
            else:
                if default_start is not None and default_start <= i:
                    default_value = arg_spec.defaults[default_start - i]

                    arguments.append((arg, spec_type, default_value))
                else:
                    arguments.append((arg, spec_type))

        if "return" in arg_spec.annotations:
            self._return = arg_spec.annotations["return"]

        return arguments

    def add_argument(self, arg_type, arg_type_name, arg_name, optional=False):
        """
            Add an argument at the next position, of given type.
        """
        self.arguments.append((arg_type, arg_type_name, arg_name, optional))

    def get_signature(self):
        """
            Generate the signature of this plugin
        """
        arg_list = []
        for arg in self.arguments:
            if len(arg) == 3:
                arg_list.append("%s: %s=%s" % (arg[0], arg[1], str(arg[2])))

            elif len(arg) == 2:
                arg_list.append("%s: %s" % (arg[0], arg[1]))

            else:
                arg_list.append(arg[0])

        args = ", ".join(arg_list)

        return "%s(%s)" % (self.__class__.__function_name__, args)

    def to_type(self, arg_type, resolver):
        """
            Convert a string representation of a type to a type
        """
        if arg_type is None:
            return None

        if not isinstance(arg_type, str):
            raise CompilerException("bad annotation in plugin %s::%s, expected str but got %s (%s)" %
                                    (self.ns, self.__class__.__function_name__, type(arg_type), arg_type))

        if arg_type == "any":
            return None

        if arg_type == "list":
            return list

        if arg_type == "expression":
            return None

        return resolver.get_type(arg_type)

    def _is_instance(self, value, arg_type):
        """
            Check if value is of arg_type
        """
        if arg_type is None:
            return True

        if hasattr(arg_type, "validate"):
            return arg_type.validate(value)

        return isinstance(value, arg_type)

    def check_args(self, args):
        """
            Check if the arguments of the call match the function signature
        """
        max_arg = len(self.arguments)
        required = len([x for x in self.arguments if len(x) == 2])

        if len(args) < required or len(args) > max_arg:
            raise Exception("Incorrect number of arguments for %s. Expected at least %d, got %d" %
                            (self.get_signature(), required, len(args)))

        for i in range(len(args)):
            if isinstance(args[i], Unknown):
                return False

            if self.arguments[i][0] is not None and not self._is_instance(args[i], self.argtypes[i]):
                raise Exception(("Invalid type for argument %d of '%s', it should be " +
                                 "%s and %s given.") % (i + 1, self.__class__.__function_name__,
                                                        self.arguments[i][1], args[i].__class__.__name__))
        return True

    def emit_statement(self):
        """
            This method is called to determine if the plugin call pushes a new
            statement
        """
        return self.new_statement

    def get_variable(self, name, scope):
        """
            Get the given variable
        """
        return DynamicProxy.return_value(self._scope.get_variable(name, scope).value)

    def check_requirements(self):
        """
            Check if the plug-in has all it requires
        """
        if "bin" in self.opts and self.opts["bin"] is not None:
            for _bin in self.opts["bin"]:
                p = subprocess.Popen(
                    ["bash", "-c", "type -p %s" % _bin], stdout=subprocess.PIPE)
                result = p.communicate()

                if len(result[0]) == 0:
                    print("%s requires %s to be available in $PATH" %
                          (self.__function_name__, _bin))

    def __call__(self, *args):
        """
            The function call itself
        """

        self.check_requirements()
        new_args = []
        for arg in args:
            if isinstance(arg, Context):
                new_args.append(arg)
            else:
                new_args.append(DynamicProxy.return_value(arg))

        value = self.call(*new_args)

        if isinstance(value, DynamicProxy):
            value = value._get_instance()

        if self.returntype is not None and not isinstance(value, Unknown):
            valid = False
            exception = None

            try:
                valid = (
                    value is None or self._is_instance(value, self.returntype))
            except Exception as exp:
                exception = exp

            if not valid:
                msg = ""
                if exception is not None:
                    msg = "\n\tException details: " + str(exception)

                raise Exception("Plugin %s should return value of type %s ('%s' was returned) %s" %
                                (self.__class__.__function_name__, self.returntype, value, msg))

        # print(value)
        return value


def plugin(function=None, commands=None, emits_statements=False):  # noqa: H801
    """
        Python 3 decorator to register functions with inmanta
    """
    def curry_name(name=None, commands=None, emits_statements=False):
        """
            Function to curry the name of the function
        """
        def call(fnc):
            """
                Create class to register the function and return the function itself
            """

            def wrapper(self, *args):
                """
                    Python will bind the function as method into the class
                """
                return fnc(*args)

            nonlocal name, commands, emits_statements

            if name is None:
                name = fnc.__name__

            dictionary = {}
            dictionary["__module__"] = fnc.__module__
            dictionary["__function_name__"] = name
            dictionary["opts"] = {
                "bin": commands, "emits_statements": emits_statements}
            dictionary["call"] = wrapper
            dictionary["__function__"] = fnc

            bases = (Plugin,)
            PluginMeta.__new__(PluginMeta, name, bases, dictionary)

            return fnc

        return call

    if function is None:
        return curry_name(commands=commands, emits_statements=emits_statements)

    elif isinstance(function, str):
        return curry_name(function, commands=commands, emits_statements=emits_statements)

    elif function is not None:
        fnc = curry_name(commands=commands, emits_statements=emits_statements)
        return fnc(function)
