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
import functools
import hashlib
import logging
import os
import pathlib
import subprocess
import sys

from inmanta import const
from inmanta.agent import executor, forking_executor
from inmanta.agent.forking_executor import MPExecutor
from inmanta.data.model import PipConfig
from inmanta.loader import ModuleSource
from inmanta.signals import dump_ioloop_running, dump_threads
from utils import PipIndex, log_contains, log_doesnt_contain, retry_limited

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

    def make_module_source(name: str, content: str) -> ModuleSource:
        code = content.encode()
        sha1sum = hashlib.new("sha1")
        sha1sum.update(code)
        hv: str = sha1sum.hexdigest()
        return ModuleSource(
            name=name,
            hash_value=hv,
            is_byte_code=False,
            source=code,
        )

    # Prepare a source module and its hash
    module_source1 = make_module_source(
        "inmanta_plugins.test",
        """\
import inmanta
inmanta.test_agent_code_loading = 5

def test():
    return 10

import inmanta_plugins.sub
assert inmanta_plugins.sub.a == 1""",
    )

    # Prepare a cross module import, this should work
    module_source2 = make_module_source("inmanta_plugins.sub", """a=1""")

    sources1 = []
    sources2 = [module_source1, module_source2]

    # Define blueprints for executors and environments
    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements1, sources=sources1, python_version=sys.version_info[:2]
    )
    env_blueprint1 = executor.EnvBlueprint(
        pip_config=pip_config, requirements=requirements1, python_version=sys.version_info[:2]
    )
    blueprint2 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements1, sources=sources2, python_version=sys.version_info[:2]
    )
    blueprint3 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements2, sources=sources2, python_version=sys.version_info[:2]
    )
    env_blueprint2 = executor.EnvBlueprint(
        pip_config=pip_config, requirements=requirements2, python_version=sys.version_info[:2]
    )

    executor_manager = mpmanager_light
    venv_manager = mpmanager_light.process_pool.environment_manager

    # Getting a first executor should successfully create and map it
    executor_1 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint1))
    assert executor_1

    assert len(executor_manager.pool) == 1
    assert executor_1.id == executor.ExecutorId("agent1", "local:", blueprint1)
    assert executor_1.id in executor_manager.pool
    assert executor_manager.pool[executor_1.id] == executor_1

    assert len(venv_manager.pool) == 1
    assert env_blueprint1.blueprint_hash() in venv_manager.pool
    assert venv_manager.pool[env_blueprint1.blueprint_hash()] == executor_1.process.executor_virtual_env

    # Verify that required packages are installed in the environment
    installed = executor_1.process.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements1)

    # Reusing the same blueprint should reuse the executor without creating a new one
    executor_1_reuse = await executor_manager.get_executor("agent1", "local:", code_for(blueprint1))
    assert executor_1_reuse == executor_1

    assert len(executor_manager.pool) == 1
    assert executor_1_reuse.id == executor.ExecutorId("agent1", "local:", blueprint1)
    assert executor_1_reuse.id in executor_manager.pool
    assert executor_manager.pool[executor_1_reuse.id] == executor_1_reuse

    assert len(venv_manager.pool) == 1
    assert env_blueprint1.blueprint_hash() in venv_manager.pool
    assert venv_manager.pool[env_blueprint1.blueprint_hash()] == executor_1_reuse.process.executor_virtual_env

    # Changing the source without changing the requirements should create a new executor but reuse the environment
    executor_2 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint2))

    assert len(executor_manager.pool) == 2
    assert executor_2.id == executor.ExecutorId("agent1", "local:", blueprint2)
    assert executor_2.id in executor_manager.pool
    assert executor_manager.pool[executor_2.id] == executor_2

    assert len(venv_manager.pool) == 1  # Environment is reused
    assert env_blueprint1.blueprint_hash() in venv_manager.pool
    assert venv_manager.pool[env_blueprint1.blueprint_hash()] == executor_2.process.executor_virtual_env

    # Changing the requirements should necessitate a new environment
    executor_3 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint3))

    assert len(executor_manager.pool) == 3
    assert executor_3.id == executor.ExecutorId("agent1", "local:", blueprint3)
    assert executor_3.id in executor_manager.pool
    assert executor_manager.pool[executor_3.id] == executor_3

    assert len(venv_manager.pool) == 2  # A new environment is created
    assert env_blueprint2.blueprint_hash() in venv_manager.pool
    assert venv_manager.pool[env_blueprint2.blueprint_hash()] == executor_3.process.executor_virtual_env

    installed = executor_3.process.executor_virtual_env.get_installed_packages()
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
    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements, sources=sources, python_version=sys.version_info[:2]
    )
    env_bp_hash1 = blueprint1.to_env_blueprint().blueprint_hash()

    with caplog.at_level(logging.DEBUG):
        # First execution: create an executor and verify its creation
        executor_manager = mp_manager_factory(None)
        venv_manager = executor_manager.process_pool.environment_manager
        await executor_manager.get_executor("agent1", "internal:", code_for(blueprint1))
        assert len(executor_manager.pool) == 1
        assert len(venv_manager.pool) == 1

        env_dir = os.path.join(venv_manager.envs_dir, env_bp_hash1)

        log_doesnt_contain(caplog, "inmanta.agent.executor", logging.INFO, f"Found existing virtual environment at {env_dir}")

        # Simulate ExecutorManager restart by creating new instances of ExecutorManager and VirtualEnvironmentManager
        executor_manager2 = mp_manager_factory(None)
        venv_manager2 = executor_manager2.process_pool.environment_manager
        # Assertions before retrieving the executor to verify a fresh start
        assert len(executor_manager2.pool) == 0
        assert len(venv_manager2.pool) == 0
        # Assertions after retrieval to verify the reuse of virtual environments
        await executor_manager2.get_executor("agent1", "internal:", code_for(blueprint1))
        assert len(executor_manager2.pool) == 1
        assert len(venv_manager2.pool) == 1

        log_contains(caplog, "inmanta.agent.executor", logging.DEBUG, f"Found existing venv for content {str(blueprint1)}")


