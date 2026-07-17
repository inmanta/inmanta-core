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
import datetime
import hashlib
import logging
import pathlib
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import psutil
import pytest

import inmanta.agent
import inmanta.agent.executor
import inmanta.config
import inmanta.data
import inmanta.loader
import inmanta.protocol.ipc_light
import inmanta.util
import utils
from forking_agent.ipc_commands import Echo, GetConfig, GetName, TestLoader
from inmanta.agent import executor
from inmanta.agent.executor import EditableModuleInstall, ExecutorBlueprint, ExecutorVirtualEnvironment
from inmanta.agent.forking_executor import MPExecutor, MPManager
from inmanta.data import PipConfig
from inmanta.data.model import ExecutorModuleSource, ModuleSource, ModuleSourceMetadata
from inmanta.protocol.ipc_light import ConnectionLost
from utils import NOISY_LOGGERS, log_contains, retry_limited


def test_reconstruct_editable_module(tmp_path):
    """
    Reconstructing an editable module lays out its python sources as packages (dirs with an __init__ file) under a
    top-level inmanta_plugins namespace package (which itself gets no __init__ file), and writes its packaging files
    at the module root. The byte-code flag selects the __init__ file extension.
    """

    def source(name: str, content: bytes, *, is_byte_code: bool = False) -> ModuleSource:
        return ModuleSource(
            metadata=ModuleSourceMetadata(name=name, hash_value=hashlib.sha1(content).hexdigest(), is_byte_code=is_byte_code),
            source=content,
        )

    editable_module = EditableModuleInstall(
        name="my_mod",
        version="deadbeef",
        python_module_sources=[
            source("inmanta_plugins.my_mod", b"# root"),
            source("inmanta_plugins.my_mod.handlers", b"# handlers"),
            source("inmanta_plugins.my_mod.compiled", b"byte-code", is_byte_code=True),
        ],
        setup_cfg=b"[metadata]\nname = inmanta-module-my_mod\n",
        pyproject_toml=b"[build-system]\n",
    )

    with ThreadPoolExecutor() as thread_pool:
        venv = ExecutorVirtualEnvironment(env_path=str(tmp_path / "venv"), io_threadpool=thread_pool)
        module_root = venv._reconstruct_editable_module(editable_module)

    root = pathlib.Path(module_root)
    assert root == venv.inmanta_editable_dir / "my_mod"

    # The top-level namespace package must not get an __init__ file.
    assert not (root / "inmanta_plugins" / "__init__.py").exists()
    assert not (root / "inmanta_plugins" / "__init__.pyc").exists()

    # Every python module is materialized as a package, honoring the byte-code flag.
    assert (root / "inmanta_plugins" / "my_mod" / "__init__.py").read_bytes() == b"# root"
    assert (root / "inmanta_plugins" / "my_mod" / "handlers" / "__init__.py").read_bytes() == b"# handlers"
    assert (root / "inmanta_plugins" / "my_mod" / "compiled" / "__init__.pyc").read_bytes() == b"byte-code"

    # The packaging files land at the module root.
    assert (root / "setup.cfg").read_bytes() == b"[metadata]\nname = inmanta-module-my_mod\n"
    assert (root / "pyproject.toml").read_bytes() == b"[build-system]\n"


def test_reconstruct_editable_module_without_pyproject(tmp_path):
    """
    A module may ship a setup.cfg but no pyproject.toml (setup.cfg is mandatory for a V2 module, pyproject.toml is not,
    and get_metadata_files only returns files that exist). Such a module reconstructs its sources and setup.cfg without
    writing a pyproject.toml.
    """
    editable_module = EditableModuleInstall(
        name="my_mod",
        version="cafe",
        python_module_sources=[
            ModuleSource(
                metadata=ModuleSourceMetadata(name="inmanta_plugins.my_mod", hash_value="abc", is_byte_code=False),
                source=b"# root",
            )
        ],
        setup_cfg=b"[metadata]\nname = inmanta-module-my_mod\n",
        pyproject_toml=None,
    )

    with ThreadPoolExecutor() as thread_pool:
        venv = ExecutorVirtualEnvironment(env_path=str(tmp_path / "venv"), io_threadpool=thread_pool)
        module_root = pathlib.Path(venv._reconstruct_editable_module(editable_module))

    assert (module_root / "inmanta_plugins" / "my_mod" / "__init__.py").read_bytes() == b"# root"
    assert (module_root / "setup.cfg").read_bytes() == b"[metadata]\nname = inmanta-module-my_mod\n"
    assert not (module_root / "pyproject.toml").exists()


@pytest.fixture
def set_custom_executor_policy(server_config):
    """
    Fixture to temporarily set the policy for executor management.
    """
    old_cap_value = inmanta.agent.config.agent_executor_cap.get()

    # Keep only 2 executors per agent
    inmanta.agent.config.agent_executor_cap.set("2")

    old_retention_value = inmanta.agent.config.agent_executor_retention_time.get()
    # Clean up executors after 3s of inactivity
    inmanta.agent.config.agent_executor_retention_time.set("3")

    yield

    inmanta.agent.config.agent_executor_cap.set(str(old_cap_value))
    inmanta.agent.config.agent_executor_retention_time.set(str(old_retention_value))


