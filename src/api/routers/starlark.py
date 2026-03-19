"""Starlark (Pixlet) API routes — /starlark/* endpoints."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from src.logging_config import get_logger

logger = get_logger("api.starlark")

router = APIRouter(prefix="/starlark", tags=["starlark"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PLUGINS_DIR = PROJECT_ROOT / "plugins"
STARLARK_DIR = PLUGINS_DIR / "starlark"
APPS_DIR = STARLARK_DIR / "apps"
MANIFEST_PATH = STARLARK_DIR / "starlark_manifest.json"

TRONBYTE_REPO_URL = "https://raw.githubusercontent.com/tronbyte/pixlet-apps/main"


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


def _read_manifest() -> dict:
    """Read the starlark manifest, returning empty structure if not found."""
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read starlark manifest: %s", exc)
    return {"apps": {}}


def _write_manifest(data: dict) -> None:
    """Write the starlark manifest."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(data, indent=2))


def _is_pixlet_available() -> bool:
    """Check if the pixlet binary is on PATH."""
    return shutil.which("pixlet") is not None


def _get_app_details(app_id: str, manifest: dict) -> dict[str, Any] | None:
    """Build detail dict for a single app from the manifest."""
    app_entry = manifest.get("apps", {}).get(app_id)
    if app_entry is None:
        return None

    star_file = APPS_DIR / f"{app_id}.star"
    config_file = APPS_DIR / f"{app_id}.json"
    schema_file = APPS_DIR / f"{app_id}_schema.json"

    detail: dict[str, Any] = {
        "app_id": app_id,
        **app_entry,
        "has_star_file": star_file.exists(),
        "has_config": config_file.exists(),
        "has_schema": schema_file.exists(),
    }
    return detail


def _starlark_not_installed() -> JSONResponse:
    """Return standard error when the starlark plugin is missing."""
    return _error(
        "STARLARK_NOT_INSTALLED",
        "Starlark plugin is not installed. Install it from the plugin store.",
        404,
    )


