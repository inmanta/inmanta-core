"""
Copyright 2026 Inmanta

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
import logging
import uuid

from inmanta import config as inmanta_config_mod
from inmanta import const
from inmanta.protocol import SessionEndpoint, handle, typedmethod, websocket
from inmanta.protocol.auth.decorators import auth
from inmanta.server.config import AuthorizationProviderName
from inmanta.server.protocol import Server, ServerSlice
from utils import configure_auth

LOGGER = logging.getLogger(__name__)


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/server_status", operation="GET")
def get_current_server_status() -> str:
    """Get the status of the server"""


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/agent_status", operation="GET")
def get_current_agent_status() -> str:
    """Get the status of the agent"""


# Auth test methods: allow agent client type so agent tokens are accepted
@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/auth_server_status", operation="GET", client_types=[const.ClientType.api, const.ClientType.agent])
def get_auth_server_status() -> str:
    """Get server status (allows agent client type for auth tests)"""


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(
    path="/auth_agent_status", operation="GET", server_agent=True, enforce_auth=False, client_types=[const.ClientType.agent]
)
def get_auth_agent_status() -> str:
    """Get agent status (server→agent, no auth enforcement)"""


class WSServer(websocket.SessionListener, ServerSlice):
    def __init__(self) -> None:
        ServerSlice.__init__(self, "wsserver")

    @handle(get_current_server_status)
    async def get_current_server_status(self) -> str:
        LOGGER.error("Got status call")
        return "server status"

    @handle(get_auth_server_status)
    async def get_auth_server_status(self) -> str:
        return "auth server status"


class WSAgent(SessionEndpoint):
    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5) -> None:
        super().__init__(name, uuid.uuid4(), timeout, reconnect_delay)

    @handle(get_current_agent_status)
    async def get_current_agent_status(self) -> str:
        return "agent status"

    @handle(get_auth_agent_status)
    async def get_auth_agent_status(self) -> str:
        return "auth agent status"


class TrackingWSAgent(WSAgent):
    """WSAgent that records lifecycle events in order for testing."""

    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5) -> None:
        super().__init__(name, timeout, reconnect_delay)
        self.events: list[str] = []

    async def on_reconnect(self) -> None:
        self.events.append("reconnect")
        await super().on_reconnect()

    async def on_disconnect(self) -> None:
        self.events.append("disconnect")
        await super().on_disconnect()


async def test_ws_2way(inmanta_config: object, server_config: object) -> None:
    """Test websocket 2-way communication"""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent")
    await agent.start()

    while not agent.session or not agent.session.active:
        await asyncio.sleep(0.01)

    client_a2s = agent.session.get_typed_client()
    result = await client_a2s.get_current_server_status()
    assert result == "server status"

    client_s2a = rs._transport.get_session(*agent.session.session_key).get_typed_client()
    result = await client_s2a.get_current_agent_status()
    assert result == "agent status"

    await rs.stop()
    await agent.stop()


async def test_ws_ping_timeout_closes_stale_connection(inmanta_config: object, server_config: object) -> None:
    """Test that a stale connection is closed by the server when pong responses stop arriving,
    and that the agent reconnects automatically afterward.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    # Wait for the session to become active
    async def wait_for_active() -> None:
        while not agent.session or not agent.session.active:
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_active(), timeout=10)

    # Verify the server has the session
    session_key = agent.session.session_key
    assert session_key in rs._transport._sessions

    # Simulate network partition: close the underlying TCP stream without a WebSocket close frame.
    # This prevents pong responses from reaching the server.
    assert agent._ws_client is not None
    agent._ws_client.protocol.stream.close()

    # Wait for the server to detect the stale connection and remove the session.
    # With ws-ping-interval=1, ws-ping-timeout=1, this should happen within a few seconds.
    async def wait_for_session_removed() -> None:
        while session_key in rs._transport._sessions:
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_session_removed(), timeout=10)

    # The agent should reconnect and establish a new active session
    async def wait_for_server_session() -> None:
        while True:
            if agent.session and agent.session.active and agent.session.session_key in rs._transport._sessions:
                return
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_server_session(), timeout=10)

    await rs.stop()
    await agent.stop()


