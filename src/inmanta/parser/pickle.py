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
import threading
from pickle import Pickler, Unpickler, UnpicklingError
from typing import IO, Callable

from inmanta.ast import Namespace

# Thread-local storage for unpickling context
_unpickle_context: threading.local = threading.local()


def _reduce_namespace(
    ns: object,
) -> tuple[Callable[..., object], tuple[str]]:
    """Reducer for Namespace objects — replaces with full name string."""
    assert isinstance(ns, Namespace)
    return (_restore_namespace, (ns.get_full_name(),))


def _restore_namespace(full_name: str) -> Namespace:
    """Restore a Namespace from the thread-local unpickle context."""
    ns: Namespace = _unpickle_context.namespace
    if ns.get_full_name() != full_name:
        raise UnpicklingError(f"Namespace mismatch: expected {ns.get_full_name()}, got {full_name}")
    return ns


class ASTPickler(Pickler):
    """Pickler that replaces Namespace objects with their fully-qualified name.

    Uses dispatch_table (C-level type check) instead of persistent_id
    (Python callback per object) for ~10x faster pickling.
    """

    dispatch_table = {**copyreg.dispatch_table, Namespace: _reduce_namespace}

    def __init__(self, file: IO[bytes], protocol: int = 4) -> None:
        super().__init__(file, protocol=protocol)


class ASTUnpickler(Unpickler):
    """Unpickler that restores Namespace objects from thread-local context."""

    def __init__(self, file: IO[bytes], namespace: Namespace) -> None:
        super().__init__(file)
        # Store namespace in thread-local so _restore_namespace can access it
        _unpickle_context.namespace = namespace


def pickle_ast(file: IO[bytes], obj: object) -> None:
    """Pickle an AST object to a file."""
    ASTPickler(file, protocol=4).dump(obj)


def unpickle_ast(file: IO[bytes], namespace: Namespace) -> object:
    """Unpickle an AST object from a file, restoring Namespace references."""
    return ASTUnpickler(file, namespace).load()
