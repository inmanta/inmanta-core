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
import configparser
import datetime
import json
import logging
import os
import shutil
import uuid
from collections import abc
from dataclasses import dataclass
from datetime import timezone
from typing import Any, Dict, Optional, Sequence, Type, TypeVar, Union

import pytest
import yaml
from pkg_resources import Requirement, parse_version
from pydantic.tools import lru_cache

import build
import build.env
from _pytest.mark import MarkDecorator
from inmanta import const, data, env, module, util
from inmanta.moduletool import ModuleTool
from inmanta.protocol import Client
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.extensions import ProductMetadata
from inmanta.util import get_compiler_version
from libpip2pi.commands import dir2pi
from packaging import version

T = TypeVar("T")


def get_all_subclasses(cls: Type[T]) -> set[Type[T]]:
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


async def wait_until_logs_are_available(client: Client, environment: str, resource_id: str, expect_nr_of_logs: int) -> None:
    """
    The state of a resource and its logs are not set atomically. As such there is a small window
    when the deployment is marked as finished, but the logs are not available yet. This check
    prevents that race condition.
    """

    async def all_logs_are_available():
        response = await client.get_resource(environment, resource_id, logs=True)
        assert response.code == 200
        return len(response.result["logs"]) >= expect_nr_of_logs

    await retry_limited(all_logs_are_available, 10)


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
        for (m, a) in zip(minimal, actual):
            assert_equal_ish(m, a, sortby)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual, f"Minimal value expected is '{minimal}' but got '{actual}'"


def assert_graph(graph, expected):
    lines = [
        "%s: %s" % (f.id.get_attribute_value(), t.id.get_attribute_value()) for f in graph.values() for t in f.resource_requires
    ]
    lines = sorted(lines)

    elines = [x.strip() for x in expected.split("\n")]
    elines = sorted(elines)

    assert elines == lines, (lines, elines)


class AsyncClosing(object):
    def __init__(self, awaitable):
        self.awaitable = awaitable

    async def __aenter__(self):
        self.closable = await self.awaitable
        return object

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.closable.stop()


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

    assert False


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


class LogSequence(object):
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

    def _find(self, loggerpart, level, msg, after=0):
        for i, (logger_name, log_level, message) in enumerate(self.caplog.record_tuples[after:]):
            if msg in message:
                if loggerpart in logger_name and level == log_level:
                    if any(i in logger_name for i in self.ignore):
                        continue
                    return i + after
        return -1

    def contains(self, loggerpart, level, msg):
        index = self._find(loggerpart, level, msg, self.index)
        if not self.allow_errors:
            # first error is later
            idxe = self._find("", logging.ERROR, "", self.index)
            assert idxe == -1 or idxe >= index
        assert index >= 0, "could not find " + msg
        return LogSequence(self.caplog, index + 1, self.allow_errors, self.ignore)

    def assert_not(self, loggerpart, level, msg):
        idx = self._find(loggerpart, level, msg, self.index)
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
        assert record.levelname != "WARNING" or (record.name in loggers_to_allow)


def configure(unused_tcp_port, database_name, database_port):
    import inmanta.agent.config  # noqa: F401
    import inmanta.server.config  # noqa: F401
    from inmanta.config import Config

    free_port = str(unused_tcp_port)
    Config.load_config()
    Config.set("server", "bind-port", free_port)
    Config.set("agent_rest_transport", "port", free_port)
    Config.set("compiler_rest_transport", "port", free_port)
    Config.set("client_rest_transport", "port", free_port)
    Config.set("cmdline_rest_transport", "port", free_port)
    Config.set("database", "name", database_name)
    Config.set("database", "host", "localhost")
    Config.set("database", "port", str(database_port))


async def report_db_index_usage(min_precent=100):
    q = (
        "select relname ,idx_scan ,seq_scan , 100*idx_scan / (seq_scan + idx_scan) percent_of_times_index_used,"
        " n_live_tup rows_in_table, seq_scan * n_live_tup badness  FROM pg_stat_user_tables "
        "WHERE seq_scan + idx_scan > 0 order by badness desc"
    )
    async with data.Compile._connection_pool.acquire() as con:
        result = await con.fetch(q)

    for row in result:
        print(row)


async def wait_for_version(client, environment, cnt):
    # Wait until the server is no longer compiling
    # wait for it to finish
    async def compile_done():
        compiling = await client.is_compiling(environment)
        code = compiling.code
        return code == 204

    await retry_limited(compile_done, 30)

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


async def _wait_until_deployment_finishes(client: Client, environment: str, version: int, timeout: int = 10) -> None:
    async def is_deployment_finished() -> bool:
        result = await client.get_version(environment, version)
        print(version, result.result)
        return result.result["model"]["deployed"]

    await retry_limited(is_deployment_finished, timeout)


