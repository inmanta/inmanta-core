"""
Copyright 2025 Inmanta

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
from typing import Callable, Sequence

from inmanta import const
from inmanta.protocol.common import MethodProperties


def auth(auth_label: str, read_only: bool, environment_param: str | None = None) -> Callable[..., Callable]:
    """
    A decorator used to add authorization-related metadata to an API endpoint.
    This metadata can be used when writing an access policy. The @auth
    decorator always needs to be defined above the @method or @typedmethod
    decorator.

    :param auth_label: The name of an authorization label. The same label can be
                       applied on different API endpoint to indicate they are
                       related. This allows creating a taxonomy from the full
                       list of API endpoints.
    :param read_only: True iff the API endpoint performs a read-only operation.
    :param environment_param: The parameter in the API endpoint that indicates
                              the environment on which the endpoint is acting.
                              Or None if it's an environment-agnostic endpoint.
    """

    def wrapper(fnc: Callable[..., Callable]) -> Callable[..., Callable]:
        if not hasattr(fnc, "__method_properties__"):
            raise Exception(
                f"@method/@typedmethod decorator not found on method {fnc.__name__}."
                " Make sure the @auth decorator is always set above the @method/@typedmethod decorator."
            )
        if environment_param is not None:
            signature = inspect.signature(fnc)
            if environment_param not in signature.parameters:
                raise Exception(f"environment_param {environment_param} is not a parameter of the API endpoint {fnc.__name__}")
        method_properties = fnc.__method_properties__
        metadata = AuthorizationMetadata(method_properties, auth_label, read_only, environment_param)
        AuthorizationMetadata.register_auth_metadata(metadata)
        return fnc

    return wrapper


class AuthorizationMetadata:

    metadata: dict[str, "AuthorizationMetadata"] = {}

    def __init__(
        self,
        method_properties: MethodProperties,
        auth_label: str,
        read_only: bool,
        environment_param: str | None,
    ) -> None:
        self.method_properties = method_properties
        self.auth_label = auth_label
        self.read_only = read_only
        self.environment_param = environment_param

    @classmethod
    def register_auth_metadata(cls, metadata: "AuthorizationMetadata") -> None:
        function_name = metadata.method_properties.function_name
        if function_name in cls.metadata:
            raise Exception(f"Authorization metadata already set for method {function_name}.")
        cls.metadata[function_name] = metadata

    @classmethod
    def has_metadata_for(cls, method_name: str) -> bool:
        return method_name in cls.metadata

    @classmethod
    def get_open_policy_agent_data(cls) -> dict[str, object]:
        """
        Return the information about the different endpoints that exist
        in the format used as input to Open Policy Agent.
        """
        endpoints = {}
        for md in cls.metadata.values():
            method_properties = md.method_properties
            endpoint_id = f"{method_properties.operation} {method_properties.path}"
            endpoints[endpoint_id] = {
                "client_types": method_properties.client_types,
                "auth_label": md.auth_label,
                "read_only": md.read_only,
                "environment_param": md.environment_param,
            }
        return {"endpoints": endpoints}
