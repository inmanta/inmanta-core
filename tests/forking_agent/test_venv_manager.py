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
import concurrent.futures
import json
import os
import subprocess
import sys
import uuid

import pytest

from inmanta.agent import config as agent_config
from inmanta.agent import executor
from inmanta.data import PipConfig
from utils import PipIndex


async def test_blueprint_hash_consistency(tmpdir):
    """
    Test to verify that the hashing mechanism for EnvBlueprints is consistent across
    different orders of requirements
    """
    env_id = uuid.uuid4()
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    pip_config = PipConfig(index_url=pip_index.url)

    # Define two sets of requirements, identical but in different orders
    requirements1 = ("pkg1", "pkg2")
    requirements2 = ("pkg2", "pkg1")

    blueprint1 = executor.EnvBlueprint(
        environment_id=env_id, pip_config=pip_config, requirements=requirements1, python_version=sys.version_info[:2]
    )
    blueprint2 = executor.EnvBlueprint(
        environment_id=env_id, pip_config=pip_config, requirements=requirements2, python_version=sys.version_info[:2]
    )

    hash1 = blueprint1.blueprint_hash()
    hash2 = blueprint2.blueprint_hash()

    assert hash1 == hash2, "Blueprint hashes should be identical regardless of the order of requirements"


async def test_environment_isolation(tmpdir):
    """
    Ensure that venvs with the same specification on different Inmanta environments result in a different hash
    (i.e. use a different on disk Python environment).
    """
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    pip_config = PipConfig(index_url=pip_index.url)
    requirements = ("pkg1", "pkg2")

    blueprint1 = executor.EnvBlueprint(
        environment_id=uuid.uuid4(), pip_config=pip_config, requirements=requirements, python_version=sys.version_info[:2]
    )
    blueprint2 = executor.EnvBlueprint(
        environment_id=uuid.uuid4(), pip_config=pip_config, requirements=requirements, python_version=sys.version_info[:2]
    )

    hash1 = blueprint1.blueprint_hash()
    hash2 = blueprint2.blueprint_hash()

    assert hash1 != hash2


@pytest.mark.slowtest
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
    env_id = uuid.uuid4()
    pip_config_dict = {"index_url": "http://example.com", "extra_index_url": [], "pre": None, "use_system_config": False}
    requirements = ["pkg1", "pkg2"]

    # Serialize the configuration for passing to the subprocess
    config_str = json.dumps({"pip_config": pip_config_dict, "requirements": requirements})

    # Python code to execute in subprocess
    python_code = f"""import json
import uuid
import sys
from inmanta.agent.executor import EnvBlueprint, PipConfig

config_str = '''{config_str}'''
config = json.loads(config_str)

pip_config = PipConfig(**config["pip_config"])
blueprint = EnvBlueprint(
    environment_id=uuid.UUID("{env_id}"),
    pip_config=pip_config,
    requirements=config["requirements"],
    python_version=sys.version_info[:2],
)

# Generate and print the hash
print(blueprint.blueprint_hash())
    """

    # Generate hash in the current session for comparison
    pip_config = PipConfig(**pip_config_dict)
    current_session_blueprint = executor.EnvBlueprint(
        environment_id=env_id, pip_config=pip_config, requirements=requirements, python_version=sys.version_info[:2]
    )
    current_hash = current_session_blueprint.blueprint_hash()

    # Generate hash in a new interpreter session
    result = subprocess.run([sys.executable, "-c", python_code], capture_output=True, text=True)

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
    env_id = uuid.uuid4()
    manager = executor.VirtualEnvironmentManager(
        envs_dir=tmpdir,
        thread_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
        ),
    )

    blueprint1 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(index_url=pip_index.url),
        requirements=("pkg1",),
        python_version=sys.version_info[:2],
    )
    blueprint2 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(index_url=pip_index.url),
        requirements=(),
        python_version=sys.version_info[:2],
    )

    # Wait for all tasks to complete
    env_same_1, env_same_2, env_diff_1 = await asyncio.gather(
        manager.get_environment(blueprint1),
        manager.get_environment(
            blueprint1,
        ),
        manager.get_environment(blueprint2),
    )

    assert env_same_1 is env_same_2, "Expected the same instance for the same blueprint"
    assert env_same_1 is not env_diff_1, "Expected different instances for different blueprints"

    # Start another one, to see they initialize well
    venv_manager_2 = executor.VirtualEnvironmentManager(
        envs_dir=tmpdir,
        thread_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
        ),
    )

    await venv_manager_2.start()
    assert manager.pool.keys() == venv_manager_2.pool.keys()
    await venv_manager_2.request_shutdown()


async def test_recovery_virtual_environment_manager(tmpdir, pip_index):
    """
    Verify that the VirtualEnvironmentManager removes venvs that were not correctly initialized.
    """
    # Make sure there is no interference with the job that cleans up unused venvs.
    assert agent_config.executor_venv_retention_time.get() >= 3600

    venv_manager = executor.VirtualEnvironmentManager(
        envs_dir=tmpdir,
        thread_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
        ),
    )
    await venv_manager.start()
    env_id = uuid.uuid4()
    pip_config = PipConfig(index_url=pip_index.url)
    blueprint1 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=("pkg1",),
        python_version=sys.version_info[:2],
    )
    blueprint2 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=sys.version_info[:2],
    )
    venv1, venv2 = await asyncio.gather(
        venv_manager.get_environment(blueprint1),
        venv_manager.get_environment(blueprint2),
    )
    await venv_manager.request_shutdown()
    await venv_manager.join()

    assert len(os.listdir(tmpdir)) == 2

    # Make venv1 corrupt
    os.remove(venv1.inmanta_venv_status_file)

    venv_manager = executor.VirtualEnvironmentManager(
        envs_dir=tmpdir,
        thread_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
        ),
    )
    await venv_manager.start()

    venv_dirs = os.listdir(tmpdir)
    assert venv_dirs == [venv2.folder_name]
