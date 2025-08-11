import packaging.version
from collections.abc import Callable, Sequence
from mypy import nodes, typevars, types
from mypy.plugin import AttributeContext, Plugin
from typing import Optional


class ClientMethodsPlugin(Plugin):
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
                )
                if (name := fullname.removeprefix(prefix)) != fullname
            ),
            None,
        )

        if client_attr is None or "." in client_attr:
            return None

        # TODO: what about inmanta-lsm methods?
        node: Optional[nodes.SymbolTableNode] = (
            self.lookup_fully_qualified(f"inmanta.protocol.methods_v2.{client_attr}")
            or self.lookup_fully_qualified(f"inmanta.protocol.methods.{client_attr}")
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

    def get_attribute_hook(self, fullname: str) -> Optional[Callable[[AttributeContext], types.CallableType]]:
        """
        For dynamic method accesses on a client object, return a hook that resolves to the associated method type signature,
        with the return type wrapped in a ClientCall.
        """
        method: Optional[types.CallableType] = self._get_method(fullname)
        if method is None:
            return None

        def hook(ctx: AttributeContext) -> types.CallableType:
            drop_arg_index: Optional[int] = (
                # SessionClient injects sid => drop it from the signature offered to callers
                next((i for i, arg_name in enumerate(method.arg_names) if arg_name == "sid"), None)
                if fullname.startswith("inmanta.protocol.endpoints.SessionClient.")
                else None
            )

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
                pageable_client_call: Optional[types.Instance] = self._get_instance("inmanta.protocol.common.PageableClientCall")
                assert pageable_client_call is not None
                return_type = pageable_client_call.copy_modified(args=[default_return_type_flattened.args[0]])
            else:
                client_call: Optional[types.Instance] = self._get_instance("inmanta.protocol.common.ClientCall")
                assert client_call is not None
                return_type = client_call.copy_modified(args=[default_return_type_flattened])

            def drop[T](s: Sequence[T], i: int) -> list[T]:
                return [*s[:i], *s[i + 1:]]

            return (
                method.copy_modified(ret_type=return_type)
                if drop_arg_index is None
                else method.copy_modified(
                    arg_types=drop(method.arg_types, drop_arg_index),
                    arg_kinds=drop(method.arg_kinds, drop_arg_index),
                    arg_names=drop(method.arg_names, drop_arg_index),
                    ret_type=return_type,
                )
            )

        return hook


def plugin(version: str) -> type[Plugin]:
    return (
        ClientMethodsPlugin
        if packaging.version.Version(version) >= packaging.version.Version("1.17")
        # fall back to default behavior for older versions with unknown compatibility
        else Plugin
    )
