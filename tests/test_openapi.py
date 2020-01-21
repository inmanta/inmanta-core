"""
    Copyright 2020 Inmanta

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
from uuid import UUID

import pytest
from openapi_spec_validator import openapi_v3_spec_validator

from inmanta import data
from inmanta.protocol import method
from inmanta.protocol.common import MethodProperties, UrlMethod
from inmanta.protocol.openapi.converter import OpenApiConverter
from inmanta.protocol.openapi.model import Parameter, Response


@pytest.mark.asyncio
async def test_generate_openapi_definiton(server):
    global_url_map = server._transport.get_global_url_map(server.get_slices().values())
    openapi = OpenApiConverter()
    openapi_json = openapi.generate_openapi_definition(global_url_map)
    assert openapi_json
    openapi_parsed = json.loads(openapi_json)
    openapi_v3_spec_validator.validate(openapi_parsed)


@pytest.mark.asyncio
async def test_filter_api_methods():
    @method(path="/operation", client_types=["api", "agent"], envelope=True)
    def post_method() -> object:
        return ""

    @method(path="/operation", client_types=["agent"], operation="GET")
    def get_method():
        pass

    post = UrlMethod(
        properties=MethodProperties.methods["post_method"][0], slice=None, method_name="post_method", handler=None
    )
    methods = {
        "POST": post,
        "GET": UrlMethod(
            properties=MethodProperties.methods["get_method"][0], slice=None, method_name="get_method", handler=None
        ),
    }
    openapi = OpenApiConverter()
    api_methods = openapi.filter_api_methods(methods)
    assert len(api_methods) == 1


@pytest.mark.asyncio
async def test_get_function_parameters():
    def dummy_method(param: int, tid: UUID, id: UUID) -> str:
        return ""

    openapi = OpenApiConverter()
    function_parameters = openapi.get_function_parameters([Parameter(**{"name": "id", "in": "path"})], dummy_method)
    assert len(function_parameters) == 1
    assert function_parameters["param"] == int


@pytest.mark.asyncio
async def test_return_value():
    @method(path="/operation", client_types=["api", "agent"], envelope=True)
    def post_method() -> object:
        return ""

    openapi = OpenApiConverter()
    response = Response(description="Description of the response")
    post = UrlMethod(
        properties=MethodProperties.methods["post_method"][0], slice=None, method_name="post_method", handler=None
    )
    openapi.add_return_value_to_response(response, post)
    assert response.content.get("application/json") == {
        "schema": {"type": "object", "properties": {"data": {"type": "object"}}}
    }


@pytest.mark.asyncio
async def test_get_openapi_types():
    openapi = OpenApiConverter()

    openapi_type = openapi.get_openapi_type(UUID)
    assert openapi_type == {"type": "string", "format": "uuid"}

    openapi_type = openapi.get_openapi_type(data.Environment)
    assert openapi_type == {"type": "object"}

    openapi_type = openapi.get_openapi_type(int)
    assert openapi_type == {"type": "integer"}


@pytest.mark.asyncio
async def test_convert_params_for_post_request():
    def dummy_method(param: int, tid: UUID, id: UUID) -> str:
        return ""

    openapi = OpenApiConverter()
    parameters = [Parameter(**{"name": "id", "in": "path"})]
    function_parameters = openapi.get_function_parameters([Parameter(**{"name": "id", "in": "path"})], dummy_method)
    properties = openapi.convert_function_params_to_openapi(function_parameters, "POST", parameters, "/api/method/{id}")
    assert properties == {"param": {"type": "integer"}}
