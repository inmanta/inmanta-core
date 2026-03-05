# PR #8719: WebSocket Refactor — Code Review

**PR:** https://github.com/inmanta/inmanta-core/pull/8719
**Branch:** `websocket-refactor` → `master`
**Author:** Bart Vanbrabant (+ Claude co-authored commits)
**Reviewed:** 2026-03-04
**Updated:** 2026-03-05 (round 3 protocol & server-client interaction review)
**Diff:** +1,722 / -2,328 lines across 46 files

> **To resume working on these items with Claude Code:**
> ```
> cd /home/bart/workspace/inmanta-core && git checkout websocket-refactor
> claude --resume
> ```
> Then reference this file: "Let's work through the items in PR-8719-REVIEW.md"

---

## Overview

This PR replaces REST-based heartbeat/long-poll for server-agent communication with persistent WebSocket connections. It removes `AgentInstance`, renames `AgentProcess` → `SchedulerSession`, removes `SessionManager`, the heartbeat protocol, and primary election logic.

The PR description is excellent. The architectural direction is sound. Most round-1 issues have been addressed. The round-2 deep review found significant new issues in concurrency, resource management, and protocol correctness.

---

## Round 1 Issues — Status

All round-1 items have been verified. Summary:

| ID     | Issue                                  | Status                                            |
| ------ | -------------------------------------- | ------------------------------------------------- |
| C1     | Reconnection loop crashes              | **FIXED**                                         |
| C2     | Memory leak in timed-out replies       | **FIXED**                                         |
| C3     | `Agent.get_status()` always returns up | **FIXED**                                         |
| C4     | Server ping timeout not configured     | **FIXED**                                         |
| C5     | `_db_monitor` AttributeError           | **FIXED**                                         |
| C6     | Duplicate session on frame decoder     | **FIXED**                                         |
| C7     | `RejectSession` stub                   | **FIXED**                                         |
| S1     | WebSocket auth bypass                  | **OPEN** — see below                              |
| S2     | Information disclosure                 | **FIXED**                                         |
| T1-T6  | Test gaps                              | **FIXED** (T2 residual: `test_ws_2way` busy-wait) |
| Q1-Q12 | Code quality                           | **FIXED** (Q4 residual: `on_reconnect` docstring) |
| M1-M3  | Migration                              | **FIXED**                                         |

---

## Round 2 — Deep Review Findings

### CRITICAL

#### D1. `_register_session` assert checks wrong key — ghost sessions accumulate
- [x] **Fix required**
- **File:** `src/inmanta/server/agentmanager.py:499`

```python
async def _register_session(self, session, now):
    async with self.session_lock:
        assert session.id not in self.scheduler_for_env  # BUG: wrong dict!
        self.scheduler_for_env[session.environment] = session
        self.sessions[session.id] = session
```

`self.scheduler_for_env` is keyed by **environment UUID**, but the assert checks `session.id` (a random UUID). This assert is **always true** and checks nothing. If a second session registers for the same environment, the old session is silently overwritten in `scheduler_for_env` but remains as a ghost entry in `self.sessions` (keyed by the old session ID), never getting expired from memory.

**Fix:** `assert session.environment not in self.scheduler_for_env`

---

#### D2. Pending RPC futures not cleaned up on disconnect — callers hang until timeout
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py` — `close_session()` (lines 369-375) and `_process_messages` disconnect path

When the WebSocket connection drops, all pending futures in `self._replies` are **never resolved**. Callers awaiting those futures hang until their individual timeouts (up to 120 seconds). If 50 RPCs are in-flight when the connection dies, all 50 callers wait independently.

**Fix:** In `close_session()` or on disconnect, iterate `_replies`, set an error result on each pending future, and clear the dict:
```python
for reply_id, future in self._replies.items():
    if not future.done():
        future.set_result(common.Result(code=503, result={"message": "Connection lost"}))
self._replies.clear()
```

---

#### D3. `_handle_call` uses `json_encode` instead of `model_dump_json` — serialization mismatch
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py:384`

```python
reply = await self.dispatch_method(msg)
if reply is not None:
    await self.write_message(common.json_encode(reply))  # BUG
```

Every other serialization point in the file uses Pydantic's `.model_dump_json()`. `json_encode` is a `json.dumps` wrapper with a custom encoder. The receiving side parses with `pydantic.TypeAdapter.validate_json()`. Serialization/deserialization format mismatch could cause parsing failures, especially for UUID fields and datetime types.

**Fix:** `await self.write_message(reply.model_dump_json())`

---

