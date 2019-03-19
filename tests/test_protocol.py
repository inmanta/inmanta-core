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
import random
import base64
import threading
import os
import time

import pytest
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
from inmanta import config, protocol
from inmanta.protocol.rest import CallArguments
from inmanta.util import hash_file
from inmanta.server import config as opt
from tornado import gen, web
import tornado


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_client_files_lost(client):
    (hash, content, body) = make_random_file()

    # Get the file
    result = await client.get_file(id=hash)
    assert result.code == 404


@pytest.mark.asyncio
async def test_sync_client_files(client):
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_client_files_bad(client):
    (hash, content, body) = make_random_file()
    # Create the file
    result = await client.upload_file(id=hash + "a", content=body)
    assert result.code == 400


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_gzip_encoding(server):
    """
        Test if the server accepts gzipped encoding and returns gzipped encoding.
    """
    (hash, content, body) = make_random_file(size=1024)

    port = config.Config.get("server_rest_transport", "port")
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


@pytest.mark.asyncio(timeout=30)
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


@pytest.mark.asyncio
async def test_method_properties():
    """
        Test method properties decorator and helper functions
    """
    @protocol.method(method_name="test", operation="PUT", client_types=["api"])
    def test_method(name):
        """
            Create a new project
        """

    props: protocol.common.MethodProperties = test_method.__method_properties__
    assert "Authorization" in props.get_call_headers()
    assert props.get_listen_url() == "/api/v1/test"
    assert props.get_call_url({}) == "/api/v1/test"


@pytest.mark.asyncio
async def test_invalid_client_type():
    """
        Test invalid client ype
    """
    with pytest.raises(Exception) as e:
        @protocol.method(method_name="test", operation="PUT", client_types=["invalid"])
        def test_method(name):
            """
                Create a new project
            """
        assert "Invalid client type invalid specified for function" in str(e)


@pytest.mark.asyncio
async def test_call_arguments_defaults():
    """
        Test processing RPC messages
    """
    @protocol.method(method_name="test", operation="PUT", client_types=["api"])
    def test_method(name: str, value: int = 10):
        """
            Create a new project
        """

    call = CallArguments(test_method.__method_properties__, {"name": "test"}, {})
    await call.process()

    assert call.call_args["name"] == "test"
    assert call.call_args["value"] == 10


def test_create_client():
    with pytest.raises(AssertionError):
        protocol.SyncClient("agent", "120")

    with pytest.raises(AssertionError):
        protocol.Client("agent", "120")
