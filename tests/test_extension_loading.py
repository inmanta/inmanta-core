import importlib
import logging
import os
from contextlib import contextmanager

import pytest
import sys

from typing import Generator, Any

import inmanta_ext
from inmanta.server import SLICE_SERVER, SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER, SLICE_TRANSPORT
from inmanta.server.agentmanager import AgentManager
from inmanta.server.bootloader import InmantaBootloader, PluginLoadFailed

from inmanta.server.extensions import InvalidSliceNameException
from inmanta.server.protocol import Server
import inmanta.server
from inmanta_ext.testplugin.extension import TesterSlice

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

        all = ibl._load_extensions()

        assert "testplugin" in all
        assert all["testplugin"] == inmanta_ext.testplugin.extension.setup

        log_contains(caplog, "inmanta.server.bootloader", logging.WARNING, "Could not load extension inmanta_ext.noext")


def test_phase_2(caplog):
    ibl = InmantaBootloader()
    all = {"testplugin": inmanta_ext.testplugin.extension.setup}

    ctx = ibl._collect_slices(all)

    byname = {sl.name: sl for sl in ctx._slices}

    assert "testplugin.testslice" in byname

    # load slice in wrong namespace
    with pytest.raises(InvalidSliceNameException):
        all = {"test": inmanta_ext.testplugin.extension.setup}
        ctx = ibl._collect_slices(all)


def test_phase_3(caplog):
    server = Server()
    server.add_slice(TesterSlice())
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


def test_end_to_end(caplog):
    ibl = InmantaBootloader()
    slices = ibl.load_slices()
    byname = {sl.name: sl for sl in slices}
    assert "testplugin.testslice" in byname


def test_end_to_end_2(caplog):
    with splice_extension_in("bad_module_path"):
        ibl = InmantaBootloader()
        all = ibl._load_extensions()
        print(all)
        assert "badplugin" in all

    all = ibl._load_extensions()
    assert "badplugin" not in all


@pytest.mark.asyncio
async def test_startup_failure(caplog, async_finalizer, server_config):
    with splice_extension_in("bad_module_path"):
        ibl = InmantaBootloader()
        async_finalizer.add(ibl.stop)
        with pytest.raises(Exception) as e:
            await ibl.start()
        assert str(e.value) == "Slice badplugin.badslice failed to start because: Too bad, this plugin is broken"

    all = ibl._load_extensions()
    assert "badplugin" not in all
