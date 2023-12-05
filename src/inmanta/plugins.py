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
import asyncio
import collections.abc
import inspect
import os
import subprocess
import warnings
from collections import abc
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, Optional, Type, TypeVar

import inmanta.ast.type as inmanta_type
from inmanta import const, protocol, util
from inmanta.ast import (
    CompilerException,
    LocatableString,
    Location,
    Namespace,
    Range,
    RuntimeException,
    TypeNotFoundException,
    WithComment,
)
from inmanta.ast.type import NamedType
from inmanta.config import Config
from inmanta.execute.proxy import DynamicProxy
from inmanta.execute.runtime import QueueScheduler, Resolver, ResultVariable
from inmanta.execute.util import NoneValue, Unknown
from inmanta.stable_api import stable_api
from inmanta.warnings import InmantaWarning

T = TypeVar("T")

if TYPE_CHECKING:
    from inmanta.ast.statements import DynamicStatement
    from inmanta.ast.statements.call import FunctionCall
    from inmanta.compiler import Compiler


class PluginDeprecationWarning(InmantaWarning):
    pass


@stable_api
class Context:
    """
    An instance of this class is used to pass context to the plugin
    """

    __client: Optional["protocol.Client"] = None
    __sync_client = None

    @classmethod
    def __get_client(cls) -> "protocol.Client":
        if cls.__client is None:
            cls.__client = protocol.Client("compiler")
        return cls.__client

    def __init__(
        self, resolver: Resolver, queue: QueueScheduler, owner: "FunctionCall", plugin: "Plugin", result: ResultVariable
    ) -> None:
        self.resolver = resolver
        self.queue = queue
        self.owner = owner
        self.plugin = plugin
        self.result = result
        self.compiler = queue.get_compiler()

    def get_resolver(self) -> Resolver:
        return self.resolver

    def get_type(self, name: LocatableString) -> inmanta_type.Type:
        """
        Get a type from the configuration model.
        """
        try:
            return self.queue.get_types()[str(name)]
        except KeyError:
            raise TypeNotFoundException(name, self.owner.namespace)

    def get_queue_scheduler(self) -> QueueScheduler:
        return self.queue

    def get_environment_id(self) -> str:
        env = str(Config.get("config", "environment", None))

        if env is None:
            raise Exception("The environment of the model should be configured in config>environment")

        return env

    def get_compiler(self) -> "Compiler":
        return self.queue.get_compiler()

    def get_data_dir(self) -> str:
        """
        Get the path to the data dir (and create if it does not exist yet
        """
        data_dir = os.path.join("data", self.plugin.namespace.get_full_name())

        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        return data_dir

    def get_client(self) -> "protocol.Client":
        return self.__class__.__get_client()

    def get_sync_client(self) -> "protocol.SyncClient":
        if self.__class__.__sync_client is None:
            self.__class__.__sync_client = protocol.SyncClient("compiler")
        return self.__class__.__sync_client

    def run_sync(self, function: Callable[[], abc.Awaitable[T]], timeout: int = 5) -> T:
        """
        Execute the async function and return its result. This method uses this thread's current (not running) event loop if
        there is one, otherwise it creates a new one. The main use for this function is to use the inmanta internal rpc to
        communicate with the server.

        :param function: The async function to execute. This function should return a yieldable object.
        :param timeout: A timeout for the async function.
        :return: The result of the async call.
        :raises ConnectionRefusedError: When the function timeouts this exception is raised.
        """
        with_timeout: abc.Awaitable[T] = asyncio.wait_for(function(), timeout)
        try:
            return util.ensure_event_loop().run_until_complete(with_timeout)
        except TimeoutError:
            raise ConnectionRefusedError()


