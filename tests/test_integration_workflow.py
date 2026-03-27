import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.translation.execution_manager import ExecutionManager


class TestIntegrationWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_execution_queue_flow(self):
        """
        Integration Test: ExecutionManager -> Queue -> Worker
        Verifies that workers pick tasks from the queue and utilize available keys.
        """
        # 1. Setup Mock Resources
        # Mock HybridKeyManager (Simulate 5 active keys)
        mock_key_manager = MagicMock()
        mock_key_manager.api_keys = ["k1", "k2", "k3", "k4", "k5"]
        mock_key_manager.get_active_key_count.return_value = 5
        mock_key_manager.get_key_for_worker = AsyncMock(side_effect=["k1", "k2", "k3", "k4", "k5"])
        mock_key_manager.is_key_blocked.return_value = False

        # Mock ProgressManager
        mock_progress = MagicMock()
        mock_progress.is_chunk_completed.return_value = False
        mock_progress.completed_chunks = {}

        # Mock Translator (The Worker Logic)
        mock_translator = MagicMock()
        mock_translator.worker_caches = {}
        mock_translator._get_context_chunks.return_value = ("Original Context", "Translated Context")
        # Simulate successful translation
        mock_translator._translate_one_chunk_worker = AsyncMock(
            return_value={"status": "success", "translation": "Translated Text"}
        )

        # Mock Metrics Collector
        mock_metrics = MagicMock()
        mock_metrics.get_statistics.return_value = {"chunk_count": 0, "success_rate": 1.0, "error_types": {}}

        # 2. Initialize ExecutionManager
        resources = {
            "key_manager": mock_key_manager,
            "progress_manager": mock_progress,
            "metrics_collector": mock_metrics,
        }
        config = {"performance": {"startup_jitter": {"min": 0, "max": 0}}}
        manager = ExecutionManager(resources, config)

        # 3. Create Dummy Chunks
        chunks = [{"global_id": i, "text": f"Chunk {i}"} for i in range(10)]

        # 4. Run translate_all
        # This will spawn 5 workers (from 5 keys) to process 10 chunks
        failed_chunks = await manager.translate_all(chunks, mock_translator)

        # 5. Assertions
        # No failures
        self.assertEqual(len(failed_chunks), 0)

        # Translator called 10 times
        self.assertEqual(mock_translator._translate_one_chunk_worker.call_count, 10)

        # Progress saved 10 times
        self.assertEqual(mock_progress.save_chunk_result.call_count, 10)

        # Verify Context Passing (Mocked Check)
        # We can inspect call_args to see if context was passed
        # call_args_list[0] -> (args, kwargs) -> args[1] is original_context
        first_call_args = mock_translator._translate_one_chunk_worker.call_args_list[0]
        self.assertEqual(first_call_args[0][1], "Original Context")

    async def test_admission_control_stress(self):
        """
        Integration Test: Admission Control
        Verifies that workers sleep when system health is low.
        """
        # Mock Key Manager to report LOW health
        mock_key_manager = MagicMock()
        mock_key_manager.api_keys = ["k1"] * 10
        mock_key_manager.get_active_key_count.return_value = 2  # 20% health (< 30%)
        mock_key_manager.is_key_blocked.return_value = False

        manager = ExecutionManager(
            {"key_manager": mock_key_manager, "progress_manager": MagicMock(), "metrics_collector": MagicMock()},
            {"performance": {"startup_jitter": {"min": 0, "max": 0}}},
        )

        # We patch asyncio.sleep to verify it's called with '5' (Critical sleep)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await manager._acquire_admission()
            # Expect at least one call with 5 seconds
            mock_sleep.assert_called_with(5)


if __name__ == "__main__":
    unittest.main()
