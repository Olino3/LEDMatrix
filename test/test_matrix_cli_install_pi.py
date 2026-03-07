"""
Tests for SPIKE-010: Expand `matrix install` with Pi-specific setup steps.

Tests cover:
- _is_raspberry_pi() helper
- _run_install_script() helper
- --permissions flag (delegates to setup_cache.sh, configure_web_sudo.sh,
  configure_wifi_permissions.sh)
- --services flag (delegates to install_web_service.sh, install_wifi_monitor.sh)
- --prerequisites flag (apt package installation)
- Flags are no-ops on non-Pi platforms (dev machines)
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import matrix_cli
from matrix_cli import (
    cli,
    _is_raspberry_pi,
    _run_install_script,
    _PI_APT_PACKAGES,
)


# ---------------------------------------------------------------------------
# _is_raspberry_pi() helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsRaspberryPi:
    """Tests for Pi hardware detection helper."""

    def test_returns_true_when_dev_mem_exists(self):
        with patch("matrix_cli._PI_DEV_MEM") as mock_dev_mem, \
             patch("matrix_cli._PI_MODEL_PATH") as mock_model:
            mock_dev_mem.exists.return_value = True
            mock_model.exists.return_value = False
            assert _is_raspberry_pi() is True

    def test_returns_false_when_nothing_present(self):
        with patch("matrix_cli._PI_DEV_MEM") as mock_dev_mem, \
             patch("matrix_cli._PI_MODEL_PATH") as mock_model:
            mock_dev_mem.exists.return_value = False
            mock_model.exists.return_value = False
            assert _is_raspberry_pi() is False

    def test_returns_true_when_model_file_contains_raspberry(self, tmp_path):
        model_file = tmp_path / "model"
        model_file.write_text("Raspberry Pi 4 Model B Rev 1.4\n")
        with patch("matrix_cli._PI_DEV_MEM") as mock_dev_mem, \
             patch("matrix_cli._PI_MODEL_PATH", model_file):
            mock_dev_mem.exists.return_value = False
            assert _is_raspberry_pi() is True

    def test_returns_false_when_model_file_not_raspberry(self, tmp_path):
        model_file = tmp_path / "model"
        model_file.write_text("Some Other Board\n")
        with patch("matrix_cli._PI_DEV_MEM") as mock_dev_mem, \
             patch("matrix_cli._PI_MODEL_PATH", model_file):
            mock_dev_mem.exists.return_value = False
            assert _is_raspberry_pi() is False


# ---------------------------------------------------------------------------
# _run_install_script() helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunInstallScript:
    """Tests for _run_install_script helper."""

    def test_runs_script_with_sudo(self, tmp_path):
        scripts_dir = tmp_path / "scripts" / "install"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho ok")
        with patch("matrix_cli.LEDMATRIX_ROOT", tmp_path), \
             patch("matrix_cli._run", return_value=0) as mock_run:
            rc = _run_install_script("test_script.sh")
            assert rc == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "sudo"
            assert args[1] == "bash"
            assert "test_script.sh" in args[2]

    def test_runs_script_without_sudo(self, tmp_path):
        scripts_dir = tmp_path / "scripts" / "install"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho ok")
        with patch("matrix_cli.LEDMATRIX_ROOT", tmp_path), \
             patch("matrix_cli._run", return_value=0) as mock_run:
            rc = _run_install_script("test_script.sh", use_sudo=False)
            assert rc == 0
            args = mock_run.call_args[0][0]
            assert args[0] == "bash"
            assert "sudo" not in args

    def test_returns_1_when_script_missing(self, tmp_path):
        scripts_dir = tmp_path / "scripts" / "install"
        scripts_dir.mkdir(parents=True)
        with patch("matrix_cli.LEDMATRIX_ROOT", tmp_path):
            rc = _run_install_script("nonexistent.sh")
            assert rc == 1


# ---------------------------------------------------------------------------
# matrix install --permissions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallPermissions:
    """Tests for matrix install --permissions flag."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.runner = CliRunner()
        self.root = tmp_path / "LEDMatrix"
        self.root.mkdir()
        (self.root / "config").mkdir()
        (self.root / "config" / "config.template.json").write_text("{}")
        (self.root / "config" / "config.json").write_text("{}")
        scripts_install = self.root / "scripts" / "install"
        scripts_install.mkdir(parents=True)
        for script in ["setup_cache.sh", "configure_web_sudo.sh",
                        "configure_wifi_permissions.sh", "install_service.sh"]:
            (scripts_install / script).write_text("#!/bin/bash\necho ok")

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_permissions_runs_setup_cache(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--permissions", "--no-services"])
            assert result.exit_code == 0
            calls_str = str(mock_run.call_args_list)
            assert "setup_cache.sh" in calls_str, f"setup_cache.sh not called. Calls: {calls_str}"

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_permissions_runs_configure_web_sudo(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--permissions", "--no-services"])
            assert result.exit_code == 0
            assert "configure_web_sudo.sh" in str(mock_run.call_args_list)

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_permissions_runs_configure_wifi_permissions(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--permissions", "--no-services"])
            assert result.exit_code == 0
            assert "configure_wifi_permissions.sh" in str(mock_run.call_args_list)

    @patch("matrix_cli._is_raspberry_pi", return_value=False)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_permissions_skipped_on_non_pi(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--permissions", "--no-services"])
            assert result.exit_code == 0
            assert "not a Raspberry Pi" in result.output
            # No permission scripts should have been called
            perms_called = any(
                "setup_cache.sh" in str(c) or "configure_web_sudo.sh" in str(c)
                for c in mock_run.call_args_list
            )
            assert not perms_called

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run")
    def test_permissions_reports_script_failure(self, mock_run, mock_venv, mock_pi):
        # First call (setup_cache.sh) fails, remaining continue
        mock_run.return_value = 1
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--permissions", "--no-services"])
            assert result.exit_code == 0  # continues despite individual failures
            assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# matrix install --services
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallExtraServices:
    """Tests for matrix install --services flag (web + WiFi services)."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.runner = CliRunner()
        self.root = tmp_path / "LEDMatrix"
        self.root.mkdir()
        (self.root / "config").mkdir()
        (self.root / "config" / "config.template.json").write_text("{}")
        (self.root / "config" / "config.json").write_text("{}")
        scripts_install = self.root / "scripts" / "install"
        scripts_install.mkdir(parents=True)
        for script in ["install_service.sh", "install_web_service.sh",
                        "install_wifi_monitor.sh"]:
            (scripts_install / script).write_text("#!/bin/bash\necho ok")

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_services_installs_web_service(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--services", "--no-services"])
            assert result.exit_code == 0
            assert "install_web_service.sh" in str(mock_run.call_args_list)

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_services_installs_wifi_monitor(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--services", "--no-services"])
            assert result.exit_code == 0
            assert "install_wifi_monitor.sh" in str(mock_run.call_args_list)

    @patch("matrix_cli._is_raspberry_pi", return_value=False)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_services_skipped_on_non_pi(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--services", "--no-services"])
            assert result.exit_code == 0
            assert "not a Raspberry Pi" in result.output


# ---------------------------------------------------------------------------
# matrix install --prerequisites
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallPrerequisites:
    """Tests for matrix install --prerequisites flag (apt packages)."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.runner = CliRunner()
        self.root = tmp_path / "LEDMatrix"
        self.root.mkdir()
        (self.root / "config").mkdir()
        (self.root / "config" / "config.template.json").write_text("{}")
        (self.root / "config" / "config.json").write_text("{}")
        scripts_install = self.root / "scripts" / "install"
        scripts_install.mkdir(parents=True)
        (scripts_install / "install_service.sh").write_text("#!/bin/bash\necho ok")

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_prerequisites_runs_apt(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--prerequisites", "--no-services"])
            assert result.exit_code == 0
            calls_str = str(mock_run.call_args_list)
            assert "apt-get" in calls_str

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_prerequisites_installs_required_packages(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--prerequisites", "--no-services"])
            assert result.exit_code == 0
            # Find the apt-get install call
            install_call = None
            for c in mock_run.call_args_list:
                args = c[0][0] if c[0] else []
                if "apt-get" in args and "install" in args:
                    install_call = args
                    break
            assert install_call is not None, "apt-get install not called"
            assert "build-essential" in install_call

    @patch("matrix_cli._is_raspberry_pi", return_value=False)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_prerequisites_skipped_on_non_pi(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--prerequisites", "--no-services"])
            assert result.exit_code == 0
            assert "not a Raspberry Pi" in result.output
            apt_called = any("apt" in str(c) for c in mock_run.call_args_list)
            assert not apt_called

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run")
    def test_prerequisites_apt_update_failure_continues(self, mock_run, mock_venv, mock_pi):
        """apt-get update failure should warn but not abort."""
        def side_effect(cmd, **kwargs):
            if "update" in cmd:
                return 1
            return 0
        mock_run.side_effect = side_effect
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--prerequisites", "--no-services"])
            assert result.exit_code == 0
            assert "update failed" in result.output.lower() or "continuing" in result.output.lower()


# ---------------------------------------------------------------------------
# Integration: flags combined / backward compatibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallFlagsCombined:
    """Tests for combining multiple Pi-specific flags and backward compat."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.runner = CliRunner()
        self.root = tmp_path / "LEDMatrix"
        self.root.mkdir()
        (self.root / "config").mkdir()
        (self.root / "config" / "config.template.json").write_text("{}")
        (self.root / "config" / "config.json").write_text("{}")
        scripts_install = self.root / "scripts" / "install"
        scripts_install.mkdir(parents=True)
        for script in ["install_service.sh", "install_web_service.sh",
                        "install_wifi_monitor.sh", "setup_cache.sh",
                        "configure_web_sudo.sh", "configure_wifi_permissions.sh"]:
            (scripts_install / script).write_text("#!/bin/bash\necho ok")

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_permissions_and_services_together(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, [
                "install", "--permissions", "--services", "--no-services"
            ])
            assert result.exit_code == 0
            calls_str = str(mock_run.call_args_list)
            assert "setup_cache.sh" in calls_str
            assert "install_web_service.sh" in calls_str

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_existing_install_behavior_unchanged(self, mock_run, mock_venv, mock_pi):
        """Without new flags, install behaves exactly as before."""
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--no-services"])
            assert result.exit_code == 0
            # No Pi-specific scripts should be called
            pi_scripts = ["setup_cache.sh", "configure_web_sudo.sh",
                          "install_web_service.sh", "install_wifi_monitor.sh"]
            calls_str = str(mock_run.call_args_list)
            for script in pi_scripts:
                assert script not in calls_str, \
                    f"{script} should not be called without explicit flag"

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_all_flags_together(self, mock_run, mock_venv, mock_pi):
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, [
                "install", "--prerequisites", "--permissions", "--services",
                "--no-services"
            ])
            assert result.exit_code == 0
            calls_str = str(mock_run.call_args_list)
            assert "apt-get" in calls_str
            assert "setup_cache.sh" in calls_str
            assert "install_web_service.sh" in calls_str
            assert "install_wifi_monitor.sh" in calls_str


# ---------------------------------------------------------------------------
# _PI_APT_PACKAGES constant
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPiAptPackages:
    """Verify the apt packages list is well-formed."""

    def test_contains_build_essential(self):
        assert "build-essential" in _PI_APT_PACKAGES

    def test_contains_python3_dev(self):
        assert "python3-dev" in _PI_APT_PACKAGES

    def test_all_entries_are_strings(self):
        assert all(isinstance(p, str) for p in _PI_APT_PACKAGES)

    def test_no_empty_entries(self):
        assert all(p.strip() for p in _PI_APT_PACKAGES)
