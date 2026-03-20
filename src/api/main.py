"""FastAPI application factory and lifespan management."""

import mimetypes
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse, Response

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
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/v3", status_code=307)

    # Favicon — return 204 No Content (matches current behavior)
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    # Mount Angular SPA (when built) — single catch-all serves both
    # static assets and index.html fallback for client-side routing.
    # Computed inside create_app() so PROJECT_ROOT can be patched in tests.
    spa_dist_dir = PROJECT_ROOT / "frontend" / "dist" / "ledmatrix" / "browser"
    if spa_dist_dir.is_dir():
        _SPA_RESERVED_PREFIXES = (
            "/api/", "/docs", "/redoc", "/static", "/v3",
            "/openapi.json", "/favicon.ico",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_catch_all(full_path: str) -> Response:
            """Serve SPA static files or index.html for client-side routing."""
            request_path = f"/{full_path}"
            for prefix in _SPA_RESERVED_PREFIXES:
                if request_path.startswith(prefix):
                    return Response(status_code=404)

            # Serve static file if it exists (JS, CSS, images, etc.)
            if full_path and ".." not in full_path:
                file_path = spa_dist_dir / full_path
                if file_path.is_file():
                    media_type = mimetypes.guess_type(str(file_path))[0]
                    return FileResponse(file_path, media_type=media_type)

            # Fall back to index.html for Angular client-side routing
            index_file = spa_dist_dir / "index.html"
            if index_file.is_file():
                return HTMLResponse(content=index_file.read_text())
            return Response(status_code=404)

    return app


# Module-level app instance for `uvicorn src.api.main:app`
app = create_app()
