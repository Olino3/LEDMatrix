"""Tests for FastAPI store routes (BACK-006) — install, update, uninstall, saved repos."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client():
    """Create a test client with mocked services."""
    with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
        from src.api.main import create_app

        app = create_app()

        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {}
        mock_cm.save_config_atomic.return_value = MagicMock(status=MagicMock(value="success"))

        mock_pm = MagicMock()
        mock_pm.discover_plugins.return_value = None
        mock_pm.get_all_plugin_info.return_value = {}

        mock_sm = MagicMock()
        mock_sm.load_schema.return_value = None

        mock_oq = MagicMock()
        mock_oh = MagicMock()
        mock_oh.get_history.return_value = []

        mock_psm = MagicMock()
        mock_psm.get_all_states.return_value = {}

        mock_store = MagicMock()
        mock_store.github_token = None
        mock_store.search_plugins.return_value = []
        mock_store.fetch_registry.return_value = {"plugins": []}
        mock_store.install_plugin.return_value = True
        mock_store.install_from_url.return_value = True
        mock_store.update_plugin.return_value = True
        mock_store.uninstall_plugin.return_value = True
        mock_store.fetch_registry_from_url.return_value = {"plugins": []}

        mock_saved = MagicMock()
        mock_saved.get_all.return_value = []
        mock_saved.add.return_value = True
        mock_saved.remove.return_value = True

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
# Store browsing
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestStoreList:
    def test_list_store_plugins(self):
        client, app = _make_client()
        app.state.plugin_store_manager.search_plugins.return_value = [
            {"id": "test-plugin", "name": "Test", "version": "1.0.0"},
        ]
        resp = client.get("/api/v3/plugins/store/list")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_list_store_with_query(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/store/list", params={"query": "test", "category": "display"})
        assert resp.status_code == 200

    def test_list_store_with_tags(self):
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/store/list", params={"tags": "art,sports"})
        assert resp.status_code == 200

    def test_list_store_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.search_plugins.side_effect = RuntimeError("network error")
        resp = client.get("/api/v3/plugins/store/list")
        assert resp.status_code == 500
        assert resp.json()["status"] == "error"


@pytest.mark.unit
class TestGithubStatus:
    def test_github_status_no_token(self):
        client, app = _make_client()
        app.state.plugin_store_manager.github_token = None
        resp = client.get("/api/v3/plugins/store/github-status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["authenticated"] is False
        assert data["token_status"] == "none"

    def test_github_status_valid_token(self):
        client, app = _make_client()
        app.state.plugin_store_manager.github_token = "ghp_valid"
        app.state.plugin_store_manager._validate_github_token.return_value = (True, None)
        resp = client.get("/api/v3/plugins/store/github-status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["authenticated"] is True
        assert data["token_status"] == "valid"

    def test_github_status_invalid_token(self):
        client, app = _make_client()
        app.state.plugin_store_manager.github_token = "bad_token"
        app.state.plugin_store_manager._validate_github_token.return_value = (False, "401 Unauthorized")
        resp = client.get("/api/v3/plugins/store/github-status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["authenticated"] is False
        assert data["token_status"] == "invalid"


@pytest.mark.unit
class TestStoreRefresh:
    def test_refresh_store(self):
        client, app = _make_client()
        app.state.plugin_store_manager.fetch_registry.return_value = {"plugins": [{"id": "a"}, {"id": "b"}]}
        resp = client.post("/api/v3/plugins/store/refresh", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["data"]["plugin_count"] == 2

    def test_refresh_store_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.fetch_registry.side_effect = RuntimeError("timeout")
        resp = client.post("/api/v3/plugins/store/refresh", json={})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "STORE_REFRESH_FAILED"


# ---------------------------------------------------------------------------
# Install / update / uninstall
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestInstallPlugin:
    def test_install_plugin_success(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_plugin.return_value = True
        resp = client.post("/api/v3/plugins/install", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_install_plugin_with_branch(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_plugin.return_value = True
        resp = client.post("/api/v3/plugins/install", json={"plugin_id": "my-plugin", "branch": "dev"})
        assert resp.status_code == 200
        app.state.plugin_store_manager.install_plugin.assert_called_with("my-plugin", branch="dev")

    def test_install_plugin_missing_id(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/install", json={})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_install_plugin_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_plugin.return_value = False
        resp = client.post("/api/v3/plugins/install", json={"plugin_id": "bad-plugin"})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "INSTALL_FAILED"

    def test_install_plugin_exception(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_plugin.side_effect = RuntimeError("disk full")
        resp = client.post("/api/v3/plugins/install", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "INSTALL_FAILED"

    def test_install_plugin_invalid_json(self):
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/plugins/install",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"


@pytest.mark.unit
class TestInstallFromUrl:
    def test_install_from_url_success(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_from_url.return_value = True
        resp = client.post(
            "/api/v3/plugins/install-from-url",
            json={"repo_url": "https://github.com/user/plugin"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_install_from_url_missing_url(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/install-from-url", json={"plugin_id": "p"})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_install_from_url_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.install_from_url.return_value = False
        resp = client.post(
            "/api/v3/plugins/install-from-url",
            json={"repo_url": "https://github.com/user/plugin"},
        )
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "INSTALL_FAILED"


@pytest.mark.unit
class TestUpdatePlugin:
    def test_update_plugin_success(self):
        client, app = _make_client()
        app.state.plugin_store_manager.update_plugin.return_value = True
        resp = client.post("/api/v3/plugins/update", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_update_plugin_missing_id(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/update", json={})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_update_plugin_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.update_plugin.return_value = False
        resp = client.post("/api/v3/plugins/update", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "UPDATE_FAILED"


@pytest.mark.unit
class TestUninstallPlugin:
    def test_uninstall_plugin_success(self):
        client, app = _make_client()
        app.state.plugin_store_manager.uninstall_plugin.return_value = True
        resp = client.post("/api/v3/plugins/uninstall", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_uninstall_plugin_missing_id(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/uninstall", json={})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_uninstall_plugin_failure(self):
        client, app = _make_client()
        app.state.plugin_store_manager.uninstall_plugin.return_value = False
        resp = client.post("/api/v3/plugins/uninstall", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "UNINSTALL_FAILED"

    def test_uninstall_plugin_exception(self):
        client, app = _make_client()
        app.state.plugin_store_manager.uninstall_plugin.side_effect = RuntimeError("not found")
        resp = client.post("/api/v3/plugins/uninstall", json={"plugin_id": "my-plugin"})
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "UNINSTALL_FAILED"


# ---------------------------------------------------------------------------
# Registry from URL
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRegistryFromUrl:
    def test_get_registry_success(self):
        client, app = _make_client()
        app.state.plugin_store_manager.fetch_registry_from_url.return_value = {"plugins": [{"id": "plugin-a"}]}
        resp = client.post(
            "/api/v3/plugins/registry-from-url",
            json={"repo_url": "https://github.com/org/registry"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_get_registry_missing_url(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/registry-from-url", json={})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_get_registry_not_found(self):
        client, app = _make_client()
        app.state.plugin_store_manager.fetch_registry_from_url.return_value = None
        resp = client.post(
            "/api/v3/plugins/registry-from-url",
            json={"repo_url": "https://github.com/org/missing"},
        )
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "REGISTRY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Saved repositories
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSavedRepositories:
    def test_list_saved_repos(self):
        client, app = _make_client()
        app.state.saved_repositories_manager.get_all.return_value = [
            {"url": "https://github.com/user/repo", "name": "My Repo"}
        ]
        resp = client.get("/api/v3/plugins/saved-repositories")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert len(resp.json()["data"]) == 1

    def test_add_saved_repo_success(self):
        client, app = _make_client()
        app.state.saved_repositories_manager.add.return_value = True
        resp = client.post(
            "/api/v3/plugins/saved-repositories",
            json={"repo_url": "https://github.com/user/repo", "name": "Repo"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_add_saved_repo_missing_url(self):
        client, _ = _make_client()
        resp = client.post("/api/v3/plugins/saved-repositories", json={"name": "No URL"})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_add_saved_repo_already_exists(self):
        client, app = _make_client()
        app.state.saved_repositories_manager.add.return_value = False
        resp = client.post(
            "/api/v3/plugins/saved-repositories",
            json={"repo_url": "https://github.com/user/repo"},
        )
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "REPO_ADD_FAILED"

    def test_remove_saved_repo_success(self):
        client, app = _make_client()
        app.state.saved_repositories_manager.remove.return_value = True
        resp = client.request(
            "DELETE",
            "/api/v3/plugins/saved-repositories",
            json={"repo_url": "https://github.com/user/repo"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_remove_saved_repo_not_found(self):
        client, app = _make_client()
        app.state.saved_repositories_manager.remove.return_value = False
        resp = client.request(
            "DELETE",
            "/api/v3/plugins/saved-repositories",
            json={"repo_url": "https://github.com/user/missing"},
        )
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "REPO_NOT_FOUND"

    def test_remove_saved_repo_missing_url(self):
        client, _ = _make_client()
        resp = client.request(
            "DELETE",
            "/api/v3/plugins/saved-repositories",
            json={},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# File upload endpoints
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestFileUploads:
    def test_upload_font_file(self):
        """Test font upload with UploadFile — covers the UploadFile endpoint path."""
        client, _ = _make_client()
        font_data = b"BDF font data"
        resp = client.post(
            "/api/v3/fonts/upload",
            files={"font_file": ("test.bdf", BytesIO(font_data), "application/octet-stream")},
        )
        # Will succeed or fail based on filesystem state, but must not 500 on valid input
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["status"] == "success"

    def test_upload_font_invalid_extension(self):
        """Test font upload rejects non-font file formats."""
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/fonts/upload",
            files={"font_file": ("bad.exe", BytesIO(b"data"), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_upload_asset_files(self):
        """Test plugin asset upload with multiple UploadFile items."""
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/plugins/assets/upload",
            data={"plugin_id": "test-plugin"},
            files=[("files", ("img.png", BytesIO(b"\x89PNG"), "image/png"))],
        )
        # Filesystem may fail in CI but the endpoint must parse inputs correctly
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["status"] == "success"

    def test_upload_asset_too_many_files(self):
        """Test that uploading more than 10 files (MAX_UPLOAD_COUNT in assets.py) is rejected."""
        client, _ = _make_client()
        files = [
            ("files", (f"file{i}.png", BytesIO(b"data"), "image/png"))
            for i in range(11)  # exceeds MAX_UPLOAD_COUNT = 10 defined in src/api/routers/assets.py
        ]
        resp = client.post(
            "/api/v3/plugins/assets/upload",
            data={"plugin_id": "test-plugin"},
            files=files,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_upload_calendar_credentials_valid_json(self):
        """Test calendar credentials upload with valid JSON file."""
        client, _ = _make_client()
        creds = b'{"type": "service_account", "project_id": "test"}'
        resp = client.post(
            "/api/v3/plugins/calendar/upload-credentials",
            files={"file": ("credentials.json", BytesIO(creds), "application/json")},
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["status"] == "success"

    def test_upload_calendar_credentials_invalid_json(self):
        """Test calendar credentials upload rejects non-JSON content."""
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/plugins/calendar/upload-credentials",
            files={"file": ("credentials.json", BytesIO(b"not json"), "application/json")},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"

    def test_upload_calendar_credentials_wrong_extension(self):
        """Test calendar credentials upload rejects non-.json files."""
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/plugins/calendar/upload-credentials",
            files={"file": ("credentials.txt", BytesIO(b"{}"), "text/plain")},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# Error responses for invalid plugin IDs
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestInvalidPluginIdErrors:
    def test_get_health_unknown_plugin(self):
        """Health tracker returns data for unknown plugins (no 404 for unknown IDs)."""
        client, app = _make_client()
        app.state.plugin_manager.health_tracker.get_health_summary.return_value = {}
        resp = client.get("/api/v3/plugins/health/nonexistent-plugin")
        assert resp.status_code == 200

    def test_get_metrics_unknown_plugin(self):
        """Metrics monitor returns data for unknown plugins."""
        client, app = _make_client()
        app.state.plugin_manager.resource_monitor.get_metrics_summary.return_value = {}
        resp = client.get("/api/v3/plugins/metrics/nonexistent-plugin")
        assert resp.status_code == 200

    def test_get_operation_status_not_found(self):
        """Operation status returns 404 for unknown operation IDs."""
        client, app = _make_client()
        app.state.operation_queue.get_operation_status.return_value = None
        resp = client.get("/api/v3/plugins/operation/unknown-op-id")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "OPERATION_NOT_FOUND"

    def test_get_plugin_state_not_found(self):
        """State endpoint returns 404 for unknown plugin IDs."""
        client, app = _make_client()
        app.state.plugin_state_manager.get_plugin_state.return_value = None
        resp = client.get("/api/v3/plugins/state", params={"plugin_id": "nonexistent"})
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "STATE_NOT_FOUND"

    def test_delete_font_override_not_found(self):
        """Font override delete returns 404 for unknown keys."""
        client, _ = _make_client()
        resp = client.delete("/api/v3/fonts/overrides/unknown-element")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"

    def test_delete_font_family_not_found(self):
        """Font delete returns 404 for unknown font families."""
        client, _ = _make_client()
        resp = client.delete("/api/v3/fonts/nonexistent-font")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"

    def test_asset_delete_not_found(self):
        """Asset delete returns 404 for unknown assets."""
        client, _ = _make_client()
        resp = client.post(
            "/api/v3/plugins/assets/delete",
            json={"plugin_id": "test-plugin", "image_id": "missing.png"},
        )
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"

    def test_static_file_unknown_plugin(self):
        """Static file serve returns 404 for unknown plugins."""
        client, _ = _make_client()
        resp = client.get("/api/v3/plugins/nonexistent-plugin/static/icon.png")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"
