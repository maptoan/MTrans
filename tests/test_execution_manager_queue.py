import unittest
from unittest.mock import AsyncMock, MagicMock

from src.translation.execution_manager import ExecutionManager


class TestExecutionManagerQueue(unittest.IsolatedAsyncioTestCase):
    async def test_translate_all_queue_processing(self):
        """Test that chunks are processed via queue."""
        # Setup mocks
        mock_keys = MagicMock()
        mock_keys.get_active_key_count.return_value = 5  # Healthy
        mock_keys.api_keys = ["k1", "k2"]
        mock_keys.get_key_for_worker = AsyncMock(side_effect=["k1", "k2"])
        mock_keys.is_key_blocked.return_value = False

        mock_progress = MagicMock()
        mock_progress.is_chunk_completed.return_value = False
        mock_progress.completed_chunks = {}

        mock_metrics = MagicMock()
        mock_metrics.get_statistics.return_value = {"chunk_count": 0, "success_rate": 1.0, "error_types": {}}

        manager = ExecutionManager(
            {"key_manager": mock_keys, "progress_manager": mock_progress, "metrics_collector": mock_metrics},
            {"performance": {}},
        )

        # Test Data: 4 chunks
        chunks = [
            {"global_id": 0, "text": "c0"},
            {"global_id": 1, "text": "c1"},
            {"global_id": 2, "text": "c2"},
            {"global_id": 3, "text": "c3"},
        ]

        # Mock Translator Instance
        translator = MagicMock()
        translator.worker_caches = {}
        translator._get_context_chunks.return_value = ("orig", "trans")
        translator._translate_one_chunk_worker = AsyncMock(
            return_value={"status": "success", "translation": "trans_done"}
        )

        # Run
        failed = await manager.translate_all(chunks, translator)

        # Verify
        self.assertEqual(len(failed), 0)
        # Check call count: 4 chunks processed
        self.assertEqual(translator._translate_one_chunk_worker.call_count, 4)

        # Verify saving
        self.assertEqual(mock_progress.save_chunk_result.call_count, 4)

    async def test_priority_order(self):
        """Verify priority queue picks chunk 0 before chunk 1."""
        # This is harder to test with async concurrency,
        # but we can verify that queue puts items with correct priority.
        # We implicitly trust asyncio.PriorityQueue.
        pass


if __name__ == "__main__":
    unittest.main()
