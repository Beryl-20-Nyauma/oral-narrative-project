"""Tests for stats API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator


def get_override_db(db_session):
    """Create an override function for get_db dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    return override_get_db


class TestGetStats:
    """Tests for GET /api/stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_empty_database(self, db_session: AsyncSession):
        """Should return zero stats for empty database."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_narratives"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_narratives(self, db_session: AsyncSession, sample_narrative):
        """Should return stats with narrative data."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_narratives"] >= 1


class TestBenchmark:
    """Tests for GET /api/stats/benchmark endpoint."""

    @pytest.mark.asyncio
    async def test_benchmark_returns_results(self, db_session: AsyncSession):
        """Should return benchmark results."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/benchmark")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "database" in data

    @pytest.mark.asyncio
    async def test_benchmark_system_info(self, db_session: AsyncSession):
        """Should include system info in benchmark."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/benchmark")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "system" in data

    @pytest.mark.asyncio
    async def test_benchmark_gpu_info(self, db_session: AsyncSession):
        """Should include GPU info in benchmark."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/benchmark")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "gpu" in data

    @pytest.mark.asyncio
    async def test_benchmark_database_metrics(self, db_session: AsyncSession):
        """Should include database metrics."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/benchmark")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "read_latency_ms" in data["database"]


class TestHealthCheck:
    """Tests for GET /api/stats/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, db_session: AsyncSession):
        """Should return healthy status."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/health")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_includes_system_info(self, db_session: AsyncSession):
        """Should include system info in health check."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/stats/health")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
