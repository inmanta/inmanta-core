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
import dataclasses
import datetime
import hashlib
import importlib
import logging
import os
import pathlib
import sys
import uuid
from collections.abc import Iterator, Sequence
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
from forking_agent.ipc_commands import Echo, GetConfig, GetName, ImportModule, IsModuleLoaded, TestLoader
from inmanta import const
from inmanta.agent import executor
from inmanta.agent.executor import EditableModuleInstall, ExecutorBlueprint, ExecutorVirtualEnvironment, OnDiskCodeInstall
from inmanta.agent.forking_executor import MPExecutor, MPManager
from inmanta.data import PipConfig
from inmanta.data.model import ModuleSource, ModuleSourceMetadata
from inmanta.protocol.ipc_light import ConnectionLost
from packaging.version import Version
from utils import NOISY_LOGGERS, log_contains, retry_limited


def make_source(path: str, content: bytes) -> ModuleSource:
    """Build the python file at the given path of a module's python package tree."""
    return ModuleSource(
        metadata=ModuleSourceMetadata(path=path, hash_value=hashlib.sha1(content).hexdigest()),
        source=content,
    )


@dataclasses.dataclass
class MockedExecutorVenv:
    """
    An executor venv whose venv creation and pip calls are mocked out, for unit tests of what it writes to disk and hands
    to pip. install_calls records the keyword arguments of every pip call.
    """

    venv: ExecutorVirtualEnvironment
    install_calls: list[dict[str, object]]


@pytest.fixture
def mocked_executor_venv(tmp_path, monkeypatch) -> Iterator[MockedExecutorVenv]:
    install_calls: list[dict[str, object]] = []

    async def _noop_install(**kwargs: object) -> None:
        install_calls.append(kwargs)

    with ThreadPoolExecutor() as thread_pool:
        venv = ExecutorVirtualEnvironment(env_path=str(tmp_path / "venv"), io_threadpool=thread_pool)
        monkeypatch.setattr(venv, "init_env", lambda: None)
        monkeypatch.setattr(venv, "async_install_for_config", _noop_install)
        yield MockedExecutorVenv(venv=venv, install_calls=install_calls)


async def test_rebuild_editable_module(mocked_executor_venv: MockedExecutorVenv, caplog):
    """
    Rebuilding an editable module writes every one of its files at the path it has in the module's python package tree,
    so the rebuilt tree has exactly the shape of the one it was exported from: a package that consists of its __init__.py
    alone stays a package, a plain module next to it stays a plain module, byte code keeps its extension, and the
    top-level inmanta_plugins namespace package gets no __init__ file. Creating the venv hands the rebuilt tree to pip as
    an editable install, and logs it explicitly.
    """
    files: dict[str, bytes] = {
        "inmanta_plugins/my_mod/__init__.py": b"# root",
        "inmanta_plugins/my_mod/handlers.py": b"# handlers",
        "inmanta_plugins/my_mod/compiled.pyc": b"byte-code",
        # A plugin submodule named "model". A module installed as a package ships its .cf files in a model/ directory,
        # which the executor skips when it discovers python files. Written as model.py, this submodule is still
        # discovered and loaded.
        "inmanta_plugins/my_mod/model.py": b"# model",
        # A package that consists of its __init__.py alone
        "inmanta_plugins/my_mod/sub/__init__.py": b"# sub",
        "inmanta_plugins/my_mod/other/__init__.py": b"# other",
        "inmanta_plugins/my_mod/other/leaf.py": b"# leaf",
    }
    editable_module = EditableModuleInstall(
        name="my_mod",
        version="deadbeef",
        python_module_sources=[make_source(path, content) for path, content in files.items()],
        packaging_files=[("setup.cfg", b"[metadata]\nname = inmanta-module-my_mod\n"), ("pyproject.toml", b"[build-system]\n")],
    )

    blueprint = executor.EnvBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=PipConfig(),
        requirements=[],
        python_version=sys.version_info[:2],
        editable_modules=[editable_module],
    )
    with caplog.at_level(logging.INFO):
        await mocked_executor_venv.venv._create_and_install_environment(blueprint)

    # The editable module is rebuilt and handed to pip as an editable install.
    (install_call,) = mocked_executor_venv.install_calls
    (editable_path,) = install_call["paths"]
    assert editable_path.editable
    root = pathlib.Path(editable_path.path)
    assert root == mocked_executor_venv.venv.inmanta_editable_dir / "my_mod"

    # Every file is written at its exact path, and nothing else is written: in particular, the top-level namespace
    # package gets no __init__ file.
    assert sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()) == sorted(
        [*files, "setup.cfg", "pyproject.toml"]
    )
    for path, content in files.items():
        assert (root / path).read_bytes() == content
    assert (root / "setup.cfg").read_bytes() == b"[metadata]\nname = inmanta-module-my_mod\n"
    assert (root / "pyproject.toml").read_bytes() == b"[build-system]\n"

    # The editable install is logged explicitly.
    log_contains(caplog, "inmanta.agent.executor", logging.INFO, "Installing 1 inmanta module(s) in editable mode: my_mod")


