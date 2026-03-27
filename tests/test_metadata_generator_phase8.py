"""
Test suite for AI Metadata Generation Module (Phase 8)
Tests unified extraction, multi-document-type support, and config override logic.
"""
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.preprocessing.metadata_generator import MetadataGenerator


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'novel': {
            'name': 'Test Novel',
            'source_language': 'zh',
            'target_language': 'vi'
        },
        'metadata': {
            'document_type': 'novel'
        },
        'input': {
            'novel_path': 'test_novel.txt'
        },
        'gemini': {
            'default_model': 'gemini-2.0-flash-exp',
            'max_tokens_per_request': 1000000
        }
    }


@pytest.fixture
def mock_gemini_service():
    """Mock Gemini API service."""
    service = Mock()
    service.generate_content_async = AsyncMock()
    return service


class TestUnifiedExtraction:
    """Test unified extraction (single-pass) functionality."""

    @pytest.mark.asyncio
    async def test_unified_extraction_novel(self, mock_config, mock_gemini_service):
        """Test unified extraction for novel document type."""
        generator = MetadataGenerator(mock_config, ['test-key'])
        generator.gemini_service = mock_gemini_service

        # Mock response with both glossary and characters
        mock_response = json.dumps({
            "glossary": [
                {
                    "Type": "Character",
                    "Original_Term_Pinyin": "Zhang Wei",
                    "Original_Term_CN": "张伟",
                    "Translated_Term_VI": "Trương Vỹ",
                    "Frequency": 50
                }
            ],
            "characters": [
                {
                    "Type": "narrative_single",
                    "Character_A": "Zhang_Wei",
                    "Narrative_Term": "Trương Vỹ / hắn",
                    "Age_Stage": "young_adult (25)"
                }
            ]
        })

        mock_gemini_service.generate_content_async.return_value = mock_response

        with patch('builtins.open', create=True), \
             patch('os.path.exists', return_value=True), \
             patch.object(generator, '_save_glossary_csv', return_value=True), \
             patch.object(generator, '_save_relations_csv', return_value=True):

            success = await generator._extract_unified("Test content")

            assert success is True
            assert mock_gemini_service.generate_content_async.called

    @pytest.mark.asyncio
    async def test_unified_extraction_technical_doc(self, mock_config, mock_gemini_service):
        """Test unified extraction for technical document type."""
        mock_config['metadata']['document_type'] = 'technical_doc'
        generator = MetadataGenerator(mock_config, ['test-key'])
        generator.gemini_service = mock_gemini_service

        # Mock response with technical terms
        mock_response = json.dumps({
            "glossary": [
                {
                    "Type": "api_name",
                    "Term": "REST API",
                    "Vietnamese_Translation": "API REST",
                    "Category": "api"
                }
            ],
            "characters": []  # Empty for technical docs
        })

        mock_gemini_service.generate_content_async.return_value = mock_response

        with patch('builtins.open', create=True), \
             patch('os.path.exists', return_value=True), \
             patch.object(generator, '_save_glossary_csv', return_value=True), \
             patch.object(generator, '_save_relations_csv', return_value=True):

            success = await generator._extract_unified("Technical content")

            assert success is True


class TestDocumentTypePromptSelection:
    """Test dynamic prompt template selection based on document type."""

    def test_prompt_selection_novel(self, mock_config):
        """Test that novel type uses default prompt."""
        generator = MetadataGenerator(mock_config, ['test-key'])
        assert generator.document_type == 'novel'

    def test_prompt_selection_technical(self, mock_config):
        """Test that technical_doc type is recognized."""
        mock_config['metadata']['document_type'] = 'technical_doc'
        generator = MetadataGenerator(mock_config, ['test-key'])
        assert generator.document_type == 'technical_doc'

    def test_prompt_selection_medical(self, mock_config):
        """Test that medical type is recognized."""
        mock_config['metadata']['document_type'] = 'medical'
        generator = MetadataGenerator(mock_config, ['test-key'])
        assert generator.document_type == 'medical'

    def test_prompt_selection_academic(self, mock_config):
        """Test that academic_paper type is recognized."""
        mock_config['metadata']['document_type'] = 'academic_paper'
        generator = MetadataGenerator(mock_config, ['test-key'])
        assert generator.document_type == 'academic_paper'


