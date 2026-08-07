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
import uuid
from collections.abc import Sequence

import pytest

import inmanta
from inmanta import const
from inmanta.agent import executor, forking_executor
from inmanta.const import PLUGINS_PACKAGE
from inmanta.data.model import ModuleSource, ModuleSourceMetadata, PipConfig
from inmanta.loader import CodeManager, OnDiskCodeInstall
from inmanta.signals import dump_ioloop_running, dump_threads
from inmanta.util import hash_file
from packaging import version
from utils import PipIndex, log_contains, log_doesnt_contain, retry_limited

logger = logging.getLogger(__name__)


def make_editable_inmanta_module(
    module_name: str, content: str, *, requirements: Sequence[str] = ()
) -> executor.EditableModuleInstall:
    """
    Build an editable inmanta module named ``module_name``.

    In the iso10 code-install design, a module installed in editable mode in the compiler venv is carried in the
    blueprint as an EditableModuleInstall. On the agent side it is reconstructed as an installable python package and
    pip-installed in editable mode into the executor venv; the executor then imports it straight from the venv. The
    source ``content`` becomes the module's ``inmanta_plugins.<module_name>`` package ``__init__.py``.

    The module's python dependencies are declared as ``install_requires`` in its setup.cfg, which is the only place they
    travel: pip resolves them when it installs the reconstructed module in editable mode.

    :return: the EditableModuleInstall to add to the blueprint's ``editable_modules``. Add the module name to the
        blueprint's ``inmanta_modules_to_load`` as well for the executor to import it.
    """
    fq_name = f"inmanta_plugins.{module_name}"
    code = content.encode()
    metadata = ModuleSourceMetadata(name=fq_name, hash_value=hash_file(code), is_byte_code=False)

    install_requires = "".join(f"\n    {requirement}" for requirement in requirements)
    setup_cfg = (
        "[metadata]\n"
        f"name = inmanta-module-{module_name}\n"
        "version = 1.0.0\n"
        "\n"
        "[options]\n"
        "zip_safe = False\n"
        "include_package_data = True\n"
        "packages = find_namespace:\n"
        f"install_requires ={install_requires}\n"
    ).encode()
    pyproject_toml = (
        "[build-system]\n" 'requires = ["setuptools", "wheel"]\n' 'build-backend = "setuptools.build_meta"\n'
    ).encode()

    return executor.EditableModuleInstall(
        name=module_name,
        # Compute the version the way the write path does, so that any change to the module, e.g. a newly declared
        # requirement, yields a new version and therefore a new venv identity.
        version=CodeManager.get_module_version(set(), [metadata], [hash_file(setup_cfg), hash_file(pyproject_toml)]),
        python_module_sources=[ModuleSource(metadata=metadata, source=code)],
        setup_cfg=setup_cfg,
        pyproject_toml=pyproject_toml,
    )


@pytest.fixture
def set_custom_executor_policy(server_config):
    """
    Fixture to temporarily set the policy for executor management.
    """
    old_cap_value = inmanta.agent.config.agent_executor_cap.get()

    # Keep 4 executors per agent
    inmanta.agent.config.agent_executor_cap.set("4")

    yield

    inmanta.agent.config.agent_executor_cap.set(str(old_cap_value))


def code_for(bp: executor.ExecutorBlueprint) -> list[executor.InmantaModuleInstallSpec]:
    """
    Wrap a blueprint in the single install spec it was built for. The install mode follows from the blueprint: these
    tests are about executor and venv pooling, so they build the blueprint directly rather than through get_code.
    """
    install_mode: executor.InmantaModuleInstallMode
    if bp.on_disk_code_install is not None:
        install_mode = executor.InmantaModuleInstallMode.ON_DISK
    elif bp.editable_modules:
        install_mode = executor.InmantaModuleInstallMode.EDITABLE
    else:
        install_mode = executor.InmantaModuleInstallMode.PACKAGE
    return [executor.InmantaModuleInstallSpec("test", "abcdef", bp, install_mode)]


