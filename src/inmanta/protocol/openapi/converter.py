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

import typing_inspect  # type: ignore
from pydantic.main import BaseModel
from pydantic.networks import AnyUrl
from pydantic.schema import model_schema

from inmanta import types, util
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
from inmanta.server.extensions import FeatureManager
from inmanta.types import ReturnTypes


def openapi_json_encoder(o) -> Union[ReturnTypes, util.JSONSerializable]:
    if isinstance(o, BaseModel):
        return o.dict(by_alias=True, exclude_none=True)
    return util.custom_json_encoder(o)


class OpenApiConverter:
    """
    Extracts API information for the OpenAPI definition from the server
    """

    def __init__(self, global_url_map: Dict[str, Dict[str, UrlMethod]], feature_manager: FeatureManager):
        self.global_url_map = global_url_map
        self.feature_manager = feature_manager
        self.type_converter = OpenApiTypeConverter()
        self.arg_option_handler = ArgOptionHandler(self.type_converter)

    def _collect_server_information(self) -> List[Server]:
        bind_port = config.get_bind_port()
        server_address = config.server_address.get()
        return [
            Server(url=AnyUrl(url=f"http://{server_address}:{bind_port}/", scheme="http", host=server_address, port=bind_port))
        ]

    def _get_inmanta_version(self) -> Optional[str]:
        metadata = self.feature_manager.get_product_metadata()
        return metadata["version"]

    def generate_openapi_definition(self) -> OpenAPI:
        version = self._get_inmanta_version()
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
            operation = operation_handler.handle_method(url_method, path)
            path_item.__setattr__(http_method_name.lower(), operation)
        return path_item

    def generate_openapi_json(self) -> str:
        openapi = self.generate_openapi_definition()

        return json.dumps(openapi, default=openapi_json_encoder)

    def generate_swagger_html(self) -> str:
        return self.get_swagger_html(self.generate_openapi_json())

    def get_swagger_html(self, openapi_spec: str) -> str:
        template = f"""
        <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="//unpkg.com/swagger-ui-dist@^3.25.0/swagger-ui-bundle.js"></script>
        <link rel="stylesheet" href="//unpkg.com/swagger-ui-dist@^3.25.0/swagger-ui.css" />
        <title>Inmanta Service Orchestrator API</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script>
            window.onload = function() {{
              SwaggerUIBundle({{
                spec: {openapi_spec},
                dom_id: '#swagger-ui',
                presets: [
                  SwaggerUIBundle.presets.apis
                ],
              }})
            }}
        </script>
    </body>
    </html>
        """

        return template


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
        list: Schema(type="array", items=Schema()),
        dict: Schema(type="object"),
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
        none_type_in_type_args = len(openapi_types) < len(type_args)
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
        self, method_properties: MethodProperties, function_parameters: Dict[str, inspect.Parameter]
    ) -> List[Parameter]:
        result: List[Parameter] = []
        for option_name, option in method_properties.arg_options.items():
            param = function_parameters[option_name]
            param_schema = self.type_converter.get_openapi_type_of_parameter(param)
            param_description = method_properties.get_description_for_param(option_name)
            if option.header:
                result.append(
                    Parameter(in_=ParameterType.header, name=option.header, schema_=param_schema, description=param_description)
                )
        return result

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

    def __init__(
        self,
        type_converter: OpenApiTypeConverter,
        arg_option_handler: ArgOptionHandler,
        path: str,
        method_properties: MethodProperties,
    ):
        self.type_converter = type_converter
        self.arg_option_handler = arg_option_handler
        self.path = path
        self.method_properties = method_properties

        # Get the parameters of the handler function
        self.all_params_dct: Dict[str, inspect.Parameter] = self._extract_function_parameters(method_properties.function)
        self.path_params: Dict[str, inspect.Parameter] = {}
        self.header_params: Dict[str, inspect.Parameter] = {}
        self.non_path_and_non_header_params: Dict[str, inspect.Parameter] = {}

        for param_name, param in self.all_params_dct.items():
            if f"{{{param_name}}}" in self.path:
                self.path_params[param_name] = param
            elif (
                param_name in self.method_properties.arg_options.keys()
                and self.method_properties.arg_options[param_name].header is not None
            ):
                self.header_params[param_name] = param
            else:
                self.non_path_and_non_header_params[param_name] = param

    # Parameters

    def _extract_function_parameters(self, url_method_function: Callable) -> Dict[str, inspect.Parameter]:
        function_parameters = {
            parameter_name: parameter_type
            for parameter_name, parameter_type in inspect.signature(url_method_function).parameters.items()
        }
        return function_parameters

    def get_parameters(self) -> List[Parameter]:
        result = self._convert_header_and_path_params()
        if self.method_properties.operation not in ["POST", "PUT", "PATCH"]:
            result.extend(self._convert_function_params_to_query_params())
        return result

    def _convert_header_and_path_params(self) -> List[Parameter]:
        arg_options_params: List[Parameter] = self.arg_option_handler.extract_parameters_from_arg_options(
            self.method_properties, self.all_params_dct
        )
        path_params: List[Parameter] = self._convert_path_params_to_openapi()
        return arg_options_params + path_params

    def _convert_path_params_to_openapi(self) -> List[Parameter]:
        parameters: List[Union[Parameter, Reference]] = []
        for parameter_name, parameter_type in self.path_params.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            param_description = self.method_properties.get_description_for_param(parameter_name)
            parameters.append(
                Parameter(
                    name=parameter_name,
                    in_=ParameterType.path,
                    required=True,
                    schema_=type_description,
                    description=param_description,
                )
            )
        return parameters

    def _convert_function_params_to_query_params(self) -> List[Parameter]:
        parameters: List[Parameter] = []
        for parameter_name, parameter_type in self.non_path_and_non_header_params.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            param_description = self.method_properties.get_description_for_param(parameter_name)
            parameters.append(
                Parameter(name=parameter_name, in_=ParameterType.query, schema_=type_description, description=param_description)
            )
        return parameters

    # Request body

    def convert_request_body(self) -> RequestBody:
        properties = self._convert_function_params_to_openapi_request_body_properties()
        return self._build_json_request_body(properties)

    def _convert_function_params_to_openapi_request_body_properties(self) -> Dict[str, Schema]:
        properties = {}
        for parameter_name, parameter_type in self.non_path_and_non_header_params.items():
            type_description = self.type_converter.get_openapi_type_of_parameter(parameter_type)
            properties[parameter_name] = type_description
        return properties

    def _get_request_body_description(self) -> str:
        """
        OpenAPI supports only a single description field for the full request body. As such,
        this method return the description of the request body in CommonMark syntax to create
        an itemization of the different parameters in the request body.
        """
        result = ""
        for param_name in sorted(self.non_path_and_non_header_params.keys()):
            description = self.method_properties.get_description_for_param(param_name)
            if description is not None:
                result += f"* **{param_name}:** {description}\n"
            else:
                result += f"* **{param_name}:**\n"
        return result

    def _build_json_request_body(self, properties: Dict) -> RequestBody:
        request_body = RequestBody(
            required=True,
            content={"application/json": MediaType(schema=Schema(type="object", properties=properties))},
            description=self._get_request_body_description(),
        )
        return request_body


