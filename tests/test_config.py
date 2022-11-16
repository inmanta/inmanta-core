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
import logging
import os
import random
import socket

import netifaces
from tornado import netutil

import inmanta.agent.config as cfg
from inmanta import protocol
from inmanta.config import Config, Option, option_as_default
from inmanta.const import ClientType
from inmanta.server.protocol import Server, ServerSlice
from utils import LogSequence


def test_environment_deprecated_options(caplog):
    for (deprecated_option, new_option) in [
        (cfg.agent_interval, cfg.agent_deploy_interval),
        (cfg.agent_splay, cfg.agent_deploy_splay_time),
    ]:

        Config.set(deprecated_option.section, deprecated_option.name, "22")
        caplog.clear()
        assert new_option.get() == 22
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option.name, new_option.name) in caplog.text

        Config.set(new_option.section, new_option.name, "23")
        caplog.clear()
        assert new_option.get() == 23
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option.name, new_option.name) not in caplog.text

        Config.load_config()  # Reset config options to default values
        assert new_option.get() != 23
        assert deprecated_option.get() != 23
        Config.set(new_option.section, new_option.name, "24")
        caplog.clear()
        assert new_option.get() == 24
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option.name, new_option.name) not in caplog.text


def test_options():
    configa = Option("test", "a", "markerA", "test a docs")
    configb = Option("test", "B", option_as_default(configa), "test b docs")

    assert "test.a" in configb.get_default_desc()

    Config.load_config()

    assert configb.get() == "markerA"
    configa.set("MA2")
    assert configb.get() == "MA2"
    configb.set("MB2")
    assert configb.get() == "MB2"


