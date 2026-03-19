"""Asset and plugin file API routes — /plugins/assets/*, /plugins/*/static/* endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from src.logging_config import get_logger

logger = get_logger("api.assets")

router = APIRouter(prefix="/plugins", tags=["assets"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
PLUGINS_DIR = PROJECT_ROOT / "plugins"
PLUGIN_REPOS_DIR = PROJECT_ROOT / "plugin-repos"
DATA_DIR = PROJECT_ROOT / "data"

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_UPLOAD_COUNT = 10
CALENDAR_MAX_SIZE = 1 * 1024 * 1024  # 1 MB


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


def _get_plugin_assets_dir(plugin_id: str) -> Path:
    """Return the uploads directory for a plugin's assets."""
    return ASSETS_DIR / "plugins" / plugin_id / "uploads"


def _resolve_plugin_dir(plugin_id: str) -> Path | None:
    """Find the actual plugin directory (may be in plugins/ or plugin-repos/)."""
    for base in (PLUGINS_DIR, PLUGIN_REPOS_DIR):
        candidate = base / plugin_id
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def _is_safe_path(base: Path, target: Path) -> bool:
    """Ensure target is within base directory (prevent directory traversal)."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _file_metadata(path: Path) -> dict[str, Any]:
    """Return metadata dict for a file."""
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified": stat.st_mtime,
    }


# ---- asset upload / delete / list -------------------------------------------


@router.post("/assets/upload")
async def upload_assets(
    plugin_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """Upload asset files for a plugin (max 10 files, 5 MB each)."""
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing plugin_id")

    if len(files) > MAX_UPLOAD_COUNT:
        return _error("INVALID_INPUT", f"Maximum {MAX_UPLOAD_COUNT} files per upload")

    upload_dir = _get_plugin_assets_dir(plugin_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded: list[dict[str, Any]] = []
    errors: list[str] = []

    for f in files:
        if not f.filename:
            errors.append("Skipped file with no filename")
            continue

        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            errors.append(f"'{f.filename}' exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit")
            continue

        # Sanitize filename
        safe_name = Path(f.filename).name
        target = upload_dir / safe_name

        if not _is_safe_path(upload_dir, target):
            errors.append(f"Invalid filename: '{f.filename}'")
            continue

        try:
            target.write_bytes(content)
            uploaded.append({"filename": safe_name, "size_bytes": len(content)})
        except Exception as exc:
            errors.append(f"Failed to save '{safe_name}': {exc}")

    data: dict[str, Any] = {"uploaded": uploaded}
    if errors:
        data["errors"] = errors

    return _success(data=data, message=f"Uploaded {len(uploaded)} file(s)")


@router.post("/assets/delete")
async def delete_asset(request: Request):
    """Delete an asset file. Expects {plugin_id, image_id}."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    plugin_id = body.get("plugin_id")
    image_id = body.get("image_id")

    if not plugin_id or not image_id:
        return _error("INVALID_INPUT", "Missing required fields: plugin_id, image_id")

    assets_dir = _get_plugin_assets_dir(plugin_id)
    target = assets_dir / Path(image_id).name  # sanitize

    if not _is_safe_path(assets_dir, target):
        return _error("INVALID_INPUT", "Invalid file path")

    if not target.exists():
        return _error("NOT_FOUND", f"Asset '{image_id}' not found", 404)

    try:
        target.unlink()
        return _success(message=f"Asset '{image_id}' deleted")
    except Exception as exc:
        logger.error("Failed to delete asset: %s", exc)
        return _error("ASSET_ERROR", str(exc), 500)


@router.get("/assets/list")
async def list_assets(plugin_id: str = Query(...)):
    """List asset files for a plugin."""
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing plugin_id query parameter")

    assets_dir = _get_plugin_assets_dir(plugin_id)
    if not assets_dir.exists():
        return _success(data={"files": [], "plugin_id": plugin_id})

    files = []
    for path in sorted(assets_dir.iterdir()):
        if path.is_file():
            files.append(_file_metadata(path))

    return _success(data={"files": files, "plugin_id": plugin_id})


# ---- static file serving ----------------------------------------------------


@router.get("/{plugin_id}/static/{file_path:path}")
async def serve_plugin_static(plugin_id: str, file_path: str):
    """Serve a static file from a plugin's directory."""
    plugin_dir = _resolve_plugin_dir(plugin_id)
    if plugin_dir is None:
        return _error("NOT_FOUND", f"Plugin '{plugin_id}' not found", 404)

    target = (plugin_dir / file_path).resolve()

    if not _is_safe_path(plugin_dir, target):
        return _error("FORBIDDEN", "Access denied: path traversal detected", 403)

    if not target.exists() or not target.is_file():
        return _error("NOT_FOUND", f"File not found: {file_path}", 404)

    return FileResponse(str(target))


