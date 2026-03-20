"""HTMX page routes — serves Jinja2 templates for the web interface.

Mechanical port of the deleted Flask pages_v3.py blueprint.
These routes are temporary (Phase 2) and will be replaced by an Angular SPA in Phase 3.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src.api.dependencies import (
    get_config_manager,
    get_plugin_manager,
    get_plugin_store_manager,
)
from src.config_manager import ConfigManager
from src.logging_config import get_logger
from src.plugin_system.plugin_manager import PluginManager
from src.plugin_system.store_manager import PluginStoreManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "web_interface" / "templates"

router = APIRouter(prefix="/v3", tags=["pages"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Partials that just need main_config as context
_SIMPLE_PARTIALS = {
    "overview": "v3/partials/overview.html",
    "general": "v3/partials/general.html",
    "display": "v3/partials/display.html",
    "durations": "v3/partials/durations.html",
    "weather": "v3/partials/weather.html",
    "stocks": "v3/partials/stocks.html",
}

# Partials with no context needed
_STATIC_PARTIALS = {
    "fonts": "v3/partials/fonts.html",
    "logs": "v3/partials/logs.html",
    "wifi": "v3/partials/wifi.html",
    "cache": "v3/partials/cache.html",
    "operation-history": "v3/partials/operation_history.html",
}


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> Response:
    """Main v3 interface page."""
    try:
        main_config = config_manager.load_config()
        schedule_config = main_config.get("schedule", {})
        main_config_data = config_manager.get_raw_file_content("main")
        secrets_config_data = config_manager.get_raw_file_content("secrets")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        schedule_config = {}
        main_config_data = {}
        secrets_config_data = {}

    return templates.TemplateResponse(
        "v3/index.html",
        {
            "request": request,
            "schedule_config": schedule_config,
            "main_config_json": json.dumps(main_config_data, indent=4),
            "secrets_config_json": json.dumps(secrets_config_data, indent=4),
            "main_config_path": config_manager.get_config_path(),
            "secrets_config_path": config_manager.get_secrets_path(),
            "main_config": main_config_data,
            "secrets_config": secrets_config_data,
        },
    )


@router.get("/partials/{partial_name}", response_class=HTMLResponse)
async def load_partial(
    partial_name: str,
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    plugin_store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
) -> Response:
    """Load HTMX partials dynamically."""
    try:
        # Simple partials: just pass main_config
        if partial_name in _SIMPLE_PARTIALS:
            main_config = config_manager.load_config()
            return templates.TemplateResponse(
                _SIMPLE_PARTIALS[partial_name],
                {"request": request, "main_config": main_config},
            )

        # Static partials: no context needed
        if partial_name in _STATIC_PARTIALS:
            template = _STATIC_PARTIALS[partial_name]
            # fonts partial expects a fonts dict
            ctx: dict[str, Any] = {"request": request}
            if partial_name == "fonts":
                ctx["fonts"] = {}
            return templates.TemplateResponse(template, ctx)

        # Complex partials with custom context
        if partial_name == "schedule":
            return _render_schedule(request, config_manager)

        if partial_name == "plugins":
            return _render_plugins(request, config_manager, plugin_manager, plugin_store_manager)

        if partial_name == "raw-json":
            return _render_raw_json(request, config_manager)

        return HTMLResponse(
            content=f"Partial '{partial_name}' not found",
            status_code=404,
        )

    except Exception as e:
        logger.error(f"Error loading partial '{partial_name}': {e}")
        return HTMLResponse(
            content=f"Error loading partial '{partial_name}': {e}",
            status_code=500,
        )


@router.get("/partials/plugin-config/{plugin_id}", response_class=HTMLResponse)
async def load_plugin_config(
    plugin_id: str,
    request: Request,
    config_manager: ConfigManager = Depends(get_config_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
) -> Response:
    """Load plugin configuration partial — server-side rendered form."""
    try:
        # Handle starlark app config
        if plugin_id.startswith("starlark:"):
            return _render_starlark_config(request, plugin_id[len("starlark:") :], plugin_manager)

        plugin_info = plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            plugin_manager.discover_plugins()
            plugin_info = plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            return HTMLResponse(
                content=f'<div class="text-red-500 p-4">Plugin "{plugin_id}" not found</div>',
                status_code=404,
            )

        plugin_instance = plugin_manager.get_plugin(plugin_id)
        full_config = config_manager.load_config()
        config = full_config.get(plugin_id, {})

        # Merge uploaded images from metadata file
        plugins_dir = Path(plugin_manager.plugins_dir)
        _merge_image_metadata(plugin_id, plugins_dir, config)

        # Load schema
        schema = {}
        schema_path = plugins_dir / plugin_id / "config_schema.json"
        if schema_path.exists():
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not load schema for {plugin_id}: {e}")

        # Load web UI actions from manifest
        web_ui_actions = []
        manifest_path = plugins_dir / plugin_id / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                web_ui_actions = manifest.get("web_ui_actions", [])
            except Exception as e:
                logger.warning(f"Could not load manifest for {plugin_id}: {e}")

        enabled = config.get("enabled", True)
        if plugin_instance:
            enabled = plugin_instance.enabled

        plugin_data = {
            "id": plugin_id,
            "name": plugin_info.get("name", plugin_id),
            "author": plugin_info.get("author", "Unknown"),
            "version": plugin_info.get("version", ""),
            "description": plugin_info.get("description", ""),
            "category": plugin_info.get("category", "General"),
            "tags": plugin_info.get("tags", []),
            "enabled": enabled,
            "last_commit": plugin_info.get("last_commit") or plugin_info.get("last_commit_sha", ""),
            "branch": plugin_info.get("branch", ""),
        }

        return templates.TemplateResponse(
            "v3/partials/plugin_config.html",
            {
                "request": request,
                "plugin": plugin_data,
                "config": config,
                "schema": schema,
                "web_ui_actions": web_ui_actions,
            },
        )

    except Exception as e:
        logger.error(f"Error loading plugin config for {plugin_id}: {e}", exc_info=True)
        return HTMLResponse(
            content=f'<div class="text-red-500 p-4">Error loading plugin config: {e}</div>',
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _render_schedule(request: Request, config_manager: ConfigManager) -> Response:
    main_config = config_manager.load_config()
    return templates.TemplateResponse(
        "v3/partials/schedule.html",
        {
            "request": request,
            "schedule_config": main_config.get("schedule", {}),
            "dim_schedule_config": main_config.get("dim_schedule", {}),
            "normal_brightness": main_config.get("display", {}).get("hardware", {}).get("brightness", 90),
        },
    )


def _render_plugins(
    request: Request,
    config_manager: ConfigManager,
    plugin_manager: PluginManager,
    plugin_store_manager: PluginStoreManager,
) -> Response:
    plugins_data = []
    try:
        all_plugin_info = plugin_manager.get_all_plugin_info()
        full_config = config_manager.load_config()

        for plugin_info in all_plugin_info:
            plugin_id: str | None = plugin_info.get("id")
            if not plugin_id:
                continue

            # Re-read manifest from disk for fresh metadata
            manifest_path = Path(plugin_manager.plugins_dir) / plugin_id / "manifest.json"
            if manifest_path.exists():
                try:
                    fresh_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    plugin_info.update(fresh_manifest)
                except Exception:
                    pass

            # Determine enabled status from config (source of truth)
            enabled = None
            plugin_config = full_config.get(plugin_id, {})
            if "enabled" in plugin_config:
                enabled = bool(plugin_config["enabled"])
            if enabled is None:
                plugin_instance = plugin_manager.get_plugin(plugin_id)
                enabled = plugin_instance.enabled if plugin_instance else True

            # Get verified status from store registry
            store_info = plugin_store_manager.get_registry_info(plugin_id)
            verified = store_info.get("verified", False) if store_info else False

            last_updated = plugin_info.get("last_updated")
            last_commit = plugin_info.get("last_commit") or plugin_info.get("last_commit_sha")
            branch = plugin_info.get("branch")
            if store_info:
                last_updated = last_updated or store_info.get("last_updated") or store_info.get("last_updated_iso")
                last_commit = last_commit or store_info.get("last_commit") or store_info.get("last_commit_sha")
                branch = branch or store_info.get("branch") or store_info.get("default_branch")

            plugins_data.append(
                {
                    "id": plugin_id,
                    "name": plugin_info.get("name", plugin_id),
                    "author": plugin_info.get("author", "Unknown"),
                    "category": plugin_info.get("category", "General"),
                    "description": plugin_info.get("description", "No description available"),
                    "tags": plugin_info.get("tags", []),
                    "enabled": enabled,
                    "verified": verified,
                    "loaded": plugin_info.get("loaded", False),
                    "last_updated": last_updated,
                    "last_commit": last_commit,
                    "branch": branch,
                }
            )
    except Exception as e:
        logger.error(f"Error loading plugin data: {e}")

    return templates.TemplateResponse(
        "v3/partials/plugins.html",
        {"request": request, "plugins": plugins_data},
    )


def _render_raw_json(request: Request, config_manager: ConfigManager) -> Response:
    main_config_data = config_manager.get_raw_file_content("main")
    secrets_config_data = config_manager.get_raw_file_content("secrets")
    return templates.TemplateResponse(
        "v3/partials/raw_json.html",
        {
            "request": request,
            "main_config_json": json.dumps(main_config_data, indent=4),
            "secrets_config_json": json.dumps(secrets_config_data, indent=4),
            "main_config_path": config_manager.get_config_path(),
            "secrets_config_path": config_manager.get_secrets_path(),
        },
    )


def _render_starlark_config(request: Request, app_id: str, plugin_manager: PluginManager) -> Response:
    """Render configuration for a Starlark app."""
    starlark_plugin = plugin_manager.get_plugin("starlark-apps")

    if starlark_plugin and hasattr(starlark_plugin, "apps"):
        app = starlark_plugin.apps.get(app_id)
        if not app:
            return HTMLResponse(
                content=f'<div class="text-red-500 p-4">Starlark app not found: {app_id}</div>',
                status_code=404,
            )
        return templates.TemplateResponse(
            "v3/partials/starlark_config.html",
            {
                "request": request,
                "app_id": app_id,
                "app_name": app.manifest.get("name", app_id),
                "app_enabled": app.is_enabled(),
                "render_interval": app.get_render_interval(),
                "display_duration": app.get_display_duration(),
                "config": app.config,
                "schema": app.schema,
                "has_frames": app.frames is not None,
                "frame_count": len(app.frames) if app.frames else 0,
                "last_render_time": app.last_render_time,
            },
        )

    # Standalone: read from manifest file
    manifest_file = PROJECT_ROOT / "starlark-apps" / "manifest.json"
    if not manifest_file.exists():
        return HTMLResponse(
            content=f'<div class="text-red-500 p-4">Starlark app not found: {app_id}</div>',
            status_code=404,
        )

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    app_data = manifest.get("apps", {}).get(app_id)
    if not app_data:
        return HTMLResponse(
            content=f'<div class="text-red-500 p-4">Starlark app not found: {app_id}</div>',
            status_code=404,
        )

    # Load schema and config from disk
    schema = None
    schema_file = PROJECT_ROOT / "starlark-apps" / app_id / "schema.json"
    if schema_file.exists():
        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load schema for {app_id}: {e}")

    config = {}
    config_file = PROJECT_ROOT / "starlark-apps" / app_id / "config.json"
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load config for {app_id}: {e}")

    return templates.TemplateResponse(
        "v3/partials/starlark_config.html",
        {
            "request": request,
            "app_id": app_id,
            "app_name": app_data.get("name", app_id),
            "app_enabled": app_data.get("enabled", True),
            "render_interval": app_data.get("render_interval", 300),
            "display_duration": app_data.get("display_duration", 15),
            "config": config,
            "schema": schema,
            "has_frames": False,
            "frame_count": 0,
            "last_render_time": None,
        },
    )


def _merge_image_metadata(plugin_id: str, plugins_dir: Path, config: dict) -> None:
    """Merge uploaded image metadata into plugin config if applicable."""
    schema_path = plugins_dir / plugin_id / "config_schema.json"
    if not schema_path.exists():
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        images_prop = schema.get("properties", {}).get("images", {})
        if images_prop.get("x-widget") != "file-upload" and images_prop.get("x_widget") != "file-upload":
            return

        metadata_file = PROJECT_ROOT / "assets" / "plugins" / plugin_id / "uploads" / ".metadata.json"
        if not metadata_file.exists():
            return

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        images_from_metadata = list(metadata.values())

        if not config.get("images"):
            config["images"] = images_from_metadata
        else:
            config_image_ids = {img.get("id") for img in config.get("images", []) if img.get("id")}
            new_images = [img for img in images_from_metadata if img.get("id") not in config_image_ids]
            if new_images:
                config["images"] = config.get("images", []) + new_images
    except Exception:
        pass