#### D4. Rapid reconnect can leak sessions on server side
- [x] **Investigate**
- **File:** `src/inmanta/protocol/websocket.py:637-639`

Each `_reconnect()` call creates a new `Session` via `create_session()`, replacing `self._session`. The old session is **never explicitly closed** — its `_closed` flag stays `False`, and it retains a reference to the `WebsocketFrameDecoder` (via `websocket_protocol`). If any background task holds a reference to the old session (e.g., from `on_open_session`), calling methods on it will operate on the *current* decoder state, not the old session's.

On the server side, if the TCP connection drops without a clean close, the old session remains registered until the server's ping timeout fires. During this window, the agent's reconnect creates a new connection + new session. The server-side `register_session` handles this by evicting the old session (rest/server.py:409-414), but there's a timing window where the old listener callbacks haven't completed yet when the new session registers.

---

### HIGH

#### D5. `close_connection` sends `CloseSession` after closing local session — wrong order
- [x] **Fix recommended**
- **File:** `src/inmanta/protocol/websocket.py:400-403`

```python
async def close_connection(self) -> None:
    await self.close_session()            # closes local session first
    await self.write_message(CloseSession().model_dump_json())  # then notifies remote
```

The remote side should be notified **before** local teardown, so it can process the close message while the session is still logically open. As written, the remote side receives `CloseSession` after the local session state is already torn down.

---

#### D6. `write_message` failure in `rpc_call` silently leaves caller hanging
- [x] **Fixed** — added `_send_rpc_call` helper that catches write failures and resolves future with 503; `close_connection` now handles write errors gracefully
- **File:** `src/inmanta/protocol/websocket.py:284`

```python
self.add_background_task(self.write_message(RPC_Call(...).model_dump_json()))
```

The write is a fire-and-forget background task. If it fails (e.g., `WebSocketClosedError`), the caller's future is never resolved. The caller waits until timeout (up to 120s). Combined with D2, this makes error recovery very slow.

**Suggestion:** Either detect write failure and resolve the future immediately, or don't use a background task for the write.

---

#### D7. `stop()` and `_reconnect()` can interleave
- [x] **Investigate** — documented ordering guarantee in `stop()` docstring
- **File:** `src/inmanta/protocol/websocket.py:645-649, 607-639`

`stop()` cancels background tasks (including `_process_messages`) and then calls `close_connection()`. But `_process_messages` might be inside `_reconnect()` when cancelled. The `CancelledError` propagates out of `_reconnect`, but `close_connection()` then tries to write `CloseSession` on a half-initialized connection. The `write_message` guard protects against `None` `_ws_client`, but not against a connection in an indeterminate state.

---

#### D8. Dual disconnect handling — `_on_disconnect` callback races with `_process_messages`
- [x] **Investigate**
- **File:** `src/inmanta/protocol/websocket.py:634-643, 676-697`

When the connection drops, two things happen simultaneously:
1. `_on_disconnect` callback fires (line 634-636), scheduling `on_disconnect()` as a background task
2. `_process_messages` gets `None` from `read_message()` (line 677), sleeps, and calls `_reconnect()`

No coordination exists between these paths. `on_disconnect()` may run while `_reconnect()` is in progress. `on_reconnect()` (called from `on_open_session`) could interleave with `on_disconnect()` from the callback. For `Agent`, `on_disconnect` calls `stop_working()` while `on_reconnect` calls `start_working()` — if they interleave, the scheduler state can be corrupted.

---

#### D9. `Agent.to_dict()` always reports status as "down"
- [x] **Documented** — added comment explaining sync limitation; callers should use AgentView or get_statuses()
- **File:** `src/inmanta/data/__init__.py:~3484`

```python
def to_dict(self) -> JsonType:
    base = BaseDocument.to_dict(self)
    base["state"] = self.get_status().value  # has_active_session defaults to False
```

`get_status()` is called without `has_active_session` argument, defaulting to `False`. Every call to `to_dict()` reports non-paused agents as "down". The v1 `list_agents` API uses `to_dict()` indirectly.

---

#### D10. `_ws_client.close()` not awaited — incomplete shutdown
- [x] **No fix needed** — Tornado `close()` is synchronous, not a future
- **File:** `src/inmanta/protocol/websocket.py:723`

```python
if self._ws_client:
    self._ws_client.close()  # returns a future that is not awaited
```

Tornado's `close()` returns a future. Not awaiting it means the WebSocket close handshake may not complete, leaving server-side resources in an ambiguous state.

---

