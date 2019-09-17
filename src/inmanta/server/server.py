"""
    Copyright 2018 Inmanta

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
import logging
import os
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, cast

import importlib_metadata
from tornado import locks

from inmanta import data
from inmanta.data.model import ExtensionStatus, SliceStatus, StatusResponse
from inmanta.protocol import exceptions, methods
from inmanta.protocol.common import attach_warnings
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_COMPILER,
    SLICE_DATABASE,
    SLICE_SERVER,
    SLICE_SESSION_MANAGER,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import Apireturn, JsonType, Warnings

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.server.agentmanager import AgentManager
    from inmanta.server.services.compilerservice import CompilerService

DBLIMIT = 100000


class Server(protocol.ServerSlice):
    """
        The central Inmanta server that communicates with clients and agents and persists configuration
        information
    """

    _server_storage: Dict[str, str]
    compiler: "CompilerService"
    _server: protocol.Server

    def __init__(self) -> None:
        super().__init__(name=SLICE_SERVER)
        LOGGER.info("Starting server endpoint")

        self.setup_dashboard()
        self.dryrun_lock = locks.Lock()

    def get_dependencies(self) -> List[str]:
        return [SLICE_SESSION_MANAGER, SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        self._server = server
        self._server_storage: Dict[str, str] = self.check_storage()
        self.agentmanager: "AgentManager" = cast("AgentManager", server.get_slice(SLICE_AGENT_MANAGER))
        self.compiler: "CompilerService" = cast("CompilerService", server.get_slice(SLICE_COMPILER))

    def setup_dashboard(self) -> None:
        """
            If configured, set up tornado to serve the dashboard
        """
        if not opt.dash_enable.get():
            return

        dashboard_path = opt.dash_path.get()
        if dashboard_path is None:
            LOGGER.warning("The dashboard is enabled in the configuration but its path is not configured.")
            return

        if not opt.server_enable_auth.get():
            auth = ""
        else:
            auth = """,
    'auth': {
        'realm': '%s',
        'url': '%s',
        'clientId': '%s'
    }""" % (
                opt.dash_realm.get(),
                opt.dash_auth_url.get(),
                opt.dash_client_id.get(),
            )

        content = """
