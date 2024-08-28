"""
    Copyright 2024 Inmanta
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
import datetime
import logging
import typing
import uuid
from asyncio import Lock
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Optional

import pkg_resources

import inmanta.agent.cache
import inmanta.protocol
import inmanta.util
import logfire
from inmanta import const, data, env
from inmanta.agent import executor, handler
from inmanta.agent.executor import FailedResources, ResourceDetails
from inmanta.agent.handler import HandlerAPI, SkipResource
from inmanta.const import ParameterSource
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.loader import CodeLoader
from inmanta.resources import Id, Resource
from inmanta.types import Apireturn
from inmanta.util import NamedLock

if typing.TYPE_CHECKING:
    import inmanta.agent.agent as agent


class InProcessExecutor(executor.Executor, executor.AgentInstance):
    """
    This is an executor that executes in the process it is started in
    """

    def __init__(
        self,
        agent_name: str,
        agent_uri: str,
        environment: uuid.UUID,
        client: inmanta.protocol.SessionClient,
        eventloop: asyncio.AbstractEventLoop,
        parent_logger: logging.Logger,
    ):
        self.name = agent_name
        self.client = client
        self.uri = agent_uri

        # For agentinstance api
        self.eventloop = eventloop
        self.sessionid = client._sid
        self.environment = environment

        # threads to work
        self.thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="Pool_%s" % self.name)

        self._cache = inmanta.agent.cache.AgentCache(self)
        # This lock ensures cache entries can not be cleaned up when
        # the executor is actively working and vice versa
        self.activity_lock = asyncio.Lock()

        self.logger: logging.Logger = parent_logger.getChild(self.name)

        self._stopped = False

        self.failed_resources: FailedResources = dict()

        self.cache_cleanup_tick_rate = inmanta.agent.config.agent_cache_cleanup_tick_rate.get()
        self.periodic_cache_cleanup_job: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        self.periodic_cache_cleanup_job = asyncio.create_task(self.cleanup_stale_cache_entries())

    async def cleanup_stale_cache_entries(self) -> None:
        """
        Periodically cleans up stale entries in the cache. The clean_stale_entries
        has to be called on the thread pool because it might call finalizers.
        """
        reschedule_interval: int = self.cache_cleanup_tick_rate
        while not self._stopped:
            async with self.activity_lock:
                if self._stopped:
                    return
                try:
                    await asyncio.get_running_loop().run_in_executor(self.thread_pool, self._cache.clean_stale_entries)
                except Exception:
                    # Make sure we don't drop out of the while loop if an exception occurs.
                    self.logger.exception(
                        "An unexpected exception occurred while cleaning up the cache of agent %s.", self.name
                    )
            await asyncio.sleep(reschedule_interval)

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self.periodic_cache_cleanup_job:
            try:
                self.periodic_cache_cleanup_job.cancel()
                await self.periodic_cache_cleanup_job
            except asyncio.CancelledError:
                pass
        async with self.activity_lock:
            await asyncio.get_running_loop().run_in_executor(self.thread_pool, self._cache.close)
        self.thread_pool.shutdown(wait=False)

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor]) -> None:
        """
        Called after stop to ensure complete shutdown

        :param thread_pool_finalizer: all threadpools that should be joined should be added here.
        """
        assert self._stopped
        thread_pool_finalizer.append(self.thread_pool)
        if self.periodic_cache_cleanup_job:
            try:
                await self.periodic_cache_cleanup_job
            except asyncio.CancelledError:
                self.periodic_cache_cleanup_job = None

    def is_stopped(self) -> bool:
        return self._stopped

    async def get_provider(self, resource: Resource) -> HandlerAPI[Any]:
        provider = handler.Commander.get_provider(agent=self, resource=resource)
        provider.set_cache(self._cache)
        return provider

    async def send_in_progress(
        self, action_id: uuid.UUID, env_id: uuid.UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        result = await self.client.resource_deploy_start(
            tid=env_id,
            rvid=resource_id,
            action_id=action_id,
        )
        if result.code != 200 or result.result is None:
            raise Exception("Failed to report the start of the deployment to the server")
        return {Id.parse_id(key).resource_str(): const.ResourceState[value] for key, value in result.result["data"].items()}

    async def _execute(
        self,
        resource: Resource,
        gid: uuid.UUID,
        ctx: handler.HandlerContext,
        requires: dict[ResourceIdStr, const.ResourceState],
    ) -> None:
        """
        Get the handler for a given resource and run its ``deploy`` method.

        :param resource: The resource to deploy.
        :param gid: Id of this deploy.
        :param ctx: The context to use during execution of this deploy.
        :param requires: A dictionary that maps each dependency of the resource to be deployed, to its latest resource
                         state that was not `deploying'.
        """
        # setup provider
        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s", deploy_id=gid, resource_id=resource.id)

        provider: Optional[HandlerAPI[Any]] = None
        try:
            provider = await self.get_provider(resource)
        except Exception:
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=resource.id.resource_version_str())
            return
        else:
            # main execution
            try:
                await asyncio.get_running_loop().run_in_executor(
                    self.thread_pool,
                    provider.deploy,
                    ctx,
                    resource,
                    requires,
                )
                if ctx.status is None:
                    ctx.set_status(const.ResourceState.deployed)
            except SkipResource as e:
                ctx.set_status(const.ResourceState.skipped)
                ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)
            except Exception as e:
                ctx.set_status(const.ResourceState.failed)
                ctx.exception(
                    "An error occurred during deployment of %(resource_id)s (exception: %(exception)s",
                    resource_id=resource.id,
                    exception=repr(e),
                )
        finally:
            if provider is not None:
                provider.close()

    async def _report_resource_deploy_done(
        self,
        resource_details: ResourceDetails,
        ctx: handler.HandlerContext,
    ) -> None:
        """
        Report the end of a resource deployment to the server.

        :param resource_details: Deployed resource being reported.
        :param ctx: Context of the associated handler.
        """

        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]] = {resource_details.rvid: ctx.changes}
        response = await self.client.resource_deploy_done(
            tid=resource_details.env_id,
            rvid=resource_details.rvid,
            action_id=ctx.action_id,
            status=ctx.status,
            messages=ctx.logs,
            changes=changes,
            change=ctx.change,
        )
        if response.code != 200:
            self.logger.error("Resource status update failed %s for %s ", response.result, resource_details.rvid)

    async def deserialize(self, resource_details: ResourceDetails, action: const.ResourceAction) -> Optional[Resource]:
        started: datetime.datetime = datetime.datetime.now().astimezone()
        try:
            return Resource.deserialize(resource_details.attributes)
        except Exception:
            msg = data.LogLine.log(
                level=const.LogLevel.ERROR,
                msg="Unable to deserialize %(resource_id)s",
                resource_id=resource_details.rvid,
                timestamp=datetime.datetime.now().astimezone(),
            )

            await self.client.resource_action_update(
                tid=resource_details.env_id,
                resource_ids=[resource_details.rvid],
                action_id=uuid.uuid4(),
                action=action,
                started=started,
                finished=datetime.datetime.now().astimezone(),
                status=const.ResourceState.unavailable,
                messages=[msg],
            )
            raise

    @logfire.instrument("InProcessExecutor.execute", extract_args=True)
    async def execute(
        self,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
    ) -> None:
        try:
            resource: Resource | None = await self.deserialize(resource_details, const.ResourceAction.deploy)
        except Exception:
            return
        assert resource is not None
        ctx = handler.HandlerContext(resource, logger=self.logger)
        ctx.debug(
            "Start run for resource %(resource)s because %(reason)s",
            resource=str(resource_details.rvid),
            deploy_id=gid,
            agent=self.name,
            reason=reason,
        )

        try:
            requires: dict[ResourceIdStr, const.ResourceState] = await self.send_in_progress(
                ctx.action_id, resource_details.env_id, resource_details.rvid
            )
        except Exception:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception("Failed to report the start of the deployment to the server")
            return

        async with self.activity_lock:
            await self._execute(resource, gid=gid, ctx=ctx, requires=requires)

        ctx.debug(
            "End run for resource %(r_id)s in deploy %(deploy_id)s",
            r_id=resource_details.rvid,
            deploy_id=gid,
        )

        if ctx.facts:
            ctx.debug("Sending facts to the server")
            set_fact_response = await self.client.set_parameters(tid=resource_details.env_id, parameters=ctx.facts)
            if set_fact_response.code != 200:
                ctx.error("Failed to send facts to the server %s", set_fact_response.result)

        await self._report_resource_deploy_done(resource_details, ctx)

    async def dry_run(
        self,
        resources: Sequence[ResourceDetails],
        dry_run_id: uuid.UUID,
    ) -> None:
        """
        Perform a dryrun for the given resources

        :param resources: Sequence of resources for which to perform a dryrun.
        :param dry_run_id: id for this dryrun
        """
        model_version: int = resources[0].model_version

        env_id: uuid.UUID = resources[0].env_id

        # TODO remove versioned cache:
        async with self.activity_lock, self.cache(model_version):
            for resource in resources:
                try:
                    resource_obj: Resource | None = await self.deserialize(resource, const.ResourceAction.dryrun)
                except Exception:
                    await self.client.dryrun_update(tid=env_id, id=dry_run_id, resource=resource.rvid, changes={})
                    continue
                assert resource_obj is not None
                ctx = handler.HandlerContext(resource_obj, True)
                started = datetime.datetime.now().astimezone()
                provider = None

                resource_id: ResourceVersionIdStr = resource.rvid

                try:
                    self.logger.debug("Running dryrun for %s", resource_id)

                    try:
                        provider = await self.get_provider(resource_obj)
                    except Exception as e:
                        ctx.exception(
                            "Unable to find a handler for %(resource_id)s (exception: %(exception)s",
                            resource_id=resource_id,
                            exception=str(e),
                        )
                        await self.client.dryrun_update(
                            tid=env_id,
                            id=dry_run_id,
                            resource=resource_id,
                            changes={"handler": {"current": "FAILED", "desired": "Unable to find a handler"}},
                        )
                    else:
                        try:
                            await asyncio.get_running_loop().run_in_executor(
                                self.thread_pool, provider.execute, ctx, resource_obj, True
                            )

                            changes = ctx.changes
                            if changes is None:
                                changes = {}
                            if ctx.status == const.ResourceState.failed:
                                changes["handler"] = AttributeStateChange(current="FAILED", desired="Handler failed")
                            await self.client.dryrun_update(tid=env_id, id=dry_run_id, resource=resource_id, changes=changes)
                        except Exception as e:
                            ctx.exception(
                                "Exception during dryrun for %(resource_id)s (exception: %(exception)s",
                                resource_id=resource.rvid,
                                exception=str(e),
                            )
                            changes = ctx.changes
                            if changes is None:
                                changes = {}
                            changes["handler"] = AttributeStateChange(current="FAILED", desired="Handler failed")
                            await self.client.dryrun_update(tid=env_id, id=dry_run_id, resource=resource_id, changes=changes)

                except Exception:
                    ctx.exception("Unable to process resource for dryrun.")
                    changes = {}
                    changes["handler"] = AttributeStateChange(current="FAILED", desired="Resource Deserialization Failed")
                    await self.client.dryrun_update(tid=env_id, id=dry_run_id, resource=resource_id, changes=changes)
                finally:
                    if provider is not None:
                        provider.close()

                    finished = datetime.datetime.now().astimezone()
                    await self.client.resource_action_update(
                        tid=env_id,
                        resource_ids=[resource_id],
                        action_id=ctx.action_id,
                        action=const.ResourceAction.dryrun,
                        started=started,
                        finished=finished,
                        messages=ctx.logs,
                        status=const.ResourceState.dry,
                    )

    async def get_facts(self, resource: ResourceDetails) -> Apireturn:
        """
        Get facts for a given resource
        :param resource: The resource for which to get facts.
        """
        model_version: int = resource.model_version
        env_id: uuid.UUID = resource.env_id

        provider = None
        try:
            try:
                resource_obj: Resource | None = await self.deserialize(resource, const.ResourceAction.getfact)
            except Exception:
                return 500
            assert resource_obj is not None
            ctx = handler.HandlerContext(resource_obj)
            # TODO remove versioned cache:
            async with self.activity_lock, self.cache(model_version):
                try:
                    started = datetime.datetime.now().astimezone()
                    provider = await self.get_provider(resource_obj)
                    result = await asyncio.get_running_loop().run_in_executor(
                        self.thread_pool, provider.check_facts, ctx, resource_obj
                    )

                    parameters = [
                        {
                            "id": name,
                            "value": value,
                            "resource_id": resource.rid,
                            "source": ParameterSource.fact.value,
                        }
                        for name, value in result.items()
                    ]
                    # Add facts set via the set_fact() method of the HandlerContext
                    parameters.extend(ctx.facts)

                    await self.client.set_parameters(tid=env_id, parameters=parameters)
                    finished = datetime.datetime.now().astimezone()
                    await self.client.resource_action_update(
                        tid=env_id,
                        resource_ids=[resource.rvid],
                        action_id=ctx.action_id,
                        action=const.ResourceAction.getfact,
                        started=started,
                        finished=finished,
                        messages=ctx.logs,
                    )

                except Exception:
                    self.logger.exception("Unable to retrieve fact")

        except Exception:
            self.logger.exception("Unable to find a handler for %s", resource.id)
            return 500
        finally:
            if provider is not None:
                provider.close()
        return 200

    async def open_version(self, version: int) -> None:
        """
        Open a version on the cache
        """
        self._cache.open_version(version)

    async def close_version(self, version: int) -> None:
        """
        Close a version on the cache
        """
        # Needs to run on threadpool due to finalizers?
        # https://github.com/inmanta/inmanta-core/issues/833
        self._cache.close_version(version)


class InProcessExecutorManager(executor.ExecutorManager[InProcessExecutor]):
    """
    This is the executor that provides the backward compatible behavior, conforming to the agent in ISO7.

    It spawns an InProcessExecutor and makes sure all code is installed and loadable locally.
    """

    def __init__(
        self,
        environment: uuid.UUID,
        client: inmanta.protocol.SessionClient,
        eventloop: asyncio.AbstractEventLoop,
        parent_logger: logging.Logger,
        process: "agent.Agent",
        code_dir: str,
        env_dir: str,
        code_loader: bool = True,
    ) -> None:
        self.environment = environment
        self.client = client
        self.eventloop = eventloop
        self.logger = parent_logger
        self.process = process

        self.executors: dict[str, InProcessExecutor] = {}
        self._creation_locks: inmanta.util.NamedLock = inmanta.util.NamedLock()

        self._loader: CodeLoader | None = None
        self._env: env.VirtualEnv | None = None

        if code_loader:
            self._env = env.VirtualEnv(env_dir)
            self._env.use_virtual_env()
            self._loader = CodeLoader(code_dir, clean=True)
            # Lock to ensure only one actual install runs at a time
            self._loader_lock: asyncio.Lock = Lock()
            # Keep track for each resource type of the last loaded version
            self._last_loaded_version: dict[str, executor.ExecutorBlueprint | None] = defaultdict(lambda: None)
            # Per-resource lock to serialize all actions per resource
            self._resource_loader_lock: NamedLock = NamedLock()

    async def stop(self) -> None:
        for child in self.executors.values():
            await child.stop()

    async def start(self) -> None:
        pass

    async def stop_for_agent(self, agent_name: str) -> list[InProcessExecutor]:
        if agent_name in self.executors:
            out = self.executors[agent_name]
            del self.executors[agent_name]
            await out.stop()
            return [out]
        return []

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        for child in self.executors.values():
            await child.join(thread_pool_finalizer)

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[executor.ResourceInstallSpec]
    ) -> InProcessExecutor:
        """
        Retrieves an Executor for a given agent with the relevant handler code loaded in its venv.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param agent_uri: The name of the host on which the agent is running.
        :param code: Collection of ResourceInstallSpec defining the configuration for the Executor i.e.
            which resource types it can act on and all necessary information to install the relevant
            handler code in its venv.
        :return: An Executor instance
        """
        if agent_name in self.executors:
            out = self.executors[agent_name]
        else:
            async with self._creation_locks.get(agent_name):
                if agent_name in self.executors:
                    out = self.executors[agent_name]
                else:
                    out = InProcessExecutor(agent_name, agent_uri, self.environment, self.client, self.eventloop, self.logger)
                    await out.start()
                    self.executors[agent_name] = out
        assert out.uri == agent_uri
        out.failed_resources = await self.ensure_code(code)

        return out

    async def ensure_code(self, code: typing.Collection[executor.ResourceInstallSpec]) -> executor.FailedResources:
        """Ensure that the code for the given environment and version is loaded"""

        failed_to_load: executor.FailedResources = {}

        if self._loader is None:
            return failed_to_load

        for resource_install_spec in code:
            # only one logical thread can load a particular resource type at any time
            async with self._resource_loader_lock.get(resource_install_spec.resource_type):
                # stop if the last successful load was this one
                # The combination of the lock and this check causes the reloads to naturally 'batch up'
                if self._last_loaded_version[resource_install_spec.resource_type] == resource_install_spec.blueprint:
                    self.logger.debug(
                        "Handler code already installed for %s version=%d",
                        resource_install_spec.resource_type,
                        resource_install_spec.model_version,
                    )
                    continue

                try:
                    # Install required python packages and the list of ``ModuleSource`` with the provided pip config
                    self.logger.debug(
                        "Installing handler %s version=%d",
                        resource_install_spec.resource_type,
                        resource_install_spec.model_version,
                    )
                    await self._install(resource_install_spec.blueprint)
                    self.logger.debug(
                        "Installed handler %s version=%d",
                        resource_install_spec.resource_type,
                        resource_install_spec.model_version,
                    )

                    self._last_loaded_version[resource_install_spec.resource_type] = resource_install_spec.blueprint
                except Exception as e:
                    self.logger.exception(
                        "Failed to install handler %s version=%d",
                        resource_install_spec.resource_type,
                        resource_install_spec.model_version,
                    )
                    if resource_install_spec.resource_type not in failed_to_load:
                        failed_to_load[resource_install_spec.resource_type] = Exception(
                            f"Failed to install handler {resource_install_spec.resource_type} "
                            f"version={resource_install_spec.model_version}: {e}"
                        ).with_traceback(e.__traceback__)
                    self._last_loaded_version[resource_install_spec.resource_type] = None

        return failed_to_load

    async def _install(self, blueprint: executor.ExecutorBlueprint) -> None:
        if self._env is None or self._loader is None:
            raise Exception("Unable to load code when agent is started with code loading disabled.")

        async with self._loader_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self.process.thread_pool,
                self._env.install_for_config,
                list(pkg_resources.parse_requirements(blueprint.requirements)),
                blueprint.pip_config,
            )
            await loop.run_in_executor(self.process.thread_pool, self._loader.deploy_version, blueprint.sources)
