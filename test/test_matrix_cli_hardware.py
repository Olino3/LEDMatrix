"""
Tests for SPIKE-011: matrix install --hardware flag for rgbmatrix C-extension build.

Tests cover:
- Non-ARM platform shows error and exits
- Missing apt packages shows install suggestion
- Successful build flow (mocked subprocess)
- Build failure shows actionable error message
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import matrix_cli
from matrix_cli import cli, _install_rgbmatrix_hardware, _RGBMATRIX_APT_DEPS


@pytest.mark.unit
class TestInstallHardwareFlag:
    """Tests for matrix install --hardware via CliRunner."""

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

    @patch("matrix_cli.platform.machine", return_value="x86_64")
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_non_arm_platform_shows_error(self, mock_run, mock_venv, mock_machine):
        """--hardware on x86_64 should print an error and exit non-zero."""
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--hardware", "--no-services"])
            assert result.exit_code != 0
            assert "ARM" in result.output or "arm" in result.output.lower()
            assert "x86_64" in result.output

    @patch("matrix_cli.platform.machine", return_value="aarch64")
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_missing_apt_packages_shows_suggestion(self, mock_run, mock_venv,
                                                    mock_subprocess, mock_machine):
        """When dpkg -l fails for a package, show install suggestion."""
        def subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if cmd[0] == "dpkg" and cmd[1] == "-l":
                # Simulate python3-dev missing
                if cmd[2] == "python3-dev":
                    mock_result.returncode = 1
                else:
                    mock_result.returncode = 0
            else:
                mock_result.returncode = 0
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--hardware", "--no-services"])
            assert result.exit_code != 0
            assert "python3-dev" in result.output
            assert "sudo apt install" in result.output

    @patch("matrix_cli.platform.machine", return_value="aarch64")
    @patch("matrix_cli.shutil.which", return_value="/usr/bin/uv")
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_successful_build(self, mock_run, mock_venv, mock_subprocess,
                              mock_which, mock_machine):
        """Successful build should print success and suggest matrix doctor."""
        def subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--hardware", "--no-services"])
            assert result.exit_code == 0
            assert "rgbmatrix" in result.output.lower()
            assert "doctor" in result.output.lower()

    @patch("matrix_cli.platform.machine", return_value="aarch64")
    @patch("matrix_cli.shutil.which", return_value="/usr/bin/uv")
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli._sync_venv", return_value=0)
    @patch("matrix_cli._run", return_value=0)
    def test_build_failure_shows_error(self, mock_run, mock_venv, mock_subprocess,
                                       mock_which, mock_machine):
        """Failed build should print error with troubleshooting steps."""
        call_count = [0]

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if cmd[0] == "dpkg":
                mock_result.returncode = 0
            else:
                # uv pip install fails
                mock_result.returncode = 1
                mock_result.stderr = "error: compilation failed"
                mock_result.stdout = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect
        with patch("matrix_cli.LEDMATRIX_ROOT", self.root):
            result = self.runner.invoke(cli, ["install", "--hardware", "--no-services"])
            assert result.exit_code != 0
            assert "failed" in result.output.lower()
            assert "Troubleshooting" in result.output


@pytest.mark.unit
class TestInstallHardwareHelper:
    """Direct tests for the _install_rgbmatrix_hardware helper."""

    @patch("matrix_cli.platform.machine", return_value="armv7l")
    @patch("matrix_cli.shutil.which", return_value="/usr/bin/uv")
    @patch("matrix_cli.subprocess.run")
    def test_arm_v7_is_accepted(self, mock_subprocess, mock_which, mock_machine):
        """armv7l should be accepted as a valid ARM platform."""
        def subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect
        # Should not raise SystemExit
        _install_rgbmatrix_hardware()

    @patch("matrix_cli.platform.machine", return_value="aarch64")
    @patch("matrix_cli.subprocess.run")
    def test_all_deps_missing(self, mock_subprocess, mock_machine):
        """When all deps are missing, all should be listed."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        with pytest.raises(SystemExit):
            _install_rgbmatrix_hardware()


@pytest.mark.unit
class TestRgbmatrixAptDeps:
    """Verify the apt deps constant is well-formed."""

    def test_contains_python3_dev(self):
        assert "python3-dev" in _RGBMATRIX_APT_DEPS

    def test_contains_gcc(self):
        assert "gcc" in _RGBMATRIX_APT_DEPS

    def test_contains_make(self):
        assert "make" in _RGBMATRIX_APT_DEPS

    def test_all_entries_are_strings(self):
        assert all(isinstance(p, str) for p in _RGBMATRIX_APT_DEPS)
