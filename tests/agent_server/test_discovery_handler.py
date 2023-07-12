"""
    Copyright 2023 Inmanta

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
from inmanta.agent import Agent
from inmanta.agent.handler import ResourceHandler, DiscoveryHandler
from inmanta.protocol import SessionClient, VersionMatch, common
from test_protocol import make_random_file
from utils import _wait_until_deployment_finishes, log_contains

T = TypeVar("T")


class MockSessionClient(SessionClient):
    def __init__(self):
        self._version_match = VersionMatch.highest
        pass

    # def get_file(self, hash_id):
    #     content = b""
    #     if self.return_code != 404:
    #         content = base64.b64encode(self.content)
    #     return common.Result(self.return_code, result={"content": content})

class MyDR:
    pass

class MyUR:
    pass

class Mock_____DiscoveryHandler(DiscoveryHandler[MyDR, MyUR]):
    def __init__(self, client):
        self._client = client

    def run_sync(self, func: typing.Callable[[], T]) -> T:
        return func()


def test_get_file_corrupted():
    (hash, content, body) = make_random_file()
    client = MockSessionClient(200, b"corrupted_file")
    resource_handler = Mock_____DiscoveryHandler(client)

    with pytest.raises(Exception):
        resource_handler.get_file(hash)
