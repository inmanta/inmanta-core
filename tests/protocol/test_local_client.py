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

from inmanta import protocol
from inmanta.postgresproc import PostgresProc
from inmanta.server.protocol import LocalClient, Server, ServerSlice
from utils import configure


async def test_local_client(unused_tcp_port: int, postgres_db: PostgresProc, database_name: str, async_finalizer) -> None:
    """Test methods with simple return types"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<name>", operation="POST", client_types=["api"])
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
