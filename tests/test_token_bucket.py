
import time
import unittest

from src.utils.token_bucket import TokenBucket


class TestTokenBucket(unittest.TestCase):
    def test_bucket_consumption(self):
        """Test cơ bản về tiêu thụ token."""
        # 10 tokens capacity, 1 token/sec
        bucket = TokenBucket(rate=1.0, capacity=10.0, initial_tokens=10.0)

        # Consume 5 tokens
        self.assertTrue(bucket.consume(5.0))
        self.assertAlmostEqual(bucket.tokens, 5.0, delta=0.1)

        # Consume 6 tokens -> Fail (only 5 left)
        self.assertFalse(bucket.consume(6.0))

        # Consume 5 more
        self.assertTrue(bucket.consume(5.0))
        self.assertAlmostEqual(bucket.tokens, 0.0, delta=0.1)

    def test_bucket_refill(self):
        """Test refill logic."""
        # 1 token/sec
        bucket = TokenBucket(rate=1.0, capacity=10.0, initial_tokens=0.0)

        self.assertFalse(bucket.consume(1.0))

        # Wait 1.1 sec -> Should have > 1 token
        time.sleep(1.1)
        self.assertTrue(bucket.consume(1.0))

class TestAsyncTokenBucket(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_tokens(self):
        """Test async wait."""
        # Rate very fast for testing: 10 tokens/sec
        bucket = TokenBucket(rate=10.0, capacity=10.0, initial_tokens=0.0)

        start = time.monotonic()
        # Wait for 1 token -> Should wait approx 0.1s
        await bucket.wait_for_tokens(1.0)
        elapsed = time.monotonic() - start

        self.assertTrue(elapsed >= 0.1)
        self.assertTrue(elapsed < 0.5) # Allow more overhead for Windows/Asyncio

    async def test_wait_for_tokens_burst(self):
        """Test waiting for burst (capacity limited)."""
        bucket = TokenBucket(rate=100.0, capacity=5.0, initial_tokens=5.0)

        # Consume initial burst
        self.assertTrue(bucket.consume(5.0))

        start = time.monotonic()
        # Wait for 1 more -> Wait 0.01s (1/100)
        await bucket.wait_for_tokens(1.0)
        elapsed = time.monotonic() - start

        self.assertTrue(elapsed >= 0.01)

if __name__ == '__main__':
    unittest.main()
