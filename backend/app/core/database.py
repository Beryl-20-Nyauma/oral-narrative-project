"""Database configuration with async SQLAlchemy support."""

import os
import uuid
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Any
from sqlalchemy import String, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


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
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/oral_narratives.db")

engine = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_db_type: str = "none"

if USE_SQLITE or (not DATABASE_URL):
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite+aiosqlite:///{SQLITE_PATH}"
    engine = create_async_engine(
        sqlite_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    _db_type = "sqlite"
    logger.info(f"Using SQLite database: {SQLITE_PATH}")
elif DATABASE_URL:
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    _db_type = "postgresql"
    logger.info("Using PostgreSQL database")

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


def get_database_type() -> str:
    """Return current database type."""
    return _db_type