def test_configfile_hierarchy(monkeypatch, tmpdir):
    etc_inmanta_dir = os.path.join(tmpdir, "etc", "inmanta")
    os.makedirs(etc_inmanta_dir, exist_ok=False)

    main_inmanta_cfg_file = os.path.join(etc_inmanta_dir, "inmanta.cfg")

    inmanta_d_dir = os.path.join(etc_inmanta_dir, "inmanta.d")
    os.mkdir(inmanta_d_dir)

    inmanta_d_cfg_file01 = os.path.join(inmanta_d_dir, "01-dbconfig.cfg")
    inmanta_d_cfg_file02 = os.path.join(inmanta_d_dir, "02-dbconfig.cfg")
    inmanta_d_cfg_file_no_cfg_extension = os.path.join(inmanta_d_dir, "03-config")

    dot_inmanta_file = os.path.join(tmpdir, ".inmanta")
    dot_inmanta_cfg_file = os.path.join(tmpdir, ".inmanta.cfg")

    min_c_file = os.path.join(tmpdir, "custom.cfg")

    monkeypatch.setenv("INMANTA_SERVER_AUTH", "true")
    monkeypatch.setenv("INMANTA_SERVER_AGENT_TIMEOUT", "60")

    with open(main_inmanta_cfg_file, "w", encoding="utf-8") as f:
        f.write(
            """
[server]
auth=false
[config]
log-dir=/log
[database]
host=host1
name=db1
port=1234
connection_pool_min_size=2
username=non-default-name-0
[influxdb]
host=host1
interval=10
tags=tag1=value1
        """
        )

    with open(inmanta_d_cfg_file01, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
host=host2
name=db2
[influxdb]
host=host2
        """
        )

    with open(inmanta_d_cfg_file02, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
port=5678
[influxdb]
host=host3
interval=20
        """
        )

    with open(inmanta_d_cfg_file_no_cfg_extension, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
port=9999
        """
        )

    with open(dot_inmanta_file, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
host=host3
username=non-default-name-1
[influxdb]
tags=tag2=value2
        """
        )

    with open(dot_inmanta_cfg_file, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
username=non-default-name-2
connection_pool_min_size=3
        """
        )

    with open(min_c_file, "w", encoding="utf-8") as f:
        f.write(
            """
[database]
connection_pool_min_size=5
        """
        )

    os.chdir(tmpdir)
    Config.load_config(min_c_config_file=min_c_file, config_dir=inmanta_d_dir, main_cfg_file=main_inmanta_cfg_file)

    assert Config.get("config", "log-dir") == "/log"
    assert Config.get("database", "host") == "host3"
    assert Config.get("database", "name") == "db2"
    assert Config.get("database", "port") == 5678
    assert Config.get("influxdb", "host") == "host3"
    assert Config.get("influxdb", "interval") == 20
    assert Config.get("influxdb", "tags")["tag2"] == "value2"
    assert Config.get("database", "username") == "non-default-name-2"
    assert Config.get("database", "connection_pool_min_size") == 5
    assert Config.get("server", "auth")
    assert Config.get("server", "agent-timeout") == 60


async def test_bind_address_ipv4(async_finalizer):
    """This test case check if the Inmanta server doesn't bind on another interface than 127.0.0.1 when bind-address is equal
    to 127.0.0.1. Procedure:
        1) Get free port on all interfaces.
        2) Bind that port on a non-loopback interface, so it's not available for the inmanta server anymore.
        3) Start the Inmanta server with bind-address 127.0.0.1. and execute an API call
    """

    @protocol.method(path="/test", operation="POST", client_types=[ClientType.api])
    async def test_endpoint():
        pass

    class TestSlice(ServerSlice):
        @protocol.handle(test_endpoint)
        async def test_endpoint_handle(self):
            return 200

    # Select a bind address which is not on the loopback interface
    non_loopback_interfaces = [i for i in netifaces.interfaces() if i != "lo" and socket.AF_INET in netifaces.ifaddresses(i)]
    bind_iface = "eth0" if "eth0" in non_loopback_interfaces else random.choice(non_loopback_interfaces)
    bind_addr = netifaces.ifaddresses(bind_iface)[socket.AF_INET][0]["addr"]

    # Get free port on all interfaces
    sock = netutil.bind_sockets(0, "0.0.0.0", family=socket.AF_INET)[0]
    _addr, free_port = sock.getsockname()
    sock.close()

    # Bind port on non-loopback interface
    sock = netutil.bind_sockets(free_port, bind_addr, family=socket.AF_INET)[0]
    try:
        # Configure server
        Config.load_config()
        Config.set("server", "bind-port", str(free_port))
        Config.set("server", "bind-address", "127.0.0.1")
        Config.set("client_rest_transport", "port", str(free_port))

        # Start server
        rs = Server()
        rs.add_slice(TestSlice("test"))
        await rs.start()
        async_finalizer(rs.stop)

        # Check if server is reachable on loopback interface
        client = protocol.Client("client")
        result = await client.test_endpoint()
        assert result.code == 200
    finally:
        sock.close()


async def test_bind_address_ipv6(async_finalizer) -> None:
    @protocol.method(path="/test", operation="POST", client_types=[ClientType.api])
    async def test_endpoint():
        pass

    class TestSlice(ServerSlice):
        @protocol.handle(test_endpoint)
        async def test_endpoint_handle(self):
            return 200

    # Get free port on all interfaces
    sock = netutil.bind_sockets(0, "::", family=socket.AF_INET6)[0]
    (_addr, free_port, _flowinfo, _scopeid) = sock.getsockname()
    sock.close()

    # Configure server
    Config.load_config()
    Config.set("server", "bind-port", str(free_port))
    Config.set("server", "bind-address", "::1")
    Config.set("client_rest_transport", "port", str(free_port))
    Config.set("client_rest_transport", "host", "::1")

    # Start server
    rs = Server()
    rs.add_slice(TestSlice("test"))
    await rs.start()
    async_finalizer(rs.stop)

    client = protocol.Client("client")
    # Check if server is reachable on loopback interface
    result = await client.test_endpoint()
    assert result.code == 200


async def test_bind_port(unused_tcp_port, async_finalizer, caplog):
    @protocol.method(path="/test", operation="POST", client_types=[ClientType.api])
    async def test_endpoint():
        pass

    class TestSlice(ServerSlice):
        @protocol.handle(test_endpoint)
        async def test_endpoint_handle(self):
            return 200

    async def assert_port_bound():
        # Start server
        rs = Server()
        rs.add_slice(TestSlice("test"))
        await rs.start()
        async_finalizer(rs.stop)

        # Check if server is reachable on loopback interface
        client = protocol.Client("client")
        result = await client.test_endpoint()
        assert result.code == 200
        await rs.stop()

    deprecation_line_log_line = (
        "The server_rest_transport.port config option is deprecated in favour of the " "server.bind-port option."
    )
    ignoring_log_line = (
        "Ignoring the server_rest_transport.port config option since the new config options "
        "server.bind-port/server.bind-address are used."
    )

    # Old config option server_rest_transport.port is set
    Config.load_config()
    Config.set("server_rest_transport", "port", str(unused_tcp_port))
    Config.set("client_rest_transport", "port", str(unused_tcp_port))
    caplog.clear()
    await assert_port_bound()
    log_sequence = LogSequence(caplog, allow_errors=False)
    log_sequence.contains("py.warnings", logging.WARNING, deprecation_line_log_line)
    log_sequence.assert_not("py.warnings", logging.WARNING, ignoring_log_line)

    # Old config option server_rest_transport.port and new config option server.bind-port are set together
    Config.load_config()
    Config.set("server_rest_transport", "port", str(unused_tcp_port))
    Config.set("server", "bind-port", str(unused_tcp_port))
    Config.set("client_rest_transport", "port", str(unused_tcp_port))
    caplog.clear()
    await assert_port_bound()
    log_sequence = LogSequence(caplog, allow_errors=False)
    log_sequence.assert_not("py.warnings", logging.WARNING, deprecation_line_log_line)
    log_sequence.contains("py.warnings", logging.WARNING, ignoring_log_line)

    # The new config option server.bind-port is set
    Config.load_config()
    Config.set("server", "bind-port", str(unused_tcp_port))
    Config.set("client_rest_transport", "port", str(unused_tcp_port))
    caplog.clear()
    await assert_port_bound()
    log_sequence = LogSequence(caplog, allow_errors=False)
    log_sequence.assert_not("py.warnings", logging.WARNING, deprecation_line_log_line)
    log_sequence.assert_not("py.warnings", logging.WARNING, ignoring_log_line)


def test_option_is_list():
    option: Option = Option("test", "list", "default,values", "documentation", cfg.is_list)
    option.set("some,values")
    assert option.get() == ["some", "values"]


def test_option_is_list_empty():
    option: Option = Option("test", "list", "default,values", "documentation", cfg.is_list)
    option.set("")
    assert option.get() == []
