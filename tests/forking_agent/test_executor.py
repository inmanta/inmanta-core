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
import importlib
import logging
import os
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
from forking_agent.ipc_commands import Echo, GetConfig, GetName, ImportModule, TestLoader
from inmanta.agent import executor
from inmanta.agent.executor import EditableModuleInstall, ExecutorBlueprint, ExecutorVirtualEnvironment
from inmanta.agent.forking_executor import MPExecutor, MPManager
from inmanta.data import PipConfig
from inmanta.data.model import ExecutorModuleSource, ModuleSource, ModuleSourceMetadata
from inmanta.protocol.ipc_light import ConnectionLost
from packaging.version import Version
from utils import NOISY_LOGGERS, log_contains, retry_limited


async def test_reconstruct_editable_module(tmp_path, caplog, monkeypatch):
    """
    Reconstructing an editable module lays out its python sources as packages (dirs with an __init__ file) under a
    top-level inmanta_plugins namespace package (which itself gets no __init__ file), and writes its packaging files
    at the module root. The byte-code flag selects the __init__ file extension. Creating the venv logs the editable
    installs explicitly.
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

        # Creating the venv installs the editable modules and logs them explicitly (package installs are covered by the
        # separately-logged requirements). Stub the actual venv creation and pip install.
        monkeypatch.setattr(venv, "init_env", lambda: None)

        async def _noop_install(**kwargs: object) -> None:
            pass

        monkeypatch.setattr(venv, "async_install_for_config", _noop_install)

        blueprint = executor.EnvBlueprint(
            environment_id=uuid.uuid4(),
            pip_config=PipConfig(),
            requirements=[],
            python_version=sys.version_info[:2],
            editable_modules=[editable_module],
        )
        with caplog.at_level(logging.INFO):
            await venv._create_and_install_environment(blueprint)

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

    # The editable install is logged explicitly.
    log_contains(caplog, "inmanta.agent.executor", logging.INFO, "Installing 1 inmanta module(s) in editable mode: my_mod")


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


async def test_executor_server_iso9_compatibility_layer(
    set_custom_executor_policy, mpmanager: MPManager, client, environment, caplog
):
    """
    This test is testing the deploy_and_load_modules_iso9 path of the CodeLoader deploy_and_load method. This specific
    path, and this test can be removed in iso11.

    Test the MPManager, this includes:

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
        install_on_disk=None,
        load_module=None,
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
        install_on_disk=None,
        load_module=None,
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
        install_on_disk=None,
        load_module=None,
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


