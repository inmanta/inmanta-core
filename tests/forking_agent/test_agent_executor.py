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
import hashlib
import json
import logging
import os
import pathlib
import subprocess

from inmanta import const
from inmanta.agent import executor, forking_executor
from inmanta.data.model import PipConfig
from inmanta.loader import ModuleSource
from utils import PipIndex, log_contains, log_doesnt_contain

logger = logging.getLogger(__name__)


def code_for(bp: executor.ExecutorBlueprint) -> list[executor.ResourceInstallSpec]:
    return [executor.ResourceInstallSpec("test::Test", 5, bp)]


async def test_process_manager(environment, pip_index, mpmanager_light: forking_executor.MPManager) -> None:
    """
    This test verifies the creation and reuse of executors and their underlying environments. It checks whether
    new executors and environments are created as necessary and reused when the conditions are the same.
    """
    # Define requirements and pip configuration
    requirements1 = ("pkg1",)
    requirements2 = ("pkg1", "pkg2")
    pip_config = PipConfig(index_url=pip_index.url)

    # Prepare a source module and its hash
    code = """
def test():
    return 10

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
    blueprint1 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources1)
    env_blueprint1 = executor.EnvBlueprint(pip_config=pip_config, requirements=requirements1)
    blueprint2 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources2)
    blueprint3 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements2, sources=sources2)
    env_blueprint2 = executor.EnvBlueprint(pip_config=pip_config, requirements=requirements2)

    executor_manager = mpmanager_light
    venv_manager = mpmanager_light.environment_manager

    # Getting a first executor should successfully create and map it
    executor_1 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint1))
    assert executor_1

    assert len(executor_manager.executor_map) == 1
    assert executor_1.executor_id == executor.ExecutorId("agent1", "local:", blueprint1)
    assert executor_1.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1.executor_id] == executor_1

    assert len(venv_manager._environment_map) == 1
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_1.executor_virtual_env

    # Verify that required packages are installed in the environment
    installed = executor_1.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements1)

    # Reusing the same blueprint should reuse the executor without creating a new one
    executor_1_reuse = await executor_manager.get_executor("agent1", "local:", code_for(blueprint1))
    assert executor_1_reuse == executor_1

    assert len(executor_manager.executor_map) == 1
    assert executor_1_reuse.executor_id == executor.ExecutorId("agent1", "local:", blueprint1)
    assert executor_1_reuse.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1_reuse.executor_id] == executor_1_reuse

    assert len(venv_manager._environment_map) == 1
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_1_reuse.executor_virtual_env

    # Changing the source without changing the requirements should create a new executor but reuse the environment
    executor_2 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint2))

    assert len(executor_manager.executor_map) == 2
    assert executor_2.executor_id == executor.ExecutorId("agent1", "local:", blueprint2)
    assert executor_2.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_2.executor_id] == executor_2

    assert len(venv_manager._environment_map) == 1  # Environment is reused
    assert env_blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint1] == executor_2.executor_virtual_env

    # Changing the requirements should necessitate a new environment
    executor_3 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint3))

    assert len(executor_manager.executor_map) == 3
    assert executor_3.executor_id == executor.ExecutorId("agent1", "local:", blueprint3)
    assert executor_3.executor_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_3.executor_id] == executor_3

    assert len(venv_manager._environment_map) == 2  # A new environment is created
    assert env_blueprint2 in venv_manager._environment_map
    assert venv_manager._environment_map[env_blueprint2] == executor_3.executor_virtual_env

    installed = executor_3.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements2)


async def test_process_manager_restart(environment, tmpdir, mp_manager_factory, caplog) -> None:
    """
    Verifies that virtual environments can be rediscovered upon the restart of an ExecutorManager. This test
    simulates a restart scenario to ensure that previously created environments are reused instead of being recreated.
    """
    caplog.clear()

    # Setup a local pip, a pip config, requirements and sources
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    pip_config = PipConfig(index_url=pip_index.url)
    requirements = ()
    sources = ()

    # Create a blueprint with no requirements and no sources
    blueprint1 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements, sources=sources)
    env_bp_hash1 = blueprint1.to_env_blueprint().blueprint_hash()

    with caplog.at_level(logging.DEBUG):
        # First execution: create an executor and verify its creation
        executor_manager = mp_manager_factory(None)
        venv_manager = executor_manager.environment_manager
        await executor_manager.get_executor("agent1", "internal:", code_for(blueprint1))
        assert len(executor_manager.executor_map) == 1
        assert len(venv_manager._environment_map) == 1

        env_dir = os.path.join(venv_manager.envs_dir, env_bp_hash1)

        log_doesnt_contain(caplog, "inmanta.agent.executor", logging.INFO, f"Found existing virtual environment at {env_dir}")

        # Simulate ExecutorManager restart by creating new instances of ExecutorManager and VirtualEnvironmentManager
        executor_manager2 = mp_manager_factory(None)
        venv_manager2 = executor_manager2.environment_manager
        # Assertions before retrieving the executor to verify a fresh start
        assert len(executor_manager2.executor_map) == 0
        assert len(venv_manager2._environment_map) == 0
        # Assertions after retrieval to verify the reuse of virtual environments
        await executor_manager2.get_executor("agent1", "internal:", code_for(blueprint1))
        assert len(executor_manager2.executor_map) == 1
        assert len(venv_manager2._environment_map) == 1

        log_contains(caplog, "inmanta.agent.executor", logging.DEBUG, f"Found existing venv for content {str(blueprint1)}")


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

    blueprint1 = executor.EnvBlueprint(pip_config=pip_config, requirements=requirements1)
    blueprint2 = executor.EnvBlueprint(pip_config=pip_config, requirements=requirements2)

    hash1 = blueprint1.blueprint_hash()
    hash2 = blueprint2.blueprint_hash()
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
print(blueprint.blueprint_hash())
"""

    # Generate hash in the current session for comparison
    pip_config = PipConfig(**pip_config_dict)
    current_session_blueprint = executor.EnvBlueprint(pip_config=pip_config, requirements=requirements)
    current_hash = current_session_blueprint.blueprint_hash()

    # Generate hash in a new interpreter session
    result = subprocess.run(["python", "-c", python_code], capture_output=True, text=True)

    # Check if the subprocess ended successfully
    if result.returncode != 0:
        print(f"Error executing subprocess: {result.stderr}")
        raise RuntimeError("Subprocess execution failed")

    new_session_hash = result.stdout.strip()

    assert current_hash == new_session_hash, "Hash values should be consistent across interpreter sessions"


