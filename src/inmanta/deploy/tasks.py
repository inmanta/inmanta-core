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
import dataclasses
import logging
import traceback
import uuid
from dataclasses import dataclass

from inmanta import const, data, resources
from inmanta.agent import executor
from inmanta.agent.executor import DeployResult
from inmanta.data.model import ResourceIdStr, ResourceType
from inmanta.deploy import scheduler, state

LOGGER = logging.getLogger(__name__)


def logger_for_agent(agent: str) -> logging.Logger:
    return logging.getLogger("agent").getChild(agent)


@dataclass(frozen=True, kw_only=True)
class Task(abc.ABC):
    """
    Resource action task. Represents the execution of a specific resource action for a given resource.

    Closely coupled with deploy.scheduler.TaskManager interface. Concrete implementations must respect its contract.
    """

    resource: ResourceIdStr

    id: resources.Id = dataclasses.field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        # use object.__setattr__ because this is a frozen dataclass, see dataclasses docs
        object.__setattr__(self, "id", resources.Id.parse_id(self.resource))

    @abc.abstractmethod
    async def execute(self, task_manager: "scheduler.TaskManager", agent: str) -> None:
        pass

    def delete_with_resource(self) -> bool:
        return True

    def get_executor_resource_details(
        self, version: int, resource_details: "state.ResourceDetails"
    ) -> executor.ResourceDetails:
        return executor.ResourceDetails(
            id=self.resource,
            version=version,
            attributes=resource_details.attributes,
        )

    async def get_executor(
        self, task_manager: "scheduler.TaskManager", agent: str, resource_type: ResourceType, version: int
    ) -> executor.Executor:
        """Helper method to produce the executor"""
        code, invalid_resources = await task_manager.code_manager.get_code(
            environment=task_manager.environment,
            version=version,
            resource_types=task_manager.get_types_for_agent(agent),
        )

        # Bail out if this failed
        if resource_type in invalid_resources:
            raise invalid_resources[resource_type]

        # Get executor
        my_executor: executor.Executor = await task_manager.executor_manager.get_executor(
            agent_name=agent, agent_uri="NO_URI", code=code
        )
        failed_resources = my_executor.failed_resources

        # Bail out if this failed
        if resource_type in failed_resources:
            raise failed_resources[resource_type]

        return my_executor


class PoisonPill(Task):
    """
    Task to signal queue shutdown

    It is used to make sure all workers wake up to observe that they have been closed.
    It functions mostly as a no-op
    """

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str) -> None:
        pass


