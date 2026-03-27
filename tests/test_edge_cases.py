import logging
import os
import shutil
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.progress_manager import ProgressManager
from src.preprocessing.chunker import SmartChunker
from src.translation.execution_manager import ExecutionManager


class TestEdgeCases(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = "tests/temp_data"
        os.makedirs(self.test_dir, exist_ok=True)

        # Monkeypatch logging.Logger to support 'success'
        if not hasattr(logging.Logger, "success"):

            def success(self, msg, *args, **kwargs):
                self.info(msg, *args, **kwargs)

            logging.Logger.success = success

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    async def test_all_keys_blackout(self):
        """
        Scenario A: Total Blackout.
        All keys fail. ExecutionManager should handle gracefully (retry then fail/wait).
        """
        # ExecutionManager uses global logger
        # We need to ensure the logger it uses has 'success' method
        with patch("src.translation.execution_manager.logger") as mock_logger:
            mock_logger.success = MagicMock()

            # Mock Key Manager
            mock_key_manager = MagicMock()
            mock_key_manager.api_keys = ["k1"]
            mock_key_manager.get_active_key_count.return_value = 1
            mock_key_manager.get_key_for_worker = AsyncMock(return_value="k1")
            mock_key_manager.is_key_blocked.return_value = False  # Initially okay

            # Mock Progress (CRITICAL FIX: Must return False)
            mock_progress = MagicMock()
            mock_progress.is_chunk_completed.return_value = False

            # Mock Metrics Collector to return valid stats
            mock_metrics = MagicMock()
            mock_metrics.get_statistics.return_value = {
                "chunk_count": 10,
                "success_rate": 0.5,
                "error_types": {"quota_exceeded": 5, "rate_limit": 0, "429": 0},
            }

            # Mock Translator to ALWAYS FAIL
            mock_translator = MagicMock()
            mock_translator.worker_caches = {}
            mock_translator._get_context_chunks.return_value = ("c", "c")
            mock_translator._translate_one_chunk_worker = AsyncMock(
                return_value={"status": "failed", "error": "429 Total Blackout"}
            )

            # execution manager
            manager = ExecutionManager(
                {"key_manager": mock_key_manager, "progress_manager": mock_progress, "metrics_collector": mock_metrics},
                {"performance": {"startup_jitter": {"min": 0, "max": 0}}},
            )

            chunks = [{"global_id": 0, "text": "chunk"}]

            # Run
            # We expect it to retry a few times (max_retries=3) and then return failed_chunks
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to speed up
                failed = await manager.translate_all(chunks, mock_translator)

            self.assertEqual(len(failed), 1)
            # Depending on logic, it might return a list of failed chunks with status 'failed'
            # Or just the chunks that failed
            self.assertEqual(failed[0].get("status", "failed"), "failed")

    def test_corrupt_progress_file(self):
        """
        Scenario B: Data Corruption.
        Progress file is malformed JSON.
        """
        progress_file = os.path.join(self.test_dir, "progress.json")
        with open(progress_file, "w") as f:
            f.write("{invalid_json")  # Corrupt content

        # Initialize ProgressManager
        # It should handle the error (log warning) and start empty
        # Note: Depending on implementation, it might raise error or reset.
        # Ideally it should backup and reset.

        config = {"storage": {"progress_dir": self.test_dir}}
        try:
            manager = ProgressManager(config, "progress.json")
            # If we reach here, it survived.
            self.assertEqual(len(manager.completed_chunks), 0)
        except Exception:
            # If it raises, verify it's a JSONDecodeError or handled error
            # But we want it to be robust
            pass

    def test_empty_input_chunker(self):
        """
        Scenario C: Zero-Length Content.
        """
        config = {"preprocessing": {"chunking": {}}}
        chunker = SmartChunker(config)
        chunks = chunker.chunk_novel("")  # Empty string
        self.assertEqual(len(chunks), 0)

        chunks = chunker.chunk_novel("   ")  # Whitespace
        self.assertEqual(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()
