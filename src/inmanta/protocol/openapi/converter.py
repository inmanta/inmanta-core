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
import typing
import uuid
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional, Type, Union

import typing_inspect
from pydantic.main import BaseModel
from pydantic.networks import AnyUrl
from pydantic.schema import model_schema

from inmanta import types, util
from inmanta.const import INMANTA_MT_HEADER
from inmanta.protocol.common import ArgOption, MethodProperties, UrlMethod
from inmanta.protocol.openapi.model import (
    Components,
    Header,
    Info,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    ParameterType,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
    SchemaBase,
    Server,
)
from inmanta.server import config
from inmanta.util import get_compiler_version


def openapi_json_encoder(o) -> Union[Dict, str, List]:
    if isinstance(o, BaseModel):
        return o.dict(by_alias=True, exclude_none=True)
    return util.custom_json_encoder(o)


class OpenApiConverter:
    """
        Extracts API information for the OpenAPI definition from the server
    """

    def __init__(self, global_url_map: Dict[str, Dict[str, UrlMethod]]):
        self.global_url_map = global_url_map
        self.type_converter = OpenApiTypeConverter()
        self.arg_option_handler = ArgOptionHandler(self.type_converter)

    def _collect_server_information(self) -> List[Server]:
        bind_port = config.get_bind_port()
        bind_addresses = config.server_bind_address.get()
        return [
            Server(url=AnyUrl(url=f"http://{bind_address}:{bind_port}/", scheme="http", host=bind_address, port=bind_port))
            for bind_address in bind_addresses
        ]

    def generate_openapi_definition(self) -> OpenAPI:
        version = get_compiler_version()
        info = Info(title="Inmanta Service Orchestrator", version=version if version else "")
        servers = self._collect_server_information()
        paths = {}
        for path, methods in self.global_url_map.items():
            api_methods = self._filter_api_methods(methods)
            if len(api_methods) > 0:
                path_in_openapi_format = self._format_path(path)
                path_item = self._extract_operations_from_methods(api_methods, path_in_openapi_format)
                paths[path_in_openapi_format] = path_item
        return OpenAPI(openapi="3.0.2", info=info, paths=paths, servers=servers, components=self.type_converter.components)

    def _filter_api_methods(self, methods: Dict[str, UrlMethod]) -> Dict[str, UrlMethod]:
        return {
            method_name: url_method
            for method_name, url_method in methods.items()
            if "api" in url_method.properties.client_types
        }

    def _format_path(self, path: str) -> str:
        return path.replace("(?P<", "{").replace(">[^/]+)", "}")

    def _extract_operations_from_methods(self, api_methods: Dict[str, UrlMethod], path: str) -> PathItem:
        path_item = PathItem()
        for http_method_name, url_method in api_methods.items():
            operation_handler = OperationHandler(self.type_converter, self.arg_option_handler)
            if http_method_name in ["POST", "PUT", "PATCH"]:
                operation = operation_handler.handle_method_with_request_body(url_method, path)
            else:
                operation = operation_handler.handle_method_without_request_body(url_method, path)

            path_item.__setattr__(http_method_name.lower(), operation)
        return path_item

    def generate_openapi_json(self) -> str:
        openapi = self.generate_openapi_definition()

        return json.dumps(openapi, default=openapi_json_encoder)


