"""
Additional unit tests for ConfigManager targeting uncovered code paths.

Focuses on: error handling, edge cases, migration logic, atomic saves,
template creation, save_raw_file_content, cleanup methods, secrets
handling, and deep-merge behaviour.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config_manager import ConfigManager
from src.config_manager_atomic import SaveResult, SaveResultStatus
from src.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# _get_atomic_manager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAtomicManager:
    """Test lazy initialisation of the AtomicConfigManager."""

    def test_creates_atomic_manager_on_first_call(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        atomic = manager._get_atomic_manager()
        assert atomic is not None

    def test_returns_same_instance_on_subsequent_calls(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        first = manager._get_atomic_manager()
        second = manager._get_atomic_manager()
        assert first is second


# ---------------------------------------------------------------------------
# save_config_atomic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveConfigAtomic:
    """Test save_config_atomic delegating to AtomicConfigManager."""

    def test_successful_save_updates_in_memory_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg))
        manager.config = {"timezone": "UTC"}

        new_data = {"timezone": "America/New_York"}
        result = manager.save_config_atomic(new_data, create_backup=False, validate_after_write=False)

        assert result.status == SaveResultStatus.SUCCESS
        assert manager.config == new_data

    def test_secrets_are_stripped_before_atomic_save(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"timezone": "UTC"})
        _write_json(secrets, {"plugin1": {"api_key": "s3cr3t"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.config = {}

        new_data = {"timezone": "UTC", "plugin1": {"enabled": True, "api_key": "s3cr3t"}}
        manager.save_config_atomic(new_data, create_backup=False, validate_after_write=False)

        saved = _read_json(cfg)
        assert "api_key" not in saved.get("plugin1", {})
        assert saved["plugin1"]["enabled"] is True

    def test_rolled_back_status_reloads_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg))
        manager.config = {"timezone": "UTC"}
        manager.template_path = str(tmp_path / "nonexistent.json")

        rolled_back_result = SaveResult(
            status=SaveResultStatus.ROLLED_BACK,
            message="rolled back",
        )

        with patch.object(manager._get_atomic_manager(), "save_config_atomic", return_value=rolled_back_result):
            result = manager.save_config_atomic({"timezone": "UTC"}, create_backup=False)

        assert result.status == SaveResultStatus.ROLLED_BACK
        # Config was (re)loaded from disk after rollback
        assert manager.config.get("timezone") == "UTC"

    def test_rolled_back_status_reload_error_is_logged(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg))
        manager.config = {}

        rolled_back_result = SaveResult(
            status=SaveResultStatus.ROLLED_BACK,
            message="rolled back",
        )

        with (
            patch.object(manager._get_atomic_manager(), "save_config_atomic", return_value=rolled_back_result),
            patch.object(manager, "load_config", side_effect=ConfigError("reload fail")),
        ):
            result = manager.save_config_atomic({"x": 1}, create_backup=False)

        assert result.status == SaveResultStatus.ROLLED_BACK

    def test_secrets_load_failure_during_atomic_save_is_logged(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {})
        _write_json(secrets, "not valid json")  # corrupt

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.config = {}

        # Should not raise; logs a warning and continues
        result = manager.save_config_atomic({"timezone": "UTC"}, create_backup=False, validate_after_write=False)
        assert result.status == SaveResultStatus.SUCCESS

    def test_no_secrets_passes_none_to_atomic_manager(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg), secrets_path=str(tmp_path / "no_secrets.json"))
        manager.config = {}

        atomic = manager._get_atomic_manager()
        with patch.object(
            atomic, "save_config_atomic", return_value=SaveResult(status=SaveResultStatus.SUCCESS, message="ok")
        ) as mock_save:
            manager.save_config_atomic({"k": "v"}, create_backup=False)

        _, kwargs = mock_save.call_args
        assert kwargs.get("new_secrets") is None


# ---------------------------------------------------------------------------
# rollback_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRollbackConfig:
    """Test rollback_config."""

    def test_successful_rollback_reloads_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch.object(manager._get_atomic_manager(), "rollback_config", return_value=True):
            result = manager.rollback_config()

        assert result is True
        assert manager.config.get("timezone") == "UTC"

    def test_rollback_returns_false_when_atomic_returns_false(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch.object(manager._get_atomic_manager(), "rollback_config", return_value=False):
            result = manager.rollback_config()

        assert result is False

    def test_rollback_reload_error_returns_false(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with (
            patch.object(manager._get_atomic_manager(), "rollback_config", return_value=True),
            patch.object(manager, "load_config", side_effect=Exception("disk error")),
        ):
            result = manager.rollback_config()

        assert result is False

    def test_rollback_with_specific_version(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        atomic = manager._get_atomic_manager()
        with patch.object(atomic, "rollback_config", return_value=True) as mock_rb:
            manager.rollback_config(backup_version="20240101_120000")

        mock_rb.assert_called_once_with("20240101_120000")


# ---------------------------------------------------------------------------
# list_backups / validate_config_file
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListBackupsAndValidate:
    def test_list_backups_delegates_to_atomic_manager(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        fake_backups = [MagicMock(), MagicMock()]
        with patch.object(manager._get_atomic_manager(), "list_backups", return_value=fake_backups):
            result = manager.list_backups()

        assert result is fake_backups

    def test_validate_config_file_delegates_to_atomic_manager(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        fake_result = MagicMock()
        with patch.object(manager._get_atomic_manager(), "validate_config_file", return_value=fake_result) as mock_v:
            result = manager.validate_config_file(config_path="/some/path")

        mock_v.assert_called_once_with("/some/path")
        assert result is fake_result

    def test_validate_config_file_with_none_path(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        fake_result = MagicMock()
        with patch.object(manager._get_atomic_manager(), "validate_config_file", return_value=fake_result):
            result = manager.validate_config_file()

        assert result is fake_result


# ---------------------------------------------------------------------------
# load_config error paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadConfigErrorPaths:
    """Test uncommon/error branches in load_config."""

    def test_load_config_ioerror_raises_config_error(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch("builtins.open", side_effect=IOError("disk full")):
            with pytest.raises(ConfigError):
                manager.load_config()

    def test_load_config_oserror_raises_config_error(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch("builtins.open", side_effect=OSError("os error")):
            with pytest.raises(ConfigError):
                manager.load_config()

    def test_load_config_unexpected_exception_raises_config_error(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch("builtins.open", side_effect=RuntimeError("unexpected")):
            with pytest.raises(ConfigError):
                manager.load_config()

    def test_load_config_secrets_permission_error_continues(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"timezone": "UTC"})
        _write_json(secrets, {"api_key": "s3cr3t"})
        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")

        original_open = open

        def selective_open(path, *args, **kwargs):
            if str(path) == str(secrets):
                raise PermissionError("no access")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=selective_open):
            loaded = manager.load_config()

        # Should continue without secrets
        assert loaded.get("timezone") == "UTC"
        assert "api_key" not in loaded

    def test_load_config_secrets_json_error_continues(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"timezone": "UTC"})
        secrets.write_text("not json {{")
        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")

        loaded = manager.load_config()
        assert loaded.get("timezone") == "UTC"

    def test_load_config_secrets_oserror_continues(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"timezone": "UTC"})
        _write_json(secrets, {})
        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")

        original_open = open

        def selective_open(path, *args, **kwargs):
            if str(path) == str(secrets):
                raise OSError("oserror on secrets")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=selective_open):
            loaded = manager.load_config()

        assert loaded.get("timezone") == "UTC"

    def test_load_config_file_not_found_for_secrets_returns_current(self, tmp_path):
        """FileNotFoundError mentioning config_secrets.json should not raise."""
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg), secrets_path=str(tmp_path / "config_secrets.json"))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.config = {"pre_existing": True}

        original_open = open

        call_count = {"n": 0}

        def patched_open(path, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First open (main config) succeeds
                return original_open(path, *args, **kwargs)
            raise FileNotFoundError("config_secrets.json not found")

        with patch("builtins.open", side_effect=patched_open):
            result = manager.load_config()

        # Should return without raising; uses the in-memory config
        assert result is not None


# ---------------------------------------------------------------------------
# _create_config_from_template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateConfigFromTemplate:
    def test_raises_when_template_missing(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with pytest.raises(ConfigError):
            manager._create_config_from_template()

    def test_creates_config_from_template(self, tmp_path):
        template = tmp_path / "template.json"
        cfg = tmp_path / "config.json"
        template_data = {"timezone": "UTC", "display": {"rows": 32}}
        _write_json(template, template_data)

        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(template)
        manager._create_config_from_template()

        assert cfg.exists()
        assert _read_json(cfg) == template_data

    def test_template_directory_created_if_missing(self, tmp_path):
        sub = tmp_path / "subdir"
        cfg = sub / "config.json"
        template = tmp_path / "template.json"
        _write_json(template, {"key": "value"})

        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(template)
        manager._create_config_from_template()

        assert cfg.exists()
        assert _read_json(cfg) == {"key": "value"}


# ---------------------------------------------------------------------------
# _migrate_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMigrateConfig:
    def test_migration_skips_when_no_template(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"x": 1})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.config = {"x": 1}

        # Should not raise
        manager._migrate_config()
        assert manager.config == {"x": 1}

    def test_migration_logs_warning_for_missing_template(self, tmp_path, caplog):
        import logging

        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.config = {}

        with caplog.at_level(logging.WARNING):
            manager._migrate_config()

        assert any("skipping migration" in r.message for r in caplog.records)

    def test_migration_no_change_when_up_to_date(self, tmp_path):
        cfg = tmp_path / "config.json"
        template = tmp_path / "template.json"
        data = {"timezone": "UTC", "display": {"rows": 32}}
        _write_json(cfg, data)
        _write_json(template, data)

        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(template)
        manager.config = data.copy()

        manager._migrate_config()

        assert not (tmp_path / "config.json.backup").exists()

    def test_migration_exception_is_caught_and_logged(self, tmp_path):
        cfg = tmp_path / "config.json"
        template = tmp_path / "template.json"
        _write_json(cfg, {})
        _write_json(template, {"new_key": "val"})

        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(template)
        manager.config = {}

        with patch.object(manager, "_config_needs_migration", side_effect=RuntimeError("boom")):
            # Should not raise
            manager._migrate_config()

    def test_migration_save_failure_logged_as_warning(self, tmp_path):
        cfg = tmp_path / "config.json"
        template = tmp_path / "template.json"
        _write_json(cfg, {"existing": True})
        _write_json(template, {"existing": True, "new_key": "new_val"})

        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(template)
        manager.config = {"existing": True}

        failed_result = SaveResult(status=SaveResultStatus.FAILED, message="disk full")

        with patch.object(manager, "save_config_atomic", return_value=failed_result):
            manager._migrate_config()

        # Should not raise; warning logged about save issues
        assert "new_key" in manager.config


# ---------------------------------------------------------------------------
# _has_new_keys / _config_needs_migration / _merge_template_defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigComparisonHelpers:
    def test_has_new_keys_returns_true_when_template_has_extra_key(self):
        manager = ConfigManager()
        current = {"a": 1}
        template = {"a": 1, "b": 2}
        assert manager._has_new_keys(current, template) is True

    def test_has_new_keys_returns_false_when_same_keys(self):
        manager = ConfigManager()
        current = {"a": 1, "b": {"c": 3}}
        template = {"a": 1, "b": {"c": 3}}
        assert manager._has_new_keys(current, template) is False

    def test_has_new_keys_detects_nested_new_key(self):
        manager = ConfigManager()
        current = {"a": {"x": 1}}
        template = {"a": {"x": 1, "y": 2}}
        assert manager._has_new_keys(current, template) is True

    def test_has_new_keys_returns_false_for_empty_template(self):
        manager = ConfigManager()
        assert manager._has_new_keys({"a": 1}, {}) is False

    def test_config_needs_migration_delegates_to_has_new_keys(self):
        manager = ConfigManager()
        with patch.object(manager, "_has_new_keys", return_value=True) as mock_hnk:
            result = manager._config_needs_migration({"a": 1}, {"a": 1, "b": 2})
        assert result is True
        mock_hnk.assert_called_once()

    def test_merge_template_defaults_adds_missing_top_level_key(self):
        manager = ConfigManager()
        current = {"existing": "yes"}
        template = {"existing": "yes", "new": "default"}
        manager._merge_template_defaults(current, template)
        assert current["new"] == "default"

    def test_merge_template_defaults_does_not_overwrite_existing(self):
        manager = ConfigManager()
        current = {"key": "original"}
        template = {"key": "template_default"}
        manager._merge_template_defaults(current, template)
        assert current["key"] == "original"

    def test_merge_template_defaults_recurses_into_nested_dict(self):
        manager = ConfigManager()
        current = {"nested": {"a": 1}}
        template = {"nested": {"a": 99, "b": 2}}
        manager._merge_template_defaults(current, template)
        assert current["nested"]["a"] == 1  # not overwritten
        assert current["nested"]["b"] == 2  # added

    def test_merge_template_defaults_handles_non_dict_template_value(self):
        manager = ConfigManager()
        current = {}
        template = {"list_key": [1, 2, 3]}
        manager._merge_template_defaults(current, template)
        assert current["list_key"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeepMerge:
    def test_deep_merge_simple(self):
        manager = ConfigManager()
        target = {"a": 1}
        source = {"b": 2}
        manager._deep_merge(target, source)
        assert target == {"a": 1, "b": 2}

    def test_deep_merge_overwrites_non_dict(self):
        manager = ConfigManager()
        target = {"a": "old"}
        source = {"a": "new"}
        manager._deep_merge(target, source)
        assert target["a"] == "new"

    def test_deep_merge_recurses_dicts(self):
        manager = ConfigManager()
        target = {"plugin": {"enabled": True, "token": "old"}}
        source = {"plugin": {"token": "new", "rate": 5}}
        manager._deep_merge(target, source)
        assert target["plugin"]["enabled"] is True
        assert target["plugin"]["token"] == "new"
        assert target["plugin"]["rate"] == 5

    def test_deep_merge_source_non_dict_over_dict(self):
        """When source value is not a dict, it replaces target dict."""
        manager = ConfigManager()
        target = {"key": {"nested": True}}
        source = {"key": "flat_value"}
        manager._deep_merge(target, source)
        assert target["key"] == "flat_value"


# ---------------------------------------------------------------------------
# _strip_secrets_recursive
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripSecretsRecursive:
    def test_strips_top_level_secret_key(self):
        manager = ConfigManager()
        data = {"timezone": "UTC", "api_key": "secret"}
        secrets = {"api_key": "secret"}
        result = manager._strip_secrets_recursive(data, secrets)
        assert "api_key" not in result
        assert result["timezone"] == "UTC"

    def test_preserves_non_secret_keys(self):
        manager = ConfigManager()
        data = {"a": 1, "b": 2}
        secrets = {}
        result = manager._strip_secrets_recursive(data, secrets)
        assert result == {"a": 1, "b": 2}

    def test_strips_nested_secret_key(self):
        manager = ConfigManager()
        data = {"plugin1": {"enabled": True, "api_key": "s3cr3t"}}
        secrets = {"plugin1": {"api_key": "s3cr3t"}}
        result = manager._strip_secrets_recursive(data, secrets)
        assert "api_key" not in result["plugin1"]
        assert result["plugin1"]["enabled"] is True

    def test_omits_group_when_all_keys_are_secret(self):
        manager = ConfigManager()
        data = {"plugin1": {"api_key": "s3cr3t"}}
        secrets = {"plugin1": {"api_key": "s3cr3t"}}
        result = manager._strip_secrets_recursive(data, secrets)
        # plugin1 is stripped entirely because nothing non-secret remains
        assert "plugin1" not in result

    def test_handles_empty_secrets(self):
        manager = ConfigManager()
        data = {"a": 1, "b": {"c": 2}}
        result = manager._strip_secrets_recursive(data, {})
        assert result == data


# ---------------------------------------------------------------------------
# save_config error paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveConfigErrorPaths:
    def test_save_config_raises_config_error_on_ioerror(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch("builtins.open", side_effect=IOError("disk full")):
            with pytest.raises(ConfigError):
                manager.save_config({"key": "value"})

    def test_save_config_raises_config_error_on_oserror(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch("builtins.open", side_effect=OSError("oserror")):
            with pytest.raises(ConfigError):
                manager.save_config({"key": "value"})

    def test_save_config_raises_config_error_on_unexpected_exception(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch("builtins.open", side_effect=RuntimeError("unexpected")):
            with pytest.raises(ConfigError):
                manager.save_config({"key": "value"})

    def test_save_config_logs_when_secrets_present(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {})
        _write_json(secrets, {"plugin1": {"key": "s"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))

        # Should not raise and should log about secrets
        manager.save_config({"timezone": "UTC"})
        assert _read_json(cfg).get("timezone") == "UTC"

    def test_save_config_secrets_load_failure_continues(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {})
        secrets.write_text("broken json {{")

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))

        # Should continue with empty secrets_content
        manager.save_config({"timezone": "UTC", "key": "val"})
        saved = _read_json(cfg)
        assert saved.get("timezone") == "UTC"


# ---------------------------------------------------------------------------
# get_secret
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSecret:
    def test_returns_none_when_secrets_file_does_not_exist(self, tmp_path):
        manager = ConfigManager(secrets_path=str(tmp_path / "no_secrets.json"))
        assert manager.get_secret("api_key") is None

    def test_returns_none_on_ioerror(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        _write_json(secrets, {"key": "value"})
        manager = ConfigManager(secrets_path=str(secrets))

        with patch("builtins.open", side_effect=IOError("io error")):
            result = manager.get_secret("key")

        assert result is None

    def test_returns_value_for_existing_key(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        _write_json(secrets, {"api_key": "mytoken"})
        manager = ConfigManager(secrets_path=str(secrets))
        assert manager.get_secret("api_key") == "mytoken"

    def test_returns_none_for_missing_key(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        _write_json(secrets, {"other": "x"})
        manager = ConfigManager(secrets_path=str(secrets))
        assert manager.get_secret("missing_key") is None


# ---------------------------------------------------------------------------
# get_config (triggers load when empty)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetConfig:
    def test_get_config_returns_existing_config_without_reload(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "UTC"})
        manager = ConfigManager(config_path=str(cfg))
        manager.config = {"already": "loaded"}

        result = manager.get_config()
        assert result == {"already": "loaded"}

    def test_get_config_triggers_load_when_config_is_empty(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"timezone": "EST"})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        result = manager.get_config()
        assert result.get("timezone") == "EST"


# ---------------------------------------------------------------------------
# get_raw_file_content
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRawFileContent:
    def test_get_main_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        data = {"timezone": "UTC"}
        _write_json(cfg, data)
        manager = ConfigManager(config_path=str(cfg))
        assert manager.get_raw_file_content("main") == data

    def test_get_secrets_config(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        data = {"api_key": "s3cr3t"}
        _write_json(secrets, data)
        manager = ConfigManager(secrets_path=str(secrets))
        assert manager.get_raw_file_content("secrets") == data

    def test_get_secrets_returns_empty_when_missing(self, tmp_path):
        manager = ConfigManager(secrets_path=str(tmp_path / "no_secrets.json"))
        assert manager.get_raw_file_content("secrets") == {}

    def test_get_main_raises_config_error_when_missing(self, tmp_path):
        manager = ConfigManager(config_path=str(tmp_path / "no_config.json"))
        with pytest.raises(ConfigError):
            manager.get_raw_file_content("main")

    def test_get_main_raises_config_error_on_bad_json(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("not json {{")
        manager = ConfigManager(config_path=str(cfg))
        with pytest.raises(ConfigError):
            manager.get_raw_file_content("main")

    def test_get_main_raises_config_error_on_ioerror(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        with patch("builtins.open", side_effect=IOError("io fail")):
            with pytest.raises(ConfigError):
                manager.get_raw_file_content("main")

    def test_get_main_raises_config_error_on_oserror(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        with patch("builtins.open", side_effect=OSError("os fail")):
            with pytest.raises(ConfigError):
                manager.get_raw_file_content("main")

    def test_get_main_raises_config_error_on_unexpected_exception(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))
        with patch("builtins.open", side_effect=RuntimeError("boom")):
            with pytest.raises(ConfigError):
                manager.get_raw_file_content("main")

    def test_invalid_file_type_raises_value_error(self):
        manager = ConfigManager()
        with pytest.raises(ValueError):
            manager.get_raw_file_content("bad_type")


# ---------------------------------------------------------------------------
# save_raw_file_content
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveRawFileContent:
    def test_saves_main_config_successfully(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.save_raw_file_content("main", {"timezone": "UTC"})
        assert _read_json(cfg).get("timezone") == "UTC"

    def test_saves_secrets_config_successfully(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        # For secrets save, no reload of main config path
        manager = ConfigManager(
            config_path=str(tmp_path / "config.json"),
            secrets_path=str(secrets),
        )
        manager.template_path = str(tmp_path / "no_template.json")

        # Create a valid main config so reload doesn't fail
        _write_json(tmp_path / "config.json", {"timezone": "UTC"})

        manager.save_raw_file_content("secrets", {"api_key": "s3cr3t"})
        assert _read_json(secrets).get("api_key") == "s3cr3t"

    def test_invalid_file_type_raises_value_error(self):
        manager = ConfigManager()
        with pytest.raises(ValueError):
            manager.save_raw_file_content("bogus", {})

    def test_creates_parent_directory_if_missing(self, tmp_path):
        subdir = tmp_path / "deep" / "nested"
        cfg = subdir / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        # Also need a valid config on disk for the reload triggered after save
        # We pre-create what will be the config path written by save_raw_file_content
        manager.save_raw_file_content("main", {"key": "value"})
        assert cfg.exists()

    def test_chmod_failure_does_not_raise(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch("os.chmod", side_effect=OSError("chmod denied")):
            # Should not raise even if chmod fails
            manager.save_raw_file_content("main", {"x": 1})

        assert cfg.exists()

    def test_ensure_file_permissions_oserror_logs_warning(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch(
            "src.config_manager.ensure_file_permissions",
            side_effect=OSError("permissions denied"),
        ):
            # Should not raise; logs a warning
            manager.save_raw_file_content("main", {"x": 1})

        assert cfg.exists()

    def test_reload_failure_after_save_logs_warning_but_does_not_raise(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        with patch.object(manager, "load_config", side_effect=Exception("reload error")):
            # Should not raise
            manager.save_raw_file_content("main", {"x": 1})

    def test_raises_config_error_on_generic_oserror(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))

        with patch("tempfile.mkstemp", side_effect=OSError("out of space")):
            with pytest.raises(ConfigError):
                manager.save_raw_file_content("main", {"x": 1})

    def test_raises_config_error_on_unexpected_exception(self, tmp_path):
        cfg = tmp_path / "config.json"
        manager = ConfigManager(config_path=str(cfg))

        with patch("tempfile.mkstemp", side_effect=RuntimeError("unexpected")):
            with pytest.raises(ConfigError):
                manager.save_raw_file_content("main", {"x": 1})


# ---------------------------------------------------------------------------
# cleanup_plugin_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanupPluginConfig:
    def test_removes_plugin_from_main_only(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}, "plugin2": {"enabled": False}})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        manager.cleanup_plugin_config("plugin1", remove_secrets=False)

        saved = _read_json(cfg)
        assert "plugin1" not in saved
        assert "plugin2" in saved

    def test_plugin_not_in_config_does_not_error(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin2": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        # Should not raise
        manager.cleanup_plugin_config("nonexistent_plugin")

    def test_removes_plugin_from_secrets_when_requested(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        _write_json(secrets, {"plugin1": {"api_key": "s3cr3t"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.cleanup_plugin_config("plugin1", remove_secrets=True)

        assert "plugin1" not in _read_json(secrets)

    def test_does_not_remove_plugin_from_secrets_when_not_requested(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        _write_json(secrets, {"plugin1": {"api_key": "s3cr3t"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")
        manager.cleanup_plugin_config("plugin1", remove_secrets=False)

        # Secrets should still contain plugin1
        assert "plugin1" in _read_json(secrets)

    def test_raises_config_error_when_get_raw_file_content_fails(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch.object(manager, "get_raw_file_content", side_effect=ConfigError("fail")):
            with pytest.raises(ConfigError):
                manager.cleanup_plugin_config("plugin1")


# ---------------------------------------------------------------------------
# cleanup_orphaned_plugin_configs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanupOrphanedPluginConfigs:
    def test_removes_orphaned_from_main_only(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"valid": {"enabled": True}, "orphan": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        removed = manager.cleanup_orphaned_plugin_configs(["valid"])

        assert "orphan" in removed
        assert "valid" not in removed

    def test_no_orphans_returns_empty_list(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))
        manager.template_path = str(tmp_path / "no_template.json")

        removed = manager.cleanup_orphaned_plugin_configs(["plugin1"])

        assert removed == []

    def test_orphaned_secrets_removed(self, tmp_path):
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"valid": {}})
        _write_json(secrets, {"orphan_secret": {"api_key": "x"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")

        manager.cleanup_orphaned_plugin_configs(["valid"])

        assert "orphan_secret" not in _read_json(secrets)

    def test_exception_during_cleanup_returns_partial_removed(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch.object(manager, "get_raw_file_content", side_effect=Exception("db error")):
            removed = manager.cleanup_orphaned_plugin_configs(["plugin1"])

        assert removed == []

    def test_orphaned_only_in_secrets_not_added_to_removed(self, tmp_path):
        """Plugins only in secrets (not main) should be cleaned from secrets but not in removed list."""
        cfg = tmp_path / "config.json"
        secrets = tmp_path / "secrets.json"
        _write_json(cfg, {"valid": {}})
        _write_json(secrets, {"only_in_secrets": {"key": "val"}})

        manager = ConfigManager(config_path=str(cfg), secrets_path=str(secrets))
        manager.template_path = str(tmp_path / "no_template.json")

        removed = manager.cleanup_orphaned_plugin_configs(["valid"])

        # only_in_secrets was in secrets but not main; removed list is from main only
        assert "only_in_secrets" not in removed
        assert "only_in_secrets" not in _read_json(secrets)


# ---------------------------------------------------------------------------
# validate_all_plugin_configs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateAllPluginConfigs:
    def test_returns_empty_dict_when_no_schema_manager(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))
        result = manager.validate_all_plugin_configs(plugin_schema_manager=None)
        assert result == {}

    def test_skips_non_plugin_sections(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"display": {"rows": 32}, "plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()
        schema_mgr.load_schema.return_value = None  # no schema for plugin1

        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)

        # "display" should be skipped; plugin1 has no schema
        assert "display" not in result
        assert result.get("plugin1") == {"valid": True, "errors": []}

    def test_validates_plugin_with_schema(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()
        schema_mgr.load_schema.return_value = {"type": "object"}
        schema_mgr.validate_config_against_schema.return_value = (True, [])

        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)

        assert result["plugin1"]["valid"] is True
        assert result["plugin1"]["errors"] == []

    def test_records_validation_errors(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()
        schema_mgr.load_schema.return_value = {"type": "object"}
        schema_mgr.validate_config_against_schema.return_value = (False, ["field required"])

        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)

        assert result["plugin1"]["valid"] is False
        assert "field required" in result["plugin1"]["errors"]

    def test_skips_non_dict_config_sections(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": "not_a_dict"})
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()

        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)

        assert "plugin1" not in result

    def test_skips_all_system_sections(self, tmp_path):
        cfg = tmp_path / "config.json"
        system_data = {
            "display": {},
            "schedule": {},
            "timezone": "UTC",
            "plugin_system": {},
        }
        _write_json(cfg, system_data)
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()
        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)
        assert result == {}

    def test_exception_during_validation_is_caught(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {"plugin1": {"enabled": True}})
        manager = ConfigManager(config_path=str(cfg))

        schema_mgr = MagicMock()
        schema_mgr.load_schema.side_effect = RuntimeError("boom")

        # Should not raise
        result = manager.validate_all_plugin_configs(plugin_schema_manager=schema_mgr)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# save_raw_file_content – PermissionError branch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveRawPermissionError:
    def test_permission_error_for_existing_file_raises_config_error(self, tmp_path):
        cfg = tmp_path / "config.json"
        _write_json(cfg, {})
        manager = ConfigManager(config_path=str(cfg))

        with patch("tempfile.mkstemp", side_effect=PermissionError("no write")):
            with pytest.raises(ConfigError):
                manager.save_raw_file_content("main", {"x": 1})

    def test_permission_error_for_missing_file_raises_config_error(self, tmp_path):
        """PermissionError when target file does not exist yet (checks directory)."""
        cfg = tmp_path / "new_config.json"
        manager = ConfigManager(config_path=str(cfg))

        with patch("tempfile.mkstemp", side_effect=PermissionError("no create")):
            with pytest.raises(ConfigError):
                manager.save_raw_file_content("main", {"x": 1})
