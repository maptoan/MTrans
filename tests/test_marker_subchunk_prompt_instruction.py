import unittest

from src.translation.prompt_builder import PromptBuilder


class TestMarkerPreservationInstructionForSubChunks(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "preprocessing": {"chunking": {"use_markers": True, "marker_format": "simple"}},
            "metadata": {"document_type": "general"},
            "translation": {},
            "logging": {},
        }

    def test_instruction_present_when_only_start_marker_exists(self) -> None:
        pb = PromptBuilder(None, None, None, document_type="general", config=self.config)  # type: ignore[arg-type]
        inst = pb._build_marker_preservation_instruction("[CHUNK:1:START]\nHello")
        self.assertIn("Bảo tồn Marker CHUNK", inst)
        self.assertIn("Sub-chunk", inst)

    def test_instruction_present_when_only_end_marker_exists(self) -> None:
        pb = PromptBuilder(None, None, None, document_type="general", config=self.config)  # type: ignore[arg-type]
        inst = pb._build_marker_preservation_instruction("World\n[CHUNK:1:END]")
        self.assertIn("Bảo tồn Marker CHUNK", inst)
        self.assertIn("Sub-chunk", inst)


if __name__ == "__main__":
    unittest.main()