@pytest.mark.parametrize("with_editable_module", [True, False])
async def test_create_environment_build_isolation(mocked_executor_venv: MockedExecutorVenv, with_editable_module: bool) -> None:
    """
    The rebuilt editable modules are built with the setuptools of the agent's environment, which needs no index, so the
    pip call that installs them turns build isolation off. The flag applies to the whole pip call, so a venv without
    editable modules keeps pip's default isolated builds.
    """
    editable_modules: list[EditableModuleInstall] = (
        [
            EditableModuleInstall(
                name="my_mod",
                version="deadbeef",
                python_module_sources=[make_source("inmanta_plugins/my_mod/__init__.py", b"# root")],
                packaging_files=[("setup.cfg", b"[metadata]\nname = inmanta-module-my_mod\n")],
            )
        ]
        if with_editable_module
        else []
    )

    await mocked_executor_venv.venv._create_and_install_environment(
        executor.EnvBlueprint(
            environment_id=uuid.uuid4(),
            pip_config=PipConfig(),
            requirements=["lorem"],
            python_version=sys.version_info[:2],
            editable_modules=editable_modules,
        )
    )

    (install_call,) = mocked_executor_venv.install_calls
    assert install_call["no_build_isolation"] is with_editable_module


def test_rebuild_editable_module_without_pyproject(mocked_executor_venv: MockedExecutorVenv):
    """
    A module may ship a setup.cfg but no pyproject.toml (setup.cfg is mandatory for a V2 module, pyproject.toml is not,
    and the exporter only transports the packaging files that exist). Such a module is rebuilt with the default pyproject.toml:
    pip refuses to install a source tree in editable mode without one.
    """
    editable_module = EditableModuleInstall(
        name="my_mod",
        version="cafe",
        python_module_sources=[make_source("inmanta_plugins/my_mod/__init__.py", b"# root")],
        packaging_files=[("setup.cfg", b"[metadata]\nname = inmanta-module-my_mod\n")],
    )

    module_root = pathlib.Path(mocked_executor_venv.venv._rebuild_editable_module(editable_module))

    assert (module_root / "inmanta_plugins" / "my_mod" / "__init__.py").read_bytes() == b"# root"
    assert (module_root / "setup.cfg").read_bytes() == b"[metadata]\nname = inmanta-module-my_mod\n"
    assert (module_root / "pyproject.toml").read_bytes() == const.DEFAULT_PYPROJECT_TOML


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


