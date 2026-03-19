"""SSE streaming endpoints migrated from Flask to FastAPI.

Three streams:
- /stream/stats  — system metrics every 10 s
- /stream/display — display preview snapshots at ~2 Hz
- /stream/logs   — journalctl log tail every 5 s
"""

import asyncio
import base64
import io
import json
import os
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

router = APIRouter(prefix="/stream", tags=["streams"])

SNAPSHOT_PATH = "/tmp/led_matrix_preview.png"


# ---------------------------------------------------------------------------
# Helpers — one event per call (testable without streaming)
# ---------------------------------------------------------------------------


async def _generate_stats_event() -> dict:
    """Produce a single system-status dict."""
    cpu_percent = 0.0
    memory_used_percent = 0.0
    cpu_temp = 0.0
    disk_used_percent = 0.0

    if psutil is not None:
        try:
            cpu_percent = round(await asyncio.to_thread(psutil.cpu_percent, interval=1), 1)
            mem = await asyncio.to_thread(psutil.virtual_memory)
            memory_used_percent = round(mem.percent, 1)
            disk = await asyncio.to_thread(psutil.disk_usage, "/")
            disk_used_percent = round(disk.percent, 1)
        except Exception:
            pass

        # CPU temperature — Raspberry Pi specific
        try:
            temps = await asyncio.to_thread(psutil.sensors_temperatures)
            if temps:
                for entries in temps.values():
                    if entries:
                        cpu_temp = round(entries[0].current, 1)
                        break
        except Exception:
            pass

    # Service status via systemctl
    service_active = False
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl",
            "is-active",
            "ledmatrix",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
        service_active = stdout.decode().strip() == "active"
    except Exception:
        pass

    return {
        "timestamp": time.time(),
        "uptime": "Running",
        "service_active": service_active,
        "cpu_percent": cpu_percent,
        "memory_used_percent": memory_used_percent,
        "cpu_temp": cpu_temp,
        "disk_used_percent": disk_used_percent,
    }


async def _generate_display_event(
    config_manager=None,
    _last_modified: list | None = None,
) -> dict:
    """Produce a single display-preview dict."""
    # Resolve display dimensions from config
    width, height = 128, 64
    if config_manager is not None:
        try:
            cfg = config_manager.load_config()
            hw = cfg.get("display", {}).get("hardware", {})
            width = hw.get("cols", 64) * hw.get("chain_length", 2)
            height = hw.get("rows", 32) * hw.get("parallel", 1)
        except Exception:
            pass

    image_b64: str | None = None

    try:
        if await asyncio.to_thread(os.path.exists, SNAPSHOT_PATH):
            current_mtime = await asyncio.to_thread(os.path.getmtime, SNAPSHOT_PATH)
            last = (_last_modified or [None])[0] if _last_modified else None
            if last is None or current_mtime > last:
                from PIL import Image

                def _read_snapshot() -> str:
                    with Image.open(SNAPSHOT_PATH) as img:
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        return base64.b64encode(buf.getvalue()).decode("utf-8")

                image_b64 = await asyncio.to_thread(_read_snapshot)
                if _last_modified is not None:
                    _last_modified[0] = current_mtime
    except Exception:
        pass

    return {
        "timestamp": time.time(),
        "width": width,
        "height": height,
        "image": image_b64,
    }


async def _generate_logs_event() -> dict:
    """Produce a single logs dict from journalctl."""
    logs_text = "No logs available from ledmatrix service"
    try:
        proc = await asyncio.create_subprocess_exec(
            "journalctl",
            "-u",
            "ledmatrix.service",
            "-n",
            "50",
            "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode == 0:
            text = stdout.decode().strip()
            if text:
                logs_text = text
        else:
            logs_text = f"journalctl failed with return code {proc.returncode}: {stderr.decode().strip()}"
    except FileNotFoundError:
        logs_text = "journalctl not available on this platform"
    except asyncio.TimeoutError:
        logs_text = "journalctl timed out"
    except Exception as exc:
        logs_text = f"Error running journalctl: {exc}"

    return {
        "timestamp": time.time(),
        "logs": logs_text,
    }


# ---------------------------------------------------------------------------
# Async generators — infinite loops that yield SSE events
# ---------------------------------------------------------------------------


async def _stats_stream() -> AsyncGenerator[str, None]:
    """Infinite async generator for system stats."""
    try:
        while True:
            event = await _generate_stats_event()
            yield json.dumps(event)
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        return


async def _display_stream(config_manager=None) -> AsyncGenerator[str, None]:
    """Infinite async generator for display preview."""
    last_modified: list[float | None] = [None]
    try:
        while True:
            event = await _generate_display_event(
                config_manager=config_manager,
                _last_modified=last_modified,
            )
            yield json.dumps(event)
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        return


async def _logs_stream() -> AsyncGenerator[str, None]:
    """Infinite async generator for journal logs."""
    try:
        while True:
            event = await _generate_logs_event()
            yield json.dumps(event)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        return


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/stats")
async def stream_stats():
    """SSE stream of system status metrics (every 10 s)."""
    return EventSourceResponse(_stats_stream())


@router.get("/display")
async def stream_display(request: Request):
    """SSE stream of display preview snapshots (~2 Hz)."""
    config_mgr = getattr(request.app.state, "config_manager", None)
    return EventSourceResponse(_display_stream(config_manager=config_mgr))


@router.get("/logs")
async def stream_logs():
    """SSE stream of journalctl log entries (every 5 s)."""
    return EventSourceResponse(_logs_stream())
