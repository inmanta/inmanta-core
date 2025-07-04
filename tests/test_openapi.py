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

import enum
import inspect
import json
from datetime import datetime
from typing import Literal, Optional, Union
from uuid import UUID

import pydantic
import pytest
from openapi_spec_validator import openapi_v30_spec_validator
from pydantic.networks import AnyHttpUrl, AnyUrl, PostgresDsn

from inmanta.const import ClientType, CoreAuthorizationLabel, ResourceAction
from inmanta.data import model
from inmanta.data.model import EnvironmentSetting
from inmanta.protocol import method
from inmanta.protocol.auth.decorators import auth
from inmanta.protocol.common import ArgOption, BaseHttpException, MethodProperties, UrlMethod
from inmanta.protocol.openapi.converter import (
    ArgOptionHandler,
    FunctionParameterHandler,
    OpenApiConverter,
    OpenApiTypeConverter,
    OperationHandler,
)
from inmanta.protocol.openapi.model import MediaType, OpenApiDataTypes, ParameterType, Schema
from inmanta.server import SLICE_SERVER, config
from inmanta.server.extensions import FeatureManager
from inmanta.server.protocol import Server


class DummyException(BaseHttpException):
    def __init__(self):
        super().__init__(status_code=405)


@pytest.fixture
def feature_manager(server: Server) -> FeatureManager:
    return server.get_slice(SLICE_SERVER).feature_manager


@pytest.fixture(scope="function")
def api_methods_fixture(clean_reset):
    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(path="/simpleoperation", client_types=[ClientType.api, ClientType.agent], envelope=True)
    def post_method() -> str:
        return ""

    @method(path="/simpleoperation", client_types=[ClientType.agent], operation="GET")
    def get_method():
        pass

    arg_options = {
        "header": ArgOption(header="header-val", reply_header=True, getter=lambda x, y: "test"),
        "non_header": ArgOption(getter=lambda x, y: "test"),
    }

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(path="/operation/<id>", client_types=[ClientType.api, ClientType.agent], envelope=True, arg_options=arg_options)
    def dummy_post_with_parameters(header: str, non_header: str, param: int, id: UUID) -> str:
        """
        This is a brief description.

        This is a more in depth description of the method.

        :param header: A header value.
        :param non_header: Non header value via arg_options.
        :param param: A parameter.
        :param id: The id of the resource.
        :return: A return value.
        :raises OSError: Something went wrong
        :raises NotFound: Resource was not found.
        :raises test_openapi.DummyException: A dummy exception
        """
        return ""

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(
        path="/operation/<id>",
        client_types=[ClientType.api, ClientType.agent],
        envelope=True,
        arg_options=arg_options,
        operation="GET",
    )
    def dummy_get_with_parameters(header: str, non_header: str, param: int, id: UUID) -> str:
        """
        This is a brief description.

        This is a more in depth description of the method.

        :param header: A header value.
        :param non_header: Non header value via arg_options.
        :param param: A parameter.
        :param id: The id of the resource.
        :return: A return value.
        :raises OSError: Something went wrong
        :raises NotFound: Resource was not found.
        :raises test_openapi.DummyException: A dummy exception
        """
        return ""

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(path="/operation/<id>", client_types=[ClientType.api, ClientType.agent], envelope=True, arg_options=arg_options)
    def dummy_post_with_parameters_no_docstring(header: str, non_header: str, param: int, id: UUID) -> str:
        return ""

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(
        path="/operation/<id>",
        client_types=[ClientType.api, ClientType.agent],
        envelope=True,
        arg_options=arg_options,
        operation="GET",
    )
    def dummy_get_with_parameters_no_docstring(header: str, non_header: str, param: int, id: UUID) -> str:
        return ""

    arg_options_partial_doc = {
        "tid_doc": ArgOption(header="header-doc", reply_header=True, getter=lambda x, y: "test"),
        "tid_no_doc": ArgOption(header="header-no-doc", reply_header=True, getter=lambda x, y: "test"),
    }

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(
        path="/operation/<id_doc>/<id_no_doc>",
        client_types=[ClientType.api, ClientType.agent],
        envelope=True,
        arg_options=arg_options_partial_doc,
    )
    def dummy_post_with_parameters_partial_documentation(
        tid_doc: UUID, tid_no_doc: UUID, param_doc: int, param_no_doc: int, id_doc: UUID, id_no_doc: UUID
    ) -> str:
        """
        This is a brief description.

        :param tid_doc: The inmanta environment id.
        :param param_doc: A parameter.
        :param id_doc: The id of the resource.
        """
        return ""

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(
        path="/operation/<id_doc>/<id_no_doc>",
        client_types=[ClientType.api, ClientType.agent],
        envelope=True,
        arg_options=arg_options_partial_doc,
        operation="GET",
    )
    def dummy_get_with_parameters_partial_documentation(
        tid_doc: UUID, tid_no_doc: UUID, param_doc: int, param_no_doc: int, id_doc: UUID, id_no_doc: UUID
    ) -> str:
        """
        This is a brief description.

        :param tid_doc: The inmanta environment id.
        :param param_doc: A parameter.
        :param id_doc: The id of the resource.
        """
        return ""

    @auth(auth_label=CoreAuthorizationLabel.TEST, read_only=True)
    @method(
        path="/default/<id>",
        client_types=[ClientType.api],
        envelope=True,
        operation="GET",
    )
    def dummy_get_with_default_values(
        no_def: int, id: int = 5, param: str = "test", fl: float = 0.1, opt: Optional[str] = None
    ) -> str:
        return ""


