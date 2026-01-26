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

import logging
from collections import abc
from itertools import chain
from typing import Mapping, Optional, Sequence

import inmanta.ast
import inmanta.ast.type as InmantaType
import inmanta.execute.dataflow as dataflow
from inmanta import plugins
from inmanta.ast import (
    ExplicitPluginException,
    ExternalException,
    LocatableString,
    MultiUnsetException,
    Namespace,
    PluginTypeException,
    Range,
    RuntimeException,
    TypeReferenceAnchor,
    UnknownException,
    UnsetException,
    WrappingRuntimeException,
)
from inmanta.ast.statements import AttributeAssignmentLHS, ExpressionStatement, ReferenceStatement
from inmanta.ast.statements.generator import WrappedKwargs
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import QueueScheduler, Resolver, ResultVariable, VariableABC, Waiter
from inmanta.execute.util import NoneValue, Unknown

LOGGER = logging.getLogger(__name__)


class FunctionCall(ReferenceStatement):
    """
    This class models a call to a function

    :param name: The name of the function that needs to be called
    :param arguments: A list of arguments

    uses:          args
    provides:      return value
    contributes:
    """

    __slots__ = ("name", "arguments", "wrapped_kwargs", "location", "kwargs", "function")

    def __init__(
        self,
        name: LocatableString,
        arguments: list[ExpressionStatement],
        kwargs: list[tuple[LocatableString, ExpressionStatement]],
        wrapped_kwargs: list[WrappedKwargs],
        namespace: Namespace,
    ) -> None:
        ReferenceStatement.__init__(self, list(chain(arguments, (v for _, v in kwargs), wrapped_kwargs)))
        self.name: LocatableString = name
        self.arguments: list[ExpressionStatement] = arguments
        self.wrapped_kwargs: list[WrappedKwargs] = wrapped_kwargs
        self.location: Range = name.get_location()
        self.namespace: Namespace = namespace
        self.kwargs: dict[str, ExpressionStatement] = {}
        for loc_name, expr in kwargs:
            arg_name: str = str(loc_name)
            if arg_name in self.kwargs:
                raise RuntimeException(self, f"Keyword argument {arg_name} repeated in function call {self.name}()")
            self.kwargs[arg_name] = expr
        self.function: Optional[Function] = None

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        ReferenceStatement.normalize(self)
        func = self.namespace.get_type(self.name)
        self.anchors = [TypeReferenceAnchor(self.namespace, self.name)]
        if isinstance(func, InmantaType.Primitive):
            self.function = Cast(self, func)
        elif isinstance(func, plugins.Plugin):
            self.function = PluginFunction(self, func)
        else:
            raise RuntimeException(self, "Can not call '%s', can only call plugin or primitive type cast" % self.name)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC[object]]:
        requires: dict[object, VariableABC] = self._requires_emit_promises(resolver, queue)
        sub = ReferenceStatement.requires_emit(self, resolver, queue)
        # add lazy vars
        temp = ResultVariable()
        FunctionUnit(queue, resolver, temp, sub, self)
        requires[self] = temp
        return requires

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self]

    def execute_direct(self, requires: abc.Mapping[str, object]) -> object:
        arguments = [a.execute_direct(requires) for a in self.arguments]
        kwargs = {k: v.execute_direct(requires) for k, v in self.kwargs.items()}
        for wrapped_kwarg_expr in self.wrapped_kwargs:
            for k, v in wrapped_kwarg_expr.execute_direct(requires):
                if k in kwargs:
                    raise RuntimeException(self, "Keyword argument %s repeated in function call" % k)
                kwargs[k] = v
        return self.function.call_direct(arguments, kwargs)

    def execute_args(
        self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler
    ) -> tuple[list[object], dict[str, object]]:
        """Execute the argument expessions and return a tuple of args-kwargs"""
        arguments = [a.execute(requires, resolver, queue) for a in self.arguments]
        kwargs = {k: v.execute(requires, resolver, queue) for k, v in self.kwargs.items()}
        for wrapped_kwarg_expr in self.wrapped_kwargs:
            for k, v in wrapped_kwarg_expr.execute(requires, resolver, queue):
                if k in kwargs:
                    raise RuntimeException(self, "Keyword argument %s repeated in function call" % k)
                kwargs[k] = v
        return arguments, kwargs

    def execute_call(
        self,
        arguments: list[object],
        kwargs: dict[str, object],
        resolver: Resolver,
        queue: QueueScheduler,
        result: ResultVariable,
    ) -> None:
        """
        Evaluate this statement, using the output of execute_args
        """
        self.function.call_in_context(arguments, kwargs, resolver, queue, result)

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("FunctionCall.get_node() placeholder for %s" % self).reference()

    def __repr__(self) -> str:
        return "{}({})".format(
            self.name,
            ",".join(
                chain(
                    (repr(a) for a in self.arguments),
                    (f"{k}={repr(v)}" for k, v in self.kwargs.items()),
                    (repr(kwargs) for kwargs in self.wrapped_kwargs),
                )
            ),
        )

    def pretty_print(self) -> str:
        return "{}({})".format(
            self.name,
            ",".join(
                chain(
                    (a.pretty_print() for a in self.arguments),
                    (f"{k}={v.pretty_print()}" for k, v in self.kwargs.items()),
                    (kwargs.pretty_print() for kwargs in self.wrapped_kwargs),
                )
            ),
        )


