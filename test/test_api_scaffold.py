"""Tests for the FastAPI application scaffold (BACK-001)."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestCreateApp:
    """Test the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        from src.api import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_correct_metadata(self):
        from src.api import create_app

        app = create_app()
        assert app.title == "LED Matrix"
        assert app.version == "2.0.0"

    def test_docs_url_configured(self):
        from src.api import create_app

        app = create_app()
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"


@pytest.mark.unit
class TestRootRedirect:
    """Test the root URL redirect."""

    @patch("src.api.main.init_services")
    @patch("src.api.main.shutdown_services")
    def test_root_redirects_to_v3(self, mock_shutdown, mock_init):
        from src.api import create_app

        app = create_app()
        client = TestClient(app, follow_redirects=False)
        response = client.get("/")
        assert response.status_code == 307
        assert response.headers["location"] == "/v3"

    @patch("src.api.main.init_services")
    @patch("src.api.main.shutdown_services")
    def test_favicon_returns_204(self, mock_shutdown, mock_init):
        from src.api import create_app

        app = create_app()
        client = TestClient(app)
        response = client.get("/favicon.ico")
        assert response.status_code == 204


@pytest.mark.unit
class TestDependencies:
    """Test dependency injection callables."""

    def test_get_config_manager(self):
        from src.api.dependencies import get_config_manager

        mock_request = MagicMock()
        mock_request.app.state.config_manager = "fake_cm"
        assert get_config_manager(mock_request) == "fake_cm"

    def test_get_plugin_manager(self):
        from src.api.dependencies import get_plugin_manager

        mock_request = MagicMock()
        mock_request.app.state.plugin_manager = "fake_pm"
        assert get_plugin_manager(mock_request) == "fake_pm"

    def test_get_schema_manager(self):
        from src.api.dependencies import get_schema_manager

        mock_request = MagicMock()
        mock_request.app.state.schema_manager = "fake_sm"
        assert get_schema_manager(mock_request) == "fake_sm"

    def test_get_operation_queue(self):
        from src.api.dependencies import get_operation_queue

        mock_request = MagicMock()
        mock_request.app.state.operation_queue = "fake_oq"
        assert get_operation_queue(mock_request) == "fake_oq"


@pytest.mark.unit
class TestLifespan:
    """Test the lifespan initializes and tears down services."""

    @patch("src.api.main.shutdown_services")
    @patch("src.api.main.init_services")
    def test_lifespan_calls_init_and_shutdown(self, mock_init, mock_shutdown):
        from src.api.main import create_app

        app = create_app()
        with TestClient(app):
            mock_init.assert_called_once_with(app)
        mock_shutdown.assert_called_once_with(app)

    def test_shutdown_services_stops_health_monitor(self):
        from src.api.dependencies import shutdown_services

        mock_app = MagicMock()
        mock_monitor = MagicMock()
        mock_app.state.health_monitor = mock_monitor
        shutdown_services(mock_app)
        mock_monitor.stop.assert_called_once()

    def test_shutdown_services_noop_when_no_monitor(self):
        from src.api.dependencies import shutdown_services

        mock_app = MagicMock()
        mock_app.state.health_monitor = None
        # Should not raise
        shutdown_services(mock_app)


@pytest.mark.unit
class TestStartModule:
    """Test the start.py entry point module."""

    def test_get_local_ips_returns_list(self):
        from src.api.start import get_local_ips

        result = get_local_ips()
        assert isinstance(result, list)
        assert len(result) > 0

    @patch("src.api.start.subprocess.run", side_effect=FileNotFoundError)
    def test_get_local_ips_fallback_on_subprocess_failure(self, mock_run):
        from src.api.start import get_local_ips

        result = get_local_ips()
        assert isinstance(result, list)
        assert len(result) > 0