async def test_generate_openapi_definition(server: Server):
    feature_manager = server.get_slice(SLICE_SERVER).feature_manager
    global_url_map = server._transport.get_global_url_map(server.get_slices().values())
    openapi = OpenApiConverter(global_url_map, feature_manager)
    openapi_json = openapi.generate_openapi_json()
    assert openapi_json
    openapi_parsed = json.loads(openapi_json)
    openapi_v30_spec_validator.validate(openapi_parsed)
    assert "https" not in openapi_parsed["servers"][0]["url"]
    # enable https
    config.server_ssl_key.set("ssl_key")
    config.server_ssl_cert.set("ssl_cert")
    openapi_json = openapi.generate_openapi_json()
    assert openapi_json
    openapi_parsed = json.loads(openapi_json)
    assert "https" in openapi_parsed["servers"][0]["url"]


def test_filter_api_methods(server, api_methods_fixture, feature_manager):
    post = UrlMethod(properties=MethodProperties.methods["post_method"][0], slice=None, method_name="post_method", handler=None)
    methods = {
        "POST": post,
        "GET": UrlMethod(
            properties=MethodProperties.methods["get_method"][0], slice=None, method_name="get_method", handler=None
        ),
    }
    openapi = OpenApiConverter(server._transport.get_global_url_map(server.get_slices().values()), feature_manager)
    api_methods = openapi._filter_api_methods(methods)
    assert len(api_methods) == 1


def test_get_function_parameters(api_methods_fixture):
    url_method = UrlMethod(
        properties=MethodProperties.methods["dummy_get_with_parameters"][0],
        slice=None,
        method_name="dummy_get_with_parameters",
        handler=None,
    )
    function_parameter_handler = FunctionParameterHandler(
        OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()), "/basepath", url_method.properties
    )
    function_parameters = function_parameter_handler.all_params_dct
    assert len(function_parameters) == 4
    assert function_parameters["param"] == inspect.Parameter("param", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)


