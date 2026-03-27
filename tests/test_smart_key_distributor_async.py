
import asyncio
import os
import sys
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.smart_key_distributor import SmartKeyDistributor


class TestSmartKeyDistributorAsync(unittest.TestCase):
    """Test SmartKeyDistributor async method compatibility."""

    def setUp(self):
        self.api_keys = [f"test_key_{i}" for i in range(10)]
        self.num_chunks = 5
        self.config = {}
        self.distributor = SmartKeyDistributor(self.api_keys, self.num_chunks, self.config)

    def test_get_key_for_worker_is_async(self):
        """Verify get_key_for_worker is an async coroutine function."""
        self.assertTrue(
            asyncio.iscoroutinefunction(self.distributor.get_key_for_worker),
            "get_key_for_worker MUST be async"
        )
        print("[PASS] get_key_for_worker is async")

    def test_add_delay_between_requests_is_async(self):
        """Verify add_delay_between_requests is an async coroutine function."""
        self.assertTrue(
            asyncio.iscoroutinefunction(self.distributor.add_delay_between_requests),
            "add_delay_between_requests MUST be async"
        )
        print("[PASS] add_delay_between_requests is async")

    def test_return_key_is_async(self):
        """Verify return_key is an async coroutine function."""
        self.assertTrue(
            asyncio.iscoroutinefunction(self.distributor.return_key),
            "return_key MUST be async"
        )
        print("[PASS] return_key is async")

    def test_replace_worker_key_is_async(self):
        """Verify replace_worker_key is an async coroutine function."""
        self.assertTrue(
            asyncio.iscoroutinefunction(self.distributor.replace_worker_key),
            "replace_worker_key MUST be async"
        )
        print("[PASS] replace_worker_key is async")

    def test_async_methods_are_awaitable(self):
        """Test that async methods can be awaited without TypeError."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_checks():
            # Test get_key_for_worker
            key = await self.distributor.get_key_for_worker(worker_id=1)
            self.assertIsNotNone(key)
            print(f"[PASS] get_key_for_worker returned: {key}")

            # Test add_delay_between_requests
            await self.distributor.add_delay_between_requests(key)
            print("[PASS] add_delay_between_requests completed")

            # Test return_key
            await self.distributor.return_key(worker_id=1, key=key, is_error=False)
            print("[PASS] return_key completed")

            # Test replace_worker_key
            new_key = await self.distributor.replace_worker_key(
                worker_id=1,
                failed_key=key,
                error_type='rate_limit',
                error_message="Test error"
            )
            print(f"[PASS] replace_worker_key returned: {new_key}")

        try:
            loop.run_until_complete(run_checks())
        finally:
            loop.close()

if __name__ == '__main__':
    print("=" * 60)
    print("SmartKeyDistributor Async Compatibility Test")
    print("=" * 60)
    unittest.main(verbosity=2)
