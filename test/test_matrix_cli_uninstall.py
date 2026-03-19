"""
Tests for `matrix uninstall` subcommand.

Uses Click's CliRunner + unittest.mock to test the uninstall command
without touching the real filesystem, network, or subprocesses.
"""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import matrix_cli
from matrix_cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _invoke(args, input=None):
    """Run the CLI via CliRunner and return the result."""
    runner = CliRunner(mix_stderr=False)
    return runner.invoke(cli, ["uninstall"] + args, input=input, catch_exceptions=False)


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run so no real commands are executed."""
    mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr("matrix_cli.subprocess.run", mock)
    return mock


@pytest.fixture
def mock_filesystem(monkeypatch, tmp_path):
    """Mock LEDMATRIX_ROOT and filesystem paths to use tmp_path."""
    monkeypatch.setattr("matrix_cli.LEDMATRIX_ROOT", tmp_path)
    # Create expected directory structure
    (tmp_path / "config").mkdir()
    (tmp_path / "plugins").mkdir()
    (tmp_path / ".venv").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Confirmation prompt
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallConfirmation:
    """Confirmation prompt behavior."""

    def test_prompt_abort_on_no(self, mock_subprocess):
        """Without --yes, user is prompted and 'n' aborts."""
        result = _invoke([], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_prompt_yes_continues(self, mock_subprocess):
        """Answering 'y' to the prompt continues the uninstall."""
        result = _invoke([], input="y\n")
        assert result.exit_code == 0
        assert "cancelled" not in result.output.lower()
        # Should have proceeded to stop services
        assert "Step 1/8" in result.output

    def test_yes_flag_skips_prompt(self, mock_subprocess):
        """--yes flag skips the confirmation prompt entirely."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        assert "Are you sure" not in result.output
        # Should proceed directly
        assert "Step 1/8" in result.output


# ---------------------------------------------------------------------------
# Service management
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallServices:
    """Stop and disable systemd services."""

    def test_stops_services(self, mock_subprocess):
        """Uninstall stops ledmatrix and ledmatrix-web services."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        stop_calls = [
            c for c in mock_subprocess.call_args_list
            if "stop" in str(c) and "systemctl" in str(c)
        ]
        assert len(stop_calls) >= 1

    def test_disables_services(self, mock_subprocess):
        """Uninstall disables ledmatrix and ledmatrix-web services."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        disable_calls = [
            c for c in mock_subprocess.call_args_list
            if "disable" in str(c) and "systemctl" in str(c)
        ]
        assert len(disable_calls) >= 1

    def test_daemon_reload_called(self, mock_subprocess):
        """Uninstall calls daemon-reload after removing unit files."""
        # Mock the unit files as existing
        with patch.object(Path, "exists", return_value=True):
            result = _invoke(["--yes"])
        assert result.exit_code == 0
        reload_calls = [
            c for c in mock_subprocess.call_args_list
            if "daemon-reload" in str(c)
        ]
        assert len(reload_calls) >= 1


# ---------------------------------------------------------------------------
# Unit file removal
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallUnitFiles:
    """Remove systemd unit files."""

    def test_removes_unit_files_when_present(self, mock_subprocess):
        """When unit files exist, they are removed."""
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_symlink", return_value=False):
            result = _invoke(["--yes"])
        assert result.exit_code == 0
        all_args = " ".join(str(c) for c in mock_subprocess.call_args_list)
        assert "ledmatrix.service" in all_args

    def test_skips_unit_files_when_absent(self, mock_subprocess):
        """When unit files don't exist, they are skipped gracefully."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "Skipped" in result.output


# ---------------------------------------------------------------------------
# Sudoers removal
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallSudoers:
    """Remove sudoers files."""

    def test_removes_sudoers_files(self, mock_subprocess):
        """Uninstall attempts to handle sudoers directory."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        # Should at least mention sudoers in output
        assert "sudoers" in result.output.lower()


# ---------------------------------------------------------------------------
# Matrix symlink removal
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallSymlink:
    """Remove /usr/local/bin/matrix symlink."""

    def test_removes_matrix_symlink_when_present(self, mock_subprocess):
        """When symlink exists, it is removed."""
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_symlink", return_value=True):
            result = _invoke(["--yes"])
        assert result.exit_code == 0
        all_args = " ".join(str(c) for c in mock_subprocess.call_args_list)
        assert "/usr/local/bin/matrix" in all_args


# ---------------------------------------------------------------------------
# Keep flags
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallKeepConfig:
    """--keep-config preserves config files."""

    def test_keep_config_preserves_config_files(self, mock_subprocess, mock_filesystem):
        """With --keep-config, config files are not deleted."""
        config_json = mock_filesystem / "config" / "config.json"
        config_json.write_text("{}")
        config_secrets = mock_filesystem / "config" / "config_secrets.json"
        config_secrets.write_text("{}")
        result = _invoke(["--yes", "--keep-config"])
        assert result.exit_code == 0
        assert "Kept config files" in result.output
        # Config files should still exist
        assert config_json.exists()
        assert config_secrets.exists()

    def test_without_keep_config_removes_config(self, mock_subprocess, mock_filesystem):
        """Without --keep-config, config files are removed."""
        config_json = mock_filesystem / "config" / "config.json"
        config_json.write_text("{}")
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        assert not config_json.exists()


