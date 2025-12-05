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
from asyncio import InvalidStateError, Lock
from collections import defaultdict
from collections.abc import Mapping
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Optional

import inmanta.agent.cache
import inmanta.loader as loader
import inmanta.protocol
import inmanta.util
from inmanta import const, data, env, tracing
from inmanta.agent import executor, handler
from inmanta.agent.executor import DeployReport, DryrunReport, FailedInmantaModules, GetFactReport, ResourceDetails
from inmanta.agent.handler import HandlerAPI, SkipResource, SkipResourceForDependencies
from inmanta.const import NAME_RESOURCE_ACTION_LOGGER, ParameterSource
from inmanta.data.model import AttributeStateChange
from inmanta.resources import Resource
from inmanta.types import ResourceIdStr, ResourceVersionIdStr
from inmanta.util import NamedLock, join_threadpools


class InProcessExecutor(executor.Executor, executor.AgentInstance):
    """
    This is an executor that executes in the process it is started in. It executes the appropriate handler code in this same
    process.

    !!! This executor takes no steps to prevent handlers to mutate the resources passed into the methods !!!
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
        self.resource_action_logger = logging.getLogger(NAME_RESOURCE_ACTION_LOGGER).getChild(self.name)

        self._stopped = False

        self.failed_modules: FailedInmantaModules = dict()

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

    async def join(self) -> None:
        """
        Called after stop to ensure complete shutdown

        :param thread_pool_finalizer: all threadpools that should be joined should be added here.
        """
        assert self._stopped
        await join_threadpools([self.thread_pool])
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

    def _log_deserialization_error(self, resource_details: ResourceDetails, cause: Exception) -> data.LogLine:
        msg = data.LogLine.log(
            level=const.LogLevel.ERROR,
            msg="Unable to deserialize %(resource_id)s: %(cause)s",
            resource_id=resource_details.rvid,
            cause=cause,
            timestamp=datetime.datetime.now().astimezone(),
        )
        msg.write_to_logger_for_resource(
            agent=resource_details.id.agent_name, resource_version_string=resource_details.rvid, exc_info=True
        )
        return msg

    async def _execute(
        self,
        resource: Resource,
        ctx: handler.HandlerContext,
        requires: Mapping[ResourceIdStr, const.ResourceState],
    ) -> None:
        """
        Get the handler for a given resource and run its ``deploy`` method.

        :param resource: The resource to deploy.
        :param ctx: The context to use during execution of this deploy.
        :param requires: A dictionary that maps each dependency of the resource to be deployed, to its latest resource
                         state that was not `deploying'.
        """
        # setup provider

        provider: Optional[HandlerAPI[Any]] = None
        try:
            provider = await self.get_provider(resource)
        except Exception:
            ctx.set_resource_state(const.HandlerResourceState.unavailable)
            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=resource.id.resource_version_str())
            return
        else:
            # main execution
            try:

                def resolve_and_deploy(
                    provider: HandlerAPI[Resource],
                    ctx: handler.HandlerContext,
                    resource: Resource,
                    requires: Mapping[ResourceIdStr, const.ResourceState],
                ) -> None:
                    resource.resolve_all_references(ctx)
                    provider.deploy(ctx, resource, requires)

                await asyncio.get_running_loop().run_in_executor(
                    self.thread_pool,
                    resolve_and_deploy,
                    provider,
                    ctx,
                    resource,
                    requires,
                )
                if ctx.status is None:
                    ctx.set_resource_state(const.HandlerResourceState.deployed)
            except SkipResourceForDependencies as e:
                ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
                ctx.warning(
                    msg="Resource %(resource_id)s was skipped: %(reason)s",
                    resource_id=resource.id,
                    reason=e.args,
                )
            except SkipResource as e:
                ctx.set_resource_state(const.HandlerResourceState.skipped)
                ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)
            except Exception as e:
                ctx.set_resource_state(const.HandlerResourceState.failed)
                ctx.exception(
                    "An error occurred during deployment of %(resource_id)s (exception: %(exception)s",
                    resource_id=str(resource.id),
                    exception=repr(e),
                )
        finally:
            if provider is not None:
                provider.close()

    @tracing.instrument("InProcessExecutor.execute", extract_args=True)
    async def execute(
        self,
        action_id: uuid.UUID,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
        requires: Mapping[ResourceIdStr, const.ResourceState],
    ) -> DeployReport:
        try:
            resource: Resource = Resource.deserialize(resource_details.attributes)
        except Exception as e:
            msg = self._log_deserialization_error(resource_details, e)
            return DeployReport.undeployable(resource_details.rvid, action_id, msg)

        ctx = handler.HandlerContext(resource, action_id=action_id, logger=self.resource_action_logger)

        ctx.debug(
            "Start run because %(reason)s.",
            reason=reason,
            deploy_id=gid,
            resource=resource_details.id,
        )

        async with self.activity_lock:
            with self._cache:
                await self._execute(resource, ctx=ctx, requires=requires)

        ctx.debug(
            "End run for resource %(r_id)s in deploy %(deploy_id)s",
            r_id=resource_details.rvid,
            deploy_id=gid,
        )

        if ctx.facts:
            ctx.debug("Sending facts to the server")
            set_fact_response = await self.client.set_parameters(tid=self.environment, parameters=ctx.facts)
            if set_fact_response.code != 200:
                ctx.error("Failed to send facts to the server %s", set_fact_response.result)

        return DeployReport.from_ctx(resource_details.rvid, ctx)

    async def dry_run(
        self,
        resource: ResourceDetails,
        dry_run_id: uuid.UUID,
    ) -> DryrunReport:
        """
        Perform a dryrun for the given resources

        :param resource: Resource for which to perform a dryrun.
        :param dry_run_id: id for this dryrun
        """
        async with self.activity_lock:
            with self._cache:
                started = datetime.datetime.now().astimezone()
                try:
                    resource_obj: Resource = Resource.deserialize(resource.attributes)
                except Exception as e:
                    msg = self._log_deserialization_error(resource, e)
                    return DryrunReport(
                        rvid=resource.rvid,
                        dryrun_id=dry_run_id,
                        changes={"handler": AttributeStateChange(current="FAILED", desired="Resource Deserialization Failed")},
                        started=started,
                        finished=datetime.datetime.now().astimezone(),
                        messages=[msg],
                        resource_state=const.ResourceState.unavailable,
                    )
                assert resource_obj is not None
                ctx = handler.HandlerContext(resource_obj, True, logger=self.resource_action_logger)
                provider = None

                dryrun_result: Optional[DryrunReport] = None
                resource_id: ResourceVersionIdStr = resource.rvid

                try:
                    self.resource_action_logger.debug("Running dryrun for %s", resource_id)

                    try:
                        provider = await self.get_provider(resource_obj)
                    except Exception as e:
                        ctx.exception(
                            "Unable to find a handler for %(resource_id)s (exception: %(exception)s",
                            resource_id=resource_id,
                            exception=str(e),
                        )
                        dryrun_result = DryrunReport(
                            rvid=resource_id,
                            dryrun_id=dry_run_id,
                            changes={"handler": AttributeStateChange(current="FAILED", desired="Unable to find a handler")},
                            started=started,
                            finished=datetime.datetime.now().astimezone(),
                            messages=ctx.logs,
                        )
                    else:
                        try:

                            def resolve_and_dryrun(
                                provider: HandlerAPI[Resource],
                                ctx: handler.HandlerContext,
                                resource: Resource,
                            ) -> None:
                                resource.resolve_all_references(ctx)
                                provider.execute(ctx, resource, True)

                            await asyncio.get_running_loop().run_in_executor(
                                self.thread_pool, resolve_and_dryrun, provider, ctx, resource_obj
                            )

                            changes = ctx.changes
                            if changes is None:
                                changes = {}
                            if ctx.status == const.ResourceState.failed:
                                changes["handler"] = AttributeStateChange(current="FAILED", desired="Handler failed")
                            dryrun_result = DryrunReport(
                                rvid=resource_id,
                                dryrun_id=dry_run_id,
                                changes=changes,
                                started=started,
                                finished=datetime.datetime.now().astimezone(),
                                messages=ctx.logs,
                            )
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
                            dryrun_result = DryrunReport(
                                rvid=resource_id,
                                dryrun_id=dry_run_id,
                                changes=changes,
                                started=started,
                                finished=datetime.datetime.now().astimezone(),
                                messages=ctx.logs,
                            )

                except Exception as e:
                    ctx.exception(
                        "Unable to process resource %(resource_id)s for dryrun (exception: %(exception)s",
                        resource_id=resource.rvid,
                        exception=str(e),
                    )
                    dryrun_result = DryrunReport(
                        rvid=resource_id,
                        dryrun_id=dry_run_id,
                        changes={"handler": AttributeStateChange(current="FAILED", desired="Resource Deserialization Failed")},
                        started=started,
                        finished=datetime.datetime.now().astimezone(),
                        messages=ctx.logs,
                    )
                finally:
                    if provider is not None:
                        provider.close()
                    assert dryrun_result is not None, "Dryrun result cannot be None"
                    return dryrun_result

    async def get_facts(self, resource: ResourceDetails) -> GetFactReport:
        """
        Get facts for a given resource
        :param resource: The resource for which to get facts.
        """
        provider = None
        started = datetime.datetime.now().astimezone()
        try:
            try:
                resource_obj: Resource = Resource.deserialize(resource.attributes)
            except Exception as e:
                msg = self._log_deserialization_error(resource, e)
                return GetFactReport(
                    resource_id=resource.rvid,
                    action_id=None,
                    parameters=[],
                    started=started,
                    finished=datetime.datetime.now().astimezone(),
                    messages=[msg],
                    success=False,
                    error_msg=f"Unable to deserialize resource {resource.id}",
                    resource_state=const.ResourceState.unavailable,
                )
            assert resource_obj is not None
            ctx = handler.HandlerContext(resource_obj, logger=self.resource_action_logger)
            async with self.activity_lock:
                try:
                    with self._cache:
                        provider = await self.get_provider(resource_obj)

                        def resolve_and_getfact(
                            provider: HandlerAPI[Resource],
                            ctx: handler.HandlerContext,
                            resource: Resource,
                        ) -> dict[str, str]:
                            resource.resolve_all_references(ctx)
                            return provider.check_facts(ctx, resource)

                        result = await asyncio.get_running_loop().run_in_executor(
                            self.thread_pool, resolve_and_getfact, provider, ctx, resource_obj
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

                    return GetFactReport(
                        resource_id=resource.rvid,
                        action_id=ctx.action_id,
                        parameters=parameters,
                        started=started,
                        finished=datetime.datetime.now().astimezone(),
                        messages=ctx.logs,
                        success=True,
                    )

                except Exception:
                    error_msg = "Unable to retrieve facts for resource %s" % resource.id
                    self.resource_action_logger.exception(error_msg)
                    return GetFactReport(
                        resource_id=resource.rvid,
                        action_id=ctx.action_id,
                        parameters=[],
                        started=started,
                        finished=datetime.datetime.now().astimezone(),
                        messages=ctx.logs,
                        success=False,
                        error_msg=error_msg,
                    )

        except Exception:
            error_msg = "Unable to find a handler for %s" % resource.id
            self.resource_action_logger.exception(error_msg)
            return GetFactReport(
                resource_id=resource.rvid,
                action_id=None,
                parameters=[],
                started=started,
                finished=datetime.datetime.now().astimezone(),
                messages=[],
                success=False,
                error_msg=error_msg,
            )
        finally:
            if provider is not None:
                provider.close()


class InProcessExecutorManager(executor.ExecutorManager[InProcessExecutor]):
    """
    This is the executor that provides the backward compatible behavior, conforming to the agent in ISO7.
    It is no longer used outside of testing.

    It spawns an InProcessExecutor and makes sure all code is installed and loadable locally.
    """

    def __init__(
        self,
        environment: uuid.UUID,
        client: inmanta.protocol.SessionClient,
        eventloop: asyncio.AbstractEventLoop,
        parent_logger: logging.Logger,
        thread_pool: ThreadPoolExecutor,
        code_dir: str,
        env_dir: str,
        code_loader: bool = True,
    ) -> None:
        self.environment = environment
        self.client = client
        self.eventloop = eventloop
        self.logger = parent_logger
        self.thread_pool = thread_pool

        self.executors: dict[str, InProcessExecutor] = {}
        self._creation_locks: inmanta.util.NamedLock = inmanta.util.NamedLock()

        self._loader: loader.CodeLoader | None = None
        self._env: env.VirtualEnv | None = None
        self._running = False

        if code_loader:
            self._env = env.VirtualEnv(env_dir)
            self._env.use_virtual_env()
            self._loader = loader.CodeLoader(code_dir, clean=True)
            # Lock to ensure only one actual install runs at a time
            self._loader_lock: asyncio.Lock = Lock()
            # Keep track for each resource type of the last loaded version
            self._last_loaded_version: dict[str, executor.ExecutorBlueprint | None] = defaultdict(lambda: None)
            # Per-resource lock to serialize all actions per resource
            self._resource_loader_lock: NamedLock = NamedLock()

    async def stop(self) -> None:
        self._running = False
        for child in self.executors.values():
            await child.stop()

    async def start(self) -> None:
        assert all(e.is_stopped() for e in self.executors.values())
        await self.join(thread_pool_finalizer=[], timeout=const.SHUTDOWN_GRACE_IOLOOP * 0.9)
        self.executors.clear()
        self._running = True

    def get_environment_manager(self) -> None:
        return None

    async def stop_all_executors(self) -> list[InProcessExecutor]:
        raise NotImplementedError("Not used")

    async def stop_for_agent(self, agent_name: str) -> list[InProcessExecutor]:
        if agent_name in self.executors:
            out = self.executors[agent_name]
            del self.executors[agent_name]
            await out.stop()
        return []

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        assert not self._running
        await asyncio.gather(*(child.join() for child in self.executors.values()))

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
            handler code in its venv. Must have at least one element.
        :return: An Executor instance
        """
        if not self._running:
            raise InvalidStateError("This executor manager is not running")
        if not code:
            raise ValueError(f"{self.__class__.__name__}.get_executor() expects at least one resource install specification")
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
        out.failed_modules = await self.ensure_code(code)

        return out

    async def ensure_code(self, code: typing.Collection[executor.ResourceInstallSpec]) -> executor.FailedInmantaModules:
        """Ensure that the code for the given environment and version is loaded"""

        failed_to_load: FailedInmantaModules = defaultdict(dict)

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
                        failed_to_load[resource_install_spec.resource_type][resource_install_spec.resource_type] = Exception(
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
                self.thread_pool,
                self._env.install_for_config,
                inmanta.util.parse_requirements(blueprint.requirements),
                blueprint.pip_config,
            )
            await loop.run_in_executor(self.thread_pool, self._loader.deploy_version, blueprint.sources)
