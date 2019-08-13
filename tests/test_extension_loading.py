"""
    Copyright 2019 Inmanta

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
import importlib
import logging
import os
import sys
from contextlib import contextmanager
from typing import Any, Generator

import pytest

import inmanta.server
import inmanta_ext
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SERVER, SLICE_SESSION_MANAGER, SLICE_TRANSPORT, config
from inmanta.server.agentmanager import AgentManager
from inmanta.server.bootloader import InmantaBootloader, PluginLoadFailed
from inmanta.server.extensions import InvalidSliceNameException
from inmanta.server.protocol import Server
from inmanta_ext.testplugin.extension import XTestSlice
from utils import log_contains


@contextmanager
def splice_extension_in(name: str) -> Generator[Any, Any, None]:
    """Context manager to all extensions in tests/data/{name}/inmanta_ext/ to the interpreter and unload them again"""
    oldpath = sys.path
    try:
        sys.path = sys.path + [os.path.join(os.path.dirname(__file__), "data", name)]
        importlib.reload(inmanta_ext)
        yield
    finally:
        sys.path = oldpath
        importlib.reload(inmanta_ext)


def test_discover_and_load():
    with splice_extension_in("test_module_path"):

        config.server_enabled_extensions.set("testplugin")

        ibl = InmantaBootloader()
        print("plugins: ", ibl._discover_plugin_packages())

        assert "inmanta_ext.testplugin" in ibl._discover_plugin_packages()

        tpl = ibl._load_extension("inmanta_ext.testplugin")

        assert tpl == inmanta_ext.testplugin.extension.setup

        with pytest.raises(PluginLoadFailed):
            ibl._load_extension("inmanta_ext.noext")

        with pytest.raises(PluginLoadFailed):
            ibl._load_extension("inmanta_ext.noinit")


def test_phase_1(caplog):
    with splice_extension_in("test_module_path"):
        ibl = InmantaBootloader()

        config.server_enabled_extensions.set("testplugin,noext")

        all = ibl._load_extensions()

        assert "testplugin" in all
        assert all["testplugin"] == inmanta_ext.testplugin.extension.setup

        log_contains(caplog, "inmanta.server.bootloader", logging.WARNING, "Could not load extension inmanta_ext.noext")


def test_phase_2():
    ibl = InmantaBootloader()
    all = {"testplugin": inmanta_ext.testplugin.extension.setup}

    ctx = ibl._collect_slices(all)

    byname = {sl.name: sl for sl in ctx._slices}

    assert "testplugin.testslice" in byname

    # load slice in wrong namespace
    with pytest.raises(InvalidSliceNameException):
        all = {"test": inmanta_ext.testplugin.extension.setup}
        ctx = ibl._collect_slices(all)


def test_phase_3():
    server = Server()
    server.add_slice(XTestSlice())
    server.add_slice(inmanta.server.server.Server())
    server.add_slice(AgentManager())

    order = server._get_slice_sequence()
    print([s.name for s in order])
    assert [s.name for s in order] == [
        SLICE_SESSION_MANAGER,
        SLICE_SERVER,
        SLICE_AGENT_MANAGER,
        SLICE_TRANSPORT,
        "testplugin.testslice",
    ]


def test_end_to_end():
    ibl = InmantaBootloader()

    config.server_enabled_extensions.set("testplugin")

    slices = ibl.load_slices()
    byname = {sl.name: sl for sl in slices}
    assert "testplugin.testslice" in byname


def test_end_to_end_2():
    with splice_extension_in("bad_module_path"):
        config.server_enabled_extensions.set("badplugin")

        ibl = InmantaBootloader()
        all = ibl._load_extensions()
        print(all)
        assert "badplugin" in all

    config.server_enabled_extensions.set("")
    all = ibl._load_extensions()
    assert "badplugin" not in all


@pytest.mark.asyncio
async def test_startup_failure(async_finalizer, server_config):
    with splice_extension_in("bad_module_path"):
        config.server_enabled_extensions.set("badplugin")

        ibl = InmantaBootloader()
        async_finalizer.add(ibl.stop)
        with pytest.raises(Exception) as e:
            await ibl.start()
        assert str(e.value) == "Slice badplugin.badslice failed to start because: Too bad, this plugin is broken"

    config.server_enabled_extensions.set("")
    all = ibl._load_extensions()
    assert "badplugin" not in all


def test_load_and_filter(caplog):
    caplog.set_level(logging.INFO)

    with splice_extension_in("test_module_path"):
        ibl = InmantaBootloader()

        plugin_pkgs = ibl._discover_plugin_packages()
        assert "inmanta_ext.core" in plugin_pkgs
        assert len(plugin_pkgs) == 1

        # When extensions are available but not enabled, log a message with the correct option
        log_contains(caplog, "inmanta.server.bootloader", logging.INFO, "Load extensions by setting configuration option")

        with pytest.raises(PluginLoadFailed):
            config.server_enabled_extensions.set("unknown")
            plugin_pkgs = ibl._discover_plugin_packages()
