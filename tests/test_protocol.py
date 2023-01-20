"""
    Copyright 2018 Inmanta

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
import base64
import datetime
import json
import os
import random
import threading
import time
import urllib.parse
import uuid
from enum import Enum
from itertools import chain
from typing import Any, Dict, Iterator, List, Optional, Union

import pydantic
import pytest
import tornado
from pydantic.types import StrictBool
from tornado import gen, web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from inmanta import config, const, protocol
from inmanta.const import ClientType
from inmanta.data.model import BaseModel
from inmanta.protocol import VersionMatch, exceptions, json_encode
from inmanta.protocol.common import (
    HTML_CONTENT,
    HTML_CONTENT_WITH_UTF8_CHARSET,
    OCTET_STREAM_CONTENT,
    ZIP_CONTENT,
    ArgOption,
    InvalidMethodDefinition,
    InvalidPathException,
    MethodProperties,
    Result,
    ReturnValue,
)
from inmanta.protocol.methods import ENV_OPTS
from inmanta.protocol.rest import CallArguments
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.server import config as opt
from inmanta.server.config import server_bind_port
from inmanta.server.protocol import Server, ServerSlice
from inmanta.types import Apireturn
from inmanta.util import hash_file
from utils import configure


def make_random_file(size=0):
    """
    Generate a random file.

    :param size: If size is > 0 content is generated that is equal or more than size.
    """
    randomvalue = str(random.randint(0, 10000))
    if size > 0:
        while len(randomvalue) < size:
            randomvalue += randomvalue

    content = ("Hello world %s\n" % (randomvalue)).encode()
    hash = hash_file(content)

    body = base64.b64encode(content).decode("ascii")

    return (hash, content, body)


async def test_client_files(client):
    (hash, content, body) = make_random_file()

    # Check if the file exists
    result = await client.stat_file(id=hash)
    assert result.code == 404

    # Create the file
    result = await client.upload_file(id=hash, content=body)
    assert result.code == 200

    # Get the file
    result = await client.get_file(id=hash)
    assert result.code == 200
    assert "content" in result.result
    assert result.result["content"] == body


async def test_client_files_lost(client):
    (hash, content, body) = make_random_file()

    # Get the file
    result = await client.get_file(id=hash)
    assert result.code == 404


async def test_sync_client_files(client):
    # work around for https://github.com/pytest-dev/pytest-asyncio/issues/168
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

    done = []
    limit = 100
    sleep = 0.01

    def do_test():
        sync_client = protocol.SyncClient("client")

        (hash, content, body) = make_random_file()

        # Check if the file exists
        result = sync_client.stat_file(id=hash)
        assert result.code == 404

        # Create the file
        result = sync_client.upload_file(id=hash, content=body)
        assert result.code == 200

        # Get the file
        result = sync_client.get_file(id=hash)
        assert result.code == 200
        assert "content" in result.result
        assert result.result["content"] == body

        done.append(True)

    thread = threading.Thread(target=do_test)
    thread.start()

    while len(done) == 0 and limit > 0:
        await gen.sleep(sleep)
        limit -= 1

    thread.join()
    assert len(done) > 0


async def test_client_files_stat(client):

    file_names = []
    i = 0
    while i < 10:
        (hash, content, body) = make_random_file()
        if hash not in file_names:
            file_names.append(hash)
            result = await client.upload_file(id=hash, content=body)
            assert result.code == 200
            i += 1

    result = await client.stat_files(files=file_names)
    assert len(result.result["files"]) == 0

    other_files = ["testtest"]
    result = await client.stat_files(files=file_names + other_files)
    assert len(result.result["files"]) == len(other_files)


async def test_diff(client):
    ca = "Hello world\n".encode()
    ha = hash_file(ca)
    result = await client.upload_file(id=ha, content=base64.b64encode(ca).decode("ascii"))
    assert result.code == 200

    cb = "Bye bye world\n".encode()
    hb = hash_file(cb)
    result = await client.upload_file(id=hb, content=base64.b64encode(cb).decode("ascii"))
    assert result.code == 200

    diff = await client.diff(ha, hb)
    assert diff.code == 200
    assert len(diff.result["diff"]) == 5

    diff = await client.diff(0, hb)
    assert diff.code == 200
    assert len(diff.result["diff"]) == 4

    diff = await client.diff(ha, 0)
    assert diff.code == 200
    assert len(diff.result["diff"]) == 4


async def test_client_files_bad(server, client):
    (hash, content, body) = make_random_file()
    # Create the file
    result = await client.upload_file(id=hash + "a", content=body)
    assert result.code == 400


async def test_client_files_corrupt(client):
    (hash, content, body) = make_random_file()
    # Create the file
    result = await client.upload_file(id=hash, content=body)
    assert result.code == 200

    state_dir = opt.state_dir.get()

    file_dir = os.path.join(state_dir, "server", "files")

    file_name = os.path.join(file_dir, hash)

    with open(file_name, "wb+") as fd:
        fd.write("Haha!".encode())

    opt.server_delete_currupt_files.set("false")
    result = await client.get_file(id=hash)
    assert result.code == 500

    result = await client.upload_file(id=hash, content=body)
    assert result.code == 500

    opt.server_delete_currupt_files.set("true")
    result = await client.get_file(id=hash)
    assert result.code == 500

    result = await client.upload_file(id=hash, content=body)
    assert result.code == 200


async def test_gzip_encoding(server):
    """
    Test if the server accepts gzipped encoding and returns gzipped encoding.
    """
    (hash, content, body) = make_random_file(size=1024)

    port = opt.get_bind_port()
    url = "http://localhost:%s/api/v1/file/%s" % (port, hash)

    zipped, body = protocol.gzipped_json({"content": body})
    assert zipped

    request = HTTPRequest(
        url=url,
        method="PUT",
        headers={"Accept-Encoding": "gzip", "Content-Encoding": "gzip"},
        body=body,
        decompress_response=True,
    )
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200

    request = HTTPRequest(url=url, method="GET", headers={"Accept-Encoding": "gzip"}, decompress_response=True)
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200
    assert response.headers["X-Consumed-Content-Encoding"] == "gzip"


class MainHandler(web.RequestHandler):
    def get(self):
        time.sleep(1.1)


@pytest.fixture(scope="function")
async def app(unused_tcp_port):
    http_app = web.Application([(r"/api/v1/file/abc", MainHandler)])
    server = tornado.httpserver.HTTPServer(http_app)
    server.bind(unused_tcp_port)
    server.start()
    yield server

    server.stop()
    await server.close_all_connections()


async def test_timeout_error(app):
    """
    Test test verifies that the protocol client can handle requests that timeout. This means it receives a http error
    status that is not generated by the server but by the client.
    """
    from inmanta.config import Config

    Config.load_config()

    port = str(list(app._sockets.values())[0].getsockname()[1])
    Config.set("client_rest_transport", "port", port)
    Config.set("client_rest_transport", "request_timeout", "1")

    from inmanta import protocol

    client = protocol.Client("client")
    x = await client.get_file(id="abc")

    assert x.code == 599
    assert "message" in x.result


async def test_method_properties():
    """
    Test method properties decorator and helper functions
    """

    @protocol.method(path="/test", operation="PUT", client_types=["api"], api_prefix="x", api_version=2)
    def test_method(name):
        """
        Create a new project
        """

    props = protocol.common.MethodProperties.methods["test_method"][0]
    assert "Authorization" in props.get_call_headers()
    assert props.get_listen_url() == "/x/v2/test"
    assert props.get_call_url({}) == "/x/v2/test"


async def test_invalid_client_type():
    """
    Test invalid client ype
    """
    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.method(path="/test", operation="PUT", client_types=["invalid"])
        def test_method(name):
            """
            Create a new project
            """

        assert "Invalid client type invalid specified for function" in str(e)


async def test_call_arguments_defaults():
    """
    Test processing RPC messages
    """

    @protocol.method(path="/test", operation="PUT", client_types=["api"])
    def test_method(name: str, value: int = 10):
        """
        Create a new project
        """

    call = CallArguments(protocol.common.MethodProperties.methods["test_method"][0], {"name": "test"}, {})
    await call.process()

    assert call.call_args["name"] == "test"
    assert call.call_args["value"] == 10


def test_create_client():
    with pytest.raises(AssertionError):
        protocol.SyncClient("agent", "120")

    with pytest.raises(AssertionError):
        protocol.Client("agent", "120")


async def test_pydantic():
    """
    Test validating pydantic objects
    """

    class Project(BaseModel):
        id: uuid.UUID
        name: str

    @protocol.method(path="/test", operation="PUT", client_types=["api"])
    def test_method(project: Project):
        """
        Create a new project
        """

    id = uuid.uuid4()
    call = CallArguments(
        protocol.common.MethodProperties.methods["test_method"][0], {"project": {"name": "test", "id": str(id)}}, {}
    )
    await call.process()

    project = call.call_args["project"]
    assert project.name == "test"
    assert project.id == id

    with pytest.raises(exceptions.BadRequest):
        call = CallArguments(
            protocol.common.MethodProperties.methods["test_method"][0], {"project": {"name": "test", "id": "abcd"}}, {}
        )
        await call.process()


def test_pydantic_json():
    """
    Test running pydanyic objects through the json encoder
    """

    class Options(str, Enum):
        yes = "yes"
        no = "no"

    class Project(BaseModel):
        id: uuid.UUID
        name: str
        opts: Options

    project = Project(id=uuid.uuid4(), name="test", opts="no")
    assert project.opts == Options.no

    json_string = json_encode(project)
    data = json.loads(json_string)

    assert "id" in data
    assert "name" in data
    assert data["id"] == str(project.id)
    assert data["name"] == "test"

    # Now create the project again
    new = Project(**data)

    assert project == new
    assert project is not new


async def test_pydantic_alias(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Round trip test on aliased object
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        source: str
        validate_: bool

        class Config:
            fields = {"validate_": {"alias": "validate"}}

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(project: Project) -> ReturnValue[Project]:  # NOQA
            """
            Create a new project
            """

        @protocol.typedmethod(path="/test2", operation="POST", client_types=["api"])
        def test_method2(project: List[Project]) -> ReturnValue[List[Project]]:  # NOQA
            """
            Create a new project
            """

        @protocol.handle(test_method)
        async def test_methodi(self, project: Project) -> ReturnValue[Project]:
            new_project = project.copy()

            return ReturnValue(response=new_project)

        @protocol.handle(test_method2)
        async def test_method2i(self, project: List[Project]) -> ReturnValue[List[Project]]:

            return ReturnValue(response=project)

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")

    projectt = Project(id=uuid.uuid4(), source="test", validate=True)
    assert projectt.validate_ is True
    projectf = Project(id=uuid.uuid4(), source="test", validate=False)
    assert projectf.validate_ is False

    async def roundtrip(obj: Project) -> None:
        data = await client.test_method(obj)
        assert obj.validate_ == data.result["data"]["validate"]

        data = await client.test_method2([obj])
        assert obj.validate_ == data.result["data"][0]["validate"]

    await roundtrip(projectf)
    await roundtrip(projectt)


async def test_return_non_warnings(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test return none but pushing warnings
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(name: str) -> ReturnValue[None]:  # NOQA
            """
            Create a new project
            """

        @protocol.handle(test_method)
        async def test_method_handler(self, name) -> ReturnValue[None]:
            rv = ReturnValue()
            rv.add_warnings(["error1", "error2"])
            return rv

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")

    response = await client.test_method("x")
    assert response.code == 200
    assert "data" in response.result
    assert response.result["data"] is None
    assert "metadata" in response.result
    assert "warnings" in response.result["metadata"]
    assert "error1" in response.result["metadata"]["warnings"]


async def test_invalid_handler():
    """
    Handlers should be async
    """
    with pytest.raises(ValueError):

        class ProjectServer(ServerSlice):
            @protocol.method(path="/test", operation="POST", client_types=["api"])
            def test_method(self):
                """
                Create a new project
                """

            @protocol.handle(test_method)
            def test_method(self):
                return


async def test_return_value(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test the use and validation of methods that use common.ReturnValue
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        id: uuid.UUID
        name: str

    class ProjectServer(ServerSlice):
        @protocol.method(path="/test", operation="POST", client_types=["api"])
        def test_method(project: Project) -> ReturnValue[Project]:  # NOQA
            """
            Create a new project
            """

        @protocol.handle(test_method)
        async def test_method(self, project: Project) -> ReturnValue[Project]:
            new_project = project.copy()

            return ReturnValue(response=new_project)

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "id" in result.result
    assert "name" in result.result


async def test_return_model(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test the use and validation of methods that use common.ReturnValue
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        id: uuid.UUID
        name: str

    class ProjectServer(ServerSlice):
        @protocol.method(path="/test", operation="POST", client_types=["api"])
        def test_method(project: Project) -> Project:  # NOQA
            """
            Create a new project
            """

        @protocol.method(path="/test2", operation="POST", client_types=["api"])
        def test_method2(project: Project) -> None:  # NOQA
            pass

        @protocol.method(path="/test3", operation="POST", client_types=["api"])
        def test_method3(project: Project) -> None:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, project: Project) -> Project:
            new_project = project.copy()

            return new_project

        @protocol.handle(test_method2)
        async def test_method2(self, project: Project) -> None:
            pass

        @protocol.handle(test_method3)
        async def test_method3(self, project: Project) -> None:
            return 1

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "id" in result.result
    assert "name" in result.result

    result = await client.test_method2({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    result = await client.test_method3({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 500


async def test_data_envelope(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test the use and validation of methods that use common.ReturnValue
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        id: uuid.UUID
        name: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(project: Project) -> ReturnValue[Project]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, project: Project) -> ReturnValue[Project]:
            new_project = project.copy()
            return ReturnValue(response=new_project)

        @protocol.typedmethod(path="/test2", operation="POST", client_types=["api"], envelope_key="method")
        def test_method2(project: Project) -> ReturnValue[Project]:  # NOQA
            pass

        @protocol.handle(test_method2)
        async def test_method2(self, project: Project) -> ReturnValue[Project]:
            new_project = project.copy()
            return ReturnValue(response=new_project)

        @protocol.method(path="/test3", operation="POST", client_types=["api"], envelope=True)
        def test_method3(project: Project):  # NOQA
            pass

        @protocol.handle(test_method3)
        async def test_method3(self, project: dict) -> Apireturn:
            return 200, {"id": 1, "name": 2}

        @protocol.method(path="/test4", operation="POST", client_types=["api"], envelope=True, envelope_key="project")
        def test_method4(project: Project):  # NOQA
            pass

        @protocol.handle(test_method4)
        async def test_method4(self, project: dict) -> Apireturn:
            return 200, {"id": 1, "name": 2}

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    # 1
    result = await client.test_method({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "data" in result.result
    assert "id" in result.result["data"]
    assert "name" in result.result["data"]

    # 2
    result = await client.test_method2({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "method" in result.result
    assert "id" in result.result["method"]
    assert "name" in result.result["method"]

    # 3
    result = await client.test_method3({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "data" in result.result
    assert "id" in result.result["data"]
    assert "name" in result.result["data"]

    # 4
    result = await client.test_method4({"name": "test", "id": str(uuid.uuid4())})
    assert result.code == 200

    assert "project" in result.result
    assert "id" in result.result["project"]
    assert "name" in result.result["project"]


async def test_invalid_paths():
    """
    Test path validation
    """
    with pytest.raises(InvalidPathException) as e:

        @protocol.method(path="test", operation="PUT", client_types=["api"], api_prefix="x", api_version=2)
        def test_method(name):
            pass

    assert "test should start with a /" == str(e.value)

    with pytest.raises(InvalidPathException) as e:

        @protocol.method(path="/test/<othername>", operation="PUT", client_types=["api"], api_prefix="x", api_version=2)
        def test_method2(name):
            pass

    assert str(e.value).startswith("Variable othername in path /test/<othername> is not defined in function")


async def test_nested_paths(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test overlapping path definition"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<data>", operation="GET", client_types=["api"])
        def test_method(data: str) -> Project:  # NOQA
            pass

        @protocol.typedmethod(path="/test/<data>/config", operation="GET", client_types=["api"])
        def test_method2(data: str) -> Project:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: str) -> Project:
            # verify that URL encoded data is properly decoded
            assert "%20" not in data
            return Project(name="test_method")

        @protocol.handle(test_method2)
        async def test_method2(self, data: str) -> Project:
            return Project(name="test_method2")

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method({"data": "test "})
    assert result.code == 200
    assert "test_method" == result.result["data"]["name"]

    client = protocol.Client("client")
    result = await client.test_method2({"data": "test"})
    assert result.code == 200
    assert "test_method2" == result.result["data"]["name"]


async def test_list_basemodel_argument(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test list of basemodel arguments and primitive types"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(data: List[Project], data2: List[int]) -> Project:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: List[Project], data2: List[int]) -> Project:
            assert len(data) == 1
            assert data[0].name == "test"
            assert len(data2) == 3

            return Project(name="test_method")

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method(data=[{"name": "test"}], data2=[1, 2, 3])
    assert result.code == 200
    assert "test_method" == result.result["data"]["name"]


async def test_dict_basemodel_argument(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test dict of basemodel arguments and primitive types"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(data: Dict[str, Project], data2: Dict[str, int]) -> Project:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: Dict[str, Project], data2: Dict[str, int]) -> Project:
            assert len(data) == 1
            assert data["projectA"].name == "test"
            assert len(data2) == 3

            return Project(name="test_method")

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method(data={"projectA": {"name": "test"}}, data2={"1": 1, "2": 2, "3": 3})
    assert result.code == 200
    assert "test_method" == result.result["data"]["name"]


async def test_dict_with_optional_values(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test dict which may have None as a value"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    types = Union[pydantic.StrictInt, pydantic.StrictStr]

    class Result(BaseModel):
        val: Optional[types]

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(data: Dict[str, Optional[types]]) -> Result:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: Dict[str, Optional[types]]) -> Result:
            assert len(data) == 1
            assert "test" in data
            return Result(val=data["test"])

        @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
        def test_method2(data: Optional[str] = None) -> None:  # NOQA
            pass

        @protocol.handle(test_method2)
        async def test_method2(self, data: Optional[str] = None) -> None:
            assert data is None

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method(data={"test": None})
    assert result.code == 200
    assert result.result["data"]["val"] is None

    result = await client.test_method(data={"test": 5})
    assert result.code == 200
    assert result.result["data"]["val"] == 5

    result = await client.test_method(data={"test": "test123"})
    assert result.code == 200
    assert result.result["data"]["val"] == "test123"

    result = await client.test_method2()
    assert result.code == 200

    result = await client.test_method2(data=None)
    assert result.code == 200


async def test_dict_and_list_return(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test list of basemodel arguments"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(data: Project) -> List[Project]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: Project) -> List[Project]:  # NOQA
            return [Project(name="test_method")]

        @protocol.typedmethod(path="/test2", operation="POST", client_types=["api"])
        def test_method2(data: Project) -> List[str]:  # NOQA
            pass

        @protocol.handle(test_method2)
        async def test_method2(self, data: Project) -> List[str]:  # NOQA
            return ["test_method"]

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method(data={"name": "test"})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert "test_method" == result.result["data"][0]["name"]

    result = await client.test_method2(data={"name": "test"})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert "test_method" == result.result["data"][0]


async def test_method_definition():
    """
    Test typed methods with wrong annotations
    """
    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.typedmethod(path="/test", operation="PUT", client_types=["api"])
        def test_method1(name) -> None:
            """
            Create a new project
            """

    assert "has no type annotation." in str(e.value)

    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.typedmethod(path="/test", operation="PUT", client_types=["api"])
        def test_method2(name: Iterator[str]) -> None:
            """
            Create a new project
            """

    assert "Type typing.Iterator[str] of argument name can only be generic List, Dict or Literal" in str(e.value)

    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.typedmethod(path="/test", operation="PUT", client_types=["api"])
        def test_method3(name: List[object]) -> None:
            """
            Create a new project
            """

    assert (
        "Type object of argument name must be a either BaseModel, Enum, UUID, str, float, int, StrictNonIntBool, datetime, "
        "bytes or a List of these types or a Dict with str keys and values of these types."
    ) in str(e.value)

    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.typedmethod(path="/test", operation="PUT", client_types=["api"])
        def test_method4(name: Dict[int, str]) -> None:
            """
            Create a new project
            """

    assert "Type typing.Dict[int, str] of argument name must be a Dict with str keys and not int" in str(e.value)

    with pytest.raises(InvalidMethodDefinition) as e:

        @protocol.typedmethod(path="/test", operation="PUT", client_types=["api"])
        def test_method5(name: Dict[str, object]) -> None:
            """
            Create a new project
            """

    assert (
        "Type object of argument name must be a either BaseModel, Enum, UUID, str, float, int, StrictNonIntBool, datetime, "
        "bytes or a List of these types or a Dict with str keys and values of these types."
    ) in str(e.value)

    @protocol.typedmethod(path="/service_types/<service_type>", operation="DELETE", client_types=["api"])
    def lcm_service_type_delete(tid: uuid.UUID, service_type: str) -> None:
        """Delete an existing service type."""


def test_optional():
    @protocol.typedmethod(path="/service_types/<service_type>", operation="DELETE", client_types=["api"])
    def lcm_service_type_delete(tid: uuid.UUID, service_type: str, version: Optional[str] = None) -> None:
        """Delete an existing service type."""


async def test_union_types(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test use of union types"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    SimpleTypes = Union[float, int, StrictBool, str]  # NOQA
    AttributeTypes = Union[SimpleTypes, List[SimpleTypes], Dict[str, SimpleTypes]]  # NOQA

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
        def test_method(data: SimpleTypes, version: Optional[int] = None) -> List[SimpleTypes]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: SimpleTypes, version: Optional[int] = None) -> List[SimpleTypes]:  # NOQA
            if isinstance(data, list):
                return data
            return [data]

        @protocol.typedmethod(path="/testp", operation="POST", client_types=["api"])
        def test_methodp(data: AttributeTypes, version: Optional[int] = None) -> List[SimpleTypes]:  # NOQA
            pass

        @protocol.handle(test_methodp)
        async def test_methodp(self, data: AttributeTypes, version: Optional[int] = None) -> List[SimpleTypes]:  # NOQA
            if isinstance(data, list):
                return data
            return [data]

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")

    result = await client.test_methodp(data=[5], version=7)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert 5 == result.result["data"][0]

    result = await client.test_method(data=5, version=3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert 5 == result.result["data"][0]

    result = await client.test_method(data=5)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert 5 == result.result["data"][0]

    result = await client.test_method(data=5, version=7)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert 5 == result.result["data"][0]


async def test_basemodel_validation(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test validation of basemodel arguments and return, and how they are reported"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str
        value: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(data: Project) -> Project:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, data: Project) -> Project:  # NOQA
            return Project()

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")

    # Check validation of arguments
    result = await client.test_method(data={})
    assert result.code == 400
    assert "error_details" in result.result

    details = result.result["error_details"]["validation_errors"]
    assert len(details) == 2

    name = [d for d in details if d["loc"] == ["data", "name"]][0]
    value = [d for d in details if d["loc"] == ["data", "value"]][0]

    assert name["msg"] == "field required"
    assert value["msg"] == "field required"

    # Check the validation of the return value
    result = await client.test_method(data={"name": "X", "value": "Y"})
    assert result.code == 500
    assert "data validation error" in result.result["message"]


async def test_ACOA_header(server):
    """
    Test if the server accepts gzipped encoding and returns gzipped encoding.
    """
    port = opt.get_bind_port()
    url = f"http://localhost:{port}/api/v1/environment"

    request = HTTPRequest(url=url, method="GET")
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200
    assert response.headers.get("Access-Control-Allow-Origin") is None

    config.Config.set("server", "access-control-allow-origin", "*")
    response = await client.fetch(request)
    assert response.code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "*"


async def test_multi_version_method(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test multi version methods"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str
        value: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test2", operation="POST", client_types=["api"], api_version=3)
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"], api_version=2, envelope_key="data")
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"], api_version=1, envelope_key="project")
        def test_method(project: Project) -> Project:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, project: Project) -> Project:  # NOQA
            return project

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # rest call
    port = opt.get_bind_port()

    request = HTTPRequest(
        url=f"http://localhost:{port}/api/v1/test", method="POST", body=json_encode({"project": {"name": "a", "value": "b"}})
    )
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200
    body = json.loads(response.body)
    assert "project" in body

    request = HTTPRequest(
        url=f"http://localhost:{port}/api/v2/test", method="POST", body=json_encode({"project": {"name": "a", "value": "b"}})
    )
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200
    body = json.loads(response.body)
    assert "data" in body

    request = HTTPRequest(
        url=f"http://localhost:{port}/api/v3/test2", method="POST", body=json_encode({"project": {"name": "a", "value": "b"}})
    )
    client = AsyncHTTPClient()
    response = await client.fetch(request)
    assert response.code == 200
    body = json.loads(response.body)
    assert "data" in body

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "project" in response.result

    client = protocol.Client("client", version_match=VersionMatch.highest)
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "data" in response.result

    client = protocol.Client("client", version_match=VersionMatch.exact, exact_version=1)
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "project" in response.result

    client = protocol.Client("client", version_match=VersionMatch.exact, exact_version=2)
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "data" in response.result


async def test_multi_version_handler(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test multi version methods"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str
        value: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"], api_version=2, envelope_key="data")
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"], api_version=1, envelope_key="project")
        def test_method(project: Project) -> Project:  # NOQA
            pass

        @protocol.handle(test_method, api_version=1)
        async def test_methodX(self, project: Project) -> Project:  # NOQA
            return Project(name="v1", value="1")

        @protocol.handle(test_method, api_version=2)
        async def test_methodY(self, project: Project) -> Project:  # NOQA
            return Project(name="v2", value="2")

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "project" in response.result
    assert response.result["project"]["name"] == "v1"

    client = protocol.Client("client", version_match=VersionMatch.highest)
    response = await client.test_method(project=Project(name="a", value="b"))
    assert response.code == 200
    assert "data" in response.result
    assert response.result["data"]["name"] == "v2"


async def test_simple_return_type(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test methods with simple return types"""
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=["api"])
        def test_method(project: str) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_methodY(self, project: str) -> str:  # NOQA
            return project

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method(project="x")
    assert response.code == 200
    assert response.result["data"] == "x"


