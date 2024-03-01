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
import concurrent
import hashlib
import json
import logging
import os
import subprocess
import uuid

import pytest

from inmanta import config, data, protocol
from inmanta.agent import Agent, reporting
from inmanta.agent.agent import EnvBlueprint, ExecutorBlueprint, ExecutorId, ExecutorManager, VirtualEnvironmentManager
from inmanta.agent.handler import HandlerContext, InvalidOperation
from inmanta.data.model import AttributeStateChange, PipConfig
from inmanta.loader import ModuleSource
from inmanta.resources import Id, PurgeableResource
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from packaging import version
from utils import PipIndex, create_python_package, log_contains, log_doesnt_contain, retry_limited

logger = logging.getLogger(__name__)


@pytest.mark.slowtest
async def test_agent_get_status(server, environment, agent):
    clients = server.get_slice(SLICE_SESSION_MANAGER)._sessions.values()
    assert len(clients) == 1
    clients = [x for x in clients]
    client = clients[0].get_client()
    status = await client.get_status()
    status = status.get_result()
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
    assert status.get("env") is None


def test_context_changes():
    """Test registering changes in the handler context"""
    resource = PurgeableResource(Id.parse_id("std::File[agent,path=/test],v=1"))
    ctx = HandlerContext(resource)

    # use attribute change attributes
    ctx.update_changes({"value": AttributeStateChange(current="a", desired="b")})
    assert len(ctx.changes) == 1

    # use dict
    ctx.update_changes({"value": dict(current="a", desired="b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use dict with empty string
    ctx.update_changes({"value": dict(current="", desired="value")})
    assert len(ctx.changes) == 1
    assert ctx.changes["value"].current == ""
    assert ctx.changes["value"].desired == "value"

    # use tuple
    ctx.update_changes({"value": ("a", "b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use wrong arguments
    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ("a", "b", 3)})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ["a", "b"]})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": "test"})


@pytest.fixture(scope="function")
async def async_started_agent(server_config):
    """
    Start agent with the use_autostart_agent_map option to true.
    agent.start() is executed in the background, since connection to the server will fail.
    """
    config.Config.set("config", "use_autostart_agent_map", "true")

    env_id = uuid.uuid4()
    a = Agent(hostname="node1", environment=env_id, agent_map=None, code_loader=False)
    task = asyncio.ensure_future(a.start())
    yield a
    task.cancel()
    while not task.done():
        # The CancelledError is only thrown on the next invocation of the event loop.
        # Wait until the cancellation has finished.
        await asyncio.sleep(0)


@pytest.fixture(scope="function")
async def startable_server(server_config):
    """
    This fixture returns the bootloader of a server which is not yet started.
    """
    bootloader = InmantaBootloader()
    yield bootloader
    try:
        await bootloader.stop(timeout=15)
    except concurrent.futures.TimeoutError:
        logger.exception("Timeout during stop of the server in teardown")


async def test_agent_cannot_retrieve_autostart_agent_map(async_started_agent, startable_server, caplog):
    """
    When an agent with the config option use_autostart_agent_map set to true, cannot retrieve the autostart_agent_map
    from the server at startup, the process should retry. This test verifies that the retry happens correctly.
    """
    client = protocol.Client("client")

    def retry_occured() -> bool:
        return caplog.text.count("Failed to retrieve the autostart_agent_map setting from the server.") > 2

    # Agent cannot contact server, since server is not started yet.
    await retry_limited(retry_occured, 10)

    # Start server
    await startable_server.start()

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="dev", environment_id=async_started_agent.environment)
    assert result.code == 200

    # set agent in agent map
    result = await client.get_setting(tid=async_started_agent.environment, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    result = await client.set_setting(
        tid=async_started_agent.environment,
        id=data.AUTOSTART_AGENT_MAP,
        value={"agent1": "localhost"} | result.result["value"],
    )
    assert result.code == 200

    # Assert agent managed to establish session with the server
    agent_manager = startable_server.restserver.get_slice(SLICE_AGENT_MANAGER)
    await retry_limited(lambda: (async_started_agent.environment, "agent1") in agent_manager.tid_endpoint_to_session, 10)


async def test_set_agent_map(server, environment, agent_factory):
    """
    This test verifies whether an agentmap is set correct when set via:
        1) The constructor
        2) Via the agent-map configuration option
    """
    env_id = uuid.UUID(environment)
    agent_map = {"agent1": "localhost"}

    # Set agentmap in constructor
    agent1 = await agent_factory(hostname="node1", environment=env_id, agent_map=agent_map)
    assert agent1.agent_map == agent_map

    # Set agentmap via config option
    config.Config.set("config", "agent-map", "agent2=localhost")
    agent2 = await agent_factory(hostname="node2", environment=env_id)
    assert agent2.agent_map == {"agent2": "localhost"}

    # When both are set, the constructor takes precedence
    config.Config.set("config", "agent-map", "agent3=localhost")
    agent3 = await agent_factory(hostname="node3", environment=env_id, agent_map=agent_map)
    assert agent3.agent_map == agent_map


async def test_hostname(server, environment, agent_factory):
    """
    This test verifies whether the hostname of an agent is set correct when set via:
        1) The constructor
        2) Via the agent-names configuration option
    """
    env_id = uuid.UUID(environment)

    # Set hostname in constructor
    agent1 = await agent_factory(hostname="node1", environment=env_id)
    assert list(agent1.get_end_point_names()) == ["node1"]

    # Set hostname via config option
    config.Config.set("config", "agent-names", "test123,test456")
    agent2 = await agent_factory(environment=env_id)
    assert sorted(list(agent2.get_end_point_names())) == sorted(["test123", "test456"])

    # When both are set, the constructor takes precedence
    agent3 = await agent_factory(hostname="node3", environment=env_id)
    assert list(agent3.get_end_point_names()) == ["node3"]


async def test_update_agent_map(server, environment, agent_factory):
    """
    If the URI of an enabled agent changes, it should still be enabled after the change
    """
    env_id = uuid.UUID(environment)
    agent_map = {"node1": "localhost"}

    agent1 = await agent_factory(hostname="node1", environment=env_id, agent_map=agent_map)
    assert agent1.agent_map == agent_map

    agent1.unpause("node1")

    await agent1._update_agent_map({"node1": "localhost2"})

    assert agent1._instances["node1"].is_enabled()


async def test_process_manager(environment, agent_factory, tmpdir) -> None:
    """
    This test verifies the creation and reuse of executors and their underlying environments. It checks whether
    new executors and environments are created as necessary and reused when the conditions are the same.
    """

    # Setup the agent
    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"]
    )

    # Setup a local pip index and create two packages, pkg1 and pkg2
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )
    create_python_package(
        name="pkg2",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg2"),
        publish_index=pip_index,
    )

    # Define requirements and pip configuration
    requirements1 = ("pkg1",)
    requirements2 = ("pkg1", "pkg2")
    pip_config = PipConfig(index_url=pip_index.url)

    # Prepare a source module and its hash
    code = """
    def test():
        return 10
    res1 = TestResource(Id("aa::Aa", "agent1", "aa", "aa", 1))
    res2 = TestResource(Id("aa::Aa", "agent1", "aa", "aa", 1))
    import inmanta
    inmanta.test_agent_code_loading = 5
    """.encode()
    sha1sum = hashlib.new("sha1")
    sha1sum.update(code)
    hv: str = sha1sum.hexdigest()
    module_source1 = ModuleSource(
        name="inmanta_plugins.test",
        hash_value=hv,
        is_byte_code=False,
        source=code,
    )
    sources1 = ()
    sources2 = (module_source1,)

    # Define blueprints for executors and environments
    blueprint1 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources1)
    env_blueprint1 = EnvBlueprint(pip_config=pip_config, requirements=requirements1)
    blueprint2 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources2)
    blueprint3 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements2, sources=sources2)
    env_blueprint2 = EnvBlueprint(pip_config=pip_config, requirements=requirements2)

    # Initialize the virtual environment and executor managers
    venv_manager = VirtualEnvironmentManager()
    executor_manager = ExecutorManager(agent, venv_manager)

    # Getting a first executor should successfully create and map it
    executor_1 = await executor_manager.get_executor("agent1", blueprint1)
    assert executor_1

    assert len(executor_manager.executor_map) == 1
    assert executor_1.executor_id == ExecutorId("agent1", blueprint1)
    assert executor_1.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1.executor_id] == executor_1

    assert len(venv_manager._environment_map) == 1
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_1.executor_virtual_env

    # Verify that required packages are installed in the environment
    installed = executor_1.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements1)

    # Reusing the same blueprint should reuse the executor without creating a new one
    executor_1_reuse = await executor_manager.get_executor("agent1", blueprint1)
    assert executor_1_reuse == executor_1

    assert len(executor_manager.executor_map) == 1
    assert executor_1_reuse.executor_id == ExecutorId("agent1", blueprint1)
    assert executor_1_reuse.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1_reuse.executor_id] == executor_1_reuse

    assert len(venv_manager._environment_map) == 1
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_1_reuse.executor_virtual_env

    # Changing the source without changing the requirements should create a new executor but reuse the environment
    executor_2 = await executor_manager.get_executor("agent1", blueprint2)

    assert len(executor_manager.executor_map) == 2
    assert executor_2.executor_id == ExecutorId("agent1", blueprint2)
    assert executor_2.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_2.executor_id] == executor_2

    assert len(venv_manager._environment_map) == 1  # Environment is reused
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_2.executor_virtual_env

    # Changing the requirements should necessitate a new environment
    executor_3 = await executor_manager.get_executor("agent1", blueprint3)

    assert len(executor_manager.executor_map) == 3
    assert executor_3.executor_id == ExecutorId("agent1", blueprint3)
    assert executor_3.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_3.executor_id] == executor_3

    assert len(venv_manager._environment_map) == 2  # A new environment is created
    assert env_blueprint2 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint2] == executor_3.executor_virtual_env

    installed = executor_3.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements2)


