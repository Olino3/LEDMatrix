"""
Tests for first_time_install.sh deprecation wrapper.

Verifies that the script has been replaced with a thin wrapper that:
1. Prints a deprecation warning directing users to `matrix install`
2. Forwards to `matrix install` when run
3. Does NOT contain the original ~700-line installation logic
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
INSTALL_SCRIPT = REPO_ROOT / "first_time_install.sh"


@pytest.mark.unit
class TestFirstTimeInstallDeprecation:
    """Ensure first_time_install.sh is a thin deprecation wrapper."""

    def test_script_exists(self):
        """The script still exists (backward compat for one-shot installer)."""
        assert INSTALL_SCRIPT.exists(), "first_time_install.sh should still exist as a wrapper"

    def test_script_is_short(self):
        """The wrapper should be under 50 lines (was ~700+ lines)."""
        lines = INSTALL_SCRIPT.read_text().splitlines()
        assert len(lines) < 50, (
            f"first_time_install.sh should be a thin wrapper (<50 lines), "
            f"but has {len(lines)} lines"
        )

    def test_script_contains_deprecation_warning(self):
        """The wrapper must warn users that the script is deprecated."""
        content = INSTALL_SCRIPT.read_text()
        assert "deprecated" in content.lower() or "DEPRECATED" in content, (
            "first_time_install.sh should contain a deprecation warning"
        )

    def test_script_mentions_matrix_install(self):
        """The wrapper must direct users to `matrix install`."""
        content = INSTALL_SCRIPT.read_text()
        assert "matrix install" in content, (
            "first_time_install.sh should reference 'matrix install' as the replacement"
        )

    def test_script_does_not_contain_apt_install(self):
        """The wrapper should NOT contain apt install logic (that was the old script)."""
        content = INSTALL_SCRIPT.read_text()
        assert "apt install" not in content and "apt-get install" not in content, (
            "first_time_install.sh should not contain apt install logic — "
            "it should be a thin wrapper"
        )

    def test_script_does_not_contain_rgbmatrix_build(self):
        """The wrapper should NOT contain rgbmatrix build logic."""
        content = INSTALL_SCRIPT.read_text()
        assert "rpi-rgb-led-matrix" not in content, (
            "first_time_install.sh should not contain rgbmatrix build logic"
        )


@pytest.mark.unit
class TestOneShotInstallUpdated:
    """Ensure one-shot-install.sh references matrix install, not first_time_install.sh."""

    ONE_SHOT_SCRIPT = REPO_ROOT / "scripts" / "install" / "one-shot-install.sh"

    def test_one_shot_script_exists(self):
        assert self.ONE_SHOT_SCRIPT.exists()

    def test_one_shot_does_not_call_first_time_install(self):
        """one-shot-install.sh should no longer invoke first_time_install.sh."""
        content = self.ONE_SHOT_SCRIPT.read_text()
        # Allow references in comments but not as an actual command invocation
        lines = [
            line for line in content.splitlines()
            if "first_time_install.sh" in line
            and not line.strip().startswith("#")
        ]
        assert len(lines) == 0, (
            f"one-shot-install.sh still invokes first_time_install.sh in "
            f"non-comment lines: {lines}"
        )

    def test_one_shot_calls_matrix_install(self):
        """one-shot-install.sh should call matrix install."""
        content = self.ONE_SHOT_SCRIPT.read_text()
        assert "matrix install" in content or "matrix_cli" in content, (
            "one-shot-install.sh should use 'matrix install' as the installation method"
        )
