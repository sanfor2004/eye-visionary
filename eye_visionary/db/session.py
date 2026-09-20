from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eye_visionary.config import get_settings


if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


settings = get_settings()
engine = create_async_engine(async_database_url(settings.database_url), pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def database_check() -> dict[str, object]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
        vector = await connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        return {"postgresql": True, "pgvector": bool(vector.scalar())}
