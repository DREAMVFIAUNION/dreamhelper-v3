"""Redis 短期记忆存储 — 会话消息按 session_id 存储为 Redis List

每条消息 JSON 编码存入 list，TTL 24 小时自动过期。
当 Redis 不可用时自动降级到内存字典。
"""

import json
import time
import logging
from collections import defaultdict
from typing import List, Optional, Dict

logger = logging.getLogger("memory.redis_store")

SESSION_TTL = 86400  # 24h
SESSION_KEY_PREFIX = "mem:session:"
SUMMARY_KEY_PREFIX = "mem:summary:"
OWNER_KEY_PREFIX = "mem:owner:"  # 安全审计 P0-#3: 会话归属跟踪

_redis_client = None
_fallback_mode = False


async def get_redis():
    """获取 Redis 连接（懒初始化）"""
    global _redis_client, _fallback_mode
    if _redis_client is not None:
        return _redis_client
    if _fallback_mode:
        return None
    try:
        import redis.asyncio as aioredis
        from ...common.config import settings
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        await _redis_client.ping()
        logger.info("[RedisStore] Connected to Redis: %s", settings.REDIS_URL)
        return _redis_client
    except Exception as e:
        if _redis_client is not None:
            try:
                await _redis_client.aclose()
            except Exception:
                pass
            finally:
                _redis_client = None
        logger.warning("[RedisStore] Redis unavailable (%s), falling back to memory", e)
        _fallback_mode = True
        return None


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


class RedisSessionStore:
    """Redis-backed session message store with in-memory fallback."""

    def __init__(self):
        self._mem_fallback: Dict[str, List[dict]] = defaultdict(list)
        self._mem_summaries: Dict[str, str] = {}
        self._mem_owners: Dict[str, str] = {}  # P0-#3: 内存降级时的 owner 跟踪

    async def set_session_owner(self, session_id: str, user_id: str):
        """P0-#3: 记录会话归属用户（首次消息时调用）"""
        if not user_id or user_id == "anonymous":
            return
        r = await get_redis()
        if r:
            key = OWNER_KEY_PREFIX + session_id
            await r.set(key, user_id, ex=SESSION_TTL, nx=True)  # nx=True 只设置一次
        else:
            if session_id not in self._mem_owners:
                self._mem_owners[session_id] = user_id

    async def get_session_owner(self, session_id: str) -> str | None:
        """P0-#3: 获取会话归属用户"""
        r = await get_redis()
        if r:
            return await r.get(OWNER_KEY_PREFIX + session_id)
        return self._mem_owners.get(session_id)

    async def add_message(self, session_id: str, role: str, content: str, metadata: dict | None = None):
        entry = {
            "role": role,
            "content": content,
            "ts": time.time(),
            "meta": metadata or {},
        }
        r = await get_redis()
        if r:
            key = SESSION_KEY_PREFIX + session_id
            await r.rpush(key, json.dumps(entry, ensure_ascii=False))
            await r.expire(key, SESSION_TTL)
        else:
            self._mem_fallback[session_id].append(entry)

    async def get_history(self, session_id: str, limit: int = 40) -> List[dict]:
        r = await get_redis()
        if r:
            key = SESSION_KEY_PREFIX + session_id
            raw = await r.lrange(key, -limit, -1)
            return [{"role": json.loads(x)["role"], "content": json.loads(x)["content"]} for x in raw]
        items = self._mem_fallback.get(session_id, [])[-limit:]
        return [{"role": it["role"], "content": it["content"]} for it in items]

    async def get_context(self, session_id: str, max_messages: int = 6) -> str:
        # Check summary cache
        r = await get_redis()
        if r:
            skey = SUMMARY_KEY_PREFIX + session_id
            cached = await r.get(skey)
            if cached:
                return cached
        elif session_id in self._mem_summaries:
            return self._mem_summaries[session_id]

        history = await self.get_history(session_id, limit=max_messages)
        if not history:
            return ""
        lines = []
        for msg in history[-max_messages:]:
            prefix = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{prefix}: {msg['content'][:100]}")
        return "\n".join(lines)

    async def set_summary(self, session_id: str, summary: str):
        r = await get_redis()
        if r:
            await r.set(SUMMARY_KEY_PREFIX + session_id, summary, ex=SESSION_TTL)
        else:
            self._mem_summaries[session_id] = summary

    async def clear_session(self, session_id: str):
        r = await get_redis()
        if r:
            await r.delete(SESSION_KEY_PREFIX + session_id, SUMMARY_KEY_PREFIX + session_id, OWNER_KEY_PREFIX + session_id)
        else:
            self._mem_fallback.pop(session_id, None)
            self._mem_summaries.pop(session_id, None)
            self._mem_owners.pop(session_id, None)

    async def get_stats(self) -> dict:
        r = await get_redis()
        if r:
            keys = await r.keys(SESSION_KEY_PREFIX + "*")
            return {"store": "redis", "active_sessions": len(keys)}
        return {
            "store": "memory_fallback",
            "active_sessions": len(self._mem_fallback),
            "total_messages": sum(len(v) for v in self._mem_fallback.values()),
        }


# Singleton
_session_store: Optional[RedisSessionStore] = None


def get_session_store() -> RedisSessionStore:
    global _session_store
    if _session_store is None:
        _session_store = RedisSessionStore()
    return _session_store
