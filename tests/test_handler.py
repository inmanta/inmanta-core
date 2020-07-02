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

import pytest

from inmanta import resources
from inmanta.agent.handler import CRUDHandler, HandlerContext, ResourcePurged
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

    class DummyCrud(CRUDHandler):
        def __init__(self):
            self.updated = False
            self.created = False
            self.deleted = False

        def read_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
            resource.purged = purged_actual
            if updated:
                resource.value = "b"
            if excn:
                raise ResourcePurged()

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: resources.PurgeableResource) -> None:
            self.updated = True

        def create_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
            self.created = True

        def delete_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
            self.deleted = True

    @resource("aa::Aa", "aa", "aa")
    class TestResource(PurgeableResource):
        fields = ("value",)

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
