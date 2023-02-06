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
import base64
import binascii
import logging
import os
import re
import shutil
import uuid
import warnings
from collections import defaultdict
from collections.abc import Set
from enum import Enum
from typing import Dict, List, Optional, Pattern, cast

from asyncpg import StringDataRightTruncationError

from inmanta import config, data
from inmanta.data import Setting, model
from inmanta.protocol import encode_token, handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, Forbidden, NotFound, ServerError
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_COMPILER,
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
from inmanta.server.services.compilerservice import CompilerService
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
    icon_regex: Pattern[str] = re.compile("^(image/png|image/jpeg|image/webp|image/svg\\+xml);(base64),(.+)$")

    def __init__(self) -> None:
        super(EnvironmentService, self).__init__(SLICE_ENVIRONMENT)
        self.listeners = defaultdict(list)
        self.agent_state_lock = asyncio.Lock()

    def get_dependencies(self) -> List[str]:
        return [
            SLICE_COMPILER,
            SLICE_SERVER,
            SLICE_DATABASE,
            SLICE_AUTOSTARTED_AGENT_MANAGER,
            SLICE_ORCHESTRATION,
            SLICE_RESOURCE,
        ]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))
        self.agent_manager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))
        self.compiler_service = cast(CompilerService, server.get_slice(SLICE_COMPILER))
        self.orchestration_service = cast(OrchestrationService, server.get_slice(SLICE_ORCHESTRATION))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

    async def start(self) -> None:
        await super().start()
        await self._enable_schedules_all_envs()

    async def _enable_schedules_all_envs(self) -> None:
        """
        Schedules appropriate actions for schedule-related settings for all environments. Overrides old schedules.
        """
        env: data.Environment
        for env in await data.Environment.get_list(details=False):
            await self._enable_schedules(env)

    async def _enable_schedules(self, env: data.Environment, setting: Optional[data.Setting] = None) -> None:
        """
        Schedules appropriate actions for a single environment according to the settting value. Overrides old schedules.

        :param setting: Only schedule appropriate actions for this setting, if any.
        """
        if setting is None or setting.name == data.AUTO_FULL_COMPILE:
            if setting is not None:
                LOGGER.info("Environment setting %s changed. Rescheduling full compiles.", setting.name)
            self.compiler_service.schedule_full_compile(env, await env.get(data.AUTO_FULL_COMPILE))

    def _disable_schedules(self, env: data.Environment) -> None:
        """
        Removes scheduling of all appropriate actions for a single environment.
        """
        self.compiler_service.schedule_full_compile(env, schedule_cron="")

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

        self.add_background_task(self._enable_schedules(env, setting))

        return warnings

    # v1 handlers
    @handle(methods.create_environment)
    async def create_environment(
        self, project_id: uuid.UUID, name: str, repository: str, branch: str, environment_id: Optional[uuid.UUID]
    ) -> Apireturn:
        return (
            200,
            {"environment": rename_fields(await self.environment_create(project_id, name, repository, branch, environment_id))},
        )

    @handle(methods.modify_environment, environment_id="id")
    async def modify_environment(self, environment_id: uuid.UUID, name: str, repository: str, branch: str) -> Apireturn:
        return 200, {"environment": rename_fields(await self.environment_modify(environment_id, name, repository, branch))}

    @handle(methods.get_environment, environment_id="id", api_version=1)
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

    @handle(methods.list_environments)
    async def list_environments(self) -> Apireturn:
        return 200, {"environments": [rename_fields(env) for env in await self.environment_list()]}

    @handle(methods.delete_environment, environment_id="id")
    async def delete_environment(self, environment_id: uuid.UUID) -> Apireturn:
        await self.environment_delete(environment_id)
        return 200

    @handle(methods_v2.halt_environment, env="tid")
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

    @handle(methods_v2.resume_environment, env="tid")
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

    @handle(methods.decomission_environment, env="id")
    async def decommission_environment(self, env: data.Environment, metadata: Optional[JsonType]) -> Apireturn:
        data: Optional[model.ModelMetadata] = None
        if metadata:
            data = model.ModelMetadata(message=metadata.get("message", ""), type=metadata.get("type", ""))

        version = await self.environment_decommission(env, data)
        return 200, {"version": version}

    @handle(methods.clear_environment, env="id")
    async def clear_environment(self, env: data.Environment) -> Apireturn:
        await self.environment_clear(env)
        return 200

    @handle(methods.create_token, env="tid")
    async def create_token(self, env: data.Environment, client_types: List[str], idempotent: bool) -> Apireturn:
        """
        Create a new auth token for this environment
        """
        return 200, {"token": await self.environment_create_token(env, client_types, idempotent)}

    @handle(methods.list_settings, env="tid")
    async def list_settings(self, env: data.Environment) -> Apireturn:
        settings = {k: env.settings[k] for k in env.settings.keys() if k in data.Environment._settings.keys()}
        return 200, {"settings": settings, "metadata": data.Environment._settings}

    @handle(methods.set_setting, env="tid", key="id")
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
            raise BadRequest(f"Invalid value. {e}")

    @handle(methods.get_setting, env="tid", key="id")
    async def get_setting(self, env: data.Environment, key: str) -> Apireturn:
        setting = await self.environment_setting_get(env, key)
        return 200, {"value": setting.settings[key], "metadata": data.Environment._settings}

    @handle(methods.delete_setting, env="tid", key="id")
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
    @handle(methods_v2.environment_create)
    async def environment_create(
        self,
        project_id: uuid.UUID,
        name: str,
        repository: str,
        branch: str,
        environment_id: Optional[uuid.UUID],
        description: str = "",
        icon: str = "",
    ) -> model.Environment:
        if environment_id is None:
            environment_id = uuid.uuid4()

        if (repository is None and branch is not None) or (repository is not None and branch is None):
            raise BadRequest("Repository and branch should be set together.")
        if repository is None:
            repository = ""
        if branch is None:
            branch = ""

        # fetch the project first
        project = await data.Project.get_by_id(project_id)
        if project is None:
            raise NotFound("The project id for the environment does not exist.")

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=project_id, name=name)
        if len(envs) > 0:
            raise ServerError(f"Project {project.name} (id={project.id}) already has an environment with name {name}")

        self.validate_icon(icon)

        env = data.Environment(
            id=environment_id,
            name=name,
            project=project_id,
            repo_url=repository,
            repo_branch=branch,
            description=description,
            icon=icon,
        )
        try:
            await env.insert()
        except StringDataRightTruncationError:
            raise BadRequest("Maximum size of the icon data url or the description exceeded")
        await self.notify_listeners(EnvironmentAction.created, env.to_dto())
        await self._enable_schedules(env)
        return env.to_dto()

    def validate_icon(self, icon: str) -> None:
        """Check if the icon is in the supported format, raise an exception otherwise"""
        if icon == "":
            return
        match = self.icon_regex.match(icon)
        if match and len(match.groups()) == 3:
            encoded_image = match.groups()[2]
            try:
                base64.b64decode(encoded_image, validate=True)
            except binascii.Error:
                raise BadRequest("The icon is not a valid base64 encoded string")
        else:
            raise BadRequest("The value supplied for the icon parameter is invalid")

    @handle(methods_v2.environment_modify, environment_id="id")
    async def environment_modify(
        self,
        environment_id: uuid.UUID,
        name: str,
        repository: Optional[str],
        branch: Optional[str],
        project_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> model.Environment:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            raise NotFound("The environment id does not exist.")
        original_env = env.to_dto()

        project = project_id or env.project

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=project, name=name)
        if len(envs) > 0 and envs[0].id != environment_id:
            raise BadRequest(f"Project with id={project} already has an environment with name {name}")

        fields = {"name": name}
        if repository is not None:
            fields["repo_url"] = repository

        if branch is not None:
            fields["repo_branch"] = branch

        # Update the project field if requested and the project exists
        if project_id is not None:
            project_from_db = await data.Project.get_by_id(project_id)
            if not project_from_db:
                raise BadRequest(f"Project with id={project_id} doesn't exist")
            fields["project"] = project_id

        if description is not None:
            fields["description"] = description

        if icon is not None:
            self.validate_icon(icon)
            fields["icon"] = icon

        try:
            await env.update_fields(connection=None, **fields)
        except StringDataRightTruncationError:
            raise BadRequest("Maximum size of the icon data url or the description exceeded")
        await self.notify_listeners(EnvironmentAction.updated, env.to_dto(), original_env)
        return env.to_dto()

    @handle(methods_v2.environment_get, environment_id="id", api_version=2)
    async def environment_get(self, environment_id: uuid.UUID, details: bool = False) -> model.Environment:
        env = await data.Environment.get_by_id(environment_id, details=details)

        if env is None:
            raise NotFound("The environment id does not exist.")

        return env.to_dto()

    @handle(methods_v2.environment_list)
    async def environment_list(self, details: bool = False) -> List[model.Environment]:
        # data access framework does not support multi-column order by, but multi-environment projects are rare
        # (and discouraged)
        # => sort by primary column in SQL, then do full sort in Python, cheap because mostly sorted already by this point
        env_list = await data.Environment.get_list(details=details, order_by_column="project")
        return sorted((env.to_dto() for env in env_list), key=lambda e: (e.project_id, e.name, e.id))

    @handle(methods_v2.environment_delete, environment_id="id")
    async def environment_delete(self, environment_id: uuid.UUID) -> None:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            raise NotFound("The environment with given id does not exist.")

        is_protected_environment = await env.get(data.PROTECTED_ENVIRONMENT)
        if is_protected_environment:
            raise Forbidden(f"Environment {environment_id} is protected. See environment setting: {data.PROTECTED_ENVIRONMENT}")

        self._disable_schedules(env)
        await asyncio.gather(self.autostarted_agent_manager.stop_agents(env), env.delete_cascade())

        self.resource_service.close_resource_action_logger(environment_id)
        await self.notify_listeners(EnvironmentAction.deleted, env.to_dto())

    @handle(methods_v2.environment_decommission, env="id")
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

    @handle(methods_v2.environment_clear, env="id")
    async def environment_clear(self, env: data.Environment) -> None:
        """
        Clear the environment
        """
        is_protected_environment = await env.get(data.PROTECTED_ENVIRONMENT)
        if is_protected_environment:
            raise Forbidden(f"Environment {env.id} is protected. See environment setting: {data.PROTECTED_ENVIRONMENT}")

        await self.autostarted_agent_manager.stop_agents(env)
        await env.delete_cascade(only_content=True)

        await self.notify_listeners(EnvironmentAction.cleared, env.to_dto())

        project_dir = os.path.join(self.server_slice._server_storage["environments"], str(env.id))
        if os.path.exists(project_dir):
            # This call might fail when someone manually creates a directory or file that is owned
            # by another user than the user running the inmanta server. Execute rmtree() after
            # notify_listeners() to ensure that the listeners are notified.
            shutil.rmtree(project_dir)

    @handle(methods_v2.environment_create_token, env="tid")
    async def environment_create_token(self, env: data.Environment, client_types: List[str], idempotent: bool) -> str:
        """
        Create a new auth token for this environment
        """
        if not config.Config.getboolean("server", "auth", False):
            raise BadRequest("Authentication is disabled, generating a token is not allowed")
        return encode_token(client_types, str(env.id), idempotent)

    @handle(methods_v2.environment_settings_list, env="tid")
    async def environment_settings_list(self, env: data.Environment) -> model.EnvironmentSettingsReponse:
        return model.EnvironmentSettingsReponse(
            settings=env.settings, definition={k: v.to_dto() for k, v in data.Environment._settings.items()}
        )

    @handle(methods_v2.environment_settings_set, env="tid", key="id")
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

    @handle(methods_v2.environment_setting_get, env="tid", key="id")
    async def environment_setting_get(self, env: data.Environment, key: str) -> model.EnvironmentSettingsReponse:
        try:
            value = await env.get(key)
            return model.EnvironmentSettingsReponse(
                settings={key: value}, definition={k: v.to_dto() for k, v in data.Environment._settings.items()}
            )
        except KeyError:
            raise NotFound()

    @handle(methods_v2.environment_setting_delete, env="tid", key="id")
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

    def register_listener_for_multiple_actions(self, listener: EnvironmentListener, actions: Set[EnvironmentAction]) -> None:
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
                if action == EnvironmentAction.updated and original_env:
                    await listener.environment_action_updated(updated_env, original_env)
            except Exception:
                LOGGER.warning("Notifying listener of %s failed with the following exception", action.value, exc_info=True)

    async def register_setting(self, setting: Setting) -> None:
        """
        Should only be called during pre-start
        Adds a new setting to the environments from outside inmanta-core.
        As example, inmanta-lsm can use this method to add settings that are only
        relevant for inmanta-lsm but that are needed in the environment.
        :param setting: the setting that should be added to the existing settings
        """
        warnings.warn(
            "Registering environment settings via the inmanta.server.services.environmentservice.register_setting endpoint "
            "is deprecated. Environment settings defined by an extension should be advertised via the "
            "register_environment_settings method of the inmanta_ext.<extension_name>.extension.py file of an extension.",
            category=DeprecationWarning,
        )
        data.Environment.register_setting(setting)
