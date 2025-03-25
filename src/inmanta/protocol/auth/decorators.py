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

from typing import Callable, Sequence
import inspect
from inmanta import const
from inmanta.protocol.common import MethodProperties

def auth(auth_label: str, read_only: bool, environment_param: str | None = None) -> Callable[..., Callable]:
    """
    A decorator used to add authorization-related metadata to a API endpoint.
    This metadata can be used when writing an authorization policy. The @auth
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
                f"@method decorator not found on method {fnc.__name__}."
                " Make sure the @auth decorator is always set above the @method decorator"
            )
        if environment_param is not None:
            signature = inspect.signature(fnc)
            if environment_param not in signature.parameters:
                raise Exception(
                    f"environment_param {environment_param} is not a parameter of the API endpoint {fnc.__name__}"
                )
        method_properties = fnc.__method_properties__
        client_types = list(method_properties.client_types)
        metadata = AuthorizationMetadata(fnc.__name__, auth_label, read_only, environment_param, client_types)
        AuthorizationMetadata.register_auth_metadata(metadata)
        return fnc
    return wrapper


class AuthorizationMetadata:

    metadata: dict[str, "AuthorizationMetadata"] = {}

    def __init__(
        self,
        fnc_name: str,
        auth_label: str,
        read_only: bool,
        environment_param: str | None,
        client_types: Sequence[const.ClientType],
    ) -> None:
        self.fnc_name = fnc_name
        self.auth_label = auth_label
        self.read_only = read_only
        self.environment_param = environment_param
        self.client_types = client_types

    @classmethod
    def register_auth_metadata(cls, metadata: "AuthorizationMetadata") -> None:
        cls.metadata[metadata.fnc_name] = metadata

    @classmethod
    def has_metadata_for(cls, method_name: str) -> bool:
        return method_name in cls.metadata
