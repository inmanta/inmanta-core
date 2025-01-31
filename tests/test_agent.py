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

from inmanta.agent import reporting
from inmanta.agent.handler import HandlerContext, InvalidOperation
from inmanta.data.model import AttributeStateChange
from inmanta.resources import Id, PurgeableResource
from inmanta.server import SLICE_SESSION_MANAGER

logger = logging.getLogger(__name__)


@pytest.mark.slowtest
async def test_agent_get_status(server, environment, agent):
    clients = server.get_slice(SLICE_SESSION_MANAGER)._sessions.values()
    assert len(clients) == 1
    clients = [x for x in clients]
    client = clients[0].get_client()
    status = await client.get_status()
    status = status.get_result()
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
    assert status.get("env") is None


def test_context_changes():
    """Test registering changes in the handler context"""
    resource = PurgeableResource(Id.parse_id("std::testing::NullResource[agent,name=test],v=1"))
    ctx = HandlerContext(resource)

    # use attribute change attributes
    ctx.update_changes({"value": AttributeStateChange(current="a", desired="b")})
    assert len(ctx.changes) == 1

    # use dict
    ctx.update_changes({"value": dict(current="a", desired="b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use dict with empty string
    ctx.update_changes({"value": dict(current="", desired="value")})
    assert len(ctx.changes) == 1
    assert ctx.changes["value"].current == ""
    assert ctx.changes["value"].desired == "value"

    # use tuple
    ctx.update_changes({"value": ("a", "b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use wrong arguments
    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ("a", "b", 3)})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ["a", "b"]})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": "test"})


def test_entrypoint_for_handler_typing():
    from inmanta.agent.agent import AgentInstance  # noqa: F401
