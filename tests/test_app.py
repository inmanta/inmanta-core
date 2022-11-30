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

import os
import re
import signal
import subprocess
import sys
from subprocess import TimeoutExpired
from threading import Timer

import pytest

import inmanta.util
from inmanta import const


def get_command(
    tmp_dir,
    stdout_log_level=None,
    log_file=None,
    log_level_log_file=None,
    timed=False,
    dbport=None,
    dbname="inmanta",
    dbhost=None,
    dbuser=None,
    dbpass=None,
    config_dir=None,
    server_extensions=[],
    version=False,
):
    root_dir = tmp_dir.mkdir("root").strpath
    log_dir = os.path.join(root_dir, "log")
    state_dir = os.path.join(root_dir, "data")
    for directory in [log_dir, state_dir]:
        os.mkdir(directory)
    config_file = os.path.join(root_dir, "inmanta.cfg")

    if dbport is not None:
        port = dbport
    else:
        port = inmanta.util.get_free_tcp_port()

    with open(config_file, "w+", encoding="utf-8") as f:
        f.write("[config]\n")
        f.write("log-dir=" + log_dir + "\n")
        f.write("state-dir=" + state_dir + "\n")
        f.write("[database]\n")
        f.write("port=" + str(port) + "\n")
        f.write("name=" + dbname + "\n")
        if dbhost:
            f.write(f"host={dbhost}\n")
        if dbuser:
            f.write(f"username={dbuser}\n")
        if dbpass:
            f.write(f"password={dbpass}\n")
        f.write("[server]\n")
        f.write(f"enabled_extensions={', '.join(server_extensions)}\n")

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
    if config_dir:
        args += ["--config-dir", config_dir]
    if version:
        args += ["--version"]
    args += ["-c", config_file, "server"]
    return (args, log_dir)


def do_run(args, env={}, cwd=None):
    baseenv = os.environ.copy()
    baseenv.update(env)
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=baseenv)
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

    t1.cancel()
    t2.cancel()

    stdout = convert_to_ascii(out)
    stderr = convert_to_ascii(err)
    return (stdout, stderr, process.returncode)


def run_without_tty(args, env={}, killtime=3, termtime=2):
    process = do_run(args, env)
    return do_kill(process, killtime, termtime)


def run_with_tty(args, killtime=3, termtime=2):
    """Could not get code for actual tty to run stable in docker, so we are faking it"""
    env = {const.ENVIRON_FORCE_TTY: "true"}
    return run_without_tty(args, env=env, killtime=killtime, termtime=termtime)


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


