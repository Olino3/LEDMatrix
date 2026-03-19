"""FastAPI middleware stack for the LED Matrix web interface."""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.middleware.caching import CachingMiddleware
from src.api.middleware.captive_portal import CaptivePortalMiddleware
from src.api.middleware.request_id import RequestIdMiddleware
from src.api.middleware.security import SecurityHeadersMiddleware
from src.api.middleware.timing import RequestTimingMiddleware

# Default CORS origins — localhost dev servers for Angular (Phase 3) and current Flask
DEFAULT_CORS_ORIGINS = [
    "http://localhost:4200",
    "http://localhost:5000",
]


def register_middleware(app: FastAPI, *, cors_origins: list[str] | None = None) -> None:
    """Register all middleware on the FastAPI app.

    Order matters — middleware added last runs first on the request path.
    We add in reverse priority so the outermost (first to run) is CORS.
    """
    # Added last → runs first on request
    app.add_middleware(CaptivePortalMiddleware)
    app.add_middleware(CachingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or DEFAULT_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
