"""
Copyright 2019 Inmanta

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
from typing import Any

import pytest

from inmanta.agent.handler import CRUDHandlerGeneric as CRUDHandler
from inmanta.agent.handler import HandlerContext, ResourcePurged
from inmanta.const import ResourceState
from inmanta.resources import Id, PurgeableResource, resource
from utils import log_contains, no_error_in_logs


@pytest.mark.parametrize(
    "purged_desired,purged_actual,excn,create,delete",
    [
        (True, False, True, False, False),
        (True, True, False, False, False),
        (True, False, False, False, True),
        (True, True, True, False, False),
        (False, False, True, True, False),
        (False, True, False, True, False),
        (False, True, True, True, False),
        (False, False, False, False, False),
    ],
)
@pytest.mark.parametrize("updated", [True, False])
def test_CRUD_handler_purged_response(purged_desired, purged_actual, excn, create, delete, updated, caplog):
    """
    purged_actual and excn are conceptually equivalent, this test case serves to prove that they are in fact, equivalent
    """
    caplog.set_level(logging.DEBUG)

    @resource("aa::Aa", "aa", "aa")
    class TestResource(PurgeableResource):
        fields = ("value",)

    class DummyCrud(CRUDHandler[TestResource]):
        def __init__(self):
            self.updated = False
            self.created = False
            self.deleted = False

        def read_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            resource.purged = purged_actual
            if updated:
                resource.value = "b"
            if excn:
                raise ResourcePurged()

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: TestResource) -> None:
            self.updated = True

        def create_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            self.created = True

        def delete_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            self.deleted = True

    res = TestResource(Id("aa::Aa", "aa", "aa", "aa", 1))
    res.purged = purged_desired
    res.value = "a"

    ctx = HandlerContext(res, False)

    handler = DummyCrud()
    handler.execute(ctx, res, False)

    assert handler.updated == ((not (create or delete)) and updated and not purged_desired)
    assert handler.created == create
    assert handler.deleted == delete
    no_error_in_logs(caplog)
    log_contains(caplog, "inmanta.agent.handler", logging.DEBUG, "resource aa::Aa[aa,aa=aa],v=1: Calling read_resource")


@pytest.mark.parametrize(
    "running_test",
    [True, False],
)
def test_3470_CRUD_handler_with_unserializable_changes(running_test: bool, monkeypatch, caplog):
    """
    This test case checks that unserializable items in the 'changes' set not longer make
    the CRUD handler hang in production and that an exception is raised when the
    RUNNING_TEST variable is set to True.
    """
    import inmanta

    monkeypatch.setattr(inmanta, "RUNNING_TESTS", running_test)

    @resource(name="aa::Aa", id_attribute="aa", agent="aa")
    class TestResource(PurgeableResource):
        fields = ("value",)

    class DummyCrud(CRUDHandler[TestResource]):
        def __init__(self):
            self.updated = False

        def read_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            resource.value = "b"

        def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: TestResource) -> None:
            self.updated = True

    res = TestResource(Id(entity_type="aa::Aa", agent_name="aa", attribute="aa", attribute_value="aa", version=1))

    # Sets are not JSON serializable
    res.value = {"a"}
    res.purged = False

    ctx = HandlerContext(res, dry_run=False)

    handler = DummyCrud()

    if running_test:
        handler.execute(ctx, res, dry_run=False)
        assert ctx.status is ResourceState.failed
        error_message = "Failed to serialize attribute {'a'}"

        assert error_message in caplog.text

    else:
        handler.execute(ctx, res, dry_run=False)
        assert ctx.status is ResourceState.deployed
        assert handler.updated


@pytest.mark.parametrize(
    "running_test",
    [True, False],
)
def test_3470_CRUD_handler_with_unserializable_items_log_message(running_test: bool, monkeypatch, caplog):
    """
    This test case checks that unserializable log messages no longer make
    the CRUD handler hang in production and that an exception is raised when the
    RUNNING_TEST variable is set to True.
    """
    import inmanta

    monkeypatch.setattr(inmanta, "RUNNING_TESTS", running_test)

    @resource(name="aa::Aa", id_attribute="aa", agent="aa")
    class TestResource(PurgeableResource):
        fields = ("value",)

    class DummyCrud(CRUDHandler[TestResource]):
        def __init__(self):
            self.updated = False

        def read_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            resource.value = "b"
            unserializable_set = {"b"}
            ctx.debug(msg="Unserializable kwargs: ", kwargs={"unserializable": unserializable_set})

        def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: TestResource) -> None:
            self.updated = True

    res = TestResource(Id(entity_type="aa::Aa", agent_name="aa", attribute="aa", attribute_value="aa", version=1))

    res.value = "a"
    res.purged = False

    ctx = HandlerContext(res, dry_run=False)

    handler = DummyCrud()

    if running_test:
        handler.execute(ctx, res, dry_run=False)
        error_message = "Failed to serialize argument for log message"
        assert ctx.status is ResourceState.failed
        assert error_message in caplog.text

    else:
        handler.execute(ctx, res, dry_run=False)
        assert ctx.status is ResourceState.deployed
        assert handler.updated


def _log_context() -> HandlerContext:
    @resource(name="logtest::Res", id_attribute="key", agent="agent")
    class LogTestResource(PurgeableResource):
        fields = ("key",)

    res = LogTestResource(Id(entity_type="logtest::Res", agent_name="agent", attribute="key", attribute_value="k", version=1))
    return HandlerContext(res, dry_run=False)


def test_log_message_without_kwargs_is_not_formatted() -> None:
    """
    A message without keyword arguments is logged as is, also when it contains a percent sign, e.g. an f-string with an
    URL-encoded path.
    """
    ctx = _log_context()
    ctx.info(f"Request to {'https://device/api/a%2Fb'} failed")
    ctx.warning("Disk 95% full")
    assert [line.msg for line in ctx.logs] == ["Request to https://device/api/a%2Fb failed", "Disk 95% full"]


def test_log_message_with_kwargs_is_formatted() -> None:
    ctx = _log_context()
    ctx.info("Created %(path)s", path="/etc/motd")
    assert ctx.logs[0].msg == "Created /etc/motd"


def test_log_message_rejects_positional_arguments() -> None:
    ctx = _log_context()
    with pytest.raises(TypeError):
        ctx.error("Failed: %s", "reason")


@pytest.mark.parametrize("running_test", [True, False])
def test_log_message_format_error(running_test: bool, monkeypatch) -> None:
    """
    A message that does not match its keyword arguments fails in the tests, and is kept unformatted in production
    instead of failing the action that logs it.
    """
    import inmanta

    monkeypatch.setattr(inmanta, "RUNNING_TESTS", running_test)
    ctx = _log_context()
    if running_test:
        with pytest.raises(KeyError):
            ctx.info("Created %(path)s", name="motd")
    else:
        ctx.info("Created %(path)s", name="motd")
        assert ctx.logs[0].msg == "Created %(path)s"
