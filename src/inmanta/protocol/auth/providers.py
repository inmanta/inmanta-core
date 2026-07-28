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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Mapping

from inmanta import const
from inmanta.protocol import common, exceptions, methods_v2
from inmanta.protocol.auth import auth, policy_engine
from inmanta.server import config as server_config

if TYPE_CHECKING:
    from inmanta.protocol import rest


class AuthorizationProvider(ABC):
    """
    A class used to validate whether an API request is authorized.
    """

    def __init__(self) -> None:
        self.running = False

    async def start(self) -> None:
        """
        Start the authorization provider. The provider has to be started
        before it can accept calls on the authorize_request() method.
        """
        self.running = True

    async def stop(self) -> None:
        """
        Stop the authorization provider.
        """
        self.running = False

    async def authorize_request(self, call_arguments: "rest.CallArguments") -> None:
        """
        Main entrypoint to validate whether an API call is authorized or not.

        :raises UnauthorizedException: If no authorization token is found in call_arguments.
        :raises Forbidden: If the authorization token in call_arguments doesn't authorize the request.
        """
        if not self.running:
            raise Exception("Authorization provider was not started.")

        await self._do_authorize_request(
            call_arguments.auth_token,
            call_arguments.method_properties,
            call_arguments.metadata,
            call_arguments.policy_engine_call_args,
        )

    async def authorize_request_custom_handler(
        self,
        auth_token: auth.claim_type,
        method_properties: common.MethodProperties,
        call_args_dct: dict[str, object],
    ) -> None:
        """
        Entrypoint to use when the API endpoint relies on a custom Tornado handler so that no
        CallArguments object is available.
        """
        if not self.running:
            raise Exception("Authorization provider was not started.")

        await self._do_authorize_request(auth_token, method_properties, metadata={}, call_args_dct=call_args_dct)

    @abstractmethod
    async def _do_authorize_request(
        self,
        auth_token: auth.claim_type | None,
        method_properties: common.MethodProperties,
        metadata: dict[str, object],
        call_args_dct: dict[str, object],
    ) -> None:
        """
        To be overriden by the subclass. Contains the logic to validate whether the given method call is authorized
        for this authorization provider.

        :raises UnauthorizedException: If no authorization token is found in call_arguments.
        :raises Forbidden: If the authorization token in call_arguments doesn't authorize the request.
        """
        raise NotImplementedError()

    @classmethod
    def create_from_config(cls) -> "AuthorizationProvider":
        """
        Returns an AuthorizationProvider that corresponds to the authorization provider
        configured in the server config.
        """
        authorization_provider_name = server_config.authorization_provider.get()
        match server_config.AuthorizationProviderName(authorization_provider_name):
            case server_config.AuthorizationProviderName.policy_engine:
                return PolicyEngineAuthorizationProvider()
            case server_config.AuthorizationProviderName.legacy:
                return LegacyAuthorizationProvider()
            case _:
                raise Exception(f"Unknown authorization provider {authorization_provider_name}.")


class LegacyAuthorizationProvider(AuthorizationProvider):
    """
    An authorization provider that authorizes the API call based on the authorization token only.
    """

    async def _do_authorize_request(
        self,
        auth_token: auth.claim_type | None,
        method_properties: common.MethodProperties,
        metadata: dict[str, object],
        call_args_dct: dict[str, object],
    ) -> None:
        if auth_token is None:
            if method_properties.enforce_auth:
                # We only need a valid token when the endpoint enforces authentication
                raise exceptions.UnauthorizedException()
            return

        # Enforce environment restrictions
        env_key: str = const.INMANTA_URN + "env"
        if env_key in auth_token:
            if env_key not in metadata:
                if method_properties.allow_env_scoped_tokens:
                    return
                else:
                    raise exceptions.Forbidden("The authorization token is scoped to a specific environment.")

            if metadata[env_key] != "all" and auth_token[env_key] != metadata[env_key]:
                raise exceptions.Forbidden("The authorization token is not valid for the requested environment.")

        # Enforce client_types restrictions
        ct_key: str = const.INMANTA_URN + "ct"
        if not any(ct for ct in auth_token[ct_key] if ct in method_properties.client_types):
            raise exceptions.Forbidden(
                "The authorization token does not have a valid client type for this call."
                + f" ({auth_token[ct_key]} provided, {method_properties.client_types} expected)"
            )


class PolicyEngineAuthorizationProvider(AuthorizationProvider):
    """
    An Authorization provider that authorizes non-service tokens using the defined access policy.
    Service tokens are authorized using the LegacyAuthorizationProvider.
    """

    def __init__(self) -> None:
        super().__init__()
        self._policy_engine = policy_engine.PolicyEngine()
        self._legacy_authorization_provider = LegacyAuthorizationProvider()

    async def start(self) -> None:
        await self._policy_engine.start()
        await self._legacy_authorization_provider.start()
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        await self._policy_engine.stop()
        await self._legacy_authorization_provider.stop()

    async def _do_authorize_request(
        self,
        auth_token: auth.claim_type | None,
        method_properties: common.MethodProperties,
        metadata: dict[str, object],
        call_args_dct: dict[str, object],
    ) -> None:
        if method_properties.function == methods_v2.login:
            # On a login call the authorization is done using the provided username and password.
            # No need to authorize the token.
            return
        if method_properties.function == methods_v2.health:
            # For ease of use, the health endpoint should be accessible without authentication.
            return
        if auth_token is None:
            raise exceptions.UnauthorizedException()
        if auth.is_service_token(auth_token):
            # Service (machine-to-machine) requests always use the legacy provider.
            await self._legacy_authorization_provider._do_authorize_request(
                auth_token, method_properties, metadata, call_args_dct
            )
        else:
            input_data = self._get_input_for_policy_engine(auth_token, method_properties, call_args_dct)
            if not await self._policy_engine.does_satisfy_access_policy(input_data):
                raise exceptions.Forbidden("Request is not allowed by the access policy.")

    def _get_input_for_policy_engine(
        self,
        auth_token: auth.claim_type,
        method_properties: common.MethodProperties,
        call_args_dct: dict[str, object],
    ) -> Mapping[str, object]:
        """
        Returns the input that should be provided to the policy engine to validate
        whether this call is authorized or not.
        """
        return {
            "input": {
                "request": {
                    "endpoint_id": f"{method_properties.operation} {method_properties.get_full_path()}",
                    "parameters": call_args_dct,
                },
                "token": auth_token,
            }
        }