@pytest.mark.parametrize_any(
    "log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines",
    [
        (
            3,
            False,
            False,
            [r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint", r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint"],
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
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m\x1b\[34mStarting server endpoint",
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m\x1b\[34mStarting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            False,
            True,
            [r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m\x1b\[34mStarting server endpoint"],
            [r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m\x1b\[34mStarting Server Rest Endpoint"],
        ),
        (
            3,
            True,
            False,
            [r"[a-z.]*[ ]*INFO[\s]+Starting server endpoint", r"[a-z.]*[ ]*DEBUG[\s]+Starting Server Rest Endpoint"],
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
                r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m\x1b\[34mStarting server endpoint",
                r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m\x1b\[34mStarting Server Rest Endpoint",
            ],
            [],
        ),
        (
            2,
            True,
            True,
            [r"\x1b\[32m[a-z.]*[ ]*INFO[\s]*\x1b\[0m\x1b\[34mStarting server endpoint"],
            [r"\x1b\[36m[a-z.]*[ ]*DEBUG[\s]*\x1b\[0m\x1b\[34mStarting Server Rest Endpoint"],
        ),
    ],
)
@pytest.mark.timeout(20)
def test_no_log_file_set(tmpdir, log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines):
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, timed=timed)
    if with_tty:
        (stdout, _, _) = run_with_tty(args)
    else:
        (stdout, _, _) = run_without_tty(args)
    log_file = "server.log"
    assert log_file not in os.listdir(log_dir)
    assert len(stdout) != 0
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, timed)


@pytest.mark.parametrize_any(
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
def test_log_file_set(tmpdir, log_level, with_tty, regexes_required_lines, regexes_forbidden_lines):
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    log_file = "server.log"
    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, log_file=log_file, log_level_log_file=log_level)
    if with_tty:
        (stdout, _, _) = run_with_tty(args)
    else:
        (stdout, _, _) = run_without_tty(args)
    assert log_file in os.listdir(log_dir)
    log_file = os.path.join(log_dir, log_file)
    with open(log_file, "r") as f:
        log_lines = f.readlines()
    check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=True)
    check_logs(stdout, [], regexes_required_lines, timed=False)


def check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed):
    compiled_regexes_requires_lines = get_compiled_regexes(regexes_required_lines, timed)
    compiled_regexes_forbidden_lines = get_compiled_regexes(regexes_forbidden_lines, timed)
    for line in log_lines:
        print(line)
    for regex in compiled_regexes_requires_lines:
        if not any(regex.match(line) for line in log_lines):
            pytest.fail("Required pattern was not found in log lines: %s" % (regex.pattern,))
    for regex in compiled_regexes_forbidden_lines:
        if any(regex.match(line) for line in log_lines):
            pytest.fail("Forbidden pattern found in log lines: %s" % (regex.pattern,))


def test_check_shutdown():
    process = do_run([sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py")])
    # wait for handler to be in place
    try:
        process.communicate(timeout=2)
    except TimeoutExpired:
        pass
    process.send_signal(signal.SIGUSR1)
    out, err, code = do_kill(process, killtime=3, termtime=1)
    print(out, err)
    assert code == 0
    assert "----- Thread Dump ----" in out
    assert "STOP" in out
    assert "SHUTDOWN COMPLETE" in out


def test_check_bad_shutdown():
    print([sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py"), "bad"])
    process = do_run([sys.executable, os.path.join(os.path.dirname(__file__), "miniapp.py"), "bad"])
    out, err, code = do_kill(process, killtime=5, termtime=2)
    print(out, err)
    assert code == 3
    assert "----- Thread Dump ----" in out
    assert "STOP" not in out
    assert "SHUTDOWN COMPLETE" not in out


def test_startup_failure(tmpdir, postgres_db, database_name):
    (args, log_dir) = get_command(
        tmpdir,
        dbport=postgres_db.port,
        dbname=database_name,
        dbhost=postgres_db.host,
        dbuser=postgres_db.user,
        dbpass=postgres_db.password,
        server_extensions=["badplugin"],
    )
    pp = ":".join(sys.path)
    # Add a bad module
    extrapath = os.path.join(os.path.dirname(__file__), "data", "bad_module_path")
    (stdout, stderr, code) = run_without_tty(args, env={"PYTHONPATH": pp + ":" + extrapath}, killtime=15, termtime=10)
    assert "inmanta                  ERROR   Server setup failed" in stdout
    assert (
        "                                 " + "inmanta.server.protocol.SliceStartupException: Slice badplugin.badslice "
        "failed to start because: Too bad, this plugin is broken"
    ) in stdout
    assert code == 4


@pytest.mark.parametrize("cache_cf_files", [True, False])
def test_compiler_exception_output(snippetcompiler, cache_cf_files):
    """
    This test case is also used to test the caching (issue 3838)
    Since this is a basic smoke test for argument parsing, no assertion
    about the caching is done here.
    """
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number attr
end

implement Test using std::none

o = Test(attr="1234")
        """
    )
    cwd = snippetcompiler.project_dir if cache_cf_files else "."

    output = (
        f"""Could not set attribute `attr` on instance `__config__::Test (instantiated at {cwd}/main.cf:8)` """
        f"""(reported in Construct(Test) ({cwd}/main.cf:8))
caused by:
  Invalid value '1234', expected Number (reported in Construct(Test) ({cwd}/main.cf:8))
"""
    )

    def exec(*cmd):
        process = do_run([sys.executable, "-m", "inmanta.app"] + list(cmd), cwd=snippetcompiler.project_dir)
        _, err = process.communicate(timeout=30)
        assert output in err.decode()

    no_cache_option = [] if cache_cf_files else ["--no-cache"]

    cl_compile = ["compile"] + no_cache_option
    cl_export = ["export", "-J", "out.json"] + no_cache_option

    exec(*cl_compile)
    exec(*cl_export)


@pytest.mark.timeout(15)
@pytest.mark.parametrize_any(
    "cmd", [(["-X", "compile"]), (["compile", "-X"]), (["compile"]), (["export", "-X"]), (["-X", "export"]), (["export"])]
)
def test_minus_x_option(snippetcompiler, cmd):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    nuber attr
end
"""
    )

    process = do_run([sys.executable, "-m", "inmanta.app"] + cmd, cwd=snippetcompiler.project_dir)
    out, err = process.communicate(timeout=30)
    if "-X" in cmd:
        assert "inmanta.ast.TypeNotFoundException: could not find type nuber in namespace" in str(err)
    else:
        assert "inmanta.ast.TypeNotFoundException: could not find type nuber in namespace" not in str(err)


@pytest.mark.timeout(20)
def test_warning_config_dir_option_on_server_command(tmpdir):
    non_existing_dir = os.path.join(tmpdir, "non_existing_dir")
    assert not os.path.isdir(non_existing_dir)
    (args, _) = get_command(tmpdir, stdout_log_level=3, config_dir=non_existing_dir)
    (stdout, _, _) = run_without_tty(args)
    stdout = "".join(stdout)
    assert "Starting server endpoint" in stdout
    assert f"Config directory {non_existing_dir} doesn't exist" in stdout


@pytest.mark.timeout(20)
def test_warning_min_c_option_file_doesnt_exist(snippetcompiler, tmpdir):
    non_existing_config_file = os.path.join(tmpdir, "non_existing_config_file")
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number attr
end
"""
    )
    config_options = ["-c", non_existing_config_file, "-vvv"]
    args = [sys.executable, "-m", "inmanta.app"] + config_options + ["compile"]
    process = do_run(args, cwd=snippetcompiler.project_dir)
    out, err = process.communicate(timeout=30)
    assert process.returncode == 0

    out = out.decode()
    err = err.decode()
    all_output = out + err

    assert "Starting compile" in all_output
    assert "Compile done" in all_output
    assert f"Config file {non_existing_config_file} doesn't exist" in all_output


@pytest.mark.parametrize_any(
    "with_tty, version_should_be_shown, regexes_required_lines, regexes_forbidden_lines",
    [
        (False, True, [r"Inmanta Service Orchestrator", r"Compiler version: ", r"Extensions:", r"\s*\* core:"], []),
        (True, True, [r"Inmanta Service Orchestrator", r"Compiler version: ", r"Extensions:", r"\s*\* core:"], []),
        (False, False, [], [r"Inmanta Service Orchestrator", r"Compiler version: ", r"Extensions:", r"\s*\* core:"]),
        (True, False, [], [r"Inmanta Service Orchestrator", r"Compiler version: ", r"Extensions:", r"\s*\* core:"]),
    ],
)
@pytest.mark.timeout(20)
def test_version_argument_is_set(tmpdir, with_tty, version_should_be_shown, regexes_required_lines, regexes_forbidden_lines):
    (args, log_dir) = get_command(tmpdir, version=version_should_be_shown)
    if with_tty:
        (stdout, _, _) = run_with_tty(args, killtime=15, termtime=10)
    else:
        (stdout, _, _) = run_without_tty(args, killtime=15, termtime=10)
    assert len(stdout) != 0
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, False)


def test_init_project(tmpdir):
    args = [sys.executable, "-m", "inmanta.app", "project", "init", "-n", "test-project", "-o", tmpdir, "--default"]
    (stdout, stderr, return_code) = run_without_tty(args, killtime=15, termtime=10)
    test_project_path = os.path.join(tmpdir, "test-project")
    assert return_code == 0
    assert os.path.exists(test_project_path)
    (stdout, stderr, return_code) = run_without_tty(args, killtime=15, termtime=10)
    assert return_code != 0
    assert any("already exists" in error for error in stderr)