@stable_api
class PluginMeta(type):
    """
    A metaclass that keeps track of concrete plugin subclasses. This class is responsible for all plugin registration.
    """

    def __new__(cls, name: str, bases: tuple[type, ...], dct: dict[str, object]) -> type:
        subclass = type.__new__(cls, name, bases, dct)
        if hasattr(subclass, "__function_name__"):
            cls.add_function(subclass)
        return subclass

    __functions: dict[str, type["Plugin"]] = {}

    @classmethod
    def add_function(cls, plugin_class: type["Plugin"]) -> None:
        """
        Add a function plugin class
        """
        cls.__functions[plugin_class.__fq_plugin_name__] = plugin_class

    @classmethod
    def get_functions(cls) -> dict[str, "Type[Plugin]"]:
        """
        Get all functions that are registered
        """
        return dict(cls.__functions)

    @classmethod
    def clear(cls, inmanta_module: Optional[str] = None) -> None:
        """
        Clears registered plugin functions.

        :param inmanta_module: Clear plugin functions for a specific inmanta module. If omitted, clears all registered plugin
            functions.
        """
        if inmanta_module is not None:
            top_level: str = f"{const.PLUGINS_PACKAGE}.{inmanta_module}"
            cls.__functions = {
                fq_name: plugin_class
                for fq_name, plugin_class in cls.__functions.items()
                if plugin_class.__module__ != top_level and not plugin_class.__module__.startswith(f"{top_level}.")
            }
        else:
            cls.__functions = {}


class Null(inmanta_type.Type):
    """
    This custom type is used for the validation of plugins which only
    accept null as an argument or return value.
    """

    def validate(self, value: Optional[object]) -> bool:
        if isinstance(value, NoneValue):
            return True

        raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

    def type_string(self) -> str:
        return "null"

    def type_string_internal(self) -> str:
        return self.type_string()


# Define some types which are used in the context of plugins.
PLUGIN_TYPES = {
    "any": inmanta_type.Type(),  # Any value will pass validation
    "expression": inmanta_type.Type(),  # Any value will pass validation
    "null": Null(),  # Only NoneValue will pass validation
    None: inmanta_type.Type(),  # In iso6, a None return type accepts any value, from iso7+ it expects a None value.
}


class PluginValue:
    """
    Base class for all values that go in and out of a plugin: arguments and return value.

    The class has two class attributes that should be set in the different subclasses:
    :attr VALUE_TYPE: The type of io value it is, argument or return value
    :attr VALUE_NAME: The name of the io value, the argument name or "return value"

    These attributes are only used for better error reporting.
    """

    VALUE_TYPE: str = ""
    VALUE_NAME: str = ""

    def __init__(self, type_expression: object) -> None:
        self.type_expression = type_expression
        self._resolved_type: Optional[inmanta_type.Type] = None

    @property
    def resolved_type(self) -> inmanta_type.Type:
        """
        Get the resolved type of this plugin io.  The resolved type can only be accessed
        once this object has been normalized (which happens during the plugin normalization).
        """
        if self._resolved_type is None:
            raise CompilerException(
                f"{type(self).__name__} {self.VALUE_NAME} ({repr(self.type_expression)}) has not been normalized, "
                "its resolved type can't be accessed."
            )
        return self._resolved_type

    def resolve_type(self, plugin: "Plugin", resolver: Namespace) -> inmanta_type.Type:
        """
        Convert the string representation of this argument's type to a type.
        If no type annotation is present or if the type annotation allows any type to be passed
        as argument, then None is returned.

        :param plugin: The plugin that this argument is part of.
        :param resolver: The namespace that can be used to resolve the type annotation of this
            argument.
        """
        if self.type_expression in PLUGIN_TYPES:
            self._resolved_type = PLUGIN_TYPES[self.type_expression]
            return self._resolved_type

        if not isinstance(self.type_expression, str):
            raise CompilerException(
                "Bad annotation in plugin %s for %s, expected str but got %s (%s)"
                % (plugin.get_full_name(), self.VALUE_NAME, type(self.type_expression).__name__, self.type_expression)
            )

        plugin_line: Range = Range(plugin.location.file, plugin.location.lnr, 1, plugin.location.lnr + 1, 1)
        locatable_type: LocatableString = LocatableString(self.type_expression, plugin_line, 0, resolver)
        self._resolved_type = inmanta_type.resolve_type(locatable_type, resolver)
        return self._resolved_type

    def validate(self, value: object) -> bool:
        """
        Validate that the given value can be passed to this argument.  Returns True if the value is known
        and valid, False if the value is unknown, and raises a ValueError is the value is not of the
        expected type.

        :param value: The value to validate
        """
        if isinstance(value, Unknown):
            # Value is not known, it can not be validated
            return False

        # Validate the value, use custom validate method of the type if it exists
        return self.resolved_type.validate(value)


