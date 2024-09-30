"""
    Copyright 2017 Inmanta

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
import time
import uuid
from collections import defaultdict, namedtuple
from threading import Condition
from typing import Any, Generic

from pytest import fixture

from inmanta import const, data
from inmanta.agent.agent import Agent
from inmanta.agent.handler import CRUDHandlerGeneric as CRUDHandler
from inmanta.agent.handler import HandlerContext, ResourceHandler, ResourcePurged, SkipResource, TResource, provider
from inmanta.data.model import ResourceIdStr
from inmanta.resources import IgnoreResourceException, PurgeableResource, Resource, resource
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import get_compiler_version
from utils import retry_limited

logger = logging.getLogger("inmanta.test.server_agent")


async def get_agent(server, environment, *endpoints, hostname="nodes1") -> Agent:
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    prelen = len(agentmanager.sessions)
    agent = Agent(
        hostname=hostname, environment=environment, agent_map={agent: "localhost" for agent in endpoints}, code_loader=False
    )
    for agentname in endpoints:
        await agent.add_end_point_name(agentname)
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == prelen + 1, 10)
    return agent


async def stop_agent(server, agent):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    prelen = len(agentmanager.sessions)
    await agent.stop()
    await retry_limited(lambda: len(agentmanager.sessions) == prelen - 1, 10)


async def _deploy_resources(client, environment, resources, version, push, agent_trigger_method=None):
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, push, agent_trigger_method)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == len(resources)

    result = await client.get_version(environment, version)
    assert result.code == 200

    return result


async def wait_for_n_deployed_resources(client, environment, version, n, timeout=5):
    async def is_deployment_finished():
        result = await client.get_version(environment, version)
        assert result.code == 200
        print(result.result["model"])
        return result.result["model"]["done"] >= n

    await retry_limited(is_deployment_finished, timeout)


async def _wait_for_n_deploying(client, environment, version, n, timeout=10):
    async def in_progress():
        result = await client.get_version(environment, version)
        assert result.code == 200
        res = [res for res in result.result["resources"] if res["status"] == "deploying"]
        return len(res) >= n

    await retry_limited(in_progress, timeout)


ResourceContainer = namedtuple(
    "ResourceContainer", ["Provider", "waiter", "wait_for_done_with_waiters", "wait_for_condition_with_waiters"]
)


@fixture(scope="function")
def resource_container(clean_reset):
    @resource("test::Resource", agent="agent", id_attribute="key")
    class MyResource(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::Fact", agent="agent", id_attribute="key")
    class FactResource(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "skip", "factvalue", "skipFact")

    @resource("test::SetFact", agent="agent", id_attribute="key")
    class SetFactResource(PurgeableResource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::SetNonExpiringFact", agent="agent", id_attribute="key")
    class SetNonExpiringFactResource(PurgeableResource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::Fail", agent="agent", id_attribute="key")
    class FailR(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::Wait", agent="agent", id_attribute="key")
    class WaitR(Resource):
        """
        A file on a filesystem
        """
        timeout: float = 10
        fields = ("key", "value", "purged")

    @resource("test::Noprov", agent="agent", id_attribute="key")
    class NoProv(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::FailFast", agent="agent", id_attribute="key")
    class FailFastR(Resource):
        """
        Raise an exception in the check_resource() method.
        """

        fields = ("key", "value", "purged")

    @resource("test::FailFastCRUD", agent="agent", id_attribute="key")
    class FailFastPR(PurgeableResource):
        """
        Raise an exception at the beginning of the read_resource() method
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::BadPost", agent="agent", id_attribute="key")
    class BadPostR(Resource):
        """
        Raise an exception in the post() method of the ResourceHandler.
        """

        fields = ("key", "value", "purged")

    @resource("test::BadPostCRUD", agent="agent", id_attribute="key")
    class BadPostPR(PurgeableResource):
        """
        Raise an exception in the post() method of the CRUDHandlerGeneric.
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::BadLogging", agent="agent", id_attribute="key")
    class BadLoggingR(Resource):
        """
        Raises an exception when trying to log a message that's not serializable.
        """

        fields = ("key", "value", "purged")

    @resource("test::Deploy", agent="agent", id_attribute="key")
    class DeployR(Resource):
        """
        Raise a SkipResource exception in the deploy() handler method.
        """

        fields = ("key", "value", "set_state_to_deployed", "purged")

    @resource("test::EventResource", agent="agent", id_attribute="key")
    class EventResource(PurgeableResource):
        """
        Raise a SkipResource exception in the deploy() handler method.
        """

        fields = ("key", "value", "change", "purged")

        @classmethod
        def get_change(cls, _, r):
            return False

    # Remote control state, shared over all resources
    _STATE = defaultdict(dict)
    _WRITE_COUNT = defaultdict(lambda: defaultdict(int))
    _RELOAD_COUNT = defaultdict(lambda: defaultdict(int))
    _READ_COUNT = defaultdict(lambda: defaultdict(int))
    _TO_SKIP = defaultdict(lambda: defaultdict(int))
    _TO_FAIL = defaultdict(lambda: defaultdict(int))

    class Provider(ResourceHandler[TResource], Generic[TResource]):
        def check_resource(self, ctx, resource):
            self.read(resource.id.get_agent_name(), resource.key)
            assert resource.value != const.UNKNOWN_STRING
            current = resource.clone()
            current.purged = not self.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = self.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            if self.skip(resource.id.get_agent_name(), resource.key):
                raise SkipResource()

            if self.fail(resource.id.get_agent_name(), resource.key):
                raise Exception("Failed")

            if "purged" in changes:
                self.touch(resource.id.get_agent_name(), resource.key)
                if changes["purged"]["desired"]:
                    self.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    self.set(resource.id.get_agent_name(), resource.key, resource.value)
                    ctx.set_created()

            elif "value" in changes:
                ctx.info("Set key '%(key)s' to value '%(value)s'", key=resource.key, value=resource.value)
                self.touch(resource.id.get_agent_name(), resource.key)
                self.set(resource.id.get_agent_name(), resource.key, resource.value)
                ctx.set_updated()

            return changes

        def facts(self, ctx, resource):
            return {"length": len(self.get(resource.id.get_agent_name(), resource.key)), "key1": "value1", "key2": "value2"}

        def can_reload(self) -> bool:
            return True

        def do_reload(self, ctx, resource):
            _RELOAD_COUNT[resource.id.get_agent_name()][resource.key] += 1

        @classmethod
        def set_skip(cls, agent, key, skip):
            _TO_SKIP[agent][key] = skip

        @classmethod
        def set_fail(cls, agent, key, failcount):
            _TO_FAIL[agent][key] = failcount

        @classmethod
        def skip(cls, agent, key):
            doskip = _TO_SKIP[agent][key]
            if doskip == 0:
                return False
            _TO_SKIP[agent][key] -= 1
            return True

        @classmethod
        def fail(cls, agent, key):
            doskip = _TO_FAIL[agent][key]
            if doskip == 0:
                return False
            _TO_FAIL[agent][key] -= 1
            return True

        @classmethod
        def touch(cls, agent, key):
            _WRITE_COUNT[agent][key] += 1

        @classmethod
        def read(cls, agent, key):
            _READ_COUNT[agent][key] += 1

        @classmethod
        def set(cls, agent, key, value):
            _STATE[agent][key] = value

        @classmethod
        def get(cls, agent, key):
            if key in _STATE[agent]:
                return _STATE[agent][key]
            return None

        @classmethod
        def isset(cls, agent, key):
            return key in _STATE[agent]

        @classmethod
        def delete(cls, agent, key):
            if cls.isset(agent, key):
                del _STATE[agent][key]

        @classmethod
        def changecount(cls, agent, key):
            return _WRITE_COUNT[agent][key]

        @classmethod
        def readcount(cls, agent, key):
            return _READ_COUNT[agent][key]

        @classmethod
        def reloadcount(cls, agent, key):
            return _RELOAD_COUNT[agent][key]

        @classmethod
        def reset(cls):
            _STATE.clear()
            _WRITE_COUNT.clear()
            _READ_COUNT.clear()
            _TO_SKIP.clear()
            _TO_FAIL.clear()
            _RELOAD_COUNT.clear()

    @provider("test::Resource", name="test_resource")
    class ResourceProvider(Provider[MyResource]):
        pass

    @provider("test::Fail", name="test_fail")
    class Fail(ResourceHandler[FailR]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = Provider.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            raise Exception()

    @provider("test::FailFast", name="test_failfast")
    class FailFast(ResourceHandler[FailFastR]):
        def check_resource(self, ctx: HandlerContext, resource: Resource) -> Resource:
            raise Exception("An\nError\tMessage")

    @provider("test::FailFastCRUD", name="test_failfast_crud")
    class FailFastCRUD(CRUDHandler[FailFastPR]):
        def read_resource(self, ctx: HandlerContext, resource: FailFastPR) -> None:
            raise Exception("An\nError\tMessage")

    @provider("test::Fact", name="test_fact")
    class Fact(ResourceHandler[FactResource]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            current.value = "that"

            return current

        def do_changes(self, ctx, resource, changes):
            if resource.skip:
                raise SkipResource("can not deploy")
            if "purged" in changes:
                if changes["purged"]["desired"]:
                    Provider.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    Provider.set(resource.id.get_agent_name(), resource.key, "x")
                    ctx.set_created()
            else:
                ctx.set_updated()

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            if not Provider.isset(resource.id.get_agent_name(), resource.key):
                return {}
            elif resource.skipFact:
                raise SkipResource("Not ready")
            return {"fact": resource.factvalue}

    @provider("test::SetFact", name="test_set_fact")
    class SetFact(CRUDHandler[SetFactResource]):
        def read_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            self._do_set_fact(ctx, resource)

        def create_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            pass

        def delete_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            pass

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: SetFactResource) -> None:
            pass

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            self._do_set_fact(ctx, resource)
            return {f"returned_fact_{resource.key}": "test"}

        def _do_set_fact(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            ctx.set_fact(fact_id=resource.key, value=resource.value)

    @provider("test::SetNonExpiringFact", name="test_set_non_expiring_fact")
    class SetNonExpiringFact(CRUDHandler[SetNonExpiringFactResource]):
        def read_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            self._do_set_fact(ctx, resource)

        def create_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            pass

        def delete_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            pass

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: SetNonExpiringFactResource) -> None:
            pass

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            self._do_set_fact(ctx, resource)
            return {}

        def _do_set_fact(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            expires = resource.key == "expiring"
            ctx.set_fact(fact_id=resource.key, value=resource.value, expires=expires)

    @provider("test::BadPost", name="test_bad_posts")
    class BadPost(Provider):
        def post(self, ctx: HandlerContext, resource: Resource) -> None:
            raise Exception("An\nError\tMessage")

    @provider("test::BadPostCRUD", name="test_bad_posts_crud")
    class BadPostCRUD(CRUDHandler[BadPostPR]):
        def post(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
            raise Exception("An\nError\tMessage")

    class Empty:
        pass

    @provider("test::BadLogging", name="test_bad_logging")
    class BadLogging(ResourceHandler[BadLoggingR]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            return current

        def do_changes(self, ctx, resource, changes):
            ctx.info("This is not JSON serializable: %(val)s", val=Empty())

    @resource("test::AgentConfig", agent="agent", id_attribute="agentname")
    class AgentConfig(PurgeableResource):
        """
        A resource that can modify the agentmap for autostarted agents
        """

        fields = ("agentname", "uri", "autostart")

        @staticmethod
        def get_autostart(exp, obj):
            try:
                if not obj.autostart:
                    raise IgnoreResourceException()
            except Exception as e:
                # When this attribute is not set, also ignore it
                raise IgnoreResourceException() from e
            return obj.autostart

    @provider("test::AgentConfig", name="agentrest")
    class AgentConfigHandler(CRUDHandler[AgentConfig]):
        def _get_map(self) -> dict:
            def call():
                return self.get_client().get_setting(tid=self._agent.environment, id=data.AUTOSTART_AGENT_MAP)

            value = self.run_sync(call)
            return value.result["value"]

        def _set_map(self, agent_config: dict) -> None:
            def call():
                return self.get_client().set_setting(
                    tid=self._agent.environment, id=data.AUTOSTART_AGENT_MAP, value=agent_config
                )

            return self.run_sync(call)

        def read_resource(self, ctx: HandlerContext, resource: AgentConfig) -> None:
            agent_config = self._get_map()
            ctx.set("map", agent_config)

            if resource.agentname not in agent_config:
                raise ResourcePurged()

            resource.uri = agent_config[resource.agentname]

        def create_resource(self, ctx: HandlerContext, resource: AgentConfig) -> None:
            agent_config = ctx.get("map")
            agent_config[resource.agentname] = resource.uri
            self._set_map(agent_config)

        def delete_resource(self, ctx: HandlerContext, resource: AgentConfig) -> None:
            agent_config = ctx.get("map")
            del agent_config[resource.agentname]
            self._set_map(agent_config)

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: AgentConfig) -> None:
            agent_config = ctx.get("map")
            agent_config[resource.agentname] = resource.uri
            self._set_map(agent_config)

    waiter = Condition()

    async def wait_for_done_with_waiters(client, env_id, version, wait_for_this_amount_of_resources_in_done=None, timeout=10):
        def log_progress(done: int, total: int) -> None:
            logger.info(
                "waiting with waiters, %s/%s resources done",
                done,
                (wait_for_this_amount_of_resources_in_done if wait_for_this_amount_of_resources_in_done else total),
            )

        # unhang waiters
        result = await client.get_version(env_id, version)
        assert result.code == 200
        now = time.time()
        log_progress(result.result["model"]["done"], result.result["model"]["total"])
        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            if now + timeout < time.time():
                raise Exception("Timeout")
            if (
                wait_for_this_amount_of_resources_in_done
                and result.result["model"]["done"] - wait_for_this_amount_of_resources_in_done >= 0
            ):
                break
            result = await client.get_version(env_id, version)
            log_progress(result.result["model"]["done"], result.result["model"]["total"])
            waiter.acquire()
            waiter.notify_all()
            waiter.release()
            await asyncio.sleep(0.1)

        return result

    async def wait_for_condition_with_waiters(wait_condition, timeout=10):
        """
        Wait until wait_condition() returns false
        """
        now = time.time()
        while await wait_condition():
            if now + timeout < time.time():
                raise Exception("Timeout")
            logger.info("waiting with waiters")
            waiter.acquire()
            waiter.notify_all()
            waiter.release()
            await asyncio.sleep(0.1)

    @provider("test::Wait", name="test_wait")
    class Wait(Provider[WaitR]):
        def __init__(self, agent, io=None):
            super().__init__(agent, io)
            self.traceid = uuid.uuid4()

        def deploy(self, ctx, resource: WaitR, requires) -> None:
            # Hang even when skipped
            logger.info("Hanging waiter %s", self.traceid)
            waiter.acquire()
            notified_before_timeout = waiter.wait(timeout=resource.timeout)
            waiter.release()
            if not notified_before_timeout:
                raise Exception("Timeout occurred")
            logger.info("Releasing waiter %s", self.traceid)
            super().deploy(ctx, resource, requires)

    @provider("test::EventResource", name="test_event_processing")
    class EventResourceProvider(CRUDHandler[EventResource]):
        def __init__(self, agent, io=None):
            super().__init__(agent, io)
            self.traceid = uuid.uuid4()

        def read_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            logger.info("Hanging waiter %s", self.traceid)
            waiter.acquire()
            notified_before_timeout = waiter.wait(timeout=10)
            waiter.release()
            if not notified_before_timeout:
                raise Exception("Timeout occurred")
            logger.info("Releasing waiter %s", self.traceid)

            Provider.read(resource.id.get_agent_name(), resource.key)
            environment = self._agent.environment

            async def should_redeploy() -> bool:
                client = self.get_client()
                result = await client.get_resource_events(
                    environment,
                    resource.id.resource_version_str(),
                    const.Change.nochange,
                )
                if result.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when checking for events: received {result.code} "
                        f"(expected 200): {result.result}"
                    )
                changed_dependencies = result.result["data"]
                assert isinstance(changed_dependencies, dict)

                actual_changes = {k: v for k, v in changed_dependencies.items() if v}
                if actual_changes:
                    ctx.debug("Change found: %(changes)s, deploying", changes=actual_changes)
                else:
                    ctx.debug("No changes, not deploying")

                return bool(actual_changes)

            resource.change = self.run_sync(should_redeploy)

        def create_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_created()

        def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_updated()

        def delete_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_purged()

    @provider("test::Deploy", name="test_wait")
    class Deploy(Provider):
        def deploy(
            self,
            ctx: HandlerContext,
            resource: Resource,
            requires: dict[ResourceIdStr, const.ResourceState],
        ) -> None:
            if self.skip(resource.id.agent_name, resource.key):
                raise SkipResource()
            elif self.fail(resource.id.agent_name, resource.key):
                raise Exception()
            elif resource.set_state_to_deployed:
                ctx.set_status(const.ResourceState.deployed)

    yield ResourceContainer(
        Provider=Provider,
        wait_for_done_with_waiters=wait_for_done_with_waiters,
        waiter=waiter,
        wait_for_condition_with_waiters=wait_for_condition_with_waiters,
    )
    Provider.reset()
