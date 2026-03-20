"""In-memory API call counter.

Tracks API call counts by kind (e.g. "odds", "weather").
Used by plugins and the system status endpoint.
"""

import threading
from typing import Dict

_counts: Dict[str, int] = {}
_lock = threading.Lock()


def increment_api_counter(kind: str, count: int = 1) -> None:
    """Increment the API call counter for the given kind."""
    with _lock:
        _counts[kind] = _counts.get(kind, 0) + count


def get_api_counts() -> Dict[str, int]:
    """Return a copy of current API call counts."""
    with _lock:
        return dict(_counts)
