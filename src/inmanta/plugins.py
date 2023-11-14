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
import copy
import inspect
import os
import subprocess
import warnings
from collections import abc
from functools import reduce
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

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
from inmanta.execute.util import Unknown
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
class Context(object):
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

    def __new__(cls, name: str, bases: Tuple[type, ...], dct: Dict[str, object]) -> Type:
        subclass = type.__new__(cls, name, bases, dct)
        if hasattr(subclass, "__function_name__"):
            cls.add_function(subclass)
        return subclass

    __functions: Dict[str, Type["Plugin"]] = {}

    @classmethod
    def add_function(cls, plugin_class: Type["Plugin"]) -> None:
        """
        Add a function plugin class
        """
        cls.__functions[plugin_class.__fq_plugin_name__] = plugin_class

    @classmethod
    def get_functions(cls) -> Dict[str, "Type[Plugin]"]:
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


def resolve_type(locatable_type: LocatableString, resolver: Namespace) -> Optional[inmanta_type.Type]:
    """
    Convert a locatable type string, into a real inmanta type, that can be used for validation.
    Alternatively, if the locatable string defines a type that doesn't have any constraint, return None.

    :param locatable_type: An object pointing to the type annotation string.
    :param resolver: The namespace that can be used to resolve the type annotation of this
        argument.
    """
    if locatable_type.value == "any":
        return None

    if locatable_type.value == "expression":
        return None

    # quickfix issue #1774
    allowed_element_type: inmanta_type.Type = inmanta_type.Type()
    if locatable_type.value == "list":
        return inmanta_type.TypedList(allowed_element_type)
    if locatable_type.value == "dict":
        return inmanta_type.TypedDict(allowed_element_type)

    # stack of transformations to be applied to the base inmanta_type.Type
    # transformations will be applied right to left
    transformation_stack: List[Callable[[inmanta_type.Type], inmanta_type.Type]] = []

    if locatable_type.value.endswith("?"):
        # We don't want to modify the object we received as argument
        locatable_type = copy.copy(locatable_type)
        locatable_type.value = locatable_type.value[0:-1]
        transformation_stack.append(inmanta_type.NullableType)

    if locatable_type.value.endswith("[]"):
        # We don't want to modify the object we received as argument
        locatable_type = copy.copy(locatable_type)
        locatable_type.value = locatable_type.value[0:-2]
        transformation_stack.append(inmanta_type.TypedList)

    return reduce(lambda acc, transform: transform(acc), reversed(transformation_stack), resolver.get_type(locatable_type))


class PluginIO:
    """
    Base class for all values that go in and out of a plugin: arguments and return value.

    The class has two class attributes that should be set in the different subclasses:
    :attr IO_TYPE: The type of io value it is, argument or return value
    :attr IO_NAME: The name of the io value, the argument name or "return value"

    These attributes are only used for better error reporting.
    """

    IO_TYPE: str = ""
    IO_NAME: str = ""

    def __init__(self, type_expression: object) -> None:
        self.type_expression = type_expression

        # We define the attribute but don't set it yet, this will be done when
        # the type is resolved.  This allows to differentiate between a type that
        # has not been resolved and a type that is a match for "any" (None).
        self._resolved_type: Optional[inmanta_type.Type]

    @property
    def resolved_type(self) -> Optional[inmanta_type.Type]:
        if not hasattr(self, "_resolved_type"):
            raise CompilerException(
                f"{type(self).__name__} {self.IO_NAME} ({repr(self.type_expression)}) has not been normalized, "
                "its resolved type can't be accessed."
            )
        return self._resolved_type

    def resolve_type(self, plugin: "Plugin", resolver: Namespace) -> Optional[inmanta_type.Type]:
        """
        Convert the string representation of this argument's type to a type.
        If no type annotation is present or if the type annotation allows any type to be passed
        as argument, then None is returned.

        :param plugin: The plugin that this argument is part of.
        :param resolver: The namespace that can be used to resolve the type annotation of this
            argument.
        """
        if self.type_expression is None:
            self._resolved_type = None
            return self._resolved_type

        if not isinstance(self.type_expression, str):
            raise CompilerException(
                "Bad annotation in plugin %s for %s, expected str but got %s (%s)"
                % (plugin.get_full_name(), self.IO_NAME, type(self.type_expression).__name__, self.type_expression)
            )

        plugin_line: Range = Range(plugin.location.file, plugin.location.lnr, 1, plugin.location.lnr + 1, 1)
        locatable_type: LocatableString = LocatableString(self.type_expression, plugin_line, 0, None)
        self._resolved_type = resolve_type(locatable_type, resolver)
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

        if self.resolved_type is None:
            # Any value is valid
            return True

        # Validate the value, use custom validate method of the type if it exists
        if hasattr(self.resolved_type, "validate"):
            valid = getattr(self.resolved_type, "validate")(value)
        else:
            valid = isinstance(value, self.resolved_type)

        if not valid:
            # Validation fail, we should raise an exception
            raise ValueError(
                "Invalid %s for %s: value %s has type %s (expected %s)"
                % (self.IO_TYPE, self.IO_NAME, repr(value), type(value).__name__, type(self.resolved_type).__name__)
            )

        return True


