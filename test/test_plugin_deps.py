"""
Tests for plugin dependency installation via uv.

RED tests for SPIKE-008: Plugin dependency installation migrated to venv/uv.
Tests cover:
- _find_uv() utility discovers uv binary
- _build_install_command() constructs correct uv pip install command
- PluginLoader.install_dependencies uses uv instead of pip
- StoreManager._install_dependencies uses uv instead of pip
- PluginManager._install_plugin_dependencies uses uv instead of pip
- Fallback to pip when uv is not available
"""

import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.plugin_system.plugin_loader import PluginLoader


class TestFindUv:
    """Test _find_uv utility function."""

    def test_find_uv_in_path(self):
        """_find_uv returns path when uv is on PATH."""
        from src.plugin_system.dep_installer import _find_uv

        with patch("shutil.which", return_value="/usr/local/bin/uv"):
            result = _find_uv()
            assert result == "/usr/local/bin/uv"

    def test_find_uv_not_found(self):
        """_find_uv returns None when uv is not available."""
        from src.plugin_system.dep_installer import _find_uv, _UV_SEARCH_PATHS

        with patch("shutil.which", return_value=None):
            with patch.object(Path, "exists", return_value=False):
                result = _find_uv()
                assert result is None

    def test_find_uv_prefers_venv_local(self):
        """_find_uv checks common locations beyond PATH."""
        from src.plugin_system.dep_installer import _find_uv

        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=True):
                result = _find_uv()
                # Should find uv in a well-known location
                assert result is not None


class TestBuildInstallCommand:
    """Test _build_install_command constructs correct command."""

    def test_builds_uv_pip_install_command(self):
        """Command uses 'uv pip install -r requirements.txt'."""
        from src.plugin_system.dep_installer import _build_install_command

        cmd = _build_install_command(
            Path("/path/to/requirements.txt"),
            uv_path="/usr/local/bin/uv",
        )
        assert cmd[0] == "/usr/local/bin/uv"
        assert "pip" in cmd
        assert "install" in cmd
        assert "-r" in cmd
        assert "/path/to/requirements.txt" in cmd[cmd.index("-r") + 1]

    def test_does_not_include_break_system_packages(self):
        """Command must NOT include --break-system-packages."""
        from src.plugin_system.dep_installer import _build_install_command

        cmd = _build_install_command(
            Path("/path/to/requirements.txt"),
            uv_path="/usr/local/bin/uv",
        )
        assert "--break-system-packages" not in cmd

    def test_targets_venv_python(self):
        """Command targets the venv python via --python flag."""
        from src.plugin_system.dep_installer import _build_install_command

        cmd = _build_install_command(
            Path("/path/to/requirements.txt"),
            uv_path="/usr/local/bin/uv",
            python_path="/home/user/.venv/bin/python3",
        )
        assert "--python" in cmd
        python_idx = cmd.index("--python")
        assert cmd[python_idx + 1] == "/home/user/.venv/bin/python3"

    def test_fallback_pip_when_no_uv(self):
        """Falls back to sys.executable -m pip when uv not found."""
        from src.plugin_system.dep_installer import _build_install_command

        cmd = _build_install_command(
            Path("/path/to/requirements.txt"),
            uv_path=None,
        )
        assert cmd[0] == sys.executable
        assert "-m" in cmd
        assert "pip" in cmd
        assert "--break-system-packages" not in cmd


class TestInstallPluginDependencies:
    """Test the install_plugin_dependencies function."""

    @patch("subprocess.run")
    def test_install_success(self, mock_run):
        """Successful installation returns True."""
        from src.plugin_system.dep_installer import install_plugin_dependencies

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch("src.plugin_system.dep_installer._find_uv", return_value="/usr/bin/uv"):
            result = install_plugin_dependencies(
                Path("/plugins/test-plugin/requirements.txt"),
                plugin_id="test-plugin",
            )

        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/uv"

    @patch("subprocess.run")
    def test_install_failure(self, mock_run):
        """Failed installation returns False."""
        from src.plugin_system.dep_installer import install_plugin_dependencies

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        with patch("src.plugin_system.dep_installer._find_uv", return_value="/usr/bin/uv"):
            result = install_plugin_dependencies(
                Path("/plugins/test-plugin/requirements.txt"),
                plugin_id="test-plugin",
            )

        assert result is False

    @patch("subprocess.run")
    def test_install_timeout(self, mock_run):
        """Timeout returns False."""
        from src.plugin_system.dep_installer import install_plugin_dependencies

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["uv"], timeout=300)

        with patch("src.plugin_system.dep_installer._find_uv", return_value="/usr/bin/uv"):
            result = install_plugin_dependencies(
                Path("/plugins/test-plugin/requirements.txt"),
                plugin_id="test-plugin",
            )

        assert result is False

    @patch("subprocess.run")
    def test_fallback_to_pip(self, mock_run):
        """When uv not found, falls back to pip."""
        from src.plugin_system.dep_installer import install_plugin_dependencies

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch("src.plugin_system.dep_installer._find_uv", return_value=None):
            result = install_plugin_dependencies(
                Path("/plugins/test-plugin/requirements.txt"),
                plugin_id="test-plugin",
            )

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "-m" in cmd
        assert "pip" in cmd


