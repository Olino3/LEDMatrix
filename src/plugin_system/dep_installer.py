"""
Plugin dependency installer using uv.

Centralises plugin dependency installation for PluginLoader, PluginManager,
and StoreManager.  Prefers ``uv pip install`` when uv is available and falls
back to ``sys.executable -m pip install`` otherwise.

SPIKE-008: Migrated from raw pip with --break-system-packages to venv-aware
uv commands.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from src.logging_config import get_logger

logger = get_logger(__name__)

# Well-known locations where uv may be installed but not on PATH
_UV_SEARCH_PATHS = [
    Path.home() / ".local" / "bin" / "uv",
    Path.home() / ".cargo" / "bin" / "uv",
    Path("/usr/local/bin/uv"),
]


def _find_uv() -> Optional[str]:
    """Locate the ``uv`` binary.

    Checks ``PATH`` first via :func:`shutil.which`, then falls back to
    well-known install locations.

    Returns:
        Absolute path to ``uv`` or ``None`` if not found.
    """
    path = shutil.which("uv")
    if path:
        return path

    for candidate in _UV_SEARCH_PATHS:
        if candidate.exists():
            return str(candidate)

    return None


def _build_install_command(
    requirements_file: Path,
    *,
    uv_path: Optional[str] = None,
    python_path: Optional[str] = None,
) -> List[str]:
    """Build the pip/uv install command for a plugin's requirements.

    Args:
        requirements_file: Path to the plugin's ``requirements.txt``.
        uv_path: Path to ``uv`` binary, or ``None`` to fall back to pip.
        python_path: Optional explicit Python interpreter path for
            ``uv pip install --python``.

    Returns:
        Command list suitable for :func:`subprocess.run`.
    """
    if uv_path:
        cmd = [uv_path, "pip", "install", "-r", str(requirements_file)]
        if python_path:
            cmd.extend(["--python", python_path])
        return cmd

    # Fallback: use the current interpreter's pip module
    return [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]


def install_plugin_dependencies(
    requirements_file: Path,
    *,
    plugin_id: str = "",
    timeout: int = 300,
    python_path: Optional[str] = None,
) -> bool:
    """Install dependencies from a plugin's ``requirements.txt``.

    Uses ``uv pip install`` when available, falling back to
    ``sys.executable -m pip install``.  The ``--break-system-packages``
    flag is intentionally omitted — all installs target the project venv.

    Args:
        requirements_file: Path to ``requirements.txt``.
        plugin_id: Plugin identifier (for log messages).
        timeout: Subprocess timeout in seconds.
        python_path: Optional Python interpreter for ``--python`` flag.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    uv_path = _find_uv()
    cmd = _build_install_command(
        requirements_file, uv_path=uv_path, python_path=python_path
    )

    tool_name = "uv" if uv_path else "pip"
    log_id = plugin_id or requirements_file.parent.name

    try:
        logger.info("Installing dependencies for %s via %s", log_id, tool_name)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode == 0:
            logger.info("Dependencies installed successfully for %s", log_id)
            return True

        logger.warning(
            "Dependency installation returned non-zero exit code for %s: %s",
            log_id,
            result.stderr,
        )
        return False

    except subprocess.TimeoutExpired:
        logger.error("Dependency installation timed out for %s", log_id)
        return False
    except FileNotFoundError:
        logger.warning(
            "%s not found. Skipping dependency installation for %s",
            tool_name,
            log_id,
        )
        return True
    except (BrokenPipeError, OSError) as e:
        if isinstance(e, OSError) and e.errno == 32:
            logger.error(
                "Broken pipe error during dependency installation for %s. "
                "This usually indicates a network interruption. "
                "Try installing again or check your network connection.",
                log_id,
            )
        else:
            logger.error(
                "OS error during dependency installation for %s: %s", log_id, e
            )
        return False
    except Exception as e:
        logger.error(
            "Unexpected error installing dependencies for %s: %s",
            log_id,
            e,
            exc_info=True,
        )
        return False
