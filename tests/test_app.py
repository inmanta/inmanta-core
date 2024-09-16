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

import logging
import os
import re
import signal
import subprocess
import sys
import typing
from subprocess import TimeoutExpired
from threading import Timer

import pytest

import inmanta.util
from inmanta import const
from inmanta.app import CompileSummaryReporter

LOGGER = logging.getLogger(__name__)


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
    command: str = "server",
):
    """Build an argument string for subprocess to run the orchestrator inmanta.app entrypoint"""
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
    args += ["-c", config_file, command]
    return (args, log_dir)


def do_run(args: list[str], env: typing.Optional[dict[str, str]] = None, cwd: typing.Optional[str] = None) -> subprocess.Popen:
    if env is None:
        env = {}
    LOGGER.info("Running %s with env %s and cwd %s", args, env, cwd)
    baseenv = os.environ.copy()
    baseenv.update(env)
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=baseenv)
    return process


def convert_to_ascii(text):
    return [line for line in text.decode("ascii").split("\n") if line != ""]


def do_kill(process: subprocess.Popen, killtime: int = 3, termtime: int = 2) -> tuple[str, str, int]:
    """Terminate the process after termtime and kill it after killtime"""

    def do_and_log(func, msg):
        def w():
            LOGGER.warning(msg)
            func()

        return w

    t1 = Timer(killtime, do_and_log(process.kill, f"killed process after {killtime}s"))
    t2 = Timer(termtime, do_and_log(process.terminate, f"terminated process after {termtime}s"))
    t1.start()
    t2.start()

    out, err = process.communicate()

    t1.cancel()
    t2.cancel()

    stdout = convert_to_ascii(out)
    stderr = convert_to_ascii(err)
    return (stdout, stderr, process.returncode)


def run_without_tty(
    args: list[str], env: typing.Optional[dict[str, str]] = None, killtime: int = 4, termtime: int = 3
) -> tuple[str, str, int]:
    """Run the given command without a tty"""
    process = do_run(args, env)
    return do_kill(process, killtime, termtime)


def run_with_tty(args, killtime=4, termtime=3):
    """Could not get code for actual tty to run stable in docker, so we are faking it"""
    env = {const.ENVIRON_FORCE_TTY: "true"}
    return run_without_tty(args, env=env, killtime=killtime, termtime=termtime)


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


# Log lines emitted by the --version command of inmanta.app on the cli or a log file (with logger between level and message)
INFO_MSG = r"INFO\s+[a-z\.]*\s+Discovered extensions:"
DEBUG_MSG = r"DEBUG\s+[a-z\.]*\s+Using selector: EpollSelector"
INFO_MSG_TTY = r"INFO\s+[a-z\.]*\s+\x1b\[0m\x1b\[34mDiscovered extensions:"
DEBUG_MSG_TTY = r"DEBUG\s+[a-z\.]*\s+\x1b\[0m\x1b\[34mUsing selector: EpollSelector"

# The number of v arguments provided to get this level of logs
LEVEL_WARNING = 1
LEVEL_INFO = 2
LEVEL_DEBUG = 3


@pytest.mark.parametrize_any(
    "log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines",
    [
        (LEVEL_DEBUG, False, False, [INFO_MSG, DEBUG_MSG], []),
        (LEVEL_INFO, False, False, [INFO_MSG], [DEBUG_MSG]),
        (LEVEL_DEBUG, False, True, [INFO_MSG_TTY, DEBUG_MSG_TTY], []),
        (LEVEL_INFO, False, True, [INFO_MSG_TTY], [DEBUG_MSG_TTY]),
        (LEVEL_DEBUG, True, False, [INFO_MSG, DEBUG_MSG], []),
        (LEVEL_INFO, True, False, [INFO_MSG], [DEBUG_MSG]),
        (LEVEL_DEBUG, True, True, [INFO_MSG_TTY, DEBUG_MSG_TTY], []),
        (LEVEL_INFO, True, True, [INFO_MSG_TTY], [DEBUG_MSG_TTY]),
    ],
)
@pytest.mark.timeout(20)
def test_no_log_file_set(tmpdir, log_level, timed, with_tty, regexes_required_lines, regexes_forbidden_lines):
    """Test if"""
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    (args, log_dir) = get_command(tmpdir, stdout_log_level=log_level, timed=timed, command="--version")
    if with_tty:
        (stdout, _, _) = run_with_tty(args)
    else:
        (stdout, _, _) = run_without_tty(args)
    log_file = "server.log"
    assert log_file not in os.listdir(log_dir)
    assert len(stdout) != 0
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, timed)


@pytest.mark.parametrize_any(
    "log_level,with_tty, regexes_required_lines, regexes_forbidden_lines",
    [
        (LEVEL_DEBUG, False, [INFO_MSG, DEBUG_MSG], []),
        ("DEBUG", False, [INFO_MSG, DEBUG_MSG], []),
        (LEVEL_INFO, False, [INFO_MSG], [DEBUG_MSG]),
        ("INFO", False, [INFO_MSG], [DEBUG_MSG]),
        (LEVEL_DEBUG, True, [INFO_MSG, DEBUG_MSG], []),
        (LEVEL_INFO, True, [INFO_MSG], [DEBUG_MSG]),
    ],
)
@pytest.mark.timeout(60)
def test_log_file_set(tmpdir, log_level, with_tty, regexes_required_lines, regexes_forbidden_lines):
    """Check if lines are logged correctly to file and those lines are not emited on the commandline"""
    if is_colorama_package_available() and with_tty:
        pytest.skip("Colorama is present")

    log_file = "server.log"
    (args, log_dir) = get_command(tmpdir, log_file=log_file, log_level_log_file=log_level, command="--version")
    if with_tty:
        (stdout, _, _) = run_with_tty(args)
    else:
        (stdout, _, _) = run_without_tty(args)
    assert log_file in os.listdir(log_dir)
    log_file = os.path.join(log_dir, log_file)
    with open(log_file) as f:
        log_lines = f.readlines()

    check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed=False)
    # Check if the message appears in the logs, it is not a full line match so timing is not relevant
    check_logs(stdout, [], regexes_required_lines, timed=False)


