from inmanta.config import Config
import inmanta.agent.config as cfg


def test_environment_depricated_setting(caplog):
    for (depricated_option, new_option) in [(cfg.agent_interval, cfg.agent_deploy_interval),
                                            (cfg.agent_splay, cfg.agent_deploy_splay_time)]:

        Config.set(depricated_option.section, depricated_option.name, "22")
        caplog.clear()
        assert new_option.get() == 22
        assert "Config option %s is depricated. use %s instead." % (depricated_option.name, new_option.name) in caplog.text

        Config.set(new_option.section, new_option.name, "23")
        caplog.clear()
        assert new_option.get() == 23
        assert "Config option %s is depricated. use %s instead." % (depricated_option.name, new_option.name) not in caplog.text

        Config.load_config()  # Reset config options to default values
        assert new_option.get() != 23
        assert depricated_option.get() != 23
        Config.set(new_option.section, new_option.name, "24")
        caplog.clear()
        assert new_option.get() == 24
        assert "Config option %s is depricated. use %s instead." % (depricated_option.name, new_option.name) not in caplog.text
