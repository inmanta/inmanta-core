import os

import inmanta.agent.config as cfg
from inmanta.config import Config, Option, option_as_default


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


def test_configfile_hierarchy(tmpdir):
    etc_dir = os.path.join(tmpdir, "etc")
    os.mkdir(etc_dir)

    main_inmanta_cfg_file = os.path.join(etc_dir, "inmanta.cfg")

    inmanta_d_dir = os.path.join(etc_dir, "inmanta.d")
    os.mkdir(inmanta_d_dir)

    inmanta_d_cfg_file01 = os.path.join(inmanta_d_dir, "01-dbconfig.cfg")
    inmanta_d_cfg_file02 = os.path.join(inmanta_d_dir, "02-dbconfig.cfg")
    inmanta_d_cfg_file_no_cfg_extension = os.path.join(inmanta_d_dir, "03-config")

    dot_inmanta_file = os.path.join(tmpdir, ".inmanta")
    dot_inmanta_cfg_file = os.path.join(tmpdir, ".inmanta.cfg")

    with open(main_inmanta_cfg_file, "w+") as f:
        f.write(
            """
[database]
host=host1
name=db1
port=1234
[influxdb]
host=host1
interval=10
tags=tag1=value1
[dashboard]
path=/some/directory
        """
        )

    with open(inmanta_d_cfg_file01, "w+") as f:
        f.write(
            """
[database]
host=host2
name=db2
[influxdb]
host=host2
        """
        )

    with open(inmanta_d_cfg_file02, "w+") as f:
        f.write(
            """
[database]
port=5678
[influxdb]
host=host3
interval=20
        """
        )

    with open(inmanta_d_cfg_file_no_cfg_extension, "w+") as f:
        f.write(
            """
[database]
port=9999
        """
        )

    with open(dot_inmanta_file, "w+") as f:
        f.write(
            """
[database]
host=host3
[influxdb]
tags=tag2=value2
[dashboard]
path=/some/other/directory
        """
        )

    with open(dot_inmanta_cfg_file, "w+") as f:
        f.write(
            """
[dashboard]
path=/directory
        """
        )

    os.chdir(tmpdir)
    Config._main_cfg_file = main_inmanta_cfg_file
    Config._inmanta_d_dir = inmanta_d_dir
    Config.load_config()

    assert Config.get("database", "host") == "host3"
    assert Config.get("database", "name") == "db2"
    assert Config.get("database", "port") == 5678
    assert Config.get("influxdb", "host") == "host3"
    assert Config.get("influxdb", "interval") == 20
    assert Config.get("influxdb", "tags")["tag2"] == "value2"
    assert Config.get("dashboard", "path") == "/directory"
