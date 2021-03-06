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
import asyncio
import logging
import os
import shutil
import uuid
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional, Set, cast

from inmanta import data
from inmanta.data import model
from inmanta.protocol import encode_token, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, Forbidden, NotFound, ServerError
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_ENVIRONMENT,
    SLICE_ORCHESTRATION,
    SLICE_RESOURCE,
    SLICE_SERVER,
    SLICE_TRANSPORT,
    protocol,
)
from inmanta.server.agentmanager import AgentManager, AutostartedAgentManager
from inmanta.server.server import Server
from inmanta.server.services.orchestrationservice import OrchestrationService
from inmanta.server.services.resourceservice import ResourceService
from inmanta.types import Apireturn, JsonType, Warnings
from inmanta.util import get_compiler_version

LOGGER = logging.getLogger(__name__)


def rename_fields(env: model.Environment) -> JsonType:
    env_dict = env.dict()
    env_dict["project"] = env_dict["project_id"]
    del env_dict["project_id"]
    return env_dict


class EnvironmentAction(str, Enum):
    created = "created"
    deleted = "deleted"
    cleared = "cleared"
    updated = "updated"


class EnvironmentListener:
    """
    Base class for environment listeners
    Exceptions from the listeners are dropped, the listeners are responsible for handling them
    """

    async def environment_action_created(self, env: model.Environment) -> None:
        """
        Will be called when a new environment is created

        :param env: The new environment
        """
        pass

    async def environment_action_cleared(self, env: model.Environment) -> None:
        """
        Will be called when the environment is cleared

        :param env: The environment that is cleared
        """
        pass

    async def environment_action_deleted(self, env: model.Environment) -> None:
        """
        Will be called when the environment is deleted

        :param env: The environment that is deleted
        """
        pass

    async def environment_action_updated(self, updated_env: model.Environment, original_env: model.Environment) -> None:
        """
        Will be called when an environment is updated
        :param updated_env: The updated environment
        :param original_env: The original environment
        """
        pass


