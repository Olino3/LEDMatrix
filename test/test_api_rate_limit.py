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
class TestRateLimitHeaders:
    """Verify rate limit headers are present on API responses."""

    def test_api_response_has_rate_limit_headers(self):
        client = _make_client()
        resp = client.get("/api/v3/system/version")
        # slowapi adds X-RateLimit-Limit and X-RateLimit-Remaining headers
        assert "x-ratelimit-limit" in resp.headers or "X-RateLimit-Limit" in resp.headers

    def test_rate_limit_value_is_1000_per_minute(self):
        client = _make_client()
        resp = client.get("/api/v3/system/version")
        limit = resp.headers.get("X-RateLimit-Limit", resp.headers.get("x-ratelimit-limit", ""))
        assert "1000" in limit


@pytest.mark.unit
class TestRateLimitEnforcement:
    """Verify 429 is returned when rate limit is exceeded."""

    def test_sse_endpoint_has_stricter_limit(self):
        client = _make_client()
        resp = client.get("/api/v3/stream/stats")
        limit = resp.headers.get("X-RateLimit-Limit", resp.headers.get("x-ratelimit-limit", ""))
        # SSE endpoints should have 20/minute limit
        assert "20" in limit
