# -*- coding: utf-8 -*-

"""
Token Bucket Algorithm
======================
Implementation of the Token Bucket algorithm for rate limiting.
Allows managing Requests Per Minute (RPM) and Tokens Per Minute (TPM) with burst capability.
"""

import asyncio
import time
from typing import Optional


class TokenBucket:
    """
    Token Bucket rate limiter.

    Attributes:
        rate (float): Refill rate (tokens per second).
        capacity (float): Max burst capacity.
        tokens (float): Current available tokens.
        last_refill (float): Timestamp of last refill.
    """

    def __init__(
        self, rate: float, capacity: float, initial_tokens: Optional[float] = None
    ):
        """
        Args:
            rate: Tokens added per second. (e.g., 15 RPM -> 15/60 = 0.25 tokens/sec)
            capacity: Maximum bucket size (burst limit).
            initial_tokens: Initial tokens (defaults to capacity).
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.monotonic()

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        if elapsed > 0:
            added = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + added)
            self.last_refill = now

    def consume(self, amount: float = 1.0) -> bool:
        """
        Attempt to consume tokens. Returns True if successful, False otherwise.
        Non-blocking.
        """
        self._refill()

        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    async def wait_for_tokens(self, amount: float = 1.0):
        """
        Wait until enough tokens are available.
        Blocking (async).
        """
        if amount > self.capacity:
            raise ValueError(f"Amount {amount} exceeds bucket capacity {self.capacity}")

        while True:
            if self.consume(amount):
                return

            # Calculate wait time
            deficit = amount - self.tokens
            wait_time = deficit / self.rate

            # Wait at least a small interval to avoid busy loop
            await asyncio.sleep(max(0.1, wait_time))


class AdaptiveRateLimiter:
    """
    Composite Rate Limiter tracking both RPM and TPM.
    """

    def __init__(self, rpm_limit: int, tpm_limit: int):
        # RPM Bucket: rate = rpm/60, capacity = rpm (or smaller if we want less burst)
        self.rpm_bucket = TokenBucket(rate=rpm_limit / 60.0, capacity=rpm_limit)

        # TPM Bucket: rate = tpm/60
        self.tpm_bucket = TokenBucket(rate=tpm_limit / 60.0, capacity=tpm_limit)

    async def acquire(self, tokens: int = 0):
        """
        Acquire permission for 1 request with estimated N tokens.
        """
        # Wait for RPM (1 request cost = 1)
        await self.rpm_bucket.wait_for_tokens(1.0)

        # Wait for TPM (if tokens > 0)
        if tokens > 0:
            await self.tpm_bucket.wait_for_tokens(tokens)
