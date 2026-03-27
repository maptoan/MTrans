import unittest
from unittest.mock import MagicMock

from src.translation.output_manager import OutputManager
from src.translation.translator import NovelTranslator


class TestMarkerGuardrailGating(unittest.TestCase):
    def _build_translator_stub(self, use_markers: bool) -> NovelTranslator:
        translator = NovelTranslator.__new__(NovelTranslator)
        translator.use_markers = use_markers
        translator._marker_pattern_cache = {}
        return translator

    def test_no_markers_skip_marker_validation(self) -> None:
        translator = self._build_translator_stub(use_markers=False)
        original_chunks = [{"global_id": 1, "text": "No marker input"}]
        translated_parts = ["Ban dich binh thuong"]

        translator._validate_with_markers = MagicMock(side_effect=AssertionError("must not be called"))
        translator._validate_and_merge_chunks = MagicMock(return_value="fallback-merged")

        merged = translator._validate_and_merge_chunks_optimized(translated_parts, original_chunks)

        self.assertEqual(merged, "fallback-merged")
        translator._validate_and_merge_chunks.assert_called_once_with(translated_parts, original_chunks)

    def test_with_markers_strict_path_still_active(self) -> None:
        translator = self._build_translator_stub(use_markers=True)
        original_chunks = [{"global_id": 1, "text": "plain"}]
        translated_parts = ["[CHUNK:1:START]Ban dich[CHUNK:1:END]"]

        translator._validate_with_markers = MagicMock(
            return_value={"is_valid": True, "chunks": ["Ban dich"], "suspicious_chunks": []}
        )
        translator._merge_with_markers = MagicMock(return_value="Ban dich")

        merged = translator._validate_and_merge_chunks_optimized(translated_parts, original_chunks)

        self.assertEqual(merged, "Ban dich")
        translator._validate_with_markers.assert_called_once()
        translator._merge_with_markers.assert_called_once_with(["Ban dich"])

    def test_config_input_mismatch_detects_original_markers(self) -> None:
        translator = self._build_translator_stub(use_markers=False)
        original_chunks = [{"global_id": 1, "text": "[CHUNK:1:START]abc[CHUNK:1:END]"}]

        enabled = translator._is_marker_guardrail_enabled(original_chunks)

        self.assertTrue(enabled)

    def test_retry_once_missing_end_then_success(self) -> None:
        translator = self._build_translator_stub(use_markers=True)
        original_chunks = [{"global_id": 1, "text": "[CHUNK:1:START]goc[CHUNK:1:END]"}]

        first_pass = ["[CHUNK:1:START]ban dich thieu end"]
        second_pass = ["[CHUNK:1:START]ban dich du[CHUNK:1:END]"]

        first_result = translator._validate_and_merge_chunks_optimized(first_pass, original_chunks)
        second_result = translator._validate_and_merge_chunks_optimized(second_pass, original_chunks)

        self.assertIsNone(first_result)
        self.assertEqual(second_result, "ban dich du")


class TestOutputManagerMarkerGuardrail(unittest.TestCase):
    def test_validate_with_markers_bypassed_when_guardrail_disabled(self) -> None:
        manager = OutputManager(
            progress_manager=MagicMock(),
            output_formatter=MagicMock(),
            novel_name="demo",
            config={"preprocessing": {"chunking": {"use_markers": True}}},
        )
        translated_parts = ["khong co marker"]
        original_chunks = [{"global_id": 1}]

        result = manager.validate_with_markers(
            translated_parts,
            original_chunks,
            marker_guardrail_enabled=False,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["suspicious_chunks"], [])
        self.assertEqual(result["cleaned_chunks"], ["khong co marker"])


if __name__ == "__main__":
    unittest.main()
