"""Plugin store API routes — /plugins/store/*, install, update, uninstall endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_operation_queue,
    get_plugin_manager,
    get_plugin_state_manager,
    get_plugin_store_manager,
    get_saved_repositories_manager,
)
from src.logging_config import get_logger
from src.plugin_system.operation_queue import PluginOperationQueue
from src.plugin_system.plugin_manager import PluginManager
from src.plugin_system.saved_repositories import SavedRepositoriesManager
from src.plugin_system.state_manager import PluginStateManager
from src.plugin_system.store_manager import PluginStoreManager

logger = get_logger("api.store")

router = APIRouter(prefix="/plugins", tags=["store"])


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


# ---- store browsing ---------------------------------------------------------


@router.get("/store/list")
async def list_store_plugins(
    query: str = Query("", description="Search query"),
    category: str = Query("", description="Filter by category"),
    tags: str = Query("", description="Comma-separated tags"),
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
    saved_repos: SavedRepositoriesManager = Depends(get_saved_repositories_manager),
):
    """List available plugins from the store registry."""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        plugins = store_manager.search_plugins(
            query=query,
            category=category,
            tags=tag_list,
            fetch_commit_info=True,
            include_saved_repos=True,
            saved_repositories_manager=saved_repos,
        )
        return _success(data=plugins)
    except Exception as exc:
        logger.error("Failed to list store plugins: %s", exc)
        return _error("STORE_LIST_FAILED", str(exc), 500)


@router.get("/store/github-status")
async def get_github_auth_status(
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
):
    """Check GitHub API authentication status and rate limit."""
    try:
        token = store_manager.github_token
        if not token:
            return _success(
                data={
                    "token_status": "none",
                    "authenticated": False,
                    "rate_limit": 60,
                    "message": "No GitHub token configured",
                    "error": None,
                }
            )

        is_valid, error_message = store_manager._validate_github_token(token)
        if is_valid:
            return _success(
                data={
                    "token_status": "valid",
                    "authenticated": True,
                    "rate_limit": 5000,
                    "message": "GitHub API authenticated",
                    "error": None,
                }
            )
        return _success(
            data={
                "token_status": "invalid",
                "authenticated": False,
                "rate_limit": 60,
                "message": (
                    f"GitHub token is invalid: {error_message}" if error_message else "GitHub token is invalid"
                ),
                "error": error_message,
            }
        )
    except Exception as exc:
        return _error("GITHUB_STATUS_FAILED", str(exc), 500)


@router.post("/store/refresh")
async def refresh_store(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
):
    """Force refresh the plugin registry from GitHub."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        registry = store_manager.fetch_registry(force_refresh=True)
        plugin_count = len(registry.get("plugins", []))
        fetch_commit_info = body.get("fetch_commit_info", body.get("fetch_latest_versions", False))
        message = "Plugin store refreshed"
        if fetch_commit_info:
            message += " (with refreshed commit metadata from GitHub)"
        return _success(data={"plugin_count": plugin_count}, message=message)
    except Exception as exc:
        return _error("STORE_REFRESH_FAILED", str(exc), 500)


# ---- install / update / uninstall ------------------------------------------


@router.post("/install")
async def install_plugin(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
    state_manager: PluginStateManager = Depends(get_plugin_state_manager),
    operation_queue: PluginOperationQueue = Depends(get_operation_queue),
):
    """Install a plugin from the official registry."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    plugin_id = body.get("plugin_id")
    branch = body.get("branch")
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id'")

    try:
        success = store_manager.install_plugin(plugin_id, branch=branch)
        if success:
            state_manager.set_plugin_installed(plugin_id)
            return _success(message=f"Plugin '{plugin_id}' installed successfully")
        return _error(
            "INSTALL_FAILED",
            f"Failed to install plugin '{plugin_id}'",
            500,
        )
    except Exception as exc:
        logger.error("Failed to install plugin %s: %s", plugin_id, exc)
        return _error("INSTALL_FAILED", str(exc), 500)


@router.post("/install-from-url")
async def install_from_url(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
    state_manager: PluginStateManager = Depends(get_plugin_state_manager),
):
    """Install a plugin from a custom GitHub URL."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    repo_url = body.get("repo_url")
    plugin_id = body.get("plugin_id")
    plugin_path = body.get("plugin_path")
    branch = body.get("branch")
    if not repo_url:
        return _error("INVALID_INPUT", "Missing 'repo_url'")

    try:
        success = store_manager.install_from_url(
            repo_url=repo_url,
            plugin_id=plugin_id,
            plugin_path=plugin_path,
            branch=branch,
        )
        if success:
            if plugin_id:
                state_manager.set_plugin_installed(plugin_id)
            return _success(message=f"Plugin installed from {repo_url}")
        return _error("INSTALL_FAILED", "Failed to install plugin from URL", 500)
    except Exception as exc:
        logger.error("Failed to install from URL %s: %s", repo_url, exc)
        return _error("INSTALL_FAILED", str(exc), 500)


