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
import sys
from io import StringIO

import pytest

from inmanta.logging import InmantaLoggerConfig, MultiLineFormatter, Options


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


def test_setup_instance_with_stream():
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


def test_set_log_level():
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


def test_set_log_formatter():
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
def test_apply_options(tmpdir, log_file, log_file_level, verbose):
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


def test_logging_apply_options_2_times():
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    options1 = Options(log_file=None, log_file_level="INFO", verbose="1")
    inmanta_logger.apply_options(options1)
    with pytest.raises(Exception) as e:
        options2 = Options(log_file=None, log_file_level="INFO", verbose="2")
        inmanta_logger.apply_options(options2)
    message = "Options can only be applied once to a handler."
    assert message in str(e.value)


def test_logging_cleaned_after_apply_options(tmpdir):
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
