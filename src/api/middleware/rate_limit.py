"""Rate limiting middleware via slowapi.

Default: 1000 requests/minute per client IP.
SSE streaming endpoints: 20 requests/minute per client IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — imported by routers that need custom limits
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])
