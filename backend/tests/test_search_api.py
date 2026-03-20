"""Tests for search API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator


class TestSearchEndpoint:
    """Tests for GET /api/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_empty_database(self, db_session: AsyncSession):
        """Should return empty results for empty database."""
        from main import app
        from app.core.database import get_db
        
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/search?q=test")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_with_results(self, db_session: AsyncSession, sample_narrative):
        """Should return matching results."""
        from main import app
        from app.core.database import get_db
        
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/search?q=Test")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_no_query(self, db_session: AsyncSession):
        """Should return 400 when no query provided."""
        from main import app
        from app.core.database import get_db
        
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/search")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_with_limit(self, db_session: AsyncSession, sample_narrative):
        """Should respect limit parameter."""
        from main import app
        from app.core.database import get_db
        
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/search?q=Test&limit=1")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 1
