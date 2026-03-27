import asyncio
import logging
from unittest.mock import MagicMock

from src.preprocessing.ocr.ai_processor import _ai_cleanup_parallel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NovelTranslator")

async def test_quota_guard():
    print("\n--- Testing Quota Guard ---")
    
    # Mock text chunks
    chunks = ["Chunk 1 content", "Chunk 2 content"]
    
    # Mock Key Manager with 0 active keys
    mock_km = MagicMock()
    mock_km.get_active_key_count.return_value = 0
    mock_km.get_available_key.return_value = None
    mock_km.get_quota_status_summary.return_value = {"available_keys": 0}
    
    # Run _ai_cleanup_parallel
    # result_text, total - failures, failures, failed_indices
    result_text, success_count, failures, failed_indices = await _ai_cleanup_parallel(
        text_chunks=chunks,
        api_keys=["fake-key"],
        model_name="fake-model",
        prompt="Cleanup: ",
        max_parallel=2,
        delay=0.1,
        show_progress=False,
        timeout_s=10,
        max_retries=1,
        progress_interval=10,
        key_manager=mock_km
    )
    
    print(f"Success Count: {success_count}")
    print(f"Failures: {failures}")
    print(f"Failed Indices: {failed_indices}")
    
    assert failures == 2
    assert success_count == 0
    assert failed_indices == [0, 1]
    print("SUCCESS: Quota Guard verification successful: Workflow stopped when 0 keys available.")

if __name__ == "__main__":
    asyncio.run(test_quota_guard())
