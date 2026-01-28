"""
Copyright 2021 Inmanta

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

import asyncio
import base64
import configparser
import datetime
import enum
import functools
import json
import logging
import math
import os
import pathlib
import queue
import random
import re
import shutil
import uuid
from collections import abc
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timezone
from logging import LogRecord
from typing import TYPE_CHECKING, Any, Collection, Mapping, Optional, Set, TypeVar, Union

import pytest
import yaml
from tornado import httpclient
from tornado.httpclient import HTTPRequest

import build
import build.env
import inmanta.util
import packaging.requirements
import packaging.version
from _pytest.mark import MarkDecorator
from inmanta import config, const, data, env, module, protocol, util
from inmanta.agent import config as cfg
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ExecutorBlueprint, ModuleInstallSpec
from inmanta.const import AGENT_SCHEDULER_ID
from inmanta.data.model import LEGACY_PIP_DEFAULT, AuthMethod, PipConfig, SchedulerStatusReport
from inmanta.deploy import state
from inmanta.deploy.scheduler import ResourceScheduler
from inmanta.deploy.state import ResourceIntent
from inmanta.moduletool import ModuleTool
from inmanta.protocol import Client, SessionEndpoint, methods, methods_v2
from inmanta.protocol.auth import auth, policy_engine
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.config import AuthorizationProviderName, server_auth_method
from inmanta.server.extensions import ProductMetadata
from inmanta.server.services.compilerservice import CompilerService
from inmanta.types import Apireturn, ResourceIdStr
from inmanta.util import hash_file
from libpip2pi.commands import dir2pi

T = TypeVar("T")

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from conftest import CompileRunnerMock


def get_all_subclasses(cls: type[T]) -> set[type[T]]:
    """
    Returns all loaded subclasses of any depth for a given class. Includes the class itself.
    """
    return {cls}.union(*(get_all_subclasses(sub) for sub in cls.__subclasses__()))


async def retry_limited(
    fun: Union[abc.Callable[..., bool], abc.Callable[..., abc.Awaitable[bool]]],
    timeout: float,
    interval: float = 0.1,
    *args: object,
    **kwargs: object,
) -> None:
    try:
        await util.retry_limited(fun, timeout, interval, *args, **kwargs)
    except asyncio.TimeoutError:
        raise AssertionError("Bounded wait failed")


async def assertion_error_to_boolean(fun: abc.Callable[[], abc.Awaitable[object]]) -> bool:
    try:
        await fun()
        return True
    except AssertionError:
        LOGGER.info("Assertion failed, returning false", exc_info=True)
        return False


async def retry_limited_assertion(
    fun: Union[abc.Callable[..., abc.Awaitable[object]]],
    timeout: float,
    interval: float = 0.1,
    *args: object,
    **kwargs: object,
) -> None:
    try:
        await util.retry_limited(
            functools.partial(assertion_error_to_boolean, functools.partial(fun, *args, **kwargs)),
            timeout,
            interval,
        )
    except asyncio.TimeoutError:
        raise AssertionError("Bounded wait failed")


async def wait_until_logs_are_available(client: Client, environment: str, resource_id: str, expect_nr_of_logs: int) -> None:
    """
    The state of a resource and its logs are not set atomically. As such there is a small window
    when the deployment is marked as finished, but the logs are not available yet. This check
    prevents that race condition.
    """

    async def all_logs_are_available():
        response = await client.get_resource(environment, resource_id, logs=True)
        assert response.code == 200
        LOGGER.warning("%s", response.result["logs"])
        return len(response.result["logs"]) >= expect_nr_of_logs

    await retry_limited(all_logs_are_available, 15)


UNKWN = object()


def assert_equal_ish(minimal, actual, sortby=[]):
    if isinstance(minimal, dict):
        for k in minimal.keys():
            assert_equal_ish(minimal[k], actual[k], sortby)
    elif isinstance(minimal, list):
        assert len(minimal) == len(actual), "list not equal %d!=%d  %s != %s" % (len(minimal), len(actual), minimal, actual)
        if len(sortby) > 0:

            def keyfunc(val):
                if not isinstance(val, dict):
                    return val
                key = [str(val[x]) for x in sortby if x in val]
                return "_".join(key)

            minimal = sorted(minimal, key=keyfunc)
            actual = sorted(actual, key=keyfunc)
        for m, a in zip(minimal, actual):
            assert_equal_ish(m, a, sortby)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual, f"Minimal value expected is '{minimal}' but got '{actual}'"


def no_error_in_logs(caplog, levels=[logging.ERROR], ignore_namespaces=["tornado.access"]):
    for logger_name, log_level, message in caplog.record_tuples:
        if logger_name in ignore_namespaces:
            continue
        assert log_level not in levels, f"{logger_name} {log_level} {message}"


def log_contains(caplog, loggerpart, level, msg, test_phase="call"):
    close = []
    for record in caplog.get_records(test_phase):
        logger_name, log_level, message = record.name, record.levelno, record.message
        if msg in message:
            if loggerpart in logger_name and level == log_level:
                return
            else:
                close.append((logger_name, log_level, message))
    if close:
        print("found nearly matching log entry")
        for logger_name, log_level, message in close:
            print(logger_name, log_level, message)
        print("------------")

    assert False, f'Message "{msg}" not present in logs'


def log_doesnt_contain(caplog, loggerpart, level, msg):
    for logger_name, log_level, message in caplog.record_tuples:
        if loggerpart in logger_name and level == log_level and msg in message:
            assert False


def log_index(caplog, loggerpart, level, msg, after=0):
    """Find a log in line in the captured log, return the index of the first occurrence

    :param after: only consider records after the given index"""
    close = []
    for i, (logger_name, log_level, message) in enumerate(caplog.record_tuples[after:]):
        if msg in message:
            if loggerpart in logger_name and level == log_level:
                return i + after
            else:
                close.append((logger_name, log_level, message))

    if close:
        print("found nearly matching")
        for logger_name, log_level, message in close:
            print(logger_name, log_level, message)
        print("------------")

    assert False


class LogSequence:
    def __init__(self, caplog, index=0, allow_errors=True, ignore=[]):
        """

        :param caplog: caplog fixture
        :param index: start index in the log
        :param allow_errors: allow errors between log entries that are requested by log_contains
        :param ignore: ignore following namespaces
        """
        self.caplog = caplog
        self.index = index
        self.allow_errors = allow_errors
        self.ignore = ignore

    def _find(self, loggerpart, level, msg, after=0, min_level: int = math.inf):
        """

        :param loggerpart: part of the logger name to match
        :param level: exact log level to match
        :param min_level: minimal level to match (works as normal loglevel settings that take all higher levels)
        :param msg: part of the message to match on
        :param after: starting point in th capture buffer to search

        :return: matched index in the capture buffer, -1 for no match
        """
        close = []

        for i, (logger_name, log_level, message) in enumerate(self.caplog.record_tuples[after:]):
            if msg in message:
                if loggerpart in logger_name and (level == log_level or (log_level >= min_level)):
                    if any(i in logger_name for i in self.ignore):
                        continue
                    return i + after
                else:
                    close.append((logger_name, log_level, message))

        if close:
            print("found nearly matching")
            for logger_name, log_level, message in close:
                print(logger_name, log_level, message)
            print("------------")

        return -1

    def get(self, loggerpart, level, msg, min_level: int = math.inf) -> LogRecord:
        idx = self._find(loggerpart, level, msg, self.index, min_level)
        if idx < 0:
            raise KeyError()
        return self.caplog.records[idx]

    def contains(self, loggerpart, level, msg, min_level: int = math.inf) -> "LogSequence":
        """
        :param loggerpart: part of the logger name to match
        :param level: exact log level to match
        :param min_level: minimal level to match (works as normal loglevel settings that take all higher levels)
        :param msg: part of the message to match on
        """
        index = self._find(loggerpart, level, msg, self.index, min_level)
        if not self.allow_errors:
            # first error is later
            idxe = self._find("", logging.ERROR, "", self.index, min_level)
            assert idxe == -1 or idxe >= index, f"Unexpected ERROR log line found: {self.caplog.records[idxe]}"
        assert index >= 0, "could not find " + msg
        return LogSequence(self.caplog, index + 1, self.allow_errors, self.ignore)

    def assert_not(self, loggerpart, level, msg, min_level: int = math.inf) -> None:
        """
        :param loggerpart: part of the logger name to match
        :param level: exact log level to match
        :param min_level: minimal level to match (works as normal loglevel settings that take all higher levels)
        :param msg: part of the message to match on
        """
        idx = self._find(loggerpart, level, msg, self.index, min_level)
        assert idx == -1, f"{idx}, {self.caplog.record_tuples[idx]}"

    def no_more_errors(self):
        self.assert_not("", logging.ERROR, "")


NOISY_LOGGERS = [
    "inmanta.config",  # Option deprecations
    "inmanta.util",  # cancel background tasks
]


def assert_no_warning(caplog, loggers_to_allow: list[str] = NOISY_LOGGERS):
    """
    Assert there are no warning, except from the list of loggers to allow
    """
    for record in caplog.records:
        assert record.levelname != "WARNING" or (record.name in loggers_to_allow), str(record) + record.getMessage()


def configure_auth(
    auth: bool,
    ca: bool,
    ssl: bool,
    authentication_method: AuthMethod | None = None,
    authorization_provider: AuthorizationProviderName | None = None,
    access_policy: str | None = None,
    path_opa_executable: str | None = None,
) -> None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if auth:
        config.Config.set("server", "auth", "true")
        if authentication_method:
            server_auth_method.set(authentication_method.value)
        if authorization_provider:
            config.Config.set("server", "authorization-provider", authorization_provider.value)
        if access_policy:
            assert path_opa_executable is not None
            state_dir = config.state_dir.get()
            os.mkdir(os.path.join(state_dir, "policy_engine"))
            access_policy_file = os.path.join(state_dir, "policy_engine", "policy.rego")
            with open(access_policy_file, "w") as fh:
                fh.write(access_policy)
            policy_engine.policy_file.set(access_policy_file)
            policy_engine.path_opa_executable.set(path_opa_executable)
    for x, ct in [
        ("server", None),
        ("agent_rest_transport", ["agent"]),
        ("compiler_rest_transport", ["compiler"]),
        ("client_rest_transport", ["api", "compiler"]),
        ("cmdline_rest_transport", ["api"]),
    ]:
        if ssl and not ca:
            config.Config.set(x, "ssl_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(path, "server.open.key"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl", "True")
        if ssl and ca:
            capath = os.path.join(path, "ca", "enduser-certs")

            config.Config.set(x, "ssl_cert_file", os.path.join(capath, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(capath, "server.key.open"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(capath, "server.chain"))
            config.Config.set(x, "ssl", "True")
        if auth and ct is not None:
            token = protocol.encode_token(ct)
            config.Config.set(x, "token", token)


async def report_db_index_usage(min_precent=100):
    q = (
        "select relname ,idx_scan ,seq_scan , 100*idx_scan / (seq_scan + idx_scan) percent_of_times_index_used,"
        " n_live_tup rows_in_table, seq_scan * n_live_tup badness  FROM pg_stat_user_tables "
        "WHERE seq_scan + idx_scan > 0 order by badness desc"
    )
    async with data.get_connection_pool().acquire() as con:
        result = await con.fetch(q)

    for row in result:
        print(row)


async def wait_until_version_is_released(client, environment: uuid.UUID, version: int) -> None:
    """
    Wait until the configurationmodel with the given version and environment is released.
    """

    async def _is_version_released() -> bool:
        result = await client.get_version(tid=environment, id=version)
        if result.code == 404:
            return False
        assert result.code == 200
        return result.result["model"]["released"]

    await retry_limited(_is_version_released, timeout=10)


async def wait_for_version(client, environment, cnt: int, compile_timeout: int = 30):
    """
    :param compile_timeout: Raise an AssertionError if the compilation didn't finish after this amount of seconds.
    """

    # Wait until the server is no longer compiling
    # wait for it to finish
    async def compile_done():
        result = await client.get_reports(environment)
        assert result.code == 200
        return all(r["success"] is not None for r in result.result["reports"])

    await retry_limited(compile_done, compile_timeout)

    # Output compile report for debugging purposes
    reports = await client.get_reports(environment)
    for report in reports.result["reports"]:
        data = await client.get_report(report["id"])
        print(json.dumps(data.result, indent=4))
        assert report["success"]

    # wait for it to appear
    async def sufficient_versions():
        versions = await client.list_versions(environment)
        return versions.result["count"] >= cnt

    await retry_limited(sufficient_versions, 10)

    versions = await client.list_versions(environment)
    return versions.result


async def get_done_and_total(
    client: Client,
    environment: str,
) -> tuple[int, int]:
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
    #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}

    return (
        (
            summary["by_state"]["deployed"]
            + summary["by_state"]["failed"]
            + summary["by_state"]["skipped"]
            + summary["by_state"]["skipped_for_undefined"]
            + summary["by_state"]["unavailable"]
            + summary["by_state"]["undefined"]
        ),
        summary["total"],
    )


async def get_done_count(
    client: Client,
    environment: str,
) -> int:
    return (await get_done_and_total(client, environment))[0]


async def wait_until_deployment_finishes(
    client: Client, environment: str, *, version: int = -1, timeout: int = 10, wait_for_n: int | None = None
) -> None:
    async def done() -> bool:

        if version >= 0:
            scheduler = await data.Scheduler.get_one(environment=environment)
            if (
                scheduler is None
                or scheduler.last_processed_model_version is None
                or scheduler.last_processed_model_version < version
            ):
                return False

        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200

        summary = result.result["metadata"]["deploy_summary"]

        # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
        #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
        if wait_for_n is None:
            available = summary["by_state"]["available"]
            deploying = summary["by_state"]["deploying"]
            if available + deploying != 0:
                return False
            total: int = summary["total"]
        else:
            total = wait_for_n
        return (
            summary["by_state"]["deployed"]
            + summary["by_state"]["failed"]
            + summary["by_state"]["skipped"]
            + summary["by_state"]["skipped_for_undefined"]
            + summary["by_state"]["unavailable"]
            + summary["by_state"]["undefined"]
            + summary["by_state"]["non_compliant"]
            >= total
        )

    await retry_limited(done, timeout)


async def wait_for_resource_actions(
    client: Client, environment: str, rid: ResourceIdStr, deploy_count: int, timeout: int = 10
) -> None:
    async def is_deployment_finished() -> bool:
        result = await client.resource_logs(environment, rid, filter={"action": ["deploy"]})
        assert result.code == 200
        end_lines = [line for line in result.result["data"] if "End run" in line.get("msg", "")]
        LOGGER.info("Deploys done: %s", end_lines)
        return len(end_lines) >= deploy_count

    await retry_limited(is_deployment_finished, timeout)


async def wait_full_success(client: Client, environment: str, version: int = -1, timeout: int = 10) -> None:
    """Interface kept for backward compat"""

    async def done():
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
        #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
        print(summary)
        total = summary["total"]
        success = summary["by_state"]["deployed"]
        return total == success

    await retry_limited(done, 10)


class ClientHelper:
    def __init__(self, client: Client, environment: uuid.UUID) -> None:
        self.client = client
        self.environment = environment

    async def get_version(self) -> int:
        res = await self.client.reserve_version(self.environment)
        assert res.code == 200
        return res.result["data"]

    async def put_version_simple(self, resources: list[dict[str, Any]], version: int, wait_for_released: bool = False) -> None:
        res = await self.client.put_version(
            tid=self.environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            module_version_info={},
        )
        assert res.code == 200, res.result
        if wait_for_released:
            await retry_limited(functools.partial(self.is_released, version), timeout=1, interval=0.05)

    async def wait_for_released(self, version: int | None = None):
        """
        Version None means latest
        """
        await retry_limited(functools.partial(self.is_released, version), timeout=1, interval=0.05)

    async def is_released(self, version: int | None = None) -> bool:
        """Version None means latest"""
        versions = await self.client.list_versions(tid=self.environment)
        assert versions.code == 200
        if version is None:
            return versions.result["versions"][0]["released"]
        lookup = {v["version"]: v["released"] for v in versions.result["versions"]}
        return lookup[version]

    async def wait_for_deployed(self, version: int = -1, timeout=10) -> None:
        await wait_until_deployment_finishes(self.client, str(self.environment), version=version, timeout=timeout)

    async def wait_full_success(self) -> None:
        await wait_full_success(self.client, self.environment)

    async def done_count(self) -> int:
        return await get_done_count(self.client, self.environment)

    async def set_auto_deploy(self, auto: bool = True) -> None:
        result = await self.client.set_setting(self.environment, data.AUTO_DEPLOY, auto)
        assert result.code == 200

    async def set_setting(self, setting: str, value: str | int) -> None:
        result = await self.client.set_setting(self.environment, setting, value)
        assert result.code == 200


def get_resource(version: int, key: str = "key1", agent: str = "agent1", value: str = "value1") -> dict[str, Any]:
    return {
        "key": key,
        "value": value,
        "id": f"test::Resource[{agent},key={key}],v=%d" % version,
        "send_event": False,
        "purged": False,
        "requires": [],
    }


@functools.lru_cache(1)
def get_product_meta_data() -> ProductMetadata:
    """Get the produce meta-data"""
    bootloader = InmantaBootloader(configure_logging=True)
    context = bootloader.load_slices()
    return context.get_product_metadata()


def product_version_lower_or_equal_than(version: str) -> bool:
    return packaging.version.Version(version=get_product_meta_data().version) <= packaging.version.Version(version=version)


def mark_only_for_version_higher_than(version: str) -> "MarkDecorator":
    current = get_product_meta_data().version
    return pytest.mark.skipif(
        product_version_lower_or_equal_than(version),
        reason=f"This test is only intended for version larger than {version} currently at {current}",
    )


@dataclass
class PipIndex:
    """
    Local pip index that makes use of dir2pi to publish its artifacts.
    """

    artifact_dir: str

    @property
    def url(self) -> str:
        return f"{self.artifact_dir}/simple"

    def publish(self) -> None:
        dir2pi(argv=["dir2pi", self.artifact_dir])


def create_python_package(
    name: str,
    pkg_version: packaging.version.Version,
    path: str,
    *,
    requirements: Optional[Sequence[inmanta.util.CanonicalRequirement]] = None,
    install: bool = False,
    editable: bool = False,
    publish_index: Optional[PipIndex] = None,
    optional_dependencies: Optional[dict[str, Sequence[inmanta.util.CanonicalRequirement]]] = None,
) -> None:
    """
    Creates an empty Python package.

    :param name: The name of the package.
    :param pkg_version: The version of the package.
    :param path: The path to an empty or non-existant directory to create the package in.
    :param requirements: The requirements for the package, if any.
    :param install: Install the newly created package in the active Python environment. Requires virtualenv to be installed in
        the Python environment unless editable is True.
    :param editable: Whether to install the package in editable mode, ignored if install is False.
    :param publish_index: Publish to the given local path index. Requires virtualenv to be installed in the python environment.
    """
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise Exception(f"{path} is not a directory.")
        if os.listdir(path):
            raise Exception(f"{path} is not an empty directory.")
    else:
        os.makedirs(path)

    with open(os.path.join(path, "pyproject.toml"), "w") as fd:
        fd.write("""
