from __future__ import annotations

import asyncio
import logging

from .config import get_settings
from .pipeline import AnalysisPipeline
from .queue import RedisQueue
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    queue = RedisQueue(settings.redis_url)
    pipeline = AnalysisPipeline(settings)
    logger.info("Eye Visionary worker listening on %s", queue.name)
    try:
        while True:
            try:
                job_id = await queue.dequeue(timeout=5)
            except RedisError as exc:
                logger.error("Redis queue error; retrying: %s", exc)
                await asyncio.sleep(2)
                continue
            if job_id is not None:
                retry = await pipeline.process(job_id)
                if retry:
                    await queue.enqueue(job_id)
    finally:
        await queue.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
