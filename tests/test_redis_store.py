"""Tests for the Redis-backed session store.

These exercise the in-memory fallback and the Redis-backed store via a small
fake client, so no real Redis is required.
"""

from redis_store import InMemorySessionStore, RedisSessionStore


class FakeRedis:
    """Minimal stand-in for the redis client surface we use."""

    def __init__(self):
        self.store = {}
        self.set_calls = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.set_calls.append((key, ex))
        self.store[key] = value

    def exists(self, key):
        return 1 if key in self.store else 0

    def getdel(self, key):
        return self.store.pop(key, None)


def test_inmemory_session_roundtrip():
    s = InMemorySessionStore()
    assert s.get("a") is None
    assert s.exists("a") is False
    s.set("a", {"access_token": "t"})
    assert s.get("a") == {"access_token": "t"}
    assert s.exists("a") is True


def test_inmemory_get_returns_copy():
    s = InMemorySessionStore()
    s.set("a", {"x": 1})
    got = s.get("a")
    got["x"] = 999
    assert s.get("a")["x"] == 1  # mutating the copy must not change the store


def test_redis_session_roundtrip_and_prefix_and_ttl():
    fake = FakeRedis()
    s = RedisSessionStore(fake)
    s.set("sid", {"access_token": "t", "expires_at": 123})
    key, ttl = fake.set_calls[-1]
    assert key == "session:sid"
    assert ttl is not None and ttl > 0
    assert s.get("sid") == {"access_token": "t", "expires_at": 123}
    assert s.exists("sid") is True
    assert s.get("missing") is None
    assert s.exists("missing") is False


def test_redis_consume_is_one_time_and_prefixed():
    fake = FakeRedis()
    s = RedisSessionStore(fake)
    s.set_with_ttl("oauth-state:abc", {"state": "abc"}, 600)

    assert s.consume("oauth-state:abc") is True
    assert s.consume("oauth-state:abc") is False
