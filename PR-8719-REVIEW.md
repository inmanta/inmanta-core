# PR #8719: WebSocket Refactor — Code Review

**PR:** https://github.com/inmanta/inmanta-core/pull/8719
**Branch:** `websocket-refactor` → `master`
**Author:** Bart Vanbrabant (+ Claude co-authored commits)
**Reviewed:** 2026-03-04
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

The PR description is excellent. The architectural direction is sound — WebSockets are the right choice here. The happy path works well. However, error handling, edge cases, and test coverage need more work before merge.

---

## Critical Issues

### C1. Reconnection loop crashes on connection failure
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py:659-676`

Only `CancelledError` is caught in `_process_messages`. If `_reconnect()` raises any other exception (connection refused, DNS failure, SSL error), the message loop dies silently and the agent becomes permanently disconnected with no recovery.

```python
# Current code — no error handling around reconnect
async def _process_messages(self) -> None:
    try:
        while True:
            if self._ws_client is not None and not self._ws_client.closed:
                msg = await self._ws_client.read_message()
                if msg is None:
                    await asyncio.sleep(self.reconnect_delay)
                    await self._reconnect()  # <-- unhandled exceptions kill the loop
            else:
                await self._reconnect()  # <-- same here
    except asyncio.CancelledError:
        pass
```

**Fix:** Wrap `_reconnect()` calls in `try/except Exception` with logging and retry after `reconnect_delay`.

---

### C2. Memory leak in timed-out RPC replies
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py:258-283`

When `handle_timeout` fires, it cancels the future but does **not** remove the entry from `self._replies`. Cleanup only happens when a reply arrives (line 358). Timed-out calls leave orphaned entries forever.

**Fix:** `handle_timeout` should receive `self._replies` and `reply_id`, and `del self._replies[reply_id]` after timeout.

---

### C3. `Agent.get_status()` always returns `up` for non-paused agents
- [ ] **Fix required**
- **File:** `src/inmanta/data/__init__.py:3466-3472`

```python
def get_status(self) -> AgentStatus:
    if self.paused:
        return AgentStatus.paused
    return AgentStatus.up
    # TODO: fix
    return AgentStatus.down  # UNREACHABLE
```

With `id_primary` removed, there's no way to determine if an agent is actually connected. The `AgentView` in `dataview.py:1264-1276` partially compensates with an environment-wide `SchedulerSession` check, but `get_status()` on the model itself is broken.

---

### C4. Server ping timeout not configured — stale sessions persist
- [x] **Fix required**
- **File:** `src/inmanta/protocol/rest/server.py:345`

`websocket_ping_interval=1` is set but `websocket_ping_timeout` is not. The **server** will never proactively close a dead client connection. If a client is killed without TCP FIN, the server session persists until OS TCP keepalive expires (~2 hours).

**Fix:** Add `websocket_ping_timeout=<N>` to the Tornado application settings.

---

### C5. `_db_monitor` AttributeError on early stop
- [x] **Fix required**
- **File:** `src/inmanta/agent/agent_new.py`

`self._db_monitor` is assigned in `start()` but checked in `stop()` (`if self._db_monitor:`). Calling `stop()` before `start()` raises `AttributeError`.

**Fix:** Initialize `self._db_monitor = None` in `__init__`.

---

### C6. Duplicate session handling not implemented on frame decoder
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py:303` — `# TODO: handle duplicate sessions`

The server-side `register_session` (`rest/server.py:407-419`) handles the race by evicting the old session, but the frame decoder has no protection against a client opening multiple sessions on the same connection.

---

### C7. `RejectSession` handling is a stub
- [x] **Fix required**
- **File:** `src/inmanta/protocol/websocket.py:325-329`

```python
case RejectSession():
    # TODO: implement
    pass
```

If the server rejects a session, the client silently ignores it. The session stays unconfirmed and reconnect logic won't trigger.

**Fix:** At minimum, log the rejection reason, close the session, and trigger reconnect.

---

## Security Concerns

### S1. WebSocket endpoint lacks authentication
- [ ] **Verify / Fix**
- **File:** `src/inmanta/protocol/websocket.py:562-566`