class ClientHelper(object):
    def __init__(self, client: Client, environment: uuid.UUID) -> None:
        self.client = client
        self.environment = environment

    async def get_version(self) -> int:
        res = await self.client.reserve_version(self.environment)
        assert res.code == 200
        return res.result["data"]

    async def put_version_simple(self, resources: Dict[str, Any], version: int) -> None:
        res = await self.client.put_version(
            tid=self.environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200, res.result


def get_resource(version: int, key: str = "key1", agent: str = "agent1", value: str = "value1") -> Dict[str, Any]:
    return {
        "key": key,
        "value": value,
        "id": f"test::Resource[{agent},key={key}],v=%d" % version,
        "send_event": False,
        "purged": False,
        "requires": [],
    }


@lru_cache(1)
def get_product_meta_data() -> ProductMetadata:
    """Get the produce meta-data"""
    bootloader = InmantaBootloader()
    context = bootloader.load_slices()
    return context.get_product_metadata()


def product_version_lower_or_equal_than(version: str) -> bool:
    return parse_version(get_product_meta_data().version) <= parse_version(version)


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
    pkg_version: version.Version,
    path: str,
    *,
    requirements: Optional[Sequence[Requirement]] = None,
    install: bool = False,
    editable: bool = False,
    publish_index: Optional[PipIndex] = None,
    optional_dependencies: Optional[Dict[str, Sequence[Requirement]]] = None,
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
        fd.write(
            """
[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools"]
            """.strip()
        )

    install_requires_content = "".join(f"\n  {req}" for req in (requirements if requirements is not None else []))
    with open(os.path.join(path, "setup.cfg"), "w") as fd:
        egg_info: str = (
            f"""
[egg_info]
tag_build = .dev{pkg_version.dev}
            """.strip()
            if pkg_version.is_devrelease
            else ""
        )
        fd.write(
            f"""
[metadata]
name = {name}
version = {pkg_version.base_version}
description = An empty package for testing purposes
license = Apache 2.0
author = Inmanta <code@inmanta.com>

{egg_info}

""".strip()
        )

        fd.write("\n[options]")
        fd.write(f"\ninstall_requires ={install_requires_content}")

        if optional_dependencies:
            fd.write("\n[options.extras_require]")
            for option_name, requirements in optional_dependencies.items():
                requirements_as_string = "".join(f"\n  {req}" for req in requirements)
                fd.write(f"\n{option_name} ={requirements_as_string}")

    if install:
        env.process_env.install_from_source([env.LocalPackagePath(path=path, editable=editable)])
    if publish_index is not None:
        with build.env.IsolatedEnvBuilder() as build_env:
            builder = build.ProjectBuilder(
                srcdir=path, python_executable=build_env.executable, scripts_dir=build_env.scripts_dir
            )
            build_env.install(builder.build_system_requires)
            build_env.install(builder.get_requires_for_build(distribution="wheel"))
            builder.build(distribution="wheel", output_directory=publish_index.artifact_dir)
        publish_index.publish()


def module_from_template(
    source_dir: str,
    dest_dir: Optional[str] = None,
    *,
    new_version: Optional[version.Version] = None,
    new_name: Optional[str] = None,
    new_requirements: Optional[Sequence[Union[module.InmantaModuleRequirement, Requirement]]] = None,
    new_extras: Optional[abc.Mapping[str, abc.Sequence[Union[module.InmantaModuleRequirement, Requirement]]]] = None,
    install: bool = False,
    editable: bool = False,
    publish_index: Optional[PipIndex] = None,
    new_content_init_cf: Optional[str] = None,
    new_content_init_py: Optional[str] = None,
    in_place: bool = False,
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
    """

    def to_python_requires(
        requires: abc.Sequence[Union[module.InmantaModuleRequirement, Requirement]]
    ) -> abc.Iterator[Requirement]:
        return (str(req if isinstance(req, Requirement) else req.get_python_package_requirement()) for req in requires)

    if (dest_dir is None) != in_place:
        raise ValueError("Either dest_dir or in_place must be set, never both.")
    if dest_dir is None:
        dest_dir = source_dir
    else:
        shutil.copytree(source_dir, dest_dir)
    config_file: str = os.path.join(dest_dir, module.ModuleV2.MODULE_FILE)
    config: configparser.ConfigParser = configparser.ConfigParser()
    config.read(config_file)
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
        with open(manifest_file, "r") as fd:
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
        ModuleTool().install(editable=editable, path=dest_dir)
    if publish_index is not None:
        ModuleTool().build(path=dest_dir, output_dir=publish_index.artifact_dir)
        publish_index.publish()
    with open(config_file, "r") as fh:
        return module.ModuleV2Metadata.parse(fh)


def v1_module_from_template(
    source_dir: str,
    dest_dir: str,
    *,
    new_version: Optional[version.Version] = None,
    new_name: Optional[str] = None,
    new_requirements: Optional[Sequence[Union[module.InmantaModuleRequirement, Requirement]]] = None,
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
    config: Dict[str, object] = configparser.ConfigParser()
    with open(config_file, "r") as fd:
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
                    str(req if isinstance(req, Requirement) else req.get_python_package_requirement())
                    for req in new_requirements
                )
            )
    with open(config_file, "r") as fd:
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
        post_ra_one = await postgresql_client.fetch(
            """SELECT ra.action_id, r.environment, r.resource_id, r.model FROM public.resourceaction as ra
                    INNER JOIN public.resource as r
                    ON r.resource_id || ',v=' || r.model = ANY(ra.resource_version_ids)
                    AND r.environment = ra.environment
            """
        )
        post_ra_one_set = {(r[0], r[1], r[2], r[3]) for r in post_ra_one}

        post_ra_two = await postgresql_client.fetch(
            """SELECT ra.action_id, r.environment, r.resource_id, r.model FROM public.resource as r
                    INNER JOIN public.resourceaction_resource as jt
                         ON r.environment = jt.environment
                        AND r.resource_id = jt.resource_id
                        AND r.model = jt.resource_version
                    INNER JOIN public.resourceaction as ra
                        ON ra.action_id = jt.resource_action_id
            """
        )
        post_ra_two_set = {(r[0], r[1], r[2], r[3]) for r in post_ra_two}
        return post_ra_one_set, post_ra_two_set

    # The above-mentioned queries have to be executed with at least the repeatable_read isolation level.
    # Otherwise it might happen that a repair run adds more resource actions between the execution of both queries.
    (post_ra_one_set, post_ra_two_set) = await data.ResourceAction.execute_in_retryable_transaction(
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