class OpenApiTypeConverter:
    """
        Lookup for OpenAPI types corresponding to python types
    """

    components = Components(schemas={})

    python_to_openapi_types = {
        bool: Schema(type="boolean"),
        int: Schema(type="integer"),
        str: Schema(type="string"),
        tuple: Schema(type="array", items=Schema()),
        float: Schema(type="number", format="float"),
        bytes: Schema(type="string", format="binary"),
        datetime: Schema(type="string", format="date-time"),
        uuid.UUID: Schema(type="string", format="uuid"),
        typing.Any: Schema(),
        types.StrictNonIntBool: Schema(type="boolean"),
    }

    def get_openapi_type_of_parameter(self, parameter_type: inspect.Parameter) -> Schema:
        type_annotation = parameter_type.annotation
        return self.get_openapi_type(type_annotation)

    def _is_none_type(self, type_annotation: Type) -> bool:
        return inspect.isclass(type_annotation) and issubclass(type_annotation, type(None))

    def _handle_union_type(self, type_annotation: Type) -> Schema:
        # An Optional is always a Union
        type_args = typing_inspect.get_args(type_annotation, evaluate=True)
        openapi_types = [self.get_openapi_type(type_arg) for type_arg in type_args if not self._is_none_type(type_arg)]
        none_type_in_type_args = len([type_arg for type_arg in type_args if self._is_none_type(type_arg)]) > 0
        if none_type_in_type_args:
            if len(openapi_types) == 1:
                openapi_type = openapi_types[0].copy(deep=True)
                # An Optional in the OpenAPI Schema is nullable
                openapi_type.nullable = True
                return openapi_type
            return Schema(anyOf=openapi_types, nullable=True)
        # A Union type can be expressed as a schema that matches any of the type arguments
        return Schema(anyOf=openapi_types)

    def _handle_dictionary(self, type_annotation: Type) -> Schema:
        type_args = typing_inspect.get_args(type_annotation, evaluate=True)
        return Schema(type="object", additionalProperties=self.get_openapi_type(type_args[1]))

    def _handle_pydantic_model(self, type_annotation: Type) -> Schema:
        # JsonSchema stores the model (and sub-model) definitions at #/definitions,
        # but OpenAPI requires them to be placed at "#/components/schemas/"
        # The ref_prefix changes the references, but the actual schemas are still at #/definitions
        schema = model_schema(type_annotation, by_alias=True, ref_prefix="#/components/schemas/")
        if "definitions" in schema.keys():
            definitions = schema.pop("definitions")
            if self.components.schemas is not None:
                self.components.schemas.update(definitions)
        return Schema(**schema)

    def _handle_enums(self, type_annotation: Type) -> Schema:
        enum_keys = [name for name in type_annotation.__members__.keys()]
        return Schema(type="string", enum=enum_keys)

    def _handle_list(self, type_annotation: Type) -> Schema:
        # Type argument is always present, see protocol.common.MethodProperties._validate_type_arg()
        list_member_type = typing_inspect.get_args(type_annotation, evaluate=True)
        return Schema(type="array", items=self.get_openapi_type(list_member_type[0]))

    def get_openapi_type(self, type_annotation: Type) -> Schema:
        type_origin = typing_inspect.get_origin(type_annotation)
        if typing_inspect.is_union_type(type_annotation):
            return self._handle_union_type(type_annotation)
        elif inspect.isclass(type_annotation) and issubclass(type_annotation, BaseModel):
            return self._handle_pydantic_model(type_annotation)
        elif inspect.isclass(type_annotation) and issubclass(type_annotation, Enum):
            return self._handle_enums(type_annotation)
        elif inspect.isclass(type_origin) and issubclass(type_origin, typing.Mapping):
            return self._handle_dictionary(type_annotation)
        elif inspect.isclass(type_origin) and issubclass(type_origin, typing.Sequence):
            return self._handle_list(type_annotation)
        # Fallback to primitive types
        return self.python_to_openapi_types.get(type_annotation, Schema(type="object"))


class ArgOptionHandler:
    """
        Extracts header, response header and path parameter information from ArgOptions
    """

    def __init__(self, type_converter: OpenApiTypeConverter):
        self.type_converter = type_converter

    def extract_parameters_from_arg_options(
        self, path: str, arg_options: Dict[str, ArgOption], function_parameters: Dict[str, inspect.Parameter]
    ) -> List[Union[Parameter, Reference]]:
        parameters: List[Union[Parameter, Reference]] = []
        for option_name, option in arg_options.items():
            param = function_parameters[option_name]
            param_schema = self.type_converter.get_openapi_type_of_parameter(param)
            if option.header:
                parameters.append(Parameter(in_=ParameterType.header, name=option.header, schema_=param_schema))
            elif f"{{{option_name}}}" in path:
                parameters.append(Parameter(in_=ParameterType.path, name=option_name, required=True, schema_=param_schema))
        return parameters

    def extract_response_headers_from_arg_options(
        self, arg_options: Dict[str, ArgOption]
    ) -> Optional[Dict[str, Union[Header, Reference]]]:
        headers: Dict[str, Union[Header, Reference]] = {}
        for option_name, option in arg_options.items():
            if option.header and option.reply_header:
                headers[option.header] = Header(description=option.header, schema=Schema(type="string"))
        return headers if headers else None


