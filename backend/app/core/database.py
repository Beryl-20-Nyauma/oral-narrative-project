"""Database configuration with async SQLAlchemy support."""

import os
import uuid
from typing import AsyncGenerator, Optional, Any
from sqlalchemy import String, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)


class GUID(TypeDecorator):
    """Platform-independent GUID type that stores UUID as CHAR(36) in SQLite."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


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
