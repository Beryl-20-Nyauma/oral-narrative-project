"""Tests for narrators API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from typing import AsyncGenerator
import uuid

from app.models.narrative import Narrator


def get_override_db(db_session):
    """Create an override function for get_db dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    return override_get_db


class TestListNarrators:
    """Tests for GET /api/narrators endpoint."""

    @pytest.mark.asyncio
    async def test_list_empty(self, db_session: AsyncSession):
        """Should return empty list when no narrators exist."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/narrators")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["narrators"] == []

    @pytest.mark.asyncio
    async def test_list_with_narrators(self, db_session: AsyncSession):
        """Should return list of narrators."""
        from main import app
        from app.core.database import get_db
        
        narrator1 = Narrator(
            name="Narrator One",
            face_embedding=[0.1] * 512,
            narrative_count=2
        )
        narrator2 = Narrator(
            name="Narrator Two",
            face_embedding=[0.2] * 512,
            narrative_count=1
        )
        db_session.add(narrator1)
        db_session.add(narrator2)
        await db_session.commit()
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/narrators")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["narrators"]) == 2


class TestGetNarrator:
    """Tests for GET /api/narrators/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_narrator_found(self, db_session: AsyncSession):
        """Should return narrator details."""
        from main import app
        from app.core.database import get_db
        
        narrator = Narrator(
            name="Test Narrator",
            face_embedding=[0.1] * 512,
            narrative_count=1
        )
        db_session.add(narrator)
        await db_session.commit()
        await db_session.refresh(narrator)
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(f"/api/narrators/{narrator.id}")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Narrator"

    @pytest.mark.asyncio
    async def test_get_narrator_not_found(self, db_session: AsyncSession):
        """Should return 404 for missing narrator."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        fake_id = str(uuid.uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(f"/api/narrators/{fake_id}")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 404


class TestRenameNarrator:
    """Tests for PATCH /api/narrators/{id}/rename endpoint."""

    @pytest.mark.asyncio
    async def test_rename_success(self, db_session: AsyncSession):
        """Should rename narrator."""
        from main import app
        from app.core.database import get_db
        
        narrator = Narrator(
            name="Old Name",
            face_embedding=[0.1] * 512,
            narrative_count=1
        )
        db_session.add(narrator)
        await db_session.commit()
        await db_session.refresh(narrator)
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/narrators/{narrator.id}/rename",
                json={"name": "New Name"}
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"


class TestIdentifyNarrator:
    """Tests for POST /api/narrators/identify endpoint."""

    @pytest.mark.asyncio
    async def test_identify_no_media(self, db_session: AsyncSession):
        """Should return error when no image provided."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post("/api/narrators/identify")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 422


class TestRebuildIndex:
    """Tests for POST /api/narrators/rebuild-index endpoint."""

    @pytest.mark.asyncio
    async def test_rebuild_index(self, db_session: AsyncSession):
        """Should rebuild FAISS index."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = get_override_db(db_session)
        
        with patch("app.routers.narrators.rebuild_faiss_index") as mock_rebuild:
            mock_rebuild.return_value = {"indexed": 0}
            
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post("/api/narrators/rebuild-index")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
