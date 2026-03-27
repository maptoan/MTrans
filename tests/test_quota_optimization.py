import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.translation.translator import NovelTranslator


class TestQuotaOptimization(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = {
            "input": {"novel_path": "dummy.txt"},
            "translation": {
                "context_caching": {"enabled": True, "ttl_minutes": 60},
                "use_new_sdk": True,
                "max_retries_per_chunk": 2,
            },
            "performance": {"max_parallel_workers": 5, "use_optimized_key_workflow": False},
            "metadata": {"document_type": "novel"},
        }
        self.api_keys = ["key1"]

    @patch("src.services.smart_key_distributor.SmartKeyDistributor")
    @patch("src.services.gemini_api_service.GeminiAPIService")
    @patch("src.preprocessing.chunker.SmartChunker")
    @patch("src.managers.progress_manager.ProgressManager")
    async def test_warm_up_once(self, mock_progress, mock_chunker, mock_gemini, mock_skd):
        # Setup
        mock_chunker.return_value.chunk_novel.return_value = [{"global_id": 1, "text": "Chunk 1"}]
        chunks = [{"global_id": 1, "text": "Chunk 1"}]

        # Ensure it doesn't think all chunks are completed
        mock_progress.return_value.is_chunk_completed.return_value = False

        translator = NovelTranslator(self.config, self.api_keys)

        # Patch open to avoid file reading issues
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Content"

            # Mock warm_up_resources on init_service
            translator.init_service.warm_up_resources = AsyncMock(return_value={"key1": "cache1"})

            # Mock executor which is ExecutionManager
            translator.executor = MagicMock()
            translator.executor.translate_all = AsyncMock(return_value=[])

            # Mock setup_resources_async to avoid re-init overwriting mocks
            translator.setup_resources_async = AsyncMock()

            # Run cycle
            await translator._translate_all_chunks(chunks)

            # Verify warm_up_resources was called
            self.assertEqual(translator.init_service.warm_up_resources.call_count, 1)
            self.assertTrue(translator._warm_up_completed)

            # Run again - should NOT call warm_up again if reused
            await translator._translate_all_chunks(chunks)
            self.assertEqual(translator.init_service.warm_up_resources.call_count, 1)

    # Legacy test_partitioning_sanity removed as _dedicated_worker_consumer is deprecated.


if __name__ == "__main__":
    unittest.main()
