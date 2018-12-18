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
import conftest


def get_command(tmp_dir, stdout_log_level=None, log_file=None, log_level_log_file=None, timed=False):
    root_dir = tmp_dir.mkdir("root").strpath
    log_dir = os.path.join(root_dir, "log")
    state_dir = os.path.join(root_dir, "data")
    for directory in [log_dir, state_dir]:
        os.mkdir(directory)
    config_file = os.path.join(root_dir, "inmanta.cfg")

    port = conftest.get_free_tcp_port()

    with open(config_file, 'w+') as f:
        f.write("[config]\n")
        f.write("log-dir=" + log_dir + "\n")
        f.write("state-dir=" + state_dir + "\n")
        f.write("[database]\n")
        f.write("port-dir=" + str(port) + "\n")

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


def get_compiled_regexes(regexes, timed):
    result = []
    for regex in regexes:
        if timed:
            regex = get_timestamp_regex() + ' ' + regex
        compiled_regex = re.compile(regex)
        result.append(compiled_regex)
    return result


@pytest.mark.parametrize("log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines", [
    (3, False, False, [r'INFO[\s]+Starting server endpoint', r'DEBUG[\s]+Starting Server Rest Endpoint'], []),
    (2, False, False, [r'INFO[\s]+Starting server endpoint'], [r'DEBUG[\s]+Starting Server Rest Endpoint']),
    (3, False, True, [r'\x1b\[32mINFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint',
                      r'\x1b\[36mDEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint'], []),
    (2, False, True, [r'\x1b\[32mINFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint'],
                     [r'\x1b\[36mDEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint']),
    (3, True, False, [r'INFO[\s]+Starting server endpoint', r'DEBUG[\s]+Starting Server Rest Endpoint'], []),
    (2, True, False, [r'INFO[\s]+Starting server endpoint'], [r'DEBUG[\s]+Starting Server Rest Endpoint']),
    (3, True, True, [r'\x1b\[32mINFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint',
                     r'\x1b\[36mDEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint'], []),
    (2, True, True, [r'\x1b\[32mINFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint'],
                    [r'\x1b\[36mDEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint'])
])
def test_no_log_file_set(tmpdir, log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines):
    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, timed=timed)
    if with_tty:
        (stdout, _) = run_with_tty(args)
    else:
        (stdout, _) = run_without_tty(args)
    log_file = "server.log"
    assert log_file not in os.listdir(log_dir)
    assert len(stdout) != 0
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, timed)


@pytest.mark.parametrize("log_level, with_tty, regexes_required_lines, regexes_forbidden_lines", [
    (3, False, [r'INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint',
                r'DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint'], []),
    (2, False, [r'INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint'],
               [r'DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint']),
    (3, True, [r'INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint',
               r'DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint'], []),
    (2, True, [r'INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint'],
              [r'DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint'])
])
def test_log_file_set(tmpdir, log_level, with_tty, regexes_required_lines, regexes_forbidden_lines):
    log_file = "server.log"
    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, log_file=log_file, log_level_log_file=log_level)
    if with_tty:
        (stdout, _) = run_without_tty(args)
    else:
        (stdout, _) = run_without_tty(args)
    assert log_file in os.listdir(log_dir)
    log_file = os.path.join(log_dir, log_file)
    with open(log_file, 'r') as f:
        log_lines = f.readlines()
    check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=False)


def check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed):
    compiled_regexes_requires_lines = get_compiled_regexes(regexes_required_lines, timed)
    compiled_regexes_forbidden_lines = get_compiled_regexes(regexes_forbidden_lines, timed)
    for regex in compiled_regexes_requires_lines:
        if not any(regex.match(line) for line in log_lines):
            pytest.fail("Required pattern was not found in log lines: %s" % (regex.pattern,))
    for regex in compiled_regexes_forbidden_lines:
        if any(regex.match(line) for line in log_lines):
            pytest.fail("Forbidden pattern found in log lines: %s" % (regex.pattern,))
