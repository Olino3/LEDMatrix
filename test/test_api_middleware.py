"""Tests for the FastAPI middleware stack (BACK-004)."""

import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import register_middleware


def _make_app(**middleware_kwargs) -> FastAPI:
    """Create a minimal FastAPI app with middleware registered."""
    app = FastAPI()
    register_middleware(app, **middleware_kwargs)

    @app.get("/")
    async def root():
        return {"ok": True}

    @app.get("/api/v3/status")
    async def api_status():
        return {"status": "running"}

    @app.get("/v3/page")
    async def page():
        return {"page": True}

    return app


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSecurityHeaders:
    def test_security_headers_present(self):
        client = TestClient(_make_app())
        resp = client.get("/")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRequestId:
    def test_request_id_in_response_header(self):
        client = TestClient(_make_app())
        resp = client.get("/")
        request_id = resp.headers.get("X-Request-Id")
        assert request_id is not None
        # Should be a valid UUID
        uuid.UUID(request_id)

    def test_request_ids_are_unique(self):
        client = TestClient(_make_app())
        id1 = client.get("/").headers["X-Request-Id"]
        id2 = client.get("/").headers["X-Request-Id"]
        assert id1 != id2


# ---------------------------------------------------------------------------
# Request timing
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRequestTiming:
    def test_response_time_header_present(self):
        client = TestClient(_make_app())
        resp = client.get("/")
        rt = resp.headers.get("X-Response-Time")
        assert rt is not None
        assert rt.endswith("ms")


# ---------------------------------------------------------------------------
# Caching headers
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCachingHeaders:
    def test_api_get_has_short_cache(self):
        client = TestClient(_make_app())
        resp = client.get("/api/v3/status")
        assert "max-age=5" in resp.headers.get("Cache-Control", "")

    def test_html_page_has_no_cache(self):
        client = TestClient(_make_app())
        resp = client.get("/v3/page")
        assert "no-cache" in resp.headers.get("Cache-Control", "")
        assert resp.headers.get("Pragma") == "no-cache"

    def test_root_has_no_cache(self):
        client = TestClient(_make_app())
        resp = client.get("/", follow_redirects=False)
        # Root is a non-static, non-API path
        cc = resp.headers.get("Cache-Control", "")
        assert "no-cache" in cc or resp.status_code == 307


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCORS:
    def test_cors_allows_configured_origin(self):
        client = TestClient(_make_app())
        resp = client.options(
            "/api/v3/status",
            headers={
                "Origin": "http://localhost:4200",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:4200"

    def test_cors_rejects_unknown_origin(self):
        client = TestClient(_make_app())
        resp = client.options(
            "/api/v3/status",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette CORS middleware omits the header for disallowed origins
        assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"

    def test_cors_custom_origins(self):
        client = TestClient(_make_app(cors_origins=["http://custom:9000"]))
        resp = client.options(
            "/api/v3/status",
            headers={
                "Origin": "http://custom:9000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://custom:9000"


# ---------------------------------------------------------------------------
# Captive portal
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCaptivePortal:
    @patch("src.api.middleware.captive_portal._is_ap_mode_active", return_value=True)
    def test_redirects_unknown_path_in_ap_mode(self, mock_ap):
        client = TestClient(_make_app(), follow_redirects=False)
        resp = client.get("/some-random-page")
        assert resp.status_code == 302
        assert resp.headers["location"] == "/v3"

    @patch("src.api.middleware.captive_portal._is_ap_mode_active", return_value=True)
    def test_allows_v3_in_ap_mode(self, mock_ap):
        client = TestClient(_make_app())
        resp = client.get("/v3/page")
        assert resp.status_code == 200

    @patch("src.api.middleware.captive_portal._is_ap_mode_active", return_value=True)
    def test_allows_api_in_ap_mode(self, mock_ap):
        client = TestClient(_make_app())
        resp = client.get("/api/v3/status")
        assert resp.status_code == 200

    @patch("src.api.middleware.captive_portal._is_ap_mode_active", return_value=False)
    def test_no_redirect_when_ap_inactive(self, mock_ap):
        client = TestClient(_make_app())
        resp = client.get("/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# register_middleware importability
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRegisterMiddleware:
    def test_register_middleware_importable(self):
        from src.api.middleware import register_middleware
        assert callable(register_middleware)

    def test_individual_middleware_importable(self):
        from src.api.middleware.caching import CachingMiddleware
        from src.api.middleware.captive_portal import CaptivePortalMiddleware
        from src.api.middleware.request_id import RequestIdMiddleware
        from src.api.middleware.security import SecurityHeadersMiddleware
        from src.api.middleware.timing import RequestTimingMiddleware
        assert all(callable(cls) for cls in [
            SecurityHeadersMiddleware, RequestIdMiddleware,
            RequestTimingMiddleware, CachingMiddleware, CaptivePortalMiddleware,
        ])
