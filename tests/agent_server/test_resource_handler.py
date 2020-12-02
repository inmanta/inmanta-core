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
import base64
import logging
import typing
from typing import TypeVar

import pytest

from inmanta import const
from inmanta.agent.handler import ResourceHandler
from inmanta.protocol import SessionClient, VersionMatch, common
from test_protocol import make_random_file
from utils import _wait_until_deployment_finishes, log_contains

T = TypeVar("T")


class MockSessionClient(SessionClient):
    def __init__(self, return_code, content):
        self._version_match = VersionMatch.highest
        self.return_code = return_code
        self.content = content
        pass

    def get_file(self, hash_id):
        content = b""
        if self.return_code != 404:
            content = base64.b64encode(self.content)
        return common.Result(self.return_code, result={"content": content})


class MockGetFileResourceHandler(ResourceHandler):
    def __init__(self, client):
        self._client = client

    def run_sync(self, func: typing.Callable[[], T]) -> T:
        return func()


def test_get_file_corrupted():
    (hash, content, body) = make_random_file()
    client = MockSessionClient(200, b"corrupted_file")
    resource_handler = MockGetFileResourceHandler(client)

    with pytest.raises(Exception):
        resource_handler.get_file(hash)


def test_get_file_success():
    (hash, content, body) = make_random_file()
    client = MockSessionClient(200, content)
    resource_handler = MockGetFileResourceHandler(client)

    result = resource_handler.get_file(hash)
    assert content == result


def test_get_file_not_found():
    client = MockSessionClient(404, None)
    resource_handler = MockGetFileResourceHandler(client)
    result = resource_handler.get_file("hash")
    assert result is None


@pytest.mark.asyncio(timeout=15)
async def test_logging_error(resource_container, environment, client, agent, clienthelper, caplog):
    """
    When a log call uses an argument that is not JSON serializable, the corresponding resource should be marked as failed,
    and the exception logged.
    """
    resource_container.Provider.reset()
    version = await clienthelper.get_version()

    res_id_1 = "test::BadLogging[agent1,key=key1],v=%d" % version
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_resource(tid=environment, id=res_id_1, logs=False, status=True)
    assert result.code == 200
    assert result.result["status"] == "failed"

    log_contains(caplog, "inmanta.agent", logging.ERROR, "Exception during serializing log message arguments")
