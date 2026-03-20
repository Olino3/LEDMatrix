"""Caching headers middleware — sets Cache-Control based on request path."""

from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CachingMiddleware(BaseHTTPMiddleware):
    """Set cache headers matching the existing Flask behaviour."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        path = request.url.path

        if path.startswith("/static/"):
            # Static assets — cache 1 year (versioned via query params)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            expires = datetime.now(timezone.utc) + timedelta(days=365)
            response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        elif path.startswith("/api/v3/"):
            # API GET responses (except streams) — short cache
            if request.method == "GET" and "stream" not in path:
                response.headers["Cache-Control"] = "private, max-age=5, must-revalidate"
        else:
            # HTML pages — no cache
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response