class TestMergeLogic:
    """Test global merger for deduplication."""

    def test_merge_glossary_entries(self, mock_config):
        """Test glossary entry merging with duplicate detection."""
        generator = MetadataGenerator(mock_config, ['test-key'])

        entries = [
            {"Original_Term_CN": "张伟", "Frequency": 50},
            {"Original_Term_CN": "李明", "Frequency": 30},
            {"Original_Term_CN": "张伟", "Frequency": 70},  # Duplicate with higher frequency
        ]

        merged = generator._merge_glossary_entries(entries)

        assert len(merged) == 2
        # Should keep the entry with higher frequency
        zhang_wei = next(e for e in merged if e["Original_Term_CN"] == "张伟")
        assert zhang_wei["Frequency"] == 70

    def test_merge_character_entries(self, mock_config):
        """Test character entry merging with duplicate detection."""
        generator = MetadataGenerator(mock_config, ['test-key'])

        entries = [
            {"Character_A": "Zhang_Wei", "Type": "narrative_single", "Character_B": ""},
            {"Character_A": "Li_Ming", "Type": "narrative_single", "Character_B": ""},
            {"Character_A": "Zhang_Wei", "Type": "narrative_single", "Character_B": ""},  # Duplicate
        ]

        merged = generator._merge_character_entries(entries)

        assert len(merged) == 2


class TestJSONParsing:
    """Test JSON response parsing with various formats."""

    def test_parse_clean_json(self, mock_config):
        """Test parsing clean JSON response."""
        generator = MetadataGenerator(mock_config, ['test-key'])

        response = '{"glossary": [], "characters": []}'
        parsed = generator._parse_unified_response(response)

        assert parsed is not None
        assert "glossary" in parsed
        assert "characters" in parsed

    def test_parse_json_with_markdown_blocks(self, mock_config):
        """Test parsing JSON wrapped in markdown code blocks."""
        generator = MetadataGenerator(mock_config, ['test-key'])

        response = '```json\n{"glossary": [], "characters": []}\n```'
        parsed = generator._parse_unified_response(response)

        assert parsed is not None
        assert "glossary" in parsed

    def test_parse_invalid_json(self, mock_config):
        """Test handling of invalid JSON."""
        generator = MetadataGenerator(mock_config, ['test-key'])

        response = 'This is not JSON'
        parsed = generator._parse_unified_response(response)

        assert parsed is None


class TestCSVSaving:
    """Test CSV file saving functionality."""

    def test_save_glossary_csv(self, mock_config, tmp_path):
        """Test saving glossary to CSV file."""
        generator = MetadataGenerator(mock_config, ['test-key'])
        generator.glossary_path = tmp_path / "glossary.csv"

        entries = [
            {
                "Type": "Character",
                "Original_Term_Pinyin": "Zhang Wei",
                "Original_Term_CN": "张伟",
                "Translated_Term_VI": "Trương Vỹ",
                "Frequency": 50
            }
        ]

        success = generator._save_glossary_csv(entries)

        assert success is True
        assert generator.glossary_path.exists()

    def test_save_relations_csv(self, mock_config, tmp_path):
        """Test saving character relations to CSV file."""
        generator = MetadataGenerator(mock_config, ['test-key'])
        generator.relations_path = tmp_path / "relations.csv"

        entries = [
            {
                "Type": "narrative_single",
                "Character_A": "Zhang_Wei",
                "Narrative_Term": "Trương Vỹ / hắn"
            }
        ]

        success = generator._save_relations_csv(entries)

        assert success is True
        assert generator.relations_path.exists()

    def test_save_empty_glossary(self, mock_config, tmp_path):
        """Test saving empty glossary (should succeed without creating file)."""
        generator = MetadataGenerator(mock_config, ['test-key'])
        generator.glossary_path = tmp_path / "glossary.csv"

        success = generator._save_glossary_csv([])

        assert success is True  # Empty is not an error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