# ---- of-the-day JSON upload / delete ----------------------------------------


@router.post("/of-the-day/json/upload")
async def upload_of_the_day_json(
    files: UploadFile = File(...),
):
    """Upload a JSON data file for the of-the-day plugin."""
    if not files.filename:
        return _error("INVALID_INPUT", "No filename provided")

    if not files.filename.lower().endswith(".json"):
        return _error("INVALID_INPUT", "Only .json files are accepted")

    content = await files.read()
    if len(content) > MAX_FILE_SIZE:
        return _error("INVALID_INPUT", f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit")

    save_dir = DATA_DIR / "of-the-day"
    save_dir.mkdir(parents=True, exist_ok=True)

    target = save_dir / Path(files.filename).name
    if not _is_safe_path(save_dir, target):
        return _error("INVALID_INPUT", "Invalid filename")

    try:
        target.write_bytes(content)
        return _success(
            data={"filename": target.name, "size_bytes": len(content)},
            message=f"Uploaded '{target.name}'",
        )
    except Exception as exc:
        logger.error("Failed to upload of-the-day JSON: %s", exc)
        return _error("ASSET_ERROR", str(exc), 500)


@router.post("/of-the-day/json/delete")
async def delete_of_the_day_json(request: Request):
    """Delete a JSON data file. Expects {file_id}."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    file_id = body.get("file_id")
    if not file_id:
        return _error("INVALID_INPUT", "Missing required field: file_id")

    save_dir = DATA_DIR / "of-the-day"
    target = save_dir / Path(file_id).name

    if not _is_safe_path(save_dir, target):
        return _error("INVALID_INPUT", "Invalid file path")

    if not target.exists():
        return _error("NOT_FOUND", f"File '{file_id}' not found", 404)

    try:
        target.unlink()
        return _success(message=f"File '{file_id}' deleted")
    except Exception as exc:
        logger.error("Failed to delete of-the-day JSON: %s", exc)
        return _error("ASSET_ERROR", str(exc), 500)


# ---- calendar credentials ---------------------------------------------------


@router.post("/calendar/upload-credentials")
async def upload_calendar_credentials(
    file: UploadFile = File(...),
):
    """Upload Google Calendar credentials JSON file."""
    if not file.filename:
        return _error("INVALID_INPUT", "No filename provided")

    if not file.filename.lower().endswith(".json"):
        return _error("INVALID_INPUT", "Only .json files are accepted")

    content = await file.read()
    if len(content) > CALENDAR_MAX_SIZE:
        return _error("INVALID_INPUT", f"File exceeds {CALENDAR_MAX_SIZE // (1024 * 1024)} MB limit")

    # Validate it is parsable JSON
    try:
        import json

        json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return _error("INVALID_INPUT", "File is not valid JSON")

    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / "google_calendar_credentials.json"

    try:
        target.write_bytes(content)
        return _success(message="Calendar credentials uploaded successfully")
    except Exception as exc:
        logger.error("Failed to save calendar credentials: %s", exc)
        return _error("ASSET_ERROR", str(exc), 500)


@router.get("/calendar/list-calendars")
async def list_calendars():
    """List Google calendars using stored credentials."""
    creds_path = PROJECT_ROOT / "config" / "google_calendar_credentials.json"
    if not creds_path.exists():
        return _error("NOT_FOUND", "No calendar credentials found. Upload credentials first.", 404)

    # Try to import the calendar plugin's helper
    try:
        from plugins.google_calendar.calendar_helper import list_calendars as _list_cals

        calendars = _list_cals(str(creds_path))
        return _success(data={"calendars": calendars})
    except ImportError:
        pass

    # Fallback: try plugin-repos path
    try:
        import importlib.util

        helper_path = PLUGIN_REPOS_DIR / "google_calendar" / "calendar_helper.py"
        if helper_path.exists():
            spec = importlib.util.spec_from_file_location("calendar_helper", str(helper_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                calendars = mod.list_calendars(str(creds_path))
                return _success(data={"calendars": calendars})
    except Exception as exc:
        logger.warning("Failed to load calendar helper from plugin-repos: %s", exc)

    return _error(
        "DEPENDENCY_MISSING",
        "Google Calendar plugin not installed. Install it to list calendars.",
        503,
    )
