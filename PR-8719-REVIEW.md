# PR #8719: WebSocket Refactor — Code Review

**PR:** https://github.com/inmanta/inmanta-core/pull/8719
**Branch:** `websocket-refactor` → `master`
**Author:** Bart Vanbrabant (+ Claude co-authored commits)
**Reviewed:** 2026-03-04
**Updated:** 2026-03-04 (round 2 deep review after rebase)
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

| ID | Issue | Status |
|----|-------|--------|
| C1 | Reconnection loop crashes | **FIXED** |
| C2 | Memory leak in timed-out replies | **FIXED** |
| C3 | `Agent.get_status()` always returns up | **FIXED** |
| C4 | Server ping timeout not configured | **FIXED** |
| C5 | `_db_monitor` AttributeError | **FIXED** |
| C6 | Duplicate session on frame decoder | **FIXED** |
| C7 | `RejectSession` stub | **FIXED** |
| S1 | WebSocket auth bypass | **OPEN** — see below |
| S2 | Information disclosure | **FIXED** |
| T1-T6 | Test gaps | **FIXED** (T2 residual: `test_ws_2way` busy-wait) |
| Q1-Q12 | Code quality | **FIXED** (Q4 residual: `on_reconnect` docstring) |
| M1-M3 | Migration | **FIXED** |

---

## Round 2 — Deep Review Findings

### CRITICAL

#### D1. `_register_session` assert checks wrong key — ghost sessions accumulate
- [ ] **Fix required**
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
- [ ] **Fix required**
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
- [ ] **Fix required**
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
- [ ] **Investigate**
- **File:** `src/inmanta/protocol/websocket.py:637-639`

Each `_reconnect()` call creates a new `Session` via `create_session()`, replacing `self._session`. The old session is **never explicitly closed** — its `_closed` flag stays `False`, and it retains a reference to the `WebsocketFrameDecoder` (via `websocket_protocol`). If any background task holds a reference to the old session (e.g., from `on_open_session`), calling methods on it will operate on the *current* decoder state, not the old session's.

On the server side, if the TCP connection drops without a clean close, the old session remains registered until the server's ping timeout fires. During this window, the agent's reconnect creates a new connection + new session. The server-side `register_session` handles this by evicting the old session (rest/server.py:409-414), but there's a timing window where the old listener callbacks haven't completed yet when the new session registers.

---

### HIGH

#### D5. `close_connection` sends `CloseSession` after closing local session — wrong order
- [ ] **Fix recommended**
- **File:** `src/inmanta/protocol/websocket.py:400-403`

```python
async def close_connection(self) -> None:
    await self.close_session()            # closes local session first
    await self.write_message(CloseSession().model_dump_json())  # then notifies remote
```

The remote side should be notified **before** local teardown, so it can process the close message while the session is still logically open. As written, the remote side receives `CloseSession` after the local session state is already torn down.

---

#### D6. `write_message` failure in `rpc_call` silently leaves caller hanging
- [ ] **Fix recommended**
- **File:** `src/inmanta/protocol/websocket.py:284`

```python
self.add_background_task(self.write_message(RPC_Call(...).model_dump_json()))
```

The write is a fire-and-forget background task. If it fails (e.g., `WebSocketClosedError`), the caller's future is never resolved. The caller waits until timeout (up to 120s). Combined with D2, this makes error recovery very slow.

**Suggestion:** Either detect write failure and resolve the future immediately, or don't use a background task for the write.

---

#### D7. `stop()` and `_reconnect()` can interleave
- [ ] **Investigate**
- **File:** `src/inmanta/protocol/websocket.py:645-649, 607-639`

`stop()` cancels background tasks (including `_process_messages`) and then calls `close_connection()`. But `_process_messages` might be inside `_reconnect()` when cancelled. The `CancelledError` propagates out of `_reconnect`, but `close_connection()` then tries to write `CloseSession` on a half-initialized connection. The `write_message` guard protects against `None` `_ws_client`, but not against a connection in an indeterminate state.