async def test_process_manager_restart(environment, agent_factory, tmpdir, caplog) -> None:
    """
    Verifies that virtual environments can be rediscovered upon the restart of an ExecutorManager. This test
    simulates a restart scenario to ensure that previously created environments are reused instead of being recreated.
    """
    caplog.clear()
    # Setup an agent
    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"]
    )

    # Setup a local pip, a pip config, requirements and sources
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    pip_config = PipConfig(index_url=pip_index.url)
    requirements = ()
    sources = ()

    # Create a blueprint with no requirements and no sources
    blueprint1 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements, sources=sources)
    env_bp_hash1 = blueprint1.to_env_blueprint().generate_blueprint_hash()

    with caplog.at_level(logging.INFO):
        # First execution: create an executor and verify its creation
        venv_manager = VirtualEnvironmentManager()
        executor_manager = ExecutorManager(agent=agent, environment_manager=venv_manager)
        await executor_manager.get_executor("agent1", blueprint1)
        assert len(executor_manager.executor_map) == 1
        assert len(venv_manager._environment_map) == 1

        env_dir = os.path.join(venv_manager.envs_dir, env_bp_hash1)

        log_doesnt_contain(caplog, "inmanta.agent.agent", logging.INFO, f"Found existing virtual environment at {env_dir}")

        # Simulate ExecutorManager restart by creating new instances of ExecutorManager and VirtualEnvironmentManager
        venv_manager2 = VirtualEnvironmentManager()
        executor_manager2 = ExecutorManager(agent, venv_manager2)
        # Assertions before retrieving the executor to verify a fresh start
        assert len(executor_manager2.executor_map) == 0
        assert len(venv_manager2._environment_map) == 0
        # Assertions after retrieval to verify the reuse of virtual environments
        await executor_manager2.get_executor("agent1", blueprint1)
        assert len(executor_manager2.executor_map) == 1
        assert len(venv_manager2._environment_map) == 1

        log_contains(caplog, "inmanta.agent.agent", logging.INFO, f"Found existing virtual environment at {env_dir}")


