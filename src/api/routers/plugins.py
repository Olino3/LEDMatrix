"""Plugin API routes — /plugins/* endpoints for CRUD, health, metrics, state, and auth."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_config_manager,
    get_operation_history,
    get_operation_queue,
    get_plugin_manager,
    get_plugin_state_manager,
    get_schema_manager,
)
from src.config_manager import ConfigManager
from src.logging_config import get_logger
from src.plugin_system.operation_history import OperationHistory
from src.plugin_system.operation_queue import PluginOperationQueue
from src.plugin_system.plugin_manager import PluginManager
from src.plugin_system.schema_manager import SchemaManager
from src.plugin_system.state_manager import PluginStateManager

logger = get_logger("api.plugins")
router = APIRouter(prefix="/plugins", tags=["plugins"])
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _error(error_code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"status": "error", "error_code": error_code, "message": message}, status_code=status)


def _success(data: Any = None, message: str | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"status": "success"}
    if data is not None:
        resp["data"] = data
    if message is not None:
        resp["message"] = message
    return resp


def _save_config_atomic(cm: ConfigManager, data: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        if hasattr(cm, "save_config_atomic"):
            r = cm.save_config_atomic(data, create_backup=True)
            if hasattr(r, "status") and r.status.value == "success":
                return True, None
            return False, getattr(r, "message", "Atomic save failed")
        cm.save_config(data)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _find_secret_fields(properties: dict[str, Any], prefix: str = "") -> set[str]:
    fields: set[str] = set()
    for name, props in properties.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(props, dict) and props.get("x-secret", False):
            fields.add(path)
        if isinstance(props, dict) and props.get("type") == "object" and "properties" in props:
            fields.update(_find_secret_fields(props["properties"], path))
    return fields


def _separate_secrets(
    config: dict[str, Any], secret_fields: set[str], prefix: str = ""
) -> tuple[dict[str, Any], dict[str, Any]]:
    regular: dict[str, Any] = {}
    secrets: dict[str, Any] = {}
    for key, value in config.items():
        path = f"{prefix}.{key}" if prefix else key
        if path in secret_fields:
            secrets[key] = value
        elif isinstance(value, dict):
            r, s = _separate_secrets(value, secret_fields, path)
            if r:
                regular[key] = r
            if s:
                secrets[key] = s
        else:
            regular[key] = value
    return regular, secrets


def _get_plugin_dir(pm: PluginManager, pid: str) -> str | None:
    return pm.get_plugin_directory(pid) if hasattr(pm, "get_plugin_directory") else None


async def _run_script(
    script: Path, env: dict[str, str], *, stdin_data: bytes | None = None, timeout: float = 60.0
) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script),
        stdin=asyncio.subprocess.PIPE if stdin_data else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT if stdin_data else asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(input=stdin_data), timeout=timeout)
    return proc.returncode == 0, stdout.decode()


@router.get("/installed", response_model=None)
async def get_installed_plugins(
    pm: PluginManager = Depends(get_plugin_manager),
    cm: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        pm.discover_plugins()
        plugins_map = pm.get_all_plugin_info()
        config = cm.load_config()
        # get_all_plugin_info may return dict or list depending on plugin manager version
        raw: Any = plugins_map
        plugins: list[dict[str, Any]] = list(raw.values()) if isinstance(raw, dict) else list(raw)
        for p in plugins:
            p["enabled"] = config.get(p.get("id", ""), {}).get("enabled", True)
        return _success(data=plugins)
    except Exception as exc:
        return _error("PLUGIN_LIST_FAILED", str(exc), 500)


@router.post("/toggle", response_model=None)
async def toggle_plugin(
    request: Request,
    cm: ConfigManager = Depends(get_config_manager),
    sm: PluginStateManager = Depends(get_plugin_state_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")
    plugin_id, enabled = body.get("plugin_id"), body.get("enabled")
    if not plugin_id or enabled is None:
        return _error("INVALID_INPUT", "Missing 'plugin_id' or 'enabled'")
    try:
        config = cm.load_config()
        config.setdefault(plugin_id, {})["enabled"] = bool(enabled)
        ok, err = _save_config_atomic(cm, config)
        if not ok:
            return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
        sm.set_plugin_enabled(plugin_id, bool(enabled))
        return _success(message=f"Plugin {plugin_id} {'enabled' if enabled else 'disabled'}")
    except Exception as exc:
        return _error("TOGGLE_FAILED", str(exc), 500)


@router.get("/config", response_model=None)
async def get_plugin_config(
    plugin_id: str = Query(...),
    cm: ConfigManager = Depends(get_config_manager),
    schema_mgr: SchemaManager = Depends(get_schema_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        cfg = cm.load_config().get(plugin_id, {})
        defaults = schema_mgr.generate_default_config(plugin_id, use_cache=True)
        return _success(data=schema_mgr.merge_with_defaults(cfg, defaults))
    except Exception as exc:
        return _error("CONFIG_LOAD_FAILED", str(exc), 500)


@router.post("/config", response_model=None)
async def save_plugin_config(
    request: Request,
    cm: ConfigManager = Depends(get_config_manager),
    schema_mgr: SchemaManager = Depends(get_schema_manager),
    pm: PluginManager = Depends(get_plugin_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")
    plugin_id = body.pop("plugin_id", None)
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id'")
    try:
        config = cm.load_config()
        base = config.get(plugin_id, {})
        preserved_enabled = base.get("enabled", True)
        plugin_config = {**base, **body}
        schema = schema_mgr.load_schema(plugin_id, use_cache=True)
        if schema:
            defaults = schema_mgr.generate_default_config(plugin_id, use_cache=True)
            plugin_config = schema_mgr.merge_with_defaults(plugin_config, defaults)
        plugin_config["enabled"] = preserved_enabled
        if schema:
            errors = schema_mgr.validate_config_against_schema(plugin_id, plugin_config)
            if errors:
                return _error("VALIDATION_ERROR", "; ".join(str(e) for e in errors[:5]))
        sf = _find_secret_fields(schema["properties"]) if schema and "properties" in schema else set()
        regular, secrets = _separate_secrets(plugin_config, sf) if sf else (plugin_config, {})
        config[plugin_id] = regular
        ok, err = _save_config_atomic(cm, config)
        if not ok:
            return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
        if secrets:
            try:
                sd = cm.get_raw_file_content("secrets")
                sd.setdefault(plugin_id, {}).update(secrets)
                cm.save_raw_file_content("secrets", sd)
            except Exception as se:
                logger.warning("Failed to save secrets for %s: %s", plugin_id, se)
        inst = pm.get_plugin(plugin_id) if hasattr(pm, "get_plugin") else None
        if inst and hasattr(inst, "on_config_change"):
            try:
                inst.on_config_change()
            except Exception:
                pass
        msg = "Configuration saved"
        if secrets:
            msg += f" ({len(secrets)} secret field(s) saved to config_secrets.json)"
        return _success(message=msg)
    except Exception as exc:
        logger.error("Failed to save plugin config for %s: %s", plugin_id, exc)
        return _error("CONFIG_SAVE_FAILED", str(exc), 500)


@router.post("/config/reset", response_model=None)
async def reset_plugin_config(
    request: Request,
    cm: ConfigManager = Depends(get_config_manager),
    schema_mgr: SchemaManager = Depends(get_schema_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")
    plugin_id = body.get("plugin_id")
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id'")
    try:
        defaults = schema_mgr.generate_default_config(plugin_id, use_cache=True)
        config = cm.load_config()
        if body.get("preserve_secrets", True):
            old = config.get(plugin_id, {})
            schema = schema_mgr.load_schema(plugin_id, use_cache=True)
            if schema and "properties" in schema:
                for field in _find_secret_fields(schema["properties"]):
                    parts = field.split(".")
                    src, dst = old, defaults
                    for p in parts[:-1]:
                        src = src.get(p, {})
                        dst = dst.setdefault(p, {})
                    if parts[-1] in src:
                        dst[parts[-1]] = src[parts[-1]]
        config[plugin_id] = defaults
        ok, err = _save_config_atomic(cm, config)
        if not ok:
            return _error("CONFIG_SAVE_FAILED", err or "Unknown error", 500)
        return _success(data=defaults, message="Configuration reset to defaults")
    except Exception as exc:
        return _error("CONFIG_RESET_FAILED", str(exc), 500)


@router.get("/schema", response_model=None)
async def get_plugin_schema(
    plugin_id: str = Query(...), sm: SchemaManager = Depends(get_schema_manager)
) -> dict[str, Any] | JSONResponse:
    try:
        schema = sm.load_schema(plugin_id, use_cache=True)
        if schema is None:
            return _error("SCHEMA_NOT_FOUND", f"No schema for '{plugin_id}'", 404)
        return _success(data=schema)
    except Exception as exc:
        return _error("SCHEMA_LOAD_FAILED", str(exc), 500)


@router.post("/action", response_model=None)
async def execute_plugin_action(
    request: Request, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")
    plugin_id, action_id = body.get("plugin_id"), body.get("action_id")
    if not plugin_id or not action_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id' or 'action_id'")
    try:
        pdir = _get_plugin_dir(pm, plugin_id)
        if not pdir or not Path(pdir).exists():
            return _error("PLUGIN_NOT_FOUND", f"Plugin '{plugin_id}' not found", 404)
        script = Path(pdir) / "actions" / f"{action_id}.py"
        if not script.exists():
            return _error("ACTION_NOT_FOUND", f"Action '{action_id}' not found", 404)
        env = os.environ.copy()
        env["LEDMATRIX_ROOT"] = str(PROJECT_ROOT)
        ok, output = await _run_script(script, env, timeout=60.0)
        if ok:
            return _success(message="Action completed", data={"output": output})
        return _error("ACTION_FAILED", output or "Action failed", 500)
    except asyncio.TimeoutError:
        return _error("ACTION_TIMEOUT", "Action timed out", 408)
    except Exception as exc:
        return _error("ACTION_FAILED", str(exc), 500)


@router.get("/health", response_model=None)
async def get_all_plugin_health(pm: PluginManager = Depends(get_plugin_manager)) -> dict[str, Any] | JSONResponse:
    tracker = getattr(pm, "health_tracker", None)
    if not tracker:
        return _success(data={}, message="Health tracker not available")
    try:
        return _success(data=tracker.get_all_health_summaries())
    except Exception as exc:
        return _error("HEALTH_FETCH_FAILED", str(exc), 500)


@router.get("/health/{plugin_id}", response_model=None)
async def get_plugin_health(
    plugin_id: str, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    tracker = getattr(pm, "health_tracker", None)
    if not tracker:
        return _error("HEALTH_UNAVAILABLE", "Health tracker not available", 503)
    try:
        return _success(data=tracker.get_health_summary(plugin_id))
    except Exception as exc:
        return _error("HEALTH_FETCH_FAILED", str(exc), 500)


@router.post("/health/{plugin_id}/reset", response_model=None)
async def reset_plugin_health(
    plugin_id: str, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    tracker = getattr(pm, "health_tracker", None)
    if not tracker:
        return _error("HEALTH_UNAVAILABLE", "Health tracker not available", 503)
    try:
        tracker.reset_health(plugin_id)
        return _success(message=f"Health reset for '{plugin_id}'")
    except Exception as exc:
        return _error("HEALTH_RESET_FAILED", str(exc), 500)


@router.get("/metrics", response_model=None)
async def get_all_plugin_metrics(pm: PluginManager = Depends(get_plugin_manager)) -> dict[str, Any] | JSONResponse:
    monitor = getattr(pm, "resource_monitor", None)
    if not monitor:
        return _success(data={}, message="Resource monitor not available")
    try:
        return _success(data=monitor.get_all_metrics_summaries())
    except Exception as exc:
        return _error("METRICS_FETCH_FAILED", str(exc), 500)


@router.get("/metrics/{plugin_id}", response_model=None)
async def get_plugin_metrics(
    plugin_id: str, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    monitor = getattr(pm, "resource_monitor", None)
    if not monitor:
        return _error("METRICS_UNAVAILABLE", "Resource monitor not available", 503)
    try:
        return _success(data=monitor.get_metrics_summary(plugin_id))
    except Exception as exc:
        return _error("METRICS_FETCH_FAILED", str(exc), 500)


@router.post("/metrics/{plugin_id}/reset", response_model=None)
async def reset_plugin_metrics(
    plugin_id: str, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    monitor = getattr(pm, "resource_monitor", None)
    if not monitor:
        return _error("METRICS_UNAVAILABLE", "Resource monitor not available", 503)
    try:
        monitor.reset_metrics(plugin_id)
        return _success(message=f"Metrics reset for '{plugin_id}'")
    except Exception as exc:
        return _error("METRICS_RESET_FAILED", str(exc), 500)


@router.get("/limits/{plugin_id}", response_model=None)
async def get_resource_limits(
    plugin_id: str, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    monitor = getattr(pm, "resource_monitor", None)
    if not monitor:
        return _error("LIMITS_UNAVAILABLE", "Resource monitor not available", 503)
    try:
        limits = monitor.get_limits(plugin_id)
        return _success(data=asdict(limits) if limits else {})
    except Exception as exc:
        return _error("LIMITS_FETCH_FAILED", str(exc), 500)


@router.post("/limits/{plugin_id}", response_model=None)
async def set_resource_limits(
    plugin_id: str, request: Request, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    monitor = getattr(pm, "resource_monitor", None)
    if not monitor:
        return _error("LIMITS_UNAVAILABLE", "Resource monitor not available", 503)
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")
    try:
        from src.plugin_system.resource_monitor import ResourceLimits

        monitor.set_limits(
            plugin_id,
            ResourceLimits(
                max_memory_mb=body.get("max_memory_mb"),
                max_cpu_percent=body.get("max_cpu_percent"),
                max_execution_time=body.get("max_execution_time"),
                warning_threshold=body.get("warning_threshold", 0.8),
            ),
        )
        return _success(message=f"Resource limits set for '{plugin_id}'")
    except Exception as exc:
        return _error("LIMITS_SET_FAILED", str(exc), 500)


@router.get("/operation/{operation_id}", response_model=None)
async def get_operation_status(
    operation_id: str, oq: PluginOperationQueue = Depends(get_operation_queue)
) -> dict[str, Any] | JSONResponse:
    try:
        op = oq.get_operation_status(operation_id)
        if op is None:
            return _error("OPERATION_NOT_FOUND", f"Operation '{operation_id}' not found", 404)
        return _success(data=op.to_dict() if hasattr(op, "to_dict") else str(op))
    except Exception as exc:
        return _error("OPERATION_FETCH_FAILED", str(exc), 500)


@router.get("/operation/history", response_model=None)
async def get_operation_history_list(
    limit: int = Query(50, ge=1, le=500),
    plugin_id: str | None = Query(None),
    operation_type: str | None = Query(None),
    history: OperationHistory = Depends(get_operation_history),
) -> dict[str, Any] | JSONResponse:
    try:
        records = history.get_history(limit=limit, plugin_id=plugin_id, operation_type=operation_type)
        return _success(data=[r.to_dict() if hasattr(r, "to_dict") else r for r in records])
    except Exception as exc:
        return _error("HISTORY_FETCH_FAILED", str(exc), 500)


@router.delete("/operation/history", response_model=None)
async def clear_operation_history(
    history: OperationHistory = Depends(get_operation_history),
) -> dict[str, Any] | JSONResponse:
    try:
        history.clear_history()
        return _success(message="Operation history cleared")
    except Exception as exc:
        return _error("HISTORY_CLEAR_FAILED", str(exc), 500)


@router.get("/state", response_model=None)
async def get_plugin_state(
    plugin_id: str | None = Query(None),
    sm: PluginStateManager = Depends(get_plugin_state_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        if plugin_id:
            state = sm.get_plugin_state(plugin_id)
            if state is None:
                return _error("STATE_NOT_FOUND", f"No state for '{plugin_id}'", 404)
            return _success(data=state.to_dict())
        return _success(data={pid: s.to_dict() for pid, s in sm.get_all_states().items()})
    except Exception as exc:
        return _error("STATE_FETCH_FAILED", str(exc), 500)


@router.post("/state/reconcile", response_model=None)
async def reconcile_state(
    pm: PluginManager = Depends(get_plugin_manager),
    sm: PluginStateManager = Depends(get_plugin_state_manager),
    cm: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any] | JSONResponse:
    try:
        pm.discover_plugins()
        config = cm.load_config()
        reconciled = 0
        for plugin in pm.get_all_plugin_info():
            pid = plugin.get("id", "")
            if not pid:
                continue
            sm.set_plugin_enabled(pid, config.get(pid, {}).get("enabled", True))
            if plugin.get("version"):
                sm.update_plugin_state(pid, {"version": plugin["version"]}, notify=False)
            reconciled += 1
        return _success(data={"reconciled_count": reconciled}, message=f"Reconciled {reconciled} plugins")
    except Exception as exc:
        return _error("RECONCILE_FAILED", str(exc), 500)


@router.post("/authenticate/spotify", response_model=None)
async def authenticate_spotify(
    request: Request, pm: PluginManager = Depends(get_plugin_manager)
) -> dict[str, Any] | JSONResponse:
    """Spotify OAuth flow (2-step: get URL, then complete with redirect)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    redirect_url = (body.get("redirect_url") or "").strip()
    plugin_id = "ledmatrix-music"
    pdir = _get_plugin_dir(pm, plugin_id)
    if not pdir or not Path(pdir).exists():
        return _error("PLUGIN_NOT_FOUND", f"Plugin {plugin_id} not found", 404)
    script = Path(pdir) / "authenticate_spotify.py"
    if not script.exists():
        return _error("AUTH_SCRIPT_NOT_FOUND", "Spotify auth script not found", 404)
    env = os.environ.copy()
    env["LEDMATRIX_ROOT"] = str(PROJECT_ROOT)
    if redirect_url:
        try:
            ok, output = await _run_script(script, env, stdin_data=(redirect_url + "\n").encode(), timeout=120.0)
            if ok:
                return _success(message="Spotify authentication completed", data={"output": output})
            return _error("AUTH_FAILED", "Spotify authentication failed", 400)
        except asyncio.TimeoutError:
            return _error("AUTH_TIMEOUT", "Authentication timed out", 408)
    else:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("auth_spotify", script)
            if spec is None:
                return _error("AUTH_FAILED", "Could not load auth script", 500)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["auth_spotify"] = mod
            os.environ["LEDMATRIX_ROOT"] = str(PROJECT_ROOT)
            exec_module = getattr(spec.loader, "exec_module", None)
            if exec_module is not None:
                exec_module(mod)
            cid, csec, ruri = mod.load_spotify_credentials()
            if not all([cid, csec, ruri]):
                return _error("AUTH_CONFIG_MISSING", "Spotify credentials not configured", 400)
            from spotipy.oauth2 import SpotifyOAuth

            sp = SpotifyOAuth(
                client_id=cid,
                client_secret=csec,
                redirect_uri=ruri,
                scope=mod.SCOPE,
                cache_path=getattr(mod, "SPOTIFY_AUTH_CACHE_PATH", None),
            )
            return _success(data={"auth_url": sp.get_authorize_url(), "needs_redirect": True})
        except Exception as exc:
            return _error("AUTH_FAILED", f"Error generating auth URL: {exc}", 500)


@router.post("/authenticate/ytm", response_model=None)
async def authenticate_ytm(pm: PluginManager = Depends(get_plugin_manager)) -> dict[str, Any] | JSONResponse:
    """Run YouTube Music authentication script."""
    plugin_id = "ledmatrix-music"
    pdir = _get_plugin_dir(pm, plugin_id)
    if not pdir or not Path(pdir).exists():
        return _error("PLUGIN_NOT_FOUND", f"Plugin {plugin_id} not found", 404)
    script = Path(pdir) / "authenticate_ytm.py"
    if not script.exists():
        return _error("AUTH_SCRIPT_NOT_FOUND", "YTM auth script not found", 404)
    env = os.environ.copy()
    env["LEDMATRIX_ROOT"] = str(PROJECT_ROOT)
    try:
        ok, output = await _run_script(script, env, timeout=60.0)
        if ok:
            return _success(message="YouTube Music authentication completed", data={"output": output})
        return _error("AUTH_FAILED", "YouTube Music authentication failed", 400)
    except asyncio.TimeoutError:
        return _error("AUTH_TIMEOUT", "Authentication timed out", 408)
    except Exception as exc:
        return _error("AUTH_FAILED", str(exc), 500)