#### D11. `Agent.get_statuses` N+1 query problem
- [x] **Fixed** — replaced N `get_one()` calls with single `get_list()` + dict lookup
- **File:** `src/inmanta/data/__init__.py:~3453-3465`

Performs 1 query for live sessions + N queries for N agent names. Should use a single `WHERE name IN (...)` query.

---

#### D12. Wrong error message in `get_session` — says "Duplication" when session not found
- [x] **Already fixed** — error message already reads "Session not found"
- **File:** `src/inmanta/protocol/rest/server.py:434-435`

```python
raise KeyError("Duplication session")  # TODO: correct exception
```

Error message says "Duplication" but condition is "not found". Exception type `KeyError` is inappropriate for API layer.

---

### MEDIUM

#### D13. `_expire_session` silently drops cleanup during shutdown
- [x] **Acceptable risk — documented**
- **File:** `src/inmanta/server/agentmanager.py:521-526`

If `is_stopping()` is true, queued expire actions are discarded. Sessions are cleaned from DB at next startup (`_expire_all_sessions_in_db`), but in-memory dictionaries can have stale entries during the shutdown window.

---

#### D14. `on_open_session` runs inline on server (blocks message loop) but as background on client
- [x] **Documented**
- **File:** `src/inmanta/protocol/websocket.py:316-318 vs 321-329`

On the server side, a slow `on_open_session` blocks all message processing on that connection. On the client side, it runs as a background task. This asymmetry is intentional but could cause issues if `on_open_session` performs RPCs or DB queries.

---

#### D15. `match_call` rebuilds URL mapping on every WebSocket RPC message
- [x] **Fixed** — cached `get_op_mapping()` result on `CallTarget` using lazy attribute initialization
- **File:** `src/inmanta/protocol/rest/__init__.py:698-713`

`target.get_op_mapping()` rebuilds the mapping each call. Should be cached once at startup.

---

#### D16. `start_connected()` called before session is confirmed
- [x] **Documented** — fixed misleading docstring
- **File:** `src/inmanta/protocol/websocket.py:639`

`start_connected()` runs after `session.open()` sends `OpenSession` but before `SessionOpened` is received. Session is not yet `active`. RPC calls in `start_connected()` would fail.

---

#### D17. Diamond inheritance in `SessionEndpoint` — double `TaskHandler.__init__`
- [x] **Fixed** — added idempotency guard in `TaskHandler.__init__` to skip re-initialization in diamond hierarchies
- **File:** `src/inmanta/protocol/websocket.py:535-548`

```python
class SessionEndpoint(endpoints.Endpoint, common.CallTarget, WebsocketFrameDecoder, rest.AuthnzInterface):
    def __init__(self, ...):
        endpoints.Endpoint.__init__(self, name)       # calls TaskHandler.__init__
        WebsocketFrameDecoder.__init__(self)           # calls TaskHandler.__init__ AGAIN
```

`TaskHandler.__init__` is called twice, resetting `_background_tasks`. If `Endpoint.__init__` adds tasks before `WebsocketFrameDecoder.__init__`, they are lost.

---

#### D18. Invalid type annotation for `_sessions` dict key
- [x] **Fix**
- **File:** `src/inmanta/protocol/rest/server.py:304`

```python
self._sessions: dict[(uuid.UUID, str), websocket.Session] = {}
```

Should be `dict[tuple[uuid.UUID, str], websocket.Session]`.

---

#### D19. Mutable default argument in `RESTServer.start()`
- [x] **Fix**
- **File:** `src/inmanta/protocol/rest/server.py:329`

```python
async def start(self, targets, additional_rules: list[routing.Rule] = []) -> None:
```

Classic Python anti-pattern. Should be `= None` with guard.

---

#### D20. Dead `on_pong_callback` — pong never tracked on client
- [x] **Removed**
- **File:** `src/inmanta/protocol/websocket.py:623, 525-527`

`on_pong_callback=None` is always passed. The `WebSocketClientConnection` class has pong handling code (lines 525-527) that is never triggered. If client-side liveness tracking was intended, this needs to be wired up.

---

### LOW

#### D21. `_process_session_listener_actions` references potentially unbound variable
- [x] **Documented** — added comment explaining variable is guaranteed bound (queue.get only raises CancelledError)
- **File:** `src/inmanta/server/agentmanager.py:438`

If `queue.get()` raises non-CancelledError, `session_action` is unbound in the `except` block → `UnboundLocalError` masks original exception.

---

#### D22. `get_agent_client` isinstance check contradicts type annotation
- **File:** `src/inmanta/server/agentmanager.py:564`