class EnvironmentService(protocol.ServerSlice):
    """Slice with project and environment management"""

    server_slice: Server
    agent_manager: AgentManager
    autostarted_agent_manager: AutostartedAgentManager
    orchestration_service: OrchestrationService
    resource_service: ResourceService
    listeners: Dict[EnvironmentAction, List[EnvironmentListener]]
    agent_state_lock: asyncio.Lock

    def __init__(self) -> None:
        super(EnvironmentService, self).__init__(SLICE_ENVIRONMENT)
        self.listeners = defaultdict(list)
        self.agent_state_lock = asyncio.Lock()

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AUTOSTARTED_AGENT_MANAGER, SLICE_ORCHESTRATION, SLICE_RESOURCE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))
        self.agent_manager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))
        self.orchestration_service = cast(OrchestrationService, server.get_slice(SLICE_ORCHESTRATION))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

    async def _setting_change(self, env: data.Environment, key: str) -> Warnings:
        setting = env._settings[key]

        warnings = None
        if setting.recompile:
            LOGGER.info("Environment setting %s changed. Recompiling with update = %s", key, setting.update)
            metadata = model.ModelMetadata(
                message="Recompile for modified setting", type="setting", extra_data={"setting": key}
            )
            warnings = await self.server_slice._async_recompile(env, setting.update, metadata=metadata.dict())

        if setting.agent_restart:
            if key == data.AUTOSTART_AGENT_MAP:
                LOGGER.info("Environment setting %s changed. Notifying agents.", key)
                self.add_background_task(self.autostarted_agent_manager.notify_agent_about_agent_map_update(env))
            else:
                LOGGER.info("Environment setting %s changed. Restarting agents.", key)
                self.add_background_task(self.autostarted_agent_manager.restart_agents(env))

        return warnings

    # v1 handlers
    @protocol.handle(methods.create_environment)
    async def create_environment(
        self, project_id: uuid.UUID, name: str, repository: str, branch: str, environment_id: Optional[uuid.UUID]
    ) -> Apireturn:
        return (
            200,
            {"environment": rename_fields(await self.environment_create(project_id, name, repository, branch, environment_id))},
        )

    @protocol.handle(methods.modify_environment, environment_id="id")
    async def modify_environment(self, environment_id: uuid.UUID, name: str, repository: str, branch: str) -> Apireturn:
        return 200, {"environment": rename_fields(await self.environment_modify(environment_id, name, repository, branch))}

    @protocol.handle(methods.get_environment, environment_id="id", api_version=1)
    async def get_environment(
        self, environment_id: uuid.UUID, versions: Optional[int] = None, resources: Optional[int] = None
    ) -> Apireturn:
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        env = await data.Environment.get_by_id(environment_id)

        if env is None:
            raise NotFound("The environment id does not exist.")

        env_dict = env.to_dict()

        if versions > 0:
            env_dict["versions"] = await data.ConfigurationModel.get_versions(environment_id, limit=versions)

        if resources > 0:
            env_dict["resources"] = await data.Resource.get_resources_report(environment=environment_id)

        return 200, {"environment": env_dict}

    @protocol.handle(methods.list_environments)
    async def list_environments(self) -> Apireturn:
        return 200, {"environments": [rename_fields(env) for env in await self.environment_list()]}

    @protocol.handle(methods.delete_environment, environment_id="id")
    async def delete_environment(self, environment_id: uuid.UUID) -> Apireturn:
        await self.environment_delete(environment_id)
        return 200

    @protocol.handle(methods_v2.halt_environment, env="tid")
    async def halt(self, env: data.Environment) -> None:
        async with self.agent_state_lock:
            async with data.Environment.get_connection() as connection:
                async with connection.transaction():
                    refreshed_env: Optional[data.Environment] = await data.Environment.get_by_id(env.id, connection=connection)
                    if refreshed_env is None:
                        raise NotFound("Environment %s does not exist" % env.id)

                    # silently ignore requests if this environment has already been halted
                    if refreshed_env.halted:
                        return

                    await refreshed_env.update_fields(halted=True, connection=connection)
                    await self.agent_manager.halt_agents(refreshed_env, connection=connection)
            await self.autostarted_agent_manager.stop_agents(refreshed_env)

    @protocol.handle(methods_v2.resume_environment, env="tid")
    async def resume(self, env: data.Environment) -> None:
        async with self.agent_state_lock:
            async with data.Environment.get_connection() as connection:
                async with connection.transaction():
                    refreshed_env: Optional[data.Environment] = await data.Environment.get_by_id(env.id, connection=connection)
                    if refreshed_env is None:
                        raise NotFound("Environment %s does not exist" % env.id)

                    # silently ignore requests if this environment has already been resumed
                    if not refreshed_env.halted:
                        return

                    await refreshed_env.update_fields(halted=False, connection=connection)
                    await self.agent_manager.resume_agents(refreshed_env, connection=connection)
            await self.autostarted_agent_manager.restart_agents(refreshed_env)
        await self.server_slice.compiler.resume_environment(refreshed_env.id)

    @protocol.handle(methods.decomission_environment, env="id")
    async def decommission_environment(self, env: data.Environment, metadata: Optional[JsonType]) -> Apireturn:
        data: Optional[model.ModelMetadata] = None
        if metadata:
            data = model.ModelMetadata(message=metadata.get("message", ""), type=metadata.get("type", ""))

        version = await self.environment_decommission(env, data)
        return 200, {"version": version}

    @protocol.handle(methods.clear_environment, env="id")
    async def clear_environment(self, env: data.Environment) -> Apireturn:
        await self.environment_clear(env)
        return 200

    @protocol.handle(methods.create_token, env="tid")
    async def create_token(self, env: data.Environment, client_types: List[str], idempotent: bool) -> Apireturn:
        """
        Create a new auth token for this environment
        """
        return 200, {"token": await self.environment_create_token(env, client_types, idempotent)}

    @protocol.handle(methods.list_settings, env="tid")
    async def list_settings(self, env: data.Environment) -> Apireturn:
        return 200, {"settings": env.settings, "metadata": data.Environment._settings}

    @protocol.handle(methods.set_setting, env="tid", key="id")
    async def set_setting(self, env: data.Environment, key: str, value: model.EnvSettingType) -> Apireturn:
        try:
            original_env = env.to_dto()
            await env.set(key, value)
            warnings = await self._setting_change(env, key)
            await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
            return attach_warnings(200, None, warnings)
        except KeyError:
            raise NotFound()
        except ValueError as e:
            raise ServerError(f"Invalid value. {e}")

    @protocol.handle(methods.get_setting, env="tid", key="id")
    async def get_setting(self, env: data.Environment, key: str) -> Apireturn:
        setting = await self.environment_setting_get(env, key)
        return 200, {"value": setting.settings[key], "metadata": data.Environment._settings}

    @protocol.handle(methods.delete_setting, env="tid", key="id")
    async def delete_setting(self, env: data.Environment, key: str) -> Apireturn:
        try:
            original_env = env.to_dto()
            await env.unset(key)
            warnings = await self._setting_change(env, key)
            await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
            return attach_warnings(200, None, warnings)
        except KeyError:
            raise NotFound()

    # v2 handlers
    @protocol.handle(methods_v2.environment_create)
    async def environment_create(
        self, project_id: uuid.UUID, name: str, repository: str, branch: str, environment_id: Optional[uuid.UUID]
    ) -> model.Environment:
        if environment_id is None:
            environment_id = uuid.uuid4()

        if (repository is None and branch is not None) or (repository is not None and branch is None):
            raise BadRequest("Repository and branch should be set together.")

        # fetch the project first
        project = await data.Project.get_by_id(project_id)
        if project is None:
            raise NotFound("The project id for the environment does not exist.")

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=project_id, name=name)
        if len(envs) > 0:
            raise ServerError(f"Project {project.name} (id={project.id}) already has an environment with name {name}")

        env = data.Environment(id=environment_id, name=name, project=project_id, repo_url=repository, repo_branch=branch)
        await env.insert()
        await self.notify_listeners(EnvironmentAction.created, env.to_dto())
        return env.to_dto()

    @protocol.handle(methods_v2.environment_modify, environment_id="id")
    async def environment_modify(
        self, environment_id: uuid.UUID, name: str, repository: Optional[str], branch: Optional[str]
    ) -> model.Environment:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            raise NotFound("The environment id does not exist.")
        original_env = env.to_dto()

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=env.project, name=name)
        if len(envs) > 0 and envs[0].id != environment_id:
            raise ServerError(f"Project with id={env.project} already has an environment with name {name}")

        fields = {"name": name}
        if repository is not None:
            fields["repo_url"] = repository

        if branch is not None:
            fields["repo_branch"] = branch

        await env.update_fields(**fields)
        await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
        return env.to_dto()

    @protocol.handle(methods_v2.environment_get, environment_id="id", api_version=2)
    async def environment_get(self, environment_id: uuid.UUID) -> model.Environment:
        env = await data.Environment.get_by_id(environment_id)

        if env is None:
            raise NotFound("The environment id does not exist.")

        return env.to_dto()

    @protocol.handle(methods_v2.environment_list)
    async def environment_list(self) -> List[model.Environment]:
        return [env.to_dto() for env in await data.Environment.get_list()]

    @protocol.handle(methods_v2.environment_delete, environment_id="id")
    async def environment_delete(self, environment_id: uuid.UUID) -> None:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            raise NotFound("The environment with given id does not exist.")

        is_protected_environment = await env.get(data.PROTECTED_ENVIRONMENT)
        if is_protected_environment:
            raise Forbidden(f"Environment {environment_id} is protected. See environment setting: {data.PROTECTED_ENVIRONMENT}")

        await asyncio.gather(self.autostarted_agent_manager.stop_agents(env), env.delete_cascade())

        self.resource_service.close_resource_action_logger(environment_id)
        await self.notify_listeners(EnvironmentAction.deleted, env.to_dto())

    @protocol.handle(methods_v2.environment_decommission, env="id")
    async def environment_decommission(self, env: data.Environment, metadata: Optional[model.ModelMetadata]) -> int:
        is_protected_environment = await env.get(data.PROTECTED_ENVIRONMENT)
        if is_protected_environment:
            raise Forbidden(f"Environment {env.id} is protected. See environment setting: {data.PROTECTED_ENVIRONMENT}")
        version = await env.get_next_version()
        if metadata is None:
            metadata = model.ModelMetadata(message="Decommission of environment", type="api")
        version_info = model.ModelVersionInfo(export_metadata=metadata)
        await self.orchestration_service.put_version(env, version, [], {}, [], version_info.dict(), get_compiler_version())
        return version

    @protocol.handle(methods_v2.environment_clear, env="id")
    async def environment_clear(self, env: data.Environment) -> None:
        """
        Clear the environment
        """
        is_protected_environment = await env.get(data.PROTECTED_ENVIRONMENT)
        if is_protected_environment:
            raise Forbidden(f"Environment {env.id} is protected. See environment setting: {data.PROTECTED_ENVIRONMENT}")

        await self.autostarted_agent_manager.stop_agents(env)
        await env.delete_cascade(only_content=True)

        project_dir = os.path.join(self.server_slice._server_storage["environments"], str(env.id))
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        await self.notify_listeners(EnvironmentAction.cleared, env.to_dto())

    @protocol.handle(methods_v2.environment_create_token, env="tid")
    async def environment_create_token(self, env: data.Environment, client_types: List[str], idempotent: bool) -> str:
        """
        Create a new auth token for this environment
        """
        return encode_token(client_types, str(env.id), idempotent)

    @protocol.handle(methods_v2.environment_settings_list, env="tid")
    async def environment_settings_list(self, env: data.Environment) -> model.EnvironmentSettingsReponse:
        return model.EnvironmentSettingsReponse(
            settings=env.settings, definition={k: v.to_dto() for k, v in data.Environment._settings.items()}
        )

    @protocol.handle(methods_v2.environment_settings_set, env="tid", key="id")
    async def environment_settings_set(self, env: data.Environment, key: str, value: model.EnvSettingType) -> ReturnValue[None]:
        try:
            original_env = env.to_dto()
            await env.set(key, value)
            warnings = await self._setting_change(env, key)
            result: ReturnValue[None] = ReturnValue(response=None)
            if warnings:
                result.add_warnings(warnings)
            await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
            return result
        except KeyError:
            raise NotFound()
        except ValueError:
            raise ServerError("Invalid value")

    @protocol.handle(methods_v2.environment_setting_get, env="tid", key="id")
    async def environment_setting_get(self, env: data.Environment, key: str) -> model.EnvironmentSettingsReponse:
        try:
            value = await env.get(key)
            return model.EnvironmentSettingsReponse(
                settings={key: value}, definition={k: v.to_dto() for k, v in data.Environment._settings.items()}
            )
        except KeyError:
            raise NotFound()

    @protocol.handle(methods_v2.environment_setting_delete, env="tid", key="id")
    async def environment_setting_delete(self, env: data.Environment, key: str) -> ReturnValue[None]:
        try:
            original_env = env.to_dto()
            await env.unset(key)
            warnings = await self._setting_change(env, key)
            result: ReturnValue[None] = ReturnValue(response=None)
            if warnings:
                result.add_warnings(warnings)
            await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
            return result
        except KeyError:
            raise NotFound()

    def register_listener_for_multiple_actions(self, listener, actions: Set[EnvironmentAction]) -> None:
        """
            Should only be called during pre-start
        :param listener: The listener to register
        :param actions: type of actions the listener is interested in
        """
        for action in actions:
            self.register_listener(listener, action)

    def register_listener(self, listener: EnvironmentListener, action: EnvironmentAction) -> None:
        """
            Should only be called during pre-start
        :param listener: The listener to register
        :param action: type of action the listener is interested in
        """
        self.listeners[action].append(listener)

    def remove_listener(self, action: EnvironmentAction, listener: EnvironmentListener) -> None:
        self.listeners[action].remove(listener)

    async def notify_listeners(
        self, action: EnvironmentAction, updated_env: model.Environment, original_env: Optional[model.Environment] = None
    ) -> None:
        for listener in self.listeners[action]:
            try:
                if action == EnvironmentAction.created:
                    await listener.environment_action_created(updated_env)
                if action == EnvironmentAction.deleted:
                    await listener.environment_action_deleted(updated_env)
                if action == EnvironmentAction.cleared:
                    await listener.environment_action_cleared(updated_env)
                if action == EnvironmentAction.updated:
                    await listener.environment_action_updated(updated_env, original_env)
            except Exception:
                LOGGER.warning(f"Notifying listener of {action} failed with the following exception", exc_info=True)
