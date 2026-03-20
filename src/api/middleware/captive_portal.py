"""Captive portal middleware — redirects to /v3 when AP mode is active."""

import subprocess

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

# Paths that should NOT be redirected when AP mode is active
_ALLOWED_PREFIXES = (
    "/v3",
    "/api/v3/",
    "/static/",
    "/hotspot-detect.html",
    "/generate_204",
    "/connecttest.txt",
    "/success.txt",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _is_ap_mode_active() -> bool:
    """Check if hostapd (AP mode) is running."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "hostapd"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.returncode == 0 and result.stdout.strip() == "active"
    except Exception:
        return False


class CaptivePortalMiddleware(BaseHTTPMiddleware):
    """Redirect all requests to /v3 when the Pi is in AP mode, except allowed paths."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _is_ap_mode_active():
            path = request.url.path
            if not any(path.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
                return RedirectResponse(url="/v3", status_code=302)
        return await call_next(request)
