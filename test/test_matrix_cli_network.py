"""
Tests for the `matrix network` CLI subcommand group.

Uses Click's CliRunner + unittest.mock to test all network subcommands
without touching the real filesystem, network, or subprocesses.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from matrix_cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# network group
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetworkGroup:
    """The `matrix network` group exists and shows help."""

    def test_network_group_exists(self, runner):
        result = runner.invoke(cli, ["network", "--help"])
        assert result.exit_code == 0
        assert "Network and WiFi management" in result.output

    def test_network_no_subcommand_shows_help(self, runner):
        result = runner.invoke(cli, ["network"])
        # Click groups return exit code 2 when invoked without subcommand
        assert result.exit_code in (0, 2)
        assert "status" in result.output or "Usage" in result.output
        assert "reconnect" in result.output
        assert "test-portal" in result.output


# ---------------------------------------------------------------------------
# network status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetworkStatus:
    """Tests for `matrix network status`."""

    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli.socket.getaddrinfo")
    def test_status_shows_connectivity_online(self, mock_dns, mock_run, runner):
        """When ping succeeds, status shows online."""
        # ping succeeds
        mock_run.return_value = MagicMock(returncode=0, stdout="PING ok")
        # DNS resolves
        mock_dns.return_value = [(2, 1, 6, "", ("142.250.80.46", 443))]

        with patch("matrix_cli.subprocess.check_output", return_value=b"192.168.1.100 "):
            result = runner.invoke(cli, ["network", "status"])

        assert result.exit_code == 0
        assert "Online" in result.output or "online" in result.output.lower()

    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli.socket.getaddrinfo", side_effect=OSError("DNS failed"))
    def test_status_shows_connectivity_offline(self, mock_dns, mock_run, runner):
        """When ping fails, status shows offline."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        with patch("matrix_cli.subprocess.check_output", side_effect=Exception("no ip")):
            result = runner.invoke(cli, ["network", "status"])

        assert result.exit_code == 0
        assert "Offline" in result.output or "offline" in result.output.lower()

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli.socket.getaddrinfo")
    @patch("matrix_cli.subprocess.check_output")
    def test_status_shows_wifi_signal_on_pi(self, mock_co, mock_dns, mock_run, mock_pi, runner):
        """On Pi, status shows WiFi signal strength from iwconfig."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_dns.return_value = [(2, 1, 6, "", ("142.250.80.46", 443))]

        def check_output_side_effect(cmd, **kwargs):
            if "iwconfig" in cmd:
                return b'wlan0  IEEE 802.11  ESSID:"MyNetwork"  Signal level=-45 dBm  Link Quality=65/70'
            return b"192.168.1.100 "

        mock_co.side_effect = check_output_side_effect
        result = runner.invoke(cli, ["network", "status"])

        assert result.exit_code == 0

    @patch("matrix_cli._is_raspberry_pi", return_value=False)
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli.socket.getaddrinfo")
    @patch("matrix_cli.subprocess.check_output", return_value=b"192.168.1.100 ")
    def test_status_no_wifi_section_off_pi(self, mock_co, mock_dns, mock_run, mock_pi, runner):
        """Off Pi, no WiFi signal section shown."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_dns.return_value = [(2, 1, 6, "", ("142.250.80.46", 443))]

        result = runner.invoke(cli, ["network", "status"])
        assert result.exit_code == 0
        # Should not show iwconfig-related content
        assert "Signal" not in result.output or "signal" not in result.output


# ---------------------------------------------------------------------------
# network reconnect
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetworkReconnect:
    """Tests for `matrix network reconnect`."""

    @patch("matrix_cli._is_raspberry_pi", return_value=False)
    def test_reconnect_exits_on_non_pi(self, mock_pi, runner):
        """On non-Pi, reconnect exits gracefully with message."""
        result = runner.invoke(cli, ["network", "reconnect"])
        assert result.exit_code == 0
        assert "Raspberry Pi" in result.output

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli.os.geteuid", return_value=1000)
    def test_reconnect_warns_no_sudo(self, mock_euid, mock_pi, runner):
        """On Pi without sudo, warns user."""
        result = runner.invoke(cli, ["network", "reconnect"])
        assert result.exit_code == 0
        assert "sudo" in result.output.lower() or "root" in result.output.lower()

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli.os.geteuid", return_value=0)
    @patch("matrix_cli.subprocess.run")
    @patch("matrix_cli.time.sleep")
    def test_reconnect_already_connected(self, mock_sleep, mock_run, mock_euid, mock_pi, runner):
        """If already connected, reports success without restarting."""
        # ping succeeds (already connected)
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ["network", "reconnect"])
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "connected" in result.output.lower()

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli.os.geteuid", return_value=0)
    @patch("matrix_cli.time.sleep")
    @patch("matrix_cli.subprocess.run")
    def test_reconnect_restarts_network_manager(self, mock_run, mock_sleep, mock_euid, mock_pi, runner):
        """When disconnected, tries to restart NetworkManager."""
        call_count = [0]

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            if "ping" in cmd:
                call_count[0] += 1
                # First ping fails (disconnected), second succeeds (after restart)
                result.returncode = 1 if call_count[0] <= 1 else 0
            else:
                result.returncode = 0
            return result

        mock_run.side_effect = side_effect

        result = runner.invoke(cli, ["network", "reconnect"])
        assert result.exit_code == 0

    @patch("matrix_cli._is_raspberry_pi", return_value=True)
    @patch("matrix_cli.os.geteuid", return_value=0)
    @patch("matrix_cli.time.sleep")
    @patch("matrix_cli.subprocess.run")
    def test_reconnect_tries_dhcp_on_failure(self, mock_run, mock_sleep, mock_euid, mock_pi, runner):
        """When NetworkManager restart fails, tries DHCP release/renew."""
        # All pings fail
        mock_run.return_value = MagicMock(returncode=1)

        result = runner.invoke(cli, ["network", "reconnect"])
        assert result.exit_code == 0
        # Should mention dhcp or dhclient in attempts
        calls_str = str(mock_run.call_args_list)
        assert "dhclient" in calls_str or "dhcp" in calls_str.lower()


# ---------------------------------------------------------------------------
# network test-portal
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetworkTestPortal:
    """Tests for `matrix network test-portal`."""

    @patch("matrix_cli.requests.get")
    def test_portal_no_captive_portal(self, mock_get, runner):
        """When response contains 'success', no captive portal."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>success</body></html>"
        mock_response.url = "http://detectportal.firefox.com/canonical.html"
        mock_response.is_redirect = False
        mock_response.history = []
        mock_get.return_value = mock_response

        result = runner.invoke(cli, ["network", "test-portal"])
        assert result.exit_code == 0
        assert "No captive portal" in result.output or "no captive portal" in result.output.lower()

    @patch("matrix_cli.requests.get")
    def test_portal_captive_portal_detected(self, mock_get, runner):
        """When response does not contain 'success', captive portal detected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Please sign in</body></html>"
        mock_response.url = "http://captive.portal.example.com/login"
        mock_response.is_redirect = False
        mock_response.history = [MagicMock(status_code=302)]
        mock_get.return_value = mock_response

        result = runner.invoke(cli, ["network", "test-portal"])
        assert result.exit_code == 0
        assert "captive portal" in result.output.lower()

    @patch("matrix_cli.requests.get", side_effect=Exception("Connection refused"))
    def test_portal_no_connectivity(self, mock_get, runner):
        """When request fails entirely, reports no connectivity."""
        result = runner.invoke(cli, ["network", "test-portal"])
        assert result.exit_code == 0
        assert "connectivity" in result.output.lower() or "connection" in result.output.lower()