`tid: uuid.UUID` but code does `if isinstance(tid, str)`. Either fix callers or update annotation.

---

#### D23. Test bug: truthiness assertion instead of equality
- [x] **Fix**
- **File:** `tests/protocol/test_2way_protocol.py:153`

```python
assert status.result["agents"][0]["status"], "ok"
```

This asserts truthiness, not equality. Should be `== "ok"`.

---

#### D24. Typo "tupple" in error message
- **File:** `src/inmanta/protocol/rest/__init__.py:523`

---

## Security — S1 Still Open

### S1. WebSocket endpoint authentication
- [ ] **Verify / Fix**
- **File:** `src/inmanta/protocol/websocket.py:569-573`

No authentication occurs during WebSocket upgrade or `OPEN_SESSION`. No test validates that unauthenticated/expired-token WebSocket upgrades are rejected. This is the most important open item.

---

## Test Coverage Analysis (Round 2)

### What IS well tested
- Basic bidirectional RPC (test_ws_2way)
- Ping timeout detection and auto-reconnect (test_ws_ping_timeout_closes_stale_connection)
- Reconnection after connection failure (test_ws_reconnect_on_connection_failure)
- Duplicate session rejection on same connection (test_ws_reject_duplicate_session_on_same_connection)
- Client-side RejectSession handling (test_ws_client_handles_reject_session)
- Concurrent RPCs (test_ws_concurrent_rpcs, 10 calls)
- RPC on dead connection fails (test_ws_rpc_on_closed_session)
- Server shutdown + agent reconnect (test_ws_server_shutdown_during_active_session)
- Session eviction on duplicate (test_ws_duplicate_session_replaces_old)
- SessionListener callback ordering
- SchedulerSession CRUD and cleanup
- AgentManager session registration/expiry

### What is NOT tested (significant gaps)

| Gap                                           | Risk         | Notes                                                           |
| --------------------------------------------- | ------------ | --------------------------------------------------------------- |
| WebSocket upgrade auth                        | **Critical** | No test for unauthenticated WS connection                       |
| Malformed WS messages                         | High         | No test for invalid JSON, wrong action types, wrong field types |
| Agent crash with in-flight RPCs               | High         | Server-side future cleanup untested                             |
| Concurrent register + expire for same env     | High         | Only sequential paths tested                                    |
| Server crash (SIGKILL) recovery               | Medium       | Only graceful shutdown tested                                   |
| DB failure during session expiry logging      | Medium       | Only creation failure tested                                    |
| Multiple environments interleaved             | Medium       | All multi-env tests are sequential                              |
| Large-scale concurrent RPCs (100+)            | Medium       | Only 10 tested                                                  |
| `on_disconnect` / `on_reconnect` interleaving | Medium       | Related to D8                                                   |
| `stop()` during `_reconnect()`                | Medium       | Related to D7                                                   |

### MockSession fidelity issues
The `MockSession` in `test_agent_manager.py` does not implement: `active` property, `session_key`, `close_session()`, `is_closed()`, `confirm_open()`, `get_typed_client()`, `close_connection()`. Tests using this mock may pass even when production code has bugs in these code paths.

---

## Remaining TODO Comments

| File             | Line | TODO                             | Status                  |
| ---------------- | ---- | -------------------------------- | ----------------------- |
| `websocket.py`   | 292  | "log this"                       | Stale — already logging |
| `websocket.py`   | 345  | Handle RPC_Call when not active  | Open                    |
| `websocket.py`   | 351  | Handle RPC_Reply when not active | Open                    |
| `rest/server.py` | 338  | Add constant for `/v2/ws`        | Open                    |
| `rest/server.py` | 434  | Correct exception type           | Open                    |

---

## Round 3 — Protocol & Server-Client Interaction Review

**Updated:** 2026-03-05

Focus: protocol correctness, race conditions in session lifecycle, edge cases in RPC delivery, targeted tests to break the implementation.

### CRITICAL

#### E1. `notify_close_session` can delete the wrong session — active session dropped from registry
- [x] **Fixed** — identity check (`is not session`) instead of key existence in `notify_close_session`
- **File:** `src/inmanta/protocol/rest/server.py:438-445`
- **Test:** `tests/protocol/test_ws_round3.py::test_ws_notify_close_session_identity_check`

`notify_close_session` checks `session.session_key not in self._sessions` but does **not** verify that the session currently in the dict is the *same* session being closed. When a new session B replaces old session A (same agent reconnecting), the old connection's deferred `on_close` callback can delete the new session:

