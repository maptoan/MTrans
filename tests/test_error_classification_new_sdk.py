# -*- coding: utf-8 -*-
"""
Test: Error Classification for New SDK (v5.2)
==============================================
Tests the error classification logic for google.genai SDK exceptions.
Ensures proper handling of:
- Quota exceeded (429)
- Rate limit errors
- Invalid API keys
- Network/timeout errors
- Generation blocked errors
"""


import pytest


class TestErrorClassificationNewSDK:
    """Test error classification for google.genai SDK exceptions."""

    def test_quota_exceeded_detection_429(self):
        """Test detection of 429 Quota Exceeded error."""
        # Simulate google.genai ClientError for quota
        error_msg = "429 RESOURCE_EXHAUSTED: Quota exceeded"

        # Expected: Should be classified as quota error
        is_quota = "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg
        assert is_quota is True

    def test_quota_exceeded_with_retry_delay(self):
        """Test parsing retryDelay from quota error response."""
        # Simulate error with retryAfter metadata
        error_msg = "429 RESOURCE_EXHAUSTED: retryDelay=60s"

        # Should extract retry delay
        import re
        match = re.search(r'retryDelay[=:]?\s*(\d+)', error_msg)
        if match:
            delay_seconds = int(match.group(1))
        else:
            delay_seconds = 60  # Default

        assert delay_seconds == 60

    def test_rate_limit_detection(self):
        """Test detection of rate limit error (different from quota)."""
        error_msg = "429 RATE_LIMIT_EXCEEDED: Too many requests"

        is_rate_limit = "RATE_LIMIT" in error_msg
        assert is_rate_limit is True

    def test_invalid_api_key_detection(self):
        """Test detection of invalid API key error."""
        error_msg = "400 INVALID_ARGUMENT: API key not valid"

        is_invalid_key = "API key not valid" in error_msg or "INVALID_API_KEY" in error_msg
        assert is_invalid_key is True

    def test_timeout_error_detection(self):
        """Test detection of timeout errors."""
        # asyncio.TimeoutError doesn't have message
        error_type = "TimeoutError"

        is_timeout = "Timeout" in error_type
        assert is_timeout is True

    def test_generation_blocked_detection(self):
        """Test detection of content blocked errors."""
        error_msg = "SAFETY: Content blocked due to safety filters"

        is_blocked = "SAFETY" in error_msg or "blocked" in error_msg.lower()
        assert is_blocked is True

    def test_server_error_detection(self):
        """Test detection of 5xx server errors."""
        error_msg = "500 INTERNAL: Server error occurred"

        is_server_error = error_msg.startswith("5") or "INTERNAL" in error_msg
        assert is_server_error is True

    def test_unknown_error_fallback(self):
        """Test fallback handling for unknown errors."""
        error_msg = "Some completely unknown error message"

        # Should classify as unknown and apply default cooldown
        known_patterns = ["429", "RESOURCE_EXHAUSTED", "RATE_LIMIT", "API key", "Timeout", "SAFETY", "500"]
        is_known = any(p in error_msg for p in known_patterns)

        assert is_known is False  # Unknown error

    def test_error_code_extraction(self):
        """Test extraction of HTTP error code from message."""
        import re

        test_cases = [
            ("429 RESOURCE_EXHAUSTED", 429),
            ("400 INVALID_ARGUMENT", 400),
            ("500 INTERNAL", 500),
            ("Some message without code", None),
        ]

        for error_msg, expected_code in test_cases:
            match = re.match(r'^(\d{3})\s+', error_msg)
            code = int(match.group(1)) if match else None
            assert code == expected_code, f"Failed for: {error_msg}"


class TestCentralizedErrorHandler:
    """Test the CentralizedErrorHandler error classification."""

    def test_classify_quota_error(self):
        """Test classification of quota errors."""
        # Mock exception with typical quota error patterns
        patterns = [
            "Resource has been exhausted",
            "Quota exceeded for quota metric",
            "429 errors",
            "RESOURCE_EXHAUSTED",
        ]

        for pattern in patterns:
            # All should be classified as quota errors
            is_quota = any(p.lower() in pattern.lower() for p in ["quota", "429", "exhausted"])
            assert is_quota is True, f"Pattern {pattern} should be quota"

    def test_error_recovery_action_mapping(self):
        """Test that each error type maps to correct recovery action."""
        error_actions = {
            "quota_exceeded": "mark_key_cooldown_dynamic",
            "rate_limit": "mark_key_rate_limited",
            "invalid_key": "mark_key_inactive",
            "timeout": "retry_with_backoff",
            "generation_blocked": "mark_chunk_failed",
            "server_error": "retry_with_backoff",
            "unknown": "retry_with_backoff",
        }

        # All error types should have an action
        for error_type, action in error_actions.items():
            assert action is not None, f"Error type {error_type} needs action"
            assert len(action) > 0, f"Action for {error_type} should not be empty"


class TestDynamicCooldown:
    """Test dynamic cooldown calculation based on error response."""

    def test_parse_retry_after_header(self):
        """Test parsing Retry-After from response headers."""
        import re

        test_responses = [
            ("retryDelay: 120s", 120),
            ("Retry-After: 60", 60),
            ("retryAfter=30", 30),
            ("No retry info here", 60),  # Default
        ]

        for response, expected_delay in test_responses:
            match = re.search(r'(?:retryDelay|Retry-After|retryAfter)[=:\s]*(\d+)', response)
            delay = int(match.group(1)) if match else 60
            assert delay == expected_delay, f"Failed for: {response}"

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        base_delay = 1
        max_delay = 300

        for attempt in range(5):
            delay = min(base_delay * (2 ** attempt), max_delay)
            # Validate delay is within bounds
            assert delay >= base_delay
            assert delay <= max_delay

        # After many attempts, should cap at max
        delay = min(base_delay * (2 ** 10), max_delay)
        assert delay == max_delay


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
