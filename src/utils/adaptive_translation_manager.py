"""
Integration của Adaptive Worker Manager vào NovelTranslator.

Module này cung cấp adaptive worker management cho translation process,
tự động điều chỉnh số lượng workers dựa trên performance metrics.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from .adaptive_worker_manager import AdaptiveWorkerManager, PerformanceTracker

T = TypeVar("T")

logger = logging.getLogger("NovelTranslator")


class AdaptiveTranslationManager:
    """
    Quản lý dịch thuật với adaptive workers.

    Tự động điều chỉnh số lượng workers dựa trên:
    - Performance metrics (response time, success rate)
    - Queue length (số chunks đang chờ)
    - Rate limit incidents
    - Available API keys
    """

    def __init__(self, translator_instance: Any) -> None:
        """
        Khởi tạo Adaptive Translation Manager.

        Args:
            translator_instance: Instance của NovelTranslator để truy cập config và API keys
        """
        self.translator = translator_instance
        self.worker_manager = AdaptiveWorkerManager(
            min_workers=1,
            max_workers=20,
            adjustment_interval=30,  # Điều chỉnh mỗi 30 giây
            metrics_window=10,
        )
        self.performance_tracker = PerformanceTracker()
        self.is_monitoring: bool = False
        self.monitoring_task: Optional[asyncio.Task] = None

    async def start_adaptive_monitoring(self) -> None:
        """
        Bắt đầu monitoring và điều chỉnh workers tự động.
        """
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🚀 Bắt đầu Adaptive Worker Monitoring")

    async def stop_adaptive_monitoring(self) -> None:
        """
        Dừng monitoring và cancel background task.
        """
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Dừng Adaptive Worker Monitoring")

    async def _monitoring_loop(self) -> None:
        """
        Vòng lặp monitoring chính chạy trong background.
        """
        while self.is_monitoring:
            try:
                await self._collect_and_adjust()
                await asyncio.sleep(10)  # Kiểm tra mỗi 10 giây
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lỗi trong monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _collect_and_adjust(self) -> None:
        """
        Thu thập metrics và điều chỉnh số workers.
        """
        # Lấy số API keys hiện tại
        available_keys = len(self.translator.valid_api_keys)

        # Lấy queue length (số chunks đang chờ)
        queue_length = len(getattr(self.translator, "pending_chunks", []))

        # Tạo metrics từ performance tracker
        metrics = self.performance_tracker.get_metrics(queue_length)
        metrics.active_workers = self.worker_manager.get_current_workers()

        # Thêm vào worker manager
        self.worker_manager.add_metrics(metrics)

        # Tính toán workers mới
        new_workers = self.worker_manager.calculate_adjustment(available_keys)

        # Cập nhật số workers trong translator
        if new_workers != self.translator.config["performance"]["max_parallel_workers"]:
            self.translator.config["performance"]["max_parallel_workers"] = new_workers
            logger.info(
                f"🔄 Adaptive Workers: Cập nhật max_parallel_workers = {new_workers}"
            )

    def record_translation_request(
        self, response_time: float, success: bool, is_rate_limit: bool = False
    ) -> None:
        self.performance_tracker.record_request(response_time, success, is_rate_limit)

    def get_adaptive_status(self) -> Dict[str, Any]:
        total_requests = self.performance_tracker.total_requests
        return {
            "is_monitoring": self.is_monitoring,
            "worker_manager_status": self.worker_manager.get_status_report(),
            "performance_tracker": {
                "total_requests": total_requests,
                "success_rate": (
                    self.performance_tracker.success_count / max(1, total_requests)
                ),
                "rate_limit_rate": (
                    self.performance_tracker.rate_limit_count / max(1, total_requests)
                ),
            },
        }

    def reset_adaptive_system(self) -> None:
        self.worker_manager.reset()
        self.performance_tracker.reset()
        logger.info("🔄 Reset Adaptive Worker System")


# Decorator để track performance của translation methods
def track_translation_performance(
    adaptive_manager: AdaptiveTranslationManager,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            success = False
            is_rate_limit = False

            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                # Kiểm tra xem có phải rate limit không
                if "429" in str(e) or "rate limit" in str(e).lower():
                    is_rate_limit = True
                raise
            finally:
                response_time = time.time() - start_time
                adaptive_manager.record_translation_request(
                    response_time, success, is_rate_limit
                )

        return wrapper

    return decorator