def test_return_value(api_methods_fixture):
    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))

    json_response_content = operation_handler._build_return_value_wrapper(MethodProperties.methods["post_method"][0])
    assert json_response_content == {
        "application/json": MediaType(schema=Schema(type="object", properties={"data": Schema(type="string")}))
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
    assert openapi_type.ref == type_converter.openapi_ref_prefix + "Environment"

    environment_type = type_converter.resolve_reference(openapi_type.ref)
    assert environment_type.required == ["id", "name", "project_id", "repo_url", "repo_branch", "settings", "halted"]


def test_openapi_types_union() -> None:
    # Test union type
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Union[str, bytes, Literal["test"]])
    assert openapi_type == Schema(
        anyOf=[
            Schema(type="string"),
            Schema(type="string", format="binary"),
            Schema(type="string", enum=["test"]),
        ]
    )

    # Test union type wrapped into an object
    class Test(pydantic.BaseModel):
        val: Union[str, bytes, Literal["test"]]

    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Test)
    schema_ref = f"{type_converter.openapi_ref_prefix}{Test.__name__}"
    assert openapi_type.ref == schema_ref
    schema_test_obj = type_converter.components.schemas[Test.__name__]
    assert schema_test_obj.title == Test.__name__
    assert schema_test_obj.required == ["val"]
    assert len(schema_test_obj.properties) == 1
    schema_val_property = schema_test_obj.properties["val"]
    assert schema_val_property == Schema(
        title="Val",
        anyOf=[
            Schema(type="string"),
            Schema(type="string", format="binary"),
            Schema(type="string", enum=["test"]),
        ],
    )


def test_openapi_types_optional():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Optional[str])
    assert openapi_type == Schema(type="string", nullable=True)


def test_openapi_types_list():
    # Test list type
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(list[Union[int, UUID, Literal["test"]]])
    assert openapi_type == Schema(
        type="array",
        items=Schema(
            anyOf=[
                Schema(type="integer"),
                Schema(type="string", format="uuid"),
                Schema(type="string", enum=["test"]),
            ]
        ),
    )

    # Test list type wrapped into an object
    class Test(pydantic.BaseModel):
        val: list[Union[int, UUID, Literal["test"]]]

    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Test)
    schema_ref = f"{type_converter.openapi_ref_prefix}{Test.__name__}"
    assert openapi_type.ref == schema_ref
    schema_test_obj = type_converter.components.schemas[Test.__name__]
    assert schema_test_obj.title == Test.__name__
    assert schema_test_obj.required == ["val"]
    assert schema_test_obj.type == "object"
    assert len(schema_test_obj.properties) == 1
    schema_array = schema_test_obj.properties["val"]
    assert schema_array == Schema(
        title="Val",
        type="array",
        items=Schema(
            anyOf=[
                Schema(type="integer"),
                Schema(type="string", format="uuid"),
                Schema(type="string", enum=["test"]),
            ]
        ),
    )


def test_openapi_types_enum():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(list[ResourceAction])
    assert openapi_type.type == "array"
    assert openapi_type.items.ref == type_converter.openapi_ref_prefix + "ResourceAction"

    resource_action_type = type_converter.components.schemas["ResourceAction"]
    assert resource_action_type.type == "string"
    assert resource_action_type.enum == ["store", "push", "pull", "deploy", "dryrun", "getfact", "other"]


def test_openapi_types_dict():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(dict[str, UUID])
    assert openapi_type == Schema(type="object", additionalProperties=Schema(type="string", format="uuid"))


def test_openapi_types_list_of_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(list[model.Project])
    assert openapi_type.type == "array"
    assert openapi_type.items.ref == type_converter.openapi_ref_prefix + "Project"


def test_openapi_types_list_of_list_of_optional_model():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(list[list[Optional[model.Project]]])
    assert openapi_type.type == "array"
    assert openapi_type.items.type == "array"
    assert openapi_type.items.items.ref == type_converter.openapi_ref_prefix + "Project"
    assert openapi_type.items.items.nullable


def test_openapi_types_dict_of_union():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(dict[str, Union[model.Project, model.Environment, Literal["test"]]])
    assert openapi_type.type == "object"
    assert len(openapi_type.additionalProperties.anyOf) == 3
    assert openapi_type.additionalProperties.anyOf[0].ref == type_converter.openapi_ref_prefix + "Project"
    assert openapi_type.additionalProperties.anyOf[1].ref == type_converter.openapi_ref_prefix + "Environment"
    assert openapi_type.additionalProperties.anyOf[2] == Schema(type="string", enum=["test"])


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
    assert openapi_type == Schema(type="number")


def test_openapi_types_bytes():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(bytes)
    assert openapi_type == Schema(type="string", format="binary")


