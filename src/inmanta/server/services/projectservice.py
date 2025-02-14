"""
    Copyright 2019 Inmanta

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

import logging
import uuid
from typing import Optional, cast

import asyncpg

from inmanta import data
from inmanta.data import model
from inmanta.graphql.models import Environment, Project
from inmanta.graphql.schema import get_async_session
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.exceptions import Conflict, NotFound, ServerError
from inmanta.server import (
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_PROJECT,
    SLICE_RESOURCE,
    SLICE_TRANSPORT,
    protocol,
)
from inmanta.server.agentmanager import AutostartedAgentManager
from inmanta.server.services.resourceservice import ResourceService
from inmanta.types import Apireturn, JsonType
from sqlalchemy import insert, select

LOGGER = logging.getLogger(__name__)


class ProjectService(protocol.ServerSlice):
    """Slice with project and environment management"""

    autostarted_agent_manager: AutostartedAgentManager
    resource_service: ResourceService

    def __init__(self) -> None:
        super().__init__(SLICE_PROJECT)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE, SLICE_RESOURCE, SLICE_AUTOSTARTED_AGENT_MANAGER]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

    # v1 handlers
    @handle(methods.create_project)
    async def create_project(self, name: str, project_id: Optional[uuid.UUID]) -> Apireturn:
        return 200, {"project": await self.project_create(name, project_id)}

    @handle(methods.delete_project, project_id="id", api_version=1)
    async def delete_project(self, project_id: uuid.UUID) -> Apireturn:
        await self.project_delete(project_id)
        return 200

    @handle(methods.modify_project, project_id="id")
    async def modify_project(self, project_id: uuid.UUID, name: str) -> Apireturn:
        return 200, {"project": (await self.project_modify(project_id, name)).model_dump()}

    @handle(methods.list_projects)
    async def list_projects(self) -> Apireturn:
        async with get_async_session() as session:
            # stmt = select(Project)
            stmt = select(Project.id, Project.name, Environment.id).join(Project.environments)
            # stmt = select(Project.id, Project.name, Project.environments)
            rt = await session.execute(stmt)
            # project_list: list[JsonType] = [row._mapping for row in rt.all()]

            project_list: list[JsonType] = rt.all()
            # project_list: list[JsonType] = [rst.to_dict() for rst in rt.mappings().all()]

        def to_dict(pj_row_result):
            return {
                "id": str(pj_row_result.id),
                "name": str(pj_row_result.name),
                # 'environments': [str(pj_row_result.name),
            }

        return 200, {"projects": [to_dict(pj) for pj in project_list]}

    @handle(methods.get_project, project_id="id")
    async def get_project(self, project_id: uuid.UUID) -> Apireturn:
        project_model = (await self.project_get(project_id)).model_dump()
        project_model["environments"] = [e.id for e in await data.Environment.get_list(project=project_id)]
        return 200, {"project": project_model}

    # v2 handlers
    @handle(methods_v2.project_create)
    async def project_create(self, name: str, project_id: Optional[uuid.UUID]) -> model.Project:
        if project_id is None:
            project_id = uuid.uuid4()

        stmt = insert(Project)
        data = {"id": project_id, "name": name}

        async with get_async_session() as session:
            await session.execute(stmt, data)
            await session.commit()

        return data

    @handle(methods_v2.project_delete, project_id="id", api_version=2)
    async def project_delete(self, project_id: uuid.UUID) -> None:
        project = await data.Project.get_by_id(project_id)
        if project is None:
            raise NotFound("The project with given id does not exist.")

        environments = await data.Environment.get_list(project=project.id)
        if len(environments) > 0:
            raise Conflict(
                f"Cannot remove the project `{project_id}` because it still contains some environments: "
                f"{','.join([str((env.name, str(env.id))) for env in environments])}"
            )

        await project.delete()

    @handle(methods_v2.project_modify, project_id="id")
    async def project_modify(self, project_id: uuid.UUID, name: str) -> model.Project:
        try:
            project = await data.Project.get_by_id(project_id)
            if project is None:
                raise NotFound("The project with given id does not exist.")

            await project.update_fields(name=name)

            return project.to_dto()

        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError(f"A project with name {name} already exists.")

    @handle(methods_v2.project_list)
    async def project_list(self, environment_details: bool = False) -> list[model.Project]:
        project_list = []

        for project in await data.Project.get_list(order_by_column="name", order="ASC"):
            project_model = project.to_dto()
            project_model.environments = [
                e.to_dto()
                for e in await data.Environment.get_list(
                    project=project.id, details=environment_details, order_by_column="name", order="ASC"
                )
            ]

            project_list.append(project_model)

        return project_list

    @handle(methods_v2.project_get, project_id="id")
    async def project_get(self, project_id: uuid.UUID, environment_details: bool = False) -> model.Project:
        project = await data.Project.get_by_id(project_id)

        if project is None:
            raise NotFound("The project with given id does not exist.")

        project_model = project.to_dto()
        project_model.environments = [
            e.to_dto() for e in await data.Environment.get_list(project=project.id, details=environment_details)
        ]

        return project_model
