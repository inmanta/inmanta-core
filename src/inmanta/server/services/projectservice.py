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
import asyncio
import logging
import uuid
from typing import List, Optional, cast

import asyncpg

from inmanta import data
from inmanta.data import model
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.exceptions import NotFound, ServerError
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

LOGGER = logging.getLogger(__name__)


class ProjectService(protocol.ServerSlice):
    """Slice with project and environment management"""

    autostarted_agent_manager: AutostartedAgentManager
    resource_service: ResourceService

    def __init__(self) -> None:
        super(ProjectService, self).__init__(SLICE_PROJECT)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_RESOURCE, SLICE_AUTOSTARTED_AGENT_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

    # v1 handlers
    @handle(methods.create_project)
    async def create_project(self, name: str, project_id: Optional[uuid.UUID]) -> Apireturn:
        return 200, {"project": (await self.project_create(name, project_id)).dict()}

    @handle(methods.delete_project, project_id="id", api_version=1)
    async def delete_project(self, project_id: uuid.UUID) -> Apireturn:
        await self.project_delete(project_id)
        return 200

    @handle(methods.modify_project, project_id="id")
    async def modify_project(self, project_id: uuid.UUID, name: str) -> Apireturn:
        return 200, {"project": (await self.project_modify(project_id, name)).dict()}

    @handle(methods.list_projects)
    async def list_projects(self) -> Apireturn:
        project_list: List[JsonType] = [x.dict() for x in await self.project_list()]
        for project in project_list:
            project["environments"] = [x["id"] for x in project["environments"]]
        return 200, {"projects": project_list}

    @handle(methods.get_project, project_id="id")
    async def get_project(self, project_id: uuid.UUID) -> Apireturn:
        project_model = (await self.project_get(project_id)).dict()
        project_model["environments"] = [e.id for e in await data.Environment.get_list(project=project_id)]
        return 200, {"project": project_model}

    # v2 handlers
    @handle(methods_v2.project_create)
    async def project_create(self, name: str, project_id: Optional[uuid.UUID]) -> model.Project:
        if project_id is None:
            project_id = uuid.uuid4()

        try:
            project = data.Project(id=project_id, name=name)
            await project.insert()
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError(f"A project with name {name} already exists.")

        return project.to_dto()

    @handle(methods_v2.project_delete, project_id="id", api_version=2)
    async def project_delete(self, project_id: uuid.UUID) -> None:
        project = await data.Project.get_by_id(project_id)
        if project is None:
            raise NotFound("The project with given id does not exist.")

        environments = await data.Environment.get_list(project=project.id)
        for env in environments:
            await asyncio.gather(self.autostarted_agent_manager.stop_agents(env), env.delete_cascade())
            self.resource_service.close_resource_action_logger(env.id)

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
    async def project_list(self, environment_details: bool = False) -> List[model.Project]:
        project_list = []

        for project in await data.Project.get_list():
            project_model = project.to_dto()
            project_model.environments = [
                e.to_dto() for e in await data.Environment.get_list(project=project.id, details=environment_details)
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
