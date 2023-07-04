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
import inspect
import os
import subprocess
import warnings
from collections import abc
from functools import reduce
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Optional, Tuple, Type, TypeVar

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


class PluginArgument:
    """
    Represents the argument of an Inmanta plugin.
    """

    # Marker used to indicate that a plugin argument has no default value.
    NO_DEFAULT_VALUE_SET = object()

    def __init__(
        self, arg_name: str, arg_type: object, is_kw_only_argument: bool, default_value: object = NO_DEFAULT_VALUE_SET
    ) -> None:
        self.arg_name = arg_name
        self.arg_type = arg_type
        self.is_kw_only_argument = is_kw_only_argument
        self._default_value = default_value

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
        self._return = None

        self.arguments: List[PluginArgument]
        if hasattr(self.__class__, "__function__"):
            self.arguments = self._load_signature(self.__class__.__function__)
        else:
            self.arguments = []

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
        self.argtypes = [self.to_type(arg.arg_type, self.namespace) for arg in self.arguments]
        self.returntype = self.to_type(self._return, self.namespace)

    def _load_signature(self, function: Callable[..., object]) -> List[PluginArgument]:
        """
        Load the signature from the given python function
        """
        arg_spec = inspect.getfullargspec(function)

        # Calculate at which index the default values start (for the non-keyword-only attributes)
        default_start_for_args: Optional[int]
        if arg_spec.defaults is not None:
            default_start_for_args = len(arg_spec.args) - len(arg_spec.defaults)
        else:
            default_start_for_args = None

        arguments: List[PluginArgument] = []

        def process_kw_only_args(argument_name: str, annotation: object) -> PluginArgument:
            if arg_spec.kwonlydefaults and argument_name in arg_spec.kwonlydefaults:
                default_value = arg_spec.kwonlydefaults[argument_name]
                return PluginArgument(argument_name, annotation, is_kw_only_argument=True, default_value=default_value)
            else:
                return PluginArgument(argument_name, annotation, is_kw_only_argument=True)

        def process_regular_args(index: int, argument_name: str, annotation: object) -> PluginArgument:
            if default_start_for_args is not None and default_start_for_args <= index:
                default_value = arg_spec.defaults[default_start_for_args - index]
                return PluginArgument(argument_name, annotation, is_kw_only_argument=False, default_value=default_value)
            else:
                return PluginArgument(argument_name, annotation, is_kw_only_argument=False)

        def process_arg(index: int, argument_name: str, is_kwonly_arg: bool) -> None:
            if argument_name not in arg_spec.annotations:
                raise CompilerException(f"All arguments of plugin '{function.__name__}' should be annotated")
            annotation = arg_spec.annotations[argument_name]
            if annotation == Context:
                self._context = index
            else:
                if is_kwonly_arg:
                    plugin_argument = process_kw_only_args(argument_name, annotation)
                else:
                    plugin_argument = process_regular_args(index, argument_name, annotation)
                arguments.append(plugin_argument)

        # Process regular arguments
        for i in range(len(arg_spec.args)):
            process_arg(i, arg_spec.args[i], is_kwonly_arg=False)
        # Process keyword-only arguments
        for i in range(len(arg_spec.kwonlyargs)):
            process_arg(i, arg_spec.kwonlyargs[i], is_kwonly_arg=True)

        if "return" in arg_spec.annotations:
            self._return = arg_spec.annotations["return"]

        return arguments

    def get_signature(self) -> str:
        """
        Generate the signature of this plugin
        """
        arg_list = []
        for arg in self.arguments:
            if arg.has_default_value():
                arg_list.append("%s: %s=%s" % (arg.arg_name, arg.arg_type, str(arg.default_value)))
            else:
                arg_list.append("%s: %s" % (arg.arg_name, arg.arg_type))

        args = ", ".join(arg_list)

        if self._return is None:
            return "%s(%s)" % (self.__class__.__function_name__, args)
        return "%s(%s) -> %s" % (self.__class__.__function_name__, args, self._return)

    def to_type(self, arg_type: Optional[object], resolver: Namespace) -> Optional[inmanta_type.Type]:
        """
        Convert a string representation of a type to a type
        """
        if arg_type is None:
            return None

        if not isinstance(arg_type, str):
            raise CompilerException(
                "bad annotation in plugin %s::%s, expected str but got %s (%s)"
                % (self.ns, self.__class__.__function_name__, type(arg_type), arg_type)
            )

        if arg_type == "any":
            return None

        if arg_type == "expression":
            return None

        # quickfix issue #1774
        allowed_element_type: inmanta_type.Type = inmanta_type.Type()
        if arg_type == "list":
            return inmanta_type.TypedList(allowed_element_type)
        if arg_type == "dict":
            return inmanta_type.TypedDict(allowed_element_type)

        plugin_line: Range = Range(self.location.file, self.location.lnr, 1, self.location.lnr + 1, 1)
        locatable_type: LocatableString = LocatableString(arg_type, plugin_line, 0, None)

        # stack of transformations to be applied to the base inmanta_type.Type
        # transformations will be applied right to left
        transformation_stack: List[Callable[[inmanta_type.Type], inmanta_type.Type]] = []

        if locatable_type.value.endswith("?"):
            locatable_type.value = locatable_type.value[0:-1]
            transformation_stack.append(inmanta_type.NullableType)

        if locatable_type.value.endswith("[]"):
            locatable_type.value = locatable_type.value[0:-2]
            transformation_stack.append(inmanta_type.TypedList)

        return reduce(lambda acc, transform: transform(acc), reversed(transformation_stack), resolver.get_type(locatable_type))

    def _is_instance(self, value: object, arg_type: Type[object]) -> bool:
        """
        Check if value is of arg_type
        """
        if arg_type is None:
            return True

        if hasattr(arg_type, "validate"):
            return arg_type.validate(value)

        return isinstance(value, arg_type)

    def check_args(self, args: List[object], kwargs: Dict[str, object]) -> bool:
        """
        Check if the arguments of the call match the function signature
        """
        max_arg = len(self.arguments)
        if len(args) + len(kwargs) > max_arg:
            raise Exception(
                "Incorrect number of arguments for %s. Expected at most %d, got %d"
                % (self.get_signature(), max_arg, len(args) + len(kwargs))
            )
        # check for missing arguments
        required_args: FrozenSet[str] = frozenset(arg.arg_name for arg in self.arguments if not arg.has_default_value())
        present_positional_args: FrozenSet[str] = frozenset(arg.arg_name for arg in self.arguments[: len(args)])
        present_kwargs: FrozenSet[str] = frozenset(kwargs.keys())
        missing_args = required_args.difference({*present_positional_args, *present_kwargs})
        if missing_args:
            raise RuntimeException(
                None,
                "Missing %d required arguments for %s(): %s"
                % (len(missing_args), self.__class__.__function_name__, ",".join(missing_args)),
            )
        # check for kwargs overlap with positional arguments
        overlapping_args: FrozenSet[str] = present_kwargs.intersection(present_positional_args)
        if overlapping_args:
            raise RuntimeException(
                None,
                "Multiple values for %s in %s()" % (",".join(overlapping_args), self.__class__.__function_name__),
            )

        def is_valid(expected_arg: PluginArgument, expected_type: Type[object], arg: object) -> bool:
            if isinstance(arg, Unknown):
                return False

            if not self._is_instance(arg, expected_type):
                raise Exception(
                    "Invalid type for argument %s of '%s', it should be %s and %s given."
                    % (expected_arg.arg_name, self.__class__.__function_name__, expected_arg.arg_type, arg.__class__.__name__)
                )
            return True

        for i in range(len(args)):
            if not is_valid(self.arguments[i], self.argtypes[i], args[i]):
                return False
        arg_types: Dict[str, Tuple[PluginArgument, Optional[inmanta_type.Type]]] = {
            arg.arg_name: (arg, self.argtypes[i]) for i, arg in enumerate(self.arguments)
        }
        for k, v in kwargs.items():
            try:
                (expected_arg, expected_type) = arg_types[k]
                if not is_valid(expected_arg, expected_type, v):
                    return False
            except KeyError:
                raise RuntimeException(None, "Invalid keyword argument '%s' for '%s()'" % (k, self.__class__.__function_name__))
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
            msg: str = f"Plugin '{self.__function_name__}' in module '{self.__module__}' is deprecated."
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

        if self.returntype is not None and not isinstance(value, Unknown):
            valid = False
            exception = None

            try:
                valid = value is None or self._is_instance(value, self.returntype)
            except RuntimeException as e:
                raise e
            except Exception as exp:
                exception = exp

            if not valid:
                msg = ""
                if exception is not None:
                    msg = "\n\tException details: " + str(exception)

                raise Exception(
                    "Plugin %s should return value of type %s ('%s' was returned) %s"
                    % (self.__class__.__function_name__, self.returntype, value, msg)
                )

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
