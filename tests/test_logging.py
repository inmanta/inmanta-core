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

from inmanta.logging import InmantaLoggerConfig, MultiLineFormatter


def test_setup_instance():
    inmanta_logger = InmantaLoggerConfig.get_instance()
    handler = inmanta_logger.get_handler()
    assert handler.stream == sys.stdout
    assert isinstance(handler.formatter, MultiLineFormatter)
    assert handler.level == logging.INFO


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


def test_set_logfile_location(tmpdir):
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
    with open(str(log_file), "r") as f:
        contents = f.read()
        assert "This is a test message" in contents


class Options:
    def __init__(self, log_file=None, log_file_level=None, verbose=None):
        self.log_file = log_file
        self.log_file_level = log_file_level
        self.verbose = verbose
        self.timed = False


def test_apply_options(tmpdir):
    stream = StringIO()
    inmanta_logger = InmantaLoggerConfig.get_instance(stream)
    logger = logging.getLogger("test_logger")

    # test that if no log_file is given, the stream will be used with the specified verbose option
    # For verbose level 1, WARNINGs are shown INFOs not
    options1 = Options(log_file=None, log_file_level="INFO", verbose="1")
    inmanta_logger.apply_options(options1)
    logger.info("info: This is the first test")
    logger.warning("warning: This is the second test")
    log_output = stream.getvalue().strip()
    assert "test_logger              INFO    info: This is the first test" not in log_output
    assert "test_logger              WARNING warning: This is the second test" in log_output

    # test that if no log_file is given, the stream will be used with the specified verbose option
    # For verbose level 4, WARNINGs and INFOs are shown
    options2 = Options(log_file=None, log_file_level="ERROR", verbose="4")
    inmanta_logger.apply_options(options2)
    logger.warning("warning: This is the third test")
    logger.info("info: This is the forth test")
    log_output = stream.getvalue().strip()
    assert "test_logger              INFO    info: This is the forth test" in log_output
    assert "test_logger              WARNING warning: This is the third test" in log_output

    log_file = tmpdir.join("test.log")

    # test that with if a log_file is given, the logfile will be used will be used with the specified log_file_level
    # Here WARNINGs are shown INFOs not
    options3 = Options(log_file=log_file, log_file_level="WARNING", verbose="4")
    inmanta_logger.apply_options(options3)
    logger.info("info: This is the first test")
    logger.warning("warning: This is the second test")
    logger.debug("debug: This is the third test")
    with open(str(log_file), "r") as f:
        contents = f.read()
        assert "INFO     test_logger info: This is the first test" not in contents
        assert "WARNING  test_logger warning: This is the second test" in contents
        assert "DEBUG    test_logger debug: This is the third test" not in contents

    # test that with if a log_file is given, the logfile will be used will be used with the specified log_file_level
    # Here both WARNINGs and INFOs are shown
    options4 = Options(log_file=log_file, log_file_level="DEBUG", verbose="4")
    inmanta_logger.apply_options(options4)
    logger.warning("warning: This is the forth test")
    logger.info("info: This is the fifth test")
    logger.debug("debug: This is the sixth test")
    with open(str(log_file), "r") as f:
        contents = f.read()
        assert "WARNING  test_logger warning: This is the forth test" in contents
        assert "INFO     test_logger info: This is the fifth test" in contents
        assert "DEBUG    test_logger debug: This is the sixth test" in contents
