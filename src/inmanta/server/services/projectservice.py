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
from inmanta.protocol import methods
from inmanta.protocol.exceptions import NotFound, ServerError
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_PROJECT, SLICE_RESOURCE, SLICE_SERVER, protocol
from inmanta.server.agentmanager import AgentManager
from inmanta.server.server import Server
from inmanta.server.services.resourceservice import ResourceService
from inmanta.types import Apireturn

LOGGER = logging.getLogger(__name__)


class ProjectService(protocol.ServerSlice):
    """Slice with project and environment management"""

    server_slice: Server
    agentmanager: AgentManager
    resource_service: ResourceService

    def __init__(self) -> None:
        super(ProjectService, self).__init__(SLICE_PROJECT)

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AGENT_MANAGER]

    async def prestart(self, server: protocol.Server) -> None:
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))
        self.agentmanager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

    # Project handlers
    @protocol.handle(methods.create_project)
    async def create_project(self, name: str, project_id: Optional[uuid.UUID]) -> Apireturn:
        if project_id is None:
            project_id = uuid.uuid4()
        try:
            project = data.Project(id=project_id, name=name)
            await project.insert()
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError(f"A project with name {name} already exists.")

        return 200, {"project": project}

    @protocol.handle(methods.delete_project, project_id="id")
    async def delete_project(self, project_id: uuid.UUID) -> None:
        project = await data.Project.get_by_id(project_id)
        if project is None:
            raise NotFound("The project with given id does not exist.")

        environments = await data.Environment.get_list(project=project.id)
        for env in environments:
            await asyncio.gather(self.agentmanager.stop_agents(env), env.delete_cascade())
            self.resource_service.close_resource_action_logger(env.id)

        await project.delete()

    @protocol.handle(methods.modify_project, project_id="id")
    async def modify_project(self, project_id: uuid.UUID, name: str) -> Apireturn:
        try:
            project = await data.Project.get_by_id(project_id)
            if project is None:
                raise NotFound("The project with given id does not exist.")

            await project.update_fields(name=name)

            return 200, {"project": project}

        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError(f"A project with name {name} already exists.")

    @protocol.handle(methods.list_projects)
    async def list_projects(self) -> Apireturn:
        projects = await data.Project.get_list()
        return 200, {"projects": projects}

    @protocol.handle(methods.get_project, project_id="id")
    async def get_project(self, project_id: uuid.UUID) -> Apireturn:
        try:
            project = await data.Project.get_by_id(project_id)
            environments = await data.Environment.get_list(project=project_id)

            if project is None:
                raise NotFound("The project with given id does not exist.")

            project_dict = project.to_dict()
            project_dict["environments"] = [e.id for e in environments]

            return 200, {"project": project_dict}
        except ValueError:
            raise NotFound("The project with given id does not exist.")
