"""
Short-lived per-session working memory, backed by Redis.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_TTL_SECONDS = 3600


class Scratch:
    def __init__(self, redis=None) -> None:
        self._redis = redis
        self._local: dict[str, str] = {}

    @staticmethod
    def _key(user_id: UUID, session_id: str, name: str) -> str:
        return f"scratch:{user_id}:{session_id}:{name}"

    def get(self, user_id: UUID, session_id: str, name: str) -> Any | None:
        key = self._key(user_id, session_id, name)
        try:
            raw = self._redis.get(key) if self._redis else self._local.get(key)
        except Exception:
            logger.warning("scratch read failed", exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    def set(self, user_id: UUID, session_id: str, name: str, value: Any) -> None:
        key = self._key(user_id, session_id, name)
        payload = json.dumps(value, ensure_ascii=False)
        try:
            if self._redis:
                self._redis.setex(key, _TTL_SECONDS, payload)
            else:
                self._local[key] = payload
        except Exception:
            logger.warning("scratch write failed", exc_info=True)


def build_scratch() -> Scratch:
    from core.config import settings

    if not settings.redis_url:
        logger.info("no REDIS_URL; scratch is in-process only")
        return Scratch()
    try:
        import redis
        return Scratch(redis.from_url(settings.redis_url, decode_responses=True))
    except Exception:
        logger.warning("redis unavailable; scratch is in-process only", exc_info=True)
        return Scratch()
