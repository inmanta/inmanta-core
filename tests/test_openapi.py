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
import inspect
import json
from typing import Dict, List, Optional, Union
from uuid import UUID

import pytest
from openapi_spec_validator import openapi_v3_spec_validator

from inmanta.const import INMANTA_MT_HEADER, ResourceAction
from inmanta.data import model
from inmanta.protocol import method
from inmanta.protocol.common import MethodProperties, UrlMethod
from inmanta.protocol.methods import ENV_OPTS
from inmanta.protocol.openapi.converter import (
    ArgOptionHandler,
    FunctionParameterHandler,
    OpenApiConverter,
    OpenApiTypeConverter,
    OperationHandler,
)
from inmanta.protocol.openapi.model import MediaType, Parameter, Schema


@pytest.mark.asyncio
async def test_generate_openapi_definition(server):
    global_url_map = server._transport.get_global_url_map(server.get_slices().values())
    openapi = OpenApiConverter(global_url_map)
    openapi_json = openapi.generate_openapi_json()
    assert openapi_json
    openapi_parsed = json.loads(openapi_json)
    openapi_v3_spec_validator.validate(openapi_parsed)


@pytest.mark.asyncio
async def test_filter_api_methods(server):
    @method(path="/operation", client_types=["api", "agent"], envelope=True)
    def post_method() -> object:
        return ""

    @method(path="/operation", client_types=["agent"], operation="GET")
    def get_method():
        pass

    post = UrlMethod(properties=MethodProperties.methods["post_method"][0], slice=None, method_name="post_method", handler=None)
    methods = {
        "POST": post,
        "GET": UrlMethod(
            properties=MethodProperties.methods["get_method"][0], slice=None, method_name="get_method", handler=None
        ),
    }
    openapi = OpenApiConverter(server._transport.get_global_url_map(server.get_slices().values()))
    api_methods = openapi._filter_api_methods(methods)
    assert len(api_methods) == 1


@pytest.mark.asyncio
async def test_get_function_parameters():
    def dummy_method(param: int, tid: UUID, id: UUID) -> str:
        return ""

    function_parameter_handler = FunctionParameterHandler(
        OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()), "/basepath"
    )
    function_parameters = function_parameter_handler._extract_function_parameters(dummy_method)
    assert len(function_parameters) == 3
    assert function_parameters["param"] == inspect.Parameter("param", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)


@pytest.mark.asyncio
async def test_filter_function_parameters():
    function_parameter_handler = FunctionParameterHandler(
        OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()), "/basepath"
    )
    function_parameters = {
        "tid": inspect.Parameter("tid", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=UUID),
        "param": inspect.Parameter("param", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
    }
    already_existing_parameters = [Parameter(in_="header", required=True, name=INMANTA_MT_HEADER)]
    filtered_function_parameters = function_parameter_handler._filter_already_processed_function_params(
        function_parameters, already_existing_parameters
    )
    assert len(filtered_function_parameters) == 1
    assert filtered_function_parameters["param"] == inspect.Parameter(
        "param", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int
    )


@pytest.mark.asyncio
async def test_return_value():
    @method(path="/operation", client_types=["api", "agent"], envelope=True)
    def post_method() -> object:
        return ""

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))

    json_response_content = operation_handler._build_return_value_wrapper(MethodProperties.methods["post_method"][0])
    assert json_response_content == {
        "application/json": MediaType(schema=Schema(type="object", properties={"data": {"type": "object"}}))
    }


@pytest.mark.asyncio
async def test_get_openapi_types():
    type_converter = OpenApiTypeConverter()

    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=UUID)
    )
    assert openapi_type == Schema(type="string", format="uuid")

    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    )
    assert openapi_type == Schema(type="integer")


@pytest.mark.asyncio
async def test_openapi_types_base_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=model.Environment)
    )
    assert openapi_type.required == ["id", "name", "project_id", "repo_url", "repo_branch", "settings"]


@pytest.mark.asyncio
async def test_openapi_types_union():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Union[str, bytes])
    assert openapi_type == Schema(anyOf=[Schema(type="string"), Schema(type="string", format="binary")])


@pytest.mark.asyncio
async def test_openapi_types_optional():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Optional[str])
    assert openapi_type == Schema(type="string", nullable=True)


@pytest.mark.asyncio
async def test_openapi_types_list():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[Union[int, UUID]])
    assert openapi_type == Schema(
        type="array", items=Schema(anyOf=[Schema(type="integer"), Schema(type="string", format="uuid")])
    )


@pytest.mark.asyncio
async def test_openapi_types_enum():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[ResourceAction])
    assert openapi_type == Schema(
        type="array", items=Schema(type="string", enum=["store", "push", "pull", "deploy", "dryrun", "getfact", "other"])
    )


@pytest.mark.asyncio
async def test_openapi_types_dict():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Dict[str, UUID])
    assert openapi_type == Schema(type="object", format="typing.Dict[str, uuid.UUID]")


@pytest.mark.asyncio
async def test_post_operation():
    @method(path="/operation", client_types=["api", "agent"], envelope=True, arg_options=ENV_OPTS)
    def dummy_method(tid: UUID, param: int, id: UUID) -> str:
        return ""

    post = UrlMethod(
        properties=MethodProperties.methods["dummy_method"][0], slice=None, method_name="dummy_method", handler=None
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method_with_request_body(post, "/operation")
    assert "X-Inmanta-tid" in [parameter.name for parameter in operation.parameters]
    assert "param" in operation.requestBody.content["application/json"].schema_.properties.keys()
    assert "id" in operation.requestBody.content["application/json"].schema_.properties.keys()
    assert "X-Inmanta-tid" in operation.responses["200"].headers.keys()


@pytest.mark.asyncio
async def test_get_operation():
    @method(path="/operation", client_types=["api", "agent"], envelope=True, arg_options=ENV_OPTS, operation="GET")
    def dummy_method(tid: UUID, param: int, id: UUID) -> str:
        return ""

    get = UrlMethod(
        properties=MethodProperties.methods["dummy_method"][0], slice=None, method_name="dummy_method", handler=None
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method_without_request_body(get, "/operation")
    assert "X-Inmanta-tid" in [parameter.name for parameter in operation.parameters]
    assert "param" in [parameter.name for parameter in operation.parameters]
    assert "id" in [parameter.name for parameter in operation.parameters]
    assert not operation.requestBody
    assert "X-Inmanta-tid" in operation.responses["200"].headers.keys()
