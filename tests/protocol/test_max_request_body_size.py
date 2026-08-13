"""
Copyright 2026 Inmanta

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

import json

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import config
from inmanta.server import config as opt
from utils import make_random_file

MAX_REQUEST_BODY_SIZE = 1024


@pytest.fixture
def server_pre_start(server_config):
    config.Config.set("server", "max-request-body-size", str(MAX_REQUEST_BODY_SIZE))


def test_max_request_body_size_default() -> None:
    assert opt.server_max_request_body_size.get() == 100 * 1024 * 1024


@pytest.mark.parametrize("above_limit", [True, False])
async def test_max_request_body_size(server, above_limit: bool) -> None:
    """
    Verify that the server rejects requests with a body larger than the configured maximum and accepts smaller ones.
    """
    file_hash, _, file_content = make_random_file(size=MAX_REQUEST_BODY_SIZE if above_limit else 1)
    body = json.dumps({"content": file_content}).encode()
    assert (len(body) > MAX_REQUEST_BODY_SIZE) == above_limit

    port = opt.server_bind_port.get()
    request = HTTPRequest(url=f"http://localhost:{port}/api/v1/file/{file_hash}", method="PUT", body=body)
    response = await AsyncHTTPClient().fetch(request, raise_error=False)

    assert response.code == (400 if above_limit else 200)