class PluginArgument(PluginValue):
    """
    Represents the argument of an Inmanta plugin.
    """

    VALUE_TYPE = "argument value"

    # Marker used to indicate that a plugin argument has no default value.
    NO_DEFAULT_VALUE_SET = object()

    def __init__(
        self,
        arg_name: str,
        arg_type: object,
        arg_position: Optional[int] = None,
        default_value: object = NO_DEFAULT_VALUE_SET,
    ) -> None:
        super().__init__(arg_type)
        self.arg_name = arg_name
        self.arg_type = self.type_expression
        self.arg_position = arg_position
        self.is_kw_only_argument = arg_position is None
        self._default_value = default_value
        self.VALUE_NAME = self.arg_name

    @property
    def default_value(self) -> Optional[object]:
        if not self.has_default_value():
            raise Exception("PluginArgument doesn't have a default value")
        return self._default_value

    def has_default_value(self) -> bool:
        """
        Return True iff this plugin argument has a default value set.
        """
        return self._default_value is not self.NO_DEFAULT_VALUE_SET

    def __str__(self) -> str:
        if self.has_default_value():
            return "%s: %s = %s" % (self.arg_name, repr(self.arg_type), str(self.default_value))
        else:
            return "%s: %s" % (self.arg_name, repr(self.arg_type))


class PluginReturn(PluginValue):
    """
    Represent the return type of an Inmanta plugin.
    """

    VALUE_TYPE = "returned value"
    VALUE_NAME = "return value"


