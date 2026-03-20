"""Tests for BACK-003: Pydantic settings and request/response models."""

import os
from unittest.mock import patch

# ---------------------------------------------------------------------------
# AppSettings
# ---------------------------------------------------------------------------


class TestAppSettings:
    """Tests for src.api.config.AppSettings."""

    def test_default_values(self):
        """AppSettings has sensible defaults without any env vars."""
        from src.api.config import AppSettings

        settings = AppSettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 5000
        assert settings.debug is False
        assert settings.json_logging is False
        assert settings.hot_reload is False
        assert settings.config_path == "config/config.json"
        assert settings.secrets_path == "config/config_secrets.json"

    def test_env_var_override_port(self):
        """LEDMATRIX_PORT overrides the default port."""
        from src.api.config import AppSettings

        with patch.dict(os.environ, {"LEDMATRIX_PORT": "8080"}):
            settings = AppSettings()
        assert settings.port == 8080

    def test_env_var_override_debug(self):
        """LEDMATRIX_DEBUG overrides the default debug flag."""
        from src.api.config import AppSettings

        with patch.dict(os.environ, {"LEDMATRIX_DEBUG": "true"}):
            settings = AppSettings()
        assert settings.debug is True

    def test_env_var_override_host(self):
        """LEDMATRIX_HOST overrides the default host."""
        from src.api.config import AppSettings

        with patch.dict(os.environ, {"LEDMATRIX_HOST": "127.0.0.1"}):
            settings = AppSettings()
        assert settings.host == "127.0.0.1"

    def test_env_prefix_is_ledmatrix(self):
        """All env vars use the LEDMATRIX_ prefix."""
        from src.api.config import AppSettings

        with patch.dict(os.environ, {"LEDMATRIX_JSON_LOGGING": "true"}):
            settings = AppSettings()
        assert settings.json_logging is True

    def test_get_settings_returns_instance(self):
        """get_settings() returns an AppSettings instance."""
        from src.api.config import AppSettings, get_settings

        result = get_settings()
        assert isinstance(result, AppSettings)

    def test_get_settings_is_cached(self):
        """get_settings() returns the same instance on repeated calls."""
        from src.api.config import get_settings

        a = get_settings()
        b = get_settings()
        assert a is b


# ---------------------------------------------------------------------------
# Common models
# ---------------------------------------------------------------------------


class TestCommonModels:
    """Tests for src.api.models.common."""

    def test_success_response_defaults(self):
        from src.api.models.common import SuccessResponse

        resp = SuccessResponse(message="ok")
        assert resp.status == "success"
        assert resp.message == "ok"
        assert resp.data is None

    def test_success_response_with_data(self):
        from src.api.models.common import SuccessResponse

        resp = SuccessResponse(message="ok", data={"key": "value"})
        assert resp.data == {"key": "value"}

    def test_error_response(self):
        from src.api.models.common import ErrorResponse

        resp = ErrorResponse(error_code="NOT_FOUND", message="not found")
        assert resp.status == "error"
        assert resp.error_code == "NOT_FOUND"
        assert resp.message == "not found"
        assert resp.details is None

    def test_error_response_with_details(self):
        from src.api.models.common import ErrorResponse

        resp = ErrorResponse(
            error_code="VALIDATION",
            message="bad",
            details={"field": "name"},
        )
        assert resp.details == {"field": "name"}

    def test_paginated_response(self):
        from src.api.models.common import PaginatedResponse

        resp = PaginatedResponse(items=[1, 2, 3], total=10, page=1, page_size=3)
        assert resp.items == [1, 2, 3]
        assert resp.total == 10
        assert resp.page == 1
        assert resp.page_size == 3


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


