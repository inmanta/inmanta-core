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
from collections.abc import Set

import asyncpg


class ResourceSetListener(abc.ABC):
    """
    Base class for listeners on the resources of a model version being written.

    Unlike the compile and environment listeners, this one takes part in the transaction that writes the resources: it
    is handed that transaction's connection, and an exception it raises aborts the export. A listener that cannot
    offer that guarantee does not belong here, because whatever it maintains would then be committed out of step with
    the resources it is derived from.

    The counterpart to that guarantee is the cost: a listener runs inside the transaction, on the critical path of
    every export. Its work is added to the duration of every export and to the time the resource and resource_set rows
    stay locked, so it should stay proportional to the resource sets it is handed rather than to the size of the
    environment.
    """

    @abc.abstractmethod
    async def resource_sets_written(
        self,
        environment: uuid.UUID,
        model_version: int,
        resource_sets: Set[uuid.UUID],
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Called when the resources of a model version have been written, before the transaction commits.

        The configurationmodel row for this version is in place, and so are the resource, resource_set and
        resource_set_configuration_model rows for these resource sets, so a listener may reference any of them. The
        version is not finished being written, though: its total is not yet final and its unknown parameters are not
        yet inserted.

        :param environment: The environment the resources were written for.
        :param model_version: The model version the resource sets were linked to.
        :param resource_sets: The ids of the resource sets that were newly inserted for this version. A named set that
            was linked to this version unchanged is not included, because its resources did not change. The shared
            set, the one whose name is null, is the exception: a partial export carries its resources over by
            exporting them again, so whenever there are any it is written under a new id and reported, even though
            none of them changed.
        :param connection: The connection of the transaction that wrote the resources. The listener must use it, and
            must not commit or roll it back.
        """