[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools"]
            """.strip())

    install_requires_content = "".join(f"\n  {req}" for req in (requirements if requirements is not None else []))
    with open(os.path.join(path, "setup.cfg"), "w") as fd:
        egg_info: str = f"""
[egg_info]
tag_build = .dev{pkg_version.dev}
            """.strip() if pkg_version.is_devrelease else ""
        fd.write(f"""
[metadata]
name = {name}
version = {pkg_version.base_version}
description = An empty package for testing purposes
license = Apache 2.0
author = Inmanta <code@inmanta.com>

{egg_info}

""".strip())

        fd.write("\n[options]")
        fd.write(f"\ninstall_requires ={install_requires_content}")

        if optional_dependencies:
            fd.write("\n[options.extras_require]")
            for option_name, requirements in optional_dependencies.items():
                requirements_as_string = "".join(f"\n  {req}" for req in requirements)
                fd.write(f"\n{option_name} ={requirements_as_string}")

    if install:
        env.process_env.install_for_config(
            requirements=[],
            paths=[env.LocalPackagePath(path=path, editable=editable)],
            config=PipConfig(use_system_config=True),
        )
    if publish_index is not None:
        with build.env.DefaultIsolatedEnv() as build_env:
            builder = build.ProjectBuilder(source_dir=path, python_executable=build_env.python_executable)
            build_env.install(builder.build_system_requires)
            build_env.install(builder.get_requires_for_build(distribution="wheel"))
            builder.build(distribution="wheel", output_directory=publish_index.artifact_dir)
        publish_index.publish()


def module_from_template(
    source_dir: str,
    dest_dir: Optional[str] = None,
    *,
    new_version: Optional[packaging.version.Version] = None,
    new_name: Optional[str] = None,
    new_requirements: Optional[Sequence[Union[module.InmantaModuleRequirement, inmanta.util.CanonicalRequirement]]] = None,
    new_extras: Optional[
        abc.Mapping[str, abc.Sequence[Union[module.InmantaModuleRequirement, inmanta.util.CanonicalRequirement]]]
    ] = None,
    install: bool = False,
    editable: bool = False,
    publish_index: Optional[PipIndex] = None,
    new_content_init_cf: Optional[str] = None,
    new_content_init_py: Optional[str] = None,
    in_place: bool = False,
    four_digit_version: bool = False,
) -> module.ModuleV2Metadata:
    """
    Creates a v2 module from a template.

    :param source_dir: The directory where the original module lives.
    :param dest_dir: The directory to use to copy the original to and to stage any changes in.
    :param new_version: The new version for the module, if any.
    :param new_name: The new name of the inmanta module, if any.
    :param new_requirements: The new requirements for the module, if any.
    :param new_extras: The new optional dependencies for the module, if any.
    :param install: Install the newly created module with the module tool. Requires virtualenv to be installed in the
        python environment unless editable is True.
    :param editable: Whether to install the module in editable mode, ignored if install is False.
    :param publish_index: Publish to the given local path index. Requires virtualenv to be installed in the python environment.
    :param new_content_init_cf: The new content of the _init.cf file.
    :param new_content_init_py: The new content of the __init__.py file.
    :param in_place: Modify the module in-place instead of copying it.
    :param four_digit_version: if the version uses 4 digits (3 by default)
    """

    def to_python_requires(
        requires: abc.Sequence[Union[module.InmantaModuleRequirement, inmanta.util.CanonicalRequirement]],
    ) -> list[str]:
        return [
            str(req) if isinstance(req, packaging.requirements.Requirement) else str(req.get_python_package_requirement())
            for req in requires
        ]

    if (dest_dir is None) != in_place:
        raise ValueError("Either dest_dir or in_place must be set, never both.")
    if dest_dir is None:
        dest_dir = source_dir
    else:
        shutil.copytree(source_dir, dest_dir)
    config_file: str = os.path.join(dest_dir, module.ModuleV2.MODULE_FILE)
    config: configparser.ConfigParser = configparser.ConfigParser()
    config.read(config_file)
    if four_digit_version:
        config["metadata"]["four_digit_version"] = "True"
    if new_version is not None:
        base, tag = module.ModuleV2Metadata.split_version(new_version)
        config["metadata"]["version"] = base
        if tag is not None:
            config["egg_info"] = {"tag_build": tag}
    if new_name is not None:
        old_name: str = module.ModuleV2Source.get_inmanta_module_name(config["metadata"]["name"])
        os.rename(
            os.path.join(dest_dir, const.PLUGINS_PACKAGE, old_name),
            os.path.join(dest_dir, const.PLUGINS_PACKAGE, new_name),
        )
        config["metadata"]["name"] = module.ModuleV2Source.get_package_name_for(new_name)
        manifest_file: str = os.path.join(dest_dir, "MANIFEST.in")
        manifest_content: str
        with open(manifest_file) as fd:
            manifest_content: str = fd.read()
        with open(manifest_file, "w", encoding="utf-8") as fd:
            fd.write(manifest_content.replace(f"inmanta_plugins/{old_name}/", f"inmanta_plugins/{new_name}/"))
    if new_requirements:
        config["options"]["install_requires"] = "\n    ".join(to_python_requires(new_requirements))
    if new_extras:
        # start from a clean slate
        config.remove_section("options.extras_require")
        config.add_section("options.extras_require")
        for extra, requires in new_extras.items():
            config["options.extras_require"][extra] = "\n    ".join(to_python_requires(requires))
    if new_content_init_cf is not None:
        init_cf_file = os.path.join(dest_dir, "model", "_init.cf")
        with open(init_cf_file, "w", encoding="utf-8") as fd:
            fd.write(new_content_init_cf)
    if new_content_init_py is not None:
        init_py_file: str = os.path.join(
            dest_dir,
            const.PLUGINS_PACKAGE,
            module.ModuleV2Source.get_inmanta_module_name(config["metadata"]["name"]),
            "__init__.py",
        )
        with open(init_py_file, "w", encoding="utf-8") as fd:
            fd.write(new_content_init_py)
    with open(config_file, "w") as fh:
        config.write(fh)
    if install:
        if editable:
            env.process_env.install_for_config(
                requirements=[],
                paths=[env.LocalPackagePath(path=dest_dir, editable=True)],
                config=PipConfig(use_system_config=True),
            )
        else:
            mod_artifact_paths = ModuleTool().build(path=dest_dir, wheel=True)
            env.process_env.install_for_config(
                requirements=[],
                paths=[env.LocalPackagePath(path=mod_artifact_paths[0])],
                config=PipConfig(use_system_config=True),
            )
    if publish_index is not None:
        ModuleTool().build(path=dest_dir, output_dir=publish_index.artifact_dir, wheel=True)
        publish_index.publish()
    with open(config_file) as fh:
        return module.ModuleV2Metadata.parse(fh)


def v1_module_from_template(
    source_dir: str,
    dest_dir: str,
    *,
    new_version: Optional[packaging.version.Version] = None,
    new_name: Optional[str] = None,
    new_requirements: Optional[Sequence[Union[module.InmantaModuleRequirement, inmanta.util.CanonicalRequirement]]] = None,
    new_content_init_cf: Optional[str] = None,
    new_content_init_py: Optional[str] = None,
) -> module.ModuleV2Metadata:
    """
    Creates a v1 module from a template.

    :param source_dir: The directory where the original module lives.
    :param dest_dir: The directory to use to copy the original to and to stage any changes in.
    :param new_version: The new version for the module, if any.
    :param new_name: The new name of the inmanta module, if any.
    :param new_requirements: The new Python requirements for the module, if any.
    :param new_content_init_cf: The new content of the _init.cf file.
    :param new_content_init_py: The new content of the __init__.py file.
    """
    shutil.copytree(source_dir, dest_dir)
    config_file: str = os.path.join(dest_dir, module.ModuleV1.MODULE_FILE)
    config: dict[str, object] = configparser.ConfigParser()
    with open(config_file) as fd:
        config = yaml.safe_load(fd)
    if new_version is not None:
        config["version"] = str(new_version)
    if new_name is not None:
        config["name"] = new_name
    if new_content_init_cf is not None:
        init_cf_file = os.path.join(dest_dir, "model", "_init.cf")
        with open(init_cf_file, "w", encoding="utf-8") as fd:
            fd.write(new_content_init_cf)
    if new_content_init_py is not None:
        plugins_dir: str = os.path.join(dest_dir, "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        init_py_file: str = os.path.join(plugins_dir, "__init__.py")
        with open(init_py_file, "w", encoding="utf-8") as fd:
            fd.write(new_content_init_py)
    with open(config_file, "w") as fd:
        yaml.dump(config, fd)
    if new_requirements:
        with open(os.path.join(dest_dir, "requirements.txt"), "w") as fd:
            fd.write(
                "\n".join(
                    (
                        str(req)
                        if isinstance(req, packaging.requirements.Requirement)
                        else str(req.get_python_package_requirement())
                    )
                    for req in new_requirements
                )
            )
    with open(config_file) as fd:
        return module.ModuleV1Metadata.parse(fd)


def parse_datetime_to_utc(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=datetime.timezone.utc)


async def resource_action_consistency_check():
    """
    The resourceaction table is joined to the resource table in two different ways
    This method asserts that
        - both methods produce identical results (i.e. the updates are consistent)
        - both methods are in use (i.e. the queries return at least one record)
    """

    async def get_data(postgresql_client):
        post_ra_one = await postgresql_client.fetch("""SELECT
                ra.action_id,
                r.environment,
                r.resource_id,
                rscm.model
                FROM resource_set_configuration_model AS rscm
                INNER JOIN resource AS r
                    ON rscm.environment=r.environment
                    AND rscm.resource_set=r.resource_set
                INNER JOIN resourceaction as ra
                    ON r.resource_id || ',v=' || rscm.model = ANY(ra.resource_version_ids)
                    AND r.environment = ra.environment
            """)
        post_ra_one_set = {(r[0], r[1], r[2], r[3]) for r in post_ra_one}

        post_ra_two = await postgresql_client.fetch("""SELECT
                ra.action_id,
                r.environment,
                r.resource_id,
                rscm.model
            FROM resource_set_configuration_model AS rscm
            INNER JOIN resource AS r
                ON rscm.environment=r.environment
                AND rscm.resource_set=r.resource_set
            INNER JOIN public.resourceaction_resource as jt
                 ON r.environment = jt.environment
                AND r.resource_id = jt.resource_id
                AND rscm.model = jt.resource_version
            INNER JOIN public.resourceaction as ra
                ON ra.action_id = jt.resource_action_id
            """)
        post_ra_two_set = {(r[0], r[1], r[2], r[3]) for r in post_ra_two}
        return post_ra_one_set, post_ra_two_set

    # The above-mentioned queries have to be executed with at least the repeatable_read isolation level.
    # Otherwise it might happen that a repair run adds more resource actions between the execution of both queries.
    post_ra_one_set, post_ra_two_set = await data.ResourceAction.execute_in_retryable_transaction(
        get_data, tx_isolation_level="repeatable_read"
    )
    assert post_ra_one_set == post_ra_two_set
    assert post_ra_one_set


def get_as_naive_datetime(timestamp: datetime) -> datetime:
    """
    Convert the give timestamp, which is timezone aware, into a naive timestamp object in UTC.
    """
    if timestamp.tzinfo is None:
        return timestamp
    return timestamp.astimezone(timezone.utc).replace(tzinfo=None)


def make_random_file(size: int = 0) -> tuple[str, bytes, str]:
    """
    Generate a random file.

    :param size: If size is > 0 content is generated that is equal or more than size.
    """
    randomvalue = str(random.randint(0, 10000))
    if size > 0:
        while len(randomvalue) < size:
            randomvalue += randomvalue

    content = ("Hello world %s\n" % (randomvalue)).encode()
    hash = hash_file(content)

    body = base64.b64encode(content).decode("ascii")

    return hash, content, body


async def _deploy_resources(client, environment, resources, version: int, push, agent_trigger_method=None):
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, push, agent_trigger_method)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment, version=version)

    result = await client.get_version(environment, version)
    assert result.code == 200

    return result


async def wait_for_n_deployed_resources(client, environment, version, n, timeout=5):
    await wait_until_deployment_finishes(client, environment, timeout=timeout, wait_for_n=n)


class NullAgent(SessionEndpoint):

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        """
        :param environment: environment id
        """
        super().__init__(name="agent", timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())
        self._env_id = environment
        self.enabled: dict[str, bool] = {}

    async def start_connected(self) -> None:
        """
        Setup our single endpoint
        """
        await self.add_end_point_name(AGENT_SCHEDULER_ID)

    @protocol.handle(methods.set_state)
    async def set_state(self, agent: Optional[str], enabled: bool) -> Apireturn:
        self.enabled[agent] = enabled
        return 200

    async def on_reconnect(self) -> None:
        pass

    async def on_disconnect(self) -> None:
        pass

    @protocol.handle(methods.trigger, env="tid", agent="id")
    async def trigger_update(self, env: uuid.UUID, agent: str, incremental_deploy: bool) -> Apireturn:
        return 200

    @protocol.handle(methods.trigger_read_version, env="tid", agent="id")
    async def read_version(self, env: uuid.UUID) -> Apireturn:
        return 200

    @protocol.handle(methods.do_dryrun, env="tid", dry_run_id="id")
    async def run_dryrun(self, env: uuid.UUID, dry_run_id: uuid.UUID, agent: str, version: int) -> Apireturn:
        return 200

    @protocol.handle(methods.get_parameter, env="tid")
    async def get_facts(self, env: uuid.UUID, agent: str, resource: dict[str, Any]) -> Apireturn:
        return 200

    @protocol.handle(methods.get_status)
    async def get_status(self) -> Apireturn:
        return 200, {}

    @protocol.handle(methods_v2.trigger_get_status, env="tid")
    async def get_scheduler_resource_state(self, env: data.Environment) -> SchedulerStatusReport:
        return SchedulerStatusReport(scheduler_state={}, db_state={}, resource_states={}, discrepancies=[])


def make_requires(resources: Mapping[ResourceIdStr, ResourceIntent]) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
    """Convert resources from the scheduler input format to its requires format"""
    return {k: {req for req in resource.attributes.get("requires", [])} for k, resource in resources.items()}


def _get_dummy_blueprint_for(environment: uuid.UUID) -> ExecutorBlueprint:
    return ExecutorBlueprint(
        environment_id=environment,
        pip_config=LEGACY_PIP_DEFAULT,
        requirements=[],
        python_version=(3, 11),
        sources=[],
    )


class DummyCodeManager(CodeManager):
    """Code manager that pretends no code is ever needed"""

    async def get_code(
        self, environment: uuid.UUID, model_version: int, agent_name: str
    ) -> tuple[Collection[ModuleInstallSpec], executor.FailedModules]:
        dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)
        return ([ModuleInstallSpec("dummy_module", "0.0.0", dummyblueprint)], {})


async def is_agent_done(scheduler: ResourceScheduler, agent_name: str) -> bool:
    """
    Return True iff the given agent has finished executing all its tasks.

    :param scheduler: The resource scheduler that hands out work to the agent for which the done status has to be checked.
    :param agent_name: The name of the agent for which the done status has to be checked.
    """
    agent_queue = scheduler._work.agent_queues._agent_queues.get(agent_name)
    if not agent_queue:
        # Agent queue doesn't exist -> Tasks have not been queued yet
        return False
    return agent_queue._unfinished_tasks == 0


def assert_resource_persistent_state(
    resource_persistent_state: data.ResourcePersistentState,
    is_undefined: bool,
    is_orphan: bool,
    last_handler_run: state.HandlerResult,
    blocked: state.Blocked,
    expected_compliance: Optional[state.Compliance],
    last_handler_run_compliant: Optional[bool],
) -> None:
    """
    Assert that the given ResourcePersistentState record has the given content.
    """
    assert (
        resource_persistent_state.is_undefined == is_undefined
    ), f"{resource_persistent_state.resource_id} ({resource_persistent_state.is_undefined} != {is_undefined})"
    assert (
        resource_persistent_state.is_orphan == is_orphan
    ), f"{resource_persistent_state.resource_id} ({resource_persistent_state.is_orphan} != {is_orphan})"
    assert (
        resource_persistent_state.last_handler_run is last_handler_run
    ), f"{resource_persistent_state.resource_id} ({resource_persistent_state.last_handler_run} != {last_handler_run})"
    assert (
        resource_persistent_state.blocked is blocked
    ), f"{resource_persistent_state.resource_id} ({resource_persistent_state.blocked} != {blocked})"
    assert resource_persistent_state.get_compliance_status() is expected_compliance, (
        f"{resource_persistent_state.resource_id}"
        f" ({resource_persistent_state.get_compliance_status()} != {expected_compliance})"
    )
    assert resource_persistent_state.last_handler_run_compliant is last_handler_run_compliant, f"""
{resource_persistent_state.resource_id} ({resource_persistent_state.last_handler_run_compliant} != {last_handler_run_compliant})
"""


async def run_compile_and_wait_until_compile_is_done(
    compiler_service: CompilerService,
    compiler_queue: queue.Queue["CompileRunnerMock"],
    env_id: uuid.UUID,
    fail: Optional[bool] = None,
    fail_on_pull=False,
) -> "CompileRunnerMock":
    """
    Unblock the first compile in the compiler queue and wait until the compile finishes.
    """
    # prevent race conditions where compile request is not yet in queue
    await retry_limited(lambda: not compiler_queue.empty(), timeout=10)
    run = compiler_queue.get(block=True)
    if fail is not None:
        run._make_compile_fail = fail
    run._make_pull_fail = fail_on_pull

    current_task = compiler_service._env_to_compile_task[env_id]
    run.block = False

    def _is_compile_finished() -> bool:
        if env_id not in compiler_service._env_to_compile_task:
            return True
        if current_task is not compiler_service._env_to_compile_task[env_id]:
            return True
        return False

    await retry_limited(_is_compile_finished, timeout=10)
    return run


def validate_version_numbers_migration_scripts(versions_folder: pathlib.Path) -> None:
    """
    Validate whether the names of the database migration scripts in the given directory
    are compliant with the schema. Migration scripts must have the format vYYYYMMDDN.py
    """
    v1_found = False
    for path in versions_folder.iterdir():
        file_name = path.name
        if not file_name.endswith(".py"):
            continue
        if file_name == "__init__.py":
            continue
        if file_name == "v1.py":
            v1_found = True
            continue
        if not re.fullmatch(r"v([0-9]{9})\.py", file_name):
            raise Exception(f"Database migration script {file_name} has invalid format.")
    assert v1_found


def get_auth_client(
    env_to_role_dct: dict[str, list[str]], is_admin: bool, client_types: abc.Sequence[const.ClientType] | None = None
) -> protocol.Client:
    """
    Returns a client that uses an access token to authenticate to the server.

    This method changes the `client_rest_transport.token` config option.

    :param env_to_role_dct: A dictionary that maps the id of an environment to a list of roles that user has
                            in that environment.
    :param id_admin: A boolean that indicates whether the user is a global admin.
    :param client_type: A sequence of client_types that should be included in the token.
    """
    if client_types is None:
        client_types = [const.ClientType.api]
    token = auth.encode_token(
        client_types=[c.value for c in client_types],
        expire=None,
        custom_claims={
            const.INMANTA_ROLES_URN: env_to_role_dct,
            const.INMANTA_IS_ADMIN_URN: is_admin,
        },
    )
    config.Config.set("client_rest_transport", "token", token)
    return protocol.Client("client")


async def verify_authorization_labels_in_default_policy(
    enum_with_labels: enum.Enum, include_prefixes: Set[str] | None = None, exclude_prefixes: Set[str] | None = None
) -> None:
    """
    Ensure that authorization labels defined in the access policy map to their corresponding enum and
    ensure every label only occurs in one set.

    :param enum_with_labels: The enum that has to be used to validate the authorization labels.
    :param include_prefixes: If provided, only check authorization labels that start with these prefixes.
    :param exclude_prefixes: If provided, don't check authorization labls that start with these prefixes.
    """
    policy_engine_client = httpclient.AsyncHTTPClient()

    async def evaluate_in_policy(query: str):
        request = HTTPRequest(
            url=f"http://policy_engine/v1/data/policy/{query}",
            method="POST",
            headers={"Content-Type": "application/json"},
            body="",
        )
        response = await policy_engine_client.fetch(request)
        if response.code != 200:
            raise Exception(f"Policy evaluation failed: {response.body}")
        return json.loads(response.body.decode())["result"]

    variables_containing_labels = [
        "read_only_labels",
        "noc_specific_labels",
        "operator_specific_labels",
        "admin_specific_labels",
        "expert_admin_specific_labels",
    ]

    # 1. Fetch labels from the policy
    # 2. Verify they exist in the enum
    var_name_to_labels = {
        var_name: {
            enum_with_labels(label)
            for label in await evaluate_in_policy(var_name)
            if (exclude_prefixes is None or not any(label.startswith(p) for p in exclude_prefixes))
            and (include_prefixes is None or any(label.startswith(p) for p in include_prefixes))
        }
        for var_name in variables_containing_labels
    }

    # Ensure no label exists in more than one variable
    for i in range(len(variables_containing_labels) - 1):
        for j in range(i + 1, len(variables_containing_labels)):
            var_name_i = variables_containing_labels[i]
            var_name_j = variables_containing_labels[j]
            intersection = var_name_to_labels[var_name_i] & var_name_to_labels[var_name_j]
            if intersection:
                raise Exception(f"Label(s) {intersection} exist(s) in {var_name_i} and {var_name_j}.")


def read_file(file_name: str) -> str:
    """
    Returns the content of the given file.
    """
    with open(file_name, "r") as fh:
        return fh.read()


async def insert_with_link_to_configuration_model(resource_set: data.ResourceSet, versions: list[int] | None = None) -> None:
    """
    Inserts the ResourceSet into the database and creates a link to the configuration models in the versions argument.
    :param resource_set: The resource set to create
    :param versions: The versions of the configuration model this ResourceSet belongs to
    """
    async with resource_set.get_connection() as con:
        await resource_set.insert(con)
        if versions is not None and len(versions) > 0:
            query = """
            INSERT INTO public.resource_set_configuration_model(
                environment,
                resource_set,
                model
            )
            SELECT $1, $2, UNNEST($3::int[])
            ON CONFLICT DO NOTHING;
            """
            await con.execute(query, resource_set.environment, resource_set.id, versions)
