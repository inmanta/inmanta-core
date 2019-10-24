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
import typing
from typing import TypeVar

import pytest

from inmanta.agent.handler import ResourceHandler
from inmanta.protocol import SessionClient, VersionMatch, common
from test_protocol import make_random_file

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
