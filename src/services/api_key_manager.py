#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
API Key Manager cho Metadata Extraction
Quản lý rotation và quota của multiple API keys
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Pattern, Tuple

from ..utils.token_bucket import TokenBucket

logger = logging.getLogger("NovelTranslator")

# --- Constants ---

DEFAULT_QUOTA_LIMIT = 20  # Gemini free tier limit (requests per day)
DEFAULT_MAX_REQUESTS_PER_MINUTE = 60
DEFAULT_MIN_DELAY = 1.0

# Regex Patterns for Retry Delay
RETRY_DELAY_PATTERNS: List[Tuple[Pattern, int]] = [
    # Pattern 1: "Please retry in 24.211682423s"
    (re.compile(r"retry.*?(\d+\.?\d*)\s*s", re.IGNORECASE), 0),
    # Pattern 2: RetryInfo {"retryDelay": "24s"}
    (re.compile(r'"retryDelay":\s*"(\d+)s"'), 0),
    # Pattern 3: "retryDelay": "24s" (no quotes)
    (re.compile(r'retryDelay["\']?\s*:\s*["\']?(\d+)s', re.IGNORECASE), 0),
]


@dataclass
class APIKeyStatus:
    """Trạng thái của một API key"""

    key: str
    is_active: bool = True
    last_used: Optional[datetime] = None
    request_count: int = 0
    daily_quota_used: int = 0
    daily_quota_limit: int = DEFAULT_QUOTA_LIMIT
    rate_limit_reset: Optional[datetime] = None
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    # Phase 2: Performance tracking
    total_response_time: float = 0.0  # Tổng response time (seconds)
    avg_response_time: float = 0.0  # Average response time (seconds)
    success_count: int = 0  # Số requests thành công
    error_count: int = 0  # Số requests lỗi
    success_rate: float = 1.0  # Success rate (0.0-1.0)
    # Phase 3: Utilization tracking
    total_active_time: float = 0.0  # Tổng thời gian active (seconds)
    last_active_start: Optional[datetime] = None  # Thời điểm bắt đầu active
    # Phase 4: Per-model quota tracking
    pro_quota_blocked: bool = False  # True nếu Pro model bị hết quota
    flash_quota_blocked: bool = False  # True nếu Flash model bị hết quota
    pro_quota_reset: Optional[datetime] = None  # Thời gian reset quota cho Pro
    flash_quota_reset: Optional[datetime] = None  # Thời gian reset quota cho Flash
    # Phase 4.1: Token Bucket
    bucket: Optional[TokenBucket] = None
    # RPD (Requests Per Day) block: key hết quota/ngày, không dùng lại tới ngày hôm sau
    rpd_blocked_until: Optional[datetime] = None