class OperationHandler:
    """
    Builds an OpenAPI Operation object from an Inmanta UrlMethod
    """

    def __init__(self, type_converter: OpenApiTypeConverter, arg_option_handler: ArgOptionHandler):
        self.type_converter = type_converter
        self.arg_option_handler = arg_option_handler

    def handle_method(self, url_method: UrlMethod, path: str) -> Operation:
        function_parameter_handler = FunctionParameterHandler(
            self.type_converter, self.arg_option_handler, path, url_method.properties
        )
        parameters = function_parameter_handler.get_parameters()
        responses = self._build_responses(url_method.properties)

        if url_method.get_operation() in ["POST", "PUT", "PATCH"]:
            extra_params = {"requestBody": function_parameter_handler.convert_request_body()}
        else:
            extra_params = {}

        tags = self._get_tags_of_operation(url_method)

        return Operation(
            responses=responses,
            operationId=url_method.method_name,
            parameters=(parameters if len(parameters) else None),
            summary=url_method.short_method_description,
            description=url_method.long_method_description,
            tags=tags,
            **extra_params,
        )

    def _get_tags_of_operation(self, url_method: UrlMethod) -> Optional[List[str]]:
        if url_method.endpoint is not None:
            if hasattr(url_method.endpoint, "_name"):
                return [url_method.endpoint._name]
            else:
                return [url_method.endpoint.__class__.__name__]
        else:
            return None

    def _build_responses(self, url_method_properties: MethodProperties) -> Dict[str, Response]:
        result: Dict[str, Response] = {}
        status_code_to_description_map = url_method_properties.get_description_foreach_http_status_code()
        for status_code, description in status_code_to_description_map.items():
            if status_code == 200:
                response_headers = self.arg_option_handler.extract_response_headers_from_arg_options(
                    url_method_properties.arg_options
                )
                return_value = self._build_return_value_wrapper(url_method_properties)
                result[str(status_code)] = Response(description=description, content=return_value, headers=response_headers)
            else:
                result[str(status_code)] = Response(description=description)

        return result

    def _build_return_value_wrapper(self, url_method_properties: MethodProperties) -> Optional[Dict[str, MediaType]]:
        return_type = inspect.signature(url_method_properties.function).return_annotation
        if return_type is not None and return_type != inspect.Signature.empty:
            return_properties: Optional[Dict[str, SchemaBase]] = None
            openapi_return_type = self.type_converter.get_openapi_type(return_type)
            if url_method_properties.envelope:
                return_properties = {url_method_properties.envelope_key: openapi_return_type}
            return {"application/json": MediaType(schema=Schema(type="object", properties=return_properties))}
        return None
