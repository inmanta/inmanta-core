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
import itertools
import json
import logging
import re
from collections.abc import Sequence
from typing import Callable, Optional, Union

from pydantic import ConfigDict
from typing_inspect import get_args, get_origin, is_generic_type

from inmanta import util
from inmanta.const import INMANTA_MT_HEADER
from inmanta.data.model import BaseModel
from inmanta.protocol.common import ArgOption, MethodProperties, ReturnValue, UrlMethod
from inmanta.protocol.openapi.model import (
    CodeSample,
    Components,
    Header,
    Info,
    MediaType,
    OpenAPI,
    OpenApiDataTypes,
    Operation,
    Parameter,
    ParameterType,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
    Scope,
    SecurityScheme,
    SecuritySchemeName,
    Server,
)
from inmanta.server import config
from inmanta.server.extensions import FeatureManager
from inmanta.types import ReturnTypes

LOGGER = logging.getLogger(__name__)


def openapi_json_encoder(o: object) -> Union[ReturnTypes, util.JSONSerializable]:
    if isinstance(o, BaseModel):
        return o.dict(by_alias=True, exclude_none=True)
    return util.api_boundary_json_encoder(o)


class OpenApiConverter:
    """
    Extracts API information for the OpenAPI definition from the server
    """

    def __init__(self, global_url_map: dict[str, dict[str, UrlMethod]], feature_manager: FeatureManager):
        self.global_url_map = global_url_map
        self.feature_manager = feature_manager
        self.type_converter = OpenApiTypeConverter()
        self.arg_option_handler = ArgOptionHandler(self.type_converter)

    def _collect_server_information(self) -> list[Server]:
        bind_port = config.server_bind_port.get()
        server_address = config.server_address.get()
        protocol = "https" if config.ssl_enabled() else "http"
        return [
            Server(
                url=f"{protocol}://{server_address}:{bind_port}/",
            ),
            Server(url="/"),  # Generic server, working even if the swagger is behind a reverse proxy
        ]

    def _get_inmanta_version(self) -> Optional[str]:
        metadata = self.feature_manager.get_product_metadata()
        return metadata.version

    def generate_openapi_definition(self) -> OpenAPI:
        version = self._get_inmanta_version()
        info = Info(title="Inmanta Service Orchestrator", version=version if version else "")
        servers = self._collect_server_information()
        paths = {}
        for path, methods in self.global_url_map.items():
            api_methods = self._filter_api_methods(methods)
            if len(api_methods) > 0:
                url_method: UrlMethod = next(iter(methods.values()))
                parameterized_path: str = url_method.get_path()
                path_item = self._extract_operations_from_methods(api_methods, parameterized_path)
                paths[parameterized_path] = path_item
        security: list[dict[SecuritySchemeName, list[Scope]]] | None = (
            # Set the security scheme globally for all endpoints.
            [{schema_name: []} for schema_name in self.type_converter.components.securitySchemes]
            if self.type_converter.components.securitySchemes
            else None
        )
        return OpenAPI(
            openapi="3.0.2",
            info=info,
            paths=paths,
            servers=servers,
            components=self.type_converter.components,
            security=security,
        )

    def _filter_api_methods(self, methods: dict[str, UrlMethod]) -> dict[str, UrlMethod]:
        return {
            method_name: url_method
            for method_name, url_method in methods.items()
            if "api" in url_method.properties.client_types
        }

    def _extract_operations_from_methods(self, api_methods: dict[str, UrlMethod], path: str) -> PathItem:
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
        <script src="//unpkg.com/swagger-ui-dist@^4.11.1/swagger-ui-bundle.js"></script>
        <link rel="stylesheet" href="//unpkg.com/swagger-ui-dist@^4.11.1/swagger-ui.css" />
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

    def __init__(self) -> None:
        self.components = Components(schemas={}, securitySchemes=self._get_security_schemes())
        self._pydantic_ref_key = "$defs"
        self.openapi_ref_prefix = "#/components/schemas/"
        self._ref_regex = re.compile(re.escape(self.openapi_ref_prefix) + r"(.*)")

    def _get_security_schemes(self) -> dict[SecuritySchemeName, SecurityScheme] | None:
        if config.server_enable_auth.get():
            return {
                "bearerAuth": SecurityScheme(
                    type="http",
                    scheme="bearer",
                    bearerFormat="JWT",
                )
            }
        else:
            return None

    def get_openapi_type_of_parameter(self, parameter_type: inspect.Parameter) -> Schema:
        schema = self.get_openapi_type(parameter_type.annotation)
        if parameter_type.default is not inspect.Parameter.empty:
            schema.default = parameter_type.default
        return schema

    def _handle_pydantic_model(self, type_annotation: BaseModel, by_alias: bool = True) -> Schema:
        schema = type_annotation.model_json_schema(by_alias=by_alias, ref_template=f"{self.openapi_ref_prefix}{{model}}")
        # pydantic.BaseModel.model_json_schema() stores the model (and sub-model) definitions at #/$defs/{model}
        # (pydantic.main.DEFAULT_REF_TEMPLATE) but OpenAPI requires them to be placed at "#/components/schemas/"
        # The ref_template tells pydantic to update the references (the referring side) but not the schema location (the
        # referred side). So we need to perform that translation manually.
        if self._pydantic_ref_key in schema.keys():
            definitions: dict[str, dict[str, object]] = schema.pop(self._pydantic_ref_key)
            if self.components.schemas is not None:
                for key, definition in definitions.items():
                    patched_definition = self._handle_pydantic_model_recursively(definition)
                    self.components.schemas[key] = Schema(**patched_definition)

        schema = self._handle_pydantic_model_recursively(schema)
        return Schema(**schema)

    def _handle_pydantic_model_recursively(self, definition: dict[str, object]) -> dict[str, object]:
        """
        The json-schema is not 1-to-1 compatible with the OpenAPI schema. This method patches the
        given json-schema as such that it becomes compatible with the OpenAPI schema.
        """
        # Recursive calls
        if definition.get("properties") is not None:
            properties = definition["properties"]
            for property_name in list(properties.keys()):
                properties[property_name] = self._handle_pydantic_model_recursively(properties[property_name])
        if definition.get("additionalProperties") is not None and isinstance(definition["additionalProperties"], dict):
            definition["additionalProperties"] = self._handle_pydantic_model_recursively(definition["additionalProperties"])
        if definition.get("items") is not None:
            definition["items"] = self._handle_pydantic_model_recursively(definition["items"])
        for attr_name in ["anyOf", "allOf", "oneOf"]:
            if definition.get(attr_name) is not None:
                for i in range(len(definition[attr_name])):
                    definition[attr_name][i] = self._handle_pydantic_model_recursively(definition[attr_name][i])

        definition = self._convert_const_to_enum(definition)
        definition = self._add_type_field_to_enum_value(definition)
        return definition

    def _convert_const_to_enum(self, definition: dict[str, object]) -> dict[str, object]:
        """
        The 'const' field, which is part of the JSON schema, is not part of the OpenAPI schema.
        We convert the 'const' field into an 'enum' field here to make sure the constant value
        of the parameter is available in the OpenAPI schema.
        """
        if definition.get("enum") is not None:
            # The enum field is already populated
            return definition
        if definition.get("const") is not None:
            definition["enum"] = [str(definition["const"])]
            del definition["const"]
        return definition

    def _add_type_field_to_enum_value(self, definition: dict[str, object]) -> dict[str, object]:
        """
        When pydantic converts a Python Enum type to its corresponding json schema, it doesn't
        populate the type field. This way the rendered API documentation doesn't include all possible
        enum values. This method makes sure that the type attribute of an enum is always populated.
        """
        if definition.get("enum") is not None:
            if not definition.get("type"):
                # Convert Python type to a type known by OpenAPI
                if all(isinstance(e, bool) for e in definition["enum"]):
                    definition["type"] = OpenApiDataTypes.BOOLEAN.value
                elif all(isinstance(e, int) for e in definition["enum"]):
                    definition["type"] = OpenApiDataTypes.INTEGER.value
                elif all(isinstance(e, float) or isinstance(e, int) for e in definition["enum"]):
                    definition["type"] = OpenApiDataTypes.NUMBER.value
                else:
                    definition["type"] = OpenApiDataTypes.STRING.value
            # OpenAPI expects enum values to be strings
            definition["enum"] = [str(e) for e in definition["enum"]]
        return definition

    def get_openapi_type(self, type_annotation: type) -> Schema:
        class Sub(BaseModel):
            the_field: type_annotation
            model_config = ConfigDict(arbitrary_types_allowed=True)

        pydantic_result = self._handle_pydantic_model(Sub).properties["the_field"]
        pydantic_result.title = None
        return pydantic_result

    def resolve_reference(self, reference: str) -> Optional[Schema]:
        """
        Get a schema from its reference, if this schema exists.  If it doesn't exist, None is
        returned instead.

        :param reference: The reference to the schema
        """
        ref_match = self._ref_regex.match(reference)
        if not ref_match:
            return None

        ref_key = ref_match.group(1)
        return self.components.schemas[ref_key]