@pytest.mark.parametrize_any(
    "log_level, regexes_required_lines, regexes_forbidden_lines",
    [
        (LEVEL_DEBUG, [INFO_MSG, DEBUG_MSG], []),
        (LEVEL_INFO, [INFO_MSG], [DEBUG_MSG]),
        (LEVEL_WARNING, [], [INFO_MSG, DEBUG_MSG]),
    ],
)
@pytest.mark.timeout(60)
def test_log_stdout_log_level(log_level, regexes_required_lines, regexes_forbidden_lines):
    """Check if the inmanta command prints out the correct logs depending on the amount of provided -v flags on the CLI"""
    args = [sys.executable, "-m", "inmanta.app", "-" + "v" * log_level, "--version"]
    logging.getLogger(__name__).info("Starting inmanta: %s", args)
    (stdout, err, _) = run_without_tty(args)
    check_logs(stdout, regexes_required_lines, regexes_forbidden_lines, timed=False)


def check_logs(log_lines, regexes_required_lines, regexes_forbidden_lines, timed):
    if not log_lines:
        print("No lines logged")

    for line in log_lines:
        print(line)

    for regex in regexes_required_lines:
        if not any(re.search(regex, line) for line in log_lines):
            pytest.fail(f"Required pattern was not found in log lines: {regex}")

        if timed and not any(
            re.match(r"[\d]{4}\-[\d]{2}\-[\d]{2} [\d]{2}\:[\d]{2}\:[\d]{2}\,[\d]{3}", line) for line in log_lines
        ):
            pytest.fail("Timed log should start with timestamp.")

    for regex in regexes_forbidden_lines:
        if any(re.search(regex, line) for line in log_lines):
            pytest.fail(f"Forbidden pattern found in log lines: {regex}")


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
    int attr
end

implement Test using std::none

o = Test(attr="1234")
        """,
        autostd=True,
    )
    cwd = snippetcompiler.project_dir if cache_cf_files else "."

    output = (
        f"""Could not set attribute `attr` on instance `__config__::Test (instantiated at {cwd}/main.cf:8)` """
        f"""(reported in Construct(Test) ({cwd}/main.cf:8))
caused by:
  Invalid value '1234', expected int (reported in Construct(Test) ({cwd}/main.cf:8))
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
""",
        autostd=True,
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
    (stdout, _, _) = run_without_tty(args, killtime=10, termtime=5)
    stdout = "".join(stdout)
    assert "Starting server endpoint" in stdout
    assert f"Config directory {non_existing_dir} doesn't exist" in stdout


@pytest.mark.timeout(20)
def test_warning_min_c_option_file_doesnt_exist(snippetcompiler, tmpdir):
    non_existing_config_file = os.path.join(tmpdir, "non_existing_config_file")
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    int attr
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


def test_compiler_summary_reporter(monkeypatch, capsys) -> None:
    """
    Test whether the CompileSummaryReporter class produces correct output.
    """
    # Success
    summary_reporter = CompileSummaryReporter()
    with summary_reporter.compiler_exception.capture():
        pass
    assert not summary_reporter.is_failure()
    summary_reporter.print_summary(show_stack_traces=True)
    assert re.match(r"\n=+ SUCCESS =+\n", capsys.readouterr().err)

    # Compile failure
    summary_reporter = CompileSummaryReporter()
    with summary_reporter.compiler_exception.capture():
        raise Exception("This is a compilation failure")
    assert summary_reporter.is_failure()
    summary_reporter.print_summary(show_stack_traces=False)
    output = capsys.readouterr().err
    assert re.match(r"\n=+ COMPILATION FAILURE =+\nError: This is a compilation failure\n", output)
    assert "= EXCEPTION TRACE =" not in output
    summary_reporter.print_summary(show_stack_traces=True)
    output = capsys.readouterr().err
    assert re.match(
        r"\n=+ EXCEPTION TRACE =+\n(.|\n)*\n=+ COMPILATION FAILURE =+\nError: This is a compilation failure\n", output
    )

    # Compile failure and export failure
    summary_reporter = CompileSummaryReporter()
    with summary_reporter.compiler_exception.capture():
        raise Exception("This is a compilation failure")
    with summary_reporter.exporter_exception.capture():
        raise Exception("This is an export failure")
    assert summary_reporter.is_failure()
    summary_reporter.print_summary(show_stack_traces=False)
    output = capsys.readouterr().err
    assert re.match(r"\n=+ COMPILATION FAILURE =+\nError: This is a compilation failure\n", output)
    assert "= EXCEPTION TRACE =" not in output

    # Export failure
    summary_reporter = CompileSummaryReporter()
    with summary_reporter.compiler_exception.capture():
        pass
    with summary_reporter.exporter_exception.capture():
        raise Exception("This is an export failure")
    assert summary_reporter.is_failure()
    summary_reporter.print_summary(show_stack_traces=False)
    output = capsys.readouterr().err
    assert re.match(r"\n=+ EXPORT FAILURE =+\nError: This is an export failure\n", output)
    assert "= EXCEPTION TRACE =" not in output
    summary_reporter.print_summary(show_stack_traces=True)
    output = capsys.readouterr().err
    assert re.match(r"\n=+ EXCEPTION TRACE =+\n(.|\n)*\n=+ EXPORT FAILURE =+\nError: This is an export failure\n", output)
