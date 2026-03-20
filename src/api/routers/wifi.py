"""WiFi API routes — /wifi/* endpoints."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.wifi_manager import WiFiManager

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.models.common import API_RESPONSES
from src.logging_config import get_logger

logger = get_logger("api.wifi")

router = APIRouter(prefix="/wifi", tags=["wifi"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WIFI_CONFIG_PATH = PROJECT_ROOT / "config" / "wifi_config.json"


# ---- helpers ----------------------------------------------------------------


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


def _get_wifi_manager() -> "WiFiManager":
    from src.wifi_manager import WiFiManager

    return WiFiManager()


def _read_wifi_config() -> dict[str, Any]:
    if WIFI_CONFIG_PATH.exists():
        try:
            data: dict[str, Any] = json.loads(WIFI_CONFIG_PATH.read_text())
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read wifi config: %s", exc)
    return {"auto_enable_ap_mode": False}


def _write_wifi_config(data: dict) -> None:
    """Write wifi_config.json atomically."""
    WIFI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WIFI_CONFIG_PATH.write_text(json.dumps(data, indent=2))


# ---- routes -----------------------------------------------------------------


@router.get("/status", response_model=None, responses=API_RESPONSES)
async def get_wifi_status() -> dict[str, Any] | JSONResponse:
    """Return current WiFi connection status."""
    try:
        manager = _get_wifi_manager()
        status = manager.get_wifi_status()
        return _success(data=asdict(status))
    except Exception as exc:
        logger.error("Failed to get WiFi status: %s", exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.get("/scan", response_model=None, responses=API_RESPONSES)
async def scan_networks() -> dict[str, Any] | JSONResponse:
    """Scan for available WiFi networks."""
    try:
        manager = _get_wifi_manager()
        networks = manager.scan_networks()
        return _success(data=[asdict(n) for n in networks])
    except Exception as exc:
        logger.error("Failed to scan networks: %s", exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.post("/connect", response_model=None, responses=API_RESPONSES)
async def connect_to_network(request: Request) -> dict[str, Any] | JSONResponse:
    """Connect to a WiFi network. Expects {ssid, password}."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    ssid = body.get("ssid")
    password = body.get("password", "")

    if not ssid:
        return _error("INVALID_INPUT", "Missing required field: ssid")

    try:
        manager = _get_wifi_manager()
        success, message = manager.connect_to_network(ssid, password)
        if success:
            return _success(message=message)
        return _error("WIFI_CONNECT_FAILED", message)
    except Exception as exc:
        logger.error("Failed to connect to network '%s': %s", ssid, exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.post("/disconnect", response_model=None, responses=API_RESPONSES)
async def disconnect_from_network() -> dict[str, Any] | JSONResponse:
    """Disconnect from the current WiFi network."""
    try:
        manager = _get_wifi_manager()
        success, message = manager.disconnect_from_network()
        if success:
            return _success(message=message)
        return _error("WIFI_DISCONNECT_FAILED", message)
    except Exception as exc:
        logger.error("Failed to disconnect: %s", exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.post("/ap/enable", response_model=None, responses=API_RESPONSES)
async def enable_ap_mode() -> dict[str, Any] | JSONResponse:
    """Enable access point mode."""
    try:
        manager = _get_wifi_manager()
        success, message = manager.enable_ap_mode()
        if success:
            return _success(message=message)
        return _error("AP_ENABLE_FAILED", message)
    except Exception as exc:
        logger.error("Failed to enable AP mode: %s", exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.post("/ap/disable", response_model=None, responses=API_RESPONSES)
async def disable_ap_mode() -> dict[str, Any] | JSONResponse:
    """Disable access point mode."""
    try:
        manager = _get_wifi_manager()
        success, message = manager.disable_ap_mode()
        if success:
            return _success(message=message)
        return _error("AP_DISABLE_FAILED", message)
    except Exception as exc:
        logger.error("Failed to disable AP mode: %s", exc)
        return _error("WIFI_ERROR", str(exc), 500)


@router.get("/ap/auto-enable", response_model=None, responses=API_RESPONSES)
async def get_ap_auto_enable() -> dict[str, Any] | JSONResponse:
    """Read auto_enable_ap_mode setting from wifi_config.json."""
    try:
        config = _read_wifi_config()
        return _success(
            data={
                "auto_enable_ap_mode": config.get("auto_enable_ap_mode", False),
            }
        )
    except Exception as exc:
        logger.error("Failed to read AP auto-enable config: %s", exc)
        return _error("CONFIG_ERROR", str(exc), 500)


@router.post("/ap/auto-enable", response_model=None, responses=API_RESPONSES)
async def set_ap_auto_enable(request: Request) -> dict[str, Any] | JSONResponse:
    """Update auto_enable_ap_mode setting in wifi_config.json."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    auto_enable = body.get("auto_enable_ap_mode")
    if auto_enable is None:
        return _error("INVALID_INPUT", "Missing required field: auto_enable_ap_mode")

    try:
        config = _read_wifi_config()
        config["auto_enable_ap_mode"] = bool(auto_enable)
        _write_wifi_config(config)
        return _success(message="AP auto-enable setting updated")
    except Exception as exc:
        logger.error("Failed to update AP auto-enable config: %s", exc)
        return _error("CONFIG_ERROR", str(exc), 500)
