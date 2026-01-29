"""
Copyright 2025 Inmanta

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

import importlib.metadata
from collections.abc import Callable, Sequence
from typing import Optional

import packaging.version
from mypy import nodes, types, typevars
from mypy.plugin import AttributeContext, Plugin

method_namespaces: Sequence[str] = [
    entry_point.value for entry_point in importlib.metadata.entry_points(group="inmanta.mypy.methods")
]


class ClientMethodsPlugin(Plugin):
    def get_additional_deps(self, file: nodes.MypyFile) -> list[tuple[int, str, int]]:
        """
        Make sure method namespaces are loaded when the Client module is loaded.
        """
        if file.fullname != "inmanta.protocol.endpoints":
            return []
        # See priorities in mypy.build.
        # 5 = top-level "from X import blah" => highest priority.
        # We use this priority because we really need the methods to be loaded at this point.
        # This is especially important due to the highly coupled nature of `inmanta.protocol`, which pulls in many other
        # modules, some of which with import loops involved. Without this priority, methods's signatures might not be known
        # yet at the point where we try to resolve `Client...` method accesss.
        return [(5, namespace, -1) for namespace in method_namespaces]

    def get_attribute_hook(self, fullname: str) -> Optional[Callable[[AttributeContext], types.CallableType]]:
        """
        For dynamic method accesses on a client object, return a hook that resolves to the associated method type signature,
        with the return type wrapped in a ClientCall.
        """
        method: Optional[types.CallableType] = self._get_method(fullname)
        if method is None:
            return None

        def hook(ctx: AttributeContext) -> types.CallableType:
            # unwrap ReturnValue[T]
            default_return_type_flattened: types.Type = (
                method.ret_type.args[0]
                if (
                    isinstance(method.ret_type, types.Instance)
                    and method.ret_type.type.fullname == "inmanta.protocol.common.ReturnValue"
                )
                else method.ret_type
            )

            return_type: types.Type
            if fullname.startswith("inmanta.protocol.endpoints.TypedClient."):
                # TypedClient returns method's return type without wrapping it
                return_type = default_return_type_flattened
            elif fullname.startswith("inmanta.protocol.endpoints.SyncClient."):
                # SyncClient returns method's return type wrapped in a Result object
                result_type: Optional[types.Instance] = self._get_instance("inmanta.protocol.common.Result")
                assert result_type is not None
                return_type = result_type.copy_modified(args=[default_return_type_flattened])
            # normal clients return method's return type wrapped in ClientCall or PageableClientCall
            elif (
                isinstance(default_return_type_flattened, types.Instance)
                and default_return_type_flattened.type.fullname == "builtins.list"
            ):
                pageable_client_call: Optional[types.Instance] = self._get_instance(
                    "inmanta.protocol.common.PageableClientCall"
                )
                assert pageable_client_call is not None
                return_type = pageable_client_call.copy_modified(args=[default_return_type_flattened.args[0]])
            else:
                client_call: Optional[types.Instance] = self._get_instance("inmanta.protocol.common.ClientCall")
                assert client_call is not None
                return_type = client_call.copy_modified(args=[default_return_type_flattened])

            return method.copy_modified(ret_type=return_type)

        return hook

    def _get_method(self, fullname: str) -> Optional[types.CallableType]:
        """
        If the given fully qualified name is a method access on a client object, returns the type signature object for that
        method. Returns None otherwise.
        """
        client_attr: Optional[str] = next(
            (
                name
                for prefix in (
                    "inmanta.protocol.endpoints.Client.",
                    "inmanta.protocol.endpoints.SessionClient.",
                    "inmanta.protocol.endpoints.SyncClient.",
                    "inmanta.protocol.endpoints.TypedClient.",
                    "inmanta.server.protocol.LocalClient.",
                )
                if (name := fullname.removeprefix(prefix)) != fullname
            ),
            None,
        )

        if client_attr is None or "." in client_attr:
            return None

        node: Optional[nodes.SymbolTableNode] = next(
            (
                lookup
                for namespace in method_namespaces
                if (lookup := self.lookup_fully_qualified(f"{namespace}.{client_attr}")) is not None
            ),
            None,
        )

        if node is None:
            return None

        result: Optional[types.Type] = node.type
        if result is None or not isinstance(result, types.CallableType):
            return None

        return result

    def _get_instance(self, fullname: str) -> Optional[types.Instance]:
        """
        Returns a mypy.types.Instance for the given full name, if it exists.
        """
        node: Optional[nodes.SymbolTableNode] = self.lookup_fully_qualified(fullname)
        if node is None or not isinstance(node.node, nodes.TypeInfo):
            return None
        generic: types.Instance | types.TupleType = typevars.fill_typevars(node.node)
        if not isinstance(generic, types.Instance):
            return None
        return generic


def plugin(version: str) -> type[Plugin]:
    return (
        ClientMethodsPlugin
        if packaging.version.Version(version) >= packaging.version.Version("1.17")
        # fall back to default behavior for older versions with unknown compatibility
        else Plugin
    )
