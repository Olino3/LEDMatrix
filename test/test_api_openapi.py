"""Tests for OpenAPI schema completeness (SPIKE-003)."""

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
