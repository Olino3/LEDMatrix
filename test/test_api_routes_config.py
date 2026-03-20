"""Tests for FastAPI config routes (BACK-005)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    """Create a test client with mocked services."""
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()

        # Inject mock services into app.state
        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {
            "schedule": {"enabled": True, "mode": "global", "start_time": "07:00", "end_time": "23:00"},
            "dim_schedule": {"enabled": False, "dim_brightness": 30, "mode": "global"},
        }
        mock_cm.save_config_atomic.return_value = MagicMock(status=MagicMock(value="success"))
        mock_cm.get_raw_file_content.return_value = {"github_token": "***"}

        mock_psm = MagicMock()

        app.state.config_manager = mock_cm
        app.state.plugin_store_manager = mock_psm

        return TestClient(app), mock_cm, mock_psm


@pytest.mark.unit
class TestConfigMainGet:
    def test_get_main_config_returns_success(self):
        client, cm, _ = _make_client()
        resp = client.get("/api/v3/config/main")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "schedule" in data["data"]

    def test_get_main_config_error(self):
        client, cm, _ = _make_client()
        cm.load_config.side_effect = RuntimeError("disk error")
        resp = client.get("/api/v3/config/main")
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "CONFIG_LOAD_FAILED"


@pytest.mark.unit
class TestConfigMainPost:
    def test_save_config_merges_and_saves(self):
        client, cm, _ = _make_client()
        resp = client.post("/api/v3/config/main", json={"schedule": {"enabled": False}})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        cm.save_config_atomic.assert_called_once()

    def test_save_config_invalid_json(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/config/main", content=b"not json", headers={"content-type": "application/json"})
        assert resp.status_code == 400


@pytest.mark.unit
class TestScheduleRoutes:
    def test_get_schedule(self):
        client, _, _ = _make_client()
        resp = client.get("/api/v3/config/schedule")
        assert resp.status_code == 200
        assert resp.json()["data"]["mode"] == "global"

    def test_save_schedule_global(self):
        client, cm, _ = _make_client()
        resp = client.post("/api/v3/config/schedule", json={
            "enabled": True, "mode": "global", "start_time": "08:00", "end_time": "22:00",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_save_schedule_invalid_time(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/config/schedule", json={
            "enabled": True, "mode": "global", "start_time": "25:00", "end_time": "22:00",
        })
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VALIDATION_ERROR"

    def test_save_schedule_per_day_no_day_enabled(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/config/schedule", json={
            "enabled": True, "mode": "per-day",
        })
        assert resp.status_code == 400
        assert "at least one day" in resp.json()["message"].lower()

    def test_save_schedule_invalid_mode(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/config/schedule", json={
            "enabled": True, "mode": "bogus",
        })
        assert resp.status_code == 400


@pytest.mark.unit
class TestDimScheduleRoutes:
    def test_get_dim_schedule(self):
        client, _, _ = _make_client()
        resp = client.get("/api/v3/config/dim-schedule")
        assert resp.status_code == 200

    def test_save_dim_schedule_validates_brightness(self):
        client, _, _ = _make_client()
        resp = client.post("/api/v3/config/dim-schedule", json={
            "enabled": True, "dim_brightness": 150, "mode": "global",
        })
        assert resp.status_code == 400
        assert "between 0 and 100" in resp.json()["message"]

    def test_save_dim_schedule_ok(self):
        client, cm, _ = _make_client()
        resp = client.post("/api/v3/config/dim-schedule", json={
            "enabled": True, "dim_brightness": 20, "mode": "global",
            "start_time": "21:00", "end_time": "06:00",
        })
        assert resp.status_code == 200


@pytest.mark.unit
class TestSecretsRoutes:
    def test_get_secrets(self):
        client, _, _ = _make_client()
        resp = client.get("/api/v3/config/secrets")
        assert resp.status_code == 200
        assert resp.json()["data"] == {"github_token": "***"}


@pytest.mark.unit
class TestRawConfigRoutes:
    def test_save_raw_main(self):
        client, cm, _ = _make_client()
        resp = client.post("/api/v3/config/raw/main", json={"key": "value"})
        assert resp.status_code == 200
        cm.save_raw_file_content.assert_called_once_with("main", {"key": "value"})

    def test_save_raw_secrets_reloads_token(self):
        client, cm, psm = _make_client()
        resp = client.post("/api/v3/config/raw/secrets", json={"github_token": "abc"})
        assert resp.status_code == 200
        cm.save_raw_file_content.assert_called_once_with("secrets", {"github_token": "abc"})
        psm._load_github_token.assert_called_once()
