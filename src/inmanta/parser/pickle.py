"""
Copyright 2026 Inmanta

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

Custom pickler/unpickler for AST Statement objects.

Namespace objects cannot be pickled (they're tied to runtime compilation context),
so they are replaced with their fully-qualified name string during pickling and
restored from the unpickler instance during unpickling.
"""

import contextvars
import copyreg
import types
from pickle import Pickler, Unpickler, UnpicklingError
from typing import IO, Callable

from inmanta.ast import Namespace

# Namespace the active ASTUnpickler is restoring into. A ContextVar rather than a
# thread local so that concurrent and re-entrant unpickling both stay correct.
current_namespace: contextvars.ContextVar[Namespace] = contextvars.ContextVar("ast_unpickler_namespace")


def reduce_namespace(
    ns: object,
) -> tuple[Callable[..., object], tuple[str]]:
    """Reducer for Namespace objects, replaces with full name string."""
    assert isinstance(ns, Namespace)
    return (restore_namespace, (ns.get_full_name(),))


def restore_namespace(full_name: str) -> Namespace:
    """Restore a Namespace during unpickling.

    This module-level function is referenced in the pickle stream via dispatch_table.
    It resolves the namespace from the ASTUnpickler that is currently loading, so the
    C unpickler keeps its native find_class fast path for every other global.

    If called directly (outside ASTUnpickler), raises UnpicklingError.
    """
    namespace: Namespace | None = current_namespace.get(None)
    if namespace is None:
        raise UnpicklingError(f"restore_namespace({full_name!r}) called outside ASTUnpickler context")
    if namespace.get_full_name() != full_name:
        raise UnpicklingError(f"Namespace mismatch: expected {namespace.get_full_name()}, got {full_name}")
    return namespace


class ASTPickler(Pickler):
    """Pickler that replaces Namespace objects with their fully-qualified name.

    Uses dispatch_table instead of persistent_id. persistent_id is a Python callback
    invoked for every object in the graph, and it runs before the memo lookup, so a
    namespace is re-emitted at each occurrence rather than referenced. dispatch_table
    is a C-level type lookup and its result is memoized: roughly 2x faster to write,
    2x faster to read back, and a 5% smaller cache file.
    """

    dispatch_table = types.MappingProxyType({**copyreg.dispatch_table, Namespace: reduce_namespace})


class ASTUnpickler(Unpickler):
    """Unpickler that restores Namespace objects from the namespace being loaded into.

    Publishes the namespace on a ContextVar for the duration of load() rather than
    overriding find_class(). Overriding find_class() would route every global lookup
    in the stream through a Python callback, which costs more than it saves.
    """

    def __init__(self, file: IO[bytes], namespace: Namespace) -> None:
        super().__init__(file)
        self._namespace = namespace

    def load(self) -> object:
        token = current_namespace.set(self._namespace)
        try:
            return super().load()
        finally:
            current_namespace.reset(token)
