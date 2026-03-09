# Review Round 3 — websocket-refactor

Reviewer: Claude (on behalf of Bart)
Date: 2026-03-06
Focus: race conditions, edge cases, protocol correctness


## R1. Fire-and-forget RPCs generate spurious "unknown reply" warnings (Bug)

**File**: `src/inmanta/protocol/websocket.py:348`

`rpc_call` always sets `call_spec.reply_id = uuid.uuid4()`, even for methods with
`reply=False` (`get_parameter`, `notify_timer_update`, `remove_executor_venvs`). The server
sees a non-None `reply_id` and sends back an `RPC_Reply`. The client never registered a
future (because `properties.reply` is False), so the reply triggers:

```
WARNING: Received a reply that is unknown: <uuid>
```

**Fix**: `call_spec.reply_id = uuid.uuid4() if properties.reply else None`.
The server-side `dispatch_method` already checks `method_call.reply_id is not None` before
sending a reply, so this is the only change needed.

**Status**: [x] DONE


## R2. Agent holds stale session references across reconnects (Fragile design)

**File**: `src/inmanta/agent/agent_new.py:78-80`

```python
self.scheduler = scheduler.ResourceScheduler(
    self._env_id, self.executor_manager, self.session.get_client()
)
self._client = self.session.get_client()
```

These capture a `_SessionClient` bound to the session created in `__init__`. After
reconnection, `_reconnect()` calls `create_session()` which creates a new `Session`, but
`self._client` and the scheduler's internal client still hold the old session.

This works by accident: `_SessionClient.__getattr__` routes through
`self._session.websocket_protocol.rpc_call(...)` where `websocket_protocol` is always
`self` (the `SessionEndpoint`), so it uses the current `_ws_client`. But if anyone ever
adds a session-active check to `rpc_call()`, or if `Session` gets its own transport state,
these stale references silently break.

**Fix (Option A)**: Changed `_SessionClient` to hold a `WebsocketFrameDecoder` reference
instead of a `Session` reference. `Session.get_client()` now passes `self.websocket_protocol`
directly. The decoder IS the `SessionEndpoint` on the client side, so it is always current
regardless of session replacement.

**Status**: [x] DONE


## R3. `register_session` doesn't close the old websocket connection (Edge case)

**File**: `src/inmanta/protocol/rest/server.py:416-432`

When the same agent reconnects, `register_session` evicts the old session:

```python
old_session.close_session()   # marks closed locally
del self._sessions[session.session_key]
```

But it never closes the old websocket connection. The old `WebsocketHandler` keeps its TCP
connection open until the ping timeout detects it as dead. During this window:

- The old handler keeps receiving pings and responding with pongs
- If the old client somehow sends more messages, they arrive on the old handler (whose
  session is closed, so they are dropped)
- The old handler consumes server resources unnecessarily

**Suggestion**: Call `await old_session.close_connection()` instead of just
`old_session.close_session()`. This sends a `CloseSession` on the old connection and closes
the websocket. The identity check in `notify_close_session` prevents double-removal of the
new session.

**Status**: [ ] TODO


## R4. `_register_session` in AgentManager has no shutdown guard (Minor)

**File**: `src/inmanta/server/agentmanager.py:485-502`

Unlike `_expire_session` (which checks `not self.is_running() or self.is_stopping()`),
`_register_session` has no shutdown guard. If a session-opened event is queued just before
shutdown and processed during the shutdown sequence, the session gets registered in memory
but will never be cleaned up (since `_expire_session` returns early during shutdown and the
process is going down).

Not catastrophic (the process is exiting anyway), but inconsistent with `_expire_session`.

**Suggestion**: Add the same early-return guard:

```python
async def _register_session(self, session, now):
    if not self.is_running() or self.is_stopping():
        return
    ...
```

**Status**: [ ] TODO


## R5. `on_reconnect` failure leaves agent in half-connected state (Edge case)

**File**: `src/inmanta/protocol/websocket.py:426`

On the client side, `SessionOpened` runs `on_open_session` as a background task:

```python
self.add_background_task(self.on_open_session(self._session))
```

In `Agent.on_reconnect()`, this calls `get_state()` and then `start_working()`. If
`get_state()` fails (server error, timeout), the exception is caught by `TaskHandler` and
logged, but:

- The session remains active (confirmed)
- The scheduler never starts (`start_working()` never called)
- The server thinks the agent is connected and may send RPCs
- The agent processes RPCs (session is active) but the scheduler isn't running

There is no retry mechanism. The agent sits in this half-state until the next
disconnect/reconnect cycle.

**Suggestion**: Wrap `on_reconnect` in a try/except that closes the connection on failure,
forcing a reconnect cycle. Or add a retry loop within `on_reconnect`.

**Status**: [ ] TODO


