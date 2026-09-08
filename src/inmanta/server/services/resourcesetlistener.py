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
"""

import abc
import uuid
from collections import abc as collections_abc

import asyncpg


class ResourceSetListener(abc.ABC):
    """
    Base class for listeners on the resources of a model version being written.

    Unlike the compile and environment listeners, this one takes part in the transaction that writes the resources: it
    is handed that transaction's connection, and an exception it raises aborts the export. A listener that cannot
    offer that guarantee does not belong here, because whatever it maintains would then be committed out of step with
    the resources it is derived from.
    """

    @abc.abstractmethod
    async def resource_sets_written(
        self,
        environment: uuid.UUID,
        model_version: int,
        resource_sets: collections_abc.Set[uuid.UUID],
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Called when the resources of a model version have been written, before the transaction commits.

        :param environment: The environment the resources were written for.
        :param model_version: The model version the resource sets were linked to.
        :param resource_sets: The ids of the resource sets that were newly inserted for this version. A resource set
            that was carried over from the base version unchanged is not included: its resources did not change.
        :param connection: The connection of the transaction that wrote the resources. The listener must use it, and
            must not commit or roll it back.
        """
