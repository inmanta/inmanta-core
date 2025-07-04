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
import datetime
import logging
import traceback
import uuid
from dataclasses import dataclass

from inmanta import data, resources
from inmanta.agent import executor
from inmanta.agent.executor import DeployReport, ModuleLoadingException
from inmanta.data.model import AttributeStateChange
from inmanta.deploy import scheduler, state
from inmanta.types import ResourceIdStr
from inmanta.vendor import pyformance

LOGGER = logging.getLogger(__name__)


def logger_for_agent(agent: str) -> logging.Logger:
    return logging.getLogger("agent").getChild(agent)


# must remain frozen because it's used as key/identity for deploy intent
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
    async def execute(self, task_manager: "scheduler.TaskManager", agent: str, reason: str | None = None) -> None:
        pass

    def delete_with_resource(self) -> bool:
        return True

    def get_executor_resource_details(self, version: int, resource_intent: "state.ResourceIntent") -> executor.ResourceDetails:
        return executor.ResourceDetails(
            id=self.resource,
            version=version,
            attributes=resource_intent.attributes,
        )

    async def get_executor(
        self,
        *,
        task_manager: "scheduler.TaskManager",
        agent_name: str,
        version: int,
    ) -> executor.Executor:
        """
        Helper method to produce the executor

        :param task_manager: A reference to the task manager instance.
        :param agent_name: agent name.
        :param version: The version of the code to load on the executor.
        """

        code = await task_manager.code_manager.get_code(
            environment=task_manager.environment, model_version=version, agent_name=agent_name
        )

        # Get executor
        my_executor: executor.Executor = await task_manager.executor_manager.get_executor(
            agent_name=agent_name, agent_uri="NO_URI", code=code
        )
        return my_executor


class PoisonPill(Task):
    """
    Task to signal queue shutdown

    It is used to make sure all workers wake up to observe that they have been closed.
    It functions mostly as a no-op
    """

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str, reason: str | None = None) -> None:
        pass


class Deploy(Task):
    async def execute(self, task_manager: "scheduler.TaskManager", agent: str, reason: str | None = None) -> None:
        with pyformance.timer("internal.deploy").time():
            # Make id's
            gid = uuid.uuid4()
            action_id = uuid.uuid4()  # can this be gid ?

            # First do scheduler book keeping to establish what to do
            try:
                deploy_intent = await task_manager.deploy_start(action_id, self.resource)
            except Exception:
                # Unrecoverable, can't reach DB
                LOGGER.error(
                    "Failed to report the start of the deployment to the server for %s",
                    self.resource,
                    exc_info=True,
                )
                return

            if deploy_intent is None:
                # Stale resource, can simply be dropped.
                return

            # From this point on, we HAVE to call deploy_done to make sure we are not stuck in deploying
            # We collect state here to report back in the finally block.
            # This try-finally block ensures we report at the end of the task.
            deploy_report: DeployReport
            try:
                # Dependencies are always set when calling deploy_start
                assert deploy_intent.dependencies is not None
                # Resolve to executor form
                version: int = deploy_intent.model_version
                resource_intent: "state.ResourceIntent" = deploy_intent.intent
                executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(
                    version, resource_intent
                )

                # Get executor
                try:
                    my_executor: executor.Executor = await self.get_executor(
                        task_manager=task_manager,
                        agent_name=agent,
                        version=version,
                    )
                except ModuleLoadingException as e:
                    e.log_resource_action_to_scheduler_log(
                        agent=agent, rid=executor_resource_details.rvid, include_exception_info=True
                    )
                    log_line_for_web_console = e.create_log_line_for_failed_modules(
                        agent=agent, level=logging.ERROR, verbose_message=False
                    )
                    deploy_report = DeployReport.undeployable(
                        executor_resource_details.rvid, action_id, log_line_for_web_console
                    )
                    return

                except Exception as e:
                    log_line = data.LogLine.log(
                        logging.ERROR,
                        "All resources of type `%(res_type)s` failed to install handler code "
                        "dependencies: `%(error)s`\n%(traceback)s",
                        res_type=executor_resource_details.id.entity_type,
                        error=str(e),
                        traceback="".join(traceback.format_tb(e.__traceback__)),
                    )

                    # Not attached to ctx, needs to be flushed to logger explicitly
                    log_line.write_to_logger_for_resource(agent, executor_resource_details.rvid, exc_info=True)
                    deploy_report = DeployReport.undeployable(executor_resource_details.rvid, action_id, log_line)

                    return

                assert reason is not None  # Should always be set for deploy
                # Deploy
                try:
                    deploy_report = await my_executor.execute(
                        action_id, gid, executor_resource_details, reason, deploy_intent.dependencies
                    )

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
                    # Not attached to ctx, needs to be flushed to logger explicitly
                    log_line.write_to_logger_for_resource(agent, executor_resource_details.rvid, exc_info=True)
                    deploy_report = DeployReport.undeployable(executor_resource_details.rvid, action_id, log_line)

            finally:
                # We signaled start, so we signal end
                try:
                    await task_manager.deploy_done(deploy_intent, deploy_report)
                except Exception:
                    LOGGER.error(
                        "Failed to report the end of the deployment to the server for %s",
                        resource_intent.resource_id,
                        exc_info=True,
                    )


