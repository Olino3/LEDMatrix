"""Tests for FastAPI plugin routes (BACK-006)."""

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
            "test-plugin": {"enabled": True, "display_duration": 15},
        }
        mock_cm.save_config_atomic.return_value = MagicMock(status=MagicMock(value="success"))

        mock_pm = MagicMock()
        mock_pm.discover_plugins.return_value = None
        mock_pm.get_all_plugin_info.return_value = {
            "test-plugin": {"id": "test-plugin", "name": "Test", "version": "1.0.0"},
        }
        mock_pm.health_tracker = MagicMock()
        mock_pm.health_tracker.get_all_health_summaries.return_value = {"test-plugin": {"status": "healthy"}}
        mock_pm.health_tracker.get_health_summary.return_value = {"status": "healthy"}
        mock_pm.resource_monitor = MagicMock()
        mock_pm.resource_monitor.get_all_metrics_summaries.return_value = {}
        mock_pm.resource_monitor.get_metrics_summary.return_value = {}

        mock_sm = MagicMock()
        mock_sm.load_schema.return_value = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}

        mock_oq = MagicMock()
        mock_oh = MagicMock()
        mock_oh.get_history.return_value = []

        mock_psm = MagicMock()
        mock_psm.get_all_states.return_value = {}
        mock_psm.get_plugin_state.return_value = MagicMock(to_dict=lambda: {"enabled": True})

        mock_store = MagicMock()
        mock_saved = MagicMock()
        mock_saved.get_all.return_value = []

        app.state.config_manager = mock_cm
        app.state.plugin_manager = mock_pm
        app.state.schema_manager = mock_sm
        app.state.operation_queue = mock_oq
        app.state.operation_history = mock_oh
        app.state.plugin_state_manager = mock_psm
        app.state.plugin_store_manager = mock_store
        app.state.saved_repositories_manager = mock_saved
        app.state.health_monitor = None

        return TestClient(app), app


# ---------------------------------------------------------------------------
# Plugin CRUD
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPluginInstalled:
    def test_list_installed_plugins(self):
        client, app = _make_client()
        # get_all_plugin_info returns a dict of dicts; the route iterates values
        app.state.plugin_manager.get_all_plugin_info.return_value = {
            "test-plugin": {"id": "test-plugin", "name": "Test", "version": "1.0.0"},
        }
        resp = client.get("/api/v3/plugins/installed")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


@pytest.mark.unit
class TestPluginToggle:
    def test_toggle_plugin(self):
        client, app = _make_client()
        resp = client.post("/api/v3/plugins/toggle", json={"plugin_id": "test-plugin", "enabled": False})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


@pytest.mark.unit
class TestPluginConfig:
    def test_get_plugin_config(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/config", params={"plugin_id": "test-plugin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_get_plugin_config_missing_id(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/config")
        assert resp.status_code == 422  # FastAPI validation error for missing required query param

    def test_get_plugin_schema(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/schema", params={"plugin_id": "test-plugin"})
        assert resp.status_code == 200
        assert "schema" in resp.json().get("data", {}) or resp.json()["status"] == "success"


@pytest.mark.unit
class TestPluginConfigReset:
    def test_reset_config(self):
        client, app = _make_client()
        app.state.schema_manager.generate_default_config.return_value = {"enabled": True, "display_duration": 15}
        resp = client.post("/api/v3/plugins/config/reset", json={"plugin_id": "test-plugin"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Health / Metrics
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPluginHealth:
    def test_get_all_health(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/health")
        assert resp.status_code == 200

    def test_get_single_health(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/health/test-plugin")
        assert resp.status_code == 200

    def test_reset_health(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/health/test-plugin/reset")
        assert resp.status_code == 200


@pytest.mark.unit
class TestPluginMetrics:
    def test_get_all_metrics(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/metrics")
        assert resp.status_code == 200

    def test_get_single_metrics(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/metrics/test-plugin")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPluginOperations:
    def test_get_operation_history(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/operation/history")
        assert resp.status_code == 200

    def test_clear_operation_history(self):
        client, _ = _make_client()
        resp = client.delete("/api/v3/plugins/operation/history")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPluginState:
    def test_get_all_state(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/state")
        assert resp.status_code == 200

    def test_get_single_state(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/state", params={"plugin_id": "test-plugin"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPluginStore:
    def test_list_store(self):
        client, app = _make_client()
        app.state.plugin_store_manager.get_available_plugins.return_value = []
        resp = client.get("/api/v3/plugins/store/list")
        assert resp.status_code == 200

    def test_get_github_status(self):
        client, app = _make_client()
        app.state.plugin_store_manager.github_token = None  # No token → returns default
        resp = client.get("/api/v3/plugins/store/github-status")
        assert resp.status_code == 200
        assert resp.json()["data"]["authenticated"] is False

    def test_saved_repositories_list(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/saved-repositories")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestFonts:
    def test_get_tokens(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/fonts/tokens")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "tokens" in data

    def test_get_overrides(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/fonts/overrides")
        assert resp.status_code == 200

    def test_get_catalog(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/fonts/catalog")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestWifi:
    @patch("src.api.routers.wifi._get_wifi_manager")
    def test_get_wifi_status(self, mock_get_wm):
        from dataclasses import dataclass

        @dataclass
        class FakeStatus:
            connected: bool = True
            ssid: str = "test"
            ip_address: str = "1.2.3.4"
            signal_strength: int = -50

        mock_wm = MagicMock()
        mock_wm.get_wifi_status.return_value = FakeStatus()
        mock_get_wm.return_value = mock_wm
        client, _ = _make_client()
        resp = client.get("/api/v3/wifi/status")
        assert resp.status_code == 200

    @patch("src.api.routers.wifi._get_wifi_manager")
    def test_connect_wifi(self, mock_get_wm):
        mock_wm = MagicMock()
        mock_wm.connect_to_network.return_value = (True, "Connected")
        mock_get_wm.return_value = mock_wm
        client, _ = _make_client()
        resp = client.post("/api/v3/wifi/connect", json={"ssid": "mynet", "password": "pass"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Starlark
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestStarlark:
    def test_get_starlark_status(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/starlark/status")
        assert resp.status_code == 200

    def test_get_starlark_apps_not_installed(self):
        """When starlark plugin dir doesn't exist, returns 404."""
        client, _ = _make_client()
        resp = client.get("/api/v3/starlark/apps")
        # 404 is expected when starlark plugin is not installed
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Router importability
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRouterImports:
    def test_all_routers_importable(self):
        from src.api.routers.assets import router as ar
        from src.api.routers.fonts import router as fr
        from src.api.routers.plugins import router as pr
        from src.api.routers.starlark import router as str_r
        from src.api.routers.store import router as sr
        from src.api.routers.wifi import router as wr

        assert all(r is not None for r in [pr, sr, fr, wr, ar, str_r])

    def test_total_route_count(self):
        """Verify we have a meaningful number of routes across all routers."""
        from src.api.routers.assets import router as ar
        from src.api.routers.fonts import router as fr
        from src.api.routers.plugins import router as pr
        from src.api.routers.starlark import router as str_r
        from src.api.routers.store import router as sr
        from src.api.routers.wifi import router as wr

        total = sum(len(r.routes) for r in [pr, sr, fr, wr, ar, str_r])
        assert total >= 50, f"Expected at least 50 plugin routes, got {total}"
