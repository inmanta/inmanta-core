"""
    Copyright 2018 Inmanta

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

import sys
import os
import subprocess
import time
import pytest
import re
import pty


def get_command(tmp_dir, stdout_log_level=None, log_file=None, log_level_log_file=None, timed=False):
    root_dir = tmp_dir.mkdir("root").strpath
    log_dir = os.path.join(root_dir, "log")
    state_dir = os.path.join(root_dir, "data")
    for directory in [log_dir, state_dir]:
        os.mkdir(directory)
    config_file = os.path.join(root_dir, "inmanta.cfg")
    with open(config_file, 'w+') as f:
        f.write("[config]\n")
        f.write("log-dir=" + log_dir + "\n")
        f.write("state-dir=" + state_dir + "\n")
    args = [sys.executable, "-m", "inmanta.app"]
    if stdout_log_level:
        args.append("-" + "v" * stdout_log_level)
    if log_file:
        log_file = os.path.join(log_dir, log_file)
        args += ["--log-file", log_file]
    if log_file and log_level_log_file:
        args += ["--log-file-level", str(log_level_log_file)]
    if timed:
        args += ["--timed-logs"]
    args += ["-c", config_file, "server"]
    return (args, log_dir)


def run_without_tty(args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    process.kill()

    def convert_to_ascii(lines):
        return [line.decode('ascii') for line in lines if line != ""]

    stdout = convert_to_ascii(process.stdout.readlines())
    stderr = convert_to_ascii(process.stderr.readlines())
    return (stdout, stderr)


def run_with_tty(args):

    def read(fd):
        result = ""
        while True:
            try:
                data = os.read(fd, 1024)
            except OSError:
                break
            if data == "":
                break
            result += data.decode('ascii')
        return result

    master, slave = pty.openpty()
    process = subprocess.Popen(' '.join(args), stdin=slave, stdout=slave, stderr=slave, shell=True)
    os.close(slave)
    time.sleep(2)  # Wait for some log lines
    process.kill()
    stdout = read(master)
    stdout = stdout.split('\n')
    os.close(master)
    return (stdout, '')


def get_timestamp_regex():
    return r'[\d]{4}\-[\d]{2}\-[\d]{2} [\d]{2}\:[\d]{2}\:[\d]{2}\,[\d]{3}'


@pytest.mark.parametrize("log_level, timed, with_tty, allowed_log_line_prefixes, invalid_log_line_prefixes", [
    (3, False, False, ["ERROR ", "WARNING ", "INFO ", "DEBUG "], []),
    (2, False, False, ["ERROR ", "WARNING ", "INFO "], ["DEBUG"]),
    (3, True, False, ["ERROR ", "WARNING ", "INFO ", "DEBUG "], []),
    (2, True, False, ["ERROR ", "WARNING ", "INFO "], ["DEBUG"]),
    (3, False, True, [r'\x1b\[31mERROR ', r'\x1b\[33mWARNING ', r'\x1b\[32mINFO ', r'\x1b\[36mDEBUG '], []),
    (2, False, True, [r'\x1b\[31mERROR ', r'\x1b\[33mWARNING ', r'\x1b\[32mINFO '], [r'\x1b\[36mDEBUG ']),
    (3, True, True, [r'\x1b\[31mERROR ', r'\x1b\[33mWARNING ', r'\x1b\[32mINFO ', r'\x1b\[36mDEBUG '], []),
    (2, True, True, [r'\x1b\[31mERROR ', r'\x1b\[33mWARNING ', r'\x1b\[32mINFO '], [r'\x1b\[36mDEBUG '])
])
def test_no_log_file_set(tmpdir, log_level, timed, with_tty, allowed_log_line_prefixes, invalid_log_line_prefixes):
    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, timed=timed)
    if with_tty:
        (stdout, stderr) = run_with_tty(args)
    else:
        (stdout, stderr) = run_without_tty(args)
    assert os.listdir(log_dir) == []
    assert len(stdout) != 0
    assert len(stderr) == 0

    def get_compiled_regex(prefixes):
        regex = '(' + '|'.join(prefixes) + ')'
        if timed:
            regex = get_timestamp_regex() + ' ' + regex
        return re.compile(regex)

    reg_allowed = get_compiled_regex(allowed_log_line_prefixes)
    if len(invalid_log_line_prefixes) > 0:
        reg_invalid = get_compiled_regex(invalid_log_line_prefixes)
    for line in stdout:
        if len(line) > 0:
            assert reg_allowed.match(line) is not None
            if len(invalid_log_line_prefixes) > 0:
                assert reg_invalid.match(line) is None


@pytest.mark.parametrize("log_level, with_tty, allowed_log_line_prefixes, invalid_log_line_prefixes", [
    (3, False, ["ERROR ", "WARNING ", "INFO ", "DEBUG "], []),
    (2, False, ["ERROR ", "WARNING ", "INFO "], ["DEBUG"]),
    (3, True, ["ERROR ", "WARNING ", "INFO ", "DEBUG "], []),
    (2, True, ["ERROR ", "WARNING ", "INFO "], ["DEBUG"])
])
def test_log_file_set(tmpdir, log_level, with_tty, allowed_log_line_prefixes, invalid_log_line_prefixes):
    log_file = "server.log"
    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, log_file=log_file, log_level_log_file=log_level)
    if with_tty:
        (stdout, stderr) = run_without_tty(args)
    else:
        (stdout, stderr) = run_without_tty(args)
    assert os.listdir(log_dir) == [log_file]
    assert len(stdout) == 0
    assert len(stderr) == 0
    log_file = os.path.join(log_dir, log_file)

    def get_compiled_regex(prefixes):
        regex_valid_prefixes = get_timestamp_regex() + ' (' + '|'.join(prefixes) + ')'
        return re.compile(regex_valid_prefixes)

    reg_allowed = get_compiled_regex(allowed_log_line_prefixes)
    if len(invalid_log_line_prefixes) > 0:
        reg_invalid = get_compiled_regex(invalid_log_line_prefixes)
    with open(log_file, 'r') as f:
        for line in f:
            assert reg_allowed.match(line) is not None
            if len(invalid_log_line_prefixes) > 0:
                assert reg_invalid.match(line) is None
