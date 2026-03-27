# -*- coding: utf-8 -*-

"""
Adaptive Timeout Calculator
============================
Calculate adaptive timeout dựa trên chunk size và historical response times.

PHIÊN BẢN: v2.0+
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("NovelTranslator")


@dataclass
class TimeoutHistory:
    """History của response times để tính adaptive timeout."""

    chunk_sizes: deque = field(default_factory=lambda: deque(maxlen=100))
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    last_updated: float = field(default_factory=time.time)


class AdaptiveTimeoutCalculator:
    """
    Calculate adaptive timeout dựa trên chunk size và historical data.

    Features:
    - Calculate timeout based on chunk size
    - Adjust based on historical response times
    - Max timeout limit
    - Exponential smoothing cho historical data

    Attributes:
        base_timeout: Base timeout (seconds)
        max_timeout: Maximum timeout (seconds)
        min_timeout: Minimum timeout (seconds)
        size_factor: Factor để tính timeout từ chunk size
        history: TimeoutHistory với historical data
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo AdaptiveTimeoutCalculator.

        Args:
            config: Configuration dict với timeout settings
        """
        self.config = config or {}
        timeout_config = self.config.get("timeout", {})

        self.enabled = timeout_config.get("enabled", True)
        self.base_timeout = timeout_config.get(
            "base_timeout", 60
        )  # 60 seconds (increased from 30)
        self.max_timeout = timeout_config.get(
            "max_timeout", 300
        )  # 5 minutes (increased from 2)
        self.min_timeout = timeout_config.get(
            "min_timeout", 30
        )  # 30 seconds (increased from 10)
        self.size_factor = timeout_config.get("size_factor", 0.1)  # 0.1s per 1000 chars
        self.history_weight = timeout_config.get(
            "history_weight", 0.3
        )  # Weight cho historical data

        # Historical data
        self.history = TimeoutHistory()

        logger.debug(
            f"AdaptiveTimeoutCalculator initialized: "
            f"base={self.base_timeout}s, max={self.max_timeout}s, "
            f"min={self.min_timeout}s"
        )

    def calculate_timeout(self, chunk_size: int, model: Optional[str] = None) -> float:
        """
        Calculate timeout dựa trên chunk size và historical data.

        Args:
            chunk_size: Size của chunk (characters hoặc tokens)
            model: Optional model name (flash/pro)

        Returns:
            Timeout in seconds (float)
        """
        if not self.enabled:
            return self.base_timeout

        # Base timeout từ chunk size
        size_based_timeout = self.base_timeout + (chunk_size / 1000) * self.size_factor

        # Adjust based on historical data
        historical_adjustment = self._calculate_historical_adjustment()

        # Combine với weighted average
        calculated_timeout = (
            size_based_timeout * (1 - self.history_weight)
            + historical_adjustment * self.history_weight
        )

        # Clamp to min/max
        timeout = max(self.min_timeout, min(self.max_timeout, calculated_timeout))

        logger.debug(
            f"Calculated timeout: {timeout:.1f}s "
            f"(size={chunk_size}, size_based={size_based_timeout:.1f}s, "
            f"historical={historical_adjustment:.1f}s)"
        )

        return timeout

    def _calculate_historical_adjustment(self) -> float:
        """
        Calculate timeout adjustment từ historical data.

        Returns:
            Adjusted timeout based on history
        """
        if not self.history.response_times:
            return self.base_timeout

        # Calculate average response time
        avg_response_time = sum(self.history.response_times) / len(
            self.history.response_times
        )

        # Add buffer (50% of average)
        adjusted_timeout = avg_response_time * 1.5

        return adjusted_timeout

    def record_response_time(
        self, chunk_size: int, response_time: float, model: Optional[str] = None
    ) -> None:
        """
        Record response time để update historical data.

        Args:
            chunk_size: Size của chunk
            response_time: Actual response time (seconds)
            model: Optional model name
        """
        if not self.enabled:
            return

        # Add to history
        self.history.chunk_sizes.append(chunk_size)
        self.history.response_times.append(response_time)
        self.history.last_updated = time.time()

        logger.debug(
            f"Recorded response time: {response_time:.2f}s "
            f"for chunk size {chunk_size} (model: {model or 'unknown'})"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get timeout statistics.

        Returns:
            Dict với timeout statistics
        """
        if not self.history.response_times:
            return {
                "enabled": self.enabled,
                "base_timeout": self.base_timeout,
                "max_timeout": self.max_timeout,
                "min_timeout": self.min_timeout,
                "history_count": 0,
            }

        return {
            "enabled": self.enabled,
            "base_timeout": self.base_timeout,
            "max_timeout": self.max_timeout,
            "min_timeout": self.min_timeout,
            "history_count": len(self.history.response_times),
            "avg_response_time": sum(self.history.response_times)
            / len(self.history.response_times),
            "min_response_time": min(self.history.response_times),
            "max_response_time": max(self.history.response_times),
            "last_updated": self.history.last_updated,
        }

    def reset_history(self) -> None:
        """Reset historical data."""
        self.history = TimeoutHistory()
        logger.debug("Timeout history reset")
