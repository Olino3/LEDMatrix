"""System API routes — /system/*, /health, /logs, /errors/* endpoints."""

from __future__ import annotations

import asyncio
import platform
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import get_config_manager, get_plugin_manager
from src.config_manager import ConfigManager
from src.logging_config import get_logger
from src.plugin_system.plugin_manager import PluginManager

logger = get_logger("api.system")

router = APIRouter(tags=["system"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Track web-interface start time for health endpoint
_start_time = time.time()


# ---- helpers ----------------------------------------------------------------


def _error(error_code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"status": "error", "error_code": error_code, "message": message},
        status_code=status,
    )


def _success(data: Any = None, message: str | None = None):
    resp: dict[str, Any] = {"status": "success"}
    if data is not None:
        resp["data"] = data
    if message is not None:
        resp["message"] = message
    return resp


async def _run_cmd(
    *args: str,
    timeout: float = 5.0,
) -> tuple[int, str, str]:
    """Run a subprocess asynchronously and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
    except asyncio.TimeoutError:
        return -1, "", "Command timed out"
    except Exception as exc:
        return -1, "", str(exc)


async def _get_display_service_status() -> dict[str, Any]:
    """Check the ledmatrix systemd service status."""
    rc, stdout, stderr = await _run_cmd("systemctl", "is-active", "ledmatrix", timeout=3.0)
    return {
        "active": rc == 0 and stdout == "active",
        "returncode": rc,
        "stdout": stdout,
        "stderr": stderr,
    }


def _get_git_version() -> str:
    """Get version from git tags, falling back to short hash."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "Unknown"


# ---- system routes ----------------------------------------------------------


@router.get("/system/status")
async def get_system_status():
    """Return system metrics (CPU, memory, disk, temp)."""
    try:
        import psutil
    except ImportError:
        return _error("SYSTEM_ERROR", "psutil not available", 503)

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_seconds = time.time() - psutil.boot_time()

        # CPU temperature (Raspberry Pi)
        cpu_temp: float | None = None
        thermal = Path("/sys/class/thermal/thermal_zone0/temp")
        if thermal.exists():
            try:
                cpu_temp = int(thermal.read_text().strip()) / 1000.0
            except Exception:
                pass

        service = await _get_display_service_status()

        data = {
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "service_active": service["active"],
            "cpu_percent": cpu_percent,
            "memory_used_percent": mem.percent,
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "memory_used_mb": round(mem.used / (1024 * 1024), 1),
            "cpu_temp": cpu_temp,
            "disk_used_percent": disk.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
        }
        return _success(data=data)
    except Exception as exc:
        return _error("SYSTEM_ERROR", str(exc), 500)


@router.get("/system/version")
async def get_system_version():
    """Return version info."""
    return _success(
        data={
            "version": _get_git_version(),
            "python_version": sys.version,
            "platform": platform.platform(),
        }
    )


@router.post("/system/action")
async def execute_system_action(request: Request):
    """Execute a system action (start/stop/restart service, reboot, git pull)."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    action = body.get("action")
    if not action:
        return _error("INVALID_INPUT", "Missing 'action' field")

    # All commands use asyncio.create_subprocess_exec with explicit arg lists
    # (no shell interpretation) to prevent command injection.
    action_map: dict[str, list[str]] = {
        "start_display": ["sudo", "systemctl", "start", "ledmatrix"],
        "stop_display": ["sudo", "systemctl", "stop", "ledmatrix"],
        "restart_display_service": ["sudo", "systemctl", "restart", "ledmatrix"],
        "restart_web_service": ["sudo", "systemctl", "restart", "ledmatrix-web"],
        "enable_autostart": ["sudo", "systemctl", "enable", "ledmatrix"],
        "disable_autostart": ["sudo", "systemctl", "disable", "ledmatrix"],
        "reboot_system": ["sudo", "reboot"],
        "shutdown_system": ["sudo", "poweroff"],
    }

    if action == "git_pull":
        return await _handle_git_pull()

    cmd = action_map.get(action)
    if cmd is None:
        return _error("INVALID_INPUT", f"Unknown action: '{action}'")

    rc, stdout, stderr = await _run_cmd(*cmd, timeout=30.0)
    if rc != 0:
        return _error("SYSTEM_ERROR", f"Action '{action}' failed: {stderr}", 500)
    return _success(
        message=f"Action {action} completed",
        data={
            "returncode": rc,
            "stdout": stdout,
            "stderr": stderr,
        },
    )


async def _handle_git_pull():
    """Run git pull with auto-stash for local changes."""
    # Check for local changes
    rc, stdout, _ = await _run_cmd(
        "git",
        "status",
        "--porcelain",
        "--untracked-files=no",
        timeout=30.0,
    )
    has_changes = bool(stdout.strip()) if rc == 0 else False
    stashed = False

    if has_changes:
        rc, _, stderr = await _run_cmd(
            "git",
            "stash",
            "push",
            "-m",
            "LEDMatrix auto-stash before update",
            "--",
            ":!plugins",
            timeout=30.0,
        )
        if rc != 0:
            return _error("SYSTEM_ERROR", f"Failed to stash changes: {stderr}", 500)
        stashed = True

    rc, stdout, stderr = await _run_cmd("git", "pull", "--rebase", timeout=60.0)
    if rc != 0:
        msg = f"git pull failed: {stderr}"
        if stashed:
            msg += " (local changes were stashed)"
        return _error("SYSTEM_ERROR", msg, 500)

    message = "Code updated successfully"
    if stashed:
        message += " (local changes were stashed and can be restored with 'git stash pop')"
    return _success(message=message, data={"stdout": stdout})


# ---- health -----------------------------------------------------------------


@router.get("/health")
async def get_health(
    config_manager: ConfigManager = Depends(get_config_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    """Comprehensive health check."""
    checks: dict[str, Any] = {}
    all_healthy = True

    # Web interface uptime
    checks["web_interface"] = {
        "status": "running",
        "uptime_seconds": round(time.time() - _start_time, 1),
    }

    # Display service
    service = await _get_display_service_status()
    checks["display_service"] = {
        "status": "active" if service["active"] else "inactive",
        "details": service,
    }

    # Config file
    try:
        config_manager.load_config()
        checks["config_file"] = {"status": "accessible", "readable": True}
    except Exception as exc:
        checks["config_file"] = {"status": "error", "readable": False, "error": str(exc)}
        all_healthy = False

    # Plugin system
    try:
        if hasattr(plugin_manager, "get_available_plugins"):
            plugins = plugin_manager.get_available_plugins()
            checks["plugin_system"] = {"status": "operational", "plugin_count": len(plugins)}
        else:
            checks["plugin_system"] = {"status": "operational"}
    except Exception as exc:
        checks["plugin_system"] = {"status": "error", "error": str(exc)}
        all_healthy = False

    # Hardware snapshot freshness
    snapshot = Path("/tmp/led_matrix_preview.png")
    if snapshot.exists():
        age = time.time() - snapshot.stat().st_mtime
        checks["hardware"] = {
            "status": "connected" if age < 60 else "stale",
            "snapshot_age_seconds": round(age, 1),
        }
    else:
        checks["hardware"] = {"status": "unknown"}

    status = "healthy" if all_healthy else "degraded"
    return _success(data={"status": status, "timestamp": time.time(), "checks": checks})


# ---- logs -------------------------------------------------------------------


@router.get("/logs")
async def get_logs():
    """Fetch recent ledmatrix service logs via journalctl."""
    rc, stdout, stderr = await _run_cmd(
        "sudo",
        "journalctl",
        "-u",
        "ledmatrix.service",
        "-n",
        "100",
        "--no-pager",
        timeout=5.0,
    )
    if rc == -1 and "timed out" in stderr.lower():
        return _error("SYSTEM_ERROR", "Timeout while fetching logs", 504)
    if rc != 0:
        return _error("SYSTEM_ERROR", f"Failed to get logs: {stderr}", 500)
    return _success(data={"logs": stdout})


# ---- errors -----------------------------------------------------------------


def _get_aggregator():
    """Lazy import to avoid circular deps."""
    from src.error_aggregator import get_error_aggregator

    return get_error_aggregator()


@router.get("/errors/summary")
async def get_error_summary():
    """Return error aggregator summary."""
    try:
        aggregator = _get_aggregator()
        return _success(data=aggregator.get_error_summary())
    except Exception as exc:
        return _error("SYSTEM_ERROR", str(exc), 500)


@router.get("/errors/plugin/{plugin_id}")
async def get_plugin_errors(plugin_id: str):
    """Return error health for a specific plugin."""
    try:
        aggregator = _get_aggregator()
        return _success(data=aggregator.get_plugin_health(plugin_id))
    except Exception as exc:
        return _error("SYSTEM_ERROR", str(exc), 500)


@router.post("/errors/clear")
async def clear_errors(request: Request):
    """Clear error records older than max_age_hours."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        max_age = int(body.get("max_age_hours", 24))
    except (TypeError, ValueError):
        return _error("INVALID_INPUT", "max_age_hours must be an integer")

    if max_age < 1:
        return _error("INVALID_INPUT", "max_age_hours must be at least 1")
    if max_age > 8760:
        return _error("INVALID_INPUT", "max_age_hours must not exceed 8760 (1 year)")

    try:
        aggregator = _get_aggregator()
        cleared = aggregator.clear_old_records(max_age_hours=max_age)
        return _success(
            data={"cleared_count": cleared},
            message=f"Cleared {cleared} error records older than {max_age} hours",
        )
    except Exception as exc:
        return _error("SYSTEM_ERROR", str(exc), 500)
