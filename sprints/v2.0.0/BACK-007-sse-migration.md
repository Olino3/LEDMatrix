# BACK-007 — Migrate SSE Streaming Endpoints

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-005](BACK-005-api-routes-system.md)
**Blocks:** [BACK-008](BACK-008-flask-removal-cleanup.md)

---

## Context

The Flask app has three SSE (Server-Sent Events) streaming endpoints in `app.py`:

1. `/api/v3/stream/stats` -- system status updates every 10 seconds (CPU, memory, temp, service status)
2. `/api/v3/stream/display` -- display preview updates at 2 Hz (base64-encoded PNG snapshots)
3. `/api/v3/stream/logs` -- journal log updates every 5 seconds

These use Flask's `Response(generate(), mimetype='text/event-stream')` pattern with blocking generators and `time.sleep()`. The FastAPI migration replaces these with `sse-starlette`'s `EventSourceResponse` using async generators and `asyncio.sleep()`, which is more efficient and does not block the event loop.

---

## Acceptance Criteria

- [ ] `src/api/routers/streams.py` contains all three SSE endpoints
- [ ] All generators are `async def` using `asyncio.sleep()` instead of `time.sleep()`
- [ ] System status generator uses `asyncio.to_thread()` for blocking `psutil` and `subprocess` calls
- [ ] Display preview generator uses `asyncio.to_thread()` for PIL image operations
- [ ] Logs generator uses `asyncio.create_subprocess_exec()` instead of `subprocess.run()`
- [ ] Endpoints return `EventSourceResponse` from `sse-starlette`
- [ ] Client disconnection is handled gracefully (no broken pipe errors)

---

## Implementation Checklist

### 1. Create `src/api/routers/streams.py`

- [ ] Create router with `APIRouter(prefix="/stream", tags=["streams"])`

### 2. Migrate system status stream

- [ ] Convert `system_status_generator()` to `async def`
- [ ] Wrap `psutil.cpu_percent()`, `psutil.virtual_memory()` in `asyncio.to_thread()`
- [ ] Wrap systemctl call in `asyncio.create_subprocess_exec()`
- [ ] Use `asyncio.sleep(10)` instead of `time.sleep(10)`
- [ ] Return `EventSourceResponse(generator())`

### 3. Migrate display preview stream

- [ ] Convert `display_preview_generator()` to `async def`
- [ ] Use `asyncio.to_thread()` for PIL `Image.open()` and `img.save()`
- [ ] Use `aiofiles` or `asyncio.to_thread()` for file stat checks (`os.path.getmtime`)
- [ ] Use `asyncio.sleep(0.5)` instead of `time.sleep(0.5)`

### 4. Migrate logs stream

- [ ] Convert `logs_generator()` to `async def`
- [ ] Use `asyncio.create_subprocess_exec('journalctl', ...)` with `stdout=asyncio.subprocess.PIPE`
- [ ] Use `asyncio.sleep(5)` instead of `time.sleep(5)`

### 5. Handle client disconnection

- [ ] Wrap each generator in a try/except for `asyncio.CancelledError`
- [ ] Log disconnection at debug level (not error)
- [ ] Clean up any resources on disconnect

### 6. Wire into the app

- [ ] Include streams router in `src/api/main.py` under `/api/v3` prefix
- [ ] Apply rate limiting (20/minute) to SSE endpoints

### 7. Tests

- [ ] Test SSE endpoint returns `text/event-stream` content type
- [ ] Test generator yields valid JSON data
- [ ] Test client disconnect does not raise errors

### 8. Commit

```bash
git add src/api/routers/streams.py
git commit -m "feat(api): migrate SSE streaming endpoints to FastAPI with async generators"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Streams router exists
test -f src/api/routers/streams.py && echo "OK: streams router"

# 2. Router is importable
python3 -c "
from src.api.routers.streams import router
print(f'Stream routes: {len(router.routes)}')
print('OK: streams router importable')
"

# 3. Uses sse-starlette (not raw Response)
grep -q "EventSourceResponse" src/api/routers/streams.py && echo "OK: uses EventSourceResponse"

# 4. Uses async generators
grep -q "async def" src/api/routers/streams.py && echo "OK: async handlers"
grep -q "asyncio.sleep" src/api/routers/streams.py && echo "OK: async sleep"

# 5. No blocking sleep calls
! grep -q "time.sleep" src/api/routers/streams.py && echo "OK: no blocking sleep"

# 6. Run tests
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_api_streams.py -v --override-ini="addopts="'
```

---

## Notes

- `sse-starlette` handles the SSE protocol formatting (`data:`, `event:`, `id:` fields) -- do not manually format SSE strings.
- The display preview stream at 2 Hz (500ms interval) is the most latency-sensitive. Test that async I/O does not introduce noticeable lag.
- The logs stream calls `journalctl` which is a Pi-specific tool. Handle `FileNotFoundError` gracefully for non-Pi environments.
- Consider adding a `keepalive` comment event (`:keepalive`) every 30 seconds to prevent proxy timeouts.
- The Flask SSE endpoints used `if limiter: limiter.limit("20 per minute")` -- replicate this with `slowapi` in the FastAPI version.
