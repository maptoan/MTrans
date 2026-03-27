# -*- coding: utf-8 -*-

"""
Metrics Collector
=================
Lightweight metrics collection để monitor system health.

PHIÊN BẢN: v2.0+
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("NovelTranslator")


@dataclass
class ChunkMetrics:
    """Metrics cho một chunk."""

    chunk_id: int
    status: str  # 'success' or 'failed'
    duration: float  # seconds
    model_used: Optional[str] = None
    error_type: Optional[str] = None
    prompt_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class APIKeyMetrics:
    """Metrics cho một API key."""

    key: str
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    error_types: Dict[str, int] = field(default_factory=dict)
    last_used: Optional[float] = None


@dataclass
class FlushMetrics:
    """Metrics cho flush operations."""

    flush_count: int = 0
    total_chunks_flushed: int = 0
    total_flush_duration: float = 0.0
    error_count: int = 0
    last_flush_time: Optional[float] = None


class MetricsCollector:
    """
    Lightweight metrics collector để monitor system health.

    Features:
    - Success rate per chunk
    - Average time per chunk
    - API key usage statistics
    - Error rate by type
    - Flush operation metrics
    - Periodic export to file

    Attributes:
        chunk_metrics: List of ChunkMetrics
        api_key_metrics: Dict[key, APIKeyMetrics]
        flush_metrics: FlushMetrics
        max_history: Max number of metrics to keep in memory
        export_interval: Interval to export metrics (seconds)
        export_path: Path to export metrics file
        last_export_time: Last export time
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo MetricsCollector.

        Args:
            config: Configuration dict với metrics settings
        """
        self.config = config or {}
        metrics_config = self.config.get("metrics", {})

        self.enabled = metrics_config.get("enabled", True)
        self.max_history = metrics_config.get(
            "max_history", 1000
        )  # max_history is still relevant for the dict size if we want to limit it.

        # Aggregated stats
        self.total_tokens = 0
        self.total_cached_tokens = 0

        if metrics_config.get("auto_export", True):
            self.auto_export = True
            self.export_interval = metrics_config.get(
                "export_interval", 300
            )  # 5 minutes
        else:
            self.auto_export = False
            self.export_interval = float(
                "inf"
            )  # Effectively disable interval-based auto-export

        self.export_path = Path(metrics_config.get("export_path", "data/metrics.json"))

        # Metrics storage
        # Changed from deque to dict to allow updating existing chunk metrics by ID
        self.chunk_metrics: Dict[int, ChunkMetrics] = {}
        self.api_key_metrics: Dict[str, APIKeyMetrics] = {}
        self.flush_metrics = FlushMetrics()

        # Export tracking
        self.last_export_time = time.time()

        # Ensure export directory exists
        if self.export_path:
            self.export_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"MetricsCollector initialized: enabled={self.enabled}, "
            f"max_history={self.max_history}, export_interval={self.export_interval}s"
        )

    def _check_auto_export(self) -> None:
        """Checks if auto-export is enabled and if it's time to export."""
        if self.auto_export and (
            time.time() - self.last_export_time >= self.export_interval
        ):
            self.export_metrics()

    def record_chunk_translation(
        self,
        chunk_id: int,
        status: str,
        duration: float,
        model_used: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record metrics cho chunk translation.

        Args:
            chunk_id: Chunk ID
            status: 'success' or 'failed'
            duration: Translation duration (seconds)
            model_used: Optional model name
            error_type: Optional error type nếu failed
        """
        if not self.enabled:
            return

        # If chunk already exists (e.g., token usage recorded first), update it
        if chunk_id in self.chunk_metrics:
            metric = self.chunk_metrics[chunk_id]
            metric.status = status
            metric.duration = duration
            if model_used:
                metric.model_used = model_used
            metric.error_type = error_type
            metric.timestamp = time.time()
        else:
            metric = ChunkMetrics(
                chunk_id=chunk_id,
                status=status,
                duration=duration,
                model_used=model_used,
                error_type=error_type,
            )
            self.chunk_metrics[chunk_id] = metric

        # Limit the size of chunk_metrics if it grows too large
        if len(self.chunk_metrics) > self.max_history:
            # Remove the oldest entry (smallest chunk_id if IDs are sequential)
            # This assumes chunk_id increases over time.
            oldest_chunk_id = min(self.chunk_metrics.keys())
            del self.chunk_metrics[oldest_chunk_id]

        self._check_auto_export()

    def record_token_usage(
        self,
        chunk_id: int,
        prompt_tokens: int,
        cached_tokens: int,
        total_tokens: int,
        model_name: Optional[str] = None,
    ) -> None:
        """Record token usage for a chunk."""
        if not self.enabled:
            return

        if chunk_id in self.chunk_metrics:
            metrics = self.chunk_metrics[chunk_id]
            metrics.prompt_tokens = prompt_tokens
            metrics.cached_tokens = cached_tokens
            metrics.total_tokens = total_tokens
            if model_name:
                metrics.model_used = model_name
        else:
            # Create new if doesn't exist (though usually it should be created by record_chunk_translation)
            metrics = ChunkMetrics(
                chunk_id=chunk_id,
                status="unknown",  # Status is unknown until translation completes
                duration=0.0,
                model_used=model_name,
                prompt_tokens=prompt_tokens,
                cached_tokens=cached_tokens,
                total_tokens=total_tokens,
            )
            self.chunk_metrics[chunk_id] = metrics

        # Update aggregate
        self.total_tokens += total_tokens
        self.total_cached_tokens += cached_tokens
        self._check_auto_export()

    def record_api_key_usage(
        self, key: str, success: bool, duration: float, error_type: Optional[str] = None
    ) -> None:
        """
        Record metrics cho API key usage.

        Args:
            key: API key identifier
            success: True nếu success, False nếu failed
            duration: Request duration (seconds)
            error_type: Optional error type nếu failed
        """
        if not self.enabled:
            return

        if key not in self.api_key_metrics:
            self.api_key_metrics[key] = APIKeyMetrics(key=key)

        metrics = self.api_key_metrics[key]
        metrics.request_count += 1
        metrics.total_duration += duration
        metrics.last_used = time.time()

        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
            if error_type:
                metrics.error_types[error_type] = (
                    metrics.error_types.get(error_type, 0) + 1
                )

    def record_flush(
        self, chunks_flushed: int, duration: float, success: bool = True
    ) -> None:
        """
        Record metrics cho flush operation.

        Args:
            chunks_flushed: Number of chunks flushed
            duration: Flush duration (seconds)
            success: True nếu success, False nếu failed
        """
        if not self.enabled:
            return

        self.flush_metrics.flush_count += 1
        self.flush_metrics.total_chunks_flushed += chunks_flushed
        self.flush_metrics.total_flush_duration += duration
        self.flush_metrics.last_flush_time = time.time()

        if not success:
            self.flush_metrics.error_count += 1

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Returns:
            Dict với aggregated statistics
        """
        if not self.enabled or not self.chunk_metrics:
            return {
                "enabled": self.enabled,
                "chunk_count": 0,
            }

        # Chunk statistics
        chunk_list = list(self.chunk_metrics.values())
        success_count = sum(1 for m in chunk_list if m.status == "success")
        failed_count = sum(1 for m in chunk_list if m.status == "failed")
        total_duration = sum(m.duration for m in chunk_list)
        avg_duration = total_duration / len(chunk_list) if chunk_list else 0

        # Token Statistics
        total_p_tokens = sum(m.prompt_tokens for m in chunk_list)
        total_c_tokens = sum(m.cached_tokens for m in chunk_list)
        total_t_tokens = sum(m.total_tokens for m in chunk_list)
        avg_cached_pct = (
            (total_c_tokens / total_p_tokens * 100) if total_p_tokens > 0 else 0
        )

        # Error type distribution
        error_types = defaultdict(int)
        for m in chunk_list:
            if m.error_type:
                error_types[m.error_type] += 1

        # Model usage
        model_usage = defaultdict(int)
        for m in chunk_list:
            if m.model_used:
                model_usage[m.model_used] += 1

        # API key statistics
        api_key_stats = {}
        for key, metrics in self.api_key_metrics.items():
            key_prefix = key[:10] + "..."
            api_key_stats[key_prefix] = {
                "request_count": metrics.request_count,
                "success_count": metrics.success_count,
                "failure_count": metrics.failure_count,
                "success_rate": (
                    metrics.success_count / metrics.request_count
                    if metrics.request_count > 0
                    else 0
                ),
                "avg_duration": (
                    metrics.total_duration / metrics.request_count
                    if metrics.request_count > 0
                    else 0
                ),
                "error_types": dict(metrics.error_types),
            }

        # Flush statistics
        flush_stats = {
            "flush_count": self.flush_metrics.flush_count,
            "total_chunks_flushed": self.flush_metrics.total_chunks_flushed,
            "avg_flush_duration": (
                self.flush_metrics.total_flush_duration / self.flush_metrics.flush_count
                if self.flush_metrics.flush_count > 0
                else 0
            ),
            "error_count": self.flush_metrics.error_count,
            "last_flush_time": (
                datetime.fromtimestamp(self.flush_metrics.last_flush_time).isoformat()
                if self.flush_metrics.last_flush_time
                else None
            ),
        }

        return {
            "enabled": self.enabled,
            "chunk_count": len(chunk_list),
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": success_count / len(chunk_list) if chunk_list else 0,
            "avg_duration": avg_duration,
            "min_duration": min((m.duration for m in chunk_list), default=0),
            "max_duration": max((m.duration for m in chunk_list), default=0),
            "error_types": dict(error_types),
            "model_usage": dict(model_usage),
            "token_statistics": {
                "total_prompt_tokens": total_p_tokens,
                "total_cached_tokens": total_c_tokens,
                "total_actual_tokens": total_t_tokens,
                "cache_hit_rate_pct": round(avg_cached_pct, 2),
            },
            "api_key_statistics": api_key_stats,
            "flush_statistics": flush_stats,
            "last_export_time": (
                datetime.fromtimestamp(self.last_export_time).isoformat()
            ),
        }

    def export_metrics(self, force: bool = False) -> bool:
        """
        Export metrics to file.

        Args:
            force: Force export even if interval not reached

        Returns:
            True nếu export thành công, False nếu fail
        """
        if not self.enabled:
            return False

        if not force and time.time() - self.last_export_time < self.export_interval:
            return False

        try:
            stats = self.get_statistics()

            # Convert to JSON-serializable format
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "statistics": stats,
            }

            # Write to file
            with open(self.export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.last_export_time = time.time()

            logger.debug(f"Metrics exported to {self.export_path}")
            return True

        except (IOError, OSError, json.JSONEncodeError) as e:
            logger.error(f"Error exporting metrics: {e}", exc_info=True)
            return False

    def reset(self) -> None:
        """
        Reset all metrics.

        Returns:
            None
        """
        self.chunk_metrics.clear()
        self.api_key_metrics.clear()
        self.flush_metrics = FlushMetrics()
        self.last_export_time = time.time()
        logger.debug("Metrics reset")
