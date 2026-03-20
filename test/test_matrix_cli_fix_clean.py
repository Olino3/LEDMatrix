"""
Tests for `matrix fix` and `matrix clean` subcommands in scripts/matrix_cli.py.

Uses Click's CliRunner + unittest.mock to exercise all fix/clean commands
without touching the real filesystem.
"""

import os
import stat
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import matrix_cli
from matrix_cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(*args):
    """Shortcut to invoke a CLI command and return the result."""
    return CliRunner().invoke(cli, list(args))


# ---------------------------------------------------------------------------
# fix permissions — flag combinations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixPermissionsFlags:
    """Verify that --assets/--cache/--plugins/--web flags select the right fixers."""

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_no_flags_runs_all(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions")
        assert result.exit_code == 0
        m_assets.assert_called_once()
        m_cache.assert_called_once()
        m_plugins.assert_called_once()
        m_web.assert_called_once()

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_assets_flag_only(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions", "--assets")
        assert result.exit_code == 0
        m_assets.assert_called_once()
        m_cache.assert_not_called()
        m_plugins.assert_not_called()
        m_web.assert_not_called()

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_cache_flag_only(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions", "--cache")
        assert result.exit_code == 0
        m_assets.assert_not_called()
        m_cache.assert_called_once()
        m_plugins.assert_not_called()
        m_web.assert_not_called()

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_plugins_flag_only(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions", "--plugins")
        assert result.exit_code == 0
        m_assets.assert_not_called()
        m_cache.assert_not_called()
        m_plugins.assert_called_once()
        m_web.assert_not_called()

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_web_flag_only(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions", "--web")
        assert result.exit_code == 0
        m_assets.assert_not_called()
        m_cache.assert_not_called()
        m_plugins.assert_not_called()
        m_web.assert_called_once()

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_multiple_flags(self, m_assets, m_cache, m_plugins, m_web):
        result = _invoke("fix", "permissions", "--assets", "--web")
        assert result.exit_code == 0
        m_assets.assert_called_once()
        m_cache.assert_not_called()
        m_plugins.assert_not_called()
        m_web.assert_called_once()


# ---------------------------------------------------------------------------
# fix permissions — _fix_dir_permissions internals
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixDirPermissions:
    """Test _fix_dir_permissions helper with real temp directories."""

    def test_nonexistent_dir_returns_zero(self, tmp_path):
        result = matrix_cli._fix_dir_permissions(tmp_path / "nope", 0o755, 0o644, "test")
        assert result == 0

    def test_changes_file_permissions(self, tmp_path):
        f = tmp_path / "somefile.txt"
        f.write_text("hello")
        os.chmod(f, 0o777)

        changed = matrix_cli._fix_dir_permissions(tmp_path, 0o755, 0o644, "test")
        assert changed >= 1
        assert stat.S_IMODE(f.stat().st_mode) == 0o644

    def test_changes_dir_permissions(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        os.chmod(d, 0o700)

        changed = matrix_cli._fix_dir_permissions(tmp_path, 0o755, 0o644, "test")
        assert changed >= 1
        assert stat.S_IMODE(d.stat().st_mode) == 0o755

    def test_already_correct_returns_zero(self, tmp_path):
        f = tmp_path / "correct.txt"
        f.write_text("ok")
        os.chmod(f, 0o644)
        os.chmod(tmp_path, 0o755)

        changed = matrix_cli._fix_dir_permissions(tmp_path, 0o755, 0o644, "test")
        assert changed == 0

    def test_output_shows_updated_message(self, tmp_path):
        result = _invoke("fix", "permissions", "--assets")
        # Should not crash regardless of directory state
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# fix permissions — top-level fixers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixPermissionFixers:
    """Test the individual _fix_*_permissions functions."""

    @patch("matrix_cli._fix_dir_permissions", return_value=3)
    def test_fix_assets_calls_helper(self, mock_fdp):
        result = matrix_cli._fix_assets_permissions()
        assert result == 3
        mock_fdp.assert_called_once_with(matrix_cli.ASSETS_DIR, 0o755, 0o644, "assets/")

    @patch("matrix_cli._fix_dir_permissions", return_value=2)
    def test_fix_plugin_calls_helper_for_both_dirs(self, mock_fdp):
        result = matrix_cli._fix_plugin_permissions()
        assert result == 4  # 2 + 2
        assert mock_fdp.call_count == 2

    @patch("matrix_cli._fix_dir_permissions", return_value=1)
    def test_fix_web_calls_helper(self, mock_fdp):
        result = matrix_cli._fix_web_permissions()
        assert result == 1
        mock_fdp.assert_called_once_with(matrix_cli.WEB_DIR, 0o755, 0o644, "web_interface/")


# ---------------------------------------------------------------------------
# fix permissions — output messages
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixPermissionsOutput:
    """Verify output messages for different scenarios."""

    @patch("matrix_cli._fix_web_permissions", return_value=0)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_zero_changes_shows_already_correct(self, *_mocks):
        result = _invoke("fix", "permissions")
        assert "already correct" in result.output

    @patch("matrix_cli._fix_web_permissions", return_value=5)
    @patch("matrix_cli._fix_plugin_permissions", return_value=0)
    @patch("matrix_cli._fix_cache_permissions", return_value=0)
    @patch("matrix_cli._fix_assets_permissions", return_value=0)
    def test_nonzero_changes_shows_count(self, *_mocks):
        result = _invoke("fix", "permissions")
        assert "5 permission(s) updated" in result.output


# ---------------------------------------------------------------------------
# clean cache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanCache:
    """Test `matrix clean cache` subcommand."""

    def test_removes_pycache_dirs(self, tmp_path):
        pycache = tmp_path / "src" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "mod.cpython-311.pyc").write_bytes(b"\x00")

        with patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("clean", "cache")

        assert result.exit_code == 0
        assert not pycache.exists()

    def test_removes_pyc_files(self, tmp_path):
        pyc = tmp_path / "src" / "foo.pyc"
        pyc.parent.mkdir(parents=True)
        pyc.write_bytes(b"\x00")

        with patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("clean", "cache")

        assert result.exit_code == 0
        assert not pyc.exists()

    def test_removes_webassets_cache(self, tmp_path):
        webassets = tmp_path / "web_interface" / ".webassets-cache"
        webassets.mkdir(parents=True)
        (webassets / "sass_cache").write_text("x")

        with patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("clean", "cache")

        assert result.exit_code == 0
        assert not webassets.exists()

    def test_empty_project_succeeds(self, tmp_path):
        with patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("clean", "cache")
        assert result.exit_code == 0
        assert "0 cache dir(s)" in result.output


# ---------------------------------------------------------------------------
# clean deps
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanDeps:
    """Test `matrix clean deps` subcommand."""

    def test_removes_marker_files_from_cache_dir(self, tmp_path):
        """Create a cache dir with marker files and verify they get removed."""
        cache_dir = tmp_path / ".cache" / "ledmatrix"
        cache_dir.mkdir(parents=True)
        marker = cache_dir / "plugin_clock_deps_installed"
        marker.write_text("")

        plugins = tmp_path / "plugins"
        plugins.mkdir()

        # Patch Path.home() to return tmp_path so the search_dirs find our cache
        original_path = Path
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins), patch("matrix_cli.Path") as MockPath:
            # Make Path behave normally except for Path.home() and Path("/var/cache/...")
            MockPath.side_effect = original_path
            MockPath.home.return_value = tmp_path
            result = _invoke("clean", "deps")

        assert result.exit_code == 0
        assert not marker.exists()

    def test_removes_dependency_markers_from_plugins(self, tmp_path):
        """Markers inside plugin directories (.dependencies_installed) are removed."""
        plugins = tmp_path / "plugins"
        clock_dir = plugins / "clock"
        clock_dir.mkdir(parents=True)
        marker = clock_dir / ".dependencies_installed"
        marker.write_text("")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "deps")

        assert result.exit_code == 0
        assert not marker.exists()

    def test_clean_deps_succeeds_with_no_markers(self, tmp_path):
        plugins = tmp_path / "plugins"
        plugins.mkdir()

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "deps")

        assert result.exit_code == 0
        assert "0 dependency marker(s)" in result.output

    def test_clean_deps_removes_plugin_markers(self, tmp_path):
        plugins = tmp_path / "plugins"
        clock_dir = plugins / "clock"
        clock_dir.mkdir(parents=True)
        marker = clock_dir / ".dependencies_installed"
        marker.write_text("")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "deps")

        assert result.exit_code == 0
        assert not marker.exists()
        assert "1 dependency marker(s)" in result.output


# ---------------------------------------------------------------------------
# clean backups
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanBackups:
    """Test `matrix clean backups` subcommand."""

    def test_removes_backup_dirs(self, tmp_path):
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        backup = plugins / "clock_backup"
        backup.mkdir()
        (backup / "manager.py").write_text("old code")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert not backup.exists()

    def test_removes_dotbackup_dirs(self, tmp_path):
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        backup = plugins / "clock.backup.20240101"
        backup.mkdir()

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert not backup.exists()

    def test_removes_bak_files(self, tmp_path):
        plugins = tmp_path / "plugins"
        clock = plugins / "clock"
        clock.mkdir(parents=True)
        bak = clock / "manager.py.bak"
        bak.write_text("old")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert not bak.exists()

    def test_no_backups_found(self, tmp_path):
        plugins = tmp_path / "plugins"
        plugins.mkdir()

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert "0 backup item(s)" in result.output

    def test_nonexistent_plugins_dir_skips(self, tmp_path):
        with patch.object(matrix_cli, "PLUGINS_DIR", tmp_path / "nope"):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert "does not exist" in result.output

    def test_mixed_backups_and_bak_files(self, tmp_path):
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        (plugins / "weather_backup").mkdir()
        clock = plugins / "clock"
        clock.mkdir()
        (clock / "old.bak").write_text("")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins):
            result = _invoke("clean", "backups")

        assert result.exit_code == 0
        assert "2 backup item(s)" in result.output


# ---------------------------------------------------------------------------
# CLI group registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGroupRegistration:
    """Verify fix and clean are registered as groups with help text."""

    def test_fix_group_help(self):
        result = _invoke("fix", "--help")
        assert result.exit_code == 0
        assert "permissions" in result.output

    def test_clean_group_help(self):
        result = _invoke("clean", "--help")
        assert result.exit_code == 0
        assert "cache" in result.output
        assert "deps" in result.output
        assert "backups" in result.output

    def test_fix_permissions_help(self):
        result = _invoke("fix", "permissions", "--help")
        assert result.exit_code == 0
        assert "--assets" in result.output
        assert "--cache" in result.output
        assert "--plugins" in result.output
        assert "--web" in result.output
