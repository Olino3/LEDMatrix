"""
Tests for StartupValidator.

Covers validation logic for configuration, cache directory, display config,
plugin configurations, and the raise_on_errors method.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock, mock_open

from src.startup_validator import StartupValidator
from src.exceptions import CacheError, ConfigError, PluginError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config_manager(config=None, load_config=None):
    """Return a mock ConfigManager."""
    cm = MagicMock()
    default_config = {
        "display": {
            "hardware": {"rows": 32, "cols": 64}
        },
        "timezone": "America/New_York",
    }
    cm.load_config.return_value = load_config if load_config is not None else default_config
    cm.get_config.return_value = config if config is not None else default_config
    return cm


def _make_plugin_manager(discovered=None):
    """Return a mock PluginManager."""
    pm = MagicMock()
    pm.discover_plugins.return_value = discovered if discovered is not None else []
    pm.get_plugin_directory.return_value = None
    return pm


# ---------------------------------------------------------------------------
# TestStartupValidatorInit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStartupValidatorInit:
    """Test StartupValidator initialization."""

    def test_init_without_plugin_manager(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        assert validator.config_manager is cm
        assert validator.plugin_manager is None
        assert validator.errors == []
        assert validator.warnings == []

    def test_init_with_plugin_manager(self):
        cm = _make_config_manager()
        pm = _make_plugin_manager()
        validator = StartupValidator(cm, pm)
        assert validator.plugin_manager is pm


# ---------------------------------------------------------------------------
# TestValidateAll
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateAll:
    """Test the validate_all orchestration method."""

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_returns_true_when_no_errors(self, mock_cache):
        """validate_all returns (True, [], []) for a clean config."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        is_valid, errors, warnings = validator.validate_all()
        assert is_valid is True
        assert errors == []

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_returns_false_when_errors_present(self, mock_cache):
        """validate_all returns False when config is broken."""
        cm = _make_config_manager(
            config={"timezone": "UTC"},  # missing 'display'
            load_config={"timezone": "UTC"},
        )
        validator = StartupValidator(cm)
        is_valid, errors, warnings = validator.validate_all()
        assert is_valid is False
        assert len(errors) > 0

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_calls_validate_plugins_when_plugin_manager_present(self, mock_cache):
        """validate_all delegates to _validate_plugins when plugin_manager provided."""
        cm = _make_config_manager()
        pm = _make_plugin_manager()
        validator = StartupValidator(cm, pm)
        with patch.object(validator, "_validate_plugins") as mock_plugins:
            validator.validate_all()
            mock_plugins.assert_called_once()

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_does_not_call_validate_plugins_without_plugin_manager(self, mock_cache):
        """validate_all skips _validate_plugins when no plugin_manager."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        with patch.object(validator, "_validate_plugins") as mock_plugins:
            validator.validate_all()
            mock_plugins.assert_not_called()

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_returns_copies_of_lists(self, mock_cache):
        """validate_all returns copies so mutations don't affect internal state."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        _, errors, warnings = validator.validate_all()
        errors.append("injected")
        assert "injected" not in validator.errors

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    def test_warnings_included_in_return(self, mock_cache):
        """validate_all includes warnings in the returned tuple."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        # Inject a warning manually before calling
        validator.warnings.append("a warning")
        is_valid, errors, warnings = validator.validate_all()
        assert "a warning" in warnings


# ---------------------------------------------------------------------------
# TestValidateConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateConfig:
    """Test _validate_config."""

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_valid_config_produces_no_errors(self, mock_display, mock_cache):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator._validate_config()
        assert validator.errors == []

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_missing_display_key_adds_error(self, mock_display, mock_cache):
        cm = _make_config_manager(load_config={"timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_config()
        assert any("display" in e for e in validator.errors)

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_missing_timezone_key_adds_error(self, mock_display, mock_cache):
        cm = _make_config_manager(load_config={"display": {"hardware": {}}})
        validator = StartupValidator(cm)
        validator._validate_config()
        assert any("timezone" in e for e in validator.errors)

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_empty_display_config_adds_error(self, mock_display, mock_cache):
        """An empty display dict should trigger the 'missing or empty' error."""
        cm = _make_config_manager(load_config={"display": {}, "timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_config()
        assert any("missing or empty" in e for e in validator.errors)

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_config_error_is_caught(self, mock_display, mock_cache):
        """ConfigError raised by load_config is appended to errors."""
        cm = MagicMock()
        cm.load_config.side_effect = ConfigError("bad config")
        validator = StartupValidator(cm)
        validator._validate_config()
        assert any("Configuration error" in e for e in validator.errors)

    @patch("src.startup_validator.StartupValidator._validate_cache_directory")
    @patch("src.startup_validator.StartupValidator._validate_display_config")
    def test_unexpected_exception_is_caught(self, mock_display, mock_cache):
        """An unexpected exception from load_config is appended to errors."""
        cm = MagicMock()
        cm.load_config.side_effect = RuntimeError("boom")
        validator = StartupValidator(cm)
        validator._validate_config()
        assert any("Unexpected error" in e for e in validator.errors)


# ---------------------------------------------------------------------------
# TestValidateCacheDirectory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateCacheDirectory:
    """Test _validate_cache_directory."""

    def test_no_cache_dir_adds_warning(self):
        """When get_cache_dir returns None/empty, a warning is added."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = None
            validator = StartupValidator(cm)
            validator._validate_cache_directory()
        assert any("caching will be disabled" in w for w in validator.warnings)

    def test_nonexistent_cache_dir_adds_error(self, tmp_path):
        """When the cache dir path doesn't exist on disk, an error is added."""
        missing = str(tmp_path / "nonexistent_dir")
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = missing
            validator = StartupValidator(cm)
            validator._validate_cache_directory()
        assert any("does not exist" in e for e in validator.errors)

    def test_non_writable_cache_dir_adds_error(self, tmp_path):
        """When the cache dir is not writable, an error is added."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = str(tmp_path)
            with patch("os.path.exists", return_value=True), \
                 patch("os.access", return_value=False):
                validator = StartupValidator(cm)
                validator._validate_cache_directory()
        assert any("not writable" in e for e in validator.errors)

    def test_write_test_failure_adds_error(self, tmp_path):
        """When writing the test file raises IOError, an error is added."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = str(tmp_path)
            with patch("os.path.exists", return_value=True), \
                 patch("os.access", return_value=True), \
                 patch("builtins.open", side_effect=IOError("disk full")):
                validator = StartupValidator(cm)
                validator._validate_cache_directory()
        assert any("Cannot write" in e for e in validator.errors)

    def test_valid_writable_cache_dir_no_errors(self, tmp_path):
        """A valid, writable cache dir produces no errors or warnings."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = str(tmp_path)
            validator = StartupValidator(cm)
            validator._validate_cache_directory()
        assert validator.errors == []
        assert validator.warnings == []

    def test_exception_during_cache_manager_init_adds_warning(self):
        """Exception constructing CacheManager results in a warning, not crash."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager", side_effect=Exception("no cache")):
            validator = StartupValidator(cm)
            validator._validate_cache_directory()
        assert any("Could not validate cache directory" in w for w in validator.warnings)

    def test_oserror_on_write_adds_error(self, tmp_path):
        """OSError during write test is caught and added as an error."""
        cm = _make_config_manager()
        with patch("src.cache_manager.CacheManager") as MockCM:
            instance = MockCM.return_value
            instance.get_cache_dir.return_value = str(tmp_path)
            with patch("os.path.exists", return_value=True), \
                 patch("os.access", return_value=True), \
                 patch("builtins.open", side_effect=OSError("permission denied")):
                validator = StartupValidator(cm)
                validator._validate_cache_directory()
        assert any("Cannot write" in e for e in validator.errors)


