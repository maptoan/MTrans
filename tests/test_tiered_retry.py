import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import google.api_core.exceptions

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.translation.translator import NovelTranslator
from src.utils.error_handler import CentralizedErrorHandler


class TestTieredRetry(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = {
            "input": {"novel_path": "dummy.pdf"},
            "translation": {"context_caching": {"enabled": False}},
            "performance": {},
            "error_handling": {"enabled": True},
        }
        self.valid_keys = ["key1"]
        # Mock dependencies
        patcher_init = patch("src.translation.initialization_service.InitializationService")
        patcher_exec = patch("src.translation.execution_manager.ExecutionManager")
        self.mock_init_service = patcher_init.start()
        self.mock_exec_manager = patcher_exec.start()
        self.addCleanup(patcher_init.stop)
        self.addCleanup(patcher_exec.stop)

        self.translator = NovelTranslator(self.config, self.valid_keys)
        self.translator.suppress_logs = False
        self.translator._request_semaphore = asyncio.Semaphore(1)

        self.translator.error_handler = CentralizedErrorHandler(self.config)
        self.translator.key_manager = MagicMock()
        self.translator.key_manager.get_key_for_worker = AsyncMock(return_value="key1")
        self.translator.key_manager.return_key = AsyncMock()
        self.translator.key_manager.add_delay_between_requests = AsyncMock()
        self.translator.key_manager.mark_request_error = MagicMock()
        self.translator.key_manager.mark_request_success = MagicMock()
        self.translator.key_manager.get_quota_status_summary.return_value = {
            "quota_blocked_ratio": 0.0,
            "available_keys": 1,
            "total_keys": 1,
        }

        self.translator.model_router = Mock()
        self.translator.model_router.get_model_priority.return_value = ["model1"]
        self.translator.model_router.analyze_chunk_complexity.return_value = 1
        self.translator.model_router.translate_chunk_async = AsyncMock()

        self.translator.error_handler = Mock()

        def side_effect_handler(*args, **kwargs):
            return {"recovery_strategy": {"cooldown_time": 2, "should_retry": True}, "error_type": "timeout"}

        self.translator.error_handler.handle_error.side_effect = side_effect_handler

        self.translator.prompt_orchestrator = Mock()
        self.translator.prompt_orchestrator.build_translation_prompt = AsyncMock(
            return_value=("prompt", None, [], [])
        )

        self.translator.result_handler = Mock()
        self.translator.result_handler.validate_translation_result.return_value = (True, "Translated text", None)

        self.translator.refiner = Mock()
        self.translator.refiner.detect_cjk_remaining.return_value = []
        self.translator.refiner.validate_metadata_compliance.return_value = True
        self.translator.refiner.enforce_narrative_terms.return_value = "Translated text"
        self.translator.refiner.auto_fix_glossary_enhanced.return_value = ("Translated text", 0)

        self.translator.cjk_cleaner = Mock()
        self.translator.cjk_cleaner.final_cleanup_pass = AsyncMock(return_value="Translated text")

        self.translator.validator = Mock()
        self.translator.validator.validate.return_value = {"is_valid": True, "issues": []}

        self.translator.metrics_collector = Mock()

        # Mock coverage check to avoid fallback logic
        self.translator._check_content_coverage = Mock(return_value=True)
        self.translator._validate_translated_content = Mock(return_value=True)
        self.translator._count_tokens = Mock(return_value=10)
        self.translator._record_token_usage = Mock()

        import re

        self.translator.title_pattern = re.compile(r"test")

    @patch("src.translation.translator.asyncio.sleep")
    async def test_fast_retry_timeout(self, mock_sleep):
        """Verify that Timeout triggers Fast Retry (small sleep)."""
        self.translator.model_router.translate_chunk_async.side_effect = [
            google.api_core.exceptions.DeadlineExceeded("Timeout"),
            {"status": "success", "translation": "Translated text", "model": "gemini"},
        ]

        chunk = {"global_id": 1, "text": "Hello"}
        await self.translator._translate_one_chunk_worker(chunk, [], [], worker_id=1, api_key="key1")

        self.assertTrue(mock_sleep.called)
        first_sleep_arg = mock_sleep.call_args_list[0][0][0]
        self.assertGreaterEqual(first_sleep_arg, 2.1)
        self.assertLessEqual(first_sleep_arg, 3.1)

    @patch("src.translation.translator.asyncio.sleep")
    async def test_fast_retry_server_error(self, mock_sleep):
        """Verify that Server Error triggers Fast Retry (medium sleep)."""
        self.translator.error_handler.handle_error.side_effect = None
        self.translator.error_handler.handle_error.return_value = {
            "recovery_strategy": {"cooldown_time": 5, "should_retry": True},
            "error_type": "server_error",
        }

        self.translator.model_router.translate_chunk_async.side_effect = [
            google.api_core.exceptions.ServiceUnavailable("503"),
            {"status": "success", "translation": "Translated text", "model": "gemini"},
        ]

        chunk = {"global_id": 1, "text": "Hello"}
        await self.translator._translate_one_chunk_worker(chunk, [], [], worker_id=1, api_key="key1")

        first_sleep_arg = mock_sleep.call_args_list[0][0][0]
        self.assertGreaterEqual(first_sleep_arg, 5.1)
        self.assertLessEqual(first_sleep_arg, 6.1)


if __name__ == "__main__":
    unittest.main()