def test_openapi_types_uuid():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(UUID)
    assert openapi_type == Schema(type="string", format="uuid")


def test_openapi_types_literal() -> None:
    # Test literal type
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Literal["test"])
    assert openapi_type == Schema(type="string", enum=["test"])

    # Test literal type wrapped into an object
    class Test(pydantic.BaseModel):
        val: Literal["test"]

    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(Test)
    schema_ref = f"{type_converter.openapi_ref_prefix}{Test.__name__}"
    assert openapi_type.ref == schema_ref
    schema_test_obj = type_converter.components.schemas[Test.__name__]
    assert schema_test_obj.title == Test.__name__
    assert schema_test_obj.required == ["val"]
    assert len(schema_test_obj.properties) == 1
    schema_val_property = schema_test_obj.properties["val"]
    assert schema_val_property == Schema(title="Val", type="string", enum=["test"])


def test_openapi_types_anyurl():
    type_converter = OpenApiTypeConverter()

    openapi_type = type_converter.get_openapi_type(AnyUrl)
    assert openapi_type == Schema(type="string", format="uri")

    openapi_type = type_converter.get_openapi_type(AnyHttpUrl)
    assert openapi_type == Schema(type="string", format="uri")

    openapi_type = type_converter.get_openapi_type(PostgresDsn)
    assert openapi_type == Schema(type="string", format="multi-host-uri")


def test_openapi_types_env_setting():
    type_converter = OpenApiTypeConverter()
    openapi_type = type_converter.get_openapi_type(EnvironmentSetting)
    assert openapi_type.ref == type_converter.openapi_ref_prefix + "EnvironmentSetting"

    env_settings_type = type_converter.resolve_reference(openapi_type.ref)
    assert env_settings_type.title == "EnvironmentSetting"
    assert env_settings_type.type == "object"
    assert env_settings_type.required == ["name", "type", "default", "doc", "recompile", "update_model", "agent_restart"]


