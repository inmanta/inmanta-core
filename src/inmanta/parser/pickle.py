"""
Copyright 2020 Inmanta

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

import threading
from io import BytesIO
from pickle import Pickler, Unpickler
from typing import Optional

from inmanta.ast import Namespace

# Thread-local storage for the namespace being unpickled.
# Set by ASTUnpickler.load() before invoking super().load(), cleared afterwards.
_unpickle_context: threading.local = threading.local()


def _restore_namespace() -> object:
    """
    Reconstructor called during unpickling to restore a Namespace reference.
    Returns the namespace stored in the thread-local set by ASTUnpickler.load().
    """
    return _unpickle_context.__dict__.get("namespace")


def _reduce_namespace(ns: Namespace) -> tuple[object, tuple[()]]:
    """
    Reduce function for Namespace objects registered in ASTPickler.dispatch_table.
    All Namespace references in a cached file point to the same namespace, so we
    always reconstruct via _restore_namespace() with no arguments.
    """
    return (_restore_namespace, ())


class ASTPickler(Pickler):
    """
    Custom pickler that replaces Namespace object references with a lightweight
    reconstruct call, avoiding pickling the full Namespace graph.

    Uses dispatch_table (C-level type lookup) instead of persistent_id (Python
    callback per object) for significantly lower pickling overhead.
    """

    def __init__(self, file: BytesIO, protocol: Optional[int] = None) -> None:
        super().__init__(file, protocol=protocol)
        # Register the Namespace reducer. The C pickler checks dispatch_table
        # only for matching types, so non-Namespace objects incur no Python overhead.
        self.dispatch_table = {Namespace: _reduce_namespace}  # type: ignore[dict-item]


class ASTUnpickler(Unpickler):
    def __init__(self, file: BytesIO, namespace: Namespace) -> None:
        super().__init__(file)
        self.namespace = namespace

    def load(self) -> object:
        # Store the target namespace in a thread-local so _restore_namespace()
        # can access it without being passed as an argument (which would require
        # pickling the namespace name and looking it up by name).
        _unpickle_context.namespace = self.namespace
        try:
            return super().load()
        finally:
            # Clean up the thread-local to avoid holding a reference.
            try:
                del _unpickle_context.namespace
            except AttributeError:
                pass
