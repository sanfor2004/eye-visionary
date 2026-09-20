from __future__ import annotations

import json
from uuid import UUID

from redis.asyncio import Redis, from_url


class RedisQueue:
    def __init__(self, url: str, name: str = "eye_visionary:jobs"):
        self.redis: Redis = from_url(url, decode_responses=True, socket_timeout=30, socket_connect_timeout=5)
        self.name = name

    async def enqueue(self, job_id: UUID) -> None:
        await self.redis.rpush(self.name, json.dumps({"job_id": str(job_id)}))

    async def dequeue(self, timeout: int = 5) -> UUID | None:
        result = await self.redis.blpop(self.name, timeout=timeout)
        if not result:
            return None
        _, payload = result
        return UUID(json.loads(payload)["job_id"])

    async def health(self) -> bool:
        return bool(await self.redis.ping())

    async def close(self) -> None:
        await self.redis.aclose()
