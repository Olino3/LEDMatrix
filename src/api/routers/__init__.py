"""FastAPI router package — each module maps to a route group."""

from src.api.routers.config import router as config_router
from src.api.routers.system import router as system_router

__all__ = ["config_router", "system_router"]