def with_timeout(delay):
    def decorator(func):
        @functools.wraps(func)
        async def new_func(*args, **kwargs):
            try:
                async with asyncio.timeout(delay):
                    return await func(*args, **kwargs)
            except TimeoutError:
                dump_threads()
                await dump_ioloop_running()
                raise TimeoutError(f"Test case got interrupted, because it didn't finish in {delay} seconds.")

        return new_func

    return decorator


def trace_error_26(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwds):
        try:
            return await func(*args, **kwds)
        except OSError as e:
            if e.errno == 26:
                subprocess.call(["lsof", e.filename], stderr=subprocess.STDOUT, stdout=subprocess.STDOUT)
            raise

    return wrapper


@with_timeout(30)
@trace_error_26
async def test_executor_creation_and_reuse(pip_index: PipIndex, mpmanager_light: forking_executor.MPManager, caplog) -> None:
    """
    This test verifies the creation and reuse of executors based on their blueprints. It checks whether
    the concurrency aspects and the locking mechanisms work as intended.
    """
    # Force log level down, this causes more output on the CI when this fails
    caplog.set_level("DEBUG")

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

    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements1, sources=sources1, python_version=sys.version_info[:2]
    )
    blueprint2 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements1, sources=sources2, python_version=sys.version_info[:2]
    )
    blueprint3 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements2, sources=sources2, python_version=sys.version_info[:2]
    )

    logging.info(
        """
    Blueprint1: hash: %s, env hash: %s,
    Blueprint2: hash: %s, env hash: %s,
    Blueprint3: hash: %s, env hash: %s,
    """,
        blueprint1.blueprint_hash(),
        blueprint1.to_env_blueprint().blueprint_hash(),
        blueprint2.blueprint_hash(),
        blueprint2.to_env_blueprint().blueprint_hash(),
        blueprint3.blueprint_hash(),
        blueprint3.to_env_blueprint().blueprint_hash(),
    )

    executor_manager = mpmanager_light
    executor_1, executor_1_reuse, executor_2, executor_3 = await asyncio.wait_for(
        asyncio.gather(
            executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
            executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
            executor_manager.get_executor("agent1", "local:", code_for(blueprint2)),
            executor_manager.get_executor("agent1", "local:", code_for(blueprint3)),
        ),
        20,
    )

    assert executor_1 is executor_1_reuse, "Expected the same executor instance for identical blueprint"
    assert executor_1 is not executor_2, "Expected a different executor instance for different sources"
    assert executor_1 is not executor_3, "Expected a different executor instance for different requirements and sources"
    assert executor_2 is not executor_3, "Expected different executor instances for different requirements"


