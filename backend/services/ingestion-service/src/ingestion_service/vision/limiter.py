from __future__ import annotations

import time

from redis import Redis


_RESERVE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
if current > tonumber(ARGV[1]) then return 0 end
return 1
"""


class DistributedVisionGuard:
    """Global fixed-window limiter and circuit breaker shared by all replicas."""

    def __init__(self, redis: Redis, *, requests_per_minute: int, circuit_seconds: int) -> None:
        self._redis = redis
        self._rpm = requests_per_minute
        self._circuit_seconds = circuit_seconds

    def reserve(self) -> bool:
        if self.is_open():
            return False
        minute = int(time.time() // 60)
        key = f"ingestion:vision:rate:{minute}"
        return bool(self._redis.eval(_RESERVE_SCRIPT, 1, key, self._rpm, 75))

    def is_open(self) -> bool:
        return bool(self._redis.exists("ingestion:vision:circuit"))

    def open(self, reason: str) -> None:
        self._redis.set(
            "ingestion:vision:circuit",
            reason[:200],
            ex=self._circuit_seconds,
        )

    def cached(self, digest: str) -> str | None:
        value = self._redis.get(f"ingestion:vision:cache:{digest}")
        if isinstance(value, bytes):
            return value.decode()
        return value

    def cache(self, digest: str, caption: str) -> None:
        self._redis.set(f"ingestion:vision:cache:{digest}", caption, ex=30 * 24 * 3600)

