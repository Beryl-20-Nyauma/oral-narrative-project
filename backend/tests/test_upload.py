"""Tests for upload operations."""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.narrative import Narrative


class TestUploadService:
    """Tests for upload service functions."""

    @pytest.mark.asyncio
    async def test_process_upload_creates_entry(self, db_session: AsyncSession):
        """Should create narrative entry in database."""
        from app.services.upload_service import process_upload
        
        mock_video = MagicMock()
        mock_video.read = AsyncMock(return_value=b"fake video data")
        mock_video.filename = "test.mp4"
        
        mock_task_result = MagicMock(id="test-task-id")
        mock_tasks = MagicMock()
        mock_tasks.process_video_task = MagicMock()
        mock_tasks.process_video_task.delay = MagicMock(return_value=mock_task_result)
        
        with patch("app.services.upload_service.STORAGE_DIR"):
            with patch.dict(sys.modules, {"app.core.tasks": mock_tasks}):
                result = await process_upload(
                    db=db_session,
                    video=mock_video,
                    title="Test Upload",
                    narrator_name="Test User",
                    location="Test Location",
                    language="en",
                    themes="test,upload",
                    transcript="Test transcript content"
                )
        
        assert "narrative_id" in result
        assert result["status"] == "pending"
        assert "task_id" in result
        
        narrative_result = await db_session.execute(
            select(Narrative).where(Narrative.title == "Test Upload")
        )
        narrative = narrative_result.scalar_one_or_none()
        assert narrative is not None
        assert narrative.narrator_name == "Test User"

    @pytest.mark.asyncio
    async def test_process_upload_parses_themes(self, db_session: AsyncSession):
        """Should parse comma-separated themes into list."""
        from app.services.upload_service import process_upload
        
        mock_video = MagicMock()
        mock_video.read = AsyncMock(return_value=b"test")
        
        mock_task_result = MagicMock(id="test-task-id")
        mock_tasks = MagicMock()
        mock_tasks.process_video_task = MagicMock()
        mock_tasks.process_video_task.delay = MagicMock(return_value=mock_task_result)
        
        with patch("app.services.upload_service.STORAGE_DIR"):
            with patch.dict(sys.modules, {"app.core.tasks": mock_tasks}):
                result = await process_upload(
                    db=db_session,
                    video=mock_video,
                    title="Test",
                    narrator_name="Test",
                    location="",
                    language="en",
                    themes="memory, water,  community  ",
                    transcript=""
                )
        
        narrative_result = await db_session.execute(
            select(Narrative)
            .options(selectinload(Narrative.themes))
            .where(Narrative.id == result["narrative_id"])
        )
        narrative = narrative_result.scalar_one_or_none()
        
        theme_names = [t.name for t in narrative.themes]
        assert "memory" in theme_names
        assert "water" in theme_names
        assert "community" in theme_names

    @pytest.mark.asyncio
    async def test_process_upload_schedules_celery_task(self, db_session: AsyncSession):
        """Should schedule analysis pipeline via Celery."""
        from app.services.upload_service import process_upload
        
        mock_video = MagicMock()
        mock_video.read = AsyncMock(return_value=b"test")
        
        mock_delay = MagicMock(return_value=MagicMock(id="test-task-id"))
        mock_tasks = MagicMock()
        mock_tasks.process_video_task = MagicMock()
        mock_tasks.process_video_task.delay = mock_delay
        
        with patch("app.services.upload_service.STORAGE_DIR"):
            with patch.dict(sys.modules, {"app.core.tasks": mock_tasks}):
                result = await process_upload(
                    db=db_session,
                    video=mock_video,
                    title="Test",
                    narrator_name="Test",
                    location="",
                    language="en",
                    themes="",
                    transcript=""
                )
        
        mock_delay.assert_called_once()
        assert result["task_id"] == "test-task-id"