---

#### D8. Dual disconnect handling — `_on_disconnect` callback races with `_process_messages`
- [ ] **Investigate**
- **File:** `src/inmanta/protocol/websocket.py:634-643, 676-697`

When the connection drops, two things happen simultaneously:
1. `_on_disconnect` callback fires (line 634-636), scheduling `on_disconnect()` as a background task
2. `_process_messages` gets `None` from `read_message()` (line 677), sleeps, and calls `_reconnect()`

No coordination exists between these paths. `on_disconnect()` may run while `_reconnect()` is in progress. `on_reconnect()` (called from `on_open_session`) could interleave with `on_disconnect()` from the callback. For `Agent`, `on_disconnect` calls `stop_working()` while `on_reconnect` calls `start_working()` — if they interleave, the scheduler state can be corrupted.

---

#### D9. `Agent.to_dict()` always reports status as "down"
- [ ] **Fix recommended**
- **File:** `src/inmanta/data/__init__.py:~3484`

```python
def to_dict(self) -> JsonType:
    base = BaseDocument.to_dict(self)
    base["state"] = self.get_status().value  # has_active_session defaults to False
```

`get_status()` is called without `has_active_session` argument, defaulting to `False`. Every call to `to_dict()` reports non-paused agents as "down". The v1 `list_agents` API uses `to_dict()` indirectly.

---

#### D10. `_ws_client.close()` not awaited — incomplete shutdown
- [ ] **Fix**
- **File:** `src/inmanta/protocol/websocket.py:723`

```python
if self._ws_client:
    self._ws_client.close()  # returns a future that is not awaited
```

Tornado's `close()` returns a future. Not awaiting it means the WebSocket close handshake may not complete, leaving server-side resources in an ambiguous state.

---

#### D11. `Agent.get_statuses` N+1 query problem
- [ ] **Consider fixing**
- **File:** `src/inmanta/data/__init__.py:~3453-3465`

Performs 1 query for live sessions + N queries for N agent names. Should use a single `WHERE name IN (...)` query.

---

#### D12. Wrong error message in `get_session` — says "Duplication" when session not found
- [ ] **Fix**
- **File:** `src/inmanta/protocol/rest/server.py:434-435`

```python
raise KeyError("Duplication session")  # TODO: correct exception
```

Error message says "Duplication" but condition is "not found". Exception type `KeyError` is inappropriate for API layer.

---

### MEDIUM

#### D13. `_expire_session` silently drops cleanup during shutdown
- [ ] **Acceptable risk — document**
- **File:** `src/inmanta/server/agentmanager.py:521-526`

If `is_stopping()` is true, queued expire actions are discarded. Sessions are cleaned from DB at next startup (`_expire_all_sessions_in_db`), but in-memory dictionaries can have stale entries during the shutdown window.

---

#### D14. `on_open_session` runs inline on server (blocks message loop) but as background on client
- [ ] **Document / Consider**
- **File:** `src/inmanta/protocol/websocket.py:316-318 vs 321-329`

On the server side, a slow `on_open_session` blocks all message processing on that connection. On the client side, it runs as a background task. This asymmetry is intentional but could cause issues if `on_open_session` performs RPCs or DB queries.

---

#### D15. `match_call` rebuilds URL mapping on every WebSocket RPC message
- [ ] **Performance improvement**
- **File:** `src/inmanta/protocol/rest/__init__.py:698-713`

`target.get_op_mapping()` rebuilds the mapping each call. Should be cached once at startup.

---

#### D16. `start_connected()` called before session is confirmed
- [ ] **Document**
- **File:** `src/inmanta/protocol/websocket.py:639`

`start_connected()` runs after `session.open()` sends `OpenSession` but before `SessionOpened` is received. Session is not yet `active`. RPC calls in `start_connected()` would fail.

---

