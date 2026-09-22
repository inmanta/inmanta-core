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


class ModelVersionListener(abc.ABC):
    """
    Base class for listeners on the model versions written to an environment.

    Unlike the compile and environment listeners, this one takes part in the transaction that writes the resources: it
    is handed that transaction's connection, and aborts the export (and the transaction) if an exception is raised.
    """

    @abc.abstractmethod
    async def notify_new_model_version(
        self,
        environment: uuid.UUID,
        version: int,
        new_or_updated_resource_sets: Set[uuid.UUID],
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Called when a new model version has been written, before the transaction commits.

        The configurationmodel row for this version is in place, and so are the resource, resource_set and
        resource_set_configuration_model rows for these resource sets, so a listener may reference any of them.

        :param environment: The environment the model version was written on.
        :param version: The model version that was written.
        :param new_or_updated_resource_sets: The ids of the resource sets that were newly inserted or updated for this version.
            A named set that was linked to this version unchanged is not included, because its resources did not change.
            The shared set is the exception. It always gets a new resource_set_id on every partial compile.
        :param connection: The connection of the transaction that wrote the resources. The listener must use it, and
            must not commit or roll it back.
        """