class ArgOptionHandler:
    """
    Extracts header, response header and path parameter information from ArgOptions
    """

    def __init__(self, type_converter: OpenApiTypeConverter) -> None:
        self.type_converter = type_converter

    def extract_parameters_from_arg_options(
        self, method_properties: MethodProperties, function_parameters: dict[str, inspect.Parameter]
    ) -> list[Parameter]:
        result: list[Parameter] = []
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
        self, arg_options: dict[str, ArgOption]
    ) -> Optional[dict[str, Union[Header, Reference]]]:
        headers: dict[str, Union[Header, Reference]] = {}
        for option_name, option in arg_options.items():
            if option.header and option.reply_header:
                headers[option.header] = Header(
                    description=f"The value of the request header {option.header}", schema=Schema(type="string")
                )
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
        self.all_params_dct: dict[str, inspect.Parameter] = self._extract_function_parameters(method_properties.function)
        self.path_params: dict[str, inspect.Parameter] = {}
        self.header_params: dict[str, inspect.Parameter] = {}
        self.non_path_and_non_header_params: dict[str, inspect.Parameter] = {}

        for param_name, param in self.all_params_dct.items():
            if f"<{param_name}>" in self.path:
                self.path_params[param_name] = param
            elif (
                param_name in self.method_properties.arg_options.keys()
                and self.method_properties.arg_options[param_name].header is not None
            ):
                self.header_params[param_name] = param
            else:
                self.non_path_and_non_header_params[param_name] = param

    # Parameters

    def _extract_function_parameters(self, url_method_function: Callable) -> dict[str, inspect.Parameter]:
        function_parameters = {
            parameter_name: parameter_type
            for parameter_name, parameter_type in inspect.signature(url_method_function).parameters.items()
        }
        return function_parameters

    def get_parameters(self) -> list[Parameter]:
        result = self._convert_header_and_path_params()
        if self.method_properties.operation not in ["POST", "PUT", "PATCH"]:
            result.extend(self._convert_function_params_to_query_params())
        return result

    def _convert_header_and_path_params(self) -> list[Parameter]:
        arg_options_params: list[Parameter] = self.arg_option_handler.extract_parameters_from_arg_options(
            self.method_properties, self.all_params_dct
        )
        path_params: list[Parameter] = self._convert_path_params_to_openapi()
        return arg_options_params + path_params

    def _convert_path_params_to_openapi(self) -> list[Parameter]:
        parameters: list[Union[Parameter, Reference]] = []
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

    def _convert_function_params_to_query_params(self) -> list[Parameter]:
        parameters: list[Parameter] = []
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

    def _convert_function_params_to_openapi_request_body_properties(self) -> dict[str, Schema]:
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

    def _build_json_request_body(self, properties: dict) -> RequestBody:
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

        request_body_parameters: list[str] = []

        if url_method.get_operation() in ["POST", "PUT", "PATCH"]:
            extra_params = {"requestBody": function_parameter_handler.convert_request_body()}
            try:
                request_body_parameters = list(
                    extra_params["requestBody"].content["application/json"].schema_.properties.keys()
                )
            except (KeyError, AttributeError):
                pass
        else:
            extra_params = {}

        tags = self._get_tags_of_operation(url_method)
        code_samples = self._generate_code_sample(
            method_name=url_method.method_name, parameters=parameters, request_body_parameters=request_body_parameters
        )
        return Operation(
            responses=responses,
            operationId=url_method.method_name,
            parameters=(parameters if len(parameters) else None),
            code_samples=code_samples,
            summary=url_method.short_method_description,
            description=url_method.long_method_description,
            tags=tags,
            **extra_params,
        )

    def _generate_code_sample(
        self, method_name: str, parameters: Sequence[Parameter], request_body_parameters: Sequence[str]
    ) -> list[CodeSample]:
        """
        Generate a python code sample for the given method and parameters. The returned sample is wrapped in a list to match
        the type expected by redoc
        (see https://redocly.com/docs-legacy/api-reference-docs/specification-extensions/x-code-samples#usage)
        """
        tab_padding = " " * 4
        all_parameters = list(
            itertools.chain(
                [param.name if param.name != INMANTA_MT_HEADER else "tid" for param in parameters], request_body_parameters
            )
        )
        arguments = f"\n{',\n'.join(f"{tab_padding}{param}=..." for param in all_parameters)}\n" if all_parameters else ""
        source = (
            "client = inmanta.protocol.endpoints.Client(name='api', timeout=120)\n"
            f"result = await client.{method_name}({arguments})"
        )
        code_samples = CodeSample(lang="Python", source=source)
        return [code_samples]

    def _get_tags_of_operation(self, url_method: UrlMethod) -> Optional[list[str]]:
        if url_method.endpoint is not None:
            if hasattr(url_method.endpoint, "_name"):
                return [url_method.endpoint._name]
            else:
                return [url_method.endpoint.__class__.__name__]
        else:
            return None

    def _build_responses(self, url_method_properties: MethodProperties) -> dict[str, Response]:
        result: dict[str, Response] = {}
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

    def _build_return_value_wrapper(self, url_method_properties: MethodProperties) -> Optional[dict[str, MediaType]]:
        return_type = inspect.signature(url_method_properties.function).return_annotation

        if return_type is None or return_type == inspect.Signature.empty:
            return None

        return_properties: Optional[dict[str, Schema]] = None

        if return_type == ReturnValue or is_generic_type(return_type) and get_origin(return_type) == ReturnValue:
            # Dealing with the special case of ReturnValue[...]
            links_type = self.type_converter.get_openapi_type(dict[str, str])
            links_type.title = "Links"
            links_type.nullable = True

            warnings_type = self.type_converter.get_openapi_type(list[str])
            warnings_type.title = "Warnings"

            return_properties = {
                "links": links_type,
                "metadata": Schema(
                    title="Metadata",
                    nullable=True,
                    type="object",
                    properties={
                        "warnings": warnings_type,
                    },
                ),
            }

            type_args = get_args(return_type, evaluate=True)
            if not type_args or len(type_args) != 1:
                raise RuntimeError(
                    "ReturnValue definition should take one type Argument, e.g. ReturnValue[None].  "
                    f"Got this instead: {type_args}"
                )

            if not url_method_properties.envelope:
                raise RuntimeError("Methods returning a ReturnValue object should always have an envelope")

            if type_args[0] is not type(None):
                return_properties[url_method_properties.envelope_key] = self.type_converter.get_openapi_type(type_args[0])

        else:
            openapi_return_type = self.type_converter.get_openapi_type(return_type)
            if url_method_properties.envelope:
                return_properties = {url_method_properties.envelope_key: openapi_return_type}

        return {"application/json": MediaType(schema=Schema(type="object", properties=return_properties))}
