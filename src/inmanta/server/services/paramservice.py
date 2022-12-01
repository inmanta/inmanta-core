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
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

from inmanta import data, util
from inmanta.const import ParameterSource
from inmanta.data import InvalidSort
from inmanta.data.dataview import FactsView, ParameterView
from inmanta.data.model import Fact, Parameter, ResourceIdStr
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_PARAM, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.agentmanager import AgentManager
from inmanta.server.server import Server
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType

LOGGER = logging.getLogger(__name__)


class ParameterService(protocol.ServerSlice):
    """Slice for parameter management"""

    server_slice: Server
    agentmanager: AgentManager

    def __init__(self) -> None:
        super(ParameterService, self).__init__(SLICE_PARAM)

        self._fact_expire = opt.server_fact_expire.get()
        self._fact_renew = opt.server_fact_renew.get()

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))
        self.agentmanager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))

    async def start(self) -> None:
        self.schedule(self.renew_expired_facts, self._fact_renew, cancel_on_stop=False)
        await super().start()

    async def renew_expired_facts(self) -> None:
        """
        Send out requests to renew expired facts
        """
        LOGGER.info("Renewing expired parameters")

        updated_before = datetime.datetime.now().astimezone() - datetime.timedelta(0, (self._fact_expire - self._fact_renew))
        expired_params = await data.Parameter.get_updated_before(updated_before)

        LOGGER.debug("Renewing %d expired parameters" % len(expired_params))

        for param in expired_params:
            if param.environment is None:
                LOGGER.warning(
                    "Found parameter without environment (%s for resource %s). Deleting it.", param.name, param.resource_id
                )
                await param.delete()
            else:
                LOGGER.debug(
                    "Requesting new parameter value for %s of resource %s in env %s",
                    param.name,
                    param.resource_id,
                    param.environment,
                )
                await self.agentmanager.request_parameter(param.environment, param.resource_id)

        unknown_parameters = await data.UnknownParameter.get_list(resolved=False)
        for u in unknown_parameters:
            if u.environment is None:
                LOGGER.warning(
                    "Found unknown parameter without environment (%s for resource %s). Deleting it.", u.name, u.resource_id
                )
                await u.delete()
            else:
                LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id, u.id)
                await self.agentmanager.request_parameter(u.environment, u.resource_id)

        LOGGER.info("Done renewing expired parameters")

    @handle(methods.get_param, param_id="id", env="tid")
    async def get_param(self, env: data.Environment, param_id: str, resource_id: Optional[str] = None) -> Apireturn:
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

        # check if it was expired
        now = datetime.datetime.now().astimezone()
        if resource_id is None or (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0]}

        LOGGER.info("Parameter %s of resource %s expired.", param_id, resource_id)
        out = await self.agentmanager.request_parameter(env.id, resource_id)
        return out

    async def _update_param(
        self,
        env: data.Environment,
        name: str,
        value: str,
        source: str,
        resource_id: str,
        metadata: JsonType,
        recompile: bool = False,
    ) -> bool:
        """
        Update or set a parameter.

        This method returns true if:
        - this update resolves an unknown
        - recompile is true and the parameter updates an existing parameter to a new value
        """
        LOGGER.debug("Updating/setting parameter %s in env %s (for resource %s)", name, env.id, resource_id)
        if not isinstance(value, str):
            value = str(value)

        if resource_id is None:
            resource_id = ""

        params = await data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        value_updated = True
        if len(params) == 0:
            param = data.Parameter(
                environment=env.id,
                name=name,
                resource_id=resource_id,
                value=value,
                source=source,
                updated=datetime.datetime.now().astimezone(),
                metadata=metadata,
            )
            await param.insert()
        else:
            param = params[0]
            value_updated = param.value != value
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

    @handle(methods.set_param, param_id="id", env="tid")
    async def set_param(
        self,
        env: data.Environment,
        param_id: str,
        source: ParameterSource,
        value: str,
        resource_id: str,
        metadata: JsonType,
        recompile: bool,
    ) -> Apireturn:
        result = await self._update_param(env, param_id, value, source, resource_id, metadata, recompile)
        warnings = None
        if result:
            compile_metadata = {
                "message": "Recompile model because one or more parameters were updated",
                "type": "param",
                "params": [(param_id, resource_id)],
            }
            warnings = await self.server_slice._async_recompile(env, False, metadata=compile_metadata)

        if resource_id is None:
            resource_id = ""

        params = await data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        return attach_warnings(200, {"parameter": params[0]}, warnings)

    @handle(methods.set_parameters, env="tid")
    async def set_parameters(self, env: data.Environment, parameters: List[Dict[str, Any]]) -> Apireturn:
        recompile = False

        params: List[Tuple[str, ResourceIdStr]] = []
        for param in parameters:
            name: str = param["id"]
            source = param["source"]
            value = param["value"] if "value" in param else None
            resource_id: ResourceIdStr = param["resource_id"] if "resource_id" in param else None
            metadata = param["metadata"] if "metadata" in param else None

            result = await self._update_param(env, name, value, source, resource_id, metadata)
            if result:
                recompile = True
                params.append((name, resource_id))

        compile_metadata = {
            "message": "Recompile model because one or more parameters were updated",
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
    async def list_params(self, env: data.Environment, query: Dict[str, str]) -> Apireturn:
        params = await data.Parameter.list_parameters(env.id, **query)
        return (
            200,
            {
                "parameters": params,
                "expire": self._fact_expire,
                # Return datetime in UTC without explicit timezone offset
                "now": util.datetime_utc_isoformat(datetime.datetime.now()),
            },
        )

    @handle(methods_v2.get_facts, env="tid")
    async def get_facts(self, env: data.Environment, rid: ResourceIdStr) -> List[Fact]:
        params = await data.Parameter.get_list(environment=env.id, resource_id=rid)
        dtos = [param.as_fact() for param in params]
        return dtos

    @handle(methods_v2.get_fact, env="tid")
    async def get_fact(self, env: data.Environment, rid: ResourceIdStr, id: uuid.UUID) -> Fact:
        param = await data.Parameter.get_one(environment=env.id, resource_id=rid, id=id)
        if not param:
            raise NotFound(f"Fact with id {id} does not exist")
        return param.as_fact()

    @handle(methods_v2.get_parameters, env="tid")
    async def get_parameters(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[Union[datetime.datetime, str]] = None,
        end: Optional[Union[datetime.datetime, str]] = None,
        filter: Optional[Dict[str, List[str]]] = None,
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
        filter: Optional[Dict[str, List[str]]] = None,
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