`SessionEndpoint.is_auth_enabled()` returns `False` unconditionally. There is no authentication step in the `OPEN_SESSION` flow. If `/v2/ws` is network-accessible, any client can open a session for any environment.

**Action:** Verify that either:
- HTTP upgrade requires authentication (not visible in this diff), or
- Network-level access control prevents unauthorized connections, or
- Add token-based auth to the `OPEN_SESSION` message.

---

### S2. Information disclosure in error responses
- [ ] **Fix recommended**
- **File:** `src/inmanta/protocol/rest/__init__.py:693`

```python
raise exceptions.ServerError(str(e.args))
```

Raw exception args returned to the client may leak internal paths, SQL queries, or stack details.

**Fix:** Use a generic error message; only log details server-side.

---

## Test Coverage Gaps

### T1. `set_state` notification assertions commented out
- [ ] **Fix required**
- **File:** `tests/test_agent_manager.py:355-365`

Multiple `# TODO!!!` comments where `client.set_state` assertions were removed. No test verifies agents receive state notifications on session open/close.

---

### T2. Only happy-path WebSocket test exists
- [ ] **Improve**
- **File:** `tests/protocol/test_ws.py`

Single test (`test_ws_2way`) with:
- Infinite busy-wait loop (line 72-73) — hangs forever on failure. Use `asyncio.wait_for`.
- No cleanup on failure — needs `try/finally` or fixtures.
- Missing coverage for: reconnection, rejection, auth, concurrent RPCs, network failures, closed-session calls.

---

### T3. `agent-timeout` config is now dead in tests
- [ ] **Fix**
- **Files:** `tests/protocol/test_2way_protocol.py:185, 243`

Tests set `agent-timeout` config, but the WebSocket transport ignores it. Timeout now relies on Tornado's `websocket_ping_interval` (hardcoded) and client `ping_timeout`. Tests pass by coincidence.

**Fix:** Remove the dead config setting. If the tests need to control timeout, make ping interval/timeout configurable.

---

### T4. No test for `on_reconnect` failure path
- [ ] **Add test**
- **File:** `src/inmanta/agent/agent_new.py:219-235`

If `get_state` returns non-200 on reconnect, the agent stays in `working=False` with no retry until the next disconnect/reconnect cycle.

---

### T5. No test for duplicate session replacement
- [ ] **Add test**
- **File:** `src/inmanta/protocol/rest/server.py:407-419`

When the same `(environment, name)` reconnects while the old session is still in `_sessions`, `register_session` evicts the old one. No test verifies the old session's listener callbacks fire correctly.

---

### T6. `SchedulerSession.clean_up_expired_for_env()` untested
- [ ] **Add test**
- **File:** `src/inmanta/server/agentmanager.py:512`

Called in `_log_session_creation_to_db` but only exercised indirectly through integration tests.

---

## Code Quality Issues

### Q1. Dead code: `Session._seen` field
- [ ] **Remove**
- **File:** `src/inmanta/protocol/websocket.py:49, 104, 252, 295, 340, 352`

`_seen` is set on every message via `time.monotonic()` but **never read** by any logic. The timer-based sweep is gone; liveness is connection-based.

---

### Q2. Dead code: `SessionActionType.SEEN_SESSION`
- [x] **Remove**
- **File:** `src/inmanta/server/agentmanager.py:105`

Defined in the enum but never used. The PR description says it was removed.

---

### Q3. Dead code: `Client._select_method`
- [x] **Remove**
- **File:** `src/inmanta/protocol/endpoints.py:98-111`

Duplicates `MethodProperties.select_method` and is never called.

---

### Q4. Stale heartbeat terminology
- [x] **Fix**

| File | Line | Text |
|------|------|------|
| `websocket.py` | 413 | `"heartbeat method call"` |
| `websocket.py` | 398 | docstring says `"heartbeat reply"` |
| `agentmanager.py` | 246 | `"agentprocess and agentinstance tables"` |
| `data/__init__.py` | 3435 | `:param primary:` references removed field |

---

### Q5. `AuthnzInterface` doesn't inherit `abc.ABC`
- [ ] **Fix**
- **File:** `src/inmanta/protocol/rest/__init__.py:634-648`

