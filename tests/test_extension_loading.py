import logging

import pytest

from inmanta.server import SLICE_SERVER, SLICE_AGENT_MANAGER
from inmanta.server.bootloader import InmantaBootloader, PluginLoadFailed

import inmanta_ext.testplugin.extension
from inmanta.server.extensions import InvalidSliceNameException

from utils import log_contains


def test_discover_and_load():

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
    ibl = InmantaBootloader()
    all = {"testplugin": inmanta_ext.testplugin.extension.setup}
    ctx = ibl._collect_slices(all)
    order = ibl._order_slices(ctx)
    assert [s.name for s in order] == [SLICE_SERVER, SLICE_AGENT_MANAGER, "testplugin.testslice"]