@router.post("/update")
async def update_plugin(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
    state_manager: PluginStateManager = Depends(get_plugin_state_manager),
):
    """Update an installed plugin to the latest version."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    plugin_id = body.get("plugin_id")
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id'")

    try:
        success = store_manager.update_plugin(plugin_id)
        if success:
            return _success(message=f"Plugin '{plugin_id}' updated successfully")
        return _error(
            "UPDATE_FAILED",
            f"Failed to update plugin '{plugin_id}'",
            500,
        )
    except Exception as exc:
        logger.error("Failed to update plugin %s: %s", plugin_id, exc)
        return _error("UPDATE_FAILED", str(exc), 500)


@router.post("/uninstall")
async def uninstall_plugin(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
    state_manager: PluginStateManager = Depends(get_plugin_state_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    """Uninstall a plugin."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    plugin_id = body.get("plugin_id")
    if not plugin_id:
        return _error("INVALID_INPUT", "Missing 'plugin_id'")

    try:
        success = store_manager.uninstall_plugin(plugin_id)
        if success:
            state_manager.remove_plugin_state(plugin_id)
            return _success(message=f"Plugin '{plugin_id}' uninstalled successfully")
        return _error(
            "UNINSTALL_FAILED",
            f"Failed to uninstall plugin '{plugin_id}'",
            500,
        )
    except Exception as exc:
        logger.error("Failed to uninstall plugin %s: %s", plugin_id, exc)
        return _error("UNINSTALL_FAILED", str(exc), 500)


# ---- registry from URL ------------------------------------------------------


@router.post("/registry-from-url")
async def get_registry_from_url(
    request: Request,
    store_manager: PluginStoreManager = Depends(get_plugin_store_manager),
):
    """Fetch a plugin registry from a custom GitHub repo URL."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    repo_url = body.get("repo_url")
    if not repo_url:
        return _error("INVALID_INPUT", "Missing 'repo_url'")

    try:
        registry = store_manager.fetch_registry_from_url(repo_url)
        if registry is None:
            return _error(
                "REGISTRY_NOT_FOUND",
                f"No registry found at {repo_url}",
                404,
            )
        return _success(data=registry)
    except Exception as exc:
        return _error("REGISTRY_FETCH_FAILED", str(exc), 500)


# ---- saved repositories ----------------------------------------------------


@router.get("/saved-repositories")
async def list_saved_repositories(
    saved_repos: SavedRepositoriesManager = Depends(get_saved_repositories_manager),
):
    """Return all saved repositories."""
    try:
        repos = saved_repos.get_all()
        return _success(data=repos)
    except Exception as exc:
        return _error("REPOS_FETCH_FAILED", str(exc), 500)


@router.post("/saved-repositories")
async def add_saved_repository(
    request: Request,
    saved_repos: SavedRepositoriesManager = Depends(get_saved_repositories_manager),
):
    """Add a saved repository."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    repo_url = body.get("repo_url")
    name = body.get("name")
    if not repo_url:
        return _error("INVALID_INPUT", "Missing 'repo_url'")

    try:
        success = saved_repos.add(repo_url, name=name)
        if success:
            return _success(message=f"Repository '{repo_url}' saved")
        return _error("REPO_ADD_FAILED", "Repository may already be saved", 409)
    except Exception as exc:
        return _error("REPO_ADD_FAILED", str(exc), 500)


@router.delete("/saved-repositories")
async def remove_saved_repository(
    request: Request,
    saved_repos: SavedRepositoriesManager = Depends(get_saved_repositories_manager),
):
    """Remove a saved repository."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    repo_url = body.get("repo_url")
    if not repo_url:
        return _error("INVALID_INPUT", "Missing 'repo_url'")

    try:
        success = saved_repos.remove(repo_url)
        if success:
            return _success(message=f"Repository '{repo_url}' removed")
        return _error("REPO_NOT_FOUND", "Repository not found", 404)
    except Exception as exc:
        return _error("REPO_REMOVE_FAILED", str(exc), 500)