async def test_blueprint_hash_consistency(tmpdir):
    """
    Test to verify that the hashing mechanism for EnvBlueprints is consistent across
    different orders of requirements
    """
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    pip_config = PipConfig(index_url=pip_index.url)

    # Define two sets of requirements, identical but in different orders
    requirements1 = ("pkg1", "pkg2")
    requirements2 = ("pkg2", "pkg1")

    blueprint1 = EnvBlueprint(pip_config=pip_config, requirements=requirements1)
    blueprint2 = EnvBlueprint(pip_config=pip_config, requirements=requirements2)

    hash1 = blueprint1.generate_blueprint_hash()
    hash2 = blueprint2.generate_blueprint_hash()
    print(hash1)

    assert hash1 == hash2, "Blueprint hashes should be identical regardless of the order of requirements"


def test_hash_consistency_across_sessions():
    """
    Ensures that the hash function used within EnvBlueprint objects produces consistent hash values,
    even when the interpreter session is restarted.

    The test achieves this by:
    1. Creating an EnvBlueprint object in the current session and generating a hash value for it.
    2. Serializing the configuration of the EnvBlueprint object and embedding it into a dynamically constructed Python
       code string.
    3. Executing the constructed Python code in a new Python interpreter session using the subprocess module. This simulates
       generating the hash in a fresh interpreter session.
    4. Comparing the hash value generated in the current session with the one generated in the new interpreter session
       to ensure they are identical.
    """
    pip_config_dict = {"index_url": "http://example.com", "extra_index_url": [], "pre": None, "use_system_config": False}
    requirements = ["pkg1", "pkg2"]

    # Serialize the configuration for passing to the subprocess
    config_str = json.dumps({"pip_config": pip_config_dict, "requirements": requirements})

    # Python code to execute in subprocess
    python_code = f"""
import json
from inmanta.agent.agent import EnvBlueprint, PipConfig

config_str = '''{config_str}'''
config = json.loads(config_str)

pip_config = PipConfig(**config["pip_config"])
blueprint = EnvBlueprint(pip_config=pip_config, requirements=config["requirements"])

# Generate and print the hash
print(blueprint.generate_blueprint_hash())
"""

    # Generate hash in the current session for comparison
    pip_config = PipConfig(**pip_config_dict)
    current_session_blueprint = EnvBlueprint(pip_config=pip_config, requirements=requirements)
    current_hash = current_session_blueprint.generate_blueprint_hash()

    # Generate hash in a new interpreter session
    result = subprocess.run(["python", "-c", python_code], capture_output=True, text=True)

    # Check if the subprocess ended successfully
    if result.returncode != 0:
        print(f"Error executing subprocess: {result.stderr}")
        raise RuntimeError("Subprocess execution failed")

    new_session_hash = result.stdout.strip()

    assert current_hash == new_session_hash, "Hash values should be consistent across interpreter sessions"


