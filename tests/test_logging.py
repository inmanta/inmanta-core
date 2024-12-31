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
import sys
import uuid
from asyncio import TimeoutError, subprocess, wait_for
from io import StringIO
from typing import Optional

import pytest
import yaml

import inmanta
from inmanta import config
from inmanta.const import ENVIRON_FORCE_TTY
from inmanta.logging import InmantaLoggerConfig, LoggingConfigBuilder, MultiLineFormatter, Options, load_config_file_to_dict


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

    with pytest.raises(FileNotFoundError):
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
        match="The configuration template at .* refers to context variable 'test',"
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
        sys.stdout, Options(log_file_level="INFO", log_file="/var/log/inmanta/server.log"), component="server", context={}
    )

    assert from_config._to_dict_config() == from_file_dict


async def test_print_default_logging_cmd(inmanta_config, tmp_path):
    """
    Test that piping to file does not change the logging config
    """
    components = ["scheduler", "server", "compiler"]
    for component in components:
        args = [sys.executable, "-m", "inmanta.app", "print_default_logging_config", component]

        # Output the logging config on the CLI.
        # Here we force ENVIRON_FORCE_TTY to be set to simulate that we are on a TTY
        process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, env={ENVIRON_FORCE_TTY: "yes"})
        await process.wait()
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
        process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE)
        await process.wait()
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
