"""
    Copyright 2023 Inmanta

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
import os.path
import shutil
import subprocess
import sys
import uuid
from asyncio import TimeoutError, wait_for
from asyncio.subprocess import create_subprocess_exec
from collections.abc import Mapping
from io import StringIO
from typing import Optional

import pytest
import yaml

import inmanta
from inmanta import config
from inmanta.config import compiler_log_config, logging_config
from inmanta.const import ENVIRON_FORCE_TTY
from inmanta.logging import InmantaLoggerConfig, LoggingConfigBuilder, LoggingConfigFromFile, MultiLineFormatter, Options
from inmanta.server import SLICE_SERVER
from utils import wait_for_version


def load_config_file_to_dict(file_name: str, context: Mapping[str, str]) -> dict[str, object]:
    logging_config_source = LoggingConfigFromFile(file_name=file_name)
    return logging_config_source.read_logging_config(context=context)


@pytest.fixture(autouse=True)
def cleanup_logger():
    root_log_level = logging.root.level
    InmantaLoggerConfig.clean_instance()
    yield
    # Make sure we maintain the initial root log level, so that logging in pytest works as expected.
    logging.root.setLevel(root_log_level)


def test_setup_instance():
    inmanta_logger = InmantaLoggerConfig.get_instance()
    handler = inmanta_logger.get_handler()
    assert handler.stream == sys.stdout
    assert isinstance(handler.formatter, MultiLineFormatter)
    assert handler.level == logging.INFO


def test_setup_instance_2_times():
    inmanta_logger = InmantaLoggerConfig.get_instance(sys.stderr)
    handler = inmanta_logger.get_handler()
    assert handler.stream == sys.stderr
    assert isinstance(handler.formatter, MultiLineFormatter)
    assert handler.level == logging.INFO

    inmanta_logger = InmantaLoggerConfig.get_instance(sys.stderr)
    handler = inmanta_logger.get_handler()
    assert handler.stream == sys.stderr
    assert isinstance(handler.formatter, MultiLineFormatter)
    assert handler.level == logging.INFO

    with pytest.raises(Exception) as e:
        InmantaLoggerConfig.get_instance(sys.stdout)
    message = "Instance already exists with a different stream"
    assert message in str(e.value)


def test_setup_instance_with_stream(allow_overriding_root_log_level: None):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    handler = inmanta_logger.get_handler()
    assert handler.stream == stream
    assert isinstance(handler.formatter, MultiLineFormatter)
    assert handler.level == logging.INFO

    # Log a message
    logger = logging.getLogger("test_logger")
    logger.info("This is a test message")
    log_output = stream.getvalue().strip()
    expected_output = "test_logger              INFO    This is a test message"
    assert log_output == expected_output


def test_set_log_level(allow_overriding_root_log_level: None):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    handler = inmanta_logger.get_handler()
    assert handler.level == logging.INFO

    logger = logging.getLogger("test_logger")
    expected_output = "test_logger              DEBUG   This is a test message"

    # Log a message and verify that it is not logged as the log level is too high
    logger.debug("This is a test message")
    log_output = stream.getvalue().strip()
    assert expected_output not in log_output

    # change the log_level and verify the log is visible this time.
    inmanta_logger.set_log_level("DEBUG")
    logger.debug("This is a test message")
    log_output = stream.getvalue().strip()
    assert expected_output in log_output


def test_set_log_formatter(allow_overriding_root_log_level: None):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)

    handler = inmanta_logger.get_handler()
    assert isinstance(handler.formatter, MultiLineFormatter)

    logger = logging.getLogger("test_logger")
    expected_output_format1 = "test_logger              INFO    This is a test message"
    expected_output_format2 = "test_logger - INFO - This is a test message"

    # Log a message with the default formatter
    logger.info("This is a test message")
    log_output = stream.getvalue().strip()
    assert expected_output_format1 in log_output

    # change the formatter and verify the output is different
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    inmanta_logger.set_log_formatter(formatter)
    assert inmanta_logger.get_handler().formatter == formatter

    logger.info("This is a test message")
    log_output = stream.getvalue().strip()
    assert expected_output_format2 in log_output


def test_set_logfile_location(
    tmpdir,
    allow_overriding_root_log_level: None,
):
    log_file = tmpdir.join("test.log")
    inmanta_logger = InmantaLoggerConfig.get_instance()
    inmanta_logger.set_logfile_location(str(log_file))
    handler = inmanta_logger.get_handler()
    assert isinstance(handler, logging.handlers.WatchedFileHandler)
    assert handler.baseFilename == str(log_file)

    # Log a message
    logger = logging.getLogger("test_logger")
    logger.info("This is a test message")

    # Verify the message was written to the log file
    with open(str(log_file)) as f:
        contents = f.read()
        assert "This is a test message" in contents


@pytest.mark.parametrize_any(
    "log_file, log_file_level, verbose",
    [(None, "INFO", 1), (None, "ERROR", 4), ("test.log", "WARNING", 4), ("test.log", "DEBUG", 4)],
)
def test_apply_options(tmpdir, log_file, log_file_level, verbose, allow_overriding_root_log_level: None):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    logger = logging.getLogger("test_logger")

    if log_file:
        log_file = tmpdir.join("test.log")

    options1 = Options(log_file=log_file, log_file_level=log_file_level, verbose=verbose)
    inmanta_logger.apply_options(options1)
    logger.debug("debug: This is the first test")
    logger.info("info: This is the second test")
    logger.warning("warning: This is the third test")
    logger.error("error: This is the fourth test")
    if not log_file:
        log_output = stream.getvalue().strip()
        debug_in_output = "test_logger              DEBUG   debug: This is the first test" in log_output
        info_in_output = "test_logger              INFO    info: This is the second test" in log_output
        warning_in_output = "test_logger              WARNING warning: This is the third test" in log_output
        error_in_output = "test_logger              ERROR   error: This is the fourth test" in log_output
        assert debug_in_output if int(verbose) >= 3 else not debug_in_output
        assert info_in_output if int(verbose) >= 2 else not info_in_output
        assert warning_in_output if int(verbose) >= 1 else not warning_in_output
        assert error_in_output

    else:
        with open(str(log_file)) as f:
            log_output = f.read().strip()
            debug_in_output = "DEBUG    test_logger debug: This is the first test" in log_output
            info_in_output = "INFO     test_logger info: This is the second test" in log_output
            warning_in_output = "WARNING  test_logger warning: This is the third test" in log_output
            error_in_output = "ERROR    test_logger error: This is the fourth test" in log_output
            assert debug_in_output if log_file_level in ["DEBUG"] else not debug_in_output
            assert info_in_output if log_file_level in ["DEBUG", "INFO"] else not info_in_output
            assert warning_in_output if log_file_level in ["WARNING", "INFO", "DEBUG"] else not warning_in_output
            assert error_in_output


def test_logging_apply_options_2_times(allow_overriding_root_log_level: None):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    options1 = Options(log_file=None, log_file_level="INFO", verbose="1")
    inmanta_logger.apply_options(options1)
    with pytest.raises(Exception) as e:
        options2 = Options(log_file=None, log_file_level="INFO", verbose="2")
        inmanta_logger.apply_options(options2)
    message = "Options can only be applied once to a handler."
    assert message in str(e.value)


def test_logging_cleaned_after_apply_options(tmpdir, allow_overriding_root_log_level: None):
    # verifies that when changing the stream with apply_option, the old stream is properly cleaned up
    # and not used anymore.
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    logger = logging.getLogger("test_logger")

    logger.info("This is a test message")
    log_output = stream.getvalue().strip()
    expected_output = "test_logger              INFO    This is a test message"
    assert log_output == expected_output

    log_file = tmpdir.join("test.log")

    options3 = Options(log_file=log_file, log_file_level="WARNING", verbose="4")
    inmanta_logger.apply_options(options3)
    logger.warning("warning: This is the second test")
    with open(str(log_file)) as f:
        contents = f.read()
        assert "WARNING  test_logger warning: This is the second test" in contents

    log_output = stream.getvalue().strip()
    expected_output = "test_logger              INFO    This is a test message"
    assert log_output == expected_output


def test_handling_logging_config_option(tmpdir, monkeypatch, allow_overriding_root_log_level: None) -> None:
    """
    Verify the behavior of the logging_config option.
    """
    logger = logging.getLogger("TEST")

    stream = StringIO()
    # In order to reference an object in the logging_config file, it needs to be part of a module.
    # For this reason we add the 'pytest_stream' attribute to the inmanta module. It's referenced in the
    # logging_config file using ext://inmanta.pytest_stream
    monkeypatch.setattr(inmanta, "pytest_stream", stream, raising=False)

    def write_logging_config_file(path: str, formatter: str) -> None:
        config = {
            "version": 1,
            "formatters": {
                "console_formatter": {
                    "format": formatter,
                }
            },
            "handlers": {
                "console_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "console_formatter",
                    "level": "INFO",
                    "stream": "ext://inmanta.pytest_stream",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console_handler"],
            },
            "disable_existing_loggers": False,
        }
        with open(path, "w") as fh:
            yaml.dump(config, fh)

    def setup_logging_config(cli_options: Options, file_option_value: Optional[str] = None) -> None:
        # Set/Reset config options
        config.Config._reset()
        if file_option_value:
            config.logging_config.set(file_option_value)
        # Reset/Configure logging framework
        InmantaLoggerConfig.clean_instance()
        inmanta_logger_config = InmantaLoggerConfig.get_instance()
        inmanta_logger_config.apply_options(cli_options)
        # Reset stream buffer
        stream.truncate()

    path_logging_config_file1 = os.path.join(tmpdir, "logging_config1.yml")
    path_logging_config_file2 = os.path.join(tmpdir, "logging_config2.yml")
    path_logging_config_file3 = os.path.join(tmpdir, "logging_config3.yml")

    # Set --logging-config option on CLI only
    write_logging_config_file(path=path_logging_config_file1, formatter="AAA %(message)s")
    # Also assert that the other config options are ignored when logging_config is set.
    setup_logging_config(cli_options=Options(logging_config=path_logging_config_file1, verbose=1), file_option_value=None)
    logger.info("test")
    assert "AAA test" in stream.getvalue()

    # Set logging_config option in cfg file only
    write_logging_config_file(path=path_logging_config_file1, formatter="BBB %(message)s")
    setup_logging_config(cli_options=Options(), file_option_value=path_logging_config_file1)
    logger.info("test")
    assert "BBB test" in stream.getvalue()

    # Set the logging-config config option both on CLI and cfg file. CLI option takes precedence.
    write_logging_config_file(path=path_logging_config_file1, formatter="CCC %(message)s")
    write_logging_config_file(path=path_logging_config_file2, formatter="DDD %(message)s")
    setup_logging_config(
        cli_options=Options(logging_config=path_logging_config_file1),
        file_option_value=path_logging_config_file2,
    )
    logger.info("test")
    assert "CCC test" in stream.getvalue()

    # Set the logging-config config option in the cfg config file and using the environment variable.
    # The environment variable takes precedence.
    write_logging_config_file(path=path_logging_config_file1, formatter="EEE %(message)s")
    write_logging_config_file(path=path_logging_config_file2, formatter="FFF %(message)s")
    with monkeypatch.context() as m:
        m.setenv("INMANTA_CONFIG_LOGGING_CONFIG", path_logging_config_file1)
        setup_logging_config(
            cli_options=Options(),
            file_option_value=path_logging_config_file2,
        )
        logger.info("test")
        assert "EEE test" in stream.getvalue()

    # Set the logging-config config option on the CLI, in the cfg config file and using the environment variable.
    # The CLI option takes precedence.
    write_logging_config_file(path=path_logging_config_file1, formatter="GGG %(message)s")
    write_logging_config_file(path=path_logging_config_file2, formatter="HHH %(message)s")
    write_logging_config_file(path=path_logging_config_file3, formatter="III %(message)s")
    with monkeypatch.context() as m:
        m.setenv("INMANTA_CONFIG_LOGGING_CONFIG", path_logging_config_file1)
        setup_logging_config(
            cli_options=Options(logging_config=path_logging_config_file2),
            file_option_value=path_logging_config_file3,
        )
        logger.info("test")
        assert "HHH test" in stream.getvalue()


def test_log_file_or_template(tmp_path):

    with pytest.raises(Exception, match=f"Logging config file {str(tmp_path / 'test')} doesn't exist."):
        # TODO: do we want more specific exceptions?
        load_config_file_to_dict(str(tmp_path / "test"), {})

    content_1 = {"test": "x"}
    content_2 = {"test": "{xvar}", "flah": "\n\n\n{yvar}\n", "{test}": "value"}

    f1 = tmp_path / "test.yaml"
    f2 = tmp_path / "test.yaml.tmpl"

    with open(f1, "w") as fh:
        yaml.dump(content_1, fh)

    with open(f2, "w") as fh:
        yaml.dump(content_2, fh)

    assert load_config_file_to_dict(str(f1), {}) == content_1

    with pytest.raises(
        Exception,
        match="The logging configuration template from .* refers to context variable 'test',"
        " but this variable is not available. The context is limited to xvar, yvar",
    ):
        load_config_file_to_dict(
            str(f2),
            {
                "xvar": "A",
                "yvar": "B",
            },
        )

    config = load_config_file_to_dict(str(f2), {"xvar": "A", "yvar": "B", "test": "key"})
    assert config == {"test": "A", "flah": "\n\n\nB\n", "key": "value"}

    # we control the values, so not very relevant from security perspective
    # overwrite type of injection
    config = load_config_file_to_dict(str(f2), {"xvar": "A", "yvar": "B", "test": "flah"})
    assert config == {"test": "A", "flah": "value"}

    # Full on injection
    config = load_config_file_to_dict(str(f2), {"xvar": "A", "yvar": "B", "test": "flah': 'zxxx'\ntest: zzz\nflah: zzz\n#"})
    assert config == {"test": "zzz", "flah": "zzz"}


def test_scheduler_documentation_conformance(inmanta_config, monkeypatch):
    monkeypatch.setenv(ENVIRON_FORCE_TTY, "yes")
    env = uuid.uuid4()
    from_file_dict = load_config_file_to_dict(
        os.path.join(os.path.dirname(__file__), "..", "misc/scheduler_log.yml.tmpl"), context={"environment": env}
    )
    default = LoggingConfigBuilder()
    from_config = default.get_logging_config_from_options(
        sys.stdout, Options(log_file_level="DEBUG"), component="scheduler", context={"environment": env}
    )

    assert from_config._to_dict_config() == from_file_dict


def test_server_documentation_conformance(inmanta_config, monkeypatch):
    monkeypatch.setenv(ENVIRON_FORCE_TTY, "yes")
    from_file_dict = load_config_file_to_dict(os.path.join(os.path.dirname(__file__), "..", "misc/server_log.yml"), context={})

    default = LoggingConfigBuilder()
    from_config = default.get_logging_config_from_options(
        sys.stdout,
        Options(log_file_level="INFO", log_file="/var/log/inmanta/server.log", timed=True),
        component="server",
        context={},
    )

    assert from_config._to_dict_config() == from_file_dict


def test_logging_config_content_environment_variables(monkeypatch, capsys, tmpdir) -> None:
    """
    Verify that the environment variables, that contain the content of the logging configuration,
    are correctly taken into account when loading the logging configuration.
    """
    logging_config_file = os.path.join(tmpdir, "config.yml")
    with open(logging_config_file, "w") as fh:
        fh.write(
            """
                disable_existing_loggers: false
                formatters:
                  console_formatter:
                    format: "DONT_USE -- %(message)s"
                handlers:
                  console_handler:
                    class: logging.StreamHandler
                    formatter: console_formatter
                    level: INFO
                    stream: ext://sys.stdout
                root:
                  handlers:
                  - console_handler
                  level: INFO
                version: 1
            """
        )
    logging_config.set(logging_config_file)

    # Set the INMANTA_CONFIG_LOGGING_CONFIG_TMPL environment variable and verify that it overrides
    # the logging config set via the config.logging_config configuration option.
    logging_config1 = """
        disable_existing_loggers: false
        formatters:
          console_formatter:
            format: "config1 -- {environment} -- %(message)s"
        handlers:
          console_handler:
            class: logging.StreamHandler
            formatter: console_formatter
            level: INFO
            stream: ext://sys.stdout
        root:
          handlers:
          - console_handler
          level: INFO
        version: 1
    """
    env_id = str(uuid.uuid4())
    monkeypatch.setenv("INMANTA_CONFIG_LOGGING_CONFIG_TMPL", logging_config1)
    inmanta_logging_config = InmantaLoggerConfig.get_instance(stream=sys.stdout)
    inmanta_logging_config.apply_options(options=Options(), component="server", context={"environment": env_id})
    logger = logging.getLogger("test")
    capsys.readouterr()  # Clear buffer
    logger.info("test")
    captured = capsys.readouterr()
    assert f"config1 -- {env_id} -- test" in captured.out

    # Set the component-specific template and verify that it overrides the config from INMANTA_CONFIG_LOGGING_CONFIG_TMPL
    logging_config2 = """
        disable_existing_loggers: false
        formatters:
          console_formatter:
            format: "config2 -- {environment} -- %(message)s"
        handlers:
          console_handler:
            class: logging.StreamHandler
            formatter: console_formatter
            level: INFO
            stream: ext://sys.stdout
        root:
          handlers:
          - console_handler
          level: INFO
        version: 1
    """
    monkeypatch.setenv("INMANTA_LOGGING_SERVER_TMPL", logging_config2)
    inmanta_logging_config.clean_instance()
    inmanta_logging_config = InmantaLoggerConfig.get_instance(stream=sys.stdout)
    inmanta_logging_config.apply_options(options=Options(), component="server", context={"environment": env_id})
    logger = logging.getLogger("test")
    capsys.readouterr()  # Clear buffer
    logger.info("test")
    captured = capsys.readouterr()
    assert f"config2 -- {env_id} -- test" in captured.out

    # Set INMANTA_LOGGING_SERVER_TMPL AND INMANTA_LOGGING_SERVER_CONTENT simultaneously.
    # Assert that INMANTA_LOGGING_SERVER_CONTENT is used.
    logging_config3 = """
        disable_existing_loggers: false
        formatters:
          console_formatter:
            format: "config3 -- {environment} -- %(message)s"
        handlers:
          console_handler:
            class: logging.StreamHandler
            formatter: console_formatter
            level: INFO
            stream: ext://sys.stdout
        root:
          handlers:
          - console_handler
          level: INFO
        version: 1
    """
    monkeypatch.setenv("INMANTA_LOGGING_SERVER_CONTENT", logging_config3)
    inmanta_logging_config.clean_instance()
    inmanta_logging_config = InmantaLoggerConfig.get_instance(stream=sys.stdout)
    inmanta_logging_config.apply_options(options=Options(), component="server", context={"environment": env_id})
    captured = capsys.readouterr()
    assert (
        "Environment variables INMANTA_LOGGING_SERVER_CONTENT and INMANTA_LOGGING_SERVER_TMPL are set simultaneously."
        " Using INMANTA_LOGGING_SERVER_CONTENT" in captured.out
    )
    logger = logging.getLogger("test")
    logger.info("test")
    captured = capsys.readouterr()
    assert "config3 -- {environment} -- test" in captured.out

    # Verify that the --logging-config CLI option still overrides all other config.
    other_logging_config_file = os.path.join(tmpdir, "cli.yml")
    with open(other_logging_config_file, "w") as fh:
        fh.write(
            """
                disable_existing_loggers: false
                formatters:
                  console_formatter:
                    format: "CLI -- %(message)s"
                handlers:
                  console_handler:
                    class: logging.StreamHandler
                    formatter: console_formatter
                    level: INFO
                    stream: ext://sys.stdout
                root:
                  handlers:
                  - console_handler
                  level: INFO
                version: 1
            """
        )
    inmanta_logging_config.clean_instance()
    inmanta_logging_config = InmantaLoggerConfig.get_instance(stream=sys.stdout)
    inmanta_logging_config.apply_options(
        options=Options(logging_config=other_logging_config_file), component="server", context={"environment": env_id}
    )
    logger = logging.getLogger("test")
    capsys.readouterr()  # Clear buffer
    logger.info("test")
    captured = capsys.readouterr()
    assert "CLI -- test" in captured.out


async def test_print_default_logging_cmd(inmanta_config, tmp_path):
    """
    Test that piping to file does not change the logging config
    """
    components = ["scheduler", "server", "compiler"]
    for component in components:
        args = [sys.executable, "-m", "inmanta.app", "print-default-logging-config", component]

        # Output the logging config on the CLI.
        # Here we force ENVIRON_FORCE_TTY to be set to simulate that we are on a TTY
        process = await create_subprocess_exec(*args, stdout=subprocess.PIPE, env={ENVIRON_FORCE_TTY: "yes"})
        try:
            (stdout, _) = await wait_for(process.communicate(), timeout=5)
        except TimeoutError as e:
            process.kill()
            await process.communicate()
            raise e
        assert process.returncode == 0

        tty_config_stdout = stdout.decode("utf-8")
        # Assert that TTY was present
        assert "no_color: false" in tty_config_stdout
        assert "reset: true" in tty_config_stdout
        assert "log_colors: null" not in tty_config_stdout

        # Output the logging config on the CLI with TTY unset
        # This is the same as piping to a file
        assert "ENVIRON_FORCE_TTY" not in os.environ
        process = await create_subprocess_exec(*args, stdout=subprocess.PIPE)
        try:
            (stdout, _) = await wait_for(process.communicate(), timeout=5)
        except TimeoutError as e:
            process.kill()
            await process.communicate()
            raise e
        assert process.returncode == 0

        normal_config_stdout = stdout.decode("utf-8")
        # Assert that the outputs are equal
        assert normal_config_stdout == tty_config_stdout





@pytest.fixture
def compiler_logging_config():
    logging_config = """
            disable_existing_loggers: false
            formatters:
              console_formatter:
                format: "COMPILER_CONFIG_FLAG -- %(message)s"
            handlers:
              console_handler:
                class: logging.StreamHandler
                formatter: console_formatter
                level: DEBUG
                stream: ext://sys.stdout
            root:
              handlers:
              - console_handler
              level: INFO
            version: 1
        """
    yield logging_config

@pytest.fixture
def setup_compiler_logging_via_env_var(compiler_logging_config, tmpdir, monkeypatch):
    monkeypatch.setenv("INMANTA_LOGGING_COMPILER_CONTENT", compiler_logging_config)

@pytest.fixture
def setup_compiler_logging(compiler_logging_config, tmpdir, monkeypatch):
    compiler_logging_config_file = os.path.join(tmpdir, "config.yml")
    with open(compiler_logging_config_file, "w") as fh:
        fh.write(compiler_logging_config)
    compiler_log_config.set(compiler_logging_config_file)
@pytest.mark.slowtest
async def test_server_passing_compiler_logging_config(setup_compiler_logging, server, client, environment):
    """
    Test that the server passes down the logging config to the compiler when starting it.
    """

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(environment), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "project")

    shutil.copytree(project_source, project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w", encoding="utf-8") as fd:
        fd.write(
            """
        import std::testing

        host = std::Host(name="test", os=std::linux)
        std::testing::NullResource(name=host.name)
    """
        )

    result = await client.notify_change(environment)
    assert result.code == 200

    versions = await wait_for_version(client, environment, 1, compile_timeout=40)
    assert versions["versions"][0]["total"] == 1
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "api"

    reports = await client.get_reports(environment)
    assert reports.code == 200
    assert len(reports.result["reports"]) == 1
    compile_id = reports.result["reports"][0]["id"]

    report = await client.get_report(uuid.UUID(compile_id))
    assert report.code == 200

    # Get the compile outstream
    for report in report.result["report"]["reports"]:
        if report["name"] == "Recompiling configuration model":
            compile_outstream = report["outstream"]
            assert "COMPILER_CONFIG_FLAG -- Starting compile" in compile_outstream
            break
    else:
        assert False, "Compile report doesn't contain a 'Recompiling configuration model' section."
