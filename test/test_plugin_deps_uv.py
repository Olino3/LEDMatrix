"""
RED tests for SPIKE-008: Plugin dependency installation via uv.

Verifies that all three plugin dependency installation paths
(PluginLoader, PluginManager, StoreManager) use `uv pip install`
instead of `pip install --break-system-packages`.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.plugin_system.plugin_loader import PluginLoader


class TestPluginLoaderUsesUv:
    """PluginLoader.install_dependencies must use uv pip install."""

    @pytest.fixture
    def loader(self):
        return PluginLoader()

    @pytest.fixture
    def plugin_with_reqs(self, tmp_path):
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "requirements.txt").write_text("requests>=2.28.0\n")
        # Remove marker so install actually runs
        marker = plugin_dir / ".dependencies_installed"
        if marker.exists():
            marker.unlink()
        return plugin_dir

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_uses_uv_pip_install(self, mock_which, mock_run, loader, plugin_with_reqs):
        """install_dependencies should invoke uv pip install."""
        mock_run.return_value = MagicMock(returncode=0)

        loader.install_dependencies(plugin_with_reqs, "test-plugin")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Must start with uv pip install
        assert cmd[0] == "/usr/local/bin/uv"
        assert cmd[1] == "pip"
        assert cmd[2] == "install"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_no_break_system_packages(self, mock_which, mock_run, loader, plugin_with_reqs):
        """--break-system-packages must NOT appear in the command."""
        mock_run.return_value = MagicMock(returncode=0)

        loader.install_dependencies(plugin_with_reqs, "test-plugin")

        cmd = mock_run.call_args[0][0]
        assert "--break-system-packages" not in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_passes_requirements_file(self, mock_which, mock_run, loader, plugin_with_reqs):
        """The -r <requirements.txt> arguments must be present."""
        mock_run.return_value = MagicMock(returncode=0)

        loader.install_dependencies(plugin_with_reqs, "test-plugin")

        cmd = mock_run.call_args[0][0]
        assert "-r" in cmd
        req_path = str(plugin_with_reqs / "requirements.txt")
        assert req_path in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    def test_falls_back_to_pip_when_no_uv(self, mock_which, mock_run, loader, plugin_with_reqs):
        """When uv is not available, fall back to sys.executable -m pip."""
        mock_run.return_value = MagicMock(returncode=0)

        loader.install_dependencies(plugin_with_reqs, "test-plugin")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert cmd[1] == "-m"
        assert cmd[2] == "pip"
        assert cmd[3] == "install"
        # Even in fallback, no --break-system-packages
        assert "--break-system-packages" not in cmd


class TestPluginManagerUsesUv:
    """PluginManager._install_plugin_dependencies must use uv pip install."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_uses_uv_pip_install(self, mock_which, mock_run, tmp_path):
        """_install_plugin_dependencies should invoke uv pip install."""
        from src.plugin_system.plugin_manager import PluginManager

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28.0\n")

        mock_run.return_value = MagicMock(returncode=0)

        pm = PluginManager.__new__(PluginManager)
        pm.logger = MagicMock()
        pm._install_plugin_dependencies(req_file)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/local/bin/uv"
        assert cmd[1] == "pip"
        assert cmd[2] == "install"
        assert "--break-system-packages" not in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    def test_falls_back_to_pip(self, mock_which, mock_run, tmp_path):
        """Falls back to pip when uv is not available."""
        from src.plugin_system.plugin_manager import PluginManager

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28.0\n")

        mock_run.return_value = MagicMock(returncode=0)

        pm = PluginManager.__new__(PluginManager)
        pm.logger = MagicMock()
        pm._install_plugin_dependencies(req_file)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "--break-system-packages" not in cmd


class TestStoreManagerUsesUv:
    """StoreManager._install_dependencies must use uv pip install."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_uses_uv_pip_install(self, mock_which, mock_run, tmp_path):
        """_install_dependencies should invoke uv pip install."""
        from src.plugin_system.store_manager import PluginStoreManager

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "requirements.txt").write_text("requests>=2.28.0\n")

        mock_run.return_value = MagicMock(returncode=0)

        sm = PluginStoreManager.__new__(PluginStoreManager)
        sm.logger = MagicMock()
        sm._install_dependencies(plugin_dir)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/local/bin/uv"
        assert cmd[1] == "pip"
        assert cmd[2] == "install"
        assert "--break-system-packages" not in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    def test_falls_back_to_pip(self, mock_which, mock_run, tmp_path):
        """Falls back to pip when uv is not available."""
        from src.plugin_system.store_manager import PluginStoreManager

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "requirements.txt").write_text("requests>=2.28.0\n")

        mock_run.return_value = MagicMock(returncode=0)

        sm = PluginStoreManager.__new__(PluginStoreManager)
        sm.logger = MagicMock()
        sm._install_dependencies(plugin_dir)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "--break-system-packages" not in cmd