async def test_process_manager(
    environment, pip_index, set_custom_executor_policy, mpmanager_light: forking_executor.MPManager
) -> None:
    """
    This test verifies the creation and reuse of executors and their underlying environments. It checks whether
    new executors and environments are created as necessary and reused when the conditions are the same.

    It also tests that constraints set in the EnvBlueprint are used during agent code install.
    """

    env_id = uuid.UUID(environment)
    # Define requirements and pip configuration
    requirements1 = ("pkg1",)
    requirements2 = ("pkg1", "pkg2")
    constraints = "pkg1<2.0.0\npkg2"
    pip_config = PipConfig(index_url=pip_index.url)

    def make_module_source(name: str, content: str) -> ModuleSource:
        code = content.encode()
        sha1sum = hashlib.new("sha1")
        sha1sum.update(code)
        hv: str = sha1sum.hexdigest()
        return ModuleSource(
            metadata=ModuleSourceMetadata(
                name=name,
                hash_value=hv,
                is_byte_code=False,
            ),
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

    # A distinct standalone module, only used by blueprint1
    module_source3 = make_module_source("inmanta_plugins.bp1", """b=1""")

    # These sources can only be installed on disk, outside of the venv: they are not part of an installable module.
    on_disk_install1 = OnDiskCodeInstall(module_sources=[module_source3])
    on_disk_install2 = OnDiskCodeInstall(module_sources=[module_source1, module_source2])

    # Define blueprints for executors and environments
    blueprint1 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements1,
        python_version=sys.version_info[:2],
        project_constraints=None,
        on_disk_code_install=on_disk_install1,
    )

    env_blueprint1 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements1,
        python_version=sys.version_info[:2],
        project_constraints=None,
    )

    blueprint2 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements1,
        python_version=sys.version_info[:2],
        project_constraints=None,
        on_disk_code_install=on_disk_install2,
    )
    blueprint3 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements2,
        python_version=sys.version_info[:2],
        project_constraints=None,
        on_disk_code_install=on_disk_install2,
    )
    env_blueprint2 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements2,
        python_version=sys.version_info[:2],
        project_constraints=None,
    )
    blueprint4 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements2,
        python_version=sys.version_info[:2],
        project_constraints=constraints,
        on_disk_code_install=on_disk_install2,
    )
    env_blueprint3 = executor.EnvBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements2,
        python_version=sys.version_info[:2],
        project_constraints=constraints,
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
    assert installed["pkg1"] == version.Version("2.0.0")

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
    assert installed["pkg1"] == version.Version("2.0.0")

    # Changing the project constraints should necessitate a new environment
    executor_4 = await executor_manager.get_executor("agent1", "local:", code_for(blueprint4))

    assert len(executor_manager.pool) == 4
    assert executor_4.id == executor.ExecutorId("agent1", "local:", blueprint4)
    assert executor_4.id in executor_manager.pool
    assert executor_manager.pool[executor_4.id] == executor_4

    assert len(venv_manager.pool) == 3  # A new environment is created
    assert env_blueprint3.blueprint_hash() in venv_manager.pool
    assert venv_manager.pool[env_blueprint3.blueprint_hash()] == executor_4.process.executor_virtual_env

    installed = executor_4.process.executor_virtual_env.get_installed_packages()
    assert all(element in installed for element in requirements2)
    assert installed["pkg1"] == version.Version("1.0.0")


async def test_executor_install_without_load(environment, mpmanager_light: forking_executor.MPManager) -> None:
    """
    Verify the "install but don't load" path in the iso10 design: a module installed in editable mode that is not part of
    inmanta_modules_to_load must be installed into the executor venv during executor creation, but must not be imported.
    This is the case for modules whose code an agent needs available (e.g. because another module imports it) but which
    the agent does not load itself.
    """
    env_id = uuid.UUID(environment)
    # use_system_config lets pip reach the configured index for the editable module's build backend.
    pip_config = PipConfig(use_system_config=True)

    module_name = "install_only"
    # This module raises on import: if it were loaded, executor creation would fail with a ModuleLoadingException.
    editable_install_only = make_editable_inmanta_module(
        module_name,
        "raise RuntimeError('this module must not be imported')",
    )

    # The module is not part of inmanta_modules_to_load: it is installed in the venv but never imported.
    blueprint = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=sys.version_info[:2],
        project_constraints=None,
        editable_modules=[editable_install_only],
    )

    executor_manager = mpmanager_light

    # Creating the executor must succeed: the install-only module is installed in the venv but never imported.
    the_executor = await executor_manager.get_executor("agent1", "local:", code_for(blueprint))
    assert the_executor

    # The module was installed (in editable mode) in the executor venv, even though it was not loaded.
    installed = the_executor.process.executor_virtual_env.get_installed_packages(only_editable=True)
    assert "inmanta-module-install-only" in installed

    # The source must have been written to disk in the venv's "editable" folder.
    venv_editable_dir = os.path.join(
        executor_manager.process_pool.environment_manager.envs_dir,
        the_executor.process.executor_virtual_env.inmanta_editable_dir,
    )
    source_file = os.path.join(
        venv_editable_dir,
        module_name,
        PLUGINS_PACKAGE,
        module_name,
        "__init__.py",
    )
    assert os.path.exists(source_file)


