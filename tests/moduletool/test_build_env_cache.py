"""
Copyright 2026 Inmanta

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

import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pytest import MonkeyPatch

from build.env import DefaultIsolatedEnv
from inmanta.moduletool import ModuleTool
from utils import DefaultIsolatedEnvCached


def test_module_build_uses_cached_env(tmpdir, modules_v2_dir: str, monkeypatch: MonkeyPatch) -> None:
    """
    V2 module builds in the test suite use the build environment that the test suite shares.
    """
    original_enter = DefaultIsolatedEnvCached.__enter__
    nb_enter_calls = 0

    def counting_enter(self: DefaultIsolatedEnvCached) -> DefaultIsolatedEnv:
        nonlocal nb_enter_calls
        nb_enter_calls += 1
        return original_enter(self)

    monkeypatch.setattr(DefaultIsolatedEnvCached, "__enter__", counting_enter)

    module_dir = os.path.join(tmpdir, "minimalv2module")
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)
    ModuleTool().build(path=module_dir, output_dir=os.path.join(tmpdir, "dist"), wheel=True)

    assert nb_enter_calls == 1


def test_cached_isolated_env_concurrent_first_use(monkeypatch: MonkeyPatch) -> None:
    """
    Threads that use DefaultIsolatedEnvCached for the first time concurrently all get the same instance and the same build
    environment. That environment is created once, and is handed out only after its build requirements are installed.
    This also holds for a thread that arrives while the build requirements are being installed.
    """
    nb_threads = 8
    # Start from no instance, as on the first use in a test session. Monkeypatch restores the session's instance.
    monkeypatch.setattr(DefaultIsolatedEnvCached, "_instance", None)

    # Slow down the creation of the instance and the installation of the build requirements, so that the threads overlap
    original_init = DefaultIsolatedEnvCached.__init__
    instances_created: list[DefaultIsolatedEnvCached] = []

    def slow_init(self: DefaultIsolatedEnvCached) -> None:
        time.sleep(0.2)
        original_init(self)
        instances_created.append(self)

    install_started = threading.Event()
    install_calls: list[DefaultIsolatedEnv] = []

    def slow_install_build_requirements(self: DefaultIsolatedEnvCached, isolated_env: DefaultIsolatedEnv) -> None:
        install_started.set()
        time.sleep(0.5)
        install_calls.append(isolated_env)

    monkeypatch.setattr(DefaultIsolatedEnvCached, "__init__", slow_init)
    monkeypatch.setattr(DefaultIsolatedEnvCached, "_install_build_requirements", slow_install_build_requirements)

    # All threads but the last one start together. The last one starts while the build requirements are being installed.
    early_threads_started = threading.Barrier(nb_threads - 1)

    def use_env(thread_index: int) -> tuple[DefaultIsolatedEnvCached, DefaultIsolatedEnv, int]:
        if thread_index < nb_threads - 1:
            early_threads_started.wait()
        else:
            assert install_started.wait(timeout=10)
        instance = DefaultIsolatedEnvCached.get_instance()
        with instance as env:
            return instance, env, len(install_calls)

    try:
        with ThreadPoolExecutor(max_workers=nb_threads) as executor:
            results = list(executor.map(use_env, range(nb_threads)))
    finally:
        for instance in instances_created:
            instance.destroy()

    assert len(results) == nb_threads
    assert len(instances_created) == 1
    assert len(install_calls) == 1
    assert all(instance is instances_created[0] for instance, _, _ in results)
    assert all(env is install_calls[0] for _, env, _ in results)
    # No thread got the environment before its build requirements were installed
    assert all(nb_install_calls == 1 for _, _, nb_install_calls in results)
