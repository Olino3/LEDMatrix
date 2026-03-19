"""Shared dependency injection for the FastAPI application.

Services are initialized once in the lifespan and stored on `app.state`.
Route handlers access them via FastAPI's `Depends()` pattern.
"""

from pathlib import Path

from fastapi import FastAPI, Request

from src.config_manager import ConfigManager
from src.plugin_system.operation_history import OperationHistory
from src.plugin_system.operation_queue import PluginOperationQueue
from src.plugin_system.plugin_manager import PluginManager
from src.plugin_system.saved_repositories import SavedRepositoriesManager
from src.plugin_system.schema_manager import SchemaManager
from src.plugin_system.state_manager import PluginStateManager
from src.plugin_system.store_manager import PluginStoreManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def init_services(app: FastAPI) -> None:
    """Initialize all services and store them on app.state."""
    config_manager = ConfigManager()
    config = config_manager.load_config()
    plugin_system_config = config.get("plugin_system", {})
    plugins_dir_name = plugin_system_config.get("plugins_directory", "plugin-repos")

    if Path(plugins_dir_name).is_absolute():
        plugins_dir = Path(plugins_dir_name)
    else:
        plugins_dir = PROJECT_ROOT / plugins_dir_name

    app.state.config_manager = config_manager
    app.state.plugin_manager = PluginManager(
        plugins_dir=str(plugins_dir),
        config_manager=config_manager,
        display_manager=None,
        cache_manager=None,
    )
    app.state.plugin_store_manager = PluginStoreManager(plugins_dir=str(plugins_dir))
    app.state.saved_repositories_manager = SavedRepositoriesManager()
    app.state.schema_manager = SchemaManager(
        plugins_dir=plugins_dir,
        project_root=PROJECT_ROOT,
        logger=None,
    )
    app.state.operation_queue = PluginOperationQueue(
        history_file=str(PROJECT_ROOT / "data" / "plugin_operations.json"),
        max_history=500,
        lazy_load=True,
    )
    app.state.plugin_state_manager = PluginStateManager(
        state_file=str(PROJECT_ROOT / "data" / "plugin_state.json"),
        auto_save=True,
        lazy_load=True,
    )
    app.state.operation_history = OperationHistory(
        history_file=str(PROJECT_ROOT / "data" / "operation_history.json"),
        max_records=1000,
        lazy_load=True,
    )
    app.state.health_monitor = None


def shutdown_services(app: FastAPI) -> None:
    """Clean up services on application shutdown."""
    if getattr(app.state, "health_monitor", None) is not None:
        try:
            app.state.health_monitor.stop()
        except Exception:
            pass


# --- Dependency callables for use with FastAPI Depends() ---


def get_config_manager(request: Request) -> ConfigManager:
    return request.app.state.config_manager


def get_plugin_manager(request: Request) -> PluginManager:
    return request.app.state.plugin_manager


def get_plugin_store_manager(request: Request) -> PluginStoreManager:
    return request.app.state.plugin_store_manager


def get_schema_manager(request: Request) -> SchemaManager:
    return request.app.state.schema_manager


def get_operation_queue(request: Request) -> PluginOperationQueue:
    return request.app.state.operation_queue


def get_plugin_state_manager(request: Request) -> PluginStateManager:
    return request.app.state.plugin_state_manager


def get_operation_history(request: Request) -> OperationHistory:
    return request.app.state.operation_history


def get_saved_repositories_manager(request: Request) -> SavedRepositoriesManager:
    return request.app.state.saved_repositories_manager