class TestConfigModels:
    """Tests for src.api.models.config."""

    def test_display_hardware_config(self):
        from src.api.models.config import DisplayHardwareConfig

        cfg = DisplayHardwareConfig(
            rows=32,
            cols=64,
            chain_length=2,
            parallel=1,
            brightness=90,
        )
        assert cfg.rows == 32
        assert cfg.cols == 64
        assert cfg.chain_length == 2
        assert cfg.brightness == 90

    def test_display_hardware_config_defaults(self):
        from src.api.models.config import DisplayHardwareConfig

        cfg = DisplayHardwareConfig()
        assert cfg.rows == 32
        assert cfg.cols == 64
        assert cfg.chain_length == 1
        assert cfg.parallel == 1
        assert cfg.brightness == 100

    def test_schedule_config(self):
        from src.api.models.config import ScheduleConfig

        cfg = ScheduleConfig(enabled=True, start_time="07:00", end_time="23:00")
        assert cfg.enabled is True
        assert cfg.start_time == "07:00"
        assert cfg.end_time == "23:00"

    def test_schedule_config_defaults(self):
        from src.api.models.config import ScheduleConfig

        cfg = ScheduleConfig()
        assert cfg.enabled is False

    def test_system_config_response(self):
        from src.api.models.config import SystemConfigResponse

        resp = SystemConfigResponse(
            display={"hardware": {"rows": 32}},
            schedule={"enabled": True},
            general={"timezone": "UTC"},
        )
        assert resp.display == {"hardware": {"rows": 32}}
        assert resp.schedule == {"enabled": True}
        assert resp.general == {"timezone": "UTC"}

    def test_config_update_request_partial(self):
        """ConfigUpdateRequest allows partial updates (all fields optional)."""
        from src.api.models.config import ConfigUpdateRequest

        req = ConfigUpdateRequest(display={"hardware": {"brightness": 50}})
        assert req.display == {"hardware": {"brightness": 50}}
        assert req.schedule is None
        assert req.general is None

    def test_config_update_request_empty(self):
        """ConfigUpdateRequest can be constructed with no fields."""
        from src.api.models.config import ConfigUpdateRequest

        req = ConfigUpdateRequest()
        assert req.display is None

    def test_config_models_have_from_attributes(self):
        """Config models support from_attributes for ORM compat."""
        from src.api.models.config import DisplayHardwareConfig

        assert DisplayHardwareConfig.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Plugin models
# ---------------------------------------------------------------------------


class TestPluginModels:
    """Tests for src.api.models.plugin."""

    def test_plugin_info(self):
        from src.api.models.plugin import PluginInfo

        info = PluginInfo(
            id="weather",
            name="Weather",
            version="1.0.0",
            enabled=True,
            description="Shows weather",
            display_modes=["standard"],
        )
        assert info.id == "weather"
        assert info.name == "Weather"
        assert info.enabled is True
        assert info.display_modes == ["standard"]

    def test_plugin_config_response_is_plain_dict(self):
        """PluginConfigResponse.config must remain a plain dict, not a model."""
        from src.api.models.plugin import PluginConfigResponse

        resp = PluginConfigResponse(
            plugin_id="test",
            config={"enabled": True, "display_duration": 15},
            schema={"type": "object"},
        )
        assert isinstance(resp.config, dict)
        assert resp.config["enabled"] is True
        assert isinstance(resp.schema_, dict) or isinstance(resp.schema, dict)

    def test_plugin_toggle_request(self):
        from src.api.models.plugin import PluginToggleRequest

        req = PluginToggleRequest(plugin_id="weather", enabled=False)
        assert req.plugin_id == "weather"
        assert req.enabled is False

    def test_plugin_install_request(self):
        from src.api.models.plugin import PluginInstallRequest

        req = PluginInstallRequest(
            plugin_id="transit",
            source_url="https://github.com/example/transit",
        )
        assert req.plugin_id == "transit"
        assert req.source_url == "https://github.com/example/transit"

    def test_plugin_info_has_from_attributes(self):
        from src.api.models.plugin import PluginInfo

        assert PluginInfo.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# System models
# ---------------------------------------------------------------------------


class TestSystemModels:
    """Tests for src.api.models.system."""

    def test_system_status_response(self):
        from src.api.models.system import SystemStatusResponse

        resp = SystemStatusResponse(
            cpu_percent=25.5,
            memory_percent=40.0,
            cpu_temp=55.0,
            disk_percent=60.0,
            service_active=True,
            uptime=3600.0,
        )
        assert resp.cpu_percent == 25.5
        assert resp.service_active is True
        assert resp.uptime == 3600.0

    def test_system_status_optional_temp(self):
        """cpu_temp should be optional (not available on all platforms)."""
        from src.api.models.system import SystemStatusResponse

        resp = SystemStatusResponse(
            cpu_percent=10.0,
            memory_percent=30.0,
            cpu_temp=None,
            disk_percent=50.0,
            service_active=False,
            uptime=100.0,
        )
        assert resp.cpu_temp is None

    def test_system_version_response(self):
        from src.api.models.system import SystemVersionResponse

        resp = SystemVersionResponse(
            version="2.0.0",
            python_version="3.12.0",
            platform="linux",
        )
        assert resp.version == "2.0.0"
        assert resp.platform == "linux"

    def test_health_response(self):
        from src.api.models.system import HealthResponse

        resp = HealthResponse(
            status="healthy",
            checks={"database": True, "display": True},
        )
        assert resp.status == "healthy"
        assert resp.checks["database"] is True

    def test_health_response_has_from_attributes(self):
        from src.api.models.system import HealthResponse

        assert HealthResponse.model_config.get("from_attributes") is True
