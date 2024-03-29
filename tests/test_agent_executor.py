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
import concurrent.futures.thread
import hashlib
import json
import logging
import os
import subprocess

import inmanta.agent.executor
from inmanta.agent import in_process_executor
from inmanta.agent.executor import EnvBlueprint, ExecutorBlueprint, ExecutorId, VirtualEnvironmentManager
from inmanta.data.model import PipConfig
from inmanta.loader import ModuleSource
from packaging import version
from utils import PipIndex, create_python_package, log_contains, log_doesnt_contain

logger = logging.getLogger(__name__)


async def test_process_manager(environment, tmpdir) -> None:
    """
    This test verifies the creation and reuse of executors and their underlying environments. It checks whether
    new executors and environments are created as necessary and reused when the conditions are the same.
    """

    # Setup the agent
    threadpool = concurrent.futures.thread.ThreadPoolExecutor()

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
    venv_manager = VirtualEnvironmentManager(inmanta.agent.executor.initialize_envs_directory())
    executor_manager = in_process_executor.InProcessExecutorManager(threadpool, venv_manager)

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


async def test_process_manager_restart(environment, tmpdir, caplog) -> None:
    """
    Verifies that virtual environments can be rediscovered upon the restart of an ExecutorManager. This test
    simulates a restart scenario to ensure that previously created environments are reused instead of being recreated.
    """
    caplog.clear()
    threadpool = concurrent.futures.thread.ThreadPoolExecutor()

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
        venv_manager = VirtualEnvironmentManager(inmanta.agent.executor.initialize_envs_directory())
        executor_manager = in_process_executor.InProcessExecutorManager(threadpool, venv_manager)
        await executor_manager.get_executor("agent1", blueprint1)
        assert len(executor_manager.executor_map) == 1
        assert len(venv_manager._environment_map) == 1

        env_dir = os.path.join(venv_manager.envs_dir, env_bp_hash1)

        log_doesnt_contain(caplog, "inmanta.agent.executor", logging.INFO, f"Found existing virtual environment at {env_dir}")

        # Simulate ExecutorManager restart by creating new instances of ExecutorManager and VirtualEnvironmentManager
        venv_manager2 = VirtualEnvironmentManager(inmanta.agent.executor.initialize_envs_directory())
        executor_manager2 = in_process_executor.InProcessExecutorManager(threadpool, venv_manager2)
        # Assertions before retrieving the executor to verify a fresh start
        assert len(executor_manager2.executor_map) == 0
        assert len(venv_manager2._environment_map) == 0
        # Assertions after retrieval to verify the reuse of virtual environments
        await executor_manager2.get_executor("agent1", blueprint1)
        assert len(executor_manager2.executor_map) == 1
        assert len(venv_manager2._environment_map) == 1

        log_contains(caplog, "inmanta.agent.executor", logging.INFO, f"Found existing virtual environment at {env_dir}")


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
from inmanta.agent.executor import EnvBlueprint, PipConfig

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
    manager = VirtualEnvironmentManager(inmanta.agent.executor.initialize_envs_directory())

    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )

    blueprint1 = EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=("pkg1",))
    blueprint2 = EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=())

    # Wait for all tasks to complete
    env_same_1, env_same_2, env_diff_1 = await asyncio.gather(
        manager.get_environment(blueprint1, None),
        manager.get_environment(blueprint1, None),
        manager.get_environment(blueprint2, None),
    )

    assert env_same_1 is env_same_2, "Expected the same instance for the same blueprint"
    assert env_same_1 is not env_diff_1, "Expected different instances for different blueprints"


async def test_executor_creation_and_reuse(environment, tmpdir) -> None:
    """
    This test verifies the creation and reuse of executors based on their blueprints. It checks whether
    the concurrency aspects and the locking mechanisms work as intended.
    """
    threadpool = concurrent.futures.thread.ThreadPoolExecutor()

    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )

    requirements1 = ()
    requirements2 = ("pkg1",)
    pip_config = PipConfig(index_url=pip_index.url)

    # Prepare a source module and its hash
    code = """
    def test():
        return 10
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

    blueprint1 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources1)
    blueprint2 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources2)
    blueprint3 = ExecutorBlueprint(pip_config=pip_config, requirements=requirements2, sources=sources2)

    venv_manager = VirtualEnvironmentManager(inmanta.agent.executor.initialize_envs_directory())
    executor_manager = in_process_executor.InProcessExecutorManager(threadpool, venv_manager)
    executor_1, executor_1_reuse, executor_2, executor_3 = await asyncio.gather(
        executor_manager.get_executor("agent1", blueprint1),
        executor_manager.get_executor("agent1", blueprint1),
        executor_manager.get_executor("agent1", blueprint2),
        executor_manager.get_executor("agent1", blueprint3),
    )

    assert executor_1 is executor_1_reuse, "Expected the same executor instance for identical blueprint"
    assert executor_1 is not executor_2, "Expected a different executor instance for different sources"
    assert executor_1 is not executor_3, "Expected a different executor instance for different requirements and sources"
    assert executor_2 is not executor_3, "Expected different executor instances for different requirements"
