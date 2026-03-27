import os
import sys
import unittest
from unittest.mock import patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.translation.initialization_service import InitializationService


class TestInitializationServiceSplit(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = {
            "translation": {},
            "performance": {"max_parallel_workers": 2, "use_optimized_key_workflow": False},
            "metadata": {},
            "preprocessing": {},
        }
        self.service = InitializationService(self.config)
        self.api_keys = ["key1", "key2"]
        self.novel_name = "TestNovel"

    @patch("src.services.smart_key_distributor.SmartKeyDistributor")
    @patch("src.utils.metrics_collector.MetricsCollector")
    @patch("src.utils.error_handler.CentralizedErrorHandler")
    @patch("src.translation.model_router.SmartModelRouter")
    @patch("src.preprocessing.chunker.SmartChunker")
    @patch("src.managers.style_manager.StyleManager")
    @patch("src.managers.glossary_manager.GlossaryManager")
    @patch("src.managers.relation_manager.RelationManager")
    @patch("src.translation.prompt_builder.PromptBuilder")
    @patch("src.managers.progress_manager.ProgressManager")
    @patch("src.output.formatter.OutputFormatter")
    @patch("src.services.gemini_api_service.GeminiAPIService")
    async def test_split_initialization(self, mock_gemini, mock_formatter, mock_progress, *args):
        # 1. Test Shared Init
        shared = await self.service.initialize_shared_resources(self.api_keys)
        self.assertIn("key_manager", shared)
        self.assertNotIn("progress_manager", shared)

        # 2. Test Specific Init
        # We need to ensure shared has what initialize_novel_specific_resources expects
        # It expects output_formatter, prompt_builder, gemini_service
        # Since we mocked them, they should be in 'shared' because initialize_shared_resources puts them there.
        # But wait, initialize_shared_resources creates them using the mocked classes.

        full = await self.service.initialize_novel_specific_resources(shared, self.novel_name)
        self.assertIn("progress_manager", full)

        # Verify ProgressManager called with correct novel name
        # mock_progress is the 3rd argument from bottom (Gemini, Formatter, Progress)
        # Check args mapping:
        # mock_gemini -> GeminiAPIService (Bottom)
        # mock_formatter -> OutputFormatter
        # mock_progress -> ProgressManager

        # Note: ProgressManager is instantiated in initialize_novel_specific_resources
        # shared resources are instantiated in initialize_shared_resources

        # When initialize_novel_specific_resources is called, it instantiates ProgressManager(config, novel_name)
        # So our mock should catch that.
        # However, we need to be careful about *args consuming the rest.

        mock_progress.assert_called_with(self.config, self.novel_name)

    @patch("src.translation.initialization_service.InitializationService.initialize_shared_resources")
    @patch("src.translation.initialization_service.InitializationService.initialize_novel_specific_resources")
    async def test_backward_compatibility(self, mock_specific, mock_shared):
        mock_shared.return_value = {"shared": True}
        mock_specific.return_value = {"shared": True, "specific": True}

        result = await self.service.initialize_all(self.api_keys, self.novel_name)

        mock_shared.assert_called_once_with(self.api_keys)
        mock_specific.assert_called_once_with({"shared": True}, self.novel_name)
        self.assertEqual(result["specific"], True)


if __name__ == "__main__":
    unittest.main()
