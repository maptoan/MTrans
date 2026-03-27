"""
Adaptive Worker Manager - Thuật toán điều chỉnh workers chủ động.

Module này cung cấp adaptive worker management dựa trên:
- Số lượng API keys hiện có
- Performance metrics (success rate, response time, rate limit frequency)
- Queue length
- Historical performance data

Các chức năng chính:
- Tự động điều chỉnh số workers dựa trên performance
- Tracking và phân tích metrics
- Performance reporting
"""

import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceMetrics:
    """
    Metrics để đánh giá hiệu suất của translation workers.

    Attributes:
        success_rate: Tỷ lệ thành công (0.0-1.0)
        avg_response_time: Thời gian phản hồi trung bình (giây)
        rate_limit_frequency: Tần suất lỗi 429 (0.0-1.0)
        queue_length: Số chunks đang chờ xử lý
        active_workers: Số workers đang hoạt động
        timestamp: Thời điểm đo metrics (Unix timestamp)
    """

    success_rate: float
    avg_response_time: float
    rate_limit_frequency: float
    queue_length: int
    active_workers: int
    timestamp: float


class AdaptiveWorkerManager:
    """
    Quản lý workers thích ứng dựa trên performance metrics.

    Tự động điều chỉnh số lượng workers dựa trên:
    1. Số lượng API keys hiện tại
    2. Performance metrics (success rate, response time, rate limit)
    3. Queue length
    4. Historical performance data
    """

    def __init__(
        self,
        min_workers: int = 1,
        max_workers: int = 20,
        adjustment_interval: int = 30,  # Giây
        metrics_window: int = 10,  # Số metrics để tính trung bình
    ) -> None:
        """
        Khởi tạo Adaptive Worker Manager.

        Args:
            min_workers: Số workers tối thiểu
            max_workers: Số workers tối đa
            adjustment_interval: Khoảng thời gian giữa các lần điều chỉnh (giây)
            metrics_window: Số lượng metrics để tính trung bình
        """
        self.min_workers: int = min_workers
        self.max_workers: int = max_workers
        self.adjustment_interval: int = adjustment_interval
        self.metrics_window: int = metrics_window

        # Lịch sử metrics
        self.metrics_history: deque[PerformanceMetrics] = deque(maxlen=metrics_window)

        # Cấu hình thresholds
        self.thresholds: Dict[str, float] = {
            "success_rate_min": 0.95,  # Dưới 95% → giảm workers
            "success_rate_optimal": 0.98,  # Trên 98% → có thể tăng workers
            "response_time_max": 5.0,  # Trên 5s → giảm workers
            "response_time_optimal": 2.0,  # Dưới 2s → có thể tăng workers
            "rate_limit_max": 0.05,  # Trên 5% → giảm workers
            "rate_limit_optimal": 0.01,  # Dưới 1% → có thể tăng workers
        }

        # Trạng thái hiện tại
        self.current_workers: int = min_workers
        self.last_adjustment: float = time.time()
        self.adjustment_history: List[Dict[str, Any]] = []

        # Logger
        self.logger: logging.Logger = logging.getLogger(__name__)

    def calculate_optimal_workers(self, available_keys: int) -> int:
        """
        Tính toán số workers tối ưu dựa trên số API keys

        Args:
            available_keys: Số API keys có sẵn

        Returns:
            Số workers được đề xuất
        """
        if available_keys <= 0:
            return self.min_workers

        # Công thức cơ bản: sử dụng 60-80% keys
        base_workers = int(available_keys * 0.7)  # 70% làm điểm khởi đầu

        # Điều chỉnh theo giới hạn hệ thống
        optimal_workers = min(base_workers, self.max_workers)
        optimal_workers = max(optimal_workers, self.min_workers)

        return optimal_workers

    def add_metrics(self, metrics: PerformanceMetrics) -> None:
        """
        Thêm metrics mới vào lịch sử.

        Args:
            metrics: PerformanceMetrics object chứa metrics mới

        Returns:
            None
        """
        self.metrics_history.append(metrics)

    def get_average_metrics(self) -> Optional[PerformanceMetrics]:
        """Tính toán metrics trung bình từ lịch sử"""
        if len(self.metrics_history) < 3:  # Cần ít nhất 3 điểm dữ liệu
            return None

        success_rates = [m.success_rate for m in self.metrics_history]
        response_times = [m.avg_response_time for m in self.metrics_history]
        rate_limits = [m.rate_limit_frequency for m in self.metrics_history]
        queue_lengths = [m.queue_length for m in self.metrics_history]

        return PerformanceMetrics(
            success_rate=statistics.mean(success_rates),
            avg_response_time=statistics.mean(response_times),
            rate_limit_frequency=statistics.mean(rate_limits),
            queue_length=statistics.mean(queue_lengths),
            active_workers=self.current_workers,
            timestamp=time.time(),
        )

    def analyze_performance(self, avg_metrics: PerformanceMetrics) -> Dict[str, str]:
        """
        Phân tích hiệu suất và đưa ra khuyến nghị điều chỉnh workers.

        Phân tích dựa trên:
        - Success rate
        - Response time
        - Rate limit frequency
        - Queue length

        Args:
            avg_metrics: PerformanceMetrics chứa metrics trung bình

        Returns:
            Dictionary chứa:
                - 'action': 'maintain', 'increase', hoặc 'decrease'
                - 'reason': Lý do cho action
                - 'confidence': 'low', 'medium', hoặc 'high'
        """
        analysis = {
            "action": "maintain",  # maintain, increase, decrease
            "reason": "",
            "confidence": "medium",
        }

        # Kiểm tra các điều kiện để giảm workers
        if (
            avg_metrics.success_rate < self.thresholds["success_rate_min"]
            or avg_metrics.avg_response_time > self.thresholds["response_time_max"]
            or avg_metrics.rate_limit_frequency > self.thresholds["rate_limit_max"]
        ):
            analysis["action"] = "decrease"
            reasons = []

            if avg_metrics.success_rate < self.thresholds["success_rate_min"]:
                reasons.append(f"Success rate thấp ({avg_metrics.success_rate:.2%})")
            if avg_metrics.avg_response_time > self.thresholds["response_time_max"]:
                reasons.append(
                    f"Response time cao ({avg_metrics.avg_response_time:.1f}s)"
                )
            if avg_metrics.rate_limit_frequency > self.thresholds["rate_limit_max"]:
                reasons.append(
                    f"Rate limit nhiều ({avg_metrics.rate_limit_frequency:.2%})"
                )

            analysis["reason"] = "; ".join(reasons)
            analysis["confidence"] = "high"

        # Kiểm tra các điều kiện để tăng workers
        elif (
            avg_metrics.success_rate > self.thresholds["success_rate_optimal"]
            and avg_metrics.avg_response_time < self.thresholds["response_time_optimal"]
            and avg_metrics.rate_limit_frequency < self.thresholds["rate_limit_optimal"]
            and avg_metrics.queue_length > self.current_workers * 2
        ):  # Queue dài
            analysis["action"] = "increase"
            analysis["reason"] = (
                f"Hiệu suất tốt (success: {avg_metrics.success_rate:.2%}, "
                f"response: {avg_metrics.avg_response_time:.1f}s, "
                f"rate_limit: {avg_metrics.rate_limit_frequency:.2%}) và queue dài ({avg_metrics.queue_length})"
            )
            analysis["confidence"] = "medium"

        else:
            analysis["action"] = "maintain"
            analysis["reason"] = (
                f"Hiệu suất ổn định (success: {avg_metrics.success_rate:.2%}, "
                f"response: {avg_metrics.avg_response_time:.1f}s)"
            )
            analysis["confidence"] = "low"

        return analysis

    def calculate_adjustment(self, available_keys: int) -> int:
        """
        Tính toán điều chỉnh số workers

        Args:
            available_keys: Số API keys có sẵn

        Returns:
            Số workers mới được đề xuất
        """
        # Kiểm tra xem có đủ thời gian để điều chỉnh không
        if time.time() - self.last_adjustment < self.adjustment_interval:
            return self.current_workers

        # Lấy metrics trung bình
        avg_metrics = self.get_average_metrics()
        if avg_metrics is None:
            # Chưa đủ dữ liệu, sử dụng công thức cơ bản
            return self.calculate_optimal_workers(available_keys)

        # Phân tích hiệu suất
        analysis = self.analyze_performance(avg_metrics)

        new_workers = self.current_workers

        if analysis["action"] == "decrease":
            # Giảm workers: giảm 20-30%
            reduction = max(1, int(self.current_workers * 0.25))
            new_workers = max(self.min_workers, self.current_workers - reduction)

        elif analysis["action"] == "increase":
            # Tăng workers: tăng 20-30%, nhưng không vượt quá giới hạn
            increase = max(1, int(self.current_workers * 0.25))
            max_possible = self.calculate_optimal_workers(available_keys)
            new_workers = min(
                self.max_workers, min(self.current_workers + increase, max_possible)
            )

        # Log điều chỉnh
        if new_workers != self.current_workers:
            self.logger.info(
                f"Adaptive Workers: {self.current_workers} → {new_workers} "
                f"({analysis['action']}) - {analysis['reason']} "
                f"[Confidence: {analysis['confidence']}]"
            )

            # Lưu lịch sử điều chỉnh
            self.adjustment_history.append(
                {
                    "timestamp": time.time(),
                    "from_workers": self.current_workers,
                    "to_workers": new_workers,
                    "action": analysis["action"],
                    "reason": analysis["reason"],
                    "confidence": analysis["confidence"],
                    "available_keys": available_keys,
                    "metrics": avg_metrics,
                }
            )

            self.current_workers = new_workers
            self.last_adjustment = time.time()

        return new_workers

    def get_current_workers(self) -> int:
        """
        Lấy số workers hiện tại.

        Returns:
            Số workers đang được sử dụng
        """
        return self.current_workers

    def get_adjustment_history(self) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử điều chỉnh workers.

        Returns:
            List các dictionaries chứa thông tin về các lần điều chỉnh
        """
        return self.adjustment_history.copy()

    def reset(self) -> None:
        """
        Reset về trạng thái ban đầu.

        Xóa tất cả metrics history và adjustment history,
        reset về số workers tối thiểu.

        Returns:
            None
        """
        self.current_workers = self.min_workers
        self.metrics_history.clear()
        self.adjustment_history.clear()
        self.last_adjustment = time.time()

    def get_status_report(self) -> Dict[str, Any]:
        """
        Tạo báo cáo trạng thái hiện tại của worker manager.

        Returns:
            Dictionary chứa:
                - current_workers: Số workers hiện tại
                - metrics_count: Số lượng metrics trong history
                - last_adjustment: Timestamp của lần điều chỉnh cuối
                - adjustment_count: Số lần đã điều chỉnh
                - average_metrics: Metrics trung bình (nếu có)
                - thresholds: Các ngưỡng cấu hình
        """
        avg_metrics = self.get_average_metrics()

        return {
            "current_workers": self.current_workers,
            "metrics_count": len(self.metrics_history),
            "last_adjustment": self.last_adjustment,
            "adjustment_count": len(self.adjustment_history),
            "average_metrics": avg_metrics.__dict__ if avg_metrics else None,
            "thresholds": self.thresholds.copy(),
        }


class PerformanceTracker:
    """
    Tracker để thu thập metrics hiệu suất từ translation requests.

    Theo dõi:
    - Response times
    - Success/error rates
    - Rate limit incidents
    - Total requests
    """

    def __init__(self) -> None:
        """
        Khởi tạo Performance Tracker.
        """
        self.request_times: deque[float] = deque(maxlen=100)
        self.success_count: int = 0
        self.error_count: int = 0
        self.rate_limit_count: int = 0
        self.total_requests: int = 0
        self.start_time: float = time.time()

    def record_request(
        self, response_time: float, success: bool, is_rate_limit: bool = False
    ) -> None:
        """
        Ghi lại một translation request để tracking.

        Args:
            response_time: Thời gian phản hồi tính bằng giây
            success: True nếu request thành công, False nếu thất bại
            is_rate_limit: True nếu request bị rate limit

        Returns:
            None
        """
        self.request_times.append(response_time)
        self.total_requests += 1

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        if is_rate_limit:
            self.rate_limit_count += 1

    def get_metrics(self, queue_length: int = 0) -> PerformanceMetrics:
        """Tính toán metrics hiện tại"""
        if self.total_requests == 0:
            return PerformanceMetrics(
                success_rate=1.0,
                avg_response_time=0.0,
                rate_limit_frequency=0.0,
                queue_length=queue_length,
                active_workers=0,
                timestamp=time.time(),
            )

        success_rate = self.success_count / self.total_requests
        avg_response_time = (
            statistics.mean(self.request_times) if self.request_times else 0.0
        )
        rate_limit_frequency = self.rate_limit_count / self.total_requests

        return PerformanceMetrics(
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            rate_limit_frequency=rate_limit_frequency,
            queue_length=queue_length,
            active_workers=0,  # Sẽ được set bởi caller
            timestamp=time.time(),
        )

    def reset(self) -> None:
        """
        Reset tất cả metrics về trạng thái ban đầu.

        Returns:
            None
        """
        self.request_times.clear()
        self.success_count = 0
        self.error_count = 0
        self.rate_limit_count = 0
        self.total_requests = 0
        self.start_time = time.time()
