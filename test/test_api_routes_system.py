"""Tests for FastAPI system routes (BACK-005)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    """Create a test client with mocked services."""
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()

        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {"schedule": {}}

        mock_pm = MagicMock()
        mock_pm.get_available_plugins.return_value = [{"id": "clock"}, {"id": "weather"}]

        app.state.config_manager = mock_cm
        app.state.plugin_manager = mock_pm

        return TestClient(app), mock_cm, mock_pm


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSystemStatus:
    @patch("src.api.routers.system._get_display_service_status")
    def test_system_status_returns_metrics(self, mock_svc):
        mock_svc.return_value = {"active": False, "returncode": 3, "stdout": "inactive", "stderr": ""}
        client, _, _ = _make_client()
        resp = client.get("/api/v3/system/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cpu_percent" in data
        assert "memory_used_percent" in data
        assert "disk_used_percent" in data
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# System version
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSystemVersion:
    @patch("src.api.routers.system._get_git_version", return_value="v2.0.0-test")
    def test_version_returns_info(self, mock_git):
        client, _, _ = _make_client()
        resp = client.get("/api/v3/system/version")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["version"] == "v2.0.0-test"
        assert "python_version" in data
        assert "platform" in data


# ---------------------------------------------------------------------------
# System action
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSystemAction:
    @patch("src.api.routers.system._run_cmd")
    def test_valid_action(self, mock_run):
        mock_run.return_value = (0, "ok", "")
        client, _, _ = _make_client()
        resp = client.post("/api/v3/system/action", json={"action": "stop_display"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_missing_action(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/system/action", json={})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_unknown_action(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/system/action", json={"action": "destroy_everything"})
        assert resp.status_code == 400

    @patch("src.api.routers.system._run_cmd")
    def test_git_pull_action(self, mock_run):
        # First call: git status (no changes), second call: git pull
        mock_run.side_effect = [
            (0, "", ""),   # git status --porcelain
            (0, "Already up to date.", ""),  # git pull
        ]
        client, _, _ = _make_client()
        resp = client.post("/api/v3/system/action", json={"action": "git_pull"})
        assert resp.status_code == 200
        assert "updated" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestHealth:
    @patch("src.api.routers.system._get_display_service_status")
    def test_health_returns_checks(self, mock_svc):
        mock_svc.return_value = {"active": True, "returncode": 0, "stdout": "active", "stderr": ""}
        client, _, _ = _make_client()
        resp = client.get("/api/v3/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] in ("healthy", "degraded")
        assert "web_interface" in data["checks"]
        assert "config_file" in data["checks"]
        assert "plugin_system" in data["checks"]

    @patch("src.api.routers.system._get_display_service_status")
    def test_health_degraded_on_config_error(self, mock_svc):
        mock_svc.return_value = {"active": False, "returncode": 3, "stdout": "", "stderr": ""}
        client, cm, _ = _make_client()
        cm.load_config.side_effect = RuntimeError("corrupt")
        resp = client.get("/api/v3/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "degraded"


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestLogs:
    @patch("src.api.routers.system._run_cmd")
    def test_get_logs_success(self, mock_run):
        mock_run.return_value = (0, "Mar 19 12:00:00 pi ledmatrix[123]: running", "")
        client, _, _ = _make_client()
        resp = client.get("/api/v3/logs")
        assert resp.status_code == 200
        assert "logs" in resp.json()["data"]

    @patch("src.api.routers.system._run_cmd")
    def test_get_logs_timeout(self, mock_run):
        mock_run.return_value = (-1, "", "Command timed out")
        client, _, _ = _make_client()
        resp = client.get("/api/v3/logs")
        assert resp.status_code == 504


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestErrors:
    @patch("src.api.routers.system._get_aggregator")
    def test_error_summary(self, mock_agg):
        mock_agg.return_value.get_error_summary.return_value = {"total_errors": 5}
        client, _, _ = _make_client()
        resp = client.get("/api/v3/errors/summary")
        assert resp.status_code == 200
        assert resp.json()["data"]["total_errors"] == 5

    @patch("src.api.routers.system._get_aggregator")
    def test_plugin_errors(self, mock_agg):
        mock_agg.return_value.get_plugin_health.return_value = {"plugin_id": "weather", "status": "healthy"}
        client, _, _ = _make_client()
        resp = client.get("/api/v3/errors/plugin/weather")
        assert resp.status_code == 200
        assert resp.json()["data"]["plugin_id"] == "weather"

    @patch("src.api.routers.system._get_aggregator")
    def test_clear_errors(self, mock_agg):
        mock_agg.return_value.clear_old_records.return_value = 10
        client, _, _ = _make_client()
        resp = client.post("/api/v3/errors/clear", json={"max_age_hours": 48})
        assert resp.status_code == 200
        assert resp.json()["data"]["cleared_count"] == 10

    def test_clear_errors_invalid_age(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/errors/clear", json={"max_age_hours": 0})
        assert resp.status_code == 400

    def test_clear_errors_exceeds_max(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/errors/clear", json={"max_age_hours": 9999})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Router importability
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRouterImports:
    def test_config_router_has_routes(self):
        from src.api.routers.config import router
        assert len(router.routes) >= 9  # 9 config endpoints

    def test_system_router_has_routes(self):
        from src.api.routers.system import router
        assert len(router.routes) >= 8  # system + health + logs + errors
