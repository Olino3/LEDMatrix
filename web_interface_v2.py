"""Compatibility shim — will be removed in v6.2.0 (Phase 9).

Plugins should migrate to: from src.api.services.api_counter import increment_api_counter
"""

import warnings

warnings.warn(
    "Importing from web_interface_v2 is deprecated. "
    "Use src.api.services.api_counter instead. "
    "This shim will be removed in v6.2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from src.api.services.api_counter import increment_api_counter  # noqa: E402, F401

__all__ = ["increment_api_counter"]