async def test_executor_server_iso10_editable_install(mpmanager: MPManager, caplog):
    """
    iso10+ code install through a real forking executor. An inmanta module that was installed in editable mode in the
    compiler venv is carried in the blueprint as an EditableModuleInstall. On the agent side it is reconstructed as an
    installable python package and pip-installed in editable mode into the executor venv, then imported straight from
    that venv (the iso10 load path: install_on_disk is not None, so the legacy PluginModuleFinder is never configured).

    This is the iso10 counterpart of test_executor_server_iso9_compatibility_layer: it covers the read path added for
    #10451 end-to-end (reconstruct -> editable install -> import from venv) rather than in unit isolation. It can be
    simplified but not removed in iso11, when the iso9 compatibility layer is dropped.
    """
    module_name = "iso10editable"
    fq_module_name = f"inmanta_plugins.{module_name}"

    with pytest.raises(ImportError):
        # The module must not be importable in the test process: it only ever gets installed in the executor venv.
        importlib.import_module(fq_module_name)

    manager = mpmanager
    await manager.start()

    # A minimal but valid, pip-installable V2 module. Its single python file exposes a test() function we can call
    # from inside the executor process to prove the module was installed and imported from the venv.
    module_content = f"def test():\n    return {module_name!r}\n".encode()
    setup_cfg = (
        "[metadata]\n"
        f"name = inmanta-module-{module_name}\n"
        "version = 1.0.0\n"
        "\n"
        "[options]\n"
        "zip_safe = False\n"
        "include_package_data = True\n"
        "packages = find_namespace:\n"
    ).encode()
    pyproject_toml = (
        "[build-system]\n" 'requires = ["setuptools", "wheel"]\n' 'build-backend = "setuptools.build_meta"\n'
    ).encode()

    module_metadata = ModuleSourceMetadata(
        name=fq_module_name,
        hash_value=inmanta.util.hash_file(module_content),
        is_byte_code=False,
    )

    editable_module = EditableModuleInstall(
        name=module_name,
        version="cafe",
        python_module_sources=[ModuleSource(metadata=module_metadata, source=module_content)],
        setup_cfg=setup_cfg,
        pyproject_toml=pyproject_toml,
    )

    # iso10 source: install_on_disk is not None selects the new-style load path. The code lives in the venv (editable
    # install), so deploy_and_load only imports it; load_module=True asks the executor to do so.
    source = ExecutorModuleSource(
        metadata=module_metadata,
        source=module_content,
        install_on_disk=True,
        load_module=True,
    )

    blueprint = ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        # use_system_config so pip can reach the index configured for the test suite (for build-system requirements).
        pip_config=PipConfig(use_system_config=True),
        requirements=[],
        sources=[source],
        python_version=sys.version_info[:2],
        editable_modules=[editable_module],
    )

    # get_executor builds the venv (reconstruct + editable install) and loads the code. It raises if either fails,
    # so a successful call already asserts the install and import succeeded.
    with caplog.at_level(logging.INFO):
        my_executor = await manager.get_executor(
            "agent1",
            "internal:",
            [executor.InmantaModuleInstallSpec(module_name, "cafe", blueprint)],
        )

    # The editable module was imported straight from the executor venv and its code runs there.
    assert await my_executor.call(ImportModule(fq_module_name)) == module_name

    # The reconstructed module was pip-installed in editable mode; this is logged explicitly during venv creation.
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
    and added to the executor venv as a regular pip requirement (install_on_disk=False), then imported straight from the
    venv (install_on_disk is not None -> iso10 load path, so the legacy PluginModuleFinder is never configured).

    Together with the editable variant this covers both iso10 install modes end-to-end. It can be simplified but not
    removed in iso11, when the iso9 compatibility layer is dropped.
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

    module_content = f"def test():\n    return {module_name!r}\n".encode()
    module_metadata = ModuleSourceMetadata(
        name=fq_module_name,
        hash_value=inmanta.util.hash_file(module_content),
        is_byte_code=False,
    )

    # iso10 source in package-install mode: install_on_disk=False makes from_specs add the module itself as a pip
    # requirement (inmanta-module-iso10pkg==1.0.0) rather than reconstructing and editable-installing it. load_module
    # asks the executor to import it once installed.
    source = ExecutorModuleSource(
        metadata=module_metadata,
        source=module_content,
        install_on_disk=False,
        load_module=True,
    )

    blueprint = ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=PipConfig(index_url=pip_index.url),
        requirements=[],
        sources=[source],
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

    # The module was installed from the index and imported straight from the executor venv, and its code runs there.
    assert await my_executor.call(ImportModule(fq_module_name)) == module_name

    # The module did not leak into the test process: it lives only in the executor venv.
    with pytest.raises(ImportError):
        importlib.import_module(fq_module_name)


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
        install_on_disk=None,
        load_module=None,
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


def test_from_specs_merges_source_and_package_installs():
    """
    from_specs merges the install specs of an editable module, which ships its source, and of a package installed
    module, which ships no source but a pip requirement and its name to load out of the venv.
    """
    env_id = uuid.uuid4()
    source = inmanta.data.model.ExecutorModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.editable_module",
            hash_value="aaaaa",
            is_byte_code=False,
        ),
        source=b"a = 1",
        install_on_disk=True,
        load_module=True,
    )

    def make_spec(
        module_name: str,
        sources: list[inmanta.data.model.ExecutorModuleSource],
        requirements: list[str],
        inmanta_modules_to_load: list[str],
    ) -> executor.InmantaModuleInstallSpec:
        return executor.InmantaModuleInstallSpec(
            module_name=module_name,
            module_version="1.0",
            blueprint=ExecutorBlueprint(
                environment_id=env_id,
                pip_config=PipConfig(),
                requirements=requirements,
                sources=sources,
                inmanta_modules_to_load=inmanta_modules_to_load,
                python_version=sys.version_info[:2],
            ),
        )

    blueprint = ExecutorBlueprint.from_specs(
        [
            make_spec("editable_module", [source], requirements=[], inmanta_modules_to_load=[]),
            make_spec(
                "package_module",
                [],
                requirements=["inmanta-module-package-module==1.0"],
                inmanta_modules_to_load=["package_module"],
            ),
        ]
    )

    assert blueprint.sources == [source]
    assert blueprint.requirements == ["inmanta-module-package-module==1.0"]
    assert blueprint.inmanta_modules_to_load == ["package_module"]

    # The set of modules loaded out of the venv is part of the executor identity: two agents that share a venv but load
    # a different set of modules must not share an executor process.
    other_blueprint = ExecutorBlueprint.from_specs(
        [
            make_spec("editable_module", [source], requirements=[], inmanta_modules_to_load=[]),
            make_spec("package_module", [], requirements=["inmanta-module-package-module==1.0"], inmanta_modules_to_load=[]),
        ]
    )
    assert other_blueprint != blueprint
    assert other_blueprint.blueprint_hash() != blueprint.blueprint_hash()
    # They do share a venv: the code an executor loads is not part of the venv identity.
    assert other_blueprint.to_env_blueprint() == blueprint.to_env_blueprint()
