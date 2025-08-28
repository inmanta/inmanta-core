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
import base64
import concurrent.futures
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime

import pytest

from inmanta import config, const, data, util
from inmanta.agent import config as agent_config
from inmanta.agent import executor
from inmanta.data import PipConfig
from utils import PipIndex, get_compiler_version, retry_limited, wait_until_deployment_finishes


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


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_remove_executor_virtual_envs(
    clienthelper,
    server,
    client,
    environment,
) -> None:
    """
    Verify the logic to remove all the Python environments used by the executors.
    """
    state_dir = config.Config.get("config", "state-dir")
    venvs_dir = os.path.join(state_dir, "server", environment, "executors", "venvs")
    # Increase the executor retention time so that it doesn't get cleaned up by the cleanup job.
    agent_config.agent_executor_retention_time.set("3600")

    # Disable all time-based deploy triggers
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "0")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "0")
    assert result.code == 200

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "send_event": False,
            "purge_on_delete": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": f"test::Resource[agent2,key=key2],v={version}",
            "send_event": False,
            "purge_on_delete": False,
            "purged": False,
            "requires": [],
        },
    ]
    content = """
import inmanta.agent.handler
import inmanta.resources

@inmanta.resources.resource("test::Resource", agent="agent", id_attribute="key")
class Resource(inmanta.resources.PurgeableResource):
    key: str
    value: str

    fields = ("key", "value")


@inmanta.agent.handler.provider("test::Resource", name="test")
class ResourceH(inmanta.agent.handler.CRUDHandler[Resource]):
    def read_resource(
        self, ctx: inmanta.agent.handler.HandlerContext, resource: Resource
    ) -> None:
        raise inmanta.agent.handler.ResourcePurged()

    def create_resource(
        self, ctx: inmanta.agent.handler.HandlerContext, resource: Resource
    ) -> None:
        ctx.set_created()

    def update_resource(
        self,
        ctx: inmanta.agent.handler.HandlerContext,
        changes: dict,
        resource: Resource,
    ) -> None:
        pass

    def delete_resource(
        self, ctx: inmanta.agent.handler.HandlerContext, resource: Resource
    ) -> None:
        pass

    """

    content_encoded = content.encode()
    content_hash = util.hash_file(content_encoded)
    result = await client.upload_file(id=content_hash, content=base64.b64encode(content_encoded).decode("ascii"))
    assert result.code == 200
    result = await client.upload_code_batched(
        tid=environment,
        id=version,
        resources={"test::Resource": {content_hash: ("inmanta_plugins/test/__init__.py", "inmanta_plugins.test", [])}},
    )
    assert result.code == 200
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200
    await wait_until_deployment_finishes(client, environment, version=version, timeout=10)
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"]["by_state"]["deployed"] == 2

    # Assert we have a Python environment
    assert len(os.listdir(venvs_dir)) == 1

    # Trigger removal of executor venvs
    result = await client.all_agents_action(tid=environment, action=const.AllAgentAction.remove_all_agent_venvs.value)
    assert result.code == 200

    async def venv_removal_finished() -> bool:
        result = await client.list_notifications(tid=environment)
        assert result.code == 200
        return any(n for n in result.result["data"] if n["title"] == "Agent venv removal finished")

    await retry_limited(venv_removal_finished, timeout=10)

    # Assert that the venv was removed
    assert len(os.listdir(venvs_dir)) == 0

    # Verify notifications
    result = await client.list_notifications(tid=environment)
    assert result.code == 200
    start_removal_notification = [n for n in result.result["data"] if n["title"] == "Agent operations suspended"]
    assert len(start_removal_notification) == 1
    end_removal_notification = [n for n in result.result["data"] if n["title"] == "Agent venv removal finished"]
    assert len(end_removal_notification) == 1
    assert not any(n for n in result.result["data"] if n["title"] == "Agent venv removal failed")
    assert datetime.fromisoformat(start_removal_notification[0]["created"]) < datetime.fromisoformat(
        end_removal_notification[0]["created"]
    )

    # Trigger a new deployment
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "new_value",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "send_event": False,
            "purge_on_delete": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "new_value",
            "id": f"test::Resource[agent2,key=key2],v={version}",
            "send_event": False,
            "purge_on_delete": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.upload_code_batched(
        tid=environment,
        id=version,
        resources={"test::Resource": {content_hash: ("inmanta_plugins/test/__init__.py", "inmanta_plugins.test", [])}},
    )
    assert result.code == 200
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200
    await wait_until_deployment_finishes(client, environment, version=version, timeout=10)

    # Verify that deployment was successful
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"]["by_state"]["deployed"] == 2

    # Assert we have a Python environment again
    assert len(os.listdir(venvs_dir)) == 1


async def test_recovery_virtual_environment_manager(tmpdir, pip_index, async_finalizer):
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
    async_finalizer.add(venv_manager.request_shutdown)
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
    async_finalizer.add(venv_manager.request_shutdown)

    # Assert venv1 was removed
    venv_dirs = os.listdir(tmpdir)
    assert venv_dirs == [venv2.folder_name]

    await venv_manager.request_shutdown()
    await venv_manager.join()
