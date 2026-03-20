"""Config API routes — /config/* endpoints."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import get_config_manager, get_plugin_store_manager
from src.api.models.common import API_RESPONSES
from src.config_manager import ConfigManager
from src.logging_config import get_logger
from src.plugin_system.store_manager import PluginStoreManager

logger = get_logger("api.config")

router = APIRouter(prefix="/config", tags=["config"])

# ---- helpers ----------------------------------------------------------------

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _coerce_to_bool(value: Any) -> bool:
    """Convert form / JSON values to a proper bool."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "on", "1", "yes")
    return False


def _validate_time_format(time_str: str) -> tuple[bool, str | None]:
    """Return (True, None) if HH:MM is valid, else (False, message)."""
    if not _TIME_RE.match(time_str):
        return False, f"Invalid time format: '{time_str}'. Use HH:MM."
    h, m = map(int, time_str.split(":"))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return False, f"Invalid time value: '{time_str}'."
    return True, None


def _save_config_atomic(
    config_manager: ConfigManager,
    config_data: dict,
    *,
    create_backup: bool = True,
) -> tuple[bool, str | None]:
    """Try atomic save, fall back to plain save."""
    try:
        if hasattr(config_manager, "save_config_atomic"):
            result = config_manager.save_config_atomic(config_data, create_backup=create_backup)
            if hasattr(result, "status") and result.status.value == "success":
                return True, None
            return False, getattr(result, "message", "Atomic save failed")
        config_manager.save_config(config_data)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _error(error_code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"status": "error", "error_code": error_code, "message": message},
        status_code=status,
    )


def _success(data: Any = None, message: str | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"status": "success"}
    if data is not None:
        resp["data"] = data
    if message is not None:
        resp["message"] = message
    return resp


# ---- routes -----------------------------------------------------------------


@router.get("/main", response_model=None, responses=API_RESPONSES)
async def get_main_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Return full config."""
    try:
        config = config_manager.load_config()
        return _success(data=config)
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)


@router.post("/main", response_model=None, responses=API_RESPONSES)
async def save_main_config(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Accept a partial config update, merge, and save atomically."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    try:
        config = config_manager.load_config()
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)

    # Merge top-level keys from the request body into the existing config
    for key, value in body.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value

    ok, err = _save_config_atomic(config_manager, config)
    if not ok:
        return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
    return _success(message="Configuration saved successfully")


@router.get("/schedule", response_model=None, responses=API_RESPONSES)
async def get_schedule_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Return schedule section of config."""
    try:
        config = config_manager.load_config()
        return _success(data=config.get("schedule", {}))
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)


