"""FastAPI application factory and lifespan management."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from src.api.dependencies import init_services, shutdown_services
from src.api.middleware import register_middleware
from src.api.routers import (
    assets_router,
    config_router,
    fonts_router,
    pages_router,
    plugins_router,
    starlark_router,
    store_router,
    streams_router,
    system_router,
    wifi_router,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_INTERFACE_DIR = PROJECT_ROOT / "web_interface"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down application services."""
    init_services(app)
    yield
    shutdown_services(app)


def create_app() -> FastAPI:
    """Factory function that builds and returns the FastAPI application."""
    openapi_tags = [
        {"name": "config", "description": "Display and system configuration management"},
        {"name": "system", "description": "System status, health checks, and version info"},
        {"name": "plugins", "description": "Plugin lifecycle management — enable, disable, configure"},
        {"name": "store", "description": "Plugin store — browse, install, and update plugins"},
        {"name": "fonts", "description": "Font management for LED matrix text rendering"},
        {"name": "wifi", "description": "Wi-Fi network scanning and configuration"},
        {"name": "streams", "description": "Server-Sent Event streams for real-time updates"},
        {"name": "starlark", "description": "Starlark script evaluation and management"},
        {"name": "assets", "description": "Plugin static assets — logos, images, and files"},
        {"name": "pages", "description": "HTMX page routes for the web dashboard UI"},
    ]

    app = FastAPI(
        title="LEDMatrix API",
        description="LED Matrix display controller API",
        version="2.0.0",
        contact={"name": "LEDMatrix", "url": "https://github.com/Olino3/LEDMatrix"},
        license_info={"name": "MIT"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=openapi_tags,
        lifespan=lifespan,
    )

    # Register middleware stack (CORS, security, request ID, timing, caching, captive portal)
    register_middleware(app)

    # Include API routers under /api/v3 prefix
    app.include_router(config_router, prefix="/api/v3")
    app.include_router(system_router, prefix="/api/v3")
    app.include_router(plugins_router, prefix="/api/v3")
    app.include_router(store_router, prefix="/api/v3")
    app.include_router(fonts_router, prefix="/api/v3")
    app.include_router(wifi_router, prefix="/api/v3")
    app.include_router(assets_router, prefix="/api/v3")
    app.include_router(starlark_router, prefix="/api/v3")
    app.include_router(streams_router, prefix="/api/v3")

    # HTMX page routes (no /api/v3 prefix — served at /v3/)
    app.include_router(pages_router)

    # Mount static files from web_interface (kept during Phase 2-3 transition)
    static_dir = WEB_INTERFACE_DIR / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Root redirect to /v3 (matches current Flask behavior)
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/v3", status_code=307)

    # Favicon — return 204 No Content (matches current behavior)
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        from starlette.responses import Response

        return Response(status_code=204)

    return app


# Module-level app instance for `uvicorn src.api.main:app`
app = create_app()
