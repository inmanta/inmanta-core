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
from typing import Optional

from inmanta import const, data
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
    """

    resource: ResourceIdStr

    @abc.abstractmethod
    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        """the scheduler is considered to be a friend class: access to internal members is expected"""
        pass

    def delete_with_resource(self) -> bool:
        return True

    async def get_executor(
        self, scheduler: "scheduler.ResourceScheduler", agent: str, entity_type: ResourceType, version: int
    ) -> executor.Executor:
        """Helper method to produce the executor"""
        code, invalid_resources = await scheduler._code_manager.get_code(
            environment=scheduler._environment,
            version=version,
            resource_types=scheduler._state.get_types_for_agent(agent),
        )

        # Bail out if this failed
        if entity_type in invalid_resources:
            raise invalid_resources[entity_type]

        # Get executor
        my_executor: executor.Executor = await scheduler._executor_manager.get_executor(
            agent_name=agent, agent_uri="NO_URI", code=code
        )
        failed_resources = my_executor.failed_resources

        # Bail out if this failed
        if entity_type in failed_resources:
            raise failed_resources[entity_type]

        return my_executor


class PoisonPill(Task):
    """
    Task to signal queue shutdown

    It is used to make sure all workers wake up to observe that they have been closed.
    It functions mostly as a no-op
    """

    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        pass


# TODO: drop this intermediate class now that the logic has become so simple?
class OnLatestState(Task):

    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        intent: Optional[tuple[int, "state.ResourceDetails"]]
        intent = await scheduler.get_resource_intent(self.resource)
        if intent is None:
            # Stale resource, can simply be dropped.
            return
        await self.execute_on_resource(scheduler, agent, intent[1])

    @abc.abstractmethod
    async def execute_on_resource(
        self, scheduler: "scheduler.ResourceScheduler", agent: str, resource_details: "state.ResourceDetails"
    ) -> None:
        pass


class Deploy(OnLatestState):
    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        version: int
        resource_details: "state.ResourceDetails"
        intent = await scheduler.get_resource_intent(self.resource)
        if intent is None:
            # Stale resource, can simply be dropped.
            return
        version, resource_details = intent

        status = await self.do_deploy(scheduler, agent, version, resource_details)

        is_success: bool = status == const.ResourceState.deployed
        scheduler.report_resource_state(
            resource=resource,
            attribute_hash=resource_details.attribute_hash,
            status=state.ResourceStatus.UP_TO_DATE if is_success else state.ResourceStatus.HAS_UPDATE,
            deployment_result=state.DeploymentResult.DEPLOYED if is_success else state.DeploymentResult.FAILED,
        )

    async def do_deploy(
        self,
        scheduler: "scheduler.ResourceScheduler",
        agent: str,
        version: int,
        resource_details: "state.ResourceDetails",
    ) -> "const.ResourceState":
        # FIXME: WDB to Sander: is the version of the state the correct version?
        #   It may happen that the set of types no longer matches the version?
        # FIXME: code loading interface is not nice like this,
        #   - we may want to track modules per agent, instead of types
        #   - we may also want to track the module version vs the model version
        #       as it avoid the problem of fast chanfing model versions

        async def report_deploy_failure(excn: Exception) -> None:
            res_type = resource_details.id.entity_type
            log_line = data.LogLine.log(
                logging.ERROR,
                "All resources of type `%(res_type)s` failed to load handler code or install handler code "
                "dependencies: `%(error)s`\n%(traceback)s",
                res_type=res_type,
                error=str(excn),
                traceback="".join(traceback.format_tb(excn.__traceback__)),
            )
            await scheduler._client.resource_action_update(
                tid=scheduler._environment,
                resource_ids=[resource_details.rvid],
                action_id=uuid.uuid4(),
                action=const.ResourceAction.deploy,
                started=datetime.datetime.now().astimezone(),
                finished=datetime.datetime.now().astimezone(),
                messages=[log_line],
                status=const.ResourceState.unavailable,
            )

        # Find code
        version = scheduler._state.version

        try:
            my_executor: executor.Executor = await self.get_executor(scheduler, agent, resource_details.id.entity_type, version)
        except Exception as e:
            await report_deploy_failure(e)
            return const.ResourceState.unavailable

        # DEPLOY!!!
        gid = uuid.uuid4()
        # FIXME: reason argument is not used
        executor_resource_details: executor.ResourceDetails = executor.ResourceDetails(
            id=self.resource,
            version=version,
            attributes=resource_details.attributes,
        )
        return await my_executor.execute(gid, resource_details, "New Scheduler initiated action")


@dataclass(frozen=True, kw_only=True)
class DryRun(Task):
    version: int
    resource_details: state.ResourceDetails
    dry_run_id: uuid.UUID

    def delete_with_resource(self) -> bool:
        return False

    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        try:
            my_executor: executor.Executor = await self.get_executor(
                scheduler, agent, self.resource_details.id.entity_type, self.version
            )
            await my_executor.dry_run([self.resource_details], self.dry_run_id)
        except Exception:
            logger_for_agent(agent).error(
                "Skipping dryrun for resource %s because it is in undeployable state %s",
                self.resource_details.rvid,
                exc_info=True,
            )
            await scheduler._client.dryrun_update(
                tid=scheduler._environment,
                id=self.dry_run_id,
                resource=self.resource_details.rvid,
                changes={"handler": {"current": "FAILED", "desired": "Resource is in an undeployable state"}},
            )


class RefreshFact(OnLatestState):

    async def execute_on_resource(
        self, scheduler: "scheduler.ResourceScheduler", agent: str, resource_details: "state.ResourceDetails"
    ) -> None:
        try:
            executor = await self.get_executor(scheduler, agent, resource_details.id.entity_type, scheduler._state.version)
        except Exception:
            logger_for_agent(agent).warning(
                "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded",
                resource_details.rvid,
            )
            return

        await executor.get_facts(resource_details)
