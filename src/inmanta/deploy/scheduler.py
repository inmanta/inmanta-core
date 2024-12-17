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

import abc
import asyncio
import json
import logging
import typing
import uuid
from abc import abstractmethod
from collections.abc import Collection, Mapping, Set
from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import UUID

import asyncpg

from inmanta import const, data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import DeployResult, FactResult
from inmanta.data import ConfigurationModel, Environment
from inmanta.data.model import Discrepancy, ResourceIdStr, ResourceType, ResourceVersionIdStr, SchedulerStatusReport
from inmanta.deploy import timers, work
from inmanta.deploy.persistence import StateUpdateManager, ToDbUpdateManager
from inmanta.deploy.state import (
    AgentStatus,
    BlockedStatus,
    ComplianceStatus,
    DeploymentResult,
    ModelState,
    ResourceDetails,
    ResourceState,
)
from inmanta.deploy.tasks import Deploy, DryRun, RefreshFact, Task
from inmanta.deploy.work import TaskPriority
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


class StaleResource(Exception):
    """
    An exception that indicates that a resource is not managed by the orchestrator.
    """

    pass


@dataclass(frozen=True)
class ResourceIntent:
    model_version: int
    details: ResourceDetails
    dependencies: Optional[Mapping[ResourceIdStr, const.ResourceState]]


class TaskManager(StateUpdateManager, abc.ABC):
    """
    Interface for communication with tasks (deploy.task.Task). Offers methods to inspect intent and to report task results.
    """

    environment: uuid.UUID
    client: Client
    code_manager: CodeManager
    executor_manager: executor.ExecutorManager[executor.Executor]

    @abstractmethod
    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        """
        Returns a collection of all resource types that are known to live on a given agent.
        """

    @abstractmethod
    async def get_resource_intent(
        self,
        resource: ResourceIdStr,
    ) -> Optional[ResourceIntent]:
        """
        Returns the current version and the details for the given resource, or None if it is not (anymore) managed by the
        scheduler.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_start(
        self,
        action_id: uuid.UUID,
        resource: ResourceIdStr,
    ) -> Optional[ResourceIntent]:
        """
        Register the start of deployment for the given resource and return its current version details
        along with the last non-deploying state for its dependencies, or None if it is not (anymore)
        managed by the scheduler.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_done(self, attribute_hash: str, result: DeployResult) -> None:
        """
        Register the end of deployment for the given resource: update the resource state based on the deployment result
        and inform its dependencies that deployment is finished.
        Since knowledge of deployment result implies a finished deploy, it must only be set
        when a deploy has just finished.

        Acquires appropriate locks

        :param attribute_hash: The resource's attribute hash for which this state applies. No scheduler state is updated if the
            hash indicates the state information is stale.
        :param result: The DeployResult object describing the result of the deployment.
        """


class TaskRunner:
    def __init__(self, endpoint: str, scheduler: "ResourceScheduler"):
        self.endpoint = endpoint
        self.status = AgentStatus.STOPPED
        self._scheduler = scheduler
        self._task: typing.Optional[asyncio.Task[None]] = None
        self._notify_task: typing.Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        self.status = AgentStatus.STARTED
        assert (
            self._task is None or self._task.done()
        ), f"Task Runner {self.endpoint} is trying to start twice, this should not happen"
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.status = AgentStatus.STOPPING

    async def join(self) -> None:
        assert not self.is_running(), "Joining worker that is not stopped"
        if self._task is None or self._task.done():
            return
        await self._task

    async def notify(self) -> None:
        """
        Method to notify the runner that something has changed in the DB. This method will fetch the new information
        regarding the environment and the information related to the runner (agent). Depending on the desired state of the
        agent, it will either stop / start the agent or do nothing
        """
        should_be_running = await self._scheduler.should_be_running() and await self._scheduler.should_runner_be_running(
            endpoint=self.endpoint
        )

        match self.status:
            case AgentStatus.STARTED if not should_be_running:
                await self.stop()
            case AgentStatus.STOPPED if should_be_running:
                await self.start()
            case AgentStatus.STOPPING if should_be_running:
                self.status = AgentStatus.STARTED

    def notify_sync(self) -> None:
        """
        Method to notify the runner that something has changed in the DB in a synchronous manner.
        """
        # We save it to be sure that the task will not be GC
        self._notify_task = asyncio.create_task(self.notify())

    async def _run(self) -> None:
        """Main loop for one agent. It will first fetch or create its actual state from the DB to make sure that it's
        allowed to run."""
        while self._scheduler._running and self.status == AgentStatus.STARTED:
            work_item: work.MotivatedTask[Task] = await self._scheduler._work.agent_queues.queue_get(self.endpoint)
            try:
                await work_item.task.execute(self._scheduler, self.endpoint, work_item.reason)
            except Exception:
                LOGGER.exception(
                    "Task %s for agent %s has failed and the exception was not properly handled", work_item.task, self.endpoint
                )

            self._scheduler._work.agent_queues.task_done(self.endpoint, work_item.task)

        self.status = AgentStatus.STOPPED

    def is_running(self) -> bool:
        return self.status == AgentStatus.STARTED