## R6. `_on_disconnect` can fire from failed connection attempts (Minor race)

**File**: `src/inmanta/protocol/websocket.py:770-775`

When `_reconnect()` fails at `conn.connect_future`, the `_reconnecting` flag is reset to
`False` in the `finally` block. If the failed `WebSocketClientConnection` later fires
`on_connection_close`, `_on_disconnect` is called with `_reconnecting = False`, triggering
`on_disconnect()` -> `stop_working()`. This is usually harmless (already stopped), but it
means a connection attempt that never succeeded fires a disconnect event, which is
semantically wrong.

**Suggestion**: Track connection identity so `_on_disconnect` only fires for the current
connection:

```python
def _on_disconnect(self) -> None:
    # Current code:
    if self.is_running() and not self._reconnecting:
        self.add_background_task(self.on_disconnect())

    # Suggested: also check that the callback is from the current connection
```

One way: pass `conn` as a bound argument to the callback and compare against
`self._ws_client`.

**Status**: [ ] TODO


## R7. `rpc_call` parameter type mismatch (Typing)

**File**: `src/inmanta/protocol/websocket.py:344-345`

```python
def rpc_call(
    self, properties: common.MethodProperties, args: list[object], ...
) -> ...:
```

`_SessionClient.wrap` passes `args=args` where `args` is a `tuple` (from `*args`). Should
be `Sequence[object]` to match `build_call`'s signature and the actual usage.

**Status**: [ ] TODO


## R8. `close_session` _replies iteration safety (Observation)

**File**: `src/inmanta/protocol/websocket.py:475-478`

```python
for reply_id, future in self._replies.items():
    if not future.done():
        future.set_result(...)
self._replies.clear()
```

This is safe because we are in a single asyncio task and no `await` occurs between the
iteration and the `clear()`. A `handle_timeout` coroutine cannot interleave. The
`if not future.done()` guard prevents double-set if timeout fires after `close_session`.

No action needed, but a brief comment explaining the safety invariant would help future
readers.

**Status**: [ ] TODO


## R9. Websocket transport has no authentication (Security)

**File**: `src/inmanta/protocol/websocket.py`

The REST client (`rest/client.py:107-108`) injects `Authorization: Bearer <token>` into
every HTTP request, but the websocket path through `_SessionClient` → `rpc_call()` →
`build_call()` never added auth headers. Additionally, the `OpenSession` handshake accepted
any `environment_id` claim without verification.

**Fix**: Added authentication at two layers, fully optional:

1. **OpenSession handshake** — Added `token` field to `OpenSession`. Server validates via
   `decode_token()` when `is_auth_enabled()` returns True. Rejects with `RejectSession` if
   token is missing or invalid.
2. **Per-RPC calls** — `WebsocketFrameDecoder.rpc_call()` injects `Authorization: Bearer`
   header when `_token` is set. `SessionEndpoint` reads token from config
   (`{name}_rest_transport.token`), same pattern as `RESTClient`.
3. **No-auth mode** — When `server.auth = false`, all validation is skipped. `_token` is
   `None` on both sides, no headers added, no checks performed.
4. **SSL CA cert** — `_reconnect()` now passes `ca_certs` to `HTTPRequest`, matching
   `RESTClient` behavior.

Server-side `WebsocketHandler` inherits `_token = None` from `WebsocketFrameDecoder`, so
server→agent calls never inject tokens (agent endpoints use `enforce_auth=False`).

**Tests**: 4 new tests in `test_ws.py`:
- `test_ws_rpc_with_auth` — end-to-end with valid token
- `test_ws_open_session_rejected_without_token` — no token → rejected
- `test_ws_open_session_rejected_with_invalid_token` — bad JWT → rejected
- `test_ws_rpc_fails_without_token_in_headers` — RPC rejected when auth enabled mid-session

**Status**: [x] DONE


## Summary

| #  | Severity    | Description                                                          | Status |
|----|-------------|----------------------------------------------------------------------|--------|
| R1 | Bug         | Fire-and-forget RPCs set `reply_id`, causing spurious warnings       | DONE   |
| R2 | Fragile     | Agent `_client` and scheduler hold stale session references          | DONE   |
| R3 | Edge case   | Old websocket connection not closed on session eviction              | TODO   |
| R4 | Minor       | No shutdown guard in `_register_session`                             | TODO   |
| R5 | Edge case   | `on_reconnect` failure leaves agent half-connected                   | TODO   |
| R6 | Minor race  | Stale connection close callback fires `on_disconnect` spuriously     | TODO   |
| R7 | Typing      | `rpc_call` `args` declared as `list` but receives `tuple`            | TODO   |
| R8 | Observation | `close_session` `_replies` iteration relies on single-thread asyncio | TODO   |
| R9 | Security    | Websocket transport has no authentication                            | DONE   |
