"""Redis-backed session store.

Sessions hold Spotify tokens plus the derived taste profile. Backing them with
Redis lets them survive restarts and be shared across instances.

If REDIS_URL is unset (local dev, tests, CI) the store falls back to an
in-memory dict, so the app runs without Redis.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("catch_a_vibe")

# Sessions get a sliding TTL (refreshed on every write) so active users persist
# while abandoned sessions age out.
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(7 * 24 * 3600)))

_SESSION_PREFIX = "session:"


# --- Session store ----------------------------------------------------------

class InMemorySessionStore:
    """Process-local fallback used when REDIS_URL is not configured.

    get() returns a copy so callers must call set() to persist changes — this
    matches the Redis backend's semantics and keeps behaviour identical.
    """

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        value = self._data.get(session_id)
        return dict(value) if value is not None else None

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        self._data[session_id] = dict(data)

    def exists(self, session_id: str) -> bool:
        return session_id in self._data


class RedisSessionStore:
    """Session store persisted in Redis with a sliding TTL."""

    def __init__(self, client) -> None:
        self._client = client

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        raw = self._client.get(_SESSION_PREFIX + session_id)
        return json.loads(raw) if raw else None

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        self._client.set(
            _SESSION_PREFIX + session_id,
            json.dumps(data),
            ex=SESSION_TTL_SECONDS,
        )

    def exists(self, session_id: str) -> bool:
        return bool(self._client.exists(_SESSION_PREFIX + session_id))


# --- Wiring -----------------------------------------------------------------

def _make_redis_client():
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    import redis  # imported lazily so the dependency is optional without REDIS_URL

    return redis.Redis.from_url(url, decode_responses=True)


_client = _make_redis_client()

if _client is not None:
    logger.info("Redis configured: using Redis session store")
    session_store: Any = RedisSessionStore(_client)
else:
    logger.info("REDIS_URL not set: using in-memory session store")
    session_store = InMemorySessionStore()