@router.post("/schedule", response_model=None, responses=API_RESPONSES)
async def save_schedule_config(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Validate and save schedule config (global or per-day)."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    enabled = _coerce_to_bool(body.get("enabled", False))
    mode = body.get("mode", "global")
    schedule: dict[str, Any] = {"enabled": enabled, "mode": mode}

    if mode == "global":
        start = body.get("start_time", "07:00")
        end = body.get("end_time", "23:00")
        for t in (start, end):
            ok, msg = _validate_time_format(t)
            if not ok:
                return _error("VALIDATION_ERROR", msg or "Invalid time")
        schedule["start_time"] = start
        schedule["end_time"] = end
    elif mode == "per-day":
        days: dict[str, Any] = {}
        any_day_enabled = False
        for day in _DAYS:
            day_enabled = _coerce_to_bool(body.get(f"{day}_enabled", False))
            if day_enabled:
                any_day_enabled = True
                d_start = body.get(f"{day}_start", "07:00")
                d_end = body.get(f"{day}_end", "23:00")
                for t in (d_start, d_end):
                    ok, msg = _validate_time_format(t)
                    if not ok:
                        return _error("VALIDATION_ERROR", msg or "Invalid time")
                days[day] = {"enabled": True, "start_time": d_start, "end_time": d_end}
            else:
                days[day] = {"enabled": False}
        if enabled and not any_day_enabled:
            return _error("VALIDATION_ERROR", "At least one day must be enabled in per-day mode")
        schedule["days"] = days
    else:
        return _error("VALIDATION_ERROR", f"Invalid schedule mode: '{mode}'")

    try:
        config = config_manager.load_config()
        config["schedule"] = schedule
        ok, err = _save_config_atomic(config_manager, config)
        if not ok:
            return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
        return _success(message="Schedule saved successfully")
    except Exception as exc:
        return _error("CONFIG_SAVE_FAILED", str(exc), 500)


@router.get("/dim-schedule", response_model=None, responses=API_RESPONSES)
async def get_dim_schedule_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Return dim-schedule section, with sensible defaults."""
    default = {
        "enabled": False,
        "dim_brightness": 30,
        "mode": "global",
        "start_time": "20:00",
        "end_time": "07:00",
        "days": {},
    }
    try:
        config = config_manager.load_config()
        return _success(data=config.get("dim_schedule", default))
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)


@router.post("/dim-schedule", response_model=None, responses=API_RESPONSES)
async def save_dim_schedule_config(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Validate and save dim-schedule config."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    enabled = _coerce_to_bool(body.get("enabled", False))
    mode = body.get("mode", "global")

    # Validate brightness
    try:
        brightness = int(body.get("dim_brightness", 30))
    except (TypeError, ValueError):
        return _error("VALIDATION_ERROR", "dim_brightness must be an integer")
    if not 0 <= brightness <= 100:
        return _error("VALIDATION_ERROR", "dim_brightness must be between 0 and 100")

    dim_schedule: dict[str, Any] = {
        "enabled": enabled,
        "dim_brightness": brightness,
        "mode": mode,
    }

    if mode == "global":
        start = body.get("start_time", "20:00")
        end = body.get("end_time", "07:00")
        for t in (start, end):
            ok, msg = _validate_time_format(t)
            if not ok:
                return _error("VALIDATION_ERROR", msg or "Invalid time")
        dim_schedule["start_time"] = start
        dim_schedule["end_time"] = end
    elif mode == "per-day":
        days: dict[str, Any] = {}
        any_day_enabled = False
        for day in _DAYS:
            day_enabled = _coerce_to_bool(body.get(f"{day}_enabled", False))
            if day_enabled:
                any_day_enabled = True
                d_start = body.get(f"{day}_start", "20:00")
                d_end = body.get(f"{day}_end", "07:00")
                for t in (d_start, d_end):
                    ok, msg = _validate_time_format(t)
                    if not ok:
                        return _error("VALIDATION_ERROR", msg or "Invalid time")
                days[day] = {"enabled": True, "start_time": d_start, "end_time": d_end}
            else:
                days[day] = {"enabled": False}
        if enabled and not any_day_enabled:
            return _error("VALIDATION_ERROR", "At least one day must be enabled in per-day mode")
        dim_schedule["days"] = days
    else:
        return _error("VALIDATION_ERROR", f"Invalid dim-schedule mode: '{mode}'")

    try:
        config = config_manager.load_config()
        config["dim_schedule"] = dim_schedule
        ok, err = _save_config_atomic(config_manager, config)
        if not ok:
            return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
        return _success(message="Dim schedule saved successfully")
    except Exception as exc:
        return _error("CONFIG_SAVE_FAILED", str(exc), 500)


@router.get("/secrets", response_model=None, responses=API_RESPONSES)
async def get_secrets_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Return secrets config."""
    try:
        data = config_manager.get_raw_file_content("secrets")
        return _success(data=data)
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)


@router.post("/raw/main", response_model=None, responses=API_RESPONSES)
async def save_raw_main_config(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    """Overwrite main config with raw JSON."""
    try:
        data = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    try:
        config_manager.save_raw_file_content("main", data)
        return _success(message="Main configuration saved successfully")
    except Exception as exc:
        return _error("CONFIG_SAVE_FAILED", str(exc), 500)


@router.post("/raw/secrets", response_model=None, responses=API_RESPONSES)
async def save_raw_secrets_config(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
    plugin_store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
) -> dict[str, Any] | JSONResponse:
    """Overwrite secrets config with raw JSON and reload GitHub token."""
    try:
        data = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    try:
        config_manager.save_raw_file_content("secrets", data)
        # Reload GitHub token in store manager
        if hasattr(plugin_store_manager, "_load_github_token"):
            plugin_store_manager.github_token = plugin_store_manager._load_github_token()
        return _success(message="Secrets configuration saved successfully")
    except Exception as exc:
        return _error("CONFIG_SAVE_FAILED", str(exc), 500)