class Function:
    def __init__(self, ast_node: FunctionCall) -> None:
        self.ast_node: FunctionCall = ast_node

    def call_direct(self, args: list[object], kwargs: dict[str, object]) -> object:
        """
        Call this function and return the result.
        """
        raise NotImplementedError()

    def call_in_context(
        self, args: list[object], kwargs: dict[str, object], resolver: Resolver, queue: QueueScheduler, result: ResultVariable
    ) -> None:
        """
        Call this function in the supplied context and store the result in the supplied ResultVariable.
        """
        raise NotImplementedError()


class Cast(Function):
    def __init__(self, ast_node: FunctionCall, tp: InmantaType.Primitive) -> None:
        Function.__init__(self, ast_node)
        self.type = tp

    def call_direct(self, args: list[object], kwargs: dict[str, object]) -> object:
        if len(kwargs) > 0:
            raise RuntimeException(self.ast_node, "Only positional arguments allowed in type cast")
        if len(args) != 1:
            raise RuntimeException(
                self.ast_node, "Illegal arguments %s: type cast expects exactly 1 argument" % ",".join(map(repr, args))
            )
        return self.type.cast(*args)

    def call_in_context(
        self, args: list[object], kwargs: dict[str, object], resolver: Resolver, queue: QueueScheduler, result: ResultVariable
    ) -> None:
        result.set_value(self.call_direct(args, kwargs), self.ast_node.location)