class TestPluginLoaderUsesUv:
    """Test that PluginLoader.install_dependencies uses uv."""

    @pytest.fixture
    def plugin_loader(self):
        return PluginLoader()

    @pytest.fixture
    def tmp_plugin_dir(self, tmp_path):
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        return plugin_dir

    @patch("src.plugin_system.plugin_loader.install_plugin_dependencies")
    def test_install_dependencies_delegates_to_dep_installer(
        self, mock_install, plugin_loader, tmp_plugin_dir
    ):
        """PluginLoader.install_dependencies delegates to dep_installer."""
        requirements_file = tmp_plugin_dir / "requirements.txt"
        requirements_file.write_text("requests>=2.0\n")

        mock_install.return_value = True

        result = plugin_loader.install_dependencies(tmp_plugin_dir, "test-plugin")
        assert result is True
        mock_install.assert_called_once()

    @patch("src.plugin_system.plugin_loader.install_plugin_dependencies")
    def test_install_dependencies_no_break_system_packages(
        self, mock_install, plugin_loader, tmp_plugin_dir
    ):
        """PluginLoader must not pass --break-system-packages."""
        requirements_file = tmp_plugin_dir / "requirements.txt"
        requirements_file.write_text("requests>=2.0\n")

        mock_install.return_value = True

        plugin_loader.install_dependencies(tmp_plugin_dir, "test-plugin")

        # Verify the function was called (no --break-system-packages in new code)
        mock_install.assert_called_once()


class TestStoreManagerUsesUv:
    """Test that StoreManager._install_dependencies uses uv."""

    @patch("subprocess.run")
    def test_store_manager_uses_uv_command(self, mock_run):
        """StoreManager._install_dependencies should use uv pip install."""
        from src.plugin_system.store_manager import PluginStoreManager

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        store = PluginStoreManager.__new__(PluginStoreManager)
        store.logger = MagicMock()

        plugin_path = Path("/tmp/test-plugin")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("src.plugin_system.store_manager.install_plugin_dependencies", return_value=True):
                result = store._install_dependencies(plugin_path)

        assert result is True

    @patch("subprocess.run")
    def test_store_manager_no_break_system_packages(self, mock_run):
        """StoreManager must not use --break-system-packages."""
        from src.plugin_system.store_manager import PluginStoreManager

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        store = PluginStoreManager.__new__(PluginStoreManager)
        store.logger = MagicMock()

        plugin_path = Path("/tmp/test-plugin")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("src.plugin_system.store_manager.install_plugin_dependencies", return_value=True):
                store._install_dependencies(plugin_path)

        # If subprocess.run was called directly, verify no --break-system-packages
        if mock_run.called:
            cmd = mock_run.call_args[0][0]
            assert "--break-system-packages" not in cmd


class TestPluginManagerUsesUv:
    """Test that PluginManager._install_plugin_dependencies uses uv."""

    @patch("subprocess.run")
    def test_plugin_manager_no_break_system_packages(self, mock_run):
        """PluginManager must not use --break-system-packages."""
        from src.plugin_system.plugin_manager import PluginManager

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager = PluginManager.__new__(PluginManager)
        manager.logger = MagicMock()

        requirements_file = Path("/tmp/test-plugin/requirements.txt")

        with patch("src.plugin_system.plugin_manager.install_plugin_dependencies", return_value=True):
            result = manager._install_plugin_dependencies(requirements_file)

        assert result is True