class Plugin(NamedType, WithComment, metaclass=PluginMeta):
    """
    This class models a plugin that can be called from the language.
    """

    deprecated: bool = False
    replaced_by: Optional[str] = None

    def __init__(self, namespace: Namespace) -> None:
        self.ns = namespace
        self.namespace = namespace

        # The index of the Context attribute.
        self._context: int = -1

        # Load the signature and build all the PluginArgument objects corresponding to it
        self.args: list[PluginArgument] = list()
        self.var_args: Optional[PluginArgument] = None
        self.kwargs: dict[str, PluginArgument] = dict()
        self.var_kwargs: Optional[PluginArgument] = None
        self.all_args: dict[str, PluginArgument] = dict()
        self.return_type: PluginReturn = PluginReturn("null")
        if hasattr(self.__class__, "__function__"):
            self._load_signature(self.__class__.__function__)

        self.new_statement = None

        filename: Optional[str] = inspect.getsourcefile(self.__class__.__function__)
        assert filename is not None
        try:
            line: int = inspect.getsourcelines(self.__class__.__function__)[1] + 1
        except OSError:
            # In case of bytecompiled code there is no source line
            line = 1

        if self.__class__.__function__.__doc__:
            self.comment = self.__class__.__function__.__doc__

        self.location = Location(filename, line)

    def normalize(self) -> None:
        self.resolver = self.namespace

        # Resolve all the types that we expect to receive as input of our plugin
        for arg in self.all_args.values():
            arg.resolve_type(self, self.resolver)
        if self.var_args is not None:
            self.var_args.resolve_type(self, self.resolver)
        if self.var_kwargs is not None:
            self.var_kwargs.resolve_type(self, self.resolver)

        self.return_type.resolve_type(self, self.resolver)

    def _load_signature(self, function: Callable[..., object]) -> None:
        """
        Load the signature from the given python function, and update the relevant attributes
        of this object.
        """
        # Reset relevant object attributes
        self.args = list()
        self.var_args = None
        self.kwargs = dict()
        self.var_kwargs = None
        self.all_args = dict()

        # Inspect the function to get its arguments and annotations
        arg_spec = inspect.getfullargspec(function)

        # Load the return annotation.  If not return annotation is provided, the returned
        # type is "any".
        if "return" not in arg_spec.annotations:
            self.return_type = PluginReturn("any")
        else:
            self.return_type = PluginReturn(arg_spec.annotations["return"])

        def get_annotation(arg: str) -> object:
            """
            Get the annotation for a specific argument, and if none exists, raise an exception
            """
            if arg not in arg_spec.annotations:
                raise CompilerException(
                    f"All arguments of plugin {repr(self.get_full_name())} should be annotated: "
                    f"{repr(arg)} has no annotation"
                )

            return arg_spec.annotations[arg]

        if arg_spec.varargs is not None:
            # We have a catch-all positional arguments
            self.var_args = PluginArgument(
                arg_name=arg_spec.varargs,
                arg_type=get_annotation(arg_spec.varargs),
            )

        if arg_spec.varkw is not None:
            # We have a catch-all keyword arguments
            self.var_kwargs = PluginArgument(
                arg_name=arg_spec.varkw,
                arg_type=get_annotation(arg_spec.varkw),
            )

        # Save all positional arguments
        defaults_start_at = len(arg_spec.args) - len(arg_spec.defaults or [])
        for position, arg in enumerate(arg_spec.args):
            annotation = get_annotation(arg)
            if annotation == Context:
                self._context = position
                continue

            # Resolve the default before changing the position because
            # of the context presence, as the defaults list definitely
            # takes into account the context presence.
            default = (
                arg_spec.defaults[position - defaults_start_at]
                if position >= defaults_start_at
                else PluginArgument.NO_DEFAULT_VALUE_SET
            )

            if self._context != -1:
                # If we have a context argument, the position index
                # needs to be adapted as this context object can never be passed
                # from the model.
                position -= 1

            argument = PluginArgument(
                arg_name=arg,
                arg_type=annotation,
                arg_position=position,
                default_value=default,
            )

            # This is a positional argument, we register it now
            self.args.append(argument)
            self.all_args[arg] = argument

        # Save all key-word arguments
        for arg in arg_spec.kwonlyargs:
            argument = PluginArgument(
                arg_name=arg,
                arg_type=get_annotation(arg),
                default_value=(
                    arg_spec.kwonlydefaults[arg]
                    if arg_spec.kwonlydefaults is not None and arg in arg_spec.kwonlydefaults
                    else PluginArgument.NO_DEFAULT_VALUE_SET
                ),
            )
            self.kwargs[arg] = argument
            self.all_args[arg] = argument

    def get_signature(self) -> str:
        """
        Generate the signature of this plugin.  The signature is a string representing the the function
        as it can be called as a plugin in the model.
        """
        # Start the list with all positional arguments
        arg_list = [str(arg) for arg in self.args]

        # Filter all positional arguments out of the kwargs list
        kwargs = [str(arg) for _, arg in self.kwargs.items() if arg.is_kw_only_argument]

        if self.var_args is not None:
            arg_list.append("*" + str(self.var_args))
        elif kwargs:
            # For keyword only arguments, we need a marker if we don't have a catch-all
            # positional argument
            arg_list.append("*")

        # Add all keyword-only arguments to the list
        arg_list.extend(kwargs)

        if self.var_kwargs is not None:
            arg_list.append("**" + str(self.var_kwargs))

        # Join all arguments, separated by a comma
        args_string = ", ".join(arg_list)

        if self.return_type.type_expression is None:
            return "%s(%s)" % (self.__class__.__function_name__, args_string)
        return "%s(%s) -> %s" % (self.__class__.__function_name__, args_string, repr(self.return_type.type_expression))

    def get_arg(self, position: int) -> PluginArgument:
        """
        Get the argument at a given position, raise a RuntimeException if it doesn't exists..
        If a catch-all positional argument is defined, it will never raise a RuntimeException.

        :param position: The position of the argument (excluding any Context argument)
        """
        if position < len(self.args):
            return self.args[position]
        elif self.var_args is not None:
            return self.var_args
        else:
            raise RuntimeException(None, f"{self.get_full_name()}() got an unexpected positional argument: {position}")

    def get_kwarg(self, name: str) -> PluginArgument:
        """
        Get the argument with a given name, raise a RuntimeException if it doesn't exists.
        If a catch-all keyword argument is defined, it will never raise a RuntimeException.

        We currently don't support positional-only parameters, so we can simply look for any
        parameter named this way, positional or not.

        :param name: The name of the argument
        """
        if name in self.all_args:
            return self.all_args[name]
        elif self.var_kwargs is not None:
            return self.var_kwargs
        else:
            # Trying to provide a keyword argument which doesn't exist
            # The exception raised here tries to match as closely as possible what python
            # would have raised as exception
            raise RuntimeException(None, f"{self.get_full_name()}() got an unexpected keyword argument: '{name}'")

    def report_missing_arguments(
        self, missing_args: collections.abc.Sequence[str], args_sort: Literal["positional", "keyword-only"]
    ) -> None:
        """
        Helper method to raise an exception specifying that the given arguments are missing.  We try here
        to stick as much as possible to the error that python would have raised, only changing its type.

        The type of the exception raised is RuntimeException.

        If the list of missing_args is empty, we don't report any exception.

        :param missing_args: The missing arguments we should report
        :param args_sort: The sort of argument we are checking (positional or kw)
        """
        func = self.get_full_name()
        if len(missing_args) == 1:
            # The exception raised here tries to match as closely as possible what python
            # would have raised as exception
            raise RuntimeException(None, f"{func}() missing 1 required {args_sort} argument: '{missing_args[0]}'")
        if len(missing_args) > 1:
            arg_names = " and ".join(
                (
                    ", ".join(repr(arg) for arg in missing_args[:-1]),
                    repr(missing_args[-1]),
                )
            )
            # The exception raised here tries to match as closely as possible what python
            # would have raised as exception
            raise RuntimeException(None, f"{func}() missing {len(missing_args)} required {args_sort} arguments: {arg_names}")

    def check_args(self, args: list[object], kwargs: dict[str, object]) -> bool:
        """
        Check if the arguments of the call match the function signature.

        1. Check if we have too many arguments
        2. Check if we have too few arguments
        3. Check if we have any duplicate arguments (provided as positional and keyword)
        4. Validate the type of each of the provided arguments

        :param args: All the positional arguments to pass on to the plugin function
        :param kwargs: All the keyword arguments to pass on to the plugin function
        """
        if self.var_args is None and len(args) > len(self.args):
            # (1) We got too many positional arguments
            # The exception raised here tries to match as closely as possible what python
            # would have raised as exception
            raise RuntimeException(
                None, f"{self.get_full_name()}() takes {len(self.args)} positional arguments but {len(args)} were given"
            )

        # (2) Check that all positional arguments without a default are provided
        missing_positional_arguments = [
            arg.arg_name
            for position, arg in enumerate(self.args)
            if (
                position >= len(args)  # No input from user in positional args
                and arg.arg_name not in kwargs  # No input from user in keyword args
                and not arg.has_default_value()  # No default value in plugin definition
            )
        ]
        self.report_missing_arguments(missing_positional_arguments, "positional")

        # (2) Check that all keyword arguments without a default are provided
        missing_keyword_arguments = [
            name
            for name, arg in self.kwargs.items()
            if (
                arg.is_kw_only_argument  # The argument was not yet checked as positional arg
                and name not in kwargs  # No input from user in keyword args
                and not arg.has_default_value()  # No default value in plugin definition
            )
        ]
        self.report_missing_arguments(missing_keyword_arguments, "keyword-only")

        # Validate all positional arguments
        for position, value in enumerate(args):
            # (1) Get the corresponding argument, fails if we don't have one
            arg = self.get_arg(position)

            # (4) Validate the input value
            if not arg.validate(value):
                return False

        # Validate all kw arguments
        for name, value in kwargs.items():
            # (1) Get the corresponding kwarg, fails if we don't have one
            kwarg = self.get_kwarg(name)

            # (3) Make sure that our argument is not provided twice
            if kwarg.arg_position is not None and kwarg.arg_position < len(args):
                # The exception raised here tries to match as closely as possible what python
                # would have raised as exception
                raise RuntimeException(None, f"{self.get_full_name()}() got multiple values for argument '{name}'")

            # (4) Validate the input value
            if not kwarg.validate(value):
                return False
        return True

    def emit_statement(self) -> "DynamicStatement":
        """
        This method is called to determine if the plugin call pushes a new
        statement
        """
        return self.new_statement

    def is_accept_unknowns(self) -> bool:
        return self.opts["allow_unknown"]

    def check_requirements(self) -> None:
        """
        Check if the plug-in has all it requires
        """
        if "bin" in self.opts and self.opts["bin"] is not None:
            for _bin in self.opts["bin"]:
                p = subprocess.Popen(["bash", "-c", "type -p %s" % _bin], stdout=subprocess.PIPE)
                result = p.communicate()

                if len(result[0]) == 0:
                    raise Exception(f"{self.__function_name__} requires {_bin} to be available in $PATH")

    @classmethod
    def deprecate_function(cls, replaced_by: Optional[str] = None) -> None:
        cls.deprecated = True
        cls.replaced_by = replaced_by

    def __call__(self, *args: object, **kwargs: object) -> object:
        """
        The function call itself
        """
        if self.deprecated:
            msg: str = f"Plugin '{self.get_full_name()}' is deprecated."
            if self.replaced_by:
                msg += f" It should be replaced by '{self.replaced_by}'."
            warnings.warn(PluginDeprecationWarning(msg))
        self.check_requirements()

        def new_arg(arg: object) -> object:
            if isinstance(arg, Context):
                return arg
            elif isinstance(arg, Unknown) and self.is_accept_unknowns():
                return arg
            else:
                return DynamicProxy.return_value(arg)

        new_args = [new_arg(arg) for arg in args]
        new_kwargs = {k: new_arg(v) for k, v in kwargs.items()}

        value = self.call(*new_args, **new_kwargs)

        value = DynamicProxy.unwrap(value)

        # Validate the returned value
        self.return_type.validate(value)

        return value

    def get_full_name(self) -> str:
        return f"{self.ns.get_full_name()}::{self.__class__.__function_name__}"

    def type_string(self) -> str:
        return self.get_full_name()