@pytest.mark.unit
class TestUninstallKeepPlugins:
    """--keep-plugins preserves plugins directory."""

    def test_keep_plugins_preserves_plugins(self, mock_subprocess, mock_filesystem):
        """With --keep-plugins, plugins directory contents are preserved."""
        plugin_dir = mock_filesystem / "plugins" / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("{}")
        result = _invoke(["--yes", "--keep-plugins"])
        assert result.exit_code == 0
        assert "Kept plugins" in result.output
        assert plugin_dir.exists()

    def test_without_keep_plugins_removes_contents(self, mock_subprocess, mock_filesystem):
        """Without --keep-plugins, plugin contents are removed."""
        plugin_dir = mock_filesystem / "plugins" / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("{}")
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        # Plugin directory itself should still exist, but contents removed
        assert (mock_filesystem / "plugins").exists()
        assert not plugin_dir.exists()


@pytest.mark.unit
class TestUninstallKeepVenv:
    """--keep-venv preserves .venv directory."""

    def test_keep_venv_preserves_venv(self, mock_subprocess, mock_filesystem):
        """With --keep-venv, .venv directory is preserved."""
        result = _invoke(["--yes", "--keep-venv"])
        assert result.exit_code == 0
        assert "Kept .venv" in result.output
        assert (mock_filesystem / ".venv").exists()

    def test_without_keep_venv_removes_venv(self, mock_subprocess, mock_filesystem):
        """Without --keep-venv, .venv is removed."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        assert not (mock_filesystem / ".venv").exists()


# ---------------------------------------------------------------------------
# --all flag
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallAll:
    """--all overrides all keep flags."""

    def test_all_overrides_keep_flags(self, mock_subprocess, mock_filesystem):
        """--all with --keep-config/plugins/venv still removes everything."""
        config_json = mock_filesystem / "config" / "config.json"
        config_json.write_text("{}")
        plugin_dir = mock_filesystem / "plugins" / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("{}")

        result = _invoke(["--yes", "--all", "--keep-config", "--keep-plugins", "--keep-venv"])
        assert result.exit_code == 0
        # --all overrides keep flags, so data should be removed
        assert not config_json.exists()
        assert not plugin_dir.exists()
        assert not (mock_filesystem / ".venv").exists()
        # "Kept" messages should NOT appear
        assert "Kept config" not in result.output
        assert "Kept plugins" not in result.output
        assert "Kept .venv" not in result.output

    def test_all_without_keep_flags(self, mock_subprocess, mock_filesystem):
        """--all alone removes everything."""
        config_json = mock_filesystem / "config" / "config.json"
        config_json.write_text("{}")
        result = _invoke(["--yes", "--all"])
        assert result.exit_code == 0
        assert not config_json.exists()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallIdempotency:
    """Removing already-absent resources doesn't error."""

    def test_idempotent_no_errors(self, mock_subprocess):
        """Running uninstall when nothing is installed doesn't error."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0

    def test_service_stop_failure_does_not_abort(self, mock_subprocess):
        """If services are already stopped, uninstall continues."""
        def side_effect(cmd, **kwargs):
            m = MagicMock()
            if "stop" in cmd:
                m.returncode = 5  # systemd: unit not loaded
            else:
                m.returncode = 0
            return m
        mock_subprocess.side_effect = side_effect
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        # Should have continued past stop step
        assert "Step 2/8" in result.output

    def test_double_uninstall_succeeds(self, mock_subprocess, mock_filesystem):
        """Running uninstall twice doesn't fail."""
        result1 = _invoke(["--yes"])
        assert result1.exit_code == 0
        result2 = _invoke(["--yes"])
        assert result2.exit_code == 0


# ---------------------------------------------------------------------------
# Group removal
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUninstallGroupRemoval:
    """Remove ledmatrix group."""

    def test_attempts_groupdel(self, mock_subprocess):
        """Uninstall attempts to remove ledmatrix group."""
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        all_args = " ".join(str(c) for c in mock_subprocess.call_args_list)
        assert "groupdel" in all_args

    def test_groupdel_failure_does_not_abort(self, mock_subprocess):
        """If groupdel fails (group doesn't exist), uninstall continues."""
        def side_effect(cmd, **kwargs):
            m = MagicMock()
            if "groupdel" in cmd:
                m.returncode = 6  # group doesn't exist
            else:
                m.returncode = 0
            return m
        mock_subprocess.side_effect = side_effect
        result = _invoke(["--yes"])
        assert result.exit_code == 0
        # Should complete all steps
        assert "Step 8/8" in result.output