async def test_environment_creation_locking(pip_index, tmpdir) -> None:
    """
    Tests the locking mechanism within VirtualEnvironmentManager to ensure that
    only one environment is created for the same blueprint when requested concurrently,
    preventing race conditions and duplicate environment creation.
    """
    manager = executor.VirtualEnvironmentManager(tmpdir)

    blueprint1 = executor.EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=("pkg1",))
    blueprint2 = executor.EnvBlueprint(pip_config=PipConfig(index_url=pip_index.url), requirements=())

    # Wait for all tasks to complete
    env_same_1, env_same_2, env_diff_1 = await asyncio.gather(
        manager.get_environment(blueprint1, None),
        manager.get_environment(blueprint1, None),
        manager.get_environment(blueprint2, None),
    )

    assert env_same_1 is env_same_2, "Expected the same instance for the same blueprint"
    assert env_same_1 is not env_diff_1, "Expected different instances for different blueprints"


async def test_executor_creation_and_reuse(pip_index: PipIndex, mpmanager_light: forking_executor.MPManager) -> None:
    """
    This test verifies the creation and reuse of executors based on their blueprints. It checks whether
    the concurrency aspects and the locking mechanisms work as intended.
    """

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

    blueprint1 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources1)
    blueprint2 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources2)
    blueprint3 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements2, sources=sources2)

    executor_manager = mpmanager_light
    executor_1, executor_1_reuse, executor_2, executor_3 = await asyncio.gather(
        executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
        executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
        executor_manager.get_executor("agent1", "local:", code_for(blueprint2)),
        executor_manager.get_executor("agent1", "local:", code_for(blueprint3)),
    )

    assert executor_1 is executor_1_reuse, "Expected the same executor instance for identical blueprint"
    assert executor_1 is not executor_2, "Expected a different executor instance for different sources"
    assert executor_1 is not executor_3, "Expected a different executor instance for different requirements and sources"
    assert executor_2 is not executor_3, "Expected different executor instances for different requirements"


async def test_executor_creation_and_venv_usage(pip_index: PipIndex, mpmanager_light: forking_executor.MPManager) -> None:
    """
    This test verifies the creation and reuse of executors based on their blueprints. It checks whether
    the concurrency aspects and the locking mechanisms work as intended.
    """

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

    blueprint1 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements1, sources=sources1)
    blueprint2 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=requirements2, sources=sources2)

    executor_manager = mpmanager_light
    executor_1, executor_2 = await asyncio.gather(
        executor_manager.get_executor("agent1", "local:", code_for(blueprint1), venv_checkup_interval=0.1),
        executor_manager.get_executor("agent2", "local:", code_for(blueprint2), venv_checkup_interval=0.1),
    )
    executor_1_venv_status_file = pathlib.Path(executor_1.executor_virtual_env.env_path) / const.INMANTA_VENV_STATUS_FILENAME
    executor_2_venv_status_file = pathlib.Path(executor_2.executor_virtual_env.env_path) / const.INMANTA_VENV_STATUS_FILENAME

    old_datetime = datetime.datetime(year=2022, month=9, day=22, hour=12, minute=51, second=42)
    # This part of the test is a bit subtle because we rely on the fact that there is no context switching between the
    # modification override of the inmanta file and the retrieval of the last modification of the file
    os.utime(
        executor_2_venv_status_file,
        (datetime.datetime.now().timestamp(), old_datetime.timestamp()),
    )

    old_check_executor1 = executor_1.executor_virtual_env.get_last_used_timestamp()
    old_check_executor2 = executor_2.executor_virtual_env.get_last_used_timestamp()

    await asyncio.sleep(0.2)

    new_check_executor1 = executor_1.executor_virtual_env.get_last_used_timestamp()
    new_check_executor2 = executor_2.executor_virtual_env.get_last_used_timestamp()

    assert new_check_executor1 > old_check_executor1
    assert new_check_executor2 > old_check_executor2
    assert (datetime.datetime.now() - new_check_executor2).seconds <= 2

    # Now we want to check if the cleanup is working correctly
    await executor_manager.stop_for_agent("agent1")
    # First we want to override the modification date of the `inmanta_venv_status` file
    os.utime(executor_1_venv_status_file, (datetime.datetime.now().timestamp(), old_datetime.timestamp()))

    venv_dir = pathlib.Path(mpmanager_light.environment_manager.envs_dir)
    assert len([e for e in venv_dir.iterdir()]) == 2, "We should have two Virtual Environments for our 2 executors!"
    # We remove the old VirtualEnvironment
    await mpmanager_light.environment_manager.clean_virtual_environments()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 1, "Only one Virtual Environment should exist!"
    assert [executor_2.executor_virtual_env.env_path] == venvs

    # Let's stop the other agent and pretend that the venv is broken
    await executor_manager.stop_for_agent("agent2")
    executor_2_venv_status_file.unlink()
    await mpmanager_light.environment_manager.clean_virtual_environments()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 0, "No Virtual Environment should exist!"