@dataclass(frozen=True, kw_only=True)
class DryRun(Task):
    version: int
    resource_intent: state.ResourceIntent
    dry_run_id: uuid.UUID

    def delete_with_resource(self) -> bool:
        return False

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str, reason: str | None = None) -> None:
        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(
            self.version, self.resource_intent
        )
        # Just in case we reach the general exception
        started = datetime.datetime.now().astimezone()
        try:
            my_executor: executor.Executor = await self.get_executor(
                task_manager=task_manager,
                agent_name=agent,
                version=self.version,
            )
        except Exception:
            logger_for_agent(agent).error(
                "Skipping dryrun for resource %s because due to an error in constructing the executor",
                executor_resource_details.rvid,
                exc_info=True,
            )
            dryrun_report = executor.DryrunReport(
                rvid=executor_resource_details.rvid,
                dryrun_id=self.dry_run_id,
                changes={
                    "handler": AttributeStateChange(
                        current="FAILED", desired="Unable to construct an executor for this resource"
                    )
                },
                started=started,
                finished=datetime.datetime.now().astimezone(),
                messages=[],
            )
        else:
            try:
                dryrun_report = await my_executor.dry_run(executor_resource_details, self.dry_run_id)
            except Exception:
                logger_for_agent(agent).error(
                    "Skipping dryrun for resource %s because it is in undeployable state",
                    executor_resource_details.rvid,
                    exc_info=True,
                )
                dryrun_report = executor.DryrunReport(
                    rvid=executor_resource_details.rvid,
                    dryrun_id=self.dry_run_id,
                    changes={"handler": AttributeStateChange(current="FAILED", desired="Resource is in an undeployable state")},
                    started=started,
                    finished=datetime.datetime.now().astimezone(),
                    messages=[],
                )
        await task_manager.dryrun_done(dryrun_report)


class RefreshFact(Task):

    async def execute(self, task_manager: "scheduler.TaskManager", agent: str, reason: str | None = None) -> None:
        version: int
        version_intent = await task_manager.get_resource_version_intent(self.resource)
        if version_intent is None:
            # Stale resource, can simply be dropped.
            return
        # FIXME, should not need resource intent, only id, see related FIXME on executor side
        version = version_intent.model_version
        resource_intent = version_intent.intent

        executor_resource_details: executor.ResourceDetails = self.get_executor_resource_details(version, resource_intent)
        try:
            my_executor = await self.get_executor(
                task_manager=task_manager,
                agent_name=agent,
                version=version,
            )
        except Exception:
            logger_for_agent(agent).warning(
                "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded",
                executor_resource_details.rvid,
            )
            return

        get_fact_report = await my_executor.get_facts(executor_resource_details)
        await task_manager.fact_refresh_done(get_fact_report)
