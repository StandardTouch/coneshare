import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_CACHE_SECONDS = 30
_cache_until = 0.0
_cached_enabled = True


def is_mcp_enabled() -> bool:
    """Return whether MCP is enabled according to backend public settings."""
    global _cache_until, _cached_enabled
    now = time.monotonic()
    if now < _cache_until:
        return _cached_enabled

    api_base = os.getenv('CONESHARE_API_URL', 'http://backend:8000/api/v1').rstrip('/')
    url = f'{api_base}/public/settings/'
    enabled = True
    try:
        response = httpx.get(url, timeout=2.0)
        if response.status_code == 200:
            enabled = bool(response.json().get('mcp_enabled', True))
        else:
            logger.warning('MCP feature gate: unexpected status %s from %s', response.status_code, url)
    except Exception as exc:
        logger.warning('MCP feature gate: could not reach %s (%s); assuming enabled', url, exc)

    _cached_enabled = enabled
    _cache_until = now + _CACHE_SECONDS
    return enabled


def clear_feature_gate_cache() -> None:
    global _cache_until
    _cache_until = 0.0
