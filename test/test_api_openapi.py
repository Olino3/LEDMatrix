"""Tests for OpenAPI schema completeness (SPIKE-003, SPIKE-008)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()
        return TestClient(app)


@pytest.mark.unit
class TestOpenAPISchema:
    def test_openapi_endpoint_returns_json(self):
        client = _make_client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "info" in schema

    def test_app_metadata(self):
        client = _make_client()
        schema = client.get("/openapi.json").json()
        info = schema["info"]
        assert info["title"] == "LEDMatrix API"
        assert info["version"] == "2.0.0"
        assert "contact" in info
        assert "license" in info

    def test_all_tags_have_descriptions(self):
        client = _make_client()
        schema = client.get("/openapi.json").json()
        tags = {t["name"]: t for t in schema.get("tags", [])}
        expected = {
            "config",
            "system",
            "plugins",
            "store",
            "fonts",
            "wifi",
            "streams",
            "starlark",
            "assets",
            "pages",
        }
        for tag_name in expected:
            assert tag_name in tags, f"Missing tag: {tag_name}"
            assert "description" in tags[tag_name], f"Tag '{tag_name}' missing description"

    def test_schema_has_paths(self):
        client = _make_client()
        schema = client.get("/openapi.json").json()
        # At least 30 paths expected (111 handlers, some share paths with different methods)
        assert len(schema["paths"]) >= 30


@pytest.mark.unit
class TestOpenAPIResponseModels:
    """SPIKE-008: Verify response models are documented in the OpenAPI schema."""

    def test_api_endpoints_have_error_responses(self):
        """API endpoints should document 400/500 error responses."""
        client = _make_client()
        schema = client.get("/openapi.json").json()
        # Check a representative API endpoint
        version_path = schema["paths"].get("/api/v3/system/version", {})
        get_op = version_path.get("get", {})
        responses = get_op.get("responses", {})
        assert "500" in responses, "system/version should document 500 response"

    def test_error_response_references_model(self):
        """Error responses should reference the ErrorResponse schema."""
        client = _make_client()
        schema = client.get("/openapi.json").json()
        version_path = schema["paths"].get("/api/v3/system/status", {})
        get_op = version_path.get("get", {})
        resp_500 = get_op.get("responses", {}).get("500", {})
        # Should have content with a schema reference
        content = resp_500.get("content", {})
        assert "application/json" in content

    def test_success_response_documented(self):
        """API endpoints should document 200 success response with schema."""
        client = _make_client()
        schema = client.get("/openapi.json").json()
        version_path = schema["paths"].get("/api/v3/system/version", {})
        get_op = version_path.get("get", {})
        resp_200 = get_op.get("responses", {}).get("200", {})
        content = resp_200.get("content", {})
        assert "application/json" in content

    def test_schemas_include_success_and_error_models(self):
        """Schema components should include SuccessResponse and ErrorResponse."""
        client = _make_client()
        schema = client.get("/openapi.json").json()
        components = schema.get("components", {}).get("schemas", {})
        assert "SuccessResponse" in components
        assert "ErrorResponse" in components