async def test_editable_module_dependency_with_extras(
    environment, index_with_pkgs_containing_optional_deps: str, mpmanager_light: forking_executor.MPManager
) -> None:
    """
    An inmanta module installed in editable mode declares its python dependencies in its setup.cfg, which is the only
    place they travel. Pip resolves them when it installs the reconstructed module in editable mode, extras included.
    """
    env_id = uuid.UUID(environment)
    # use_system_config lets pip reach the configured index for the editable module's build backend, the index of the
    # fixture holds the dependency and its optional dependencies.
    pip_config = PipConfig(use_system_config=True, extra_index_url=[index_with_pkgs_containing_optional_deps])

    editable_module = make_editable_inmanta_module("with_extras", "a = 1", requirements=["pkg[optional-a]"])

    blueprint = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        # The requirements the module declares are deliberately not passed along here: pip has to pull them in from the
        # setup.cfg of the module it installs.
        requirements=(),
        python_version=sys.version_info[:2],
        project_constraints=None,
        inmanta_modules_to_load=["with_extras"],
        editable_modules=[editable_module],
    )

    the_executor = await mpmanager_light.get_executor("agent1", "local:", code_for(blueprint))

    installed = the_executor.process.executor_virtual_env.get_installed_packages()
    # The dependency and the dependencies of the extra it was declared with are installed, the ones of the other extra
    # are not.
    assert {"pkg", "dep-a"} <= set(installed)
    assert not {"dep-b", "dep-c"} & set(installed)


