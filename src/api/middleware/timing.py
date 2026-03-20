"""Request timing middleware — logs duration of each request."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.logging_config import get_logger

logger = get_logger("api.timing")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Measure request duration and log it."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        logger.debug(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