class FunctionParameterHandler:
    """
        Creates OpenAPI Parameters and RequestBody items based on the handler function parameters
    """

    def __init__(self, type_converter: OpenApiTypeConverter, arg_option_handler: ArgOptionHandler, path: str):
        self.type_converter = type_converter
        self.arg_option_handler = arg_option_handler
        self.path = path
        self.path_params: Dict[str, inspect.Parameter] = {}
        self.non_path_params: Dict[str, inspect.Parameter] = {}

    def _extract_function_parameters(self, url_method_function: Callable) -> Dict[str, inspect.Parameter]:
        function_parameters = {
            parameter_name: parameter_type
            for parameter_name, parameter_type in inspect.signature(url_method_function).parameters.items()
        }
        return function_parameters

    def convert_function_params_to_query_params(self) -> List[Union[Parameter, Reference]]:
        parameters: List[Union[Parameter, Reference]] = []
        for parameter_name, parameter_type in self.non_path_params.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            parameters.append(Parameter(name=parameter_name, in_=ParameterType.query, schema_=type_description))
        return parameters

    def _convert_function_params_to_openapi_request_body_properties(
        self, function_parameters: Dict[str, inspect.Parameter]
    ) -> Dict[str, Schema]:
        properties = {}
        for parameter_name, parameter_type in function_parameters.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            properties[parameter_name] = type_description
        return properties

    def _convert_path_params_to_openapi(
        self, function_parameters: Dict[str, inspect.Parameter]
    ) -> List[Union[Parameter, Reference]]:
        parameters: List[Union[Parameter, Reference]] = []
        for parameter_name, parameter_type in function_parameters.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            parameters.append(Parameter(name=parameter_name, in_=ParameterType.path, required=True, schema_=type_description))
        return parameters

    def _filter_path_params(self, function_parameters: Dict[str, inspect.Parameter]) -> Dict[str, inspect.Parameter]:
        return {
            parameter_name: parameter_type
            for parameter_name, parameter_type in function_parameters.items()
            if f"{{{parameter_name}}}" in self.path
        }

    def _filter_non_path_params(self, function_parameters: Dict[str, inspect.Parameter]) -> Dict[str, inspect.Parameter]:
        non_path_params = {
            parameter_name: parameter_type
            for parameter_name, parameter_type in function_parameters.items()
            if parameter_name not in self.path_params.keys()
        }
        return non_path_params

    def _filter_already_processed_function_params(
        self, function_parameters: Dict[str, inspect.Parameter], already_existing_parameters: List[Union[Parameter, Reference]]
    ) -> Dict[str, inspect.Parameter]:
        parameter_names = [parameter.name for parameter in already_existing_parameters if isinstance(parameter, Parameter)]
        return {
            parameter_name: parameter_type
            for parameter_name, parameter_type in function_parameters.items()
            if parameter_name == "tid"
            and INMANTA_MT_HEADER not in parameter_names
            or parameter_name != "tid"
            and parameter_name not in parameter_names
        }

    def convert_header_and_path_params(self, method_properties: MethodProperties) -> List[Union[Parameter, Reference]]:
        # Get the parameters of the handler function
        function_parameters = self._extract_function_parameters(method_properties.function)
        # Create OpenAPI Parameter objects based on the ArgOptions
        parameters: List[Union[Parameter, Reference]] = self.arg_option_handler.extract_parameters_from_arg_options(
            self.path, method_properties.arg_options, function_parameters
        )
        # Remove the function parameters from the list, that already have an OpenAPI Parameter object
        function_parameters = self._filter_already_processed_function_params(function_parameters, parameters)

        # Separate the path and non-path parameters
        self.path_params = self._filter_path_params(function_parameters)
        self.non_path_params = self._filter_non_path_params(function_parameters)

        # Create OpenAPI Parameter objects for the path parameters and add them to the parameter list
        openapi_path_params = self._convert_path_params_to_openapi(self.path_params)
        parameters.extend(openapi_path_params)
        return parameters

    def convert_request_body(self) -> RequestBody:
        properties = self._convert_function_params_to_openapi_request_body_properties(self.non_path_params)
        return self.build_json_request_body(properties)

    def build_json_request_body(self, properties: Dict) -> RequestBody:
        request_body = RequestBody(
            required=True, content={"application/json": MediaType(schema=Schema(type="object", properties=properties))}
        )
        return request_body


class OperationHandler:
    """
        Builds an OpenAPI Operation object from an Inmanta UrlMethod
    """

    def __init__(self, type_converter: OpenApiTypeConverter, arg_option_handler: ArgOptionHandler):
        self.type_converter = type_converter
        self.arg_option_handler = arg_option_handler

    def handle_method_with_request_body(self, url_method: UrlMethod, path: str) -> Operation:
        function_parameter_handler = FunctionParameterHandler(self.type_converter, self.arg_option_handler, path)
        parameters = function_parameter_handler.convert_header_and_path_params(url_method.properties)
        request_body = function_parameter_handler.convert_request_body()
        ok_response = self._build_response(path, url_method.properties)
        responses = {"200": ok_response}
        return Operation(responses=responses, parameters=(parameters if len(parameters) else None), requestBody=request_body,)

    def handle_method_without_request_body(self, url_method: UrlMethod, path: str) -> Operation:
        function_parameter_handler = FunctionParameterHandler(self.type_converter, self.arg_option_handler, path)
        parameters = function_parameter_handler.convert_header_and_path_params(url_method.properties)
        query_params = function_parameter_handler.convert_function_params_to_query_params()
        parameters.extend(query_params)

        ok_response = self._build_response(path, url_method.properties)

        responses = {"200": ok_response}
        return Operation(responses=responses, parameters=(parameters if len(parameters) else None),)

    def _build_response(self, description: str, url_method_properties: MethodProperties) -> Response:
        response_headers = self.arg_option_handler.extract_response_headers_from_arg_options(url_method_properties.arg_options)
        return_value = self._build_return_value_wrapper(url_method_properties)
        return Response(description=description, content=return_value, headers=response_headers)

    def _build_return_value_wrapper(self, url_method_properties: MethodProperties) -> Optional[Dict[str, MediaType]]:
        return_type = inspect.signature(url_method_properties.function).return_annotation
        if return_type is not None and return_type != inspect.Signature.empty:
            return_properties: Optional[Dict[str, SchemaBase]] = None
            openapi_return_type = self.type_converter.get_openapi_type(return_type)
            if url_method_properties.envelope:
                return_properties = {url_method_properties.envelope_key: openapi_return_type}
            return {"application/json": MediaType(schema=Schema(type="object", properties=return_properties))}
        return None