class Deploy(Task):
    async def execute(self, task_manager: "scheduler.TaskManager", agent: str) -> None:

        # First do scheduler book keeping to establish what to do
        version: int
        resource_details: "state.ResourceDetails"
        intent = await task_manager.get_resource_intent(self.resource, for_deploy=True)
        if intent is None:
            # Stale resource, can simply be dropped.
            return

        # Resolve to exector form
        version, resource_details = intent
        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(version, resource_details)

        # Make id's
        gid = uuid.uuid4()
        action_id = uuid.uuid4()  # can this be gid ?

        # The main difficulty off this code is exception handling
        # We collect state here to report back in the finally block

        # Status of the deploy for the executor/requires/provides
        success: bool = True

        # Full status of the deploy,
        # may be unset if we fail before signaling start to the server, will be set if we signaled start
        deploy_result: DeployResult | None = None

        try:
            # This try catch block ensures we report at the end of the task

            # Signal start to server
            try:
                requires: dict[ResourceIdStr, const.ResourceState] = await task_manager.send_in_progress(
                    action_id, executor_resource_details.rvid
                )
            except Exception:
                # Unrecoverable, can't reach server
                success = False
                LOGGER.error(
                    "Failed to report the start of the deployment to the server for %s",
                    resource_details.resource_id,
                    exc_info=True,
                )
                return

            # Get executor
            try:
                # FIXME: code loading interface is not nice like this,
                #   - we may want to track modules per agent, instead of types
                #   - we may also want to track the module version vs the model version
                #       as it avoid the problem of fast chanfing model versions

                my_executor: executor.Executor = await self.get_executor(
                    task_manager, agent, executor_resource_details.id.entity_type, version
                )
            except Exception as e:
                log_line = data.LogLine.log(
                    logging.ERROR,
                    "All resources of type `%(res_type)s` failed to load handler code or install handler code "
                    "dependencies: `%(error)s`\n%(traceback)s",
                    res_type=executor_resource_details.id.entity_type,
                    error=str(e),
                    traceback="".join(traceback.format_tb(e.__traceback__)),
                )
                deploy_result = DeployResult.undeployable(executor_resource_details.rvid, action_id, log_line)
                success = False
                return

            # Deploy
            try:
                # FIXME: reason argument is not used
                deploy_result = await my_executor.execute(
                    action_id, gid, executor_resource_details, "New Scheduler initiated action", requires
                )
                success = deploy_result.status == const.ResourceState.deployed
            except Exception as e:
                # This should not happen

                # We log both to scheduler log as well as the DB and the resource_action_log
                # FIXME: can be logging be unified without losing the ability to have this warning prior to writing to DB?
                # Such that we can have it if the DB is not there
                LOGGER.error("Failure during executor execution for resource %s", self.resource, exc_info=True)
                log_line = data.LogLine.log(
                    logging.ERROR,
                    "Failure during executor execution for resource %(res)s",
                    res=self.resource,
                    error=str(e),
                    traceback="".join(traceback.format_tb(e.__traceback__)),
                )
                deploy_result = DeployResult.undeployable(executor_resource_details.rvid, action_id, log_line)
                success = False
        finally:
            if deploy_result is not None:
                # We signaled start, so we signal end
                try:
                    await task_manager.send_deploy_done(deploy_result)
                except Exception:
                    success = False
                    LOGGER.error(
                        "Failed to report the end of the deployment to the server for %s",
                        resource_details.resource_id,
                        exc_info=True,
                    )

            # Always notify scheduler
            await task_manager.report_resource_state(
                resource=self.resource,
                attribute_hash=resource_details.attribute_hash,
                status=state.ResourceStatus.UP_TO_DATE if success else state.ResourceStatus.HAS_UPDATE,
                deployment_result=state.DeploymentResult.DEPLOYED if success else state.DeploymentResult.FAILED,
            )


@dataclass(frozen=True, kw_only=True)
class DryRun(Task):
    version: int
    resource_details: state.ResourceDetails
    dry_run_id: uuid.UUID

    def delete_with_resource(self) -> bool:
        return False

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str) -> None:
        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(
            self.version, self.resource_details
        )
        try:
            my_executor: executor.Executor = await self.get_executor(
                task_manager, agent, executor_resource_details.id.entity_type, self.version
            )
            await my_executor.dry_run([executor_resource_details], self.dry_run_id)
        except Exception:
            # FIXME: seems weird to conclude undeployable state from generic Exception on either of two method calls
            logger_for_agent(agent).error(
                "Skipping dryrun for resource %s because it is in undeployable state",
                executor_resource_details.rvid,
                exc_info=True,
            )
            await task_manager.client.dryrun_update(
                tid=task_manager.environment,
                id=self.dry_run_id,
                resource=executor_resource_details.rvid,
                changes={"handler": {"current": "FAILED", "desired": "Resource is in an undeployable state"}},
            )


class RefreshFact(Task):

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str) -> None:
        version: int
        intent = await task_manager.get_resource_intent(self.resource)
        if intent is None:
            # Stale resource, can simply be dropped.
            return
        # FIXME, should not need resource details, only id, see related FIXME on executor side
        version, resource_details = intent

        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(version, resource_details)
        try:
            my_executor = await self.get_executor(task_manager, agent, self.id.entity_type, version)
        except Exception:
            logger_for_agent(agent).warning(
                "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded",
                executor_resource_details.rvid,
            )
            return

        await my_executor.get_facts(executor_resource_details)