@with_timeout(30)
@trace_error_26
async def test_executor_creation_and_venv_usage(
    server_config, pip_index: PipIndex, mpmanager_light: forking_executor.MPManager
) -> None:
    """
    This test verifies the creation and reuse of executors based on their blueprints. It checks whether
    the concurrency aspects and the locking mechanisms work as intended.
    """
    mpmanager_light.process_pool.venv_checkup_interval = 0.1
    requirements1 = ()
    requirements2 = ("pkg1",)
    requirements3 = ("pkg2",)
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
    sources3 = (module_source1,)

    initial_version: tuple[int, int] = (3, 11)

    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements1, sources=sources1, python_version=initial_version
    )
    blueprint2 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements2, sources=sources2, python_version=initial_version
    )
    blueprint3 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements3, sources=sources3, python_version=initial_version
    )

    executor_manager = mpmanager_light
    executor_1, executor_2, executor_3 = await asyncio.gather(
        executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
        executor_manager.get_executor("agent2", "local:", code_for(blueprint2)),
        executor_manager.get_executor("agent3", "local:", code_for(blueprint3)),
    )

    executor_1_venv_status_file = (
        pathlib.Path(executor_1.process.executor_virtual_env.env_path) / const.INMANTA_VENV_STATUS_FILENAME
    )
    executor_2_venv_status_file = (
        pathlib.Path(executor_2.process.executor_virtual_env.env_path) / const.INMANTA_VENV_STATUS_FILENAME
    )
    executor_3_venv_status_file = (
        pathlib.Path(executor_3.process.executor_virtual_env.env_path) / const.INMANTA_VENV_STATUS_FILENAME
    )

    logger.warning("Touching %s now", executor_2_venv_status_file)
    old_datetime = datetime.datetime(year=2022, month=9, day=22, hour=12, minute=51, second=42)
    # This part of the test is a bit subtle because we rely on the fact that there is no context switching between the
    # modification override of the inmanta file and the retrieval of the last modification of the file
    os.utime(
        executor_2_venv_status_file,
        (datetime.datetime.now().timestamp(), old_datetime.timestamp()),
    )

    old_check_executor1 = executor_1.process.executor_virtual_env.last_used
    old_check_executor2 = executor_2.process.executor_virtual_env.last_used

    # We wait for the refresh of the venv status files
    await asyncio.sleep(0.2)
    logger.warning("Sleeping done")

    new_check_executor1 = executor_1.process.executor_virtual_env.last_used
    new_check_executor2 = executor_2.process.executor_virtual_env.last_used

    assert new_check_executor1 > old_check_executor1
    assert new_check_executor2 > old_check_executor2
    assert (datetime.datetime.now().astimezone() - new_check_executor2).seconds <= 2

    async def wait_for_agent_stop_running(executor: MPExecutor) -> bool:
        """
        Wait for the agent to stop running
        """
        return not executor.running

    # Now we want to check if the cleanup is working correctly
    await executor_manager.stop_for_agent("agent1")
    await retry_limited(wait_for_agent_stop_running, executor=executor_1, timeout=10)
    # First we want to override the modification date of the `inmanta_venv_status` file
    os.utime(
        executor_1_venv_status_file, (datetime.datetime.now().astimezone().timestamp(), old_datetime.astimezone().timestamp())
    )
    environment_manager = mpmanager_light.process_pool.environment_manager
    venv_dir = pathlib.Path(environment_manager.envs_dir)
    assert len([e for e in venv_dir.iterdir()]) == 3, "We should have two Virtual Environments for our 2 executors!"
    # We remove the old VirtualEnvironment
    logger.debug("Calling cleanup_virtual_environments")
    await environment_manager.cleanup_inactive_pool_members()
    logger.debug("cleanup_virtual_environments ended")

    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 2, "Only two Virtual Environment should exist!"  # Venv one is gone
    assert [executor_2.process.executor_virtual_env.env_path, executor_3.process.executor_virtual_env.env_path] == venvs

    # Let's stop the other agent and pretend that the venv is broken
    executors = await executor_manager.stop_for_agent("agent2")
    await asyncio.gather(*(e.join() for e in executors))
    await retry_limited(wait_for_agent_stop_running, executor=executor_2, timeout=10)
    executor_2_venv_status_file.unlink()

    await environment_manager.cleanup_inactive_pool_members()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 1, "Only one Virtual Environment should exist!"  # Only nr 3

    # Let's stop the other agent and pretend that the venv is outdated
    executors = await executor_manager.stop_for_agent("agent3")
    await asyncio.gather(*(e.join() for e in executors))
    await retry_limited(wait_for_agent_stop_running, executor=executor_3, timeout=10)
    # This part of the test is a bit subtle because we rely on the fact that there is no context switching between the
    # modification override of the inmanta file and the retrieval of the last modification of the file
    os.utime(
        executor_3_venv_status_file,
        (datetime.datetime.now().timestamp(), old_datetime.timestamp()),
    )
    # A new version would run
    blueprint3_updated = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=requirements3, sources=sources3, python_version=(3, 12)
    )
    await executor_manager.get_executor("agent3", "local:", code_for(blueprint3_updated))
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 2, "Only two Virtual Environment should exist!"

    await mpmanager_light.process_pool.environment_manager.cleanup_inactive_pool_members()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 1, "Only one Environment should exist!"
