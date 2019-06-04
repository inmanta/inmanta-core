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