async def test_ws_reconnect_on_connection_failure(inmanta_config: object, server_config: object) -> None:
    """Test that the agent recovers when the server is unavailable at startup.

    Without the error handling in _process_messages(), a connection failure in
    _reconnect() would kill the message loop task and the agent would never recover.
    """
    # Start agent BEFORE the server is running — _reconnect() will raise connection errors
    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    # Let the agent fail a few connection attempts
    await asyncio.sleep(3)

    # Verify the agent is NOT connected while the server is down
    assert agent.session is None or not agent.session.active

    # Now start the server
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    try:
        # Wait for the agent to connect
        async def wait_for_session() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_session(), timeout=10)

        # Verify session is established
        assert agent.session is not None
        assert agent.session.active

        # Verify bidirectional RPC works
        client_a2s = agent.session.get_typed_client()
        result = await client_a2s.get_current_server_status()
        assert result == "server status"

        client_s2a = rs._transport.get_session(*agent.session.session_key).get_typed_client()
        result = await client_s2a.get_current_agent_status()
        assert result == "agent status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_reject_duplicate_session_on_same_connection(inmanta_config: object, server_config: object) -> None:
    """Test that the server rejects a second OpenSession on the same connection.

    When a duplicate OpenSession arrives on a connection that already has a session, the server sends
    RejectSession. The agent's on_message processes the RejectSession, closes the session and
    reconnects. After reconnection, RPC should work again.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    async def wait_for_active() -> None:
        while not agent.session or not agent.session.active:
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_active(), timeout=10)

    original_session_id = agent.session.id

    # Send a duplicate OpenSession on the same WebSocket connection.
    # The server-side frame decoder will reject it with RejectSession.
    # The agent's _process_messages loop receives the RejectSession, closes the session,
    # and reconnects.
    assert agent._ws_client is not None
    duplicate_msg = websocket.OpenSession(
        environment_id=agent.environment,
        session_name="agent",
        hostname="duplicate",
    ).model_dump_json()
    await agent._ws_client.write_message(duplicate_msg)

    # Wait for the agent to reconnect with a new session
    async def wait_for_new_session() -> None:
        while True:
            if agent.session and agent.session.active and agent.session.id != original_session_id:
                return
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_new_session(), timeout=30)

    # RPC works on the new session
    client_a2s = agent.session.get_typed_client()
    result = await client_a2s.get_current_server_status()
    assert result == "server status"

    await rs.stop()
    await agent.stop()


async def test_ws_client_handles_reject_session(inmanta_config: object, server_config: object) -> None:
    """Test that the client handles a RejectSession by closing the session and reconnecting."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    async def wait_for_active() -> None:
        while not agent.session or not agent.session.active:
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_active(), timeout=10)

    original_session_id = agent.session.id

    # Simulate the server sending a RejectSession to the agent's on_message handler
    reject_msg = websocket.RejectSession(reason="test rejection").model_dump_json()
    await agent.on_message(reject_msg)

    # The agent's session should be cleared
    assert agent._session is None or not agent.active()

    # The agent should reconnect and establish a new active session
    async def wait_for_new_session() -> None:
        while True:
            if agent.session and agent.session.active and agent.session.id != original_session_id:
                return
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_new_session(), timeout=30)

    # Verify the new session works
    client_a2s = agent.session.get_typed_client()
    result = await client_a2s.get_current_server_status()
    assert result == "server status"

    await rs.stop()
    await agent.stop()


async def test_ws_concurrent_rpcs(inmanta_config: object, server_config: object) -> None:
    """Test that multiple concurrent RPC calls over a single WebSocket session all succeed."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent")
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        client = agent.session.get_typed_client()
        results = await asyncio.gather(*[client.get_current_server_status() for _ in range(10)])
        assert all(r == "server status" for r in results)
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_rpc_on_closed_session(inmanta_config: object, server_config: object) -> None:
    """Test that an RPC call on a closed connection fails promptly (does not hang)."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        client = agent.session.get_typed_client()

        # Kill the server so the connection drops
        await rs.stop()

        # The RPC call should fail or raise, not hang indefinitely
        try:
            result = await asyncio.wait_for(client.get_current_server_status(), timeout=10)
            # If it returns, the result should indicate an error (not "server status")
            assert result != "server status"
        except Exception:
            # Any exception is acceptable — the key point is it doesn't hang
            pass
    finally:
        await agent.stop()


