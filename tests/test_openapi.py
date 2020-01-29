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
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

import pytest
from openapi_spec_validator import openapi_v3_spec_validator

from inmanta.const import INMANTA_MT_HEADER, ResourceAction
from inmanta.data import model
from inmanta.data.model import EnvironmentSetting
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


@pytest.fixture(scope="function")
def api_methods_fixture():
    @method(path="/simpleoperation", client_types=["api", "agent"], envelope=True)
    def post_method() -> object:
        return ""

    @method(path="/simpleoperation", client_types=["agent"], operation="GET")
    def get_method():
        pass

    @method(path="/operation", client_types=["api", "agent"], envelope=True, arg_options=ENV_OPTS)
    def dummy_post_with_parameters(tid: UUID, param: int, id: UUID) -> str:
        return ""

    @method(path="/operation", client_types=["api", "agent"], envelope=True, arg_options=ENV_OPTS, operation="GET")
    def dummy_get_with_parameters(tid: UUID, param: int, id: UUID) -> str:
        return ""


@pytest.mark.asyncio
async def test_generate_openapi_definition(server):
    global_url_map = server._transport.get_global_url_map(server.get_slices().values())
    openapi = OpenApiConverter(global_url_map)
    openapi_json = openapi.generate_openapi_json()
    assert openapi_json
    openapi_parsed = json.loads(openapi_json)
    openapi_v3_spec_validator.validate(openapi_parsed)


def test_filter_api_methods(server, api_methods_fixture):
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


def test_get_function_parameters():
    def dummy_method(param: int, tid: UUID, id: UUID) -> str:
        return ""

    function_parameter_handler = FunctionParameterHandler(
        OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()), "/basepath"
    )
    function_parameters = function_parameter_handler._extract_function_parameters(dummy_method)
    assert len(function_parameters) == 3
    assert function_parameters["param"] == inspect.Parameter("param", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)


def test_filter_function_parameters():
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


def test_return_value(api_methods_fixture):
    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))

    json_response_content = operation_handler._build_return_value_wrapper(MethodProperties.methods["post_method"][0])
    assert json_response_content == {
        "application/json": MediaType(schema=Schema(type="object", properties={"data": Schema(type="object")}))
    }


def test_get_openapi_types():
    type_converter = OpenApiTypeConverter()

    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=UUID)
    )
    assert openapi_type == Schema(type="string", format="uuid")

    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    )
    assert openapi_type == Schema(type="integer")


def test_openapi_types_base_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type_of_parameter(
        inspect.Parameter("param", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=model.Environment)
    )
    assert openapi_type.required == ["id", "name", "project_id", "repo_url", "repo_branch", "settings"]


def test_openapi_types_union():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Union[str, bytes])
    assert openapi_type == Schema(anyOf=[Schema(type="string"), Schema(type="string", format="binary")])


def test_openapi_types_optional():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Optional[str])
    assert openapi_type == Schema(type="string", nullable=True)


def test_openapi_types_list():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[Union[int, UUID]])
    assert openapi_type == Schema(
        type="array", items=Schema(anyOf=[Schema(type="integer"), Schema(type="string", format="uuid")])
    )


def test_openapi_types_enum():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[ResourceAction])
    assert openapi_type == Schema(
        type="array", items=Schema(type="string", enum=["store", "push", "pull", "deploy", "dryrun", "getfact", "other"])
    )


def test_openapi_types_dict():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Dict[str, UUID])
    assert openapi_type == Schema(type="object", additionalProperties=Schema(type="string", format="uuid"))


def test_openapi_types_list_of_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[model.Project])
    assert openapi_type.type == "array"
    assert openapi_type.items.title == "Project"
    assert openapi_type.items.required == ["id", "name", "environments"]


def test_openapi_types_list_of_list_of_optional_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(List[List[Optional[model.Project]]])
    assert openapi_type.type == "array"
    assert openapi_type.items.type == "array"
    assert openapi_type.items.items.required == ["id", "name", "environments"]
    assert openapi_type.items.items.nullable


def test_openapi_types_dict_of_union():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Dict[str, Union[model.Project, model.Environment]])
    assert openapi_type.type == "object"
    assert len(openapi_type.additionalProperties.anyOf) == 2
    assert openapi_type.additionalProperties.anyOf[0].title == "Project"
    assert openapi_type.additionalProperties.anyOf[1].title == "Environment"


def test_openapi_types_optional_union():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Optional[Union[int, str]])
    assert len(openapi_type.anyOf) == 2
    assert openapi_type.nullable


def test_openapi_types_union_optional():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Union[Optional[int], Optional[str]])
    assert len(openapi_type.anyOf) == 2
    assert openapi_type.nullable


def test_openapi_types_datetime():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(datetime)
    assert openapi_type == Schema(type="string", format="date-time")


def test_openapi_types_tuple():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(tuple)
    assert openapi_type == Schema(type="array", items=Schema())


def test_openapi_types_bool():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(bool)
    assert openapi_type == Schema(type="boolean")


def test_openapi_types_int():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(int)
    assert openapi_type == Schema(type="integer")


def test_openapi_types_string():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(str)
    assert openapi_type == Schema(type="string")


def test_openapi_types_float():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(float)
    assert openapi_type == Schema(type="number", format="float")


def test_openapi_types_bytes():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(bytes)
    assert openapi_type == Schema(type="string", format="binary")


def test_openapi_types_uuid():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(UUID)
    assert openapi_type == Schema(type="string", format="uuid")


def test_openapi_types_env_setting():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(EnvironmentSetting)
    assert openapi_type.title == "EnvironmentSetting"
    assert openapi_type.type == "object"
    assert openapi_type.required == ["name", "type", "default", "doc", "recompile", "update_model", "agent_restart"]


def test_post_operation(api_methods_fixture):
    post = UrlMethod(
        properties=MethodProperties.methods["dummy_post_with_parameters"][0],
        slice=None,
        method_name="dummy_post_with_parameters",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method_with_request_body(post, "/operation")
    assert "X-Inmanta-tid" in [parameter.name for parameter in operation.parameters]
    assert "param" in operation.requestBody.content["application/json"].schema_.properties.keys()
    assert "id" in operation.requestBody.content["application/json"].schema_.properties.keys()
    assert "X-Inmanta-tid" in operation.responses["200"].headers.keys()


def test_get_operation(api_methods_fixture):
    get = UrlMethod(
        properties=MethodProperties.methods["dummy_get_with_parameters"][0],
        slice=None,
        method_name="dummy_get_with_parameters",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method_without_request_body(get, "/operation")
    assert "X-Inmanta-tid" in [parameter.name for parameter in operation.parameters]
    assert "param" in [parameter.name for parameter in operation.parameters]
    assert "id" in [parameter.name for parameter in operation.parameters]
    assert not operation.requestBody
    assert "X-Inmanta-tid" in operation.responses["200"].headers.keys()


@pytest.mark.asyncio
async def test_openapi_endpoint(client):
    result = await client.get_api_docs("openapi")
    assert result.code == 200
    openapi_spec = result.result["data"]
    openapi_v3_spec_validator.validate(openapi_spec)
