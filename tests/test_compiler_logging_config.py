"""
Copyright 2025 Inmanta

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

import os.path
import shutil
import uuid
from configparser import ConfigParser
from typing import Iterator

import pytest

from inmanta import config
from inmanta.config import Config
from inmanta.server import SLICE_SERVER
from utils import wait_for_version


@pytest.fixture
def compiler_logging_config(tmpdir, monkeypatch):
    """
    Set up the logging config for the compiler to use a specific formatter.
    """
    compiler_logging_config = """
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
    compiler_logging_config_file = os.path.join(tmpdir, "compiler.yml")
    with open(compiler_logging_config_file, "w") as fh:
        fh.write(compiler_logging_config)
    config = os.path.join(tmpdir, "logging_config.yml")
    with open(config, "w") as fh:
        fh.write(f"""
[logging]
compiler = {os.path.abspath(compiler_logging_config_file)}
        """)
    return config


@pytest.fixture(scope="function")
def inmanta_config(clean_reset, compiler_logging_config) -> Iterator[ConfigParser]:
    Config.load_config(min_c_config_file=compiler_logging_config)
    yield config.Config.get_instance()


@pytest.mark.slowtest
async def test_server_passing_compiler_logging_config(server, client, environment):
    """
    Test that the server passes down the logging config to the compiler when starting it.
    """

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(environment), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "project")

    shutil.copytree(project_source, project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w", encoding="utf-8") as fd:
        fd.write("""
        import std::testing

        host = std::Host(name="test", os=std::linux)
        std::testing::NullResource(name=host.name)
    """)

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
