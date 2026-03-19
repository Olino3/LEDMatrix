"""
Tests for the ``matrix diagnose`` subcommand group.

Uses Click's CliRunner and unittest.mock to exercise each subcommand
without touching the real filesystem, network, or subprocesses.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from click.testing import CliRunner

# Ensure the scripts directory is importable.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import matrix_cli
from matrix_cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _invoke(*args):
    """Shorthand: invoke the CLI and return the Click Result."""
    return CliRunner().invoke(cli, list(args))


# ---------------------------------------------------------------------------
# diagnose --help
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagnoseGroup:
    """The ``matrix diagnose`` group itself."""

    def test_help_lists_subcommands(self):
        result = _invoke("diagnose", "--help")
        assert result.exit_code == 0
        assert "web" in result.output
        assert "network" in result.output
        assert "plugins" in result.output

    def test_bare_diagnose_shows_help(self):
        result = _invoke("diagnose")
        # Click groups show usage/help when invoked without a subcommand (exit 2)
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "web" in result.output


# ---------------------------------------------------------------------------
# diagnose web
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagnoseWeb:
    """``matrix diagnose web``."""

    def _run_web(self, port_open=True, status_code=200, health_code=200,
                 files_exist=True, static_exists=True, templates_exist=True,
                 autostart=True, svc_exists=False, svc_active="active"):
        """Run ``diagnose web`` with configurable mocked conditions."""
        # Build patches
        patches = {}

        with patch.object(matrix_cli, "_check_port_open", return_value=port_open), \
             patch.object(matrix_cli, "_check_url") as mock_url, \
             patch.object(matrix_cli, "_read_config", return_value={
                 "web_display_autostart": autostart,
             }), \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.is_dir") as mock_is_dir, \
             patch("pathlib.Path.rglob") as mock_rglob, \
             patch("subprocess.run") as mock_subp:

            # _check_url returns different values per call
            def url_side_effect(url, timeout=3.0):
                if "status" in url:
                    return status_code
                if "health" in url:
                    return health_code
                return None
            mock_url.side_effect = url_side_effect

            # Path.exists returns True for files we want to exist
            mock_exists.return_value = files_exist

            # Path.is_dir for static/templates
            mock_is_dir.return_value = static_exists

            # rglob returns some fake files
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_rglob.return_value = [mock_file] * 5

            # systemd
            mock_subp.return_value = MagicMock(
                stdout=svc_active + "\n", returncode=0
            )

            result = _invoke("diagnose", "web")

        return result

    def test_web_all_healthy(self):
        result = self._run_web()
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_web_port_closed_shows_fail(self):
        result = self._run_web(port_open=False)
        assert result.exit_code == 0
        assert "FAIL" in result.output
        assert "5000" in result.output

    def test_web_api_not_responding(self):
        result = self._run_web(status_code=None)
        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_web_api_500_shows_warn(self):
        result = self._run_web(status_code=500)
        assert result.exit_code == 0
        assert "WARN" in result.output

    def test_web_autostart_false_shows_warn(self):
        result = self._run_web(autostart=False)
        assert result.exit_code == 0
        assert "WARN" in result.output

    def test_web_output_contains_summary_counts(self):
        result = self._run_web()
        assert "passed" in result.output
        assert "failed" in result.output


# ---------------------------------------------------------------------------
# diagnose network
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagnoseNetwork:
    """``matrix diagnose network``."""

    def test_network_all_healthy(self):
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_network_ping_fails(self):
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "FAIL" in result.output
        assert "Unreachable" in result.output

    def test_network_dns_fails(self):
        import socket as _socket
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", side_effect=_socket.gaierror("Name resolution failed")):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_network_captive_portal_detected(self):
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=302), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "captive portal" in result.output.lower() or "WARN" in result.output

    def test_network_wifi_on_pi(self):
        iwconfig_output = (
            'wlan0     IEEE 802.11  ESSID:"MyNetwork"\n'
            '          Mode:Managed  Frequency:2.437 GHz\n'
            '          Link Quality=70/70  Signal level=-30 dBm\n'
        )
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=True), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            def run_side_effect(cmd, **kwargs):
                if "ping" in cmd:
                    return MagicMock(returncode=0, stdout="", stderr="")
                if "iwconfig" in cmd:
                    return MagicMock(returncode=0, stdout=iwconfig_output, stderr="")
                if "systemctl" in cmd:
                    return MagicMock(returncode=0, stdout="active\n", stderr="")
                return MagicMock(returncode=1, stdout="", stderr="")
            mock_run.side_effect = run_side_effect
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "MyNetwork" in result.output
        assert "-30 dBm" in result.output

    def test_network_not_pi_skips_wifi(self):
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert result.exit_code == 0
        assert "Skipped" in result.output or "not a Raspberry Pi" in result.output

    def test_network_output_contains_summary(self):
        with patch("subprocess.run") as mock_run, \
             patch.object(matrix_cli, "_check_url", return_value=204), \
             patch.object(matrix_cli, "_is_raspberry_pi", return_value=False), \
             patch("socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("151.101.0.223", 443))
             ]):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _invoke("diagnose", "network")

        assert "passed" in result.output
        assert "failed" in result.output


# ---------------------------------------------------------------------------
# diagnose plugins
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagnosePlugins:
    """``matrix diagnose plugins``."""

    def _make_plugin(self, plugins_dir, pid, manifest=None, schema=True,
                     manager=True, deps_marker=True, requirements=""):
        """Create a minimal plugin directory for testing."""
        pdir = plugins_dir / pid
        pdir.mkdir(exist_ok=True)
        if manifest is not None:
            (pdir / "manifest.json").write_text(json.dumps(manifest))
        if schema:
            (pdir / "config_schema.json").write_text(json.dumps({"type": "object"}))
        if manager:
            (pdir / "manager.py").write_text("# stub")
        if deps_marker:
            (pdir / ".dependencies_installed").write_text("")
        (pdir / "requirements.txt").write_text(requirements)
        return pdir

    def test_plugins_healthy(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "clock-simple", manifest={
            "id": "clock-simple", "name": "Clock", "version": "1.0.0",
        })
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert result.exit_code == 0
        assert "PASS" in result.output
        # Rich table may truncate plugin name; check for partial match
        assert "clock" in result.output.lower() or "1.0.0" in result.output

    def test_plugins_missing_manifest(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "bad-plugin", manifest=None)
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "FAIL" in result.output
        assert "manifest" in result.output.lower()

    def test_plugins_missing_manager(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "no-entry", manifest={
            "id": "no-entry", "name": "No Entry", "version": "1.0.0",
        }, manager=False)
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "FAIL" in result.output
        assert "manager.py" in result.output

    def test_plugins_missing_deps_marker_with_requirements(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "needs-deps", manifest={
            "id": "needs-deps", "name": "Needs Deps", "version": "1.0.0",
        }, deps_marker=False, requirements="requests>=2.0")
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "WARN" in result.output

    def test_plugins_no_requirements_no_marker_is_ok(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "simple", manifest={
            "id": "simple", "name": "Simple", "version": "1.0.0",
        }, deps_marker=False, requirements="")
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert result.exit_code == 0
        # Should show PASS for no requirements
        assert "No requirements" in result.output

    def test_plugins_dir_missing(self, tmp_path):
        missing = tmp_path / "plugins_nope"
        with patch.object(matrix_cli, "PLUGINS_DIR", missing):
            result = _invoke("diagnose", "plugins")

        assert "FAIL" in result.output
        assert "Not found" in result.output

    def test_plugins_empty_dir(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "WARN" in result.output
        assert "No plugins found" in result.output

    def test_plugins_invalid_schema_json(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        pdir = plugins_dir / "bad-schema"
        pdir.mkdir()
        (pdir / "manifest.json").write_text(json.dumps({
            "id": "bad-schema", "name": "Bad Schema", "version": "1.0.0",
        }))
        (pdir / "config_schema.json").write_text("{not valid json")
        (pdir / "manager.py").write_text("# stub")
        (pdir / ".dependencies_installed").write_text("")
        (pdir / "requirements.txt").write_text("")

        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "FAIL" in result.output
        assert "Invalid JSON" in result.output

    def test_plugins_manifest_missing_fields(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "incomplete", manifest={
            "id": "incomplete",
            # missing name and version
        })
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "WARN" in result.output
        assert "Missing fields" in result.output

    def test_plugins_output_contains_summary(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        self._make_plugin(plugins_dir, "test-plugin", manifest={
            "id": "test-plugin", "name": "Test", "version": "1.0.0",
        })
        with patch.object(matrix_cli, "PLUGINS_DIR", plugins_dir), \
             patch.object(matrix_cli, "LEDMATRIX_ROOT", tmp_path):
            result = _invoke("diagnose", "plugins")

        assert "passed" in result.output
        assert "failed" in result.output


# ---------------------------------------------------------------------------
# _DiagResult unit tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagResult:
    """Direct tests for the _DiagResult helper."""

    def test_ok_increments_passed(self):
        r = matrix_cli._DiagResult()
        r.ok("test check", "detail")
        assert r.passed == 1
        assert r.failed == 0
        assert r.warnings == 0
        assert len(r.rows) == 1

    def test_fail_increments_failed(self):
        r = matrix_cli._DiagResult()
        r.fail("test check")
        assert r.failed == 1

    def test_warn_increments_warnings(self):
        r = matrix_cli._DiagResult()
        r.warn("test check")
        assert r.warnings == 1

    def test_render_produces_output(self, capsys):
        r = matrix_cli._DiagResult()
        r.ok("check1")
        r.fail("check2", "bad")
        r.warn("check3", "meh")
        r.render("Test Title")
        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "1 passed" in captured.out
        assert "1 failed" in captured.out
        assert "1 warning" in captured.out


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiagnoseHelpers:
    """_check_port_open and _check_url."""

    def test_check_port_open_success(self):
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock()
            mock_conn.return_value.__exit__ = MagicMock()
            assert matrix_cli._check_port_open("localhost", 5000) is True

    def test_check_port_open_failure(self):
        with patch("socket.create_connection", side_effect=OSError("refused")):
            assert matrix_cli._check_port_open("localhost", 5000) is False

    def test_check_url_returns_status_code(self):
        with patch.object(matrix_cli, "requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=200)
            assert matrix_cli._check_url("http://example.com") == 200

    def test_check_url_returns_none_on_exception(self):
        with patch.object(matrix_cli, "requests") as mock_req:
            mock_req.get.side_effect = Exception("timeout")
            assert matrix_cli._check_url("http://example.com") is None
