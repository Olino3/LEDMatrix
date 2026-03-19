"""FastAPI application factory and lifespan management."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from src.api.dependencies import init_services, shutdown_services

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
    app = FastAPI(
        title="LED Matrix",
        description="LED Matrix display controller API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

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