async def test_html_content_type(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test whether API endpoints with a text/html content-type work."""
    configure(unused_tcp_port, database_name, postgres_db.port)

    html_content = "<html><body>test</body></html>"

    @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
    def test_method() -> ReturnValue[str]:  # NOQA
        pass

    class TestServer(ServerSlice):
        @protocol.handle(test_method)
        async def test_methodY(self) -> ReturnValue[str]:  # NOQA
            return ReturnValue(response=html_content, content_type=HTML_CONTENT)

    rs = Server()
    server = TestServer(name="testserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method()
    assert response.code == 200
    assert response.result == html_content


async def test_html_content_type_with_utf8_encoding(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test whether API endpoints with a "text/html; charset=UTF-8" content-type work."""
    configure(unused_tcp_port, database_name, postgres_db.port)

    html_content = "<html><body>test</body></html>"

    @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
    def test_method() -> ReturnValue[str]:  # NOQA
        pass

    class TestServer(ServerSlice):
        @protocol.handle(test_method)
        async def test_methodY(self) -> ReturnValue[str]:  # NOQA

            return ReturnValue(response=html_content, content_type=HTML_CONTENT_WITH_UTF8_CHARSET)

    rs = Server()
    server = TestServer(name="testserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method()
    assert response.code == 200
    assert response.result == html_content


async def test_octet_stream_content_type(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test whether API endpoints with an application/octet-stream content-type work."""
    configure(unused_tcp_port, database_name, postgres_db.port)

    byte_stream = b"test123"

    @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
    def test_method() -> ReturnValue[bytes]:  # NOQA
        pass

    class TestServer(ServerSlice):
        @protocol.handle(test_method)
        async def test_methodY(self) -> ReturnValue[bytes]:  # NOQA
            return ReturnValue(response=byte_stream, content_type=OCTET_STREAM_CONTENT)

    rs = Server()
    server = TestServer(name="testserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method()
    assert response.code == 200
    assert response.result == byte_stream


async def test_zip_content_type(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """Test whether API endpoints with an application/zip content-type work."""
    configure(unused_tcp_port, database_name, postgres_db.port)

    zip_content = b"test123"

    @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
    def test_method() -> ReturnValue[bytes]:  # NOQA
        pass

    class TestServer(ServerSlice):
        @protocol.handle(test_method)
        async def test_methodY(self) -> ReturnValue[bytes]:  # NOQA
            return ReturnValue(response=zip_content, content_type=ZIP_CONTENT)

    rs = Server()
    server = TestServer(name="testserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    # client based calls
    client = protocol.Client("client")
    response = await client.test_method()
    assert response.code == 200
    assert response.result == zip_content


@pytest.fixture
async def options_server():
    @protocol.typedmethod(path="/test", operation="OPTIONS", client_types=["api"])
    def test_method() -> ReturnValue[str]:  # NOQA
        pass

    class TestServer(ServerSlice):
        @protocol.handle(test_method)
        async def test_methodY(self) -> ReturnValue[str]:  # NOQA
            return ReturnValue(response="content")

    return TestServer(name="testserver")


@pytest.fixture
def options_request(unused_tcp_port):
    return HTTPRequest(
        url=f"http://localhost:{unused_tcp_port}/api/v1/test",
        method="OPTIONS",
        connect_timeout=1.0,
        request_timeout=1.0,
        decompress_response=True,
    )


@pytest.mark.parametrize("auth_enabled, auth_header_allowed", [(True, True), (False, False)])
async def test_auth_enabled_options_method(
    auth_enabled,
    auth_header_allowed,
    unused_tcp_port,
    postgres_db,
    database_name,
    async_finalizer,
    options_server,
    options_request,
):
    configure(unused_tcp_port, database_name, postgres_db.port)
    config.Config.set("server", "auth", str(auth_enabled))
    rs = Server()
    rs.add_slice(options_server)
    await rs.start()
    async_finalizer.add(options_server.stop)
    async_finalizer.add(rs.stop)
    client = AsyncHTTPClient()
    response = await client.fetch(options_request)
    assert response.code == 200
    assert ("Authorization" in response.headers.get("Access-Control-Allow-Headers")) == auth_header_allowed


async def test_required_header_not_present(server):
    client = AsyncHTTPClient()
    response = await client.fetch(f"http://localhost:{server_bind_port.get()}/api/v2/environment_settings", raise_error=False)
    assert response.code == 400


async def test_malformed_json(server):
    """
    Tests sending malformed json to the server
    """
    port = opt.get_bind_port()
    url = f"http://localhost:{port}/api/v2/environment"

    request = HTTPRequest(url=url, method="PUT", body='{"name": env}')
    client = AsyncHTTPClient()
    response = await client.fetch(request, raise_error=False)
    assert response.code == 400
    assert (
        json.loads(response.body)["message"]
        == "The request body couldn't be decoded as a JSON: Expecting value: line 1 column 10 (char 9)"
    )


async def test_tuple_index_out_of_range(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class Project(BaseModel):
        name: str
        value: str

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(
            api_prefix="test", path="/project/<project>", operation="GET", arg_options=ENV_OPTS, client_types=["api"]
        )
        def test_method(
            tid: uuid.UUID, project: str, include_deleted: bool = False
        ) -> List[Union[uuid.UUID, Project, bool]]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(
            tid: uuid.UUID, project: Project, include_deleted: bool = False
        ) -> List[Union[uuid.UUID, Project, bool]]:  # NOQA
            return [tid, project, include_deleted]

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    port = opt.get_bind_port()
    url = f"http://localhost:{port}/test/v1/project/afcb51dc-1043-42b6-bb99-b4fc88603126"

    request = HTTPRequest(url=url, method="GET")
    client = AsyncHTTPClient()
    response = await client.fetch(request, raise_error=False)
    assert response.code == 400
    assert json.loads(response.body)["message"] == "Invalid request: Field 'tid' is required."


async def test_multiple_path_params(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, age: int) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_methodY(self, id: str, name: str, age: int) -> str:  # NOQA
            return name

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(args=[], kwargs={"id": "1", "name": "monty", "age": 42})
    assert request.url == "/api/v1/test/1/monty?age=42"


async def test_2151_method_header_parameter_in_body(async_finalizer, unused_tcp_port) -> None:
    async def _id(x: object, dct: Dict[str, str]) -> object:
        return x

    @protocol.method(
        path="/testmethod",
        operation="POST",
        arg_options={"header_param": ArgOption(header="X-Inmanta-Header-Param", getter=_id)},
        client_types=[const.ClientType.api],
    )
    def test_method(header_param: str, body_param: str) -> None:
        """
        A method used for testing.
        """

    class TestSlice(ServerSlice):
        @protocol.handle(test_method)
        async def test_method_implementation(self, header_param: str, body_param: str) -> None:
            pass

    configure(unused_tcp_port, "", "")
    server: Server = Server()
    server_slice: ServerSlice = TestSlice("my_test_slice")
    server.add_slice(server_slice)
    await server.start()
    async_finalizer.add(server_slice.stop)
    async_finalizer.add(server.stop)

    client = tornado.httpclient.AsyncHTTPClient()

    # valid request should succeed
    request = tornado.httpclient.HTTPRequest(
        url=f"http://localhost:{opt.get_bind_port()}/api/v1/testmethod",
        method="POST",
        body=json_encode({"body_param": "body_param_value"}),
        headers={"X-Inmanta-Header-Param": "header_param_value"},
    )
    response: tornado.httpclient.HTTPResponse = await client.fetch(request)
    assert response.code == 200

    # invalid request should fail
    request = tornado.httpclient.HTTPRequest(
        url=f"http://localhost:{opt.get_bind_port()}/api/v1/testmethod",
        method="POST",
        body=json_encode({"header_param": "header_param_value", "body_param": "body_param_value"}),
    )
    with pytest.raises(tornado.httpclient.HTTPClientError):
        await client.fetch(request)


@pytest.mark.parametrize("return_value,valid", [(1, True), (None, True), ("Hello World!", False)])
async def test_2277_typedmethod_return_optional(async_finalizer, return_value: object, valid: bool, unused_tcp_port) -> None:
    @protocol.typedmethod(
        path="/typedtestmethod",
        operation="GET",
        client_types=[const.ClientType.api],
        api_version=1,
    )
    def test_method_typed() -> Optional[int]:
        """
        A typedmethod used for testing.
        """

    class TestSlice(ServerSlice):
        @protocol.handle(test_method_typed)
        async def test_method_typed_implementation(self) -> Optional[int]:
            return return_value  # type: ignore

    configure(unused_tcp_port, "", "")
    server: Server = Server()
    server_slice: ServerSlice = TestSlice("my_test_slice")
    server.add_slice(server_slice)
    await server.start()
    async_finalizer.add(server_slice.stop)
    async_finalizer.add(server.stop)

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method_typed()
    if valid:
        assert response.code == 200
        assert response.result == {"data": return_value}
    else:
        assert response.code == 400


def test_method_strict_exception() -> None:
    with pytest.raises(InvalidMethodDefinition, match="Invalid type for argument arg: Any type is not allowed in strict mode"):

        @protocol.typedmethod(path="/testmethod", operation="POST", client_types=[const.ClientType.api])
        def test_method(arg: Any) -> None:
            pass


async def test_method_nonstrict_allowed(async_finalizer, unused_tcp_port) -> None:
    @protocol.typedmethod(path="/zipsingle", operation="POST", client_types=[const.ClientType.api], strict_typing=False)
    def merge_dicts(one: Dict[str, Any], other: Dict[str, int], any_arg: Any) -> Dict[str, Any]:
        """
        Merge two dicts.
        """

    class TestSlice(ServerSlice):
        @protocol.handle(merge_dicts)
        async def merge_dicts_impl(self, one: Dict[str, Any], other: Dict[str, int], any_arg: Any) -> Dict[str, Any]:
            return {**one, **other}

    configure(unused_tcp_port, "", "")
    server: Server = Server()
    server_slice: ServerSlice = TestSlice("my_test_slice")
    server.add_slice(server_slice)
    await server.start()
    async_finalizer.add(server_slice.stop)
    async_finalizer.add(server.stop)

    client: protocol.Client = protocol.Client("client")

    one: Dict[str, Any] = {"my": {"nested": {"keys": 42}}}
    other: Dict[str, int] = {"single_level": 42}
    response: Result = await client.merge_dicts(one, other, None)
    assert response.code == 200
    assert response.result == {"data": {**one, **other}}


@pytest.mark.parametrize(
    "param_type,param_value,expected_url",
    [
        (
            Dict[str, str],
            {"a": "b", "c": "d", ",&?=%": ",&?=%."},
            "/api/v1/test/1/monty?filter.a=b&filter.c=d&filter.%2C%26%3F%3D%25=%2C%26%3F%3D%25.",
        ),
        (
            Dict[str, List[str]],
            {"a": ["b"], "c": ["d", "e"], "g": ["h"]},
            "/api/v1/test/1/monty?filter.a=b&filter.c=d&filter.c=e&filter.g=h",
        ),
        (
            Dict[str, List[str]],
            {"a": ["b"], "c": ["d", "e"], ",&?=%": [",&?=%", "f"], ".g.h": ["i"]},
            "/api/v1/test/1/monty?filter.a=b&filter.c=d&filter.c=e"
            "&filter.%2C%26%3F%3D%25=%2C%26%3F%3D%25&filter.%2C%26%3F%3D%25=f&filter..g.h=i",
        ),
        (
            List[str],
            [
                "a ",
                "b,",
                "c",
            ],
            "/api/v1/test/1/monty?filter=a+&filter=b%2C&filter=c",
        ),
        (
            List[str],
            ["a", "b", ",&?=%", "c", "."],
            "/api/v1/test/1/monty?filter=a&filter=b&filter=%2C%26%3F%3D%25&filter=c&filter=.",
        ),
        (List[str], ["a ", "b", "c", ","], "/api/v1/test/1/monty?filter=a+&filter=b&filter=c&filter=%2C"),
    ],
)
async def test_dict_list_get_roundtrip(
    unused_tcp_port, postgres_db, database_name, async_finalizer, param_type, param_value, expected_url
):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"], strict_typing=False)
        def test_method(id: str, name: str, filter: param_type) -> Any:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str, name: str, filter: param_type) -> Any:  # NOQA
            return filter

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(
        args=[], kwargs={"id": "1", "name": "monty", "filter": param_value}
    )
    assert request.url == expected_url

    client: protocol.Client = protocol.Client("client")
    response: Result = await client.test_method(1, "monty", filter=param_value)
    assert response.code == 200
    assert response.result["data"] == param_value


async def test_dict_get_optional(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, filter: Optional[Dict[str, str]] = None) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str, name: str, filter: Optional[Dict[str, str]] = None) -> str:  # NOQA
            return ",".join(filter.keys()) if filter is not None else ""

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(
        args=[], kwargs={"id": "1", "name": "monty", "filter": {"a": "b"}}
    )
    assert request.url == "/api/v1/test/1/monty?filter.a=b"

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method(1, "monty", filter={"a": "b", "c": "d"})
    assert response.code == 200
    assert response.result["data"] == "a,c"
    response: Result = await client.test_method(1, "monty")
    assert response.code == 200
    assert response.result["data"] == ""


async def test_dict_list_nested_get_optional(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, filter: Optional[Dict[str, List[str]]] = None) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str, name: str, filter: Optional[Dict[str, List[str]]] = None) -> str:  # NOQA
            return ",".join(filter.keys()) if filter is not None else ""

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(
        args=[], kwargs={"id": "1", "name": "monty", "filter": {"a": ["b"]}}
    )
    assert request.url == "/api/v1/test/1/monty?filter.a=b"

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method(1, "monty", filter={"a": "b", "c": ["d", "e"]})
    assert response.code == 200
    assert response.result["data"] == "a,c"
    response: Result = await client.test_method(1, "monty")
    assert response.code == 200
    assert response.result["data"] == ""


@pytest.mark.parametrize(
    "param_type,expected_error_message",
    [
        (
            Dict[str, Dict[str, str]],
            "nested dictionaries and union types for dictionary values are not supported for GET requests",
        ),
        (
            Dict[str, Union[str, List[str]]],
            "nested dictionaries and union types for dictionary values are not supported for GET requests",
        ),
        (List[Dict[str, str]], "lists of dictionaries and lists of lists are not supported for GET requests"),
        (List[List[str]], "lists of dictionaries and lists of lists are not supported for GET requests"),
    ],
)
async def test_dict_list_get_invalid(
    unused_tcp_port, postgres_db, database_name, async_finalizer, param_type, expected_error_message
):
    configure(unused_tcp_port, database_name, postgres_db.port)

    with pytest.raises(InvalidMethodDefinition) as e:

        class ProjectServer(ServerSlice):
            @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
            def test_method(id: str, name: str, filter: param_type) -> str:  # NOQA
                pass

            @protocol.handle(test_method)
            async def test_method(self, id: str, name: str, filter: param_type) -> str:  # NOQA
                return ""

        assert expected_error_message in str(e)


async def test_list_get_optional(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, sort: Optional[List[int]] = None) -> str:  # NOQA
            pass

        @protocol.typedmethod(path="/test_uuid/<id>", operation="GET", client_types=["api"])
        def test_method_uuid(id: str, sort: Optional[List[uuid.UUID]] = None) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str, name: str, sort: Optional[List[int]] = None) -> str:  # NOQA
            return str(sort) if sort else ""

        @protocol.handle(test_method_uuid)
        async def test_method_uuid(self, id: str, sort: Optional[List[uuid.UUID]] = None) -> str:  # NOQA
            return str(sort) if sort else ""

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(
        args=[], kwargs={"id": "1", "name": "monty", "sort": [1, 2]}
    )
    assert request.url == "/api/v1/test/1/monty?sort=1&sort=2"

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method(1, "monty", sort=[1, 2])
    assert response.code == 200
    assert response.result["data"] == "[1, 2]"
    response: Result = await client.test_method(1, "monty")
    assert response.code == 200
    assert response.result["data"] == ""
    uuids = [uuid.uuid4(), uuid.uuid4()]
    request = MethodProperties.methods["test_method_uuid"][0].build_call(args=[], kwargs={"id": "1", "sort": uuids})
    assert request.url == f"/api/v1/test_uuid/1?sort={uuids[0]}&sort={uuids[1]}"


async def test_dicts_multiple_get(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, filter: Dict[str, List[str]], another_filter: Dict[str, str]) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(
            self, id: str, name: str, filter: Dict[str, List[str]], another_filter: Dict[str, str]
        ) -> str:  # NOQA
            return ",".join(chain(filter.keys(), another_filter.keys()))

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    request = MethodProperties.methods["test_method"][0].build_call(
        args=[], kwargs={"id": "1", "name": "monty", "filter": {"a": ["b", "c"]}, "another_filter": {"d": "e"}}
    )
    assert request.url == "/api/v1/test/1/monty?filter.a=b&filter.a=c&another_filter.d=e"

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method(1, "monty", filter={"a": ["b"], "c": ["d", "e"]}, another_filter={"x": "y"})
    assert response.code == 200
    assert response.result["data"] == "a,c,x"


async def test_dict_list_get_by_url(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test/<id>/<name>", operation="GET", client_types=["api"])
        def test_method(id: str, name: str, filter: Dict[str, str]) -> str:  # NOQA
            pass

        @protocol.typedmethod(path="/test_list/<id>", operation="GET", client_types=["api"])
        def test_method_list(id: str, filter: List[int]) -> str:  # NOQA
            pass

        @protocol.typedmethod(path="/test_dict_of_lists/<id>", operation="GET", client_types=["api"])
        def test_method_dict_of_lists(id: str, filter: Dict[str, List[str]]) -> str:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str, name: str, filter: Dict[str, str]) -> str:  # NOQA
            return ",".join(filter.keys())

        @protocol.handle(test_method_list)
        async def test_method_list(self, id: str, filter: List[int]) -> str:  # NOQA
            return str(filter)

        @protocol.handle(test_method_dict_of_lists)
        async def test_method_dict_of_lists(self, id: str, filter: Dict[str, List[str]]) -> str:  # NOQA
            return ",".join(filter.keys())

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = AsyncHTTPClient()
    response = await client.fetch(f"http://localhost:{server_bind_port.get()}/api/v1/test/1/monty?filter.=b", raise_error=False)
    assert response.code == 400
    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test/1/monty?filter.a=b&filter.=c", raise_error=False
    )
    assert response.code == 400
    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test/1/monty?filter.a=b&filter.a=c", raise_error=False
    )
    assert response.code == 400
    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test_list/1?filter.a=b&filter.=c", raise_error=False
    )
    assert response.code == 400
    # Integer should also work
    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test_list/1?filter=42&filter=45", raise_error=False
    )
    assert response.code == 200

    # list nested in dict
    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test_dict_of_lists/1?filter.a=42&filter.a=55&filter.b=e",
        raise_error=False,
    )
    assert response.code == 200

    filter_with_comma = {"filter.a": "42,55,%2C70", "filter.b": "e"}
    url = url_concat(f"http://localhost:{server_bind_port.get()}/api/v1/test_dict_of_lists/1", filter_with_comma)
    response = await client.fetch(
        url,
        raise_error=False,
    )
    assert response.code == 200

    response = await client.fetch(
        f"http://localhost:{server_bind_port.get()}/api/v1/test_dict_of_lists/1?filter.a=42&filter.a=55&filter.&filter.c=a",
        raise_error=False,
    )
    assert response.code == 400
    filter_with_comma = {"filter.a": "b", "filter.c": "e", "filter.,&?=%": ",&?=%"}
    url = url_concat(f"http://localhost:{server_bind_port.get()}/api/v1/test/1/monty", filter_with_comma)
    response = await client.fetch(
        url,
        raise_error=False,
    )
    assert response.code == 200


async def test_api_datetime_utc(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test API input and output conversion for timestamps. Objects should be either timezone-aware or implicit UTC.
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    timezone: datetime.timezone = datetime.timezone(datetime.timedelta(hours=2))
    now: datetime.datetime = datetime.datetime.now().astimezone(timezone)
    naive_utc: datetime.datetime = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
        def test_method(timestamp: datetime.datetime) -> List[datetime.datetime]:
            pass

        @protocol.handle(test_method)
        async def test_method(self, timestamp: datetime.datetime) -> List[datetime.datetime]:
            assert timestamp.tzinfo is not None
            assert timestamp == now
            return [
                now,
                now.astimezone(datetime.timezone.utc),
                now.astimezone(datetime.timezone.utc).replace(tzinfo=None),
            ]

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client: protocol.Client = protocol.Client("client")

    response: Result = await client.test_method(timestamp=now)
    assert response.code == 200
    assert all(pydantic.parse_obj_as(datetime.datetime, timestamp) == naive_utc for timestamp in response.result["data"])

    response: Result = await client.test_method(timestamp=now.astimezone(datetime.timezone.utc))
    assert response.code == 200

    response: Result = await client.test_method(timestamp=now.astimezone(datetime.timezone.utc).replace(tzinfo=None))
    assert response.code == 200

    response: Result = await client.test_method(timestamp=now.replace(tzinfo=None))
    assert response.code == 500

    # Test REST API without going through Python client
    port = opt.get_bind_port()
    client = AsyncHTTPClient()

    async def request(timestamp: datetime.datetime) -> tornado.httpclient.HTTPResponse:
        request = HTTPRequest(
            url=(
                f"http://localhost:{port}/api/v1/test?timestamp="
                f"{urllib.parse.quote(timestamp.isoformat(timespec='microseconds'))}"
            ),
            method="GET",
        )
        return await client.fetch(request)

    response = await request(now)
    assert response.code == 200

    response = await request(now.astimezone(datetime.timezone.utc).replace(tzinfo=None))
    assert response.code == 200

    with pytest.raises(tornado.httpclient.HTTPClientError):
        response = await request(now.replace(tzinfo=None))


async def test_dict_of_list(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test API input and output conversion for timestamps. Objects should be either timezone-aware or implicit UTC.
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class APydanticType(BaseModel):
        attr: int

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="GET", client_types=[const.ClientType.api])
        def test_method(id: str) -> Dict[str, List[APydanticType]]:
            pass

        @protocol.handle(test_method)
        async def test_method(self, id: str) -> Dict[str, List[APydanticType]]:
            return {id: [APydanticType(attr=1), APydanticType(attr=5)]}

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client: protocol.Client = protocol.Client("client")

    result = await client.test_method(id="test")
    assert result.code == 200, result.result["message"]
    assert result.result["data"] == {"test": [{"attr": 1}, {"attr": 5}]}


async def test_return_value_with_meta(unused_tcp_port, postgres_db, database_name, async_finalizer):
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="GET", client_types=["api"])
        def test_method(with_warning: bool) -> ReturnValueWithMeta[str]:  # NOQA
            pass

        @protocol.handle(test_method)
        async def test_method(self, with_warning: bool) -> ReturnValueWithMeta:  # NOQA
            metadata = {"additionalInfo": f"Today's bitcoin exchange rate is: {(random.random() * 100000):.2f}$"}
            result = ReturnValueWithMeta(response="abcd", metadata=metadata)
            if with_warning:
                result.add_warnings(["Warning message"])
            return result

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)
    client: protocol.Client = protocol.Client("client")

    response = await client.test_method(False)
    assert response.code == 200
    assert response.result["data"] == "abcd"
    assert response.result["metadata"].get("additionalInfo") is not None
    assert response.result["metadata"].get("warnings") is None

    response = await client.test_method(True)
    assert response.code == 200
    assert response.result["data"] == "abcd"
    assert response.result["metadata"].get("additionalInfo") is not None
    assert response.result["metadata"].get("warnings") is not None


async def test_kwargs(unused_tcp_port, postgres_db, database_name, async_finalizer):
    """
    Test the use and validation of methods that use common.ReturnValue
    """
    configure(unused_tcp_port, database_name, postgres_db.port)

    class ProjectServer(ServerSlice):
        @protocol.typedmethod(path="/test", operation="POST", client_types=[ClientType.api], varkw=True)
        def test_method(id: str, **kwargs: object) -> Dict[str, str]:  # NOQA
            """
            Create a new project
            """

        @protocol.handle(test_method)
        async def test_method(self, id: str, **kwargs: object) -> Dict[str, str]:
            return {"name": str(kwargs["name"]), "value": str(kwargs["value"])}

    rs = Server()
    server = ProjectServer(name="projectserver")
    rs.add_slice(server)
    await rs.start()
    async_finalizer.add(server.stop)
    async_finalizer.add(rs.stop)

    client = protocol.Client("client")
    result = await client.test_method(id="test", name="test", value=True)
    assert result.code == 200
    assert result.result["data"]["name"] == "test"
    assert result.result["data"]["value"]
