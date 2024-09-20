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
import datetime
import logging
import traceback
import uuid
from dataclasses import dataclass

from inmanta import const, data, resources
from inmanta.agent import executor
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
        version: int
        resource_details: "state.ResourceDetails"
        intent = await task_manager.get_resource_intent(self.resource, for_deploy=True)
        if intent is None:
            # Stale resource, can simply be dropped.
            return
        version, resource_details = intent

        status = await self.do_deploy(task_manager, agent, version, resource_details)

        is_success: bool = status == const.ResourceState.deployed
        await task_manager.report_resource_state(
            resource=self.resource,
            attribute_hash=resource_details.attribute_hash,
            status=state.ResourceStatus.UP_TO_DATE if is_success else state.ResourceStatus.HAS_UPDATE,
            deployment_result=state.DeploymentResult.DEPLOYED if is_success else state.DeploymentResult.FAILED,
        )

    async def do_deploy(
        self,
        task_manager: "scheduler.TaskManager",
        agent: str,
        version: int,
        resource_details: "state.ResourceDetails",
    ) -> "const.ResourceState":
        # FIXME: code loading interface is not nice like this,
        #   - we may want to track modules per agent, instead of types
        #   - we may also want to track the module version vs the model version
        #       as it avoid the problem of fast chanfing model versions
        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(version, resource_details)

        async def report_deploy_failure(excn: Exception) -> None:
            log_line = data.LogLine.log(
                logging.ERROR,
                "All resources of type `%(res_type)s` failed to load handler code or install handler code "
                "dependencies: `%(error)s`\n%(traceback)s",
                res_type=executor_resource_details.id.entity_type,
                error=str(excn),
                traceback="".join(traceback.format_tb(excn.__traceback__)),
            )
            await task_manager.client.resource_action_update(
                tid=task_manager.environment,
                resource_ids=[executor_resource_details.rvid],
                action_id=uuid.uuid4(),
                action=const.ResourceAction.deploy,
                started=datetime.datetime.now().astimezone(),
                finished=datetime.datetime.now().astimezone(),
                messages=[log_line],
                status=const.ResourceState.unavailable,
            )

        try:
            my_executor: executor.Executor = await self.get_executor(
                task_manager, agent, executor_resource_details.id.entity_type, version
            )
        except Exception as e:
            await report_deploy_failure(e)
            return const.ResourceState.unavailable

        # DEPLOY!!!
        gid = uuid.uuid4()
        # FIXME: reason argument is not used
        return await my_executor.execute(gid, executor_resource_details, "New Scheduler initiated action")


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
            my_executor = await self.get_executor(
                task_manager, agent, resources.Id.parse_id(self.resource).entity_type, version
            )
        except Exception:
            logger_for_agent(agent).warning(
                "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded",
                executor_resource_details.rvid,
            )
            return

        await my_executor.get_facts(executor_resource_details)