#### D17. Diamond inheritance in `SessionEndpoint` — double `TaskHandler.__init__`
- [ ] **Investigate**
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
- [ ] **Fix**
- **File:** `src/inmanta/protocol/rest/server.py:304`

```python
self._sessions: dict[(uuid.UUID, str), websocket.Session] = {}
```

Should be `dict[tuple[uuid.UUID, str], websocket.Session]`.

---

#### D19. Mutable default argument in `RESTServer.start()`
- [ ] **Fix**
- **File:** `src/inmanta/protocol/rest/server.py:329`

```python
async def start(self, targets, additional_rules: list[routing.Rule] = []) -> None:
```

Classic Python anti-pattern. Should be `= None` with guard.

---

#### D20. Dead `on_pong_callback` — pong never tracked on client
- [ ] **Consider**
- **File:** `src/inmanta/protocol/websocket.py:623, 525-527`

`on_pong_callback=None` is always passed. The `WebSocketClientConnection` class has pong handling code (lines 525-527) that is never triggered. If client-side liveness tracking was intended, this needs to be wired up.

---

### LOW

#### D21. `_process_session_listener_actions` references potentially unbound variable
- **File:** `src/inmanta/server/agentmanager.py:438`

If `queue.get()` raises non-CancelledError, `session_action` is unbound in the `except` block → `UnboundLocalError` masks original exception.

---

#### D22. `get_agent_client` isinstance check contradicts type annotation
- **File:** `src/inmanta/server/agentmanager.py:564`

`tid: uuid.UUID` but code does `if isinstance(tid, str)`. Either fix callers or update annotation.

---

#### D23. Test bug: truthiness assertion instead of equality
- [ ] **Fix**
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

| Gap | Risk | Notes |
|-----|------|-------|
| WebSocket upgrade auth | **Critical** | No test for unauthenticated WS connection |
| Malformed WS messages | High | No test for invalid JSON, wrong action types, wrong field types |
| Agent crash with in-flight RPCs | High | Server-side future cleanup untested |
| Concurrent register + expire for same env | High | Only sequential paths tested |
| Server crash (SIGKILL) recovery | Medium | Only graceful shutdown tested |
| DB failure during session expiry logging | Medium | Only creation failure tested |
| Multiple environments interleaved | Medium | All multi-env tests are sequential |
| Large-scale concurrent RPCs (100+) | Medium | Only 10 tested |
| `on_disconnect` / `on_reconnect` interleaving | Medium | Related to D8 |
| `stop()` during `_reconnect()` | Medium | Related to D7 |

### MockSession fidelity issues
The `MockSession` in `test_agent_manager.py` does not implement: `active` property, `session_key`, `close_session()`, `is_closed()`, `confirm_open()`, `get_typed_client()`, `close_connection()`. Tests using this mock may pass even when production code has bugs in these code paths.

---

## Remaining TODO Comments

| File | Line | TODO | Status |
|------|------|------|--------|
| `websocket.py` | 292 | "log this" | Stale — already logging |
| `websocket.py` | 345 | Handle RPC_Call when not active | Open |
| `websocket.py` | 351 | Handle RPC_Reply when not active | Open |
| `rest/server.py` | 338 | Add constant for `/v2/ws` | Open |
| `rest/server.py` | 434 | Correct exception type | Open |

---

## Summary Priority Matrix

| Priority | Items |
|----------|-------|
| **Critical** | S1 (auth), D1 (wrong assert), D2 (futures not cleaned), D3 (serialization mismatch) |
| **High** | D4 (session leak on reconnect), D5 (close ordering), D6 (write failure hangs caller), D7 (stop/reconnect race), D8 (dual disconnect), D9 (to_dict always "down"), D10 (close not awaited), D11 (N+1 queries), D12 (wrong error message) |
| **Medium** | D13-D20, N1 (docstring), N4 (stale diagram), N5 (stale class docstring) |
| **Low** | D21-D24, N2 (busy-wait), N3 (heartbeat docstring), remaining TODOs |
