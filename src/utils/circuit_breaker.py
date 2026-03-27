# -*- coding: utf-8 -*-

"""
Circuit Breaker Pattern
=======================
Circuit breaker pattern để tránh waste resources khi key fail nhiều lần.

PHIÊN BẢN: v2.0+
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("NovelTranslator")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics cho circuit breaker."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    state_changed_at: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Circuit breaker pattern để tránh waste resources khi key fail nhiều lần.

    Features:
    - Key-specific circuit breaker
    - Configurable threshold và cooldown
    - Auto-recovery mechanism
    - State tracking (CLOSED, OPEN, HALF_OPEN)

    Attributes:
        key: API key identifier
        failure_threshold: Number of failures before opening circuit
        cooldown_period: Cooldown period in seconds
        half_open_max_attempts: Max attempts in HALF_OPEN state
        stats: CircuitBreakerStats với statistics
    """

    def __init__(self, key: str, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo CircuitBreaker cho một key.

        Args:
            key: API key identifier
            config: Optional configuration dict
        """
        self.key = key
        self.config = config or {}

        # Configuration
        self.failure_threshold = self.config.get("failure_threshold", 5)
        self.cooldown_period = self.config.get("cooldown_period", 300)  # 5 minutes
        self.half_open_max_attempts = self.config.get("half_open_max_attempts", 3)

        # Statistics
        self.stats = CircuitBreakerStats()

        logger.debug(
            f"CircuitBreaker initialized for key {key[:10]}...: "
            f"threshold={self.failure_threshold}, cooldown={self.cooldown_period}s"
        )

    def can_execute(self) -> bool:
        """
        Check nếu có thể execute request.

        Returns:
            True nếu có thể execute, False nếu circuit is open
        """
        # Check state transitions
        self._update_state()

        if self.stats.state == CircuitState.CLOSED:
            return True

        elif self.stats.state == CircuitState.OPEN:
            # Check nếu cooldown period đã qua
            if time.time() - self.stats.state_changed_at >= self.cooldown_period:
                # Transition to HALF_OPEN
                self.stats.state = CircuitState.HALF_OPEN
                self.stats.state_changed_at = time.time()
                self.stats.failure_count = 0  # Reset failure count
                logger.info(
                    f"Circuit breaker for key {self.key[:10]}... "
                    f"transitioned to HALF_OPEN (cooldown expired)"
                )
                return True
            return False

        elif self.stats.state == CircuitState.HALF_OPEN:
            # Allow limited attempts in HALF_OPEN
            return True

        return False

    def record_success(self) -> None:
        """
        Record successful request.

        Returns:
            None
        """
        self.stats.success_count += 1
        self.stats.last_success_time = time.time()

        # If in HALF_OPEN and have enough successes, close circuit
        if self.stats.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.half_open_max_attempts:
                self.stats.state = CircuitState.CLOSED
                self.stats.state_changed_at = time.time()
                self.stats.failure_count = 0  # Reset failure count
                logger.info(
                    f"Circuit breaker for key {self.key[:10]}... "
                    f"closed (recovered with {self.stats.success_count} successes)"
                )

        # Reset failure count on success (if in CLOSED state)
        elif self.stats.state == CircuitState.CLOSED:
            if self.stats.failure_count > 0:
                self.stats.failure_count = 0

    def record_failure(self) -> None:
        """
        Record failed request.

        Returns:
            None
        """
        self.stats.failure_count += 1
        self.stats.last_failure_time = time.time()

        # Check nếu cần open circuit
        if self.stats.state == CircuitState.CLOSED:
            if self.stats.failure_count >= self.failure_threshold:
                self.stats.state = CircuitState.OPEN
                self.stats.state_changed_at = time.time()
                logger.warning(
                    f"Circuit breaker for key {self.key[:10]}... "
                    f"opened ({self.stats.failure_count} failures >= {self.failure_threshold})"
                )

        # If in HALF_OPEN and fail, open circuit again
        elif self.stats.state == CircuitState.HALF_OPEN:
            self.stats.state = CircuitState.OPEN
            self.stats.state_changed_at = time.time()
            logger.warning(
                f"Circuit breaker for key {self.key[:10]}... "
                f"opened again (failed in HALF_OPEN state)"
            )

    def _update_state(self) -> None:
        """
        Update circuit breaker state based on time và conditions.

        Returns:
            None
        """
        # Auto-transition từ OPEN to HALF_OPEN sau cooldown
        if self.stats.state == CircuitState.OPEN:
            if time.time() - self.stats.state_changed_at >= self.cooldown_period:
                self.stats.state = CircuitState.HALF_OPEN
                self.stats.state_changed_at = time.time()
                self.stats.failure_count = 0  # Reset failure count
                logger.info(
                    f"Circuit breaker for key {self.key[:10]}... "
                    f"transitioned to HALF_OPEN (cooldown expired)"
                )

    def get_state(self) -> CircuitState:
        """
        Get current circuit breaker state.

        Returns:
            CircuitState enum
        """
        self._update_state()
        return self.stats.state

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dict với statistics
        """
        self._update_state()

        return {
            "key": self.key[:10] + "...",
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_period": self.cooldown_period,
            "last_failure_time": (
                datetime.fromtimestamp(self.stats.last_failure_time).isoformat()
                if self.stats.last_failure_time
                else None
            ),
            "last_success_time": (
                datetime.fromtimestamp(self.stats.last_success_time).isoformat()
                if self.stats.last_success_time
                else None
            ),
            "state_changed_at": (
                datetime.fromtimestamp(self.stats.state_changed_at).isoformat()
            ),
            "time_until_cooldown": (
                max(
                    0,
                    self.cooldown_period - (time.time() - self.stats.state_changed_at),
                )
                if self.stats.state == CircuitState.OPEN
                else None
            ),
        }

    def reset(self) -> None:
        """
        Reset circuit breaker to initial state.

        Returns:
            None
        """
        self.stats = CircuitBreakerStats()
        logger.debug(f"Circuit breaker for key {self.key[:10]}... reset")


class CircuitBreakerManager:
    """
    Manager để quản lý multiple circuit breakers (one per API key).

    Features:
    - Per-key circuit breakers
    - Centralized management
    - Statistics aggregation

    Attributes:
        breakers: Dict[key, CircuitBreaker] - Circuit breakers per key
        config: Configuration dict
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo CircuitBreakerManager.

        Args:
            config: Configuration dict
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

        # Per-key circuit breakers
        self.breakers: Dict[str, CircuitBreaker] = {}

        logger.debug(f"CircuitBreakerManager initialized: enabled={self.enabled}")

    def get_breaker(self, key: str) -> CircuitBreaker:
        """
        Get or create circuit breaker cho key.

        Args:
            key: API key identifier

        Returns:
            CircuitBreaker instance
        """
        if not self.enabled:
            # Return dummy breaker that always allows execution
            return CircuitBreaker(
                key, {"failure_threshold": 999999, "cooldown_period": 0}
            )

        if key not in self.breakers:
            self.breakers[key] = CircuitBreaker(key, self.config)

        return self.breakers[key]

    def can_execute(self, key: str) -> bool:
        """
        Check nếu có thể execute request với key.

        Args:
            key: API key identifier

        Returns:
            True nếu có thể execute, False nếu circuit is open
        """
        if not self.enabled:
            return True

        breaker = self.get_breaker(key)
        return breaker.can_execute()

    def record_success(self, key: str) -> None:
        """
        Record successful request cho key.

        Args:
            key: API key identifier

        Returns:
            None
        """
        if not self.enabled:
            return

        breaker = self.get_breaker(key)
        breaker.record_success()

    def record_failure(self, key: str) -> None:
        """
        Record failed request cho key.

        Args:
            key: API key identifier

        Returns:
            None
        """
        if not self.enabled:
            return

        breaker = self.get_breaker(key)
        breaker.record_failure()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated statistics cho all circuit breakers.

        Returns:
            Dict với aggregated statistics
        """
        if not self.enabled:
            return {"enabled": False}

        stats_list = [breaker.get_statistics() for breaker in self.breakers.values()]

        # Count by state
        state_counts = {}
        for state in CircuitState:
            state_counts[state.value] = sum(
                1 for s in stats_list if s["state"] == state.value
            )

        return {
            "enabled": True,
            "total_breakers": len(self.breakers),
            "state_counts": state_counts,
            "breakers": stats_list,
        }

    def reset_all(self) -> None:
        """
        Reset all circuit breakers.

        Returns:
            None
        """
        for breaker in self.breakers.values():
            breaker.reset()
        logger.debug("All circuit breakers reset")