angular.module('inmantaApi.config', []).constant('inmantaConfig', {
    'backend': window.location.origin+'/'%s
});
        """ % (
            auth
        )
        self.add_static_content("/dashboard/config.js", content=content)
        self.add_static_handler("/dashboard", dashboard_path, start=True)

    def check_storage(self) -> Dict[str, str]:
        """
            Check if the server storage is configured and ready to use.
        """

        def _ensure_directory_exist(directory: str, *subdirs: str) -> str:
            directory = os.path.join(directory, *subdirs)
            if not os.path.exists(directory):
                os.mkdir(directory)
            return directory

        state_dir = opt.state_dir.get()
        server_state_dir = os.path.join(state_dir, "server")
        dir_map = {"server": _ensure_directory_exist(state_dir, "server")}
        dir_map["files"] = _ensure_directory_exist(server_state_dir, "files")
        dir_map["environments"] = _ensure_directory_exist(server_state_dir, "environments")
        dir_map["agents"] = _ensure_directory_exist(server_state_dir, "agents")
        dir_map["logs"] = _ensure_directory_exist(opt.log_dir.get())
        return dir_map

    @protocol.handle(methods.dryrun_request, version_id="id", env="tid")
    async def dryrun_request(self, env: data.Environment, version_id: int) -> Apireturn:
        model = await data.ConfigurationModel.get_version(environment=env.id, version=version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # fetch all resource in this cm and create a list of distinct agents
        rvs = await data.Resource.get_list(model=version_id, environment=env.id)

        # Create a dryrun document
        dryrun = await data.DryRun.create(environment=env.id, model=version_id, todo=len(rvs), total=len(rvs))

        agents = await data.ConfigurationModel.get_agents(env.id, version_id)
        await self.agentmanager._ensure_agents(env, agents)

        for agent in agents:
            client = self.agentmanager.get_agent_client(env.id, agent)
            if client is not None:
                self.add_background_task(client.do_dryrun(env.id, dryrun.id, agent, version_id))
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, env.id)

        # Mark the resources in an undeployable state as done
        with (await self.dryrun_lock.acquire()):
            undeployableids = await model.get_undeployable()
            undeployableids = [rid + ",v=%s" % version_id for rid in undeployableids]
            undeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=undeployableids)
            for res in undeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

            skipundeployableids = await model.get_skipped_for_undeployable()
            skipundeployableids = [rid + ",v=%s" % version_id for rid in skipundeployableids]
            skipundeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=skipundeployableids)
            for res in skipundeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_list, env="tid")
    async def dryrun_list(self, env: data.Environment, version: Optional[int] = None) -> Apireturn:
        query_args = {}
        query_args["environment"] = env.id
        if version is not None:
            model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
            if model is None:
                return 404, {"message": "The request version does not exist."}

            query_args["model"] = version

        dryruns = await data.DryRun.get_list(**query_args)

        return (
            200,
            {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo} for x in dryruns]},
        )

    @protocol.handle(methods.dryrun_report, dryrun_id="id", env="tid")
    async def dryrun_report(self, env: data.Environment, dryrun_id: uuid.UUID) -> Apireturn:
        dryrun = await data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_update, dryrun_id="id", env="tid")
    async def dryrun_update(self, env: data.Environment, dryrun_id: uuid.UUID, resource: str, changes: JsonType) -> Apireturn:
        with (await self.dryrun_lock.acquire()):
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            await data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200

    @protocol.handle(methods.notify_change_get, env="id")
    async def notify_change_get(self, env: data.Environment, update: bool) -> Apireturn:
        result = await self.notify_change(env, update, {})
        return result

    @protocol.handle(methods.notify_change, env="id")
    async def notify_change(self, env: data.Environment, update: bool, metadata: JsonType) -> Apireturn:
        LOGGER.info("Received change notification for environment %s", env.id)
        if "type" not in metadata:
            metadata["type"] = "api"

        if "message" not in metadata:
            metadata["message"] = "Recompile trigger through API call"

        warnings = await self._async_recompile(env, update, metadata=metadata)

        return attach_warnings(200, None, warnings)

    async def _async_recompile(self, env: data.Environment, update_repo: bool, metadata: JsonType = {}) -> Warnings:
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        _, warnings = await self.compiler.request_recompile(
            env=env, force_update=update_repo, do_export=True, remote_id=uuid.uuid4(), metadata=metadata
        )
        return warnings

    @protocol.handle(methods.get_server_status)
    async def get_server_status(self) -> StatusResponse:
        try:
            distr = importlib_metadata.distribution("inmanta")
        except importlib_metadata.PackageNotFoundError:
            raise exceptions.ServerError(
                "Could not find version number for the inmanta compiler."
                "Is inmanta installed? Use stuptools install or setuptools dev to install."
            )
        slices = []
        extension_names = set()
        for slice_name, slice in self._server.get_slices().items():
            slices.append(SliceStatus(name=slice_name, status=await slice.get_status()))

            try:
                ext_name = slice_name.split(".")[0]
                package_name = slice.__class__.__module__.split(".")[0]
                distribution = importlib_metadata.distribution(package_name)

                extension_names.add((ext_name, package_name, distribution.version))
            except importlib_metadata.PackageNotFoundError:
                LOGGER.info(
                    "Package %s of slice %s is not packaged in a distribution. Unable to determine its extension.",
                    package_name,
                    slice_name,
                )

        response = StatusResponse(
            version=distr.version,
            license=distr.metadata["License"] if "License" in distr.metadata else "unknown",
            extensions=[
                ExtensionStatus(name=name, package=package, version=version) for name, package, version in extension_names
            ],
            slices=slices,
        )

        return response