class PluginArgument(PluginIO):
    """
    Represents the argument of an Inmanta plugin.
    """

    IO_TYPE = "argument value"

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
        self.IO_NAME = self.arg_name

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
            return "%s: %s = %s" % (self.arg_name, self.arg_type, str(self.default_value))
        else:
            return "%s: %s" % (self.arg_name, self.arg_type)


class PluginReturn(PluginIO):
    """
    Represent the return type of an Inmanta plugin.
    """

    IO_TYPE = "returned value"
    IO_NAME = "return value"


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
        self.return_type: PluginReturn = PluginReturn(None)
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
        for arg in self.args:
            arg.resolve_type(self, self.resolver)
        if self.var_args is not None:
            self.var_args.resolve_type(self, self.resolver)
        for arg in self.kwargs.values():
            arg.resolve_type(self, self.resolver)
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
        self.return_type = PluginReturn(arg_spec.annotations.get("return", None))

        # Inspect the function to get its arguments and annotations
        arg_spec = inspect.getfullargspec(function)

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

            if self._context != -1:
                # If we have a context argument, the position index
                # needs to be adapted as this context object can never be passed
                # from the model.
                position -= 1

            self.args.append(
                PluginArgument(
                    arg_name=arg,
                    arg_type=annotation,
                    arg_position=position,
                    default_value=(
                        arg_spec.defaults[position - defaults_start_at]
                        if position >= defaults_start_at
                        else PluginArgument.NO_DEFAULT_VALUE_SET
                    ),
                )
            )

            # All positional arguments can also be assigned as kwargs
            self.kwargs[arg] = self.args[position]

        # Save all key-word arguments
        for arg in arg_spec.kwonlyargs:
            self.kwargs[arg] = PluginArgument(
                arg_name=arg,
                arg_type=get_annotation(arg),
                default_value=(
                    arg_spec.kwonlydefaults[arg]
                    if arg_spec.kwonlydefaults is not None and arg in arg_spec.kwonlydefaults
                    else PluginArgument.NO_DEFAULT_VALUE_SET
                ),
            )

    def get_signature(self) -> str:
        """
        Generate the signature of this plugin.  The signature is a string representing the the function
        as it can be called as a plugin in the model.
        """
        arg_list = []

        for arg in self.args:
            arg_list.append(str(arg))

        if self.var_args is not None:
            arg_list.append("*" + str(self.var_args))
        elif self.kwargs:
            # For keyword only arguments, we need a marker if we don't have a catch-all
            # positional argument
            arg_list.append("*")

        for arg in self.kwargs.values():
            if not arg.is_kw_only_argument:
                # This argument should already be represented as a positional argument
                continue

            arg_list.append(str(arg))

        if self.var_kwargs is not None:
            arg_list.append("**" + str(self.var_kwargs))

        args = ", ".join(arg_list)

        if self.return_type.type_expression is None:
            return "%s(%s)" % (self.__class__.__function_name__, args)
        return "%s(%s) -> %s" % (self.__class__.__function_name__, args, self.return_type.type_expression)

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

        :param name: The name of the argument
        """
        if name in self.kwargs:
            return self.kwargs[name]
        elif self.var_kwargs is not None:
            return self.var_kwargs
        else:
            # Trying to provide a keyword argument which doesn't exist
            raise RuntimeException(None, f"{self.get_full_name()}() got an unexpected keyword argument: '{name}'")

    def check_args(self, args: List[object], kwargs: Dict[str, object]) -> bool:
        """
        Check if the arguments of the call match the function signature.

        :param args: All the positional arguments to pass on to the plugin function
        :param kwargs: All the keyword arguments to pass on to the plugin function
        """
        if self.var_args is None and len(args) > len(self.args):
            # We got too many positional arguments
            raise RuntimeException(
                None, f"{self.get_full_name()}() takes {len(self.args)} positional arguments but {len(args)} were given"
            )

        # Validate all positional arguments
        for position, value in enumerate(args):
            # Get the corresponding argument, fails if we don't have one
            arg = self.get_arg(position)

            # Validate the input value
            if not arg.validate(value):
                return False

        # Validate all kw arguments
        for name, value in kwargs.items():
            # Get the corresponding kwarg, fails if we don't have one
            kwarg = self.get_kwarg(name)

            # Make sure that our argument is not provided twice
            if kwarg.arg_position is not None and kwarg.arg_position < len(args):
                raise RuntimeException(None, f"{self.get_full_name()}() fot multiple values for argument '{name}'")

            # Validate the input value
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
                    raise Exception("%s requires %s to be available in $PATH" % (self.__function_name__, _bin))

    @classmethod
    def deprecate_function(cls, replaced_by: Optional[str] = None) -> None:
        cls.deprecated = True
        cls.replaced_by = replaced_by

    def __call__(self, *args: object, **kwargs: object) -> object:
        """
        The function call itself
        """
        if self.deprecated:
            msg: str = f"Plugin '{self.get_full_name()}' in module '{self.__module__}' is deprecated."
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
        return "%s::%s" % (self.ns.get_full_name(), self.__class__.__function_name__)

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
    commands: Optional[List[str]] = None,
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
        commands: Optional[List[str]] = None,
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
