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
from typing import Dict, List, Type

from pydantic.main import BaseModel

from inmanta.protocol.common import ArgOption, UrlMethod
from inmanta.protocol.openapi.model import OpenAPI, Operation, Parameter, ParameterType, PathItem, RequestBody, Response
from inmanta.server import config
from inmanta.util import get_compiler_version


def openapi_json_encoder(o):
    if isinstance(o, BaseModel):
        return o.dict(by_alias=True, exclude_none=True)


class OpenApiConverter:
    """
        Extracts API information for the OpenAPI definition from the server
    """

    def get_servers(self):
        bind_port = config.get_bind_port()
        bind_addresses = config.server_bind_address.get()
        return [{"url": f"http://{bind_address}:{bind_port}/"} for bind_address in bind_addresses]

    def get_top_level_object(self):
        info = {"title": "Inmanta Service Orchestrator", "version": get_compiler_version()}
        servers = self.get_servers()
        return {"openapi": "3.0.2", "info": info, "paths": {}, "servers": servers}

    def filter_api_methods(self, methods: Dict[str, UrlMethod]) -> Dict[str, UrlMethod]:
        return {
            method_name: url_method
            for method_name, url_method in methods.items()
            if "api" in url_method.properties.client_types
        }

    def get_path_of_method(self, methods: Dict[str, UrlMethod]) -> str:
        path = [
            f"/{method.properties._api_prefix}/v{method.properties.api_version}{method.properties._path.path}".replace(
                "<", "{"
            ).replace(">", "}")
            for method in methods.values()
        ][0]
        return path

    def extract_parameters_from_arg_options(self, response: Response, path: str, arg_options: Dict[str, ArgOption]):
        parameters = []
        for option_name, option in arg_options.items():
            param_dict = {}
            if option.header:
                param_dict["in"] = ParameterType.header
                param_dict["name"] = option.header
                param_dict["schema"] = {"type": "string"}
                if option.reply_header:
                    response.headers = {option.header: {"description": option.header, "schema": {"type": "string"}}}
            elif option_name in path:
                param_dict["in"] = ParameterType.path
                param_dict["name"] = option_name
                param_dict["required"] = True
                param_dict["schema"] = {"type": "string"}
            if param_dict:
                parameters.append(Parameter(**param_dict))
        return parameters

    def get_function_parameters(self, parameters: List[Parameter], url_method_function):
        function_parameters = {
            parameter_name: parameter_type
            for parameter_name, parameter_type in url_method_function.__annotations__.items()
            if parameter_name not in ["return", "tid"] and parameter_name not in [parameter.name for parameter in parameters]
        }
        return function_parameters

    def convert_function_params_to_openapi(
        self, function_parameters: Dict[str, Type], method_name: str, parameters: List[Parameter], path: str
    ):
        properties = {}
        for parameter_name, parameter_type in function_parameters.items():
            type_description = self.get_openapi_type(parameter_type)
            if parameter_name not in path:
                if method_name in ["PUT", "POST", "PATCH"]:
                    properties[parameter_name] = type_description
                else:
                    parameters.append(
                        Parameter(**{"name": parameter_name, "in": ParameterType.query, "schema": type_description})
                    )
            else:
                parameters.append(
                    Parameter(
                        **{"name": parameter_name, "in": ParameterType.path, "required": True, "schema": type_description}
                    )
                )
        return properties

    def get_openapi_type(self, parameter_type: Type):
        # TODO handle inmanta types
        if hasattr(parameter_type, "__name__"):
            type_name = parameter_type.__name__
        else:
            type_name = "dict"
        python_to_openapi_types_without_format = {
            "bool": "boolean",
            "int": "integer",
            "str": "string",
            "dict": "object",
            "list": "array",
        }
        openapi_type_name = python_to_openapi_types_without_format.get(type_name)
        if openapi_type_name:
            return {"type": openapi_type_name}
        if type_name == "float":
            return {"type": "number", "format": "float"}
        elif type_name == "bytes":
            return {"type": "string", "format": "binary"}
        elif type_name == "UUID":
            return {"type": "string", "format": "uuid"}

        return {"type": "object"}

    def add_return_value_to_response(self, response: Response, url_method: UrlMethod):
        return_type = url_method.properties.function.__annotations__.get("return")
        if return_type:
            return_properties = {}
            if url_method.properties.envelope:
                return_properties = {url_method.properties.envelope_key: {"type": "object"}}
            content = {"application/json": {"schema": {"type": "object", "properties": return_properties}}}
            response.content = content

    def get_request_body(self, properties: Dict):
        request_body_dict = {
            "required": True,
            "content": {"application/json": {"schema": {"type": "object", "properties": properties}}},
        }
        request_body = RequestBody(**request_body_dict)
        return request_body

    def get_operations(self, api_methods: Dict[str, UrlMethod], openapi_dict: Dict):
        if len(api_methods) > 0:
            path = self.get_path_of_method(api_methods)
            path_item = PathItem()
            openapi_dict["paths"][path] = path_item
            for http_method_name, url_method in api_methods.items():
                # TODO get description from docstring and handle responses other than 200
                ok_response = Response(description=path)
                parameters = self.extract_parameters_from_arg_options(ok_response, path, url_method.properties.arg_options)

                function_parameters = self.get_function_parameters(parameters, url_method.properties.function)
                properties = self.convert_function_params_to_openapi(function_parameters, http_method_name, parameters, path)
                self.add_return_value_to_response(ok_response, url_method)

                request_body = self.get_request_body(properties)
                responses = {"200": ok_response}
                operation = Operation(
                    responses=responses,
                    parameters=(parameters if len(parameters) else None),
                    requestBody=(request_body if len(properties) else None),
                )

                path_item.__setattr__(http_method_name.lower(), operation)

    def generate_openapi_definition(self, global_url_map: Dict[str, Dict[str, UrlMethod]]):
        openapi_dict = self.get_top_level_object()
        for methods in global_url_map.values():
            api_methods = self.filter_api_methods(methods)
            self.get_operations(api_methods, openapi_dict)

        return json.dumps(OpenAPI(**openapi_dict), default=openapi_json_encoder)
