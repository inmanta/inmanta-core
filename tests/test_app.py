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
import pytest
import re
from threading import Timer

import inmanta.util
from inmanta import const
import signal
from subprocess import TimeoutExpired


def get_command(
    tmp_dir, stdout_log_level=None, log_file=None, log_level_log_file=None, timed=False
):
    root_dir = tmp_dir.mkdir("root").strpath
    log_dir = os.path.join(root_dir, "log")
    state_dir = os.path.join(root_dir, "data")
    for directory in [log_dir, state_dir]:
        os.mkdir(directory)
    config_file = os.path.join(root_dir, "inmanta.cfg")

    port = inmanta.util.get_free_tcp_port()

    with open(config_file, "w+") as f:
        f.write("[config]\n")
        f.write("log-dir=" + log_dir + "\n")
        f.write("state-dir=" + state_dir + "\n")
        f.write("[database]\n")
        f.write("port=" + str(port) + "\n")

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


def do_run(args, env={}, cwd=None):
    baseenv = os.environ.copy()
    baseenv.update(env)
    process = subprocess.Popen(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=baseenv
    )
    return process


def convert_to_ascii(text):
    return [line for line in text.decode("ascii").split("\n") if line != ""]


def do_kill(process, killtime=3, termtime=2):
    def do_and_log(func, msg):
        def w():
            print(msg)
            func()

        return w

    t1 = Timer(killtime, do_and_log(process.kill, "killed process"))
    t2 = Timer(termtime, do_and_log(process.terminate, "terminated process"))
    t1.start()
    t2.start()

    out, err = process.communicate()

    print(process.returncode)

    t1.cancel()
    t2.cancel()

    stdout = convert_to_ascii(out)
    stderr = convert_to_ascii(err)
    return (stdout, stderr)


def run_without_tty(args, env={}, killtime=3, termtime=2):
    process = do_run(args, env)
    return do_kill(process, killtime, termtime)


def run_with_tty(args):
    """Could not get code for actual tty to run stable in docker, so we are faking it """
    env = {const.ENVIRON_FORCE_TTY: "true"}
    return run_without_tty(args, env=env)


def get_timestamp_regex():
    return r"[\d]{4}\-[\d]{2}\-[\d]{2} [\d]{2}\:[\d]{2}\:[\d]{2}\,[\d]{3}"


def get_compiled_regexes(regexes, timed):
    result = []
    for regex in regexes:
        if timed:
            regex = get_timestamp_regex() + " " + regex
        compiled_regex = re.compile(regex)
        result.append(compiled_regex)
    return result


def is_colorama_package_available():
    try:
        import colorama  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def test_verify_that_colorama_package_is_not_present():
    """
        The colorama package turns the colored characters in TTY-based terminal into uncolored characters.
        As such, this package should not be present.
    """
    assert not is_colorama_package_available()