class PluginFunction(Function):
    def __init__(self, ast_node: FunctionCall, plugin: plugins.Plugin) -> None:
        Function.__init__(self, ast_node)
        self.plugin: plugins.Plugin = plugin

    def call_direct(self, args: list[object], kwargs: dict[str, object]) -> object:
        processed_args = self.plugin.check_args(args, kwargs)
        no_unknows = not processed_args.unknowns

        if not no_unknows and not self.plugin.opts["allow_unknown"]:
            raise RuntimeException(self.ast_node, "Received unknown value during direct execution")

        if self.plugin._context != -1:
            raise RuntimeException(self.ast_node, "Context Aware functions are not allowed in direct execution")

        if self.plugin.opts["emits_statements"]:
            raise RuntimeException(self.ast_node, "emits_statements functions are not allowed in direct execution")
        else:
            try:
                return self.plugin(*processed_args.args, **processed_args.kwargs)
            except PluginTypeException:
                # already has sufficient context, no need to wrap it
                raise
            except RuntimeException as e:
                raise WrappingRuntimeException(
                    self.ast_node, "Exception in direct execution for plugin %s" % self.ast_node.name, e
                )
            except inmanta.ast.PluginException as e:
                raise ExplicitPluginException(
                    self.ast_node, "PluginException in direct execution for plugin %s" % self.ast_node.name, e
                )
            except Exception as e:
                raise ExternalException(self.ast_node, "Exception in direct execution for plugin %s" % self.ast_node.name, e)

    def call_in_context(
        self,
        args: Sequence[object],
        kwargs: Mapping[str, object],
        resolver: Resolver,
        queue: QueueScheduler,
        result: ResultVariable,
    ) -> None:

        processed_args = self.plugin.check_args(args, kwargs)
        no_unknows = not processed_args.unknowns

        if not no_unknows and not self.plugin.opts["allow_unknown"]:
            result.set_value(Unknown(self), self.ast_node.location)
            return

        args = processed_args.args
        kwargs = processed_args.kwargs

        if self.plugin._context != -1:
            # Don't mutate the arguments!
            args.insert(self.plugin._context, plugins.Context(resolver, queue, self.ast_node, self.plugin, result))

        if self.plugin.opts["emits_statements"]:
            self.plugin(*args, **kwargs)
        else:
            try:
                value = self.plugin.call_in_context(processed_args, resolver, queue, self.ast_node.location)
                result.set_value(value if value is not None else NoneValue(), self.ast_node.location)
            except UnknownException as e:
                result.set_value(e.unknown, self.ast_node.location)
            except (UnsetException, MultiUnsetException) as e:
                call: str = str(self.plugin)
                location: str = str(self.ast_node.location)
                LOGGER.debug(
                    "Unset value in python code in plugin at call: %s (%s) (Will be rescheduled by compiler)", call, location
                )
                # Don't handle it here!
                # This exception is used by the scheduler to re-queue the unit
                # If it is handled here, the re-queueing can not be done,
                # leading to very subtle errors such as #2787
                raise e
            except PluginTypeException:
                # already has sufficient context, no need to wrap it
                raise
            except RuntimeException as e:
                raise WrappingRuntimeException(self.ast_node, "Exception in plugin %s" % self.ast_node.name, e)
            except inmanta.ast.PluginException as e:
                raise ExplicitPluginException(self.ast_node, "PluginException in plugin %s" % self.ast_node.name, e)
            except Exception as e:
                raise ExternalException(self.ast_node, "Exception in plugin %s" % self.ast_node.name, e)


class FunctionUnit(Waiter):
    __slots__ = ("result", "base_requires", "function", "resolver", "args", "kwargs")

    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: Resolver,
        result: ResultVariable[object],
        requires: dict[object, VariableABC[object]],
        function: FunctionCall,
    ) -> None:
        Waiter.__init__(self, queue_scheduler)
        self.result = result
        # requires is used to track all required RV's
        # It can grow larger as new requires are discovered
        self.requires = requires
        # base_requires are the original requires for this function call
        self.base_requires = dict(requires)
        self.function = function
        self.resolver = resolver
        for r in requires.values():
            self.waitfor(r)
        self.ready(self)
        # resolved args and kwargs
        self.args: Optional[list[object]] = None
        self.kwargs: Optional[dict[str, object]] = None

    def execute(self) -> None:
        # Execution in two stages to prevent re-execution of argument expressions
        if self.args is None:
            # stage one: arguments
            # execute once and cache results
            requires = {k: v.get_value() for (k, v) in self.base_requires.items()}
            try:
                self.args, self.kwargs = self.function.execute_args(requires, self.resolver, self.queue)
            except RuntimeException as e:
                # for arg expression execution failures, report the sub-expression rather than the plugin call => replace=False
                e.set_statement(self.function, replace=False)
                raise e

        try:
            assert self.args is not None  # Mypy
            assert self.kwargs is not None  # Mypy
            self.function.execute_call(self.args, self.kwargs, self.resolver, self.queue, self.result)
            self.done = True
            # prevent memory leaks
            self.args = None
            self.kwargs = None
        except RuntimeException as e:
            e.set_statement(self.function)
            raise e

    def __repr__(self) -> str:
        return repr(self.function)