# ---------------------------------------------------------------------------
# TestValidateDisplayConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateDisplayConfig:
    """Test _validate_display_config."""

    def test_valid_display_config_no_errors(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert validator.errors == []
        assert validator.warnings == []

    def test_missing_display_key_adds_error(self):
        cm = _make_config_manager(config={"timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("Display configuration is missing" in e for e in validator.errors)

    def test_empty_display_dict_adds_error(self):
        cm = _make_config_manager(config={"display": {}, "timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("Display configuration is missing" in e for e in validator.errors)

    def test_missing_hardware_section_adds_error(self):
        cm = _make_config_manager(config={"display": {"brightness": 100}, "timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("hardware configuration is missing" in e for e in validator.errors)

    def test_empty_hardware_dict_adds_error(self):
        cm = _make_config_manager(config={"display": {"hardware": {}}, "timezone": "UTC"})
        validator = StartupValidator(cm)
        validator._validate_display_config()
        # Empty hardware dict counts as missing
        assert any("hardware configuration is missing" in e for e in validator.errors)

    def test_missing_rows_adds_warning(self):
        config = {"display": {"hardware": {"cols": 64}}, "timezone": "UTC"}
        cm = _make_config_manager(config=config)
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("rows" in w for w in validator.warnings)

    def test_missing_cols_adds_warning(self):
        config = {"display": {"hardware": {"rows": 32}}, "timezone": "UTC"}
        cm = _make_config_manager(config=config)
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("cols" in w for w in validator.warnings)

    def test_exception_adds_warning(self):
        cm = MagicMock()
        cm.get_config.side_effect = RuntimeError("oops")
        validator = StartupValidator(cm)
        validator._validate_display_config()
        assert any("Could not validate display configuration" in w for w in validator.warnings)


# ---------------------------------------------------------------------------
# TestValidatePlugins
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatePlugins:
    """Test _validate_plugins."""

    def test_no_plugin_manager_returns_immediately(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)  # no plugin manager
        validator._validate_plugins()  # should not raise
        assert validator.errors == []
        assert validator.warnings == []

    def test_enabled_plugin_not_in_discovered_adds_warning(self):
        config = {
            "my_plugin": {"enabled": True},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = _make_plugin_manager(discovered=[])
        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert any("my_plugin" in w and "not found" in w for w in validator.warnings)

    def test_disabled_plugin_not_in_discovered_no_warning(self):
        config = {
            "my_plugin": {"enabled": False},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = _make_plugin_manager(discovered=[])
        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert not any("my_plugin" in w for w in validator.warnings)

    def test_non_dict_plugin_config_is_skipped(self):
        """Top-level config values that are not dicts should not be inspected."""
        config = {
            "some_setting": "a_string",
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = _make_plugin_manager(discovered=[])
        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        # No error or warning about some_setting
        assert not any("some_setting" in e for e in validator.errors + validator.warnings)

    def test_system_keys_are_skipped(self):
        """Keys like 'display', 'schedule', 'timezone', 'plugin_system' are ignored."""
        config = {
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "schedule": {"enabled": True},
            "timezone": "UTC",
            "plugin_system": {"enabled": True},
        }
        cm = _make_config_manager(config=config)
        pm = _make_plugin_manager(discovered=[])
        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert validator.warnings == []

    def test_enabled_discovered_plugin_missing_manifest_adds_error(self, tmp_path):
        """A discovered+enabled plugin without manifest.json triggers an error."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        # No manifest.json created

        config = {
            "my_plugin": {"enabled": True},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = MagicMock()
        pm.discover_plugins.return_value = ["my_plugin"]
        pm.get_plugin_directory.return_value = str(plugin_dir)

        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert any("manifest.json" in e for e in validator.errors)

    def test_enabled_discovered_plugin_with_manifest_no_error(self, tmp_path):
        """A discovered+enabled plugin with manifest.json produces no error."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('{"id": "my_plugin"}')

        config = {
            "my_plugin": {"enabled": True},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = MagicMock()
        pm.discover_plugins.return_value = ["my_plugin"]
        pm.get_plugin_directory.return_value = str(plugin_dir)

        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert not any("manifest.json" in e for e in validator.errors)

    def test_plugin_with_no_directory_skips_manifest_check(self):
        """get_plugin_directory returning None skips the manifest check."""
        config = {
            "my_plugin": {"enabled": True},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = MagicMock()
        pm.discover_plugins.return_value = ["my_plugin"]
        pm.get_plugin_directory.return_value = None

        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert not any("manifest" in e for e in validator.errors)

    def test_exception_adds_warning(self):
        cm = _make_config_manager()
        pm = MagicMock()
        pm.discover_plugins.side_effect = RuntimeError("discovery failed")
        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert any("Could not validate plugins" in w for w in validator.warnings)

    def test_discovered_disabled_plugin_skips_manifest_check(self, tmp_path):
        """A discovered plugin that is disabled does not get its manifest checked."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        # No manifest.json

        config = {
            "my_plugin": {"enabled": False},
            "display": {"hardware": {"rows": 32, "cols": 64}},
            "timezone": "UTC",
        }
        cm = _make_config_manager(config=config)
        pm = MagicMock()
        pm.discover_plugins.return_value = ["my_plugin"]
        pm.get_plugin_directory.return_value = str(plugin_dir)

        validator = StartupValidator(cm, pm)
        validator._validate_plugins()
        assert not any("manifest.json" in e for e in validator.errors)


# ---------------------------------------------------------------------------
# TestRaiseOnErrors
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRaiseOnErrors:
    """Test raise_on_errors."""

    def test_no_errors_does_not_raise(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        # Should complete without raising
        validator.raise_on_errors()

    def test_config_error_raises_config_error(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Missing required configuration key: display")
        with pytest.raises(ConfigError):
            validator.raise_on_errors()

    def test_cache_error_raises_cache_error(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Cache directory does not exist: /tmp/cache")
        with pytest.raises(CacheError):
            validator.raise_on_errors()

    def test_plugin_error_raises_plugin_error(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Plugin 'foo' manifest.json not found")
        with pytest.raises(PluginError):
            validator.raise_on_errors()

    def test_other_error_raises_config_error(self):
        """Errors that don't match config/cache/plugin raise ConfigError as fallback."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Some completely unknown error occurred")
        with pytest.raises(ConfigError):
            validator.raise_on_errors()

    def test_config_error_takes_precedence_over_cache_error(self):
        """When both config and cache errors exist, ConfigError is raised first."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Missing required configuration key: display")
        validator.errors.append("Cache directory does not exist: /tmp/cache")
        with pytest.raises(ConfigError):
            validator.raise_on_errors()

    def test_cache_error_takes_precedence_over_plugin_error(self):
        """When both cache and plugin errors exist but no config error, CacheError is raised."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Cache directory is not writable: /tmp/cache")
        validator.errors.append("Plugin 'foo' manifest.json not found")
        with pytest.raises(CacheError):
            validator.raise_on_errors()

    def test_plugin_error_takes_precedence_over_other_errors(self):
        """Plugin errors outrank generic 'other' errors."""
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Plugin 'bar' manifest.json not found")
        validator.errors.append("Some unknown error")
        with pytest.raises(PluginError):
            validator.raise_on_errors()

    def test_config_error_context_contains_errors(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Missing required configuration key: timezone")
        with pytest.raises(ConfigError) as exc_info:
            validator.raise_on_errors()
        assert "errors" in exc_info.value.context

    def test_cache_error_context_contains_errors(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Cache directory does not exist: /tmp/x")
        with pytest.raises(CacheError) as exc_info:
            validator.raise_on_errors()
        assert "errors" in exc_info.value.context

    def test_plugin_error_context_contains_errors(self):
        cm = _make_config_manager()
        validator = StartupValidator(cm)
        validator.errors.append("Plugin 'baz' manifest.json not found")
        with pytest.raises(PluginError) as exc_info:
            validator.raise_on_errors()
        assert "errors" in exc_info.value.context