1. Agent connects → H1 creates session A, registered with key `(env, "agent")`
2. Agent reconnects → H2 creates session B with same key
3. `register_session(B)` evicts A via `notify_close_session(A)` — deletes dict entry, notifies listeners, registers B
4. H1's WebSocket eventually closes (ping timeout) → `on_close()` → `close_session()`
5. `A.is_closed()` is **False** — nobody called `A.close_session()`, only `notify_close_session` (which is a listener notification, not session state change)
6. `close_session()` proceeds → calls `on_close_session(A)` → `notify_close_session(A)`
7. `A.session_key in self._sessions` → **True** (because B has the same key!)
8. **Deletes B from the dict!** Notifies listeners that A closed → cascading damage to `AgentManager` (removes `scheduler_for_env[env]` which now points to B)

After this, the server has no session for this agent. All RPC calls to the agent fail. The agent doesn't know its session was dropped.

**Fix:** Check identity, not just key existence:
```python
async def notify_close_session(self, session: websocket.Session) -> None:
    if self._sessions.get(session.session_key) is not session:
        return
    del self._sessions[session.session_key]
    for listener in self.listeners:
        await listener.session_closed(session)
```

**Cascade impact:** Without this fix, `test_ws_rapid_reconnect_cycles` and `test_ws_duplicate_session_replaces_old` can intermittently fail depending on timing of the old handler's `on_close`.

---

### HIGH

#### E2. `write_message` silently drops messages when WS is closed — RPC futures hang
- [x] **Fixed** — `SessionEndpoint.write_message` raises `ConnectionError`, `WebsocketHandler.write_message` lets `WebSocketClosedError` propagate; `_send_rpc_call` catches both and resolves future with 503
- **File:** `src/inmanta/protocol/websocket.py:704-708` (client) and `src/inmanta/protocol/rest/server.py:257-261` (server)
- **Test:** `tests/protocol/test_ws_round3.py::test_ws_write_message_silent_drop_rpc_hangs`

Both `SessionEndpoint.write_message` and `WebsocketHandler.write_message` silently return when the WebSocket is closed (one checks `self._ws_client.closed`, the other catches `WebSocketClosedError`). The `_send_rpc_call` helper resolves the future only on exception, so a silent return leaves the future pending until `handle_timeout` fires (30-120 seconds later).

The existing D6 fix (`_send_rpc_call`) correctly catches exceptions from `write_message`, but both implementations swallow the error before it can propagate.

**Fix:** Either:
1. Make `write_message` raise on failure (all callers already handle exceptions), or
2. Have `_send_rpc_call` check a return value/flag from `write_message`

Option 1 is cleaner:
```python
# SessionEndpoint.write_message
async def write_message(self, message: str | bytes, binary: bool = False) -> None:
    if self._ws_client is None or self._ws_client.closed:
        raise ConnectionError("WebSocket is closed")
    await self._ws_client.write_message(message, binary)

# WebsocketHandler.write_message
async def write_message(self, message: str | bytes, binary: bool = False) -> None:
    await tornado_websocket.WebSocketHandler.write_message(self, message, binary)
    # Let WebSocketClosedError propagate — callers handle it
```

---

#### E3. `register_session` doesn't close evicted session's connection — stale handler lingers
- [x] **Fixed** — `register_session` now calls `old_session.close_session()` before evicting, preventing deferred on_close from causing damage
- **File:** `src/inmanta/protocol/rest/server.py:424-436`

When `register_session(B)` evicts old session A, it only calls `notify_close_session(A)` (listener notification). It does **not** close A's WebSocket connection or call `A.close_session()`. This means:
- H1 (old WebSocket handler) remains alive, still receiving messages
- Session A's `_closed` flag remains False
- When H1's connection eventually closes, its `close_session()` runs and triggers E1

**Fix:** Close the old session's connection before registering the new one:
```python
async def register_session(self, session: websocket.Session) -> None:
    if session.session_key in self._sessions:
        old_session = self._sessions[session.session_key]
        await old_session.close_connection()  # This closes the WS and marks session as closed
    self._sessions[session.session_key] = session
    for listener in self.listeners:
        await listener.session_opened(session)
```

Note: `close_connection` sends CloseSession, calls `close_session()` (setting `_closed=True`), and then `on_close_session` fires which calls `notify_close_session`. This correctly cleans up and prevents E1.

---

### MEDIUM

#### E4. Stale ASCII diagram and class docstring in agentmanager.py
- [x] **Fixed** — updated diagram and docstring to reflect current model (no more agent instances)
- **File:** `src/inmanta/server/agentmanager.py:72-99, 127-137`