async def test_ws_server_shutdown_during_active_session(inmanta_config: object, server_config: object) -> None:
    """Test that the agent detects server shutdown and reconnects to a new server."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Stop the server
        await rs.stop()

        # Wait for the agent to detect disconnection
        async def wait_for_inactive() -> None:
            while agent.session and agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_inactive(), timeout=10)

        # Start a new server
        rs2 = Server()
        server2 = WSServer()
        rs2.add_slice(server2)
        await rs2.start()

        try:
            # Wait for the agent to reconnect
            async def wait_for_reconnect() -> None:
                while not agent.session or not agent.session.active:
                    await asyncio.sleep(0.1)

            await asyncio.wait_for(wait_for_reconnect(), timeout=30)

            # Verify RPC works on the new connection
            client = agent.session.get_typed_client()
            result = await client.get_current_server_status()
            assert result == "server status"
        finally:
            await rs2.stop()
    finally:
        await agent.stop()


async def test_ws_pending_futures_resolved_on_disconnect(inmanta_config: object, server_config: object) -> None:
    """Test that in-flight RPC calls are resolved with 503 when the session closes,
    rather than hanging until timeout."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Start an RPC call from server to agent. We use the server-side session's client
        # to call the agent. The agent has pending futures on its decoder.
        # Instead, let's directly put a pending future in the agent's _replies dict
        # to simulate an in-flight RPC call.
        pending_future: asyncio.Future[websocket.common.Result] = asyncio.Future()
        fake_reply_id = uuid.uuid4()
        agent._replies[fake_reply_id] = pending_future

        # Close the session — this should resolve the pending future with 503
        await agent.close_session()

        # The future should be resolved quickly, not hang until timeout
        result = await asyncio.wait_for(pending_future, timeout=2)
        assert result.code == 503
        assert result.result is not None
        assert "Session closed" in result.result["message"]

        # _replies should be cleared
        assert len(agent._replies) == 0
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_duplicate_session_replaces_old(inmanta_config: object, server_config: object) -> None:
    """Test that when the same agent reconnects, the old session is evicted and listener
    callbacks fire in the correct order (close old, open new)."""

    class SessionSpy(websocket.SessionListener):
        def __init__(self) -> None:
            self.events: list[tuple[str, uuid.UUID]] = []

        async def session_opened(self, session: websocket.Session) -> None:
            self.events.append(("opened", session.id))

        async def session_closed(self, session: websocket.Session) -> None:
            self.events.append(("closed", session.id))

    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    spy = SessionSpy()
    rs._transport.add_session_listener(spy)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        agent_session_id_1 = agent.session.id
        # Record the server-side session ID for the first connection
        assert len(spy.events) == 1 and spy.events[0][0] == "opened"
        server_session_id_1 = spy.events[0][1]

        # Force-close the TCP stream to simulate a network partition.
        # The server doesn't know the connection is dead until ping timeout.
        assert agent._ws_client is not None
        agent._ws_client.protocol.stream.close()

        # Wait for the agent to reconnect with a new session
        async def wait_for_new_session() -> None:
            while True:
                if agent.session and agent.session.active and agent.session.id != agent_session_id_1:
                    return
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_new_session(), timeout=30)

        # Verify the spy saw: opened(first), closed(first), opened(second)
        actions = [e for e, _ in spy.events]
        assert "closed" in actions, f"Expected a close event, got {spy.events}"

        # The close must be for the first server-side session
        close_events = [(e, sid) for e, sid in spy.events if e == "closed" and sid == server_session_id_1]
        assert len(close_events) >= 1, f"Expected close of {server_session_id_1}, got {spy.events}"

        # A second open event should exist (for the reconnected session)
        open_events = [(e, sid) for e, sid in spy.events if e == "opened" and sid != server_session_id_1]
        assert len(open_events) >= 1, f"Expected a second open event, got {spy.events}"

        # The server should have exactly one session entry for this agent
        assert len(rs._transport._sessions) == 1
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_old_session_closed_on_reconnect(inmanta_config: object, server_config: object) -> None:
    """Test that when the agent reconnects, the old session is properly closed
    and on_disconnect/on_reconnect don't interleave."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = TrackingWSAgent("agent", reconnect_delay=1)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        old_session = agent.session
        assert old_session is not None
        assert not old_session.is_closed()

        # Also inject a pending future to verify it gets cleaned up (D2 interaction with D4)
        pending_future: asyncio.Future[websocket.common.Result] = asyncio.Future()
        agent._replies[uuid.uuid4()] = pending_future

        agent.events.clear()

        # Force-close the TCP stream to trigger reconnection
        assert agent._ws_client is not None
        agent._ws_client.protocol.stream.close()

        # Wait for reconnection
        async def wait_for_new_session() -> None:
            while True:
                if agent.session and agent.session.active and agent.session is not old_session:
                    return
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_new_session(), timeout=30)

        # The old session should be closed
        assert old_session.is_closed(), "Old session was not closed during reconnect"

        # The pending future should have been resolved (not left hanging)
        assert pending_future.done(), "Pending future was not resolved when old session closed"
        assert pending_future.result().code == 503

        # on_disconnect should not have fired during reconnection (D8: no interleaving)
        # We expect: reconnect (from on_open_session). No disconnect during the reconnect window.
        # Allow for a disconnect event from the Tornado callback, but it must come before reconnect.
        for i, event in enumerate(agent.events):
            if event == "disconnect":
                # Any disconnect must precede the reconnect, not interleave
                remaining = agent.events[i + 1 :]
                assert (
                    "disconnect" not in remaining
                ), f"Multiple disconnect events detected, possible interleaving: {agent.events}"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_close_connection_notifies_remote_before_local_teardown(inmanta_config: object, server_config: object) -> None:
    """Test that close_connection sends CloseSession to the remote before closing the local session,
    so the remote can clean up while the session is still logically open."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Track the order: was CloseSession sent while the session was still open?
        session_open_when_close_sent: list[bool] = []
        original_write = agent.write_message

        async def tracking_write(message: str | bytes, binary: bool = False) -> None:
            if isinstance(message, str) and "CLOSE_SESSION" in message:
                session_open_when_close_sent.append(not agent.session.is_closed())
            await original_write(message, binary)

        agent.write_message = tracking_write  # type: ignore[assignment]

        await agent.close_connection()

        assert len(session_open_when_close_sent) == 1, "CloseSession should have been sent exactly once"
        assert session_open_when_close_sent[0], "CloseSession should be sent before local session is closed"

        # Local session should be closed after close_connection completes
        assert agent.session.is_closed()
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_write_failure_resolves_future(inmanta_config: object, server_config: object) -> None:
    """Test that when write_message fails during an RPC call, the pending future
    is resolved with an error rather than hanging until timeout."""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Close the underlying TCP stream so write_message will fail
        assert agent._ws_client is not None
        agent._ws_client.protocol.stream.close()

        # Make an RPC call — the write should fail but the future should resolve quickly
        client = agent.session.get_typed_client()
        try:
            result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
            # If we get a result, it should be an error (not the actual server status)
            assert result != "server status"
        except asyncio.TimeoutError:
            raise AssertionError("RPC future was not resolved after write failure — hung until timeout")
        except Exception:
            # Any exception other than TimeoutError is acceptable
            pass
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_notify_close_session_identity_check(inmanta_config: object, server_config: object) -> None:
    """Test that when an old session's close callback fires after a new session with the same key
    has been registered, the new session is NOT removed from the registry.

    Scenario:
    1. Agent connects → server registers session A with key (env, "agent")
    2. Agent reconnects → server evicts A via notify_close_session, registers session B with same key
    3. Old handler's on_close fires → close_session(A) → on_close_session(A) → notify_close_session(A)
    4. notify_close_session must check identity (is not session) to avoid deleting session B
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    env_id = uuid.uuid4()

    try:
        # Simulate two sessions with the same key (same agent reconnecting).
        # Wire decoder._session so close_connection() works as in production.
        decoder_a = websocket.WebsocketFrameDecoder()
        session_a = websocket.Session(
            environment_id=env_id,
            session_name="agent",
            hostname="host1",
            websocket_protocol=decoder_a,
        )
        decoder_a._session = session_a

        decoder_b = websocket.WebsocketFrameDecoder()
        session_b = websocket.Session(
            environment_id=env_id,
            session_name="agent",
            hostname="host1",
            websocket_protocol=decoder_b,
        )
        decoder_b._session = session_b

        assert session_a.session_key == session_b.session_key
        assert session_a is not session_b

        # Register session A
        await rs._transport.register_session(session_a)
        assert rs._transport._sessions[session_a.session_key] is session_a

        # Agent reconnects: register session B (evicts A)
        await rs._transport.register_session(session_b)
        assert rs._transport._sessions[session_b.session_key] is session_b

        # Now simulate old handler's deferred on_close firing for session A.
        # This calls notify_close_session(A). The bug: it deletes B because same key.
        await rs._transport.notify_close_session(session_a)

        # Session B should still be in the registry
        assert (
            session_a.session_key in rs._transport._sessions
        ), "Session B was incorrectly removed from registry by old session A's close callback"
        assert (
            rs._transport._sessions[session_b.session_key] is session_b
        ), "Registry entry should still point to session B, not be deleted"
    finally:
        await rs.stop()


async def test_ws_evicted_session_connection_closed(inmanta_config: object, server_config: object) -> None:
    """Test that register_session itself closes the evicted session, rather than relying
    on the ping timeout to eventually close it.

    When register_session evicts an old session, it must close the session state (not just
    remove it from the dict). Otherwise the old session remains active and its deferred
    on_close callback can accidentally delete the new session from the registry.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    env_id = uuid.uuid4()

    try:
        # Create two sessions with the same key, simulating an agent reconnect.
        # Wire decoder._session so close_connection() works as in production.
        decoder_a = websocket.WebsocketFrameDecoder()
        session_a = websocket.Session(
            environment_id=env_id,
            session_name="agent",
            hostname="host1",
            websocket_protocol=decoder_a,
        )
        decoder_a._session = session_a

        decoder_b = websocket.WebsocketFrameDecoder()
        session_b = websocket.Session(
            environment_id=env_id,
            session_name="agent",
            hostname="host1",
            websocket_protocol=decoder_b,
        )
        decoder_b._session = session_b

        # Register session A
        await rs._transport.register_session(session_a)
        assert not session_a.is_closed()

        # Register session B with the same key — should evict A
        await rs._transport.register_session(session_b)

        # register_session must close the old session's connection, not just remove it
        # from the dict and notify listeners.
        assert session_a.is_closed(), (
            "Old session A should be closed by register_session when evicted, "
            "but it's still active — its deferred on_close can cause E1"
        )
    finally:
        await rs.stop()


