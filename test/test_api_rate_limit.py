"""Tests for FastAPI rate limiting via slowapi (SPIKE-006)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()
        return TestClient(app)


@pytest.mark.unit
class TestRateLimitSetup:
    """Verify rate limiter is properly wired into the app."""

    def test_app_has_limiter_on_state(self):
        with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
            from src.api.main import create_app

            app = create_app()
            assert hasattr(app.state, "limiter")

    def test_limiter_has_default_limits(self):
        from src.api.middleware.rate_limit import limiter

        assert limiter._default_limits is not None
        assert len(limiter._default_limits) > 0

    def test_rate_limit_exceeded_handler_registered(self):
        with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
            from slowapi.errors import RateLimitExceeded

            from src.api.main import create_app

            app = create_app()
            assert RateLimitExceeded in app.exception_handlers


@pytest.mark.unit
class TestSSERateLimits:
    """Verify SSE endpoints have stricter per-route limits."""

    def test_stream_stats_has_20_per_minute_limit(self):
        from src.api.middleware.rate_limit import limiter

        key = "src.api.routers.streams.stream_stats"
        assert key in limiter._route_limits
        limit_str = str(limiter._route_limits[key][0].limit)
        assert "20" in limit_str

    def test_stream_display_has_20_per_minute_limit(self):
        from src.api.middleware.rate_limit import limiter

        key = "src.api.routers.streams.stream_display"
        assert key in limiter._route_limits
        limit_str = str(limiter._route_limits[key][0].limit)
        assert "20" in limit_str

    def test_stream_logs_has_20_per_minute_limit(self):
        from src.api.middleware.rate_limit import limiter

        key = "src.api.routers.streams.stream_logs"
        assert key in limiter._route_limits
        limit_str = str(limiter._route_limits[key][0].limit)
        assert "20" in limit_str

    def test_non_sse_route_not_in_route_limits(self):
        """Non-SSE routes use the default 1000/min, not per-route limits."""
        from src.api.middleware.rate_limit import limiter

        # system.version should NOT have a per-route limit
        for key in limiter._route_limits:
            assert "system" not in key


@pytest.mark.unit
class TestRateLimitResponse:
    """Verify regular API endpoints still work with limiter active."""

    def test_api_endpoint_returns_200_with_limiter(self):
        client = _make_client()
        resp = client.get("/api/v3/system/version")
        assert resp.status_code == 200