async def test_process_manager_restart(environment, tmpdir, mp_manager_factory, caplog) -> None:
    """
    Verifies that virtual environments can be rediscovered upon the restart of an ExecutorManager. This test
    simulates a restart scenario to ensure that previously created environments are reused instead of being recreated.
    """
    caplog.clear()

    env_id = uuid.UUID(environment)
    # use_system_config lets pip reach the configured index for the build backend (setuptools/wheel) needed to install
    # the editable module. This blueprint has no requirements, so no local index is needed.
    pip_config = PipConfig(use_system_config=True)
    requirements = ()

    # A single standalone module for the blueprint, installed in editable mode.
    editable_bp1 = make_editable_inmanta_module("bp1", "b = 1")

    # Create a blueprint with no requirements and a single editable module
    blueprint1 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=requirements,
        python_version=sys.version_info[:2],
        editable_modules=[editable_bp1],
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
    env_id = uuid.uuid4()
    # Force log level down, this causes more output on the CI when this fails
    caplog.set_level("DEBUG")

    # use_system_config lets pip reach the configured index for the editable modules' build backend; the local index is
    # added as an extra index for the (pkg1) dependency declared by blueprint3's module.
    pip_config = PipConfig(use_system_config=True, extra_index_url=[pip_index.url])

    test_content = """
def test():
    return 10
    """
    # Two standalone modules installed in editable mode.
    editable_test = make_editable_inmanta_module("test", test_content)
    # A distinct standalone module, only used by blueprint1
    editable_bp1 = make_editable_inmanta_module("bp1", "b = 1")
    # Same module as blueprint2's, but with an added python dependency (pkg1). In the iso10 design a dependency is
    # declared in the module's setup.cfg, which changes its version and therefore the venv identity.
    editable_test_with_dep = make_editable_inmanta_module("test", test_content, requirements=["pkg1"])

    blueprint1 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=sys.version_info[:2],
        editable_modules=[editable_bp1],
    )
    blueprint2 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=sys.version_info[:2],
        editable_modules=[editable_test],
    )
    blueprint3 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=sys.version_info[:2],
        editable_modules=[editable_test_with_dep],
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
    assert executor_1 is not executor_2, "Expected a different executor instance for a different editable module"
    assert (
        executor_1 is not executor_3
    ), "Expected a different executor instance for a different editable module and requirements"
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
    env_id = uuid.uuid4()
    mpmanager_light.process_pool.venv_checkup_interval = 0.1  # Renew the timestamp of the venv status file every 100 ms
    # use_system_config lets pip reach the configured index for the editable modules' build backend; the local index is
    # added as an extra index for the (pkg1, pkg2) dependencies declared by the modules.
    pip_config = PipConfig(use_system_config=True, extra_index_url=[pip_index.url])

    test_content = """
def test():
    return 10
    """
    # A standalone module, only used by blueprint1
    editable_bp1 = make_editable_inmanta_module("bp1", "b = 1")
    # blueprint2 and blueprint3 share the same module sources but declare different python dependencies (pkg1 vs pkg2).
    # In the iso10 design the dependency lives in the module's setup.cfg, which distinguishes their venv identities.
    editable_test_pkg1 = make_editable_inmanta_module("test", test_content, requirements=["pkg1"])
    editable_test_pkg2 = make_editable_inmanta_module("test", test_content, requirements=["pkg2"])

    initial_version: tuple[int, int] = (3, 11)

    blueprint1 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=initial_version,
        editable_modules=[editable_bp1],
    )
    blueprint2 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=initial_version,
        editable_modules=[editable_test_pkg1],
    )
    blueprint3 = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=initial_version,
        editable_modules=[editable_test_pkg2],
    )

    executor_manager = mpmanager_light
    executor_1, executor_2, executor_3 = await asyncio.gather(
        executor_manager.get_executor("agent1", "local:", code_for(blueprint1)),
        executor_manager.get_executor("agent2", "local:", code_for(blueprint2)),
        executor_manager.get_executor("agent3", "local:", code_for(blueprint3)),
    )

    environment_manager = mpmanager_light.process_pool.environment_manager
    venv_dir = pathlib.Path(environment_manager.envs_dir)

    assert len([e for e in venv_dir.iterdir()]) == 3, "We should have three Virtual Environments for our 3 executors!"

    executor_1_venv_status_file = (
        pathlib.Path(executor_1.process.executor_virtual_env.env_path) / ".inmanta" / const.INMANTA_VENV_STATUS_FILENAME
    )
    executor_2_venv_status_file = (
        pathlib.Path(executor_2.process.executor_virtual_env.env_path) / ".inmanta" / const.INMANTA_VENV_STATUS_FILENAME
    )
    executor_3_venv_status_file = (
        pathlib.Path(executor_3.process.executor_virtual_env.env_path) / ".inmanta" / const.INMANTA_VENV_STATUS_FILENAME
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

    async def stop_executor_and_wait_for_executor_server_to_stop(
        executor_name: str, executor_blueprint: executor.ExecutorBlueprint
    ) -> None:
        # Stop the executor
        executors = await executor_manager.stop_for_agent(executor_name)
        await asyncio.gather(*(e.join() for e in executors))
        assert all(not e.running for e in executors)

        def did_executor_server_stop() -> bool:
            return executor_blueprint not in mpmanager_light.process_pool.pool

        # Also wait until the executor server has stopped, because that one refreshes the .inmanta_venv_status file.
        await retry_limited(did_executor_server_stop, timeout=10)

    # Now we want to check if the cleanup is working correctly
    await stop_executor_and_wait_for_executor_server_to_stop(executor_name="agent1", executor_blueprint=blueprint1)
    # First we want to override the modification date of the `inmanta_venv_status` file
    os.utime(
        executor_1_venv_status_file, (datetime.datetime.now().astimezone().timestamp(), old_datetime.astimezone().timestamp())
    )
    assert len([e for e in venv_dir.iterdir()]) == 3, "We should have three Virtual Environments for our 3 executors!"
    # We remove the old VirtualEnvironment
    logger.debug("Calling cleanup_virtual_environments")
    await environment_manager.cleanup_inactive_pool_members()
    logger.debug("cleanup_virtual_environments ended")

    venvs = {str(e) for e in venv_dir.iterdir()}
    assert len(venvs) == 2, "Only two Virtual Environment should exist!"  # Venv one is gone
    assert {executor_2.process.executor_virtual_env.env_path, executor_3.process.executor_virtual_env.env_path} == venvs

    # Let's stop the other agent and pretend that the venv is broken
    await stop_executor_and_wait_for_executor_server_to_stop(executor_name="agent2", executor_blueprint=blueprint2)
    executor_2_venv_status_file.unlink()

    await environment_manager.cleanup_inactive_pool_members()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 1, "Only one Virtual Environment should exist!"  # Only nr 3

    # Let's stop the other agent and pretend that the venv is outdated
    await stop_executor_and_wait_for_executor_server_to_stop(executor_name="agent3", executor_blueprint=blueprint3)
    # This part of the test is a bit subtle because we rely on the fact that there is no context switching between the
    # modification override of the inmanta file and the retrieval of the last modification of the file
    os.utime(
        executor_3_venv_status_file,
        (datetime.datetime.now().timestamp(), old_datetime.timestamp()),
    )
    # A new version would run
    blueprint3_updated = executor.ExecutorBlueprint(
        environment_id=env_id,
        pip_config=pip_config,
        requirements=(),
        python_version=(3, 12),
        editable_modules=[editable_test_pkg2],
    )
    await executor_manager.get_executor("agent3", "local:", code_for(blueprint3_updated))
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 2, "Only two Virtual Environment should exist!"

    await mpmanager_light.process_pool.environment_manager.cleanup_inactive_pool_members()
    venvs = [str(e) for e in venv_dir.iterdir()]
    assert len(venvs) == 1, "Only one Environment should exist!"
