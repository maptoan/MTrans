import asyncio
import logging
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NovelTranslator")

# Mock necessary modules
sys.modules['google.api_core.exceptions'] = MagicMock()
import google.api_core.exceptions


async def simulate_failure():
    # Mock dependencies
    mock_key_manager = MagicMock()
    mock_key_manager.get_key_for_worker = AsyncMock(return_value="mock_key")
    mock_key_manager.is_key_blocked = MagicMock(return_value=False)
    mock_key_manager.mark_request_error = MagicMock()
    mock_key_manager.return_key = AsyncMock()
    mock_key_manager.get_quota_status_summary = MagicMock(return_value={
        "quota_blocked_ratio": 0.1,
        "quota_blocked_keys": 1,
        "total_keys": 10,
        "available_keys": 9
    })

    mock_model_router = MagicMock()
    # Simulate the NEW SDK error that is NOT an instance of google.api_core.exceptions.ResourceExhausted
    # but contains "429 RESOURCE_EXHAUSTED" in its message
    mock_model_router.translate_chunk_async = AsyncMock(side_effect=Exception("429 RESOURCE_EXHAUSTED: Quota exceeded"))

    mock_metrics = MagicMock()
    mock_progress = MagicMock()
    mock_error_handler = MagicMock()
    # Classify as quota_exceeded
    mock_error_handler.handle_error = MagicMock(return_value={
        'error_type': 'quota_exceeded',
        'recovery_strategy': {'should_retry': True, 'cooldown_time': 5}
    })

    # Instantiate translator (partially mocked)
    from src.translation.translator import NovelTranslator
    
    config = {
        'input': {
            'novel_path': 'dummy.txt'
        },
        'translation': {
            'rate_limit_backoff_delay': 1,
            'max_retries_per_chunk': 1 # Speed up test
        },
        'performance': {
            'max_parallel_workers': 5,
            'rate_limit_backoff_delay': 1
        },
        'logging': {
            'show_chunk_progress': True
        }
    }
    
    # Create a dummy novel file if it doesn't exist to satisfy __init__
    if not os.path.exists('dummy.txt'):
        with open('dummy.txt', 'w') as f:
            f.write("Dummy content")

    translator = NovelTranslator(config, valid_api_keys=["mock_key"])
    translator.key_manager = mock_key_manager
    translator.model_router = mock_model_router
    translator.metrics_collector = mock_metrics
    translator.progress_manager = mock_progress
    translator.error_handler = mock_error_handler
    translator.prompt_builder = MagicMock()
    
    # Run the test
    chunk = {'global_id': 1, 'text': 'Test text'}
    print("\n--- Starting Reproduction Test ---")
    result = await translator._translate_one_chunk_worker(chunk, [], [], worker_id=0)
    
    print(f"\nResult status: {result['status']}")
    if result['status'] == 'failed':
        print("❌ REPRODUCED: Chunk failed instead of rotating key!")
        if "Lỗi không thể thử lại" in str(result.get('error', '')):
             print("Reason: Caught by generic Exception block as terminal error.")
    else:
        print("✅ FIXED: Chunk did not fail, it likely tried to rotate.")

if __name__ == "__main__":
    asyncio.run(simulate_failure())