`@abc.abstractmethod` on `get_authorization_provider` has no effect without `abc.ABC` as base class.

---

### Q6. `TypeAdapter` created per-call (performance)
- [x] **Fix**
- **File:** `src/inmanta/protocol/common.py:1544`

`pydantic.TypeAdapter(method_properties.return_type)` constructed on every typed RPC response. Should be cached on `MethodProperties`.

---

### Q7. `Request.from_dict` mutates input dict
- [x] **Fix**
- **File:** `src/inmanta/protocol/common.py:162-163`

`del value["reply_id"]` modifies the caller's dict. Use `.pop()` or work on a copy.

---

### Q8. `SchedulerSession.cleanup()` uses O(n²) query
- [ ] **Improve**
- **File:** `src/inmanta/data/__init__.py:3390-3409`

Correlated subquery with `count(*)`. Use `ROW_NUMBER() OVER (PARTITION BY ...)` instead.

---

### Q9. `LOGGER.exception()` without active exception
- [x] **Fix**
- **File:** `src/inmanta/data/__init__.py:3344`

`LOGGER.exception("Multiple objects...")` used without an active exception context. Should be `LOGGER.error()`.

---

### Q10. Stale DTO field: `AgentProcess.last_seen`
- [ ] **Remove**
- **File:** `src/inmanta/data/model.py:733`

Column dropped in migration but field remains in DTO. Always `None`.

---

### Q11. `_SessionClient` sets private attribute on `Result`
- [ ] **Fix**
- **File:** `src/inmanta/protocol/websocket.py:150`

`r._method_properties = method` — sets a private attribute from outside. `Result` should accept this via constructor or setter.

---

### Q12. Incomplete log message
- [x] **Fix**
- **File:** `src/inmanta/protocol/websocket.py:275`

```python
log_message=f"Call {call_spec.reply_id}: {call_spec.method} {call_spec.url} for timed out.",  # TODO
```

Sentence fragment: "for timed out."

---

## Migration Concerns

### M1. Stale migration docstring
- [ ] **Fix**
- **File:** `src/inmanta/db/versions/v202502031.py:24`

Says "Rename some rps columns and values" — copy-pasted from another migration.

---

### M2. Old index names persist after table rename
- [ ] **Consider fixing**
- **File:** `src/inmanta/db/versions/v202502031.py`

After `ALTER TABLE agentprocess RENAME TO schedulersession`, indexes keep their `agentprocess_*` names. The SQLAlchemy model declares `schedulersession_*` names. These diverge on upgraded databases.

---

### M3. Implicit FK constraint drop
- [ ] **Consider explicit DROP CONSTRAINT**
- **File:** `src/inmanta/db/versions/v202502031.py:27-34`

`DROP COLUMN id_primary` implicitly drops the FK to `agentinstance`. An explicit `DROP CONSTRAINT agent_id_primary_fkey` before the column drop would be clearer.

---

## Remaining TODO Comments in Code

These TODOs indicate known incomplete work. Track or resolve before merge:

| File | Line | TODO |
|------|------|------|
| `websocket.py` | 275 | Incomplete log message |
| `websocket.py` | 303 | Handle duplicate sessions |
| `websocket.py` | 328-329 | Implement RejectSession |
| `websocket.py` | 343 | Handle RPC_Call when session not active |
| `websocket.py` | 349 | Handle RPC_Reply when session not active |
| `websocket.py` | 423 | Verify error key format |
| `rest/server.py` | 338 | Add constant for `/v2/ws` URL |
| `rest/server.py` | 434-435 | Correct exception type for missing session |
| `data/__init__.py` | 3391 | Bare TODO on cleanup() |
| `data/__init__.py` | 3469 | Fix get_status() |
| `test_agent_manager.py` | 355-365 | Restore set_state assertions |

---

## Summary Priority Matrix

| Priority | Count | Items |
|----------|-------|-------|
| **Must fix** | 9 | C1, C2, C3, C4, C5, C6, C7, S1, T1 |
| **Should fix** | 8 | S2, T2, T3, T4, T5, Q1, Q2, Q4 |
| **Nice to have** | 10 | T6, Q3, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12 |
| **Migration** | 3 | M1, M2, M3 |