The ASCII diagram still references "AGENT INSTANCE" and the old model. The class docstring still mentions "primary agent instance" and "agent instance process". These concepts were removed by this PR.

---

#### E5. `_on_disconnect` fires `on_disconnect()` even when session hasn't been cleaned up yet
- [x] **Documented** — intentional ordering: on_disconnect fires promptly to stop work, session cleanup happens later in _reconnect
- **File:** `src/inmanta/protocol/websocket.py:669-671`

When the connection drops, `_on_disconnect` schedules `on_disconnect()` as a background task. But at this point, `close_session()` hasn't been called yet (it happens later in `_reconnect`). This means `Agent.on_disconnect()` → `stop_working()` fires while the session is still technically active. The `_process_messages` loop then sleeps for `reconnect_delay` before calling `_reconnect()` → `close_session()`. During this window, the agent has stopped working but the session is still registered on the server.

---

### LOW

#### E6. `close_connection` sends CloseSession even when session is already closed
- [x] **Fixed** — guard write with session state check
- **File:** `src/inmanta/protocol/websocket.py:420-426`

```python
async def close_connection(self) -> None:
    try:
        await self.write_message(CloseSession().model_dump_json())
    except Exception:
        ...
    await self.close_session()
```

If `close_session()` was already called (session `_closed=True`), `close_connection` still tries to send CloseSession. The `close_session()` call then returns early (line 380). This is mostly harmless but wastes a write on a message that will confuse the remote if the session is already closed.

---

## Round 3 Tests

Created: `tests/protocol/test_ws_round3.py`

| Test                                          | Target                                                               | Status                                  |
| --------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| `test_ws_notify_close_session_identity_check` | E1: Verifies new session not deleted by old session's close callback | **Expected to fail** (E1 bug)           |
| `test_ws_write_message_silent_drop_rpc_hangs` | E2: RPC on closed WS resolves promptly, not at timeout               | **Expected to fail** (E2 bug)           |
| `test_ws_malformed_message_no_crash`          | Robustness: various malformed messages don't crash                   | Should pass                             |
| `test_ws_rpc_reply_for_unknown_id_ignored`    | Stale/spoofed RPC_Reply safely ignored                               | Should pass                             |
| `test_ws_close_session_then_rpc_call`         | CloseSession followed by RPC_Call doesn't crash                      | Should pass                             |
| `test_ws_rapid_reconnect_cycles`              | E1 interaction: 5 rapid reconnect cycles, registry stays consistent  | **May intermittently fail** (E1 timing) |

### Full test source: `tests/protocol/test_ws_round3.py`

