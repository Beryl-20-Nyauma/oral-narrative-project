"""Tests for narrative endpoints."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.narrative_service import (
    fetch_narratives,
    fetch_narrative_by_id,
    get_narrative_status,
    get_timeline,
    get_profile,
)

TEST_NARRATIVE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TestFetchNarratives:
    """Tests for fetch_narratives function."""

    @pytest.mark.asyncio
    async def test_empty_database(self, db_session: AsyncSession):
        """Should return empty list when no narratives exist."""
        result = await fetch_narratives(db_session)
        assert result["total"] == 0
        assert result["narratives"] == []

    @pytest.mark.asyncio
    async def test_returns_all_narratives(self, db_session: AsyncSession, sample_narrative):
        """Should return all narratives without filters."""
        result = await fetch_narratives(db_session)
        assert result["total"] == 1
        assert len(result["narratives"]) == 1

    @pytest.mark.asyncio
    async def test_filter_by_narrator(self, db_session: AsyncSession, sample_narrative):
        """Should filter by narrator name."""
        result = await fetch_narratives(db_session, narrator="Test")
        assert result["total"] == 1

        result = await fetch_narratives(db_session, narrator="Nonexistent")
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_emotion(self, db_session: AsyncSession, sample_narrative):
        """Should filter by dominant emotion."""
        result = await fetch_narratives(db_session, emotion="joy")
        assert result["total"] == 1

        result = await fetch_narratives(db_session, emotion="sadness")
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_theme(self, db_session: AsyncSession, sample_narrative):
        """Should filter by theme."""
        result = await fetch_narratives(db_session, theme="memory")
        assert result["total"] == 1

        result = await fetch_narratives(db_session, theme="nonexistent")
        assert result["total"] == 0


class TestFetchNarrativeById:
    """Tests for fetch_narrative_by_id function."""

    @pytest.mark.asyncio
    async def test_returns_narrative(self, db_session: AsyncSession, sample_narrative):
        """Should return narrative if it exists."""
        result = await fetch_narrative_by_id(db_session, narrative_id=str(TEST_NARRATIVE_ID))
        assert result is not None
        assert result["archive_id"] == str(TEST_NARRATIVE_ID)

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self, db_session: AsyncSession):
        """Should return None for nonexistent narrative."""
        result = await fetch_narrative_by_id(db_session, narrative_id="nonexistent")
        assert result is None


class TestGetNarrativeStatus:
    """Tests for get_narrative_status function."""

    @pytest.mark.asyncio
    async def test_complete_status(self, db_session: AsyncSession, sample_narrative):
        """Should return complete status."""
        result = await get_narrative_status(db_session, narrative_id=str(TEST_NARRATIVE_ID))
        assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_not_found_status(self, db_session: AsyncSession):
        """Should return not_found for missing narrative."""
        result = await get_narrative_status(db_session, narrative_id="nonexistent")
        assert result["status"] == "not_found"


class TestGetTimeline:
    """Tests for get_timeline function."""

    @pytest.mark.asyncio
    async def test_returns_timeline(self, db_session: AsyncSession, sample_narrative):
        """Should return emotion timeline for complete narrative."""
        result = await get_timeline(db_session, narrative_id=str(TEST_NARRATIVE_ID))
        assert "facial_emotions" in result
        assert "vocal_features" in result
        assert "unified_timeline" in result

    @pytest.mark.asyncio
    async def test_not_found(self, db_session: AsyncSession):
        """Should return not_found for missing narrative."""
        result = await get_timeline(db_session, narrative_id="nonexistent")
        assert result["status"] == "not_found"


class TestGetProfile:
    """Tests for get_profile function."""

    @pytest.mark.asyncio
    async def test_returns_profile(self, db_session: AsyncSession, sample_narrative):
        """Should return narrator profile for complete narrative."""
        result = await get_profile(db_session, narrative_id=str(TEST_NARRATIVE_ID))
        assert "narrator_identity" in result
        assert "vocal_profile" in result
        assert "emotion_congruence" in result

    @pytest.mark.asyncio
    async def test_not_found(self, db_session: AsyncSession):
        """Should return not_found for missing narrative."""
        result = await get_profile(db_session, narrative_id="nonexistent")
        assert result["status"] == "not_found"