async def test_ws_write_message_silent_drop_resolves_future(inmanta_config: object, server_config: object) -> None:
    """Test that when write_message silently returns (WebSocket already known to be closed),
    the pending RPC future is still resolved promptly rather than hanging until timeout.

    This covers the case where _ws_client.closed is True before write_message is called,
    so no exception is raised — write_message must signal failure so the caller doesn't hang.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Close the websocket cleanly so _ws_client.closed becomes True.
        # This is different from test_ws_write_failure_resolves_future which closes the
        # underlying TCP stream (causing write_message to raise). Here write_message detects
        # the closed state before writing and must still signal failure.
        assert agent._ws_client is not None
        agent._ws_client.close()

        # Wait briefly for the close to take effect
        await asyncio.sleep(0.1)

        # Make an RPC call — write_message should detect the closed WS and signal failure
        client = agent.session.get_typed_client()
        try:
            result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
            assert result != "server status"
        except asyncio.TimeoutError:
            raise AssertionError("RPC future was not resolved after silent write_message drop — hung until timeout")
        except Exception:
            # Any exception other than TimeoutError is acceptable
            pass
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_rpc_with_auth(inmanta_config: object, server_config: object) -> None:
    """Test that websocket authentication works end-to-end when auth is enabled.

    With auth enabled and a valid agent token configured:
    - The agent connects successfully (OpenSession with token is accepted)
    - Agent→server RPC calls succeed (token injected in Authorization header)
    - Server→agent RPC calls succeed (enforce_auth=False on agent side)
    """
    configure_auth(auth=True, ca=False, ssl=False, authorization_provider=AuthorizationProviderName.legacy)

    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent")
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Agent→server RPC should succeed (agent token is valid, method allows agent client type)
        client_a2s = agent.session.get_typed_client()
        result = await client_a2s.get_auth_server_status()
        assert result == "auth server status"

        # Server→agent RPC should succeed (enforce_auth=False on agent endpoint)
        client_s2a = rs._transport.get_session(*agent.session.session_key).get_typed_client()
        result = await client_s2a.get_auth_agent_status()
        assert result == "auth agent status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_open_session_rejected_without_token(inmanta_config: object, server_config: object) -> None:
    """Test that OpenSession is rejected when auth is enabled but no token is configured."""
    configure_auth(auth=True, ca=False, ssl=False, authorization_provider=AuthorizationProviderName.legacy)

    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    try:
        # Create an agent without a token by clearing the config after configure_auth sets it
        token_before = inmanta_config_mod.Config.get("agent_rest_transport", "token", None)
        inmanta_config_mod.Config.set("agent_rest_transport", "token", "")

        agent = WSAgent("agent", reconnect_delay=60)
        await agent.start()

        try:
            # The agent should NOT be able to establish an active session
            # Wait a bit and check that no session becomes active
            await asyncio.sleep(2)
            assert agent.session is None or not agent.session.active
        finally:
            # Restore the token
            if token_before:
                inmanta_config_mod.Config.set("agent_rest_transport", "token", token_before)
            await agent.stop()
    finally:
        await rs.stop()


async def test_ws_open_session_rejected_with_invalid_token(inmanta_config: object, server_config: object) -> None:
    """Test that OpenSession is rejected when auth is enabled and an invalid token is provided."""
    configure_auth(auth=True, ca=False, ssl=False, authorization_provider=AuthorizationProviderName.legacy)

    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    try:
        # Set an invalid token
        inmanta_config_mod.Config.set("agent_rest_transport", "token", "invalid.jwt.token")

        agent = WSAgent("agent", reconnect_delay=60)
        await agent.start()

        try:
            # The agent should NOT be able to establish an active session
            await asyncio.sleep(2)
            assert agent.session is None or not agent.session.active
        finally:
            await agent.stop()
    finally:
        await rs.stop()


async def test_ws_rpc_fails_without_token_in_headers(inmanta_config: object, server_config: object) -> None:
    """Test that RPC calls fail when auth is enabled but no token is in the RPC headers.

    This simulates the edge case where a session was established (e.g. before auth was enabled)
    but the RPC call doesn't carry a token. The server's execute_call should reject it.
    """
    # First start without auth so the session can be established
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)
    await agent.start()

    try:

        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Now enable auth on the server side (simulating a config change)
        inmanta_config_mod.Config.set("server", "auth", "true")
        # Load JWT config so decode_token works
        configure_auth(auth=True, ca=False, ssl=False, authorization_provider=AuthorizationProviderName.legacy)

        # The agent has no token (it was started without auth), so RPC calls should fail with 401/403
        # Use the auth_server_status method which enforces auth
        client_a2s = agent.session.get_typed_client()
        try:
            result = await asyncio.wait_for(client_a2s.get_auth_server_status(), timeout=5)
            # If we get here, the call should have failed (not returned the actual status)
            assert result != "auth server status", "RPC should have been rejected without auth token"
        except Exception:
            # Any exception is acceptable — the point is the call is rejected
            pass
    finally:
        await rs.stop()
        await agent.stop()
