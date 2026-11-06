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

import pydantic
import pytest

from inmanta.agent.handler import CRUDHandlerGeneric as CRUDHandler
from inmanta.agent.handler import HandlerContext, LoggerABC, ResourcePurged
from inmanta.const import ResourceState
from inmanta.data.model import AttributeStateChange
from inmanta.references import Reference
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


class ConstantReference(Reference[str]):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def resolve(self, logger: LoggerABC) -> str:
        return self.value


@pytest.mark.parametrize(
    "current, changes",
    [
        # read_resource can't read the fields back: they hold the same references as desired
        (None, {}),
        # read_resource reads the fields back: they are compared with the values of the references
        ({"token": "a", "api": {"key": "b"}}, {}),
        ({"token": "x", "api": {"key": "b"}}, {"token": {"current": "x", "desired": "a"}}),
        ({"token": "a", "api": {"key": "x"}}, {"api": {"current": {"key": "x"}, "desired": {"key": "b"}}}),
    ],
)
def test_CRUD_handler_reference_typed_fields(current: dict[str, object] | None, changes: dict[str, object]) -> None:
    """
    The CRUD handler diffs a reference-typed field with the values of its references, unless the current state holds the
    same references, and reports these values as desired.
    """

    @resource(name="aa::Aa", id_attribute="aa", agent="aa")
    class TestResource(PurgeableResource):
        fields = ("token", "api")
        token: str | Reference[str]
        api: dict[str, str | Reference[str]]

    class DummyCrud(CRUDHandler[TestResource]):
        def __init__(self) -> None:
            self.changes: dict[str, dict[str, object]] = {}

        def read_resource(self, ctx: HandlerContext, resource: TestResource) -> None:
            for field, value in (current or {}).items():
                setattr(resource, field, value)

        def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: TestResource) -> None:
            self.changes = changes

    res = TestResource(Id(entity_type="aa::Aa", agent_name="aa", attribute="aa", attribute_value="aa", version=1))
    token = ConstantReference("a")
    res.token = token
    res.api = {"key": ConstantReference("b")}
    res.purged = False

    ctx = HandlerContext(res, dry_run=False)
    handler = DummyCrud()
    handler.execute(ctx, res, dry_run=False)

    assert ctx.status is ResourceState.deployed
    assert handler.changes == changes
    assert {field: change.model_dump() for field, change in ctx.changes.items()} == changes
    assert res.token is token


def test_reference_in_report_is_rejected() -> None:
    """A reference in a reported change or in a log argument is rejected, not stringified"""
    ref = ConstantReference("a")
    with pytest.raises(pydantic.ValidationError, match="is a reference, it can not be serialized"):
        AttributeStateChange(desired=ref)
    with pytest.raises(pydantic.ValidationError, match="is a reference, it can not be serialized"):
        AttributeStateChange(desired={"key": ref})

    @resource(name="aa::Aa", id_attribute="aa", agent="aa")
    class TestResource(PurgeableResource):
        fields = ("value",)

    ctx = HandlerContext(
        TestResource(Id(entity_type="aa::Aa", agent_name="aa", attribute="aa", attribute_value="aa", version=1))
    )
    with pytest.raises(Exception, match="Exception during serializing log message arguments"):
        ctx.debug("Value: %(value)s", value=ref)
