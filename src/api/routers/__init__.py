"""FastAPI router package — each module maps to a route group."""

from src.api.routers.assets import router as assets_router
from src.api.routers.config import router as config_router
from src.api.routers.fonts import router as fonts_router
from src.api.routers.plugins import router as plugins_router
from src.api.routers.starlark import router as starlark_router
from src.api.routers.store import router as store_router
from src.api.routers.streams import router as streams_router
from src.api.routers.system import router as system_router
from src.api.routers.pages import router as pages_router
from src.api.routers.wifi import router as wifi_router

__all__ = [
    "assets_router",
    "config_router",
    "fonts_router",
    "pages_router",
    "plugins_router",
    "starlark_router",
    "store_router",
    "streams_router",
    "system_router",
    "wifi_router",
]
