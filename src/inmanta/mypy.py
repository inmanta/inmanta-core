from collections.abc import Callable
from mypy import typevars
from mypy.plugin import AttributeContext, MethodContext, Plugin
from mypy.types import AnyType, NoneType, Type

from inmanta.protocol import methods, methods_v2


# TODO: fix type errors in this file


client: str = "inmanta.protocol.endpoints.SessionClient."


class ClientMethodsPlugin(Plugin):
    def _get_method(self, fullname: str) -> object:
        client_attr: Optional[str] = next(
            (
                name
                for prefix in (
                    # TODO: typed & sync clients?
                    # TODO: SessionClient injects sid
                    "inmanta.protocol.endpoints.Client.",
                    "inmanta.protocol.endpoints.SessionClient.",
                )
                if (name := fullname.removeprefix(prefix)) != fullname
            ),
            None,
        )

        if client_attr is None:
            return None

        return (
            # TODO: use registered methods instead?
            self.lookup_fully_qualified(f"inmanta.protocol.methods_v2.{client_attr}")
            or self.lookup_fully_qualified(f"inmanta.protocol.methods.{client_attr}")
        )

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], Type] | None:
        method: Optional[object] = self._get_method(fullname)
        if method is None:
            return None
        return lambda ctx: method.node.type

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        """
        Hook to modify the return type of a method. When this is called, `get_attribute_hook` has already linked the attribute
        access to the method. This hook then wraps the method's return type in a ClientCall object.
        """
        method: Optional[object] = self._get_method(fullname)
        if method is None:
            return None
        client_call = self.lookup_fully_qualified("inmanta.protocol.common.ClientCall")
        client_call_generic = typevars.fill_typevars(client_call.node)

        def hook(ctx):
            element_type = (
                ctx.default_return_type
                # TODO: better check and implementation
                if isinstance(ctx.default_return_type, (AnyType, NoneType)) or ctx.default_return_type.type.fullname != "builtins.list"
                else ctx.default_return_type.args[0]
            )
            return client_call_generic.copy_modified(args=[ctx.default_return_type, element_type])

        return hook


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return ClientMethodsPlugin
