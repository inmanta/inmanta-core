"""
Copyright 2019 Inmanta

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

import datetime
import logging
import uuid
from collections.abc import Sequence
from typing import Any, Optional, Union, cast

from inmanta import data
from inmanta.const import ParameterSource
from inmanta.data import InvalidSort
from inmanta.data.dataview import FactsView, ParameterView
from inmanta.data.model import Fact, Parameter
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_PARAM, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.agentmanager import AgentManager
from inmanta.server.server import Server
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType, ResourceIdStr

LOGGER = logging.getLogger(__name__)


class ParameterService(protocol.ServerSlice):
    """Slice for parameter management"""

    server_slice: Server
    agentmanager: AgentManager

    def __init__(self) -> None:
        super().__init__(SLICE_PARAM)

        self._fact_expire = opt.server_fact_expire.get()
        self._fact_renew = opt.server_fact_renew.get()

    def get_dependencies(self) -> list[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))
        self.agentmanager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))

    async def start(self) -> None:
        self.schedule(self.renew_facts, self._fact_renew, cancel_on_stop=False)
        await super().start()

    async def renew_facts(self) -> None:
        """
        Send out requests to renew facts.
        """
        LOGGER.info("Renewing facts")

        updated_before = datetime.datetime.now().astimezone() - datetime.timedelta(0, self._fact_renew)
        async with data.Parameter.get_connection() as connection:
            params_to_renew = await data.Parameter.get_updated_before_active_env(updated_before, connection=connection)
            unknown_parameters = await data.UnknownParameter.get_unknowns_in_latest_released_model_versions(
                connection=connection
            )

        LOGGER.debug("Renewing %d parameters", len(params_to_renew))
        for param in params_to_renew:
            LOGGER.debug(
                "Requesting new parameter value for %s of resource %s in env %s",
                param.name,
                param.resource_id,
                param.environment,
            )
            await self.agentmanager.request_parameter(param.environment, param.resource_id)

        LOGGER.debug("Requesting value for %d unknowns", len(unknown_parameters))
        for u in unknown_parameters:
            LOGGER.debug(
                "Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id, u.environment
            )
            await self.agentmanager.request_parameter(u.environment, u.resource_id)
        LOGGER.info("Done renewing parameters")

    @handle(methods.get_param, param_id="id", env="tid")
    async def get_param(self, env: data.Environment, param_id: str, resource_id: Optional[ResourceIdStr] = None) -> Apireturn:
        if resource_id is None:
            params = await data.Parameter.get_list(environment=env.id, name=param_id)
        else:
            params = await data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        if len(params) == 0:
            if resource_id is not None:
                out = await self.agentmanager.request_parameter(env.id, resource_id)
                return out
            return 404

        param = params[0]

        # check if it was expired:
        #   - If it's not associated with a resource, this is a regular parameter that never expires
        #   - Else, it's a fact: check if it can expire and if it has expired.

        now = datetime.datetime.now().astimezone()
        if resource_id is None or not param.expires or (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0]}

        LOGGER.info("Fact %s of resource %s expired.", param_id, resource_id)
        out = await self.agentmanager.request_parameter(env.id, resource_id)
        return out

    async def _update_param(
        self,
        env: data.Environment,
        name: str,
        value: Optional[str],
        source: str,
        resource_id: Optional[str],
        metadata: Optional[JsonType],
        recompile: bool = False,
        expires: Optional[bool] = None,
    ) -> bool:
        """
        Update or set a parameter or fact.

        :param expires: When setting a new parameter/fact: if set to None, then a sensible default will be provided (i.e. False
            for parameter and True for fact). When updating a parameter or fact, a None value will leave the existing value
            unchanged.

        This method returns true if:
        - this update resolves an unknown
        - recompile is true and the parameter updates an existing parameter to a new value
        """
        if resource_id:
            LOGGER.debug("Updating/setting fact %s in env %s (for resource %s)", name, env.id, resource_id)
        else:
            LOGGER.debug("Updating/setting parameter %s in env %s", name, env.id)

        if not isinstance(value, str):
            value = str(value)

        if resource_id is None:
            resource_id = ""

        params = await data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        value_updated = True

        if len(params) == 0:
            if expires is None:
                # By default:
                #   - parameters (i.e. not associated with a resource id) don't expire
                #   - facts (i.e. associated with a resource id) expire
                expires = bool(resource_id)

            param = data.Parameter(
                environment=env.id,
                name=name,
                resource_id=resource_id,
                value=value,
                source=source,
                updated=datetime.datetime.now().astimezone(),
                metadata=metadata,
                expires=expires,
            )
            await param.insert()
        else:
            param = params[0]
            value_updated = param.value != value
            if expires is not None:
                await param.update(
                    source=source, value=value, updated=datetime.datetime.now().astimezone(), metadata=metadata, expires=expires
                )
            else:
                await param.update(source=source, value=value, updated=datetime.datetime.now().astimezone(), metadata=metadata)

        # check if the parameter is an unknown
        unknown_params = await data.UnknownParameter.get_list(
            environment=env.id, name=name, resource_id=resource_id, resolved=False
        )
        if len(unknown_params) > 0:
            LOGGER.info(
                "Received values for unknown parameters %s, triggering a recompile", ", ".join([x.name for x in unknown_params])
            )
            for p in unknown_params:
                await p.update_fields(resolved=True)

            return True

        return recompile and value_updated

    def _validate_parameter(
        self,
        name: str,
        resource_id: Optional[str],
        expires: Optional[bool],
    ) -> None:
        if not resource_id and expires:
            # Parameters cannot expire
            raise BadRequest(
                "Cannot update or set parameter %s: `expire` set to True but parameters cannot expire."
                " Consider using a fact instead by providing a resource_id." % name,
            )

    @handle(methods.set_param, name="id", env="tid")
    async def set_param(
        self,
        env: data.Environment,
        name: str,
        source: ParameterSource,
        value: str,
        resource_id: Optional[str],
        metadata: JsonType,
        recompile: bool,
        expires: Optional[bool] = None,
    ) -> Apireturn:
        self._validate_parameter(name, resource_id, expires)
        result = await self._update_param(env, name, value, source, resource_id, metadata, recompile, expires)
        warnings = None
        if result:
            compile_metadata = {
                "message": "Recompile model because one or more parameters were updated",
                "type": "param",
                "params": [(name, resource_id)],
            }
            warnings = await self.server_slice._async_recompile(env, False, metadata=compile_metadata)

        if resource_id is None:
            resource_id = ""

        params = await data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        return attach_warnings(200, {"parameter": params[0]}, warnings)

    @handle(methods.set_parameters, env="tid")
    async def set_parameters(self, env: data.Environment, parameters: list[dict[str, Any]]) -> Apireturn:
        recompile = False

        updating_facts: bool = False
        updating_parameters: bool = False
        parameters_and_or_facts: str = "parameters"

        params: list[tuple[str, ResourceIdStr | None]] = []

        # Validate the full list of parameters before applying any changes
        for param in parameters:
            self._validate_parameter(
                param["id"],
                param["resource_id"] if "resource_id" in param else None,
                param["expires"] if "expires" in param else None,
            )

        for param in parameters:
            name: str = param["id"]
            source = param["source"]
            value = param["value"] if "value" in param else None
            resource_id: ResourceIdStr | None = param["resource_id"] if "resource_id" in param else None
            metadata = param["metadata"] if "metadata" in param else None
            expires = param["expires"] if "expires" in param else None

            if resource_id:
                updating_facts = True
            else:
                updating_parameters = True

            result = await self._update_param(env, name, value, source, resource_id, metadata, expires=expires)
            if result:
                recompile = True
                params.append((name, resource_id))

        if updating_facts:
            parameters_and_or_facts = "facts"
        if updating_parameters and updating_facts:
            parameters_and_or_facts = "parameters and facts"

        compile_metadata = {
            "message": f"Recompile model because one or more {parameters_and_or_facts} were updated",
            "type": "param",
            "params": params,
        }

        warnings = None
        if recompile:
            warnings = await self.server_slice._async_recompile(env, False, metadata=compile_metadata)

        return attach_warnings(200, None, warnings)

    @handle(methods.delete_param, env="tid", parameter_name="id")
    async def delete_param(self, env: data.Environment, parameter_name: str, resource_id: str) -> Apireturn:
        if resource_id is None:
            params = await data.Parameter.get_list(environment=env.id, name=parameter_name)
        else:
            params = await data.Parameter.get_list(environment=env.id, name=parameter_name, resource_id=resource_id)

        if len(params) == 0:
            return 404

        param = params[0]
        await param.delete()
        metadata = {
            "message": "Recompile model because one or more parameters were deleted",
            "type": "param",
            "params": [(param.name, param.resource_id)],
        }
        warnings = await self.server_slice._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, None, warnings)

    @handle(methods.list_params, env="tid")
    async def list_params(self, env: data.Environment, query: dict[str, str]) -> Apireturn:
        params = await data.Parameter.list_parameters(env.id, **query)
        return (
            200,
            {
                "parameters": params,
                "expire": self._fact_expire,  # Serialization happens in the RESTHandler's json encoder
                "now": datetime.datetime.now().astimezone(),
            },
        )

    @handle(methods_v2.get_facts, env="tid")
    async def get_facts(self, env: data.Environment, rid: ResourceIdStr) -> list[Fact]:
        params = await data.Parameter.get_list(environment=env.id, resource_id=rid, order_by_column="name")
        dtos = [param.as_fact() for param in params]
        return dtos

    @handle(methods_v2.get_fact, env="tid")
    async def get_fact(self, env: data.Environment, rid: ResourceIdStr, id: uuid.UUID) -> Fact:
        param = await data.Parameter.get_one(environment=env.id, resource_id=rid, id=id)
        if not param:
            raise NotFound(f"Fact with id {id} does not exist")
        return param.as_fact()

    async def _update_and_recompile(
        self,
        env: data.Environment,
        name: str,
        value: str,
        source: ParameterSource,
        metadata: dict[str, str],
        recompile: bool,
        resource_id: Optional[str] = None,
        expires: Optional[bool] = None,
    ) -> tuple[data.Parameter, Optional[list[str]]]:
        """
        Update a parameter or fact and optionally trigger recompilation.
        """
        if resource_id is None:
            resource_id = ""
        # Validate parameter or fact
        self._validate_parameter(name, resource_id, expires)

        # Update parameter/fact with new value and metadata
        recompile_required: bool = await self._update_param(env, name, value, source, resource_id, metadata, recompile, expires)
        warnings = None
        if recompile_required:
            compile_metadata = {
                "message": "Recompile model because one or more parameters/facts were updated",
                "type": "fact" if resource_id else "param",
                "params": [(name, resource_id)],
            }
            warnings = await self.server_slice._async_recompile(env, update_repo=False, metadata=compile_metadata)

        # Retrieve the updated parameter/fact
        param = await data.Parameter.get_one(environment=env.id, name=name, resource_id=resource_id)
        if not param:
            error_base = f"{name} for resource_id: {resource_id}" if resource_id else name
            error_prefix = "Fact" if resource_id else "Parameter"
            error_message = f"{error_prefix} with id {error_base} does not exist in environment {env.id}"
            raise NotFound(error_message)

        return param, warnings

    @handle(methods_v2.set_parameter, env="tid")
    async def set_parameter(
        self,
        env: data.Environment,
        name: str,
        source: ParameterSource,
        value: str,
        metadata: Optional[dict[str, str]] = None,
        recompile: bool = False,
    ) -> ReturnValue[Parameter]:
        if metadata is None:
            metadata = {}
        param, warnings = await self._update_and_recompile(env, name, value, source, metadata, recompile)
        return_value = ReturnValue(response=param.as_param())
        if warnings:
            return_value.add_warnings(warnings)
        return return_value

    @handle(methods_v2.set_fact, env="tid")
    async def set_fact(
        self,
        env: data.Environment,
        name: str,
        source: ParameterSource,
        value: str,
        resource_id: str,
        metadata: Optional[dict[str, str]] = None,
        recompile: bool = False,
        expires: Optional[bool] = True,
    ) -> ReturnValue[Fact]:
        if metadata is None:
            metadata = {}
        param, warnings = await self._update_and_recompile(env, name, value, source, metadata, recompile, resource_id, expires)
        return_value = ReturnValue(response=param.as_fact())
        if warnings:
            return_value.add_warnings(warnings)
        return return_value

    @handle(methods_v2.get_parameters, env="tid")
    async def get_parameters(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[Union[datetime.datetime, str]] = None,
        end: Optional[Union[datetime.datetime, str]] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "name.asc",
    ) -> ReturnValue[Sequence[Parameter]]:
        try:
            handler = ParameterView(
                environment=env,
                limit=limit,
                sort=sort,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                filter=filter,
            )
            out = await handler.execute()
            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.get_all_facts, env="tid")
    async def get_all_facts(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "name.asc",
    ) -> ReturnValue[Sequence[Fact]]:
        try:
            handler = FactsView(
                environment=env,
                limit=limit,
                sort=sort,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                filter=filter,
            )
            out = await handler.execute()
            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e