async def _run_cmd(
    *args: str,
    timeout: float = 30.0,
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


# ---- routes -----------------------------------------------------------------


@router.get("/status")
async def get_starlark_status():
    """Check if pixlet is available and count installed apps."""
    pixlet_available = _is_pixlet_available()
    plugin_installed = STARLARK_DIR.exists()
    manifest = _read_manifest() if plugin_installed else {"apps": {}}
    app_count = len(manifest.get("apps", {}))

    # Get pixlet version if available
    pixlet_version = None
    if pixlet_available:
        rc, stdout, _ = await _run_cmd("pixlet", "version", timeout=5.0)
        if rc == 0:
            pixlet_version = stdout

    return _success(
        data={
            "plugin_installed": plugin_installed,
            "pixlet_available": pixlet_available,
            "pixlet_version": pixlet_version,
            "app_count": app_count,
        }
    )


@router.get("/apps")
async def list_apps():
    """List all starlark apps from the manifest."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    manifest = _read_manifest()
    apps = []
    for app_id in manifest.get("apps", {}):
        detail = _get_app_details(app_id, manifest)
        if detail:
            apps.append(detail)

    return _success(data={"apps": apps})


@router.get("/apps/{app_id}")
async def get_app(app_id: str):
    """Get details for a single starlark app."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    manifest = _read_manifest()
    detail = _get_app_details(app_id, manifest)
    if detail is None:
        return _error("NOT_FOUND", f"App '{app_id}' not found", 404)

    return _success(data=detail)


@router.post("/upload")
async def upload_app(
    file: UploadFile = File(...),
    name: str = Form(...),
    app_id: str = Form(...),
    render_interval: int = Form(300),
    display_duration: int = Form(15),
):
    """Upload a .star app file."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    if not file.filename or not file.filename.endswith(".star"):
        return _error("INVALID_INPUT", "Only .star files are accepted")

    # Validate app_id (alphanumeric + underscores/hyphens)
    safe_id = "".join(c for c in app_id if c.isalnum() or c in "-_")
    if safe_id != app_id or not safe_id:
        return _error("INVALID_INPUT", "app_id must be alphanumeric with hyphens/underscores only")

    APPS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        content = await file.read()
        star_path = APPS_DIR / f"{app_id}.star"
        star_path.write_bytes(content)

        # Update manifest
        manifest = _read_manifest()
        manifest.setdefault("apps", {})[app_id] = {
            "name": name,
            "enabled": True,
            "render_interval": render_interval,
            "display_duration": display_duration,
        }
        _write_manifest(manifest)

        return _success(
            data={"app_id": app_id, "filename": star_path.name},
            message=f"App '{name}' uploaded successfully",
        )
    except Exception as exc:
        logger.error("Failed to upload starlark app: %s", exc)
        return _error("STARLARK_ERROR", str(exc), 500)


@router.delete("/apps/{app_id}")
async def delete_app(app_id: str):
    """Remove a starlark app and its files."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    manifest = _read_manifest()
    if app_id not in manifest.get("apps", {}):
        return _error("NOT_FOUND", f"App '{app_id}' not found in manifest", 404)

    # Remove files
    for suffix in (".star", ".json", "_schema.json"):
        path = APPS_DIR / f"{app_id}{suffix}"
        if path.exists():
            path.unlink()

    # Remove from manifest
    del manifest["apps"][app_id]
    _write_manifest(manifest)

    return _success(message=f"App '{app_id}' deleted")


@router.get("/apps/{app_id}/config")
async def get_app_config(app_id: str):
    """Read a starlark app's config JSON."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    config_path = APPS_DIR / f"{app_id}.json"
    if not config_path.exists():
        return _success(data={"app_id": app_id, "config": {}})

    try:
        config = json.loads(config_path.read_text())
        return _success(data={"app_id": app_id, "config": config})
    except (json.JSONDecodeError, OSError) as exc:
        return _error("STARLARK_ERROR", f"Failed to read config: {exc}", 500)


@router.put("/apps/{app_id}/config")
async def update_app_config(app_id: str, request: Request):
    """Write a starlark app's config JSON."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    APPS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = APPS_DIR / f"{app_id}.json"

    try:
        config_path.write_text(json.dumps(body, indent=2))
        return _success(message=f"Config for '{app_id}' updated")
    except Exception as exc:
        logger.error("Failed to write app config: %s", exc)
        return _error("STARLARK_ERROR", str(exc), 500)


@router.post("/apps/{app_id}/toggle")
async def toggle_app(app_id: str):
    """Toggle the enabled state of a starlark app in the manifest."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    manifest = _read_manifest()
    apps = manifest.get("apps", {})
    if app_id not in apps:
        return _error("NOT_FOUND", f"App '{app_id}' not found in manifest", 404)

    apps[app_id]["enabled"] = not apps[app_id].get("enabled", True)
    _write_manifest(manifest)

    return _success(
        data={"app_id": app_id, "enabled": apps[app_id]["enabled"]},
        message=f"App '{app_id}' {'enabled' if apps[app_id]['enabled'] else 'disabled'}",
    )


@router.post("/apps/{app_id}/render")
async def render_app(app_id: str):
    """Trigger a render of a starlark app via pixlet."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    if not _is_pixlet_available():
        return _error("DEPENDENCY_MISSING", "pixlet is not installed", 503)

    star_file = APPS_DIR / f"{app_id}.star"
    if not star_file.exists():
        return _error("NOT_FOUND", f"Star file for '{app_id}' not found", 404)

    output_path = APPS_DIR / f"{app_id}.webp"

    try:
        rc, stdout, stderr = await _run_cmd(
            "pixlet",
            "render",
            str(star_file),
            "-o",
            str(output_path),
            timeout=30.0,
        )
        if rc != 0:
            return _error("RENDER_FAILED", f"pixlet render failed: {stderr}")

        return _success(
            data={"app_id": app_id, "output": str(output_path), "stdout": stdout},
            message=f"App '{app_id}' rendered successfully",
        )
    except Exception as exc:
        logger.error("Failed to render starlark app: %s", exc)
        return _error("STARLARK_ERROR", str(exc), 500)


@router.get("/repository/browse")
async def browse_repository():
    """Fetch the app catalog from the tronbyte repository."""
    try:
        import httpx
    except ImportError:
        return _error("DEPENDENCY_MISSING", "httpx is not installed", 503)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{TRONBYTE_REPO_URL}/catalog.json")
            resp.raise_for_status()
            catalog = resp.json()
        return _success(data={"catalog": catalog})
    except Exception as exc:
        logger.error("Failed to browse repository: %s", exc)
        return _error("REPOSITORY_ERROR", str(exc), 502)


@router.post("/repository/install")
async def install_from_repository(request: Request):
    """Install an app from the tronbyte repository."""
    if not STARLARK_DIR.exists():
        return _starlark_not_installed()

    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    app_id = body.get("app_id")
    if not app_id:
        return _error("INVALID_INPUT", "Missing required field: app_id")

    try:
        import httpx
    except ImportError:
        return _error("DEPENDENCY_MISSING", "httpx is not installed", 503)

    APPS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Download .star file
            star_url = f"{TRONBYTE_REPO_URL}/apps/{app_id}/{app_id}.star"
            resp = await client.get(star_url)
            resp.raise_for_status()
            star_path = APPS_DIR / f"{app_id}.star"
            star_path.write_bytes(resp.content)

            # Try to download config schema (optional)
            schema_url = f"{TRONBYTE_REPO_URL}/apps/{app_id}/{app_id}_schema.json"
            try:
                schema_resp = await client.get(schema_url)
                if schema_resp.status_code == 200:
                    schema_path = APPS_DIR / f"{app_id}_schema.json"
                    schema_path.write_bytes(schema_resp.content)
            except Exception:
                pass

        # Update manifest
        name = body.get("name", app_id.replace("-", " ").replace("_", " ").title())
        manifest = _read_manifest()
        manifest.setdefault("apps", {})[app_id] = {
            "name": name,
            "enabled": True,
            "render_interval": body.get("render_interval", 300),
            "display_duration": body.get("display_duration", 15),
            "source": "repository",
        }
        _write_manifest(manifest)

        return _success(
            data={"app_id": app_id},
            message=f"App '{name}' installed from repository",
        )
    except Exception as exc:
        logger.error("Failed to install from repository: %s", exc)
        return _error("REPOSITORY_ERROR", str(exc), 502)


@router.get("/repository/categories")
async def list_repository_categories():
    """List available categories from the tronbyte repository."""
    try:
        import httpx
    except ImportError:
        return _error("DEPENDENCY_MISSING", "httpx is not installed", 503)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{TRONBYTE_REPO_URL}/catalog.json")
            resp.raise_for_status()
            catalog = resp.json()

        # Extract unique categories from catalog
        categories: set[str] = set()
        apps = catalog if isinstance(catalog, list) else catalog.get("apps", [])
        for app in apps:
            if isinstance(app, dict):
                cat = app.get("category")
                if cat:
                    categories.add(cat)

        return _success(data={"categories": sorted(categories)})
    except Exception as exc:
        logger.error("Failed to fetch repository categories: %s", exc)
        return _error("REPOSITORY_ERROR", str(exc), 502)


@router.post("/install-pixlet")
async def install_pixlet():
    """Install the pixlet binary by downloading the latest release."""
    if _is_pixlet_available():
        return _success(message="pixlet is already installed")

    import platform

    arch = platform.machine()
    arch_map = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm"}
    go_arch = arch_map.get(arch)

    if not go_arch:
        return _error("UNSUPPORTED", f"Unsupported architecture: {arch}")

    tarball_url = f"https://github.com/tidbyt/pixlet/releases/latest/download/pixlet_linux_{go_arch}.tar.gz"
    tmp_tarball = Path("/tmp/pixlet.tar.gz")
    tmp_binary = Path("/tmp/pixlet")

    steps = [
        (["curl", "-sL", "-o", str(tmp_tarball), tarball_url], 120.0, "Download"),
        (["tar", "xzf", str(tmp_tarball), "-C", "/tmp", "pixlet"], 30.0, "Extract"),
        (["sudo", "mv", str(tmp_binary), "/usr/local/bin/pixlet"], 10.0, "Install"),
        (["sudo", "chmod", "+x", "/usr/local/bin/pixlet"], 5.0, "Permissions"),
    ]
    try:
        for cmd, t, label in steps:
            rc, _, stderr = await _run_cmd(*cmd, timeout=t)
            if rc != 0:
                return _error("INSTALL_FAILED", f"{label} failed: {stderr}")
        return _success(message="pixlet installed successfully")
    except Exception as exc:
        logger.error("Failed to install pixlet: %s", exc)
        return _error("INSTALL_FAILED", str(exc), 500)
    finally:
        for p in (tmp_tarball, tmp_binary):
            p.unlink(missing_ok=True) if p.exists() else None
