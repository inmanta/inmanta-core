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
restored from a thread-local context during unpickling.
"""

import copyreg
from pickle import Pickler, Unpickler, UnpicklingError
from typing import IO, Callable

from inmanta.ast import Namespace


def _reduce_namespace(
    ns: object,
) -> tuple[Callable[..., object], tuple[str]]:
    """Reducer for Namespace objects — replaces with full name string."""
    assert isinstance(ns, Namespace)
    return (_restore_namespace, (ns.get_full_name(),))


def _restore_namespace(full_name: str) -> Namespace:
    """Restore a Namespace during unpickling.

    This module-level function is referenced in the pickle stream via dispatch_table.
    ASTUnpickler intercepts calls to it via find_class() and binds the namespace
    from the unpickler instance, avoiding thread-local state entirely.

    If called directly (outside ASTUnpickler), raises UnpicklingError.
    """
    raise UnpicklingError(
        f"_restore_namespace({full_name!r}) called outside ASTUnpickler context"
    )


class ASTPickler(Pickler):
    """Pickler that replaces Namespace objects with their fully-qualified name.

    Uses dispatch_table (C-level type check) instead of persistent_id
    (Python callback per object) for ~10x faster pickling.
    """

    dispatch_table = {**copyreg.dispatch_table, Namespace: _reduce_namespace}

    def __init__(self, file: IO[bytes], protocol: int = 4) -> None:
        super().__init__(file, protocol=protocol)


class ASTUnpickler(Unpickler):
    """Unpickler that restores Namespace objects from an instance-local reference.

    Overrides find_class() to intercept the pickle stream's reference to
    _restore_namespace and bind it to this instance's namespace. This avoids
    thread-local state, making concurrent and re-entrant unpickling safe.
    """

    def __init__(self, file: IO[bytes], namespace: Namespace) -> None:
        super().__init__(file)
        self._namespace = namespace

    def find_class(self, module: str, name: str) -> Callable[..., object]:
        if module == _RESTORE_MODULE and name == _RESTORE_QUALNAME:
            return self._restore_namespace_bound
        return super().find_class(module, name)

    def _restore_namespace_bound(self, full_name: str) -> Namespace:
        """Instance-bound namespace restoration — no shared mutable state."""
        if self._namespace.get_full_name() != full_name:
            raise UnpicklingError(
                f"Namespace mismatch: expected {self._namespace.get_full_name()}, got {full_name}"
            )
        return self._namespace


# Module and qualname of _restore_namespace, used by find_class() to intercept it.
_RESTORE_MODULE = _restore_namespace.__module__
_RESTORE_QUALNAME = _restore_namespace.__qualname__


def pickle_ast(file: IO[bytes], obj: object) -> None:
    """Pickle an AST object to a file."""
    ASTPickler(file, protocol=4).dump(obj)


def unpickle_ast(file: IO[bytes], namespace: Namespace) -> object:
    """Unpickle an AST object from a file, restoring Namespace references."""
    return ASTUnpickler(file, namespace).load()
