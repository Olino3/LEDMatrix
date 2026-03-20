"""Tests for HTMX page routes served via FastAPI (SPIKE-002)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    """Create a test client with mocked services."""
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()

        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {
            "schedule": {},
            "dim_schedule": {},
            "display": {
                "hardware": {
                    "brightness": 90,
                    "rows": 32,
                    "cols": 64,
                    "chain_length": 2,
                    "parallel": 1,
                    "hardware_mapping": "adafruit-hat-pwm",
                },
                "runtime": {"gpio_slowdown": 3},
                "display_durations": {},
            },
            "location": {"city": "Test", "state": "TX", "country": "US"},
            "timezone": "UTC",
            "plugin_system": {},
            "weather": {},
            "stocks": {},
        }
        mock_cm.get_raw_file_content.return_value = {}
        mock_cm.get_config_path.return_value = "/tmp/config.json"
        mock_cm.get_secrets_path.return_value = "/tmp/secrets.json"

        mock_pm = MagicMock()
        mock_pm.get_all_plugin_info.return_value = []
        mock_pm.plugins_dir = "/tmp/plugins"

        mock_psm = MagicMock()

        app.state.config_manager = mock_cm
        app.state.plugin_manager = mock_pm
        app.state.plugin_store_manager = mock_psm

        return TestClient(app)


@pytest.mark.unit
class TestIndexPage:
    def test_index_returns_html(self):
        client = _make_client()
        resp = client.get("/v3/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_index_contains_expected_content(self):
        client = _make_client()
        resp = client.get("/v3/")
        assert b"LED Matrix" in resp.content


@pytest.mark.unit
class TestPartials:
    def test_overview_partial(self):
        client = _make_client()
        resp = client.get("/v3/partials/overview")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_unknown_partial_returns_404(self):
        client = _make_client()
        resp = client.get("/v3/partials/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.parametrize("partial", [
        "general", "display", "durations", "schedule",
        "plugins", "fonts", "logs", "raw-json",
        "wifi", "cache", "operation-history",
    ])
    def test_all_partials_return_200(self, partial):
        client = _make_client()
        resp = client.get(f"/v3/partials/{partial}")
        assert resp.status_code == 200