async def test_environment_creation_locking(environment, tmpdir) -> None:
    """
    Tests the locking mechanism within VirtualEnvironmentManager to ensure that
    only one environment is created for the same blueprint when requested concurrently,
    preventing race conditions and duplicate environment creation.
    """
    manager = VirtualEnvironmentManager()

    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )

    blueprint1 = EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=("pkg1",))
    blueprint2 = EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=())

    # Event to control the execution of get environment
    creation_event = asyncio.Event()

    # adjust the environment creation method to await the event
    original_get_environment = manager.get_environment

    async def mock_get_environment(blueprint, threadpool):
        await creation_event.wait()  # Wait for the event to be set
        return await original_get_environment(blueprint, threadpool)

    manager.get_environment = mock_get_environment

    # Start all get_environment but wait before proceeding
    task_same_1 = asyncio.create_task(manager.get_environment(blueprint1, None))
    task_same_2 = asyncio.create_task(manager.get_environment(blueprint1, None))
    task_diff_1 = asyncio.create_task(manager.get_environment(blueprint2, None))

    # Allow all get_environment tasks to proceed
    creation_event.set()

    # Wait for all tasks to complete
    env_same_1, env_same_2, env_diff_1 = await asyncio.gather(task_same_1, task_same_2, task_diff_1)

    assert env_same_1 is env_same_2, "Expected the same instance for the same blueprint"
    assert env_same_1 is not env_diff_1, "Expected different instances for different blueprints"
