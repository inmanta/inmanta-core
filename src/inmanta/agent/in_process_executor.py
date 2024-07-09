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
from collections.abc import Sequence
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Optional

import inmanta.agent.cache
import inmanta.protocol
import inmanta.util
from inmanta import const, data
from inmanta.agent import executor, handler
from inmanta.agent.executor import FailedResourcesSet, ResourceDetails
from inmanta.agent.handler import HandlerAPI, SkipResource
from inmanta.agent.io.remote import ChannelClosedException
from inmanta.const import ParameterSource
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.resources import Id, Resource
from inmanta.types import Apireturn

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

        # threads to setup _io ssh connections
        self.provider_thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="ProviderPool_%s" % self.name)
        # threads to work
        self.thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="Pool_%s" % self.name)

        self._cache = inmanta.agent.cache.AgentCache(self)

        self.logger: logging.Logger = parent_logger.getChild(self.name)

        self._stopped = False

        self.failed_resource_types: FailedResourcesSet = set()

    def stop(self) -> None:
        self._stopped = True
        self._cache.close()
        self.provider_thread_pool.shutdown(wait=False)
        self.thread_pool.shutdown(wait=False)

    def join(self, thread_pool_finalizer: list[ThreadPoolExecutor]) -> None:
        """
        Called after stop to ensure complete shutdown

        :param thread_pool_finalizer: all threadpools that should be joined should be added here.
        """
        assert self._stopped
        thread_pool_finalizer.append(self.provider_thread_pool)
        thread_pool_finalizer.append(self.thread_pool)

    def is_stopped(self) -> bool:
        return self._stopped

    async def get_provider(self, resource: Resource) -> HandlerAPI[Any]:
        provider = await asyncio.get_running_loop().run_in_executor(
            self.provider_thread_pool, handler.Commander.get_provider, self._cache, self, resource
        )
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
        except ChannelClosedException as e:
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception(str(e))
            return
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
            except ChannelClosedException as e:
                ctx.set_status(const.ResourceState.failed)
                ctx.exception(str(e))
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

        async with self.cache(model_version):
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

            async with self.cache(model_version):
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
    ) -> None:
        self.environment = environment
        self.client = client
        self.eventloop = eventloop
        self.logger = parent_logger
        self.process = process

        self.executors: dict[str, InProcessExecutor] = {}
        self._creation_locks: inmanta.util.NamedLock = inmanta.util.NamedLock()

    async def stop(self) -> None:
        for child in self.executors.values():
            child.stop()

    async def start(self) -> None:
        pass

    async def stop_for_agent(self, agent_name: str) -> list[InProcessExecutor]:
        if agent_name in self.executors:
            out = self.executors[agent_name]
            del self.executors[agent_name]
            out.stop()
            return [out]
        return []

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        for child in self.executors.values():
            child.join(thread_pool_finalizer)

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
                    self.executors[agent_name] = out
        assert out.uri == agent_uri
        failed_resource_types: FailedResourcesSet = await self.process.ensure_code(code)
        out.failed_resource_types = failed_resource_types

        return out
