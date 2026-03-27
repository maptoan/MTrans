# -*- coding: utf-8 -*-
"""
Unit tests for TranslationRefiner module.
"""
import pytest

from src.translation.refiners import TranslationRefiner


class MockRelationManager:
    """Mock RelationManager for testing."""

    def get_pronoun_guidance(self, char, context):
        return []

    def get_narrative_terms_map(self):
        return {}


@pytest.fixture
def refiner():
    """Create a TranslationRefiner instance for testing."""
    config = {
        "translation": {
            "postprocessing": {
                "dialog_quotations": ['"', '"', "「」"]
            }
        }
    }
    relation_manager = MockRelationManager()
    return TranslationRefiner(config, relation_manager)


class TestAutoFixGlossary:
    """Test glossary auto-fix functionality."""

    def test_fix_cn_term(self, refiner):
        """Test replacing Chinese term with Vietnamese."""
        translation = "Anh ấy là 修真者 mạnh nhất."
        relevant_terms = [
            {
                "Original_Term_CN": "修真者",
                "Original_Term_Pinyin": "xiuzhenzhě",
                "Translated_Term_VI": "tu chân giả"
            }
        ]

        fixed, count = refiner.auto_fix_glossary(translation, relevant_terms)

        assert "修真者" not in fixed
        assert "tu chân giả" in fixed
        assert count == 1

    def test_fix_pinyin_term_case_insensitive(self, refiner):
        """Test replacing Pinyin term (case insensitive)."""
        translation = "Anh ấy là Xiuzhenzhě mạnh nhất."
        relevant_terms = [
            {
                "Original_Term_CN": "修真者",
                "Original_Term_Pinyin": "xiuzhenzhě",
                "Translated_Term_VI": "tu chân giả"
            }
        ]

        fixed, count = refiner.auto_fix_glossary(translation, relevant_terms)

        assert "Xiuzhenzhě" not in fixed
        assert "tu chân giả" in fixed
        assert count == 1

    def test_no_fix_needed(self, refiner):
        """Test when no fixes are needed."""
        translation = "Anh ấy là tu chân giả mạnh nhất."
        relevant_terms = [
            {
                "Original_Term_CN": "修真者",
                "Original_Term_Pinyin": "xiuzhenzhě",
                "Translated_Term_VI": "tu chân giả"
            }
        ]

        fixed, count = refiner.auto_fix_glossary(translation, relevant_terms)

        assert fixed == translation
        assert count == 0


class TestDetectCJKRemaining:
    """Test CJK character detection."""

    def test_detect_chinese_characters(self, refiner):
        """Test detecting Chinese characters."""
        text = "This is a test 测试 with Chinese."

        result = refiner.detect_cjk_remaining(text)

        # Should only detect actual CJK characters, not English words
        assert len(result) >= 1
        assert any("测试" in term for term in result)

    def test_no_cjk_characters(self, refiner):
        """Test text without CJK characters."""
        text = "Pure English text only"

        result = refiner.detect_cjk_remaining(text)

        # CJK pattern should not match English text
        # If it does, it's a bug in the regex
        cjk_found = any(ord(c) >= 0x4e00 for term in result for c in term)
        assert not cjk_found, f"Found false CJK matches: {result}"

    def test_multiple_cjk_terms(self, refiner):
        """Test detecting multiple CJK terms."""
        text = "混合 text with 多个 Chinese 词语"

        result = refiner.detect_cjk_remaining(text)

        # Should detect all CJK terms
        assert len(result) >= 3
        cjk_chars = ''.join(result)
        assert "混合" in cjk_chars or any("混" in r and "合" in r for r in result)
        assert "多个" in cjk_chars or any("多" in r and "个" in r for r in result)
        assert "词语" in cjk_chars or any("词" in r and "语" in r for r in result)


class TestValidateMetadataCompliance:
    """Test metadata compliance validation."""

    def test_compliance_pass(self, refiner):
        """Test when translation is compliant."""
        translation = "Anh ấy là tu chân giả mạnh nhất."
        relevant_terms = [
            {
                "Original_Term_CN": "修真者",
                "Translated_Term_VI": "tu chân giả"
            }
        ]

        is_compliant = refiner.validate_metadata_compliance(
            translation, relevant_terms, [], chunk_id=1
        )

        assert is_compliant is True

    def test_compliance_fail_cn_term(self, refiner):
        """Test when Chinese term is not translated."""
        translation = "Anh ấy là 修真者 mạnh nhất."
        relevant_terms = [
            {
                "Original_Term_CN": "修真者",
                "Translated_Term_VI": "tu chân giả"
            }
        ]

        is_compliant = refiner.validate_metadata_compliance(
            translation, relevant_terms, [], chunk_id=1
        )

        assert is_compliant is False