@pytest.mark.parametrize(
    "log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines",
    [
        (
            3,
            False,
            False,
            [
                r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint",
                r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            False,
            False,
            [r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint"],
            [r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint"],
        ),
        (
            3,
            False,
            True,
            [
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint",
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            False,
            True,
            [
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint"
            ],
            [
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint"
            ],
        ),
        (
            3,
            True,
            False,
            [
                r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint",
                r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            True,
            False,
            [r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint"],
            [r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint"],
        ),
        (
            3,
            True,
            True,
            [
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint",
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            True,
            True,
            [
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m \x1b\[34mStarting server endpoint"
            ],
            [
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m \x1b\[34mStarting Server Rest Endpoint"
            ],
        ),
    ],
)
@pytest.mark.timeout(20)
def test_no_log_file_set(
    tmpdir, log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines
):
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, timed=timed)
    if with_tty:
        (stdout, _) = run_with_tty(args)
    else:
        (stdout, _) = run_without_tty(args)
    log_file = "server.log"
    assert log_file not in os.listdir(log_dir)
    assert len(stdout) != 0
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, timed)


@pytest.mark.parametrize(
    "log_level, with_tty, regexes_required_lines, regexes_forbidden_lines",
    [
        (
            3,
            False,
            [
                r"[a-z.]*[ ]*INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint",
                r"[a-z.]*[ ]*DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            False,
            [r"[a-z.]*[ ]*INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint"],
            [r"[a-z.]*[ ]*DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint"],
        ),
        (
            3,
            True,
            [
                r"[a-z.]*[ ]*INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint",
                r"[a-z.]*[ ]*DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            True,
            [r"[a-z.]*[ ]*INFO[\s]+[a-x\.A-Z]*[\s]Starting server endpoint"],
            [r"[a-z.]*[ ]*DEBUG[\s]+[a-x\.A-Z]*[\s]Starting Server Rest Endpoint"],
        ),
    ],
)
@pytest.mark.timeout(60)
def test_log_file_set(
    tmpdir, log_level, with_tty, regexes_required_lines, regexes_forbidden_lines
):
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    log_file = "server.log"
    (args, log_dir) = get_command(
        tmpdir,
        stdout_log_level=log_level,
        log_file=log_file,
        log_level_log_file=log_level,
    )
    if with_tty:
        (stdout, _) = run_with_tty(args)
    else:
        (stdout, _) = run_without_tty(args)
    assert log_file in os.listdir(log_dir)
    log_file = os.path.join(log_dir, log_file)
    with open(log_file, "r") as f:
        log_lines = f.readlines()
    check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=False)


def check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed):
    compiled_regexes_requires_lines = get_compiled_regexes(
        regexes_required_lines, timed
    )
    compiled_regexes_forbidden_lines = get_compiled_regexes(
        regexes_forbidden_lines, timed
    )
    for line in log_lines:
        print(line)
    for regex in compiled_regexes_requires_lines:
        if not any(regex.match(line) for line in log_lines):
            pytest.fail(
                "Required pattern was not found in log lines: %s" % (regex.pattern,)
            )
    for regex in compiled_regexes_forbidden_lines:
        if any(regex.match(line) for line in log_lines):
            pytest.fail("Forbidden pattern found in log lines: %s" % (regex.pattern,))


def test_check_shutdown():
    process = do_run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py")]
    )
    # wait for handler to be in place
    try:
        process.communicate(timeout=2)
    except TimeoutExpired:
        pass
    process.send_signal(signal.SIGUSR1)
    out, err = do_kill(process, killtime=6, termtime=3)
    print(out, err)
    assert "----- Thread Dump ----" in out
    assert "STOP" in out
    assert "SHUTDOWN COMPLETE" in out


def test_check_bad_shutdown():
    print(
        [sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py"), "bad"]
    )
    process = do_run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py"), "bad"]
    )
    out, err = do_kill(process, killtime=5, termtime=2)
    print(out, err)
    assert "----- Thread Dump ----" in out
    assert "STOP" not in out
    assert "SHUTDOWN COMPLETE" not in out


def test_compiler_exception_output(snippetcompiler):
    snippetcompiler.setup_for_snippet_external(
        """
entity Test:
    number attr
end

implement Test using std::none

o = Test(attr="1234")
"""
    )

    output = """Could not set attribute `attr` on instance `__config__::Test (instantiated at ./main.cf:8)` """ \
        """(reported in Construct(Test) (./main.cf:8))
caused by:
  Invalid value '1234', expected Number (reported in Construct(Test) (./main.cf:8))
"""

    def exec(*cmd):
        process = do_run(
            [sys.executable, "-m", "inmanta.app"] + list(cmd),
            cwd=snippetcompiler.project_dir,
        )
        out, err = process.communicate(timeout=5)
        assert out.decode() == ""
        assert err.decode() == output

    exec("compile")
    exec("export", "-J", "out.json")
