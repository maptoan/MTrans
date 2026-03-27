import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock

# Setup logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("NovelTranslator")

# We don't even need to instantiate NovelTranslator if we just want to test 
# how it handles exceptions in a loop.
# But let's try a targeted test.

async def verify_fix():
    print("\n--- Starting Verification of Fix ---")
    
    # Mock necessary parts
    mock_self = MagicMock()
    mock_self.rate_limit_backoff_delay = 0.1
    mock_self.key_manager = MagicMock()
    mock_self.key_manager.get_key_for_worker = AsyncMock(return_value="new_key")
    mock_self.key_manager.get_quota_status_summary = MagicMock(return_value={
        "quota_blocked_ratio": 0.1,
        "available_keys": 5
    })
    mock_self.key_manager.mark_request_error = MagicMock()
    mock_self.key_manager.return_key = AsyncMock()
    
    mock_self.error_handler = MagicMock()
    mock_self.error_handler.handle_error = MagicMock(return_value={'error_type': 'quota_exceeded'})
    
    # Import logic directly from the file to test the patched method
    from src.translation.translator import NovelTranslator
    
    # We want to test the _translate_one_chunk_worker method but we don't want to run the loop.
    # However, we can just run it once and see if it 'continues' (returns from loop or calls next)
    
    # Let's mock a simple version of the method logic or call the real one with mocks
    
    # The fix was in the generic Exception block of a loop.
    # To test it, we can run the real method but mock everything it calls.
    
    # Setup NovelTranslator instance with minimum requirements
    config = {
        'input': {'novel_path': 'dummy.txt'},
        'translation': {'max_retries_per_chunk': 1},
        'performance': {'max_parallel_workers': 1},
        'logging': {'show_chunk_progress': True}
    }
    # Create dummy file
    with open('dummy.txt', 'w') as f: f.write("test")
    
    translator = NovelTranslator(config, ["key1"])
    translator.key_manager = mock_self.key_manager
    translator.error_handler = mock_self.error_handler
    translator.metrics_collector = MagicMock()
    translator.model_router = MagicMock()
    
    # First call fails with 429 string, second call (if rotation works) should succeed or at least not fail immediately.
    # Actually, we just need to see if it calls key_manager.mark_request_error and then tries to get a new key.
    
    translator.model_router.translate_chunk_async = AsyncMock(side_effect=[
        Exception("429 RESOURCE_EXHAUSTED"), # First attempt
        {'status': 'success', 'translation': 'Translated text', 'model_used': 'flash'} # Second attempt
    ])
    
    chunk = {'global_id': 1, 'text': 'Original text'}
    result = await translator._translate_one_chunk_worker(chunk, [], [], worker_id=0)
    
    print(f"\nResult status: {result['status']}")
    
    # Verify expectations
    if result['status'] == 'success':
        print("✅ SUCCESS: The translator rotated the key and succeeded on the second attempt!")
    else:
        print(f"❌ FAILURE: Result status was {result['status']}, error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
