# -*- coding: utf-8 -*-
"""
Unit tests for QAEditor module.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.translation.qa_editor import QAEditor


@pytest.fixture
def mock_gemini_service():
    """Create a mock Gemini service."""
    service = AsyncMock()
    service.generate_content_async = AsyncMock()
    return service


@pytest.fixture
def mock_prompt_builder():
    """Create a mock prompt builder."""
    builder = MagicMock()
    builder.build_editor_prompt = MagicMock(return_value="Test prompt")
    builder.style_manager.get_style_summary.return_value = "Style guide"
    return builder


@pytest.fixture
def qa_editor(mock_gemini_service, mock_prompt_builder):
    """Create a QAEditor instance for testing."""
    config = {}
    return QAEditor(config, mock_gemini_service, mock_prompt_builder)


class TestPerformQAEdit:
    """Test QA editing functionality."""

    @pytest.mark.asyncio
    async def test_successful_edit(self, qa_editor, mock_gemini_service):
        """Test successful QA edit."""
        mock_gemini_service.generate_content_async.return_value = "Edited translation"

        result = await qa_editor.perform_qa_edit(
            draft_translation="Draft translation",
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1
        )

        assert result == "Edited translation"
        assert mock_gemini_service.generate_content_async.called

    @pytest.mark.asyncio
    async def test_moderate_overlap_is_accepted(self, qa_editor, mock_gemini_service):
        """
        QAEditor phải chấp nhận các chỉnh sửa có độ khác biệt vừa phải (overlap ~50%)
        thay vì revert về draft, để tránh bỏ qua các bản edit hợp lệ.
        """
        draft = "Draft translation"
        edited = "Edited translation"
        # Word overlap giữa draft và edited là 50% (chung từ 'translation')
        mock_gemini_service.generate_content_async.return_value = edited

        result = await qa_editor.perform_qa_edit(
            draft_translation=draft,
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1,
        )

        assert result == edited

    @pytest.mark.asyncio
    async def test_config_can_increase_overlap_threshold(self, mock_gemini_service, mock_prompt_builder):
        """
        Khi cấu hình tăng min_word_overlap_ratio > 0.5, cùng một bản edit overlap ~50%
        phải bị reject (giữ lại draft gốc). Dùng để verify QAEditor đọc config đúng.
        """
        config = {
            "translation": {
                "qa_editor": {
                    "min_word_overlap_ratio": 0.7,
                }
            }
        }
        qa_editor = QAEditor(config, mock_gemini_service, mock_prompt_builder)

        draft = "Draft translation"
        edited = "Edited translation"  # overlap ~50%
        mock_gemini_service.generate_content_async.return_value = edited

        result = await qa_editor.perform_qa_edit(
            draft_translation=draft,
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1,
        )

        assert result == draft

    @pytest.mark.asyncio
    async def test_empty_draft(self, qa_editor):
        """Test with empty draft translation."""
        result = await qa_editor.perform_qa_edit(
            draft_translation="",
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_api_error_returns_draft(self, qa_editor, mock_gemini_service):
        """Test that API error returns original draft."""
        mock_gemini_service.generate_content_async.side_effect = Exception("API Error")

        draft = "Original draft"
        result = await qa_editor.perform_qa_edit(
            draft_translation=draft,
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1
        )

        assert result == draft

    @pytest.mark.asyncio
    async def test_empty_response_returns_draft(self, qa_editor, mock_gemini_service):
        """Test that empty API response returns original draft."""
        mock_gemini_service.generate_content_async.return_value = ""

        draft = "Original draft"
        result = await qa_editor.perform_qa_edit(
            draft_translation=draft,
            relevant_terms=[],
            api_key="test-key",
            chunk_id=1
        )

        assert result == draft