@stable_api
class PluginException(Exception):
    """
    Base class for custom exceptions raised from a plugin.
    """

    def __init__(self, message: str) -> None:
        self.message = message


@stable_api
def plugin(
    function: Optional[Callable] = None,
    commands: Optional[list[str]] = None,
    emits_statements: bool = False,
    allow_unknown: bool = False,
) -> Callable:
    """
    Python decorator to register functions with inmanta as plugin

    :param function: The function to register with inmanta. This is the first argument when it is used as decorator.
    :param commands: A list of command paths that need to be available. Inmanta raises an exception when the command is
                     not available.
    :param emits_statements: Set to true if this plugin emits new statements that the compiler should execute. This is only
                             required for complex plugins such as integrating a template engine.
    :param allow_unknown: Set to true if this plugin accepts Unknown values as valid input.
    """

    def curry_name(
        name: Optional[str] = None,
        commands: Optional[list[str]] = None,
        emits_statements: bool = False,
        allow_unknown: bool = False,
    ) -> Callable:
        """
        Function to curry the name of the function
        """

        def call(fnc):
            """
            Create class to register the function and return the function itself
            """

            def wrapper(self, *args: object, **kwargs: object) -> Any:
                """
                Python will bind the function as method into the class
                """
                return fnc(*args, **kwargs)

            nonlocal name, commands, emits_statements

            if name is None:
                name = fnc.__name__

            ns_parts = str(fnc.__module__).split(".")
            ns_parts.append(name)
            if ns_parts[0] != const.PLUGINS_PACKAGE:
                raise Exception("All plugin modules should be loaded in the %s package" % const.PLUGINS_PACKAGE)

            fq_plugin_name = "::".join(ns_parts[1:])

            dictionary = {}
            dictionary["__module__"] = fnc.__module__

            dictionary["__function_name__"] = name
            dictionary["__fq_plugin_name__"] = fq_plugin_name

            dictionary["opts"] = {"bin": commands, "emits_statements": emits_statements, "allow_unknown": allow_unknown}
            dictionary["call"] = wrapper
            dictionary["__function__"] = fnc

            bases = (Plugin,)
            fnc.__plugin__ = PluginMeta.__new__(PluginMeta, name, bases, dictionary)
            return fnc

        return call

    if function is None:
        return curry_name(commands=commands, emits_statements=emits_statements, allow_unknown=allow_unknown)

    elif isinstance(function, str):
        return curry_name(function, commands=commands, emits_statements=emits_statements, allow_unknown=allow_unknown)

    elif function is not None:
        fnc = curry_name(commands=commands, emits_statements=emits_statements, allow_unknown=allow_unknown)
        return fnc(function)


@stable_api
def deprecated(
    function: Optional[Callable] = None, *, replaced_by: Optional[str] = None, **kwargs: abc.Mapping[str, object]
) -> Callable:
    """
    the kwargs are currently ignored but where added in case we want to add something later on.
    """

    def inner(fnc: Callable):
        if hasattr(fnc, "__plugin__"):
            fnc.__plugin__.deprecate_function(replaced_by)
        else:
            raise Exception(
                f"Can not deprecate '{fnc.__name__}': The '@deprecated' decorator should be used in combination with the "
                f"'@plugin' decorator and should be placed at the top."
            )
        return fnc

    if function is not None:
        return inner(function)
    return inner
