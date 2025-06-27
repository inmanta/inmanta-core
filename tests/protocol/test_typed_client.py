"""
Copyright 2024 Inmanta

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

import uuid

import pytest

from inmanta import const, protocol
from inmanta.data.model import BaseModel
from inmanta.protocol import exceptions
from inmanta.protocol.auth.decorators import auth
from inmanta.server.protocol import LocalClient, Server, ServerSlice, common


async def test_local_client(server_config, async_finalizer) -> None:
    """Test the local client"""

    class ProjectServer(ServerSlice):
        @auth(auth_label=const.AuthorizationLabel.TEST, read_only=False)
        @protocol.typedmethod(path="/test/<name>", operation="POST", client_types=[const.ClientType.api])
        def test_method(name: str, project: str) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_methodY(self, name: str, project: str) -> str:  # NOQA
            return f"{name} -> {project}"

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = LocalClient("client", rs)
    response = await client.test_method(name="y", project="x")
    assert response == "y -> x"


async def test_return_types(server_config, async_finalizer):
    """
    Test the use and validation of methods that use common.ReturnValue
    """

    class Project(BaseModel):
        id: uuid.UUID
        name: str

    class ProjectServer(ServerSlice):
        @auth(auth_label=const.AuthorizationLabel.TEST, read_only=False)
        @protocol.typedmethod(path="/test", operation="POST", client_types=[const.ClientType.api], envelope_key="response")
        def test_method(project: Project) -> common.ReturnValue[Project]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, project: Project) -> common.ReturnValue[Project]:
            new_project = project.copy()
            return common.ReturnValue(response=new_project)

        @auth(auth_label=const.AuthorizationLabel.TEST, read_only=False)
        @protocol.typedmethod(path="/test2", operation="POST", client_types=[const.ClientType.api])
        def test_method2(project: Project) -> Project:  # NOQA
            pass

        @protocol.handle(test_method2)
        async def test_method2(self, project: Project) -> Project:
            if project.name == "error":
                raise exceptions.NotFound()
            return project

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.TypedClient("client")
    obj_id = uuid.uuid4()

    obj = await client.test_method(Project(name="test", id=obj_id))
    assert obj
    assert obj.id == obj_id
    assert obj.name == "test"

    obj = await client.test_method2(Project(name="test", id=obj_id))
    assert obj
    assert obj.id == obj_id
    assert obj.name == "test"

    with pytest.raises(exceptions.NotFound):
        await client.test_method2(Project(name="error", id=obj_id))
