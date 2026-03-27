from __future__ import annotations

import pytest

from src.utils.error_classifier import classify_error


class TestErrorClassifier:
    """Kiểm thử phân loại lỗi API thành error_type nội bộ."""

    def _make_exc(self, message: str, name: str = "ClientError") -> Exception:
        class _E(Exception):
            pass

        _E.__name__ = name
        return _E(message)

    def test_quota_exceeded_detection(self) -> None:
        exc = self._make_exc("429 RESOURCE_EXHAUSTED: Quota exceeded for project")
        assert classify_error(exc) == "quota_exceeded"

        exc2 = self._make_exc("Quota exceeded for quota metric 'tokens_per_day'")
        assert classify_error(exc2) == "quota_exceeded"

    def test_rate_limit_detection(self) -> None:
        exc = self._make_exc("429 RATE_LIMIT_EXCEEDED: Too many requests")
        assert classify_error(exc) == "rate_limit"

        exc2 = self._make_exc("Too many requests in a short period, rate_limit triggered")
        assert classify_error(exc2) == "rate_limit"

    def test_invalid_api_key_detection(self) -> None:
        exc = self._make_exc("400 INVALID_ARGUMENT: API key not valid")
        assert classify_error(exc) == "invalid_key"

        exc2 = self._make_exc("API key not valid or expired")
        assert classify_error(exc2) == "invalid_key"

        exc3 = self._make_exc("403 PERMISSION_DENIED: invalid API key")
        assert classify_error(exc3) == "invalid_key"

    def test_timeout_detection(self) -> None:
        exc = self._make_exc("Deadline exceeded after 10s", name="TimeoutError")
        assert classify_error(exc) == "timeout"

        exc2 = self._make_exc("Request timeout while calling model")
        assert classify_error(exc2) == "timeout"

    def test_generation_blocked_detection(self) -> None:
        exc = self._make_exc("SAFETY: Content blocked due to safety filters")
        assert classify_error(exc) == "generation_blocked"

        exc2 = self._make_exc("Output was blocked by safety policies")
        assert classify_error(exc2) == "generation_blocked"

    def test_server_error_detection(self) -> None:
        exc = self._make_exc("500 INTERNAL: Server error occurred")
        assert classify_error(exc) == "server_error"

        exc2 = self._make_exc("INTERNAL: server error occurred while processing request")
        assert classify_error(exc2) == "server_error"

    def test_unknown_error_fallback(self) -> None:
        exc = self._make_exc("Some completely unknown error message")
        assert classify_error(exc) == "unknown"