class ResourceScheduler(TaskManager):
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.

    The scheduler expects to be notified by the server whenever a new version is released.
    """

    def __init__(
        self, environment: uuid.UUID, executor_manager: executor.ExecutorManager[executor.Executor], client: Client
    ) -> None:
        """
        :param environment: the environment we work for
        :param executor_manager: the executor manager that will provide us with executors
        :param client: connection to the server
        """
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(
            requires=self._state.requires.requires_view(),
            provides=self._state.requires.provides_view(),
            new_agent_notify=self._create_agent,
        )

        # We uphold two locks to prevent concurrency conflicts between external events (e.g. new version or deploy request)
        # and the task executor background tasks.
        #
        # - lock to block scheduler state access (this includes model state, scheduled work and resource timers management)
        #   during scheduler-wide state updates (e.g. trigger deploy). A single lock suffices since all state accesses
        #   (both read and write) by the task runners are short, synchronous operations (and therefore we wouldn't gain
        #   anything by allowing multiple readers).
        self._scheduler_lock: asyncio.Lock = asyncio.Lock()
        # - lock to serialize updates to the scheduler's intent (version, attributes, ...), e.g. process a new version.
        self._intent_lock: asyncio.Lock = asyncio.Lock()

        self._running = False
        # Agent name to worker task
        # here to prevent it from being GC-ed
        self._workers: dict[str, TaskRunner] = {}
        # Set of resources for which a concrete non-stale deploy is in progress, i.e. we've committed for a given intent and
        # that intent still reflects the latest resource intent
        # Apart from the obvious, this differs from the agent queues' in-progress deploys in the sense that those are simply
        # tasks that have been picked up while this set contains only those tasks for which we've already committed. For each
        # deploy task, there is a (typically) short window of time where it's considered in progress by the agent queue, but
        # it has not yet started on the actual deploy, i.e. it will still see updates to the resource intent.
        self._deploying_latest: set[ResourceIdStr] = set()

        self.environment = environment
        self.client = client
        self.code_manager = CodeManager(client)
        self.executor_manager = executor_manager
        self._state_update_delegate = ToDbUpdateManager(client, environment)

        self._timer_manager = timers.TimerManager(self)

    async def _reset(self) -> None:
        """
        Clear out all state and start empty

        only allowed when ResourceScheduler is not running
        """
        assert not self._running
        self._state.reset()
        self._work.reset()
        # Ensure we are down
        for worker in self._workers.values():
            # We have no timeout here
            # This can potentially hang when an executor hangs
            # However, the stop should forcefully kill the executor
            # This will kill the connection and free the worker
            await worker.join()
        self._workers.clear()
        self._deploying_latest.clear()
        await self._timer_manager.reset()

    async def start(self) -> None:
        if self._running:
            return
        await self._reset()
        await self.reset_resource_state()

        await self._initialize()
        self._running = True

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        await self._timer_manager.stop()
        # Ensure workers go down
        # First stop them
        for worker in self._workers.values():
            await worker.stop()
        # Then wake them up to receive the stop
        self._work.agent_queues.send_shutdown()

    async def join(self) -> None:
        await asyncio.gather(*[worker.join() for worker in self._workers.values()])
        await self._timer_manager.join()

    async def _initialize(self) -> None:
        """
        Initialize the scheduler state and continue the deployment where we were before the server was shutdown.
        """
        self._timer_manager.initialize()
        async with self._intent_lock, self._scheduler_lock, data.Scheduler.get_connection() as con, con.transaction():
            # Make sure there is an entry for this scheduler in the scheduler database table
            await data.Scheduler._execute_query(
                f"""
                    INSERT INTO {data.Scheduler.table_name()}
                    VALUES($1, NULL)
                    ON CONFLICT DO NOTHING
                """,
                self.environment,
                connection=con,
            )

            # Retrieve latest released model version
            latest_release_model: Optional[data.ConfigurationModel] = await data.ConfigurationModel.get_latest_version(
                environment=self.environment, connection=con
            )
            if latest_release_model is None:
                # No model version has been released yet. No scheduler state to restore from db.
                return

            # Check at which model version the scheduler was before it went down
            scheduler: Optional[data.Scheduler] = await data.Scheduler.get_one(environment=self.environment, connection=con)
            assert scheduler is not None
            last_processed_model_version = scheduler.last_processed_model_version
            if last_processed_model_version is not None:
                # Restore scheduler state like it was before the scheduler went down
                self._state = await ModelState.create_from_db(self.environment, last_processed_model_version, connection=con)
                self._work.link_to_new_requires_provides_view(
                    requires_view=self._state.requires.requires_view(),
                    provides_view=self._state.requires.provides_view(),
                )
            else:
                # This case can occur in two different situations:
                #   * A model version has been released, but the scheduler didn't process any version yet.
                #     In this case there is no scheduler state to restore.
                #   * We migrated the Inmanta server from an old version, that didn't have the resource state
                #     tracking in the database, to a version that does. To cover this case, we rely on the
                #     increment calculation to determine which resources have to be considered dirty and which
                #     not. This migration code path can be removed in a later major version.
                await self._recover_scheduler_state_using_increments_calculation(connection=con)

            if last_processed_model_version is not None and last_processed_model_version < latest_release_model.version:
                # We restored the scheduler state from the database, but a newer, released version is available.
                # Apply the changes from each subsequent model version to the scheduler.
                versions = await data.ConfigurationModel.get_released_versions_in_interval(
                    environment=self.environment,
                    lower_bound=last_processed_model_version + 1,
                    upper_bound=latest_release_model.version,
                    connection=con,
                )
                for version in reversed(versions):
                    # Apply version from old to new
                    await self._read_version(
                        version=version,
                        start_deployment=False,
                        intent_lock_acquired=True,
                        scheduler_lock_acquired=True,
                        connection=con,
                    )
            # Start deploying everything in dirty set.
            self._work.deploy_with_context(
                self._state.dirty,
                reason="Deploy was triggered because the scheduler was started",
                priority=TaskPriority.NEW_VERSION_DEPLOY,
            )

    async def _recover_scheduler_state_using_increments_calculation(self, *, connection: asyncpg.connection.Connection) -> None:
        """
        This method exists for backwards compatibility reasons. It initializes the scheduler state
        by relying on the increments calculation logic. This method starts the deployment process.
        """
        try:
            version, resources, requires, undefined_resources = await self._get_resources_in_version(connection=connection)
        except KeyError:
            # No model version has been released yet.
            return
        # Rely on the incremental calculation to determine which resources should be deployed and which not.
        up_to_date_resources: set[ResourceIdStr]
        _, up_to_date_resources = await ConfigurationModel.get_increment(self.environment, version, connection=connection)
        await self._new_version(
            version,
            resources=resources,
            requires=requires,
            up_to_date_resources=up_to_date_resources,
            reason="Deploy was triggered because the scheduler was started",
            start_deployment=False,
            intent_lock_acquired=True,
            scheduler_lock_acquired=True,
            undefined_resources=undefined_resources,
            connection=connection,
        )

    async def deploy(self, *, reason: str, priority: TaskPriority = TaskPriority.USER_DEPLOY) -> None:
        """
        Trigger a deploy
        """
        if not self._running:
            return
        async with self._scheduler_lock:
            self._timer_manager.stop_timers(self._state.dirty)
            self._work.deploy_with_context(
                self._state.dirty, reason=reason, priority=priority, deploying=self._deploying_latest
            )

    async def repair(self, *, reason: str, priority: TaskPriority = TaskPriority.USER_REPAIR) -> None:
        """
        Trigger a repair, i.e. mark all unblocked resources as dirty, then trigger a deploy.
        """

        def _should_deploy(resource: ResourceIdStr) -> bool:
            if (resource_state := self._state.resource_state.get(resource)) is not None:
                return resource_state.blocked is BlockedStatus.NO
            # No state was found for this resource. Should probably not happen
            # but err on the side of caution and mark for redeploy.
            return True

        if not self._running:
            return
        async with self._scheduler_lock:
            self._state.dirty.update(resource for resource in self._state.resources.keys() if _should_deploy(resource))
            self._timer_manager.stop_timers(self._state.dirty)
            self._work.deploy_with_context(
                self._state.dirty, reason=reason, priority=priority, deploying=self._deploying_latest
            )

    async def _get_resource_details_of_defined_resources(self, env: uuid.UUID, version: int) -> list[ResourceDetails]:
        """
        This method is only used by the dryrun() method. It exists so that it can be mocked by the test suite.
        """
        resources_in_version = await data.Resource.get_list(environment=env, model=version)
        result = []
        for res in resources_in_version:
            if res.status is not const.ResourceState.undefined:
                # Make mypy happy
                assert res.attribute_hash is not None
                result.append(
                    ResourceDetails(
                        resource_id=res.resource_id,
                        attribute_hash=res.attribute_hash,
                        attributes=res.attributes,
                    )
                )
        return result

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        if not self._running:
            return
        resource_details = await self._get_resource_details_of_defined_resources(env=self.environment, version=version)
        for details in resource_details:
            self._work.agent_queues.queue_put_nowait(
                DryRun(
                    resource=details.resource_id,
                    version=version,
                    resource_details=ResourceDetails(
                        resource_id=details.resource_id,
                        attribute_hash=details.attribute_hash,
                        attributes=details.attributes,
                    ),
                    dry_run_id=dry_run_id,
                ),
                priority=TaskPriority.DRYRUN,
            )

    async def get_facts(self, resource: dict[str, object]) -> None:
        if not self._running:
            return
        rid = Id.parse_id(resource["id"]).resource_str()
        self._work.agent_queues.queue_put_nowait(
            RefreshFact(resource=rid),
            priority=TaskPriority.FACT_REFRESH,
        )

    async def get_resource_state(self) -> SchedulerStatusReport:
        """
        Check that the state of the resources in the DB corresponds
        to the internal state of the scheduler and return a SchedulerStatusReport
        object containing the internal state and any discrepancies between this
        state and that of the DB.
        """

        resources_in_db: Mapping[ResourceIdStr, ResourceDetails]

        async def _build_discrepancy_map(
            resource_states_in_db: Mapping[ResourceIdStr, const.ResourceState],
        ) -> dict[ResourceIdStr, list[Discrepancy]]:
            """
            For each resource in the given map, compare its persisted state in the database to its
            state as it is assumed by the scheduler. Build and return a map of all detected discrepancies.

            :param resource_states_in_db: Map each resource to its ResourceState.
            :return: A dict mapping each resource to the discrepancies related to it (if any)
            """
            state_translation_table: dict[
                const.ResourceState, Tuple[DeploymentResult | None, BlockedStatus | None, ComplianceStatus | None]
            ] = {
                # A table to translate the old states into the new states
                # None means don't care, mostly used for values we can't derive from the old state
                const.ResourceState.unavailable: (None, BlockedStatus.NO, ComplianceStatus.NON_COMPLIANT),
                const.ResourceState.skipped: (DeploymentResult.SKIPPED, None, None),
                const.ResourceState.dry: (None, None, None),  # don't care
                const.ResourceState.deployed: (DeploymentResult.DEPLOYED, BlockedStatus.NO, None),
                const.ResourceState.failed: (DeploymentResult.FAILED, BlockedStatus.NO, None),
                const.ResourceState.deploying: (None, BlockedStatus.NO, None),
                const.ResourceState.available: (None, BlockedStatus.NO, ComplianceStatus.HAS_UPDATE),
                const.ResourceState.undefined: (None, BlockedStatus.YES, ComplianceStatus.UNDEFINED),
                const.ResourceState.skipped_for_undefined: (None, BlockedStatus.YES, None),
            }

            discrepancy_map: dict[ResourceIdStr, list[Discrepancy]] = {}

            # Resources only present in the DB but missing from the scheduler
            only_in_db = resource_states_in_db.keys() - self._state.resource_state.keys()
            for rid in only_in_db:
                discrepancy_map[rid] = [
                    Discrepancy(
                        rid=rid,
                        field=None,
                        expected=(
                            f"Resource is present in the DB (model version {latest_version}). "
                            "It is expected in the scheduler's resource_state map."
                        ),
                        actual="Resource is missing from the scheduler's resource_state map.",
                    )
                ]

            # Resources only present in the scheduler but missing from the DB
            only_in_scheduler = self._state.resource_state.keys() - resource_states_in_db.keys()
            for rid in only_in_scheduler:
                discrepancy_map[rid] = [
                    Discrepancy(
                        rid=rid,
                        field=None,
                        expected=(
                            f"Resource is not present in the DB (model version {latest_version}). "
                            "It shouldn't be in the scheduler's resource_state map."
                        ),
                        actual="Resource is present in the scheduler's resource_state map.",
                    )
                ]

            # Keep track of the number of iterations to regularly pass control back to the io loop
            iteration_counter: int = 0

            # For resources in both the DB and the scheduler, check for discrepancies in state
            for rid in resources_in_db.keys() & self._state.resource_state.keys():
                resource_discrepancies: list[Discrepancy] = []

                db_resource_status = resource_states_in_db[rid]
                db_deploy_result, db_blocked_status, db_compliance_status = state_translation_table[db_resource_status]

                scheduler_resource_state: ResourceState = self._state.resource_state[rid]
                if db_deploy_result:
                    if scheduler_resource_state.deployment_result != db_deploy_result:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="deployment_result",
                                expected=db_deploy_result,
                                actual=scheduler_resource_state.deployment_result,
                            )
                        )
                if db_blocked_status:
                    if scheduler_resource_state.blocked != db_blocked_status:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="blocked_status",
                                expected=db_blocked_status,
                                actual=scheduler_resource_state.blocked,
                            )
                        )
                if db_compliance_status:
                    if scheduler_resource_state.status != db_compliance_status:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="compliance_status",
                                expected=db_compliance_status,
                                actual=scheduler_resource_state.status,
                            )
                        )

                if resource_discrepancies:
                    discrepancy_map[rid] = resource_discrepancies

                iteration_counter += 1

                # Pass back control to the io loop every 1000 iterations to not
                # block scheduler operations in case we have a lot of resources.
                if iteration_counter == 1000:
                    await asyncio.sleep(0)
                    iteration_counter = 0

            return discrepancy_map

        def report_model_version_mismatch(db_version: int | None) -> SchedulerStatusReport:
            LOGGER.info(
                "Cannot compare scheduler status and database status because of "
                "model version mismatch (%s and %s respectively). "
                "The scheduler might not have processed this new version yet.",
                self._state.version,
                db_version,
            )
            return SchedulerStatusReport(
                scheduler_state={},
                db_state={},
                resource_states={},
                discrepancies=[
                    Discrepancy(
                        rid=None,
                        field="model_version",
                        expected=str(db_version),
                        actual=str(self._state.version),
                    )
                ],
            )

        latest_version: int | None
        async with self._scheduler_lock:
            async with data.Scheduler.get_connection() as connection:
                try:
                    latest_version, resources_in_db, _, _ = await self._get_resources_in_version(connection=connection)
                except KeyError:
                    return SchedulerStatusReport(scheduler_state={}, db_state={}, resource_states={}, discrepancies={})
                if latest_version != self._state.version:
                    return report_model_version_mismatch(latest_version)

                resource_states_in_db: Mapping[ResourceIdStr, const.ResourceState]
                latest_version, resource_states_in_db = await data.Resource.get_resource_states_latest_version(
                    env=self.environment, connection=connection
                )
                if latest_version != self._state.version:
                    return report_model_version_mismatch(latest_version)

            discrepancy_map = await _build_discrepancy_map(resource_states_in_db=resource_states_in_db)
            return SchedulerStatusReport(
                scheduler_state=self._state.resource_state,
                db_state=resources_in_db,
                resource_states=resource_states_in_db,
                discrepancies=discrepancy_map,
            )

    async def deploy_resource(self, resource: ResourceIdStr, reason: str, priority: TaskPriority) -> None:
        """
        Make sure the given resource is marked for deployment with at least the provided priority.
        If the given priority is higher than the previous one (or if it didn't exist before), a new deploy
        task will be scheduled with the provided reason.
        """
        async with self._scheduler_lock:
            if resource not in self._state.resource_state:
                # The resource was removed from the model by the time this method was triggered
                return

            if self._state.resource_state[resource].blocked is BlockedStatus.YES:  # Can't deploy
                return
            self._timer_manager.stop_timer(resource)
            self._work.deploy_with_context(
                {resource},
                reason=reason,
                priority=priority,
                deploying=self._deploying_latest,
            )

    async def _build_resource_mappings_from_db(
        self, version: int, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Tuple[Mapping[ResourceIdStr, ResourceDetails], Set[ResourceIdStr]]:
        """
        Build a view on current resources. Might be filtered for a specific environment, used when a new version is released

        :return: resource_mapping {id -> resource details}
        """
        resources_from_db = await data.Resource.get_resources_for_version_raw_with_persistent_state(
            environment=self.environment,
            version=version,
            projection=[
                "resource_id",
                "status",
                "attributes",
                "attribute_hash",
            ],
            projection_persistent=["deployment_result", "last_deployed_attribute_hash"],
            connection=connection,
        )
        undefined_resources: Set[ResourceIdStr] = {
            r["resource_id"] for r in resources_from_db if const.ResourceState[r["status"]] is const.ResourceState.undefined
        }
        resource_details = {
            resource["resource_id"]: ResourceDetails(
                resource_id=resource["resource_id"],
                attribute_hash=resource["attribute_hash"],
                attributes=json.loads(resource["attributes"]),
            )
            for resource in resources_from_db
        }
        return resource_details, undefined_resources

    def _construct_requires_mapping(
        self, resources: Mapping[ResourceIdStr, ResourceDetails]
    ) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        require_mapping = {
            resource: {Id.parse_id(req).resource_str() for req in details.attributes.get("requires", [])}
            for resource, details in resources.items()
        }
        return require_mapping

    async def _get_resources_in_version(
        self,
        *,
        version: int | None = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> tuple[int, Mapping[ResourceIdStr, ResourceDetails], Mapping[ResourceIdStr, Set[ResourceIdStr]], Set[ResourceIdStr]]:
        """
        Returns a tuple containing:
            1. The version number of the configuration model.
            2. A dict mapping every resource_id in the latest released version to its ResourceDetails.
            3. A dict mapping every resource_id in the latest released version to the set of resources it requires.
        """
        async with ConfigurationModel.get_connection(connection) as con:
            if version is None:
                # Fetch the latest released model version
                cm_version = await ConfigurationModel.get_latest_version(self.environment, connection=con)
                if cm_version is None:
                    raise KeyError()
                version = cm_version.version
            resource_details, undefined_resources = await self._build_resource_mappings_from_db(version=version, connection=con)
            requires = self._construct_requires_mapping(resource_details)
            return version, resource_details, requires, undefined_resources

    async def read_version(
        self,
    ) -> None:
        """
        Update model state and scheduled work based on the latest released version in the database,
        e.g. when a new version is released. Triggers a deploy after updating internal state:
        - schedules new or updated resources to be deployed
        - schedules any resources that are not in a known good state.
        - rearranges deploy tasks by requires if required
        """
        if not self._running:
            return
        await self._read_version()

    async def _read_version(
        self,
        *,
        version: int | None = None,
        start_deployment: bool = True,
        intent_lock_acquired: bool = False,
        scheduler_lock_acquired: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        try:
            version, resources, requires, undefined_resources = await self._get_resources_in_version(
                version=version, connection=connection
            )
        except KeyError:
            # No model version has been released yet.
            return
        else:
            await self._new_version(
                version,
                resources,
                requires,
                reason="Deploy was triggered because a new version has been released",
                intent_lock_acquired=intent_lock_acquired,
                scheduler_lock_acquired=scheduler_lock_acquired,
                start_deployment=start_deployment,
                connection=connection,
            )

    async def reset_resource_state(self) -> None:
        """
        Update resources on the latest released version of the model stuck in "deploying" state.
        This can occur when the Scheduler is killed in the middle of a deployment.
        """

        await data.Resource.reset_resource_state(self.environment)

    # FIXME[#8358]: move intent lock one level up in order to prevent out-of-order versions
    async def _new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        up_to_date_resources: Optional[Set[ResourceIdStr]] = None,
        reason: str = "Deploy was triggered because a new version has been released",
        start_deployment: bool = True,
        intent_lock_acquired: bool = False,
        scheduler_lock_acquired: bool = False,
        undefined_resources: Optional[Set[ResourceIdStr]] = None,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Register a newly released version with the scheduler. Updates scheduled state and scheduled work accordingly.

        Expects to be called under the intent lock, and with monotonically increasing versions.

        :param version: The model version that is being registered.
        :param resources: All resources in this version.
        :param requires: The requires set of each resource in this version.
        :param up_to_date_resources: Set of resources that are to be considered in an assumed good state due to a previously
            successful deploy for the same intent. Should not include any blocked resources. Mostly intended for the very first
            version when the scheduler is started with a fresh state.
        :param reason: The reason to associate with any deploys caused by this newly released version.
        :param intent_lock_acquired: True iff the self._intent_lock was already acquired before entering this method.
        :param scheduler_lock_acquired: True iff the self._scheduler_lock was already acquired before entering this method.
        """
        intent_lock = self._intent_lock if not intent_lock_acquired else asyncio.Lock()
        scheduler_lock = self._scheduler_lock if not scheduler_lock_acquired else asyncio.Lock()
        up_to_date_resources = set() if up_to_date_resources is None else up_to_date_resources
        undefined_resources = set() if undefined_resources is None else undefined_resources
        async with data.Scheduler.get_connection(connection=connection) as con, con.transaction(), intent_lock:
            if version < self._state.version:
                raise ValueError(
                    f"Invalid scheduler state: received out-of-order versions. Currently at version {self._state.version} but"
                    " received version {version}"
                )
            if version == self._state.version:
                return

            # Inspect new state and compare it with the old one before acquiring the scheduler lock.
            # This is safe because we only read intent-related state here, for which we've already acquired the lock
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            # Resources with known deployable changes (new resources or old resources with deployable changes)
            new_desired_state: set[ResourceIdStr] = set()
            # Only contains the direct undeployable resources, not the transitive ones.
            undefined: set[ResourceIdStr] = set()
            # Resources that were undeployable in a previous model version, but got unblocked. Not the transitive ones.
            now_defined: set[ResourceIdStr] = set()  # resources that were previously undefined but not anymore

            # Track potential changes in requires per resource
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}

            for resource, details in resources.items():
                if resource in up_to_date_resources:
                    self._state.add_up_to_date_resource(resource, details)  # Removes from the dirty set
                    continue
                if resource in undefined_resources:
                    undefined.add(resource)
                    self._work.delete_resource(resource)
                elif resource in self._state.resources:
                    # It's a resource we know.
                    if self._state.resource_state[resource].status is ComplianceStatus.UNDEFINED:
                        # The resource has been undeployable in previous versions, but not anymore.
                        now_defined.add(resource)
                        if details.attribute_hash == self._state.resources[resource].attribute_hash:
                            LOGGER.warning("The resource with id %s has become defined, but the hash has not changed", resource)
                    if details.attribute_hash != self._state.resources[resource].attribute_hash:
                        # The desired state has changed.
                        new_desired_state.add(resource)
                else:
                    new_desired_state.add(resource)

                old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
                new_requires: Set[ResourceIdStr] = requires.get(resource, set())
                added = new_requires - old_requires
                if added:
                    added_requires[resource] = added
                removed = old_requires - new_requires
                if removed:
                    dropped_requires[resource] = removed

                # this loop is race-free, potentially slow, and completely synchronous
                # => regularly pass control to the event loop to not block scheduler operation during update prep
                await asyncio.sleep(0)

            # A resource should not be present in more than one of these resource sets
            assert len(new_desired_state | undefined) == (len(new_desired_state) + len(undefined))

            # in the current implementation everything below the lock is synchronous, so it's not technically required.
            # It is however kept for two reasons:
            # 1. pass context once more to event loop before starting on the sync path
            #    (could be achieved with a simple sleep(0) if desired)
            # 2. clarity: it clearly signifies that this is the atomic and performance-sensitive part
            async with scheduler_lock:
                self._state.version = version
                for resource in undefined:
                    self._state.update_resource_to_undefined(resource, resources[resource])  # Removes from the dirty set
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources[resource])  # Updates the dirty set
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])

                transitive_unblocked, transitive_blocked = self._state.update_transitive_state(
                    new_undefined=undefined,
                    verify_blocked=added_requires.keys(),
                    verify_unblocked=now_defined | dropped_requires.keys(),
                )

                # Update set of in-progress non-stale deploys by trimming resources with new state
                self._deploying_latest.difference_update(new_desired_state, deleted_resources, undefined, transitive_blocked)

                # Remove timers for resources that are:
                #    - in the dirty set (because they will be picked up by the scheduler eventually)
                #    - blocked: must not be deployed
                #    - deleted from the model
                self._timer_manager.stop_timers(self._state.dirty | undefined | transitive_blocked)
                self._timer_manager.remove_timers(deleted_resources)
                # Install timers for initial up-to-date resources. They are up-to-date now,
                # but we want to make sure we periodically repair them.
                self._timer_manager.update_timers(
                    up_to_date_resources | (transitive_unblocked - self._state.dirty), are_compliant=True
                )

                # ensure deploy for ALL dirty resources, not just the new ones
                if start_deployment:
                    self._work.deploy_with_context(
                        self._state.dirty,
                        reason=reason,
                        priority=TaskPriority.NEW_VERSION_DEPLOY,
                        deploying=self._deploying_latest,
                        added_requires=added_requires,
                        dropped_requires=dropped_requires,
                    )
                for resource in deleted_resources:
                    self._state.drop(resource)  # Removes from the dirty set
                for resource in undefined | transitive_blocked:
                    self._work.delete_resource(resource)

                # Updating the blocked state should be done under the scheduler lock, because this state is written
                # by both the deploy and the new version code path.
                resources_with_updated_blocked_state: Set[ResourceIdStr] = undefined | transitive_blocked | transitive_unblocked

                await self.update_resource_intent(
                    self.environment,
                    intent={
                        rid: (self._state.resource_state[rid], self._state.resources[rid])
                        for rid in resources_with_updated_blocked_state
                    },
                    update_blocked_state=True,
                    connection=con,
                )

            # Once more, drop all resources that do not exist in this version from the scheduled work,
            # in case they got added again by a deploy trigger (because we dropped them outside the lock).
            for resource in deleted_resources:
                # Delete the deleted resources outside the _scheduler_lock, because we do not want to keep
                # the _scheduler_lock acquired longer than required. The worst that can happen here is that
                # we deploy the deleted resources one time too many, which is not so bad.
                self._work.delete_resource(resource)

            # Update intent for resources with new desired state
            await self.update_resource_intent(
                self.environment,
                intent={rid: (self._state.resource_state[rid], self._state.resources[rid]) for rid in new_desired_state},
                update_blocked_state=False,
                connection=con,
            )
            # Mark orphaned resources
            await self.mark_as_orphan(self.environment, deleted_resources, con)
            await self.set_last_processed_model_version(self.environment, version, connection=con)

    def _create_agent(self, agent: str) -> None:
        """Start processing for the given agent"""
        self._workers[agent] = TaskRunner(endpoint=agent, scheduler=self)
        self._workers[agent].notify_sync()

    async def should_be_running(self) -> bool:
        """
        Check in the DB (authoritative entity) if the Scheduler should be running
            i.e. if the environment is not halted.
        """
        current_environment = await Environment.get_by_id(self.environment)
        assert current_environment
        return not current_environment.halted

    async def should_runner_be_running(self, endpoint: str) -> bool:
        """
        Check in the DB (authoritative entity) if the agent (or the Scheduler if endpoint == Scheduler id) should be running
            i.e. if it is not paused.

        :param endpoint: The name of the agent
        """
        await data.Agent.insert_if_not_exist(environment=self.environment, endpoint=endpoint)
        current_agent = await data.Agent.get(env=self.environment, endpoint=endpoint)
        return not current_agent.paused

    async def refresh_agent_state_from_db(self, name: str) -> None:
        """
        Refresh from the DB (authoritative entity) the actual state of the agent.
            - If the agent is not paused: It will make sure that the agent is running.
            - If the agent is paused: Stop a particular agent.

        :param name: The name of the agent
        """
        if name in self._workers:
            await self._workers[name].notify()

    async def refresh_all_agent_states_from_db(self) -> None:
        """
        Refresh from the DB (authoritative entity) the actual state of all agents.
            - If an agent is not paused: It will make sure that the agent is running.
            - If an agent is paused: Stop a particular agent.
        """
        for worker in self._workers.values():
            await worker.notify()

    async def is_agent_running(self, name: str) -> bool:
        """
        Return True if the provided agent is running, at least an agent that the Scheduler is aware of

        :param name: The name of the agent
        """
        return name in self._workers and self._workers[name].is_running()

    # TaskManager interface

    def _get_resource_intent(self, resource: ResourceIdStr) -> Optional[ResourceDetails]:
        """
        Get intent of a given resource.
        Always expected to be called under lock
        """
        try:
            return self._state.resources[resource]
        except KeyError:
            # Stale resource
            # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
            # because of this check, and an intrinsic part of the locking design because it's preferred over wider
            # locking for performance reasons.
            return None

    async def get_resource_intent(self, resource: ResourceIdStr) -> Optional[ResourceIntent]:
        async with self._scheduler_lock:
            # fetch resource details under lock
            resource_details = self._get_resource_intent(resource)
            if resource_details is None:
                return None
            return ResourceIntent(model_version=self._state.version, details=resource_details, dependencies=None)

    async def deploy_start(self, action_id: uuid.UUID, resource: ResourceIdStr) -> Optional[ResourceIntent]:
        async with self._scheduler_lock:
            # fetch resource details under lock
            resource_details = self._get_resource_intent(resource)
            if resource_details is None or self._state.resource_state[resource].blocked is BlockedStatus.YES:
                # We are trying to deploy a stale resource.
                return None
            dependencies = await self._get_last_non_deploying_state_for_dependencies(resource=resource)
            self._deploying_latest.add(resource)
            resource_intent = ResourceIntent(
                model_version=self._state.version, details=resource_details, dependencies=dependencies
            )
            # Update the state in the database.
            await self.send_in_progress(action_id, Id.parse_id(ResourceVersionIdStr(f"{resource},v={self._state.version}")))
            return resource_intent

    async def deploy_done(self, attribute_hash: str, result: DeployResult) -> None:
        deployment_result: DeploymentResult = DeploymentResult.from_handler_resource_state(result.resource_state)
        try:
            state = await self.update_scheduler_state_for_finished_deploy(attribute_hash, result, deployment_result)
        except StaleResource:
            # The resource is no longer managed, no need to update the database state.
            pass
        else:
            # Write deployment result to the database.
            await self.send_deploy_done(attribute_hash, result, state)

    async def update_scheduler_state_for_finished_deploy(
        self, attribute_hash: str, result: DeployResult, deployment_result: DeploymentResult
    ) -> ResourceState | None:
        """
        Update the state of the scheduler based on the DeploymentResult of the given resource.

        :raise StaleResource: This update is about a resource that is no longer managed by the server.
        :return: The new blocked status of the resource. Or None if the blocked status shouldn't be updated.
        """
        resource_id: ResourceIdStr = result.resource_id
        if deployment_result is DeploymentResult.NEW:
            raise ValueError("update_scheduler_state_for_finished_deploy should not be called to register new resources")

        async with self._scheduler_lock:
            # refresh resource details for latest model state
            details: Optional[ResourceDetails] = self._state.resources.get(resource_id, None)

            if details is None:
                # we are stale and removed
                raise StaleResource()

            state: ResourceState = self._state.resource_state[resource_id]

            recovered_from_failure: bool = deployment_result is DeploymentResult.DEPLOYED and state.deployment_result not in (
                DeploymentResult.DEPLOYED,
                DeploymentResult.NEW,
            )

            if details.attribute_hash != attribute_hash:
                # We are stale but still the last deploy
                # We can update the deployment_result (which is about last deploy)
                # We can't update status (which is about active state only)
                # None of the event propagation or other update happen either for the same reason
                # except for the event to notify dependents of failure recovery (to unblock skipped for dependencies)
                # because we might otherwise miss the recovery.
                state.deployment_result = deployment_result
                if recovered_from_failure:
                    self._send_events(details, stale_deploy=True, recovered_from_failure=True)
                return None

            # We are not stale
            state.status = (
                ComplianceStatus.COMPLIANT if result.status is const.ResourceState.deployed else ComplianceStatus.NON_COMPLIANT
            )

            # first update state, then send out events
            self._deploying_latest.remove(resource_id)
            state.deployment_result = deployment_result
            self._work.finished_deploy(resource_id)

            # Check if we need to mark a resource as transiently blocked
            # We only do that if it is not already blocked (BlockedStatus.YES)
            # We might already be unblocked if a dependency succeeded on another agent, e.g. while waiting for the lock
            # so HandlerResourceState.skipped_for_dependency might be outdated, we have an inconsistency between the
            # state of the dependencies and the exception that was raised by the handler.
            # If all dependencies are compliant we don't want to transiently block this resource.
            if (
                state.blocked is not BlockedStatus.YES
                and result.resource_state is const.HandlerResourceState.skipped_for_dependency
                and not self._state.are_dependencies_compliant(resource_id)
            ):
                state.blocked = BlockedStatus.TRANSIENT
                # Remove this resource from the dirty set when we block it
                self._state.dirty.discard(resource_id)
            elif deployment_result is DeploymentResult.DEPLOYED:
                # Remove this resource from the dirty set if it is successfully deployed
                self._state.dirty.discard(resource_id)
            else:
                # In most cases it will already be marked as dirty but in rare cases the deploy that just finished might
                # have been triggered by an event, on a previously successful deployed resource. Either way, a failure
                # (or skip) causes it to become dirty now.
                self._state.dirty.add(resource_id)

            # propagate events
            self._send_events(details, recovered_from_failure=recovered_from_failure)

            # No matter the deployment result, schedule a re-deploy for this resource unless it's blocked
            if state.blocked is BlockedStatus.NO:
                self._timer_manager.update_timer(resource_id, is_compliant=(state.status is ComplianceStatus.COMPLIANT))

            return state

    def _send_events(
        self,
        sending_resource: ResourceDetails,
        *,
        stale_deploy: bool = False,
        recovered_from_failure: bool,
    ) -> None:
        """
        Send events to the appropriate dependents of the given resources. Sends out normal events to declared event listeners
        unless this was triggered by a stale deploy. Additionally, if this was triggered by a failure recovery, it unblocks
        skipped dependents where appropriate and sends them an event to deploy.

        Expects to be called under the scheduler lock.

        :param sending_resource: Details for the given resource that has just finished deploying.
        :param state_deploy: The events are triggered by a stale deploy. Only recovery events will be sent.
        :param recovered_from_failure: This resource went from 'not deployed' to 'deployed',
            inform unblocked dependants that they might be able to progress.
        """
        resource_id: ResourceIdStr = sending_resource.resource_id
        provides: Set[ResourceIdStr] = self._state.requires.provides_view().get(resource_id, set())

        event_listeners: Set[ResourceIdStr]
        recovery_listeners: Set[ResourceIdStr]

        if stale_deploy or not sending_resource.attributes.get(const.RESOURCE_ATTRIBUTE_SEND_EVENTS, False):
            event_listeners = set()
        else:
            event_listeners = {
                dependent
                for dependent in provides
                if (dependent_details := self._state.resources.get(dependent, None)) is not None
                if self._state.resource_state[dependent].blocked is BlockedStatus.NO
                # default to True for backward compatibility, i.e. not all resources have the field
                if dependent_details.attributes.get(const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS, True)
            }

        if not recovered_from_failure:
            recovery_listeners = set()
        else:
            recovery_listeners = {
                dependent for dependent in provides if self._state.resource_state[dependent].blocked is BlockedStatus.TRANSIENT
            }
            # These resources might be able to progress now -> unblock them in addition to sending the event
            self._state.dirty.update(recovery_listeners)
            for skipped_dependent in recovery_listeners:
                self._state.resource_state[skipped_dependent].blocked = BlockedStatus.NO

        all_listeners: Set[ResourceIdStr] = event_listeners | recovery_listeners
        if all_listeners:
            # do not pass deploying tasks because for event propagation we really want to start a new one,
            # even if the current intent is already being deployed
            task = Deploy(resource=resource_id)
            assert task in self._work.agent_queues.in_progress
            priority = self._work.agent_queues.in_progress[task]
            self._timer_manager.stop_timers(all_listeners)
            self._work.deploy_with_context(
                all_listeners,
                reason=(
                    f"Deploying because a recovery event was received from {resource_id}"
                    if recovered_from_failure
                    else f"Deploying because an event was received from {resource_id}"
                ),
                priority=priority,
                # report no ongoing deploys because ongoing deploys can not capture the event. We desire new deploys
                # to be scheduled, even if any are ongoing for the same intent.
                deploying=set(),
            )

    async def _get_last_non_deploying_state_for_dependencies(
        self, resource: ResourceIdStr
    ) -> Mapping[ResourceIdStr, const.ResourceState]:
        """
        Get resource state for every dependency of a given resource from the scheduler state.
        The state is then converted to const.ResourceState.

        Should only be called under scheduler lock.

        :param resource: The id of the resource to find the dependencies for
        """
        requires_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self._state.requires.requires_view()
        dependencies: Set[ResourceIdStr] = requires_view.get(resource, set())
        dependencies_state = {}
        for dep_id in dependencies:
            resource_state_object: ResourceState = self._state.resource_state[dep_id]
            match resource_state_object:
                case ResourceState(status=ComplianceStatus.UNDEFINED):
                    dependencies_state[dep_id] = const.ResourceState.undefined
                case ResourceState(blocked=BlockedStatus.YES):
                    dependencies_state[dep_id] = const.ResourceState.skipped_for_undefined
                case ResourceState(status=ComplianceStatus.HAS_UPDATE):
                    dependencies_state[dep_id] = const.ResourceState.available
                case ResourceState(deployment_result=DeploymentResult.SKIPPED):
                    dependencies_state[dep_id] = const.ResourceState.skipped
                case ResourceState(deployment_result=DeploymentResult.DEPLOYED):
                    dependencies_state[dep_id] = const.ResourceState.deployed
                case ResourceState(deployment_result=DeploymentResult.FAILED):
                    dependencies_state[dep_id] = const.ResourceState.failed
                case _:
                    raise Exception(f"Failed to parse the resource state for {dep_id}: {resource_state_object}")
        return dependencies_state

    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        return list(self._state.types_per_agent[agent])

    async def send_in_progress(self, action_id: UUID, resource_id: Id) -> None:
        await self._state_update_delegate.send_in_progress(action_id, resource_id)

    async def send_deploy_done(self, attribute_hash: str, result: DeployResult, state: ResourceState) -> None:
        await self._state_update_delegate.send_deploy_done(attribute_hash, result, state)

    async def dryrun_update(self, env: uuid.UUID, dryrun_result: executor.DryrunResult) -> None:
        await self._state_update_delegate.dryrun_update(env, dryrun_result)

    async def set_parameters(self, fact_result: FactResult) -> None:
        await self._state_update_delegate.set_parameters(fact_result)

    async def update_resource_intent(
        self,
        environment: UUID,
        intent: dict[ResourceIdStr, tuple[ResourceState, ResourceDetails]],
        update_blocked_state: bool,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        await self._state_update_delegate.update_resource_intent(
            environment, intent, update_blocked_state, connection=connection
        )

    async def mark_as_orphan(
        self,
        environment: UUID,
        resource_ids: Set[ResourceIdStr],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        await self._state_update_delegate.mark_as_orphan(environment, resource_ids, connection=connection)

    async def set_last_processed_model_version(
        self, environment: UUID, version: int, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        await self._state_update_delegate.set_last_processed_model_version(environment, version, connection=connection)