```python
"""
Round 3 review tests: Protocol edge cases and server-client interaction.

These tests target specific race conditions and edge cases in the WebSocket
protocol implementation.
"""

import asyncio
import logging
import uuid

from inmanta import const
from inmanta.protocol import SessionEndpoint, handle, typedmethod, websocket
from inmanta.protocol.auth.decorators import auth
from inmanta.server.protocol import Server, ServerSlice

LOGGER = logging.getLogger(__name__)


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/server_status", operation="GET")
def get_current_server_status() -> str:
    """Get the status of the server"""


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/agent_status", operation="GET")
def get_current_agent_status() -> str:
    """Get the status of the agent"""


class WSServer(websocket.SessionListener, ServerSlice):
    def __init__(self) -> None:
        ServerSlice.__init__(self, "wsserver")

    @handle(get_current_server_status)
    async def get_current_server_status(self) -> str:
        return "server status"


class WSAgent(SessionEndpoint):
    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5) -> None:
        super().__init__(name, uuid.uuid4(), timeout, reconnect_delay)

    @handle(get_current_agent_status)
    async def get_current_agent_status(self) -> str:
        return "agent status"


class SessionSpy(websocket.SessionListener):
    """Records session lifecycle events for assertions."""

    def __init__(self) -> None:
        self.events: list[tuple[str, uuid.UUID]] = []

    async def session_opened(self, session: websocket.Session) -> None:
        self.events.append(("opened", session.id))

    async def session_closed(self, session: websocket.Session) -> None:
        self.events.append(("closed", session.id))


async def test_ws_notify_close_session_identity_check(inmanta_config, server_config) -> None:
    """E1: Test that notify_close_session does not delete a newer session with the same key.

    Scenario:
    1. Agent connects → session A registered
    2. Agent reconnects → session B registered (evicting A from dict)
    3. Old connection (H1) closes asynchronously → on_close fires for H1's decoder
    4. H1's close_session() calls on_close_session(A) → notify_close_session(A)
    5. BUG: notify_close_session sees A.session_key in _sessions (because B has the same key)
       and deletes B from the registry!

    After this, the server has no session for this agent and RPC calls fail.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    spy = SessionSpy()
    rs._transport.add_session_listener(spy)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    try:
        # Wait for session to become active
        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Record the first session
        session_key = agent.session.session_key
        assert session_key in rs._transport._sessions
        first_server_session = rs._transport._sessions[session_key]

        # Force-close the TCP stream to simulate network partition.
        # The server-side ping timeout hasn't fired yet, so the server still thinks H1 is alive.
        assert agent._ws_client is not None
        agent._ws_client.protocol.stream.close()

        # Wait for agent to reconnect with a new session
        async def wait_for_new_session() -> None:
            while True:
                if agent.session and agent.session.active and agent.session.session_key in rs._transport._sessions:
                    server_session = rs._transport._sessions[agent.session.session_key]
                    if server_session is not first_server_session:
                        return
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_new_session(), timeout=30)

        # Session B is now registered. Record it.
        second_server_session = rs._transport._sessions[session_key]
        assert second_server_session is not first_server_session

        # Now wait for the server's ping timeout to detect H1's dead connection.
        # When H1.on_close fires, it calls close_session() for H1's decoder,
        # which calls notify_close_session(session_A).
        # Give it enough time for the ping timeout (ws-ping-interval=1, ws-ping-timeout=1)
        await asyncio.sleep(5)

        # THE CRITICAL CHECK: Session B should still be in the registry!
        assert session_key in rs._transport._sessions, (
            "BUG: The new session was deleted from the registry by the old session's close callback. "
            f"Events: {spy.events}"
        )
        assert rs._transport._sessions[session_key] is second_server_session, (
            "BUG: The session in the registry is not the expected one"
        )

        # Verify RPC still works through the current session
        client_a2s = agent.session.get_typed_client()
        result = await asyncio.wait_for(client_a2s.get_current_server_status(), timeout=5)
        assert result == "server status"

        # Verify server-to-agent RPC also works
        client_s2a = rs._transport.get_session(*agent.session.session_key).get_typed_client()
        result = await asyncio.wait_for(client_s2a.get_current_agent_status(), timeout=5)
        assert result == "agent status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_write_message_silent_drop_rpc_hangs(inmanta_config, server_config) -> None:
    """E2: Test that RPC calls don't hang when write_message silently drops the message.

    SessionEndpoint.write_message returns silently when self._ws_client is None or closed.
    If _send_rpc_call doesn't detect this, the RPC future hangs until timeout.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=60)  # Long delay to prevent reconnect during test
    await agent.start()

    try:
        async def wait_for_active() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active(), timeout=10)

        # Set _ws_client to None to trigger the silent return path in write_message
        old_ws = agent._ws_client
        agent._ws_client = None

        # Make an RPC call. write_message will return silently without sending.
        # The future should still resolve (not hang).
        client = agent.session.get_typed_client()
        try:
            result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
            # If we get a result, it should indicate an error
            assert result != "server status", f"Got unexpected success: {result}"
        except asyncio.TimeoutError:
            raise AssertionError(
                "BUG: RPC future was not resolved after write_message silently dropped the message. "
                "The future hangs until handle_timeout fires (up to 120s)."
            )
        except Exception:
            # Any other exception is acceptable
            pass
        finally:
            # Restore for clean shutdown
            agent._ws_client = old_ws
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_malformed_message_no_crash(inmanta_config, server_config) -> None:
    """E3: Test that malformed messages don't crash the connection.

    Send various malformed messages and verify the session stays active.
    """
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

        assert agent._ws_client is not None

        # Send various malformed messages directly to the server's WebSocket
        malformed_messages = [
            "",                                          # empty
            "not json at all",                           # not JSON
            "{}",                                        # missing action field
            '{"action": "UNKNOWN_ACTION"}',              # unknown action
            '{"action": "RPC_CALL"}',                    # missing required fields
            '{"action": "OPEN_SESSION"}',                # missing required fields
            '{"action": "RPC_REPLY", "reply_id": "not-a-uuid", "code": 200}',  # invalid UUID
            '{"action": "SESSION_OPENED"}',              # unexpected SessionOpened
            '{"action": "CLOSE_SESSION"}',               # premature close (session already active)
        ]

        for msg in malformed_messages:
            try:
                await agent._ws_client.write_message(msg)
            except Exception:
                pass  # Connection might close on some of these
            await asyncio.sleep(0.1)

        # Give the server time to process all messages
        await asyncio.sleep(1)

        # The agent should eventually reconnect if the connection was dropped
        async def wait_for_active_again() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active_again(), timeout=30)

        # Verify RPC still works
        client = agent.session.get_typed_client()
        result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
        assert result == "server status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_rpc_reply_for_unknown_id_ignored(inmanta_config, server_config) -> None:
    """E4: Test that a spoofed or stale RPC_Reply for an unknown reply_id is safely ignored."""
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

        # Send a fake RPC_Reply with a random reply_id to the agent
        fake_reply = websocket.RPC_Reply(
            reply_id=uuid.uuid4(),
            result={"data": "injected"},
            code=200,
        ).model_dump_json()
        await agent._ws_client.write_message(fake_reply)
        await asyncio.sleep(0.5)

        # Session should still be active
        assert agent.session.active

        # RPC should still work
        client = agent.session.get_typed_client()
        result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
        assert result == "server status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_close_session_then_rpc_call(inmanta_config, server_config) -> None:
    """E5: Test that sending a CloseSession followed by an RPC_Call doesn't crash.

    After CloseSession, the session is inactive and RPC_Call should be dropped.
    """
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

        assert agent._ws_client is not None

        # Send CloseSession to the agent
        close_msg = websocket.CloseSession().model_dump_json()
        await agent._ws_client.write_message(close_msg)
        await asyncio.sleep(0.5)

        # Now send an RPC_Call on the same connection — should be ignored since session is closed
        rpc_msg = websocket.RPC_Call(
            url="/api/v2/server_status",
            method="GET",
            headers={},
            body=None,
            reply_id=uuid.uuid4(),
        ).model_dump_json()
        await agent._ws_client.write_message(rpc_msg)
        await asyncio.sleep(0.5)

        # The agent should reconnect and be active again
        async def wait_for_active_again() -> None:
            while not agent.session or not agent.session.active:
                await asyncio.sleep(0.1)

        await asyncio.wait_for(wait_for_active_again(), timeout=30)

        # Verify everything works
        client = agent.session.get_typed_client()
        result = await client.get_current_server_status()
        assert result == "server status"
    finally:
        await rs.stop()
        await agent.stop()


async def test_ws_rapid_reconnect_cycles(inmanta_config, server_config) -> None:
    """E6: Test that rapid connect/disconnect cycles don't corrupt state.

    Rapidly close the TCP stream multiple times to trigger reconnect cycles
    and verify the server's session registry stays consistent.
    """
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    spy = SessionSpy()
    rs._transport.add_session_listener(spy)
    await rs.start()

    agent = WSAgent("agent", reconnect_delay=1)
    await agent.start()

    try:
        for cycle in range(5):
            # Wait for active session
            async def wait_for_active() -> None:
                while not agent.session or not agent.session.active:
                    await asyncio.sleep(0.1)

            await asyncio.wait_for(wait_for_active(), timeout=15)

            # Verify the server has exactly one session for this agent
            session_key = agent.session.session_key
            assert session_key in rs._transport._sessions, f"Cycle {cycle}: session not in registry"

            if cycle < 4:  # Don't break on the last iteration
                # Force-close TCP stream
                assert agent._ws_client is not None
                agent._ws_client.protocol.stream.close()
                # Brief delay to let the disconnect propagate
                await asyncio.sleep(0.5)

        # After all cycles, verify final state
        assert agent.session is not None
        assert agent.session.active
        assert len(rs._transport._sessions) == 1

        # Verify RPC works
        client = agent.session.get_typed_client()
        result = await asyncio.wait_for(client.get_current_server_status(), timeout=5)
        assert result == "server status"

        # Wait for all server-side session cleanups to complete
        await asyncio.sleep(5)

        # The server should still have exactly one session
        assert len(rs._transport._sessions) == 1, (
            f"Expected 1 session, got {len(rs._transport._sessions)}. "
            f"Possible ghost sessions from race condition. Events: {spy.events}"
        )
    finally:
        await rs.stop()
        await agent.stop()
```

---

## Summary Priority Matrix

| Priority     | Fixed                                     | Remaining                                  |
| ------------ | ----------------------------------------- | ------------------------------------------ |
| **Critical** | D1, D2, D3, E1                            | S1 (auth)                                  |
| **High**     | D4, D5, D6, D7, D8, D9, D10, D11, D12, E2, E3 |         |
| **Medium**   | D13, D14, D15, D16, D17, D18, D19, D20, E4, E5 |           |
| **Low**      | D21, D22, D23, D24, E6                    |           |
