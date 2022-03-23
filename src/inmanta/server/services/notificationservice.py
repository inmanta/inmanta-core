"""
    Copyright 2022 Inmanta

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
import datetime
import logging
import uuid
from typing import Dict, List, Optional, Tuple, cast

from asyncpg import Connection

from inmanta import const, data
from inmanta.data import APILIMIT, InvalidSort, NotificationOrder, QueryType
from inmanta.data.model import Notification
from inmanta.data.paging import NotificationPagingCountsProvider, NotificationPagingHandler, QueryIdentifier
from inmanta.protocol import handle, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_NOTIFICATION, SLICE_TRANSPORT, protocol
from inmanta.server.services.compilerservice import CompilerService, CompileStateListener
from inmanta.server.validate_filter import InvalidFilter, NotificationFilterValidator

LOGGER = logging.getLogger(__name__)


class NotificationService(protocol.ServerSlice, CompileStateListener):
    """Slice for notification management"""

    _compiler_service: CompilerService

    def __init__(self) -> None:
        super(NotificationService, self).__init__(SLICE_NOTIFICATION)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_COMPILER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self._compiler_service = cast(CompilerService, server.get_slice(SLICE_COMPILER))
        self._compiler_service.add_listener(self)

    async def start(self) -> None:
        await super().start()
        self.schedule(self._cleanup, 3600, initial_delay=0)

    async def _cleanup(self) -> None:
        await data.Notification.clean_up_notifications()

    async def compile_done(self, compile: data.Compile) -> None:
        if not compile.success and compile.do_export:
            await self.notify(
                compile.environment,
                title="Compilation failed",
                message="An exporting compile has failed",
                severity=const.NotificationSeverity.error,
                uri=f"/api/v2/compilereport/{compile.id}",
            )

    async def notify(
        self,
        environment: uuid.UUID,
        title: str,
        message: str,
        uri: str,
        severity: const.NotificationSeverity = const.NotificationSeverity.message,
        connection: Optional[Connection] = None,
    ) -> None:
        """Internal API to create a new notification
        :param environment: The environment this notification belongs to
        :param title: The title of the notification
        :param message: The actual text of the notification
        :param severity: The severity of the notification
        :param uri: A link to an api endpoint of the server, that is relevant to the message,
                    and can be used to get further information about the problem.
                    For example a compile related problem should have the uri: `/api/v2/compilereport/<compile_id>`
        """
        await data.Notification(
            environment=environment,
            title=title,
            message=message,
            uri=uri,
            severity=severity,
            created=datetime.datetime.now().astimezone(),
        ).insert(connection)

    @handle(methods_v2.list_notifications, env="tid")
    async def list_notifications(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "created.desc",
    ) -> ReturnValue[List[Notification]]:
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(NotificationFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e

        try:
            notification_order = NotificationOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e

        try:
            dtos = await data.Notification.list_notifications(
                database_order=notification_order,
                limit=limit,
                environment=env.id,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                connection=None,
                **query,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = NotificationPagingHandler(NotificationPagingCountsProvider())
        metadata = await paging_handler.prepare_paging_metadata(
            QueryIdentifier(environment=env.id), dtos, query, limit, notification_order
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            filter,
            notification_order,
            limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )

        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

    @handle(methods_v2.get_notification, env="tid")
    async def get_notification(
        self,
        env: data.Environment,
        notification_id: uuid.UUID,
    ) -> Notification:
        notification = await data.Notification.get_one(environment=env.id, id=notification_id)
        if not notification:
            raise NotFound(f"Notification with id {notification_id} not found")
        return notification.to_dto()

    @handle(methods_v2.update_notification, env="tid")
    async def update_notification(
        self,
        env: data.Environment,
        notification_id: uuid.UUID,
        read: Optional[bool] = None,
        cleared: Optional[bool] = None,
    ) -> Notification:
        notification = await data.Notification.get_one(environment=env.id, id=notification_id)
        if not notification:
            raise NotFound(f"Notification with id {notification_id} not found")
        if read is not None and cleared is not None:
            await notification.update(read=read, cleared=cleared)
        elif read is not None:
            await notification.update(read=read)
        elif cleared is not None:
            await notification.update(cleared=cleared)
        else:
            raise BadRequest("At least one of {read, cleared} should be specified for a valid update")
        return notification.to_dto()