async def test_executor_server(set_custom_executor_policy, mpmanager: MPManager, client, environment, caplog):
    """
    Test the MPManager, this includes

    1. copying of config
    2. building up an empty venv
    3. communicate with it
    4. build up venv with requirements, source files, ...
    5. check that code is loaded correctly

    Also test that an executor policy can be set:
        - the agent_executor_cap option correctly stops the oldest executor.
        - the agent_executor_retention_time option is used to clean up old executors.
    """

    with pytest.raises(ImportError):
        # make sure lorem isn't installed at the start of the test.
        import lorem  # noqa: F401

    manager = mpmanager
    await manager.start()

    inmanta.config.Config.set("test", "aaa", "bbbb")

    empty_source_content = "".encode("utf-8")
    empty_source = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test.empty",
            hash_value=inmanta.util.hash_file(empty_source_content),
            is_byte_code=False,
        ),
        source=empty_source_content,
        install_on_disk=True,
        load_module=True,
    )

    # Simple empty venv
    simplest_blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(),
        requirements=[],
        sources=[empty_source],
        python_version=sys.version_info[:2],
    )  # No pip
    simplest = await manager.get_executor(
        "agent1",
        "test",
        [executor.InmantaModuleInstallSpec("test", "123456", simplest_blueprint)],
    )

    # check communications
    result = await simplest.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    # check config copying from parent to child
    result = await simplest.call(GetConfig("test", "aaa"))
    assert "bbbb" == result

    # Make a more complete venv
    # Direct: source is sent over directly
    direct_content = """
def test():
   return "DIRECT"
    """.encode("utf-8")
    direct = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test.testA",
            hash_value=inmanta.util.hash_file(direct_content),
            is_byte_code=False,
        ),
        source=direct_content,
        install_on_disk=True,
        load_module=True,
    )
    # Via server: source is sent via server
    server_content = """
def test():
   return "server"
""".encode("utf-8")
    server_content_hash = inmanta.util.hash_file(server_content)
    via_server = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test.testB",
            hash_value=server_content_hash,
            is_byte_code=False,
        ),
        source=server_content,
        install_on_disk=True,
        load_module=True,
    )
    # Upload
    res = await client.upload_file(id=server_content_hash, content=base64.b64encode(server_content).decode("ascii"))
    assert res.code == 200

    # Dummy executor to test executor cap:
    # Create this one first to make sure this is the one being stopped
    # when the cap is reached
    dummy = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[direct],
        python_version=sys.version_info[:2],
    )
    # Full config: 2 source files, one python dependency
    full = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[direct, via_server],
        python_version=sys.version_info[:2],
    )

    # Full runner install requires pip install, this can be slow, so we build it first to prevent the other one from timing out
    oldest_executor = await manager.get_executor("agent2", "internal:", [executor.InmantaModuleInstallSpec("test", 1, dummy)])
    full_runner = await manager.get_executor(
        "agent2",
        "internal:",
        [executor.InmantaModuleInstallSpec("test:DDD:Test", 1, full)],
    )

    assert oldest_executor.id in manager.pool

    # assert loaded
    result2 = await full_runner.call(TestLoader())
    assert ["DIRECT", "server"] == result2

    # assert they are distinct
    assert await simplest.call(GetName()) == simplest_blueprint.blueprint_hash()
    assert await full_runner.call(GetName()) == full.blueprint_hash()

    # Request a third executor:
    # The executor cap is reached -> check that the oldest executor got correctly stopped
    dummy = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[via_server],
        python_version=sys.version_info[:2],
    )

    async def oldest_gone():
        return oldest_executor not in manager.agent_map["agent2"]

    with caplog.at_level(logging.DEBUG):
        _ = await manager.get_executor(
            "agent2",
            "internal:",
            [executor.InmantaModuleInstallSpec("test::Test", "1", dummy)],
        )
        assert not oldest_executor.running
        assert full_runner.running
        await retry_limited(oldest_gone, 1)
        log_contains(
            caplog,
            "inmanta.executor",
            logging.DEBUG,
            ("Reached executor cap for agent agent2. Stopping oldest executor "),
        )

    # Assert shutdown and back up
    stopped = await mpmanager.stop_for_agent("agent2")
    # prevent leaking futures
    for x in stopped:
        await x.join()
    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 0, 10)

    full_runner = await manager.get_executor(
        "agent2",
        "internal:",
        [executor.InmantaModuleInstallSpec("test::Test", "1", full)],
    )

    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 1, 1)

    await simplest.request_shutdown()
    await simplest.join()

    async def check_connection_lost() -> bool:
        return await simplest.call(GetName()) != simplest_blueprint.blueprint_hash()

    with pytest.raises(ConnectionLost):
        await retry_limited(check_connection_lost, 1)

    with pytest.raises(ImportError):
        # we aren't leaking into this venv
        import lorem  # noqa: F401, F811

    async def check_automatic_clean_up() -> bool:
        return len(manager.agent_map["agent2"]) == 0

    assert len(manager.agent_map["agent2"]) != 0

    with caplog.at_level(logging.DEBUG):
        await retry_limited(check_automatic_clean_up, 10)
        log_contains(
            caplog,
            "inmanta.agent.resourcepool",
            logging.DEBUG,
            ("executor for agent2 will be shutdown because it was inactive for "),
        )

    # We can get `Caught subprocess termination from unknown pid: %d -> %d`
    # When we capture signals from the pip installs
    # Can't happen in real deployment as these things happen in different processes
    utils.assert_no_warning(caplog, NOISY_LOGGERS + ["asyncio"])


