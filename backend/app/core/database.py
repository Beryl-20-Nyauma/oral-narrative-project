"""Database configuration with async SQLAlchemy support."""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

if DATABASE_URL:
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Async dependency for FastAPI endpoints."""
    if async_session_factory is None:
        yield None
    else:
        async with async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


async def init_db():
    """Create all tables."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