async def test_executor_server_iso9_compatibility_layer(
    set_custom_executor_policy, mpmanager: MPManager, client, environment, caplog
):
    """
    This test covers the on-disk install path of CodeLoader.deploy_and_load: the source that is transported for a model
    version exported by an iso<10 orchestrator is written to disk and imported from there. This path, and this test, can
    be removed in iso11.

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

    empty_source = make_source("inmanta_plugins/test/empty.py", b"")

    # Simple empty venv
    simplest_blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(),
        requirements=[],
        python_version=sys.version_info[:2],
        # A model version that was exported by an iso<10 orchestrator loads every module registered for the agent
        inmanta_modules_to_load=["test"],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[empty_source]),
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
    # Fetch the name now, while the executor is guaranteed to be alive. Asserting on it later would
    # require a live call that can fail with ConnectionLost if the executor got cleaned up for inactivity
    # during the slow pip install of the full executor below.
    simplest_name = await simplest.call(GetName())

    # Make a more complete venv
    # Direct: source is sent over directly
    direct_content = """
def test():
   return "DIRECT"
    """.encode("utf-8")
    direct = make_source("inmanta_plugins/test/testA.py", direct_content)
    # Via server: source is sent via server
    server_content = """
def test():
   return "server"
""".encode("utf-8")
    server_content_hash = inmanta.util.hash_file(server_content)
    via_server = make_source("inmanta_plugins/test/testB.py", server_content)
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
        python_version=sys.version_info[:2],
        inmanta_modules_to_load=["test"],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[direct]),
    )
    # Full config: 2 source files, one python dependency
    full = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        python_version=sys.version_info[:2],
        inmanta_modules_to_load=["test"],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[direct, via_server]),
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
    assert simplest_name == simplest_blueprint.blueprint_hash()
    assert await full_runner.call(GetName()) == full.blueprint_hash()

    # Request a third executor:
    # The executor cap is reached -> check that the oldest executor got correctly stopped
    dummy = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        python_version=sys.version_info[:2],
        inmanta_modules_to_load=["test"],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[via_server]),
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


async def test_executor_server_iso10_editable_install(mpmanager: MPManager, caplog):
    """
    iso10+ code install through a real forking executor. An inmanta module whose files are transported is carried in the
    blueprint as an EditableModuleInstall. On the agent side it is rebuilt as an installable python package and pip
    installed in editable mode into the executor venv, then imported straight from that venv by discovering its python
    files there (so the legacy PluginModuleFinder is never configured).

    This is the iso10 counterpart of test_executor_server_iso9_compatibility_layer: it covers the rebuild -> editable
    install -> import from venv path end-to-end rather than in unit isolation.
    """
    module_name = "iso10editable"
    fq_module_name = f"inmanta_plugins.{module_name}"

    with pytest.raises(ImportError):
        # The module must not be importable in the test process: it only ever gets installed in the executor venv.
        importlib.import_module(fq_module_name)

    manager = mpmanager
    await manager.start()

    # A minimal but valid, pip-installable V2 module. Its __init__.py exposes a test() function we can call from inside
    # the executor process to prove the module was installed and imported from the venv.
    editable_module = utils.make_editable_inmanta_module(
        module_name,
        f"def test():\n    return {module_name!r}\n",
        # A plugin submodule named "model". A module installed as a package ships its .cf files in a model/ directory,
        # which the executor skips when it discovers python files. The rebuild writes this submodule as model.py, so
        # that it is still discovered and loaded.
        submodules={"model": "VALUE = 'model'\n"},
    )

    # The module travels as an EditableModuleInstall and its code is loaded out of the venv it is installed in.
    # inmanta_modules_to_load asks the executor to load it.
    blueprint = ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        # No index at all: the editable module is built with the setuptools of the agent's environment.
        pip_config=PipConfig(),
        requirements=[],
        inmanta_modules_to_load=[module_name],
        python_version=sys.version_info[:2],
        editable_modules=[editable_module],
    )

    # get_executor builds the venv (rebuild + editable install) and loads the code. It raises if either fails, so a
    # successful call already asserts the install and import succeeded.
    with caplog.at_level(logging.INFO):
        my_executor = await manager.get_executor(
            "agent1",
            "internal:",
            [executor.InmantaModuleInstallSpec(module_name, editable_module.version, blueprint)],
        )

    # The code install discovered the python files of the module in the venv and imported them by itself.
    assert await my_executor.call(IsModuleLoaded(fq_module_name))
    assert await my_executor.call(IsModuleLoaded(f"{fq_module_name}.model"))
    # The editable module was imported straight from the executor venv and its code runs there.
    assert await my_executor.call(ImportModule(fq_module_name)) == module_name

    # The rebuilt module was pip installed in editable mode; this is logged explicitly during venv creation.
    log_contains(
        caplog,
        "inmanta.agent.executor",
        logging.INFO,
        f"Installing 1 inmanta module(s) in editable mode: {module_name}",
    )

    # The module did not leak into the test process: it lives only in the executor venv.
    with pytest.raises(ImportError):
        importlib.import_module(fq_module_name)


async def test_executor_server_iso10_package_install(mpmanager: MPManager, modules_v2_dir, tmp_path, caplog):
    """
    iso10+ code install through a real forking executor for a module installed in *package* mode (as opposed to the
    editable mode covered by test_executor_server_iso10_editable_install). The module is published to a local pip index
    and added to the executor venv as a regular pip requirement, then imported straight from the venv by discovering its
    python files there (so the legacy PluginModuleFinder is never configured).
    """
    module_name = "iso10pkg"
    fq_module_name = f"inmanta_plugins.{module_name}"
    module_version = "1.0.0"

    with pytest.raises(ImportError):
        # The module must not be importable in the test process: it only ever gets installed in the executor venv.
        importlib.import_module(fq_module_name)

    # Publish the module as an installable V2 package to a local pip index. Its inmanta_plugins package exposes a test()
    # function we can call from inside the executor process to prove it was installed and imported there.
    pip_index = utils.PipIndex(artifact_dir=str(tmp_path / "pip-index"))
    utils.module_from_template(
        source_dir=os.path.join(modules_v2_dir, "minimalv2module"),
        dest_dir=str(tmp_path / module_name),
        new_name=module_name,
        new_version=Version(module_version),
        new_content_init_py=f"def test():\n    return {module_name!r}\n",
        publish_index=pip_index,
    )

    manager = mpmanager
    await manager.start()

    # A package install module ships no source at all: the module package itself is the pip requirement to install and
    # its python files are discovered in the venv when inmanta_modules_to_load asks the executor to load it.
    blueprint = ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=PipConfig(index_url=pip_index.url),
        requirements=[f"inmanta-module-{module_name}=={module_version}"],
        inmanta_modules_to_load=[module_name],
        python_version=sys.version_info[:2],
    )

    # get_executor builds the venv (pip install from the index) and loads the code. It raises if either fails, so a
    # successful call already asserts the install and import succeeded.
    with caplog.at_level(logging.INFO):
        my_executor = await manager.get_executor(
            "agent1",
            "internal:",
            [executor.InmantaModuleInstallSpec(module_name, module_version, blueprint)],
        )

    # The code install discovered the python files of the module in the venv and imported them by itself.
    assert await my_executor.call(IsModuleLoaded(fq_module_name))
    # The module was installed from the index and imported straight from the executor venv, and its code runs there.
    assert await my_executor.call(ImportModule(fq_module_name)) == module_name

    # The module did not leak into the test process: it lives only in the executor venv.
    with pytest.raises(ImportError):
        importlib.import_module(fq_module_name)


async def test_executor_server_dirty_shutdown(mpmanager: MPManager, caplog):
    caplog.clear()
    manager = mpmanager

    # A single standalone module for the blueprint
    module_source = make_source("inmanta_plugins/bp1/__init__.py", b"# Empty source")

    blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=[],
        python_version=sys.version_info[:2],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[module_source]),
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
    source = make_source("inmanta_plugins/my_mod/__init__.py", b"foo")
    requirement = "setuptools"
    editable_module = EditableModuleInstall(
        name="my_mod",
        version="deadbeef",
        python_module_sources=[source],
        packaging_files=[("setup.cfg", b"[metadata]\nname = inmanta-module-my_mod\n")],
    )
    simple = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement],
        python_version=sys.version_info[:2],
        editable_modules=[editable_module],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[source]),
    )
    duplicated = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement, requirement],
        python_version=sys.version_info[:2],
        editable_modules=[editable_module, editable_module],
        legacy_on_disk_code_install=OnDiskCodeInstall(module_sources=[source, source]),
    )
    assert duplicated == simple
    assert duplicated.blueprint_hash() == simple.blueprint_hash()
    # The duplicate is dropped outright, so the module is rebuilt and handed to pip once.
    assert duplicated.editable_modules == [editable_module]
    # The venv the executor pools on has to agree, or the two would be keyed differently.
    assert duplicated.to_env_blueprint() == simple.to_env_blueprint()
    assert duplicated.to_env_blueprint().blueprint_hash() == simple.to_env_blueprint().blueprint_hash()


def test_from_specs_merges_install_modes():
    """
    from_specs merges the install specs of modules of any install mode into a single blueprint: an editable module,
    which ships the module to rebuild and install in editable mode, a package installed module, which ships a pip
    requirement, and a module of unknown install mode, which ships its python files and its requirements to be
    installed on disk. The first two are loaded out of the venv, the last one from disk.
    """
    env_id = uuid.uuid4()
    editable_module = EditableModuleInstall(
        name="editable_module",
        version="aaaaa",
        python_module_sources=[make_source("inmanta_plugins/editable_module/__init__.py", b"a = 1")],
        packaging_files=[("setup.cfg", b"[metadata]\nname = inmanta-module-editable-module\n")],
    )

    def make_spec(
        module_name: str,
        *,
        on_disk_module_sources: Sequence[ModuleSource] | None = None,
        requirements: Sequence[str] = (),
        inmanta_modules_to_load: Sequence[str] = (),
        editable_modules: Sequence[EditableModuleInstall] = (),
    ) -> executor.InmantaModuleInstallSpec:
        return executor.InmantaModuleInstallSpec(
            module_name=module_name,
            module_version="1.0",
            blueprint=ExecutorBlueprint(
                environment_id=env_id,
                pip_config=PipConfig(),
                requirements=requirements,
                inmanta_modules_to_load=inmanta_modules_to_load,
                python_version=sys.version_info[:2],
                editable_modules=editable_modules,
                legacy_on_disk_code_install=(
                    None if on_disk_module_sources is None else OnDiskCodeInstall(module_sources=on_disk_module_sources)
                ),
            ),
        )

    editable_spec = make_spec(
        "editable_module",
        inmanta_modules_to_load=["editable_module"],
        editable_modules=[editable_module],
    )
    package_spec = make_spec(
        "package_module",
        requirements=["inmanta-module-package-module==1.0"],
        inmanta_modules_to_load=["package_module"],
    )

    blueprint = ExecutorBlueprint.from_specs([editable_spec, package_spec])

    # Nothing is installed on disk: the code of both modules lives in the venv.
    assert blueprint.legacy_on_disk_code_install is None
    assert blueprint.editable_modules == [editable_module]
    # Only the package install module contributes a pip requirement. The editable module is installed with pip from
    # editable_modules instead, and pip pulls in the requirements it declares from its setup.cfg.
    assert blueprint.requirements == ["inmanta-module-package-module==1.0"]
    assert blueprint.inmanta_modules_to_load == ["editable_module", "package_module"]

    # The set of modules loaded out of the venv is part of the executor identity: two agents that share a venv but load
    # a different set of modules must not share an executor process.
    other_blueprint = ExecutorBlueprint.from_specs(
        [
            editable_spec,
            # The same package module, installed in the venv but not loaded: another module's handler may import it.
            make_spec(
                "package_module",
                requirements=["inmanta-module-package-module==1.0"],
            ),
        ]
    )
    assert other_blueprint != blueprint
    assert other_blueprint.blueprint_hash() != blueprint.blueprint_hash()
    # They do share a venv: the code an executor loads is not part of the venv identity.
    assert other_blueprint.to_env_blueprint() == blueprint.to_env_blueprint()

    # A module of unknown install mode is installed on disk: without knowing how it was installed in the compiler venv,
    # that is the only mechanism that works. The two mechanisms have to merge rather than exclude each other, so that
    # such a module and an editable one can share an executor.
    legacy_module_source = make_source("inmanta_plugins/legacy_module/__init__.py", b"b = 2")
    legacy_spec = make_spec(
        "legacy_module",
        on_disk_module_sources=[legacy_module_source],
        requirements=["lorem"],
        inmanta_modules_to_load=["legacy_module"],
    )
    mixed_blueprint = ExecutorBlueprint.from_specs([editable_spec, legacy_spec])
    assert mixed_blueprint.editable_modules == [editable_module]
    assert mixed_blueprint.legacy_on_disk_code_install is not None
    assert list(mixed_blueprint.legacy_on_disk_code_install.module_sources) == [legacy_module_source]
    # A module installed on disk is not a python package, so pip can not resolve its requirements from packaging
    # metadata: they are transported and installed alongside the editable module.
    assert mixed_blueprint.requirements == ["lorem"]
    assert mixed_blueprint.inmanta_modules_to_load == ["editable_module", "legacy_module"]

    # The code installed on disk is outside of the venv: it is part of the executor identity, not of the venv identity.
    assert mixed_blueprint.blueprint_hash() != ExecutorBlueprint.from_specs([editable_spec]).blueprint_hash()


def test_editable_module_version_is_part_of_the_venv_identity():
    """
    An editable module is installed in the venv from a rebuilt tree that no pip requirement identifies, so its identity
    (name and version) is part of the venv identity: the same module at the same version shares a venv, while a change
    to the module yields a new venv and a new executor, rather than mutating a venv another executor may share.
    """
    env_id = uuid.uuid4()

    def blueprint_for(editable_module: EditableModuleInstall) -> ExecutorBlueprint:
        return ExecutorBlueprint(
            environment_id=env_id,
            pip_config=PipConfig(),
            requirements=[],
            python_version=sys.version_info[:2],
            inmanta_modules_to_load=[editable_module.name],
            editable_modules=[editable_module],
        )

    module_v1 = utils.make_editable_inmanta_module("my_mod", "VALUE = 1\n")
    same_module_v1 = utils.make_editable_inmanta_module("my_mod", "VALUE = 1\n")
    module_v2 = utils.make_editable_inmanta_module("my_mod", "VALUE = 2\n")
    # A new requirement only changes the setup.cfg, which is part of the module version as well
    module_v1_with_requirement = utils.make_editable_inmanta_module("my_mod", "VALUE = 1\n", requirements=["lorem"])
    assert len({module_v1.version, module_v2.version, module_v1_with_requirement.version}) == 3

    # The same module at the same version: one venv, one executor
    assert blueprint_for(module_v1).to_env_blueprint() == blueprint_for(same_module_v1).to_env_blueprint()
    assert blueprint_for(module_v1).blueprint_hash() == blueprint_for(same_module_v1).blueprint_hash()

    # A changed module: a new venv and a new executor
    for changed in (module_v2, module_v1_with_requirement):
        assert blueprint_for(module_v1).to_env_blueprint() != blueprint_for(changed).to_env_blueprint()
        assert (
            blueprint_for(module_v1).to_env_blueprint().blueprint_hash()
            != blueprint_for(changed).to_env_blueprint().blueprint_hash()
        )
        assert blueprint_for(module_v1).blueprint_hash() != blueprint_for(changed).blueprint_hash()