async def test_executor_server_dirty_shutdown(mpmanager: MPManager, caplog):
    caplog.clear()
    manager = mpmanager

    # A single standalone module for the blueprint
    code = b"# Empty source"
    sha1sum = hashlib.new("sha1")
    sha1sum.update(code)
    module_source = ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.bp1",
            hash_value=sha1sum.hexdigest(),
            is_byte_code=False,
        ),
        source=code,
        install_on_disk=True,
        load_module=True,
    )

    blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=[],
        sources=[module_source],
        python_version=sys.version_info[:2],
    )
    child1 = await manager.get(executor.ExecutorId("test", "Test", blueprint))

    result = await child1.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    print("Child there")

    process_name = psutil.Process(pid=child1.process.process.pid).name()
    assert process_name == f"inmanta: executor process {blueprint.blueprint_hash()} - connected"

    await asyncio.get_running_loop().run_in_executor(None, child1.process.process.kill)
    print("Kill sent")

    try:
        await asyncio.get_running_loop().run_in_executor(None, child1.process.process.join)
    except ValueError:
        # to be expected
        logging.exception("Process already gone!")
    print("Child gone")

    with pytest.raises(ConnectionLost):
        await child1.call(Echo(["aaaa"]))

    utils.assert_no_warning(caplog)


async def test_executor_call_refreshes_last_used():
    """
    Regression test: MPExecutor.call() must refresh the pool member's `last_used` timestamp via touch().
    """

    class FakeConnection:
        async def call(self, method):
            return "called"

    class FakeProcess:
        def __init__(self) -> None:
            self.connection = FakeConnection()

    blueprint = ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=PipConfig(),
        requirements=[],
        sources=[],
        python_version=sys.version_info[:2],
    )
    mp_executor = MPExecutor(FakeProcess(), executor.ExecutorId("agent1", "local:", blueprint))

    # Pretend the executor has been idle for a long time
    dummy_last_used = datetime.datetime.now().astimezone() - datetime.timedelta(hours=1)
    mp_executor._last_used = dummy_last_used
    assert mp_executor.get_idle_time() >= datetime.timedelta(hours=1)

    start_time_call = datetime.datetime.now().astimezone()
    assert await mp_executor.call(Echo(["x"])) == "called"
    end_time_call = datetime.datetime.now().astimezone()

    # call() must have refreshed the last_used timestamp
    assert mp_executor.get_idle_time() < datetime.timedelta(seconds=5)
    assert start_time_call <= mp_executor.last_used <= end_time_call
    # Verify in-flight bookkeeping is done correctly
    assert mp_executor.in_flight == 0


def test_hash_with_duplicates():
    env_id = uuid.uuid4()
    source = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="test",
            hash_value="aaaaa",
            is_byte_code=False,
        ),
        source="foo".encode(),
        install_on_disk=True,
        load_module=True,
    )
    requirement = "setuptools"
    simple = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement],
        sources=[source],
        python_version=sys.version_info[:2],
    )
    duplicated = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement, requirement],
        sources=[source, source],
        python_version=sys.version_info[:2],
    )
    assert duplicated == simple
    assert duplicated.blueprint_hash() == simple.blueprint_hash()


def test_from_specs_rejects_spec_without_sources():
    """
    An install spec describes a single inmanta module, which always ships at least one python file.
    from_specs derives the install mode from those sources, so a spec without any must be rejected
    with a clear error rather than failing with an opaque IndexError.
    """
    env_id = uuid.uuid4()
    source = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test",
            hash_value="aaaaa",
            is_byte_code=False,
        ),
        source=b"a = 1",
        install_on_disk=True,
        load_module=True,
    )

    def make_spec(
        module_name: str, sources: list[inmanta.data.model.ExecutorModuleSource]
    ) -> executor.InmantaModuleInstallSpec:
        return executor.InmantaModuleInstallSpec(
            module_name=module_name,
            module_version="1.0",
            blueprint=ExecutorBlueprint(
                environment_id=env_id,
                pip_config=PipConfig(),
                requirements=[],
                sources=sources,
                python_version=sys.version_info[:2],
            ),
        )

    # A spec with no sources is rejected with a clear error naming the offending module.
    with pytest.raises(ValueError, match="empty_module has no sources"):
        ExecutorBlueprint.from_specs([make_spec("ok_module", [source]), make_spec("empty_module", [])])

    # Sanity check: a spec with at least one source is accepted.
    blueprint = ExecutorBlueprint.from_specs([make_spec("ok_module", [source])])
    assert blueprint.sources == [source]