class APIKeyManager:
    """
    Quản lý rotation và quota của multiple API keys
    """

    def __init__(self, api_keys: List[str], config: Dict[str, Any] = None):
        self.api_keys = api_keys
        self.config = config or {}

        # Initialize API key statuses
        self.key_statuses: Dict[str, APIKeyStatus] = {}
        for key in api_keys:
            self.key_statuses[key] = APIKeyStatus(key=key)

        # Configuration
        self.health_cache_path = "data/cache/api_key_health.json"

        # Personalized Cooldown Mapping (Seconds)
        self.error_cooldown_map = {
            "quota_exceeded": 60,
            "rate_limit": 30,
            "network_error": 15,
            "server_error": 30,
            "generation_error": 5,
            "invalid_key": 86400,  # Block for a day (or until manual fix)
            "default": 30,
        }

        self.max_requests_per_key = self.config.get("max_requests_per_key", 1000)
        self.rate_limit_delay = self.config.get("rate_limit_delay", 60)
        self.quota_reset_hour = self.config.get("quota_reset_hour", 0)  # 0 = midnight
        self.enable_quota_tracking = self.config.get("enable_quota_tracking", True)

        # Rate limiting configuration
        self.min_delay_between_requests = self.config.get("min_delay_between_requests", DEFAULT_MIN_DELAY)
        self.max_requests_per_minute = self.config.get("max_requests_per_minute", DEFAULT_MAX_REQUESTS_PER_MINUTE)

        # Initialize buckets
        rpm_limit = self.max_requests_per_minute
        for status in self.key_statuses.values():
            # Rate: RPM / 60. Capacity: Burst limit (e.g. 5 or RPM)
            status.bucket = TokenBucket(rate=rpm_limit / 60.0, capacity=5.0)

        # Load persisted state
        self.load_state()

        # Thread safety
        self._lock = Lock()  # Lock để đảm bảo thread-safe khi update last_used

        # Statistics
        self.total_requests = 0
        self.total_errors = 0
        self.rotation_count = 0

        self.rotation_count = 0

        logger.info(
            f"Đã khởi tạo APIKeyManager với {len(api_keys)} keys (min_delay: {self.min_delay_between_requests}s, max_rpm: {self.max_requests_per_minute})"
        )

    def _mask_key(self, key: str) -> str:
        """Mask key for logging (e.g., ...ABCD)."""
        return "..." + key[-4:] if len(key) >= 4 else key

    def save_state(self):
        """Lưu trạng thái quota và cooldown vào file vật lý."""
        try:
            os.makedirs(os.path.dirname(self.health_cache_path), exist_ok=True)
            state_data = {}
            for key, status in self.key_statuses.items():
                state_data[key] = {
                    "daily_quota_used": status.daily_quota_used,
                    "rpd_blocked_until": status.rpd_blocked_until.isoformat() if status.rpd_blocked_until else None,
                    "rate_limit_reset": status.rate_limit_reset.isoformat() if status.rate_limit_reset else None,
                    "is_active": status.is_active,
                    "pro_quota_blocked": status.pro_quota_blocked,
                    "flash_quota_blocked": status.flash_quota_blocked,
                }

            with open(self.health_cache_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
            logger.debug(f"[Key Manager] Đã lưu trạng thái sức khỏe {len(state_data)} keys vào cache.")
        except Exception as e:
            logger.warning(f"[Key Manager] Lỗi khi lưu trạng thái: {e}")

    def load_state(self):
        """Tải trạng thái từ file vật lý."""
        if not os.path.exists(self.health_cache_path):
            return
        try:
            with open(self.health_cache_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            now = datetime.now()
            loaded_count = 0
            for key, data in state_data.items():
                if key in self.key_statuses:
                    status = self.key_statuses[key]
                    status.daily_quota_used = data.get("daily_quota_used", 0)
                    status.is_active = data.get("is_active", True)
                    status.pro_quota_blocked = data.get("pro_quota_blocked", False)
                    status.flash_quota_blocked = data.get("flash_quota_blocked", False)

                    if data.get("rpd_blocked_until"):
                        until = datetime.fromisoformat(data["rpd_blocked_until"])
                        if until > now:
                            status.rpd_blocked_until = until

                    if data.get("rate_limit_reset"):
                        reset = datetime.fromisoformat(data["rate_limit_reset"])
                        if reset > now:
                            status.rate_limit_reset = reset
                    loaded_count += 1

            if loaded_count > 0:
                logger.info(f"[Key Manager] Đã khôi phục trạng thái cho {loaded_count} keys từ cache.")
        except Exception as e:
            logger.warning(f"[Key Manager] Lỗi khi tải trạng thái: {e}")

    def _log_pool_health(self, triggering_error: str = ""):
        """Log trạng thái sức khỏe của pool key."""
        active = self.get_active_key_count()
        total = len(self.api_keys)
        msg = f"📉 Key bị chặn ({triggering_error}). Sức khỏe: {active}/{total} keys active."
        if active == 0:
            logger.critical(f"🔥 {msg} HỆ THỐNG DỪNG HOẠT ĐỘNG.")
        elif active < 5:
            logger.warning(msg)
        else:
            logger.info(msg)

    def _extract_retry_delay(self, error_message: str) -> Optional[int]:
        """
        Extract retry delay từ error message.
        """
        for pattern, buffer in RETRY_DELAY_PATTERNS:
            match = pattern.search(error_message)
            if match:
                delay_seconds = float(match.group(1))
                return int(delay_seconds) + 5  # +5s buffer
        return None

    def _calculate_dynamic_delay(self, base_delay: int, quota_keys_count: int, total_keys: int) -> int:
        """
        Tính delay động dựa trên số keys bị quota.
        """
        if total_keys == 0:
            return base_delay

        quota_ratio = quota_keys_count / total_keys

        # Nếu >50% keys bị quota → tăng delay để tránh spam
        if quota_ratio > 0.5:
            multiplier = 1.5 + (quota_ratio - 0.5) * 2  # 1.5x đến 2.5x
            return int(base_delay * multiplier)

        # Nếu <50% keys bị quota → giữ nguyên hoặc giảm nhẹ
        return base_delay

    def get_available_key(self, exclude_key: Optional[str] = None) -> Optional[str]:
        """
        Lấy API key khả dụng theo thứ tự ưu tiên.
        Ưu tiên keys không bị quota.
        """
        self._reset_daily_quotas_if_needed()

        # 1. ƯU TIÊN: Keys không bị quota và đang available
        available_keys = [
            status
            for status in self.key_statuses.values()
            if status.is_active
            and self._is_key_available(status)
            and not status.rate_limit_reset
            and (exclude_key is None or status.key != exclude_key)
        ]

        if available_keys:
            # Sort by priority: least used
            available_keys.sort(key=lambda s: s.request_count)
            return available_keys[0].key

        # Không trả key đang bị block (RPD/rate limit) để tránh 429 lặp
        return None

    async def get_key_for_worker(self, worker_id: int) -> str:
        """
        Lấy API key cố định cho một worker dựa trên ID.
        Hỗ trợ chiến lược Worker-Key Affinity.
        """
        if not self.api_keys:
            raise ValueError("No API keys available")

        key_index = worker_id % len(self.api_keys)
        return self.api_keys[key_index]

    def _is_key_available(self, status: APIKeyStatus) -> bool:
        """
        Kiểm tra xem key có khả dụng không.
        """
        # Check if key is active
        if not status.is_active:
            return False

        now = datetime.now()

        # RPD-block (quota/ngày): không dùng lại tới rpd_blocked_until
        if getattr(status, "rpd_blocked_until", None) and now < status.rpd_blocked_until:
            return False

        # Check rate limit - nếu đã qua reset time, clear nó
        if status.rate_limit_reset:
            if now >= status.rate_limit_reset:
                # Reset time đã qua, clear rate limit
                status.rate_limit_reset = None
                logger.debug(f"Rate limit reset time passed for key: {status.key[:10]}...")
            else:
                # Vẫn trong rate limit period
                return False

        # Check daily quota (chỉ nếu enable tracking)
        if self.enable_quota_tracking and status.daily_quota_used >= status.daily_quota_limit:
            # Kiểm tra xem có cần reset quota không
            self._reset_daily_quotas_if_needed()
            # Kiểm tra lại sau khi reset
            if status.daily_quota_used >= status.daily_quota_limit:
                return False

        # Check consecutive errors - chỉ deactivate nếu quá nhiều (và không phải quota error)
        if status.consecutive_errors >= 10:
            return False

        return True

    def is_key_blocked(self, key: str) -> bool:
        """Check if a specific key is currently blocked/unavailable."""
        if key not in self.key_statuses:
            return True
        return not self._is_key_available(self.key_statuses[key])

    def _reset_daily_quotas_if_needed(self):
        """Reset daily quotas nếu đã qua ngày mới."""
        now = datetime.now()
        for status in self.key_statuses.values():
            should_reset = False

            if not status.last_used:
                should_reset = True
            elif now.date() > status.last_used.date():
                if now.hour >= self.quota_reset_hour:
                    should_reset = True
            elif now.date() == status.last_used.date():
                pass
            else:
                should_reset = True

            if should_reset:
                old_quota = status.daily_quota_used
                status.daily_quota_used = 0
                if old_quota > 0:
                    status.consecutive_errors = 0
                    status.last_error = None
                    logger.info(
                        f"Đặt lại quota hàng ngày cho key: {status.key[:10]}... "
                        f"(quota cũ: {old_quota}/{status.daily_quota_limit})"
                    )

    def mark_request_success(self, key: str, tokens_used: int = 0):
        """Đánh dấu request thành công (sync)."""
        if key in self.key_statuses:
            with self._lock:
                status = self.key_statuses[key]
                status.last_used = datetime.now()
                status.request_count += 1
                status.daily_quota_used += 1
                status.consecutive_errors = 0
                status.last_error = None
                self.total_requests += 1

                logger.debug(
                    f"[Key Manager] [SUCCESS] {self._mask_key(key)} (quota: {status.daily_quota_used}/{status.daily_quota_limit})"
                )

                # Save state periodically
                if status.daily_quota_used % 5 == 0:
                    self.save_state()

                # Phase v3: RPD Warning (80%)
                if status.daily_quota_used == int(status.daily_quota_limit * 0.8):
                    logger.warning(
                        f"⚠️ Key {key[:10]}... đã đạt 80% quota ngày ({status.daily_quota_used}/{status.daily_quota_limit})."
                    )

    async def mark_request_error(self, key: str, error_type: str, error_message: str = ""):
        """Đánh dấu request lỗi với logic xử lý thông minh."""
        if key in self.key_statuses:
            with self._lock:
                status = self.key_statuses[key]
                status.last_error = error_message
                self.total_errors += 1

            error_type_lower = error_type.lower()
            error_msg_lower = error_message.lower()

            # Handle quota/rate limit errors AND 503 Service Unavailable
            if (
                error_type_lower in ["quota_exceeded", "rate_limit", "server_error"]
                or "quota" in error_type_lower
                or "429" in error_type
                or "503" in error_type
                or "quota" in error_msg_lower
                or "429" in error_message
                or "503" in error_message
                or "rate limit" in error_msg_lower
                or "resource_exhausted" in error_msg_lower
                or "overloaded" in error_msg_lower
                or "unavailable" in error_msg_lower
            ):
                # RPD (quota/ngày): "You exceeded your current quota... plan and billing" → block tới ngày mai
                if "you exceeded your current quota" in error_msg_lower and "plan and billing" in error_msg_lower:
                    status.daily_quota_used = status.daily_quota_limit
                    tomorrow = datetime.now() + timedelta(days=1)
                    status.rpd_blocked_until = tomorrow.replace(
                        hour=self.quota_reset_hour, minute=0, second=0, microsecond=0
                    )
                    logger.warning(
                        f"RPD quota reached for key {self._mask_key(key)}, blocked until {status.rpd_blocked_until.isoformat()}"
                    )
                    self.save_state()
                    self._log_pool_health("RPD_Quota")
                    return

                # Personalized Cooldown Logic
                retry_delay_seconds = self._extract_retry_delay(error_message)
                base_delay = retry_delay_seconds or self.error_cooldown_map.get(
                    error_type_lower, self.error_cooldown_map["default"]
                )
                quota_keys_count = sum(
                    1 for s in self.key_statuses.values() if s.rate_limit_reset and datetime.now() < s.rate_limit_reset
                )
                dynamic_delay = self._calculate_dynamic_delay(base_delay, quota_keys_count, len(self.key_statuses))

                # Phase 4: Detect per-model quota from error message
                is_pro_specific = "gemini-2.5-pro" in error_msg_lower or "model: gemini-2.5-pro" in error_msg_lower
                is_flash_specific = (
                    "gemini-2.5-flash" in error_msg_lower or "model: gemini-2.5-flash" in error_msg_lower
                )

                if is_pro_specific and not is_flash_specific:
                    status.pro_quota_blocked = True
                    status.pro_quota_reset = datetime.now() + timedelta(seconds=dynamic_delay)
                    logger.debug(
                        f"Pro model quota hit for key: {self._mask_key(key)} "
                        f"(Flash model may still be available, reset in {dynamic_delay}s)"
                    )
                    self.save_state()
                    self._log_pool_health("Pro Quota")
                    return
                elif is_flash_specific and not is_pro_specific:
                    status.flash_quota_blocked = True
                    status.flash_quota_reset = datetime.now() + timedelta(seconds=dynamic_delay)
                    status.rate_limit_reset = datetime.now() + timedelta(seconds=dynamic_delay)
                    logger.warning(f"Flash model quota hit for key: {self._mask_key(key)} (reset in {dynamic_delay}s)")
                    self.save_state()
                    self._log_pool_health("Flash Quota")
                    return
                else:
                    status.pro_quota_blocked = True
                    status.flash_quota_blocked = True
                    status.rate_limit_reset = datetime.now() + timedelta(seconds=dynamic_delay)
                    logger.warning(
                        f"Quota/Rate limit hit cho key: {self._mask_key(key)} "
                        f"(loại lỗi: {error_type}, reset sau {dynamic_delay}s, {quota_keys_count}/{len(self.key_statuses)} keys blocked)"
                    )
                    self.save_state()
                    return

            # Handle invalid key errors
            if (
                error_type_lower in ["invalid_key"]
                or "invalid" in error_type_lower
                or "401" in error_type
                or "403" in error_type
            ):
                status.is_active = False
                status.consecutive_errors = 0
                logger.error(f"Invalid API key deactivated: {self._mask_key(key)}")
                self.save_state()
                return

            # Handle other errors
            status.consecutive_errors += 1
            if status.consecutive_errors >= 10:
                status.is_active = False
                logger.error(f"API key deactivated due to errors ({status.consecutive_errors}): {self._mask_key(key)}")
                self.save_state()

    async def return_key(
        self,
        worker_id: int,
        key: str,
        is_error: bool = False,
        error_type: str = "",
        error_message: Optional[str] = None,
    ):
        """
        Trả lại key sau khi sử dụng (tương thích với pattern cũ nhưng hỗ trợ Affinity).
        """
        if is_error:
            await self.mark_request_error(key, error_type, error_message or "")
        else:
            self.mark_request_success(key)

    def get_status_summary(self) -> Dict[str, Any]:
        """Lấy tóm tắt trạng thái tất cả keys"""
        active_keys = sum(1 for status in self.key_statuses.values() if status.is_active)
        total_quota_used = sum(status.daily_quota_used for status in self.key_statuses.values())
        total_quota_limit = sum(status.daily_quota_limit for status in self.key_statuses.values())

        return {
            "total_keys": len(self.api_keys),
            "active_keys": active_keys,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_quota_used": total_quota_used,
            "total_quota_limit": total_quota_limit,
            "key_details": {
                key[:10] + "...": {
                    "active": status.is_active,
                    "requests": status.request_count,
                    "quota_used": status.daily_quota_used,
                    "quota_limit": status.daily_quota_limit,
                    "consecutive_errors": status.consecutive_errors,
                }
                for key, status in self.key_statuses.items()
            },
        }

    def get_active_key_count(self) -> int:
        """
        [Phase 6] Trả về số lượng key đang thực sự khả dụng (Active & Not Cooldown & Not RPD-block).
        """
        now = datetime.now()
        count = 0
        for status in self.key_statuses.values():
            if not status.is_active:
                continue

            # RPD-block (quota/ngày)
            if getattr(status, "rpd_blocked_until", None) and now < status.rpd_blocked_until:
                continue

            # Check rate limit cooldown
            if status.rate_limit_reset and now < status.rate_limit_reset:
                continue

            # Check per-model quota
            if (status.pro_quota_blocked and status.pro_quota_reset and now < status.pro_quota_reset) and (
                status.flash_quota_blocked and status.flash_quota_reset and now < status.flash_quota_reset
            ):
                continue

            # Check daily quota
            if self.enable_quota_tracking and status.daily_quota_used >= status.daily_quota_limit:
                continue

            # Check consecutive errors (Sync with _is_key_available)
            if status.consecutive_errors >= 10:
                continue
            count += 1
        return count

    def get_earliest_reset_time(self) -> Optional[datetime]:
        """Trả về thời điểm reset sớm nhất trong số các key đang bị block."""
        now = datetime.now()
        resets = []
        for status in self.key_statuses.values():
            if status.rpd_blocked_until and status.rpd_blocked_until > now:
                resets.append(status.rpd_blocked_until)
            if status.rate_limit_reset and status.rate_limit_reset > now:
                resets.append(status.rate_limit_reset)
        return min(resets) if resets else None

    def get_quota_status_summary(self) -> Dict[str, Any]:
        """Tổng hợp trạng thái quota/cooldown cho toàn bộ pool."""
        now = datetime.now()
        available = 0
        rpd_blocked = 0
        cooldown = 0

        for status in self.key_statuses.values():
            if not status.is_active:
                continue

            is_rpd = status.rpd_blocked_until and status.rpd_blocked_until > now
            is_cooldown = status.rate_limit_reset and status.rate_limit_reset > now

            if is_rpd:
                rpd_blocked += 1
            elif is_cooldown:
                cooldown += 1
            elif self.enable_quota_tracking and status.daily_quota_used >= status.daily_quota_limit:
                rpd_blocked += 1
            else:
                available += 1

        return {
            "available_keys": available,
            "rpd_blocked_keys": rpd_blocked,
            "cooldown_keys": cooldown,
            "total_keys": len(self.api_keys),
        }

    def reset_key(self, key: str):
        """Reset trạng thái của một key"""
        if key in self.key_statuses:
            status = self.key_statuses[key]
            status.is_active = True
            status.consecutive_errors = 0
            status.last_error = None
            status.rate_limit_reset = None
            if hasattr(status, "rpd_blocked_until"):
                status.rpd_blocked_until = None
            logger.info(f"Đã đặt lại API key: {key[:10]}...")

    def reset_all_keys(self):
        """Reset tất cả keys"""
        for key in self.key_statuses:
            self.reset_key(key)
        logger.info("Đã đặt lại tất cả API keys")

    async def add_delay_between_requests(self, key: str):
        """Thêm delay giữa các requests để tránh rate limit (Token Bucket)."""
        if key in self.key_statuses:
            status = self.key_statuses[key]

            # Ưu tiên dùng Token Bucket nếu có
            if status.bucket:
                await status.bucket.wait_for_tokens(1.0)
            else:
                # Fallback logic cũ
                with self._lock:
                    if status.last_used:
                        time_since_last = (datetime.now() - status.last_used).total_seconds()
                        if time_since_last < self.min_delay_between_requests:
                            delay = self.min_delay_between_requests - time_since_last
                            await asyncio.sleep(delay)

            # Update last_used regardless of method
            with self._lock:
                status.last_used = datetime.now()

    async def wait_for_available_key(self, timeout: Optional[int] = None) -> Optional[str]:
        """Đợi cho đến khi có key khả dụng."""
        start_time = datetime.now()
        while True:
            key = self.get_available_key()
            if key:
                return key
            if timeout and (datetime.now() - start_time).total_seconds() >= timeout:
                return None
            await asyncio.sleep(5)

    def get_quota_status_summary(self) -> Dict[str, Any]:
        """
        Tóm tắt trạng thái quota cho translator (tương thích SmartKeyDistributor).
        """
        total = len(self.api_keys)
        available = self.get_active_key_count()
        quota_blocked = total - available
        ratio = quota_blocked / total if total > 0 else 0.0

        earliest: Optional[datetime] = None
        now = datetime.now()
        for status in self.key_statuses.values():
            for t in (
                getattr(status, "rpd_blocked_until", None),
                status.rate_limit_reset,
                status.pro_quota_reset,
                status.flash_quota_reset,
            ):
                if t and now < t and (earliest is None or t < earliest):
                    earliest = t

        return {
            "quota_blocked_ratio": ratio,
            "quota_blocked_keys": quota_blocked,
            "available_keys": available,
            "total_keys": total,
            "earliest_reset_time": earliest,
        }

    def handle_exception(self, key: str, exc: Exception) -> str:
        """
        Phân loại exception và trả về error_type (translator gọi tiếp return_key với type này).
        """
        from ..utils.error_classifier import classify_error

        error_type = classify_error(exc)
        return error_type

    def get_earliest_reset_time(self) -> Optional[datetime]:
        """Thời điểm reset sớm nhất trong số các key đang bị block (cho recovery task)."""
        now = datetime.now()
        earliest: Optional[datetime] = None
        for status in self.key_statuses.values():
            for t in (
                getattr(status, "rpd_blocked_until", None),
                status.rate_limit_reset,
                status.pro_quota_reset,
                status.flash_quota_reset,
            ):
                if t and now < t and (earliest is None or t < earliest):
                    earliest = t
        return earliest
