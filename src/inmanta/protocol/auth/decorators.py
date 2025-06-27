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
from typing import TYPE_CHECKING, Callable

from inmanta import const

if TYPE_CHECKING:
    from inmanta.protocol.common import MethodProperties


def auth[F: Callable](
    auth_label: const.AuthorizationLabel, *, read_only: bool, environment_param: str | None = None
) -> Callable[[F], F]:
    """
    A decorator used to add authorization-related metadata to an API endpoint.
    This metadata can be used when writing an access policy. The @auth
    decorator always needs to be defined above the @method or @typedmethod
    decorator.

    :param auth_label: A label used to group together endpoints that act on
                       conceptually related data. This makes it easier to
                       write a short and well structured access policy.
    :param read_only: True iff the API endpoint performs a read-only operation.
    :param environment_param: The parameter in the API endpoint that indicates
                              the environment on which the endpoint is acting.
                              Or None if it's an environment-agnostic endpoint.
    """

    def wrapper(fnc: F) -> F:
        if not hasattr(fnc, "__method_properties__"):
            raise Exception(
                f"@method/@typedmethod decorator not found on method {fnc.__name__}."
                " Make sure the @auth decorator is always set above the @method/@typedmethod decorator."
            )
        if environment_param is not None:
            signature = inspect.signature(fnc)
            if environment_param not in signature.parameters:
                raise Exception(f"environment_param {environment_param} is not a parameter of the API endpoint {fnc.__name__}")
        for method_properties in fnc.__method_properties__:
            method_properties.authorization_metadata = AuthorizationMetadata(
                method_properties, auth_label, read_only=read_only, environment_param=environment_param
            )
        return fnc

    return wrapper


class AuthorizationMetadata:
    """
    A class that contains authorization-related metadata about an API endpoint.
    """

    def __init__(
        self,
        method_properties: "MethodProperties",
        auth_label: const.AuthorizationLabel,
        *,
        read_only: bool,
        environment_param: str | None,
    ) -> None:
        self.method_properties = method_properties
        self.auth_label = auth_label
        self.read_only = read_only
        self.environment_param = environment_param