def test_post_operation(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    POST method which is fully annotated and documented.
    """
    short_description = "This is a brief description."
    long_description = "This is a more in depth description of the method."
    header_description = "A header value."
    non_header_description = "Non header value via arg_options."
    param_description = "A parameter."
    id_description = "The id of the resource."
    return_value_description = "A return value."
    raises_os_error_description = "Something went wrong"
    raises_not_found_description = "Resource was not found."
    raises_dummy_exception_description = "A dummy exception"
    method_name = "dummy_post_with_parameters"

    post = UrlMethod(
        properties=MethodProperties.methods["dummy_post_with_parameters"][0],
        slice=None,
        method_name=method_name,
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(post, "/operation/<id>")

    # Asserts on request body
    expected_params = ["param", "non_header"]
    actual_params = list(operation.requestBody.content["application/json"].schema_.properties.keys())
    assert sorted(expected_params) == sorted(actual_params)
    assert (
        f"* **non_header:** {non_header_description}\n* **param:** {param_description}\n" == operation.requestBody.description
    )

    # Asserts on parameters
    assert operation.summary == short_description
    assert operation.description == long_description
    assert operation.operationId == method_name
    assert sorted(["header-val", "id"]) == sorted([parameter.name for parameter in operation.parameters])
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 2
    assert param_map["header-val"] == header_description
    assert param_map["id"] == id_description

    # Asserts on response
    assert len(operation.responses) == 4
    assert operation.responses["200"].description == return_value_description
    assert operation.responses["404"].description == raises_not_found_description
    assert operation.responses["405"].description == raises_dummy_exception_description
    assert operation.responses["500"].description == raises_os_error_description


def test_get_operation(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    GET method which is fully annotated and documented.
    """
    short_description = "This is a brief description."
    long_description = "This is a more in depth description of the method."
    header_description = "A header value."
    non_header_description = "Non header value via arg_options."
    param_description = "A parameter."
    id_description = "The id of the resource."
    return_value_description = "A return value."
    raises_os_error_description = "Something went wrong"
    raises_not_found_description = "Resource was not found."
    raises_dummy_exception_description = "A dummy exception"
    method_name = "dummy_get_with_parameters"

    get = UrlMethod(
        properties=MethodProperties.methods["dummy_get_with_parameters"][0],
        slice=None,
        method_name=method_name,
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(get, "/operation/<id>")

    # Asserts on request body
    assert operation.requestBody is None

    # Asserts on parameters
    assert operation.summary == short_description
    assert operation.description == long_description
    assert operation.operationId == method_name
    assert sorted(["header-val", "non_header", "param", "id"]) == sorted([parameter.name for parameter in operation.parameters])
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 4
    assert param_map["header-val"] == header_description
    assert param_map["non_header"] == non_header_description
    assert param_map["param"] == param_description
    assert param_map["id"] == id_description

    # Asserts on response
    assert len(operation.responses) == 4
    assert operation.responses["200"].description == return_value_description
    assert operation.responses["404"].description == raises_not_found_description
    assert operation.responses["405"].description == raises_dummy_exception_description
    assert operation.responses["500"].description == raises_os_error_description


def test_post_operation_no_docstring(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    POST method which doesn't have a docstring.
    """
    post = UrlMethod(
        properties=MethodProperties.methods["dummy_post_with_parameters_no_docstring"][0],
        slice=None,
        method_name="dummy_post_with_parameters_no_docstring",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(post, "/operation/<id>")

    # Asserts on request body
    expected_params = ["param", "non_header"]
    actual_params = list(operation.requestBody.content["application/json"].schema_.properties.keys())
    assert sorted(expected_params) == sorted(actual_params)
    assert operation.requestBody.description == "* **non_header:**\n* **param:**\n"

    # Asserts on parameters
    assert operation.summary is None
    assert operation.description is None
    assert sorted(["header-val", "id"]) == sorted([parameter.name for parameter in operation.parameters])
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 2
    assert param_map["header-val"] is None
    assert param_map["id"] is None

    # Asserts on response
    assert len(operation.responses) == 1
    assert ["header-val"] == list(operation.responses["200"].headers.keys())
    assert operation.responses["200"].description == ""


def test_get_operation_no_docstring(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    GET method which doesn't have a docstring.
    """
    get = UrlMethod(
        properties=MethodProperties.methods["dummy_get_with_parameters_no_docstring"][0],
        slice=None,
        method_name="dummy_get_with_parameters_no_docstring",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(get, "/operation/<id>")

    # Asserts on request body
    assert operation.requestBody is None

    # Asserts on parameters
    assert operation.summary is None
    assert operation.description is None
    assert sorted(["header-val", "non_header", "param", "id"]) == sorted([parameter.name for parameter in operation.parameters])
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 4
    assert param_map["header-val"] is None
    assert param_map["non_header"] is None
    assert param_map["param"] is None
    assert param_map["id"] is None

    # Asserts on response
    assert len(operation.responses) == 1
    assert ["header-val"] == list(operation.responses["200"].headers.keys())
    assert operation.responses["200"].description == ""


def test_post_operation_partial_documentation(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    POST method which has missing entries in its docstring.
    """
    short_description = "This is a brief description."
    tid_description = "The inmanta environment id."
    param_description = "A parameter."
    id_description = "The id of the resource."
    post = UrlMethod(
        properties=MethodProperties.methods["dummy_post_with_parameters_partial_documentation"][0],
        slice=None,
        method_name="dummy_post_with_parameters_partial_documentation",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(post, "/operation/<id_doc>/<id_no_doc>")

    # Asserts on request body
    request_body_parameters = list(operation.requestBody.content["application/json"].schema_.properties.keys())
    assert sorted(["param_doc", "param_no_doc"]) == sorted(request_body_parameters)
    assert operation.requestBody.description == f"* **param_doc:** {param_description}\n* **param_no_doc:**\n"

    # Asserts on parameters
    assert operation.summary == short_description
    assert operation.description is None
    expected_parameters = ["header-doc", "header-no-doc", "id_doc", "id_no_doc"]
    actual_parameters = [parameter.name for parameter in operation.parameters]
    assert sorted(expected_parameters) == sorted(actual_parameters)
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 4
    assert param_map["header-doc"] == tid_description
    assert param_map["header-no-doc"] is None
    assert param_map["id_doc"] == id_description
    assert param_map["id_no_doc"] is None

    # Asserts on response
    assert len(operation.responses) == 1
    assert sorted(["header-doc", "header-no-doc"]) == sorted(list(operation.responses["200"].headers.keys()))
    assert operation.responses["200"].description == ""


def test_get_operation_partial_documentation(api_methods_fixture):
    """
    Test whether an OpenAPI operation is constructed correctly for a
    GET method which has missing entries in its docstring.
    """
    short_description = "This is a brief description."
    tid_description = "The inmanta environment id."
    param_description = "A parameter."
    id_description = "The id of the resource."

    get = UrlMethod(
        properties=MethodProperties.methods["dummy_get_with_parameters_partial_documentation"][0],
        slice=None,
        method_name="dummy_get_with_parameters_partial_documentation",
        handler=None,
    )

    operation_handler = OperationHandler(OpenApiTypeConverter(), ArgOptionHandler(OpenApiTypeConverter()))
    operation = operation_handler.handle_method(get, "/operation/<id_doc>/<id_no_doc>")

    # Asserts on request body
    assert operation.requestBody is None

    # Asserts on parameters
    assert operation.summary == short_description
    assert operation.description is None

    expected_parameters = ["header-doc", "header-no-doc", "param_doc", "param_no_doc", "id_doc", "id_no_doc"]
    actual_parameters = [parameter.name for parameter in operation.parameters]
    assert sorted(expected_parameters) == sorted(actual_parameters)
    param_map = {param.name: param.description for param in operation.parameters}
    assert len(param_map) == 6
    assert param_map["header-doc"] == tid_description
    assert param_map["header-no-doc"] is None
    assert param_map["param_doc"] == param_description
    assert param_map["param_no_doc"] is None
    assert param_map["id_doc"] == id_description
    assert param_map["id_no_doc"] is None

    # Asserts on response
    assert len(operation.responses) == 1
    assert sorted(["header-doc", "header-no-doc"]) == sorted(list(operation.responses["200"].headers.keys()))
    assert operation.responses["200"].description == ""


async def test_openapi_endpoint(client):
    result = await client.get_api_docs("openapi")
    assert result.code == 200
    openapi_spec = result.result["data"]
    openapi_v30_spec_validator.validate(openapi_spec)


async def test_swagger_endpoint(client):
    result = await client.get_api_docs()
    assert result.code == 200


async def test_tags(server, feature_manager):
    global_url_map = server._transport.get_global_url_map(server.get_slices().values())
    openapi = OpenApiConverter(global_url_map, feature_manager)
    openapi_json = openapi.generate_openapi_json()
    openapi_parsed = json.loads(openapi_json)
    for path in openapi_parsed["paths"].values():
        for operation in path.values():
            assert len(operation["tags"]) > 0
    assert "core.project" in openapi_parsed["paths"]["/api/v1/project"]["get"]["tags"]


def test_openapi_schema() -> None:
    ref_prefix = "#/"
    schemas = {
        "person": Schema(
            **{
                "title": "Person",
                "properties": {
                    "address": {
                        "$ref": ref_prefix + "address",
                    },
                    "age": {
                        "title": "Age",
                        "type": "integer",
                    },
                },
            }
        ),
        "address": Schema(
            **{
                "title": "Address",
                "properties": {
                    "street": {
                        "title": "Street",
                        "type": "string",
                    },
                    "number": {
                        "title": "Number",
                        "type": "integer",
                    },
                    "city": {
                        "title": "City",
                        "type": "string",
                    },
                },
            }
        ),
    }

    assert schemas["person"] == Schema(
        title="Person",
        properties={
            "address": Schema(**{"$ref": ref_prefix + "address"}),
            "age": Schema(title="Age", type="integer"),
        },
    )

    assert schemas["address"] == Schema(
        title="Address",
        properties={
            "street": Schema(title="Street", type="string"),
            "number": Schema(title="Number", type="integer"),
            "city": Schema(title="City", type="string"),
        },
    )

    assert Schema(**{"$ref": ref_prefix + "person"}).resolve(ref_prefix, schemas) == schemas["person"]
    assert Schema(**{"$ref": ref_prefix + "address"}).resolve(ref_prefix, schemas) == schemas["address"]

    person_schema = schemas["person"].copy(deep=True)

    assert not Schema(**{"$ref": ref_prefix + "person"}).recursive_resolve(ref_prefix, schemas, update={}) == person_schema
    person_schema.properties["address"] = schemas["address"]
    assert Schema(**{"$ref": ref_prefix + "person"}).recursive_resolve(ref_prefix, schemas, update={}) == person_schema


def test_get_openapi_parameter_type_for(api_methods_fixture: None) -> None:
    """
    Verify whether the MethodProperties.get_openapi_parameter_type_for() method works as expected.
    """
    assert len(MethodProperties.methods["dummy_post_with_parameters_no_docstring"]) == 1
    method_properties = MethodProperties.methods["dummy_post_with_parameters_no_docstring"][0]
    assert method_properties.get_openapi_parameter_type_for("id") is ParameterType.path
    assert method_properties.get_openapi_parameter_type_for("header") is ParameterType.header
    assert method_properties.get_openapi_parameter_type_for("non_header") is None
    assert method_properties.get_openapi_parameter_type_for("param") is None

    assert len(MethodProperties.methods["dummy_get_with_parameters_no_docstring"]) == 1
    method_properties = MethodProperties.methods["dummy_get_with_parameters_no_docstring"][0]
    assert method_properties.get_openapi_parameter_type_for("id") is ParameterType.path
    assert method_properties.get_openapi_parameter_type_for("header") is ParameterType.header
    assert method_properties.get_openapi_parameter_type_for("non_header") is ParameterType.query
    assert method_properties.get_openapi_parameter_type_for("param") is ParameterType.query


def test_get_openapi_type_of_parameter(api_methods_fixture: None) -> None:
    """
    Verify whether the OpenApiTypeConverter.get_openapi_type_of_parameter() method works as expected.
    """
    type_converter = OpenApiTypeConverter()
    assert len(MethodProperties.methods["dummy_get_with_default_values"]) == 1
    method_properties = MethodProperties.methods["dummy_get_with_default_values"][0]
    param_dct = inspect.signature(method_properties.function).parameters
    for param_name, data_type, default_value, nullable in [
        ("no_def", OpenApiDataTypes.INTEGER.value, None, False),
        ("id", OpenApiDataTypes.INTEGER.value, 5, False),
        ("param", OpenApiDataTypes.STRING.value, "test", False),
        ("fl", OpenApiDataTypes.NUMBER.value, 0.1, False),
        ("opt", OpenApiDataTypes.STRING.value, None, True),
    ]:
        schema = type_converter.get_openapi_type_of_parameter(param_dct[param_name])
        assert schema.type == data_type
        assert schema.default == default_value
        assert schema.nullable if nullable else not schema.nullable


def test_get_openapi_type_for_on_enum() -> None:
    """
    Ensure that the type field is populated correctly when OpenApiTypeConverter.get_openapi_type() is called on an Enum.
    """

    class StrValEnum(enum.Enum):
        A = "a"
        B = "b"

    class IntValEnum(enum.Enum):
        A = 1
        B = 2

    class FloatValEnum(enum.Enum):
        A = 1
        B = 2.0

    class BoolValEnum(enum.Enum):
        A = True
        B = False

    openapi_type_converter = OpenApiTypeConverter()

    for python_type, openapi_type in [
        (StrValEnum, OpenApiDataTypes.STRING.value),
        (IntValEnum, OpenApiDataTypes.INTEGER.value),
        (FloatValEnum, OpenApiDataTypes.NUMBER.value),
        (BoolValEnum, OpenApiDataTypes.BOOLEAN.value),
    ]:
        schema = openapi_type_converter.get_openapi_type(python_type)
        resolved_schema = schema.resolve(openapi_type_converter.openapi_ref_prefix, openapi_type_converter.components.schemas)
        assert resolved_schema.type == openapi_type
