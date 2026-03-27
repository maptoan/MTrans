#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Smart Key Distributor v7.0
==========================

Hệ thống quản lý API key thông minh với:
1. Chunk-First Allocation - Phân bổ worker tối ưu theo số chunk
2. Zero-Wait Replacement - Thay key lỗi ngay lập tức
3. Auto-Recovery Pool - Tự động đưa key hết cooldown về queue

PHIÊN BẢN: v7.0 (2026-01-30)
"""

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Set

from src.services.api_key_manager import APIKeyManager
from src.utils.error_classifier import classify_error

logger = logging.getLogger("NovelTranslator")

# --- Constants ---

DEFAULT_COOLDOWNS = {
    "rate_limit": 15,  # 429 RPM
    "quota_exceeded": 60,  # Quota error
    "server_error": 30,  # 500/503
    "timeout": 10,  # Network timeout
    "generation_error": 30,  # Model error
    "unknown": 60,  # Unknown errors
}

BACKOFF_MULTIPLIERS = [1, 2, 4, 8, 16]
RPD_COOLDOWN_SECONDS = 86400  # 24 hours
MAX_RETRIES_BEFORE_RPD_PENALTY = 3


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class KeyErrorState:
    """Track error state for a key."""

    key: str
    error_type: str
    retry_count: int = 0
    first_error_time: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


@dataclass
class KeyStatus:
    """Status of an API key."""

    key: str
    is_active: bool = True
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


# =============================================================================
# COOLDOWN CALCULATOR
# =============================================================================


class CooldownCalculator:
    """Calculate cooldown time based on error type and retry history."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize with optional config overrides."""
        config = config or {}

        self.BASE_COOLDOWNS = DEFAULT_COOLDOWNS.copy()
        if "base_cooldowns" in config:
            self.BASE_COOLDOWNS.update(config["base_cooldowns"])

        self.RPD_COOLDOWN_SECONDS = config.get("rpd_cooldown_hours", 24) * 3600
        self.MAX_RETRIES_BEFORE_RPD_PENALTY = config.get("max_retries_before_rpd", MAX_RETRIES_BEFORE_RPD_PENALTY)
        self.BACKOFF_MULTIPLIERS = config.get("backoff_multipliers", BACKOFF_MULTIPLIERS)

    def calculate_cooldown(self, error_type: str, retry_count: int, error_message: str = "") -> int:
        """
        Calculate cooldown seconds based on error type and retry history.
        """
        error_type = error_type.lower()
        error_message_lower = error_message.lower()

        # 1. Parse từ API response nếu có (rate_limit)
        if error_type == "rate_limit" or "429" in error_message:
            parsed_delay = self._parse_retry_after(error_message)
            if parsed_delay:
                return parsed_delay

        # 2. Quota exceeded với retry > 3 → RPD penalty (1 day)
        if error_type == "quota_exceeded" or "quota" in error_message_lower:
            if retry_count >= self.MAX_RETRIES_BEFORE_RPD_PENALTY:
                # Giảm log lặp: chỉ log lần đầu đạt RPD hoặc mỗi 10 lần (10, 20, 30...)
                if retry_count == self.MAX_RETRIES_BEFORE_RPD_PENALTY or retry_count % 10 == 0:
                    logger.warning(
                        f"Key đã vượt quá {retry_count} lần thử lại vì lỗi quota, áp dụng thời gian chờ RPD 24h"
                    )
                else:
                    logger.debug(f"Key quota retry #{retry_count}, RPD 24h cooldown")
                return self.RPD_COOLDOWN_SECONDS

            # Check if error message mentions "daily" or "per day"
            if "daily" in error_message_lower or "per day" in error_message_lower:
                return self.RPD_COOLDOWN_SECONDS

        # 3. Server error với exponential backoff
        if error_type in ["server_error", "timeout", "generation_error"]:
            base = self.BASE_COOLDOWNS.get(error_type, 30)
            multiplier_idx = min(retry_count, len(self.BACKOFF_MULTIPLIERS) - 1)
            multiplier = self.BACKOFF_MULTIPLIERS[multiplier_idx]
            cooldown = base * multiplier

            logger.debug(f"Exponential backoff: {base}s × {multiplier} = {cooldown}s (retry #{retry_count})")
            return cooldown

        # 4. Default: base cooldown
        return self.BASE_COOLDOWNS.get(error_type, 60)

    def _parse_retry_after(self, error_message: str) -> Optional[int]:
        """Parse 'Retry after: Xs' from API error message."""
        match = re.search(r"retry\s*after[:\s]*(\d+\.?\d*)\s*s", error_message.lower())
        if match:
            return int(float(match.group(1))) + 1  # +1s safety margin
        return None


# =============================================================================
# GLOBAL RATE LIMITER
# =============================================================================


class GlobalRateLimiter:
    """
    Enforces a strict global rate limit across all keys and workers.
    Uses a Token Bucket / Sliding Window approach.
    """

    def __init__(self, rpm_limit: int = 5):
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / rpm_limit if rpm_limit > 0 else 0
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

        # Sliding Window Tracking
        self.request_timestamps = []
        self.window_size = 60.0  # 1 minute

    async def acquire(self):
        """
        Wait until a request slot is available globally.
        """
        if self.rpm_limit <= 0:
            return

        async with self._lock:
            now = asyncio.get_event_loop().time()

            # Prune old timestamps
            self.request_timestamps = [t for t in self.request_timestamps if now - t < self.window_size]

            if len(self.request_timestamps) >= self.rpm_limit:
                # Window full, calculate wait time
                earliest = self.request_timestamps[0]
                wait_time = self.window_size - (now - earliest) + 0.5  # +0.5s safety buffer

                if wait_time > 0:
                    logger.warning(
                        f"Đạt giới hạn tốc độ toàn cục ({len(self.request_timestamps)}/{self.rpm_limit}). Tạm dừng {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    # Re-check time after sleep
                    now = asyncio.get_event_loop().time()

            # Add current request
            self.request_timestamps.append(now)
            self.last_request_time = now


# =============================================================================
# SMART KEY DISTRIBUTOR
# =============================================================================


class SmartKeyDistributor:
    """
    Smart Key Distributor v7.0

    Features:
    - Chunk-first worker allocation
    - Zero-wait key replacement
    - Auto-recovery background task
    - Error-categorized pools with exponential backoff
    """

    def __init__(self, api_keys: List[str], num_chunks: int, config: Optional[Dict] = None):
        """
        Initialize Smart Key Distributor.

        Args:
            api_keys: List of API keys
            num_chunks: Number of chunks to translate
            config: Optional configuration dict
        """
        self.config = config or {}

        # [Global Rate Limiter]
        # Get RPM from performance config (default 5 for Free Tier)
        perf_config = self.config.get("performance", {})
        rpm_limit = int(perf_config.get("max_requests_per_minute", 5))
        self.global_limiter = GlobalRateLimiter(rpm_limit)

        self.rpm_limit = rpm_limit  # Store for logging later

        logger.info(f"DEBUG_KEY_DISTRIBUTOR: rpm_limit={rpm_limit}, num_keys={len(api_keys)}")
        self._all_keys = api_keys.copy()
        self.num_chunks = num_chunks
        self._running = False
        self._recovery_task_handle = None
        self._lock = Lock()

        # [Chuẩn hóa] Nguồn sự thật duy nhất cho trạng thái key (blocked/usable, RPD, quota)
        # Free tier: 5 RPM/key, 20 RPD/key → min_delay = 60/5 = 12s giữa 2 request cùng key.
        # Ưu tiên performance (free-tier) để key_management không ghi đè min_delay/max_rpm.
        key_mgmt = self.config.get("key_management", {})
        state_config = {
            "enable_quota_tracking": True,
            **key_mgmt,
            "min_delay_between_requests": perf_config.get("min_delay_between_requests", 12.0),
            "max_requests_per_minute": perf_config.get("max_requests_per_minute_per_key", 5),
        }
        self._state: APIKeyManager = APIKeyManager(api_keys, state_config)
        self._async_lock = asyncio.Lock()  # [v9.1] Async lock cho thread-safe gán key

        # Cooldown calculator (giữ cho tương thích, không dùng cho state)
        key_mgmt_config = self.config.get("key_management", {})
        self.cooldown_calculator = CooldownCalculator(key_mgmt_config)

        # Calculate optimal allocation
        allocation = self._calculate_optimal_workers(num_chunks, len(api_keys))

        # Shuffle keys để phân bố đều
        shuffled = api_keys.copy()
        random.shuffle(shuffled)

        # Phân bổ pools
        idx = 0
        num_translation = allocation["translation_workers"]
        num_editor = allocation["editor_workers"]

        self.translation_keys = shuffled[idx : idx + num_translation]
        idx += num_translation

        self.editor_keys = shuffled[idx : idx + num_editor]
        idx += num_editor

        # Reserve Queue + set keys đang trong reserve (để recovery không trùng)
        self.reserve_queue = asyncio.Queue()
        self._keys_in_reserve: Set[str] = set()
        for key in shuffled[idx:]:
            self.reserve_queue.put_nowait(key)
            self._keys_in_reserve.add(key)

        # Error pools giữ cho tương thích (read-only từ tests); trạng thái thực ở _state
        self.error_pools: Dict[str, Dict[str, KeyErrorState]] = {
            "quota": {},
            "rate_limit": {},
            "server_error": {},
            "timeout": {},
        }
        self.invalid_keys: Set[str] = set()  # Key vĩnh viễn invalid (sync từ _state khi is_active=False)

        # Worker-Key mapping
        self.worker_keys: Dict[int, str] = {}

        # Statistics
        self.stats = {
            "replacements_from_reserve": 0,
            "replacements_from_recovery": 0,
            "keys_recovered": 0,
            "keys_penalized_rpd": 0,
        }

        logger.info(
            f"Đã khởi tạo SmartKeyDistributor v7.0: "
            f"{len(api_keys)} keys, "
            f"{self.num_chunks} phân đoạn. Giới hạn toàn cục: {rpm_limit} RPM"
        )

    @property
    def key_statuses(self) -> Dict[str, Any]:
        """Trạng thái key từ _state (nguồn sự thật duy nhất)."""
        return self._state.key_statuses

    def _calculate_optimal_workers(self, num_chunks: int, num_keys: int) -> Dict:
        """
        Tính số worker tối ưu dựa trên số chunk và số key.

        Ratios (configurable):
        - 70% keys cho translation workers
        - 20% keys cho editor workers
        - 10% keys cho reserve
        """
        key_mgmt = self.config.get("key_management", {})

        if num_chunks >= num_keys:
            # Nhiều chunks → ưu tiên translation
            translation_ratio = key_mgmt.get("translation_worker_ratio", 0.7)
            editor_ratio = key_mgmt.get("editor_worker_ratio", 0.2)
            key_mgmt.get("reserve_ratio", 0.1)
        else:
            # Ít chunks → giảm workers, tăng reserve
            ratio = num_chunks / num_keys
            translation_ratio = ratio * 0.7
            editor_ratio = ratio * 0.2
            1.0 - translation_ratio - editor_ratio

        translation_workers = min(num_chunks, int(num_keys * translation_ratio))
        editor_workers = min(num_chunks, int(num_keys * editor_ratio))
        reserve_count = max(1, num_keys - translation_workers - editor_workers)

        logger.debug(
            f"Phân bổ tối ưu: {translation_workers} dịch thuật, {editor_workers} biên tập, {reserve_count} dự phòng"
        )

        return {
            "translation_workers": translation_workers,
            "editor_workers": editor_workers,
            "reserve_keys": reserve_count,
        }

    # =========================================================================
    # KEY ASSIGNMENT
    # =========================================================================

    async def get_key_for_worker(self, worker_id: int, worker_type: str = "translation") -> Optional[str]:
        """
        Lấy key cho worker (với Async Lock bảo vệ).
        """
        async with self._async_lock:
            # 1. Kiểm tra key hiện tại của worker
            if worker_id in self.worker_keys:
                current_key = self.worker_keys[worker_id]
                if self._is_key_available(current_key):
                    return current_key
                # Key hiện tại đã bị block -> Xóa bỏ để lấy key mới
                self.worker_keys.pop(worker_id, None)

            # 2. Lấy key mới từ pool hoặc reserve
            key = None
            
            # Ưu tiên từ translation_keys / editor_keys (bỏ qua key bị block)
            target_pool = self.translation_keys if worker_type == "translation" else self.editor_keys
            assigned = set(self.worker_keys.values())

            if target_pool:
                while target_pool:
                    k = target_pool.pop(0)
                    if self._state.is_key_blocked(k):
                        # Key bị block đưa vào reserve/cooldown
                        self.reserve_queue.put_nowait(k)
                        self._keys_in_reserve.add(k)
                        continue
                    if k in assigned:
                        # Key đang được worker khác dùng -> bỏ qua
                        continue
                    key = k
                    break

            # 3. Nếu chưa tìm được -> lấy từ reserve (gọi helper đã có lock logic nhưng ở đây ta đang giữ lock rồi)
            # Chú ý: _try_replace_key_internal cũng tìm trong reserve
            if not key:
                key = await self._try_replace_key_internal(worker_id)

            if key:
                self.worker_keys[worker_id] = key
                logger.debug(f"Đã gán key {key[:10]}... cho worker {worker_id}")
            return key

    async def get_key_for_worker_async(self, worker_id: int, worker_type: str = "translation") -> Optional[str]:
        """Async version of get_key_for_worker."""
        return self.get_key_for_worker(worker_id, worker_type)

    def _is_key_available(self, key: str) -> bool:
        """Check if key is available; trạng thái từ _state (APIKeyManager)."""
        if key in self.invalid_keys:
            return False
        return not self._state.is_key_blocked(key)

    async def add_delay_between_requests(self, key: str):
        """Global limiter + delegate per-key delay tới _state."""
        await self.global_limiter.acquire()
        await self._state.add_delay_between_requests(key)

    # =========================================================================
    # KEY REPLACEMENT
    # =========================================================================

    async def replace_worker_key(
        self, worker_id: int, failed_key: str, error_type: str, error_message: str = ""
    ) -> Optional[str]:
        """
        Thay key lỗi ngay lập tức. Trạng thái failed_key cập nhật qua _state.return_key.
        Dùng async lock để tránh Race Condition khi nhiều worker cùng xoay key.
        """
        async with self._async_lock:
            # 1. Trả key cũ
            await self._state.return_key(
                worker_id, failed_key, is_error=True, error_type=error_type, error_message=error_message
            )
            
            # Cập nhật invalid_keys nếu cần
            if failed_key in self._state.key_statuses and not self._state.key_statuses[failed_key].is_active:
                self.invalid_keys.add(failed_key)
            
            self.worker_keys.pop(worker_id, None)

            # 2. Tìm key thay thế
            new_key = await self._try_replace_key_internal(worker_id)
            if new_key:
                self.worker_keys[worker_id] = new_key
                self.stats["replacements_from_reserve"] += 1
                logger.info(f"♻️ Worker {worker_id}: Thay thế key lỗi → {new_key[:10]}...")
                return new_key
            
            logger.warning(f"⚠️ Worker {worker_id}: Không có key thay thế khả dụng!")
            return None

    async def _try_replace_key_internal(self, worker_id: int) -> Optional[str]:
        """[Internal] Tìm key khả dụng từ pool hoặc reserve. Gọi bên trong lock."""
        # Ưu tiên lấy từ pool tương ứng nhưng chưa được assign
        target_pool = self.translation_keys if worker_id < 100 else self.editor_keys
        assigned = set(self.worker_keys.values())
        
        for key in target_pool:
            if key not in assigned and not self._state.is_key_blocked(key):
                return key

        # Thử lấy từ reserve
        while True:
            try:
                key = self.reserve_queue.get_nowait()
                self._keys_in_reserve.discard(key)
            except asyncio.QueueEmpty:
                break
                
            if key not in assigned and not self._state.is_key_blocked(key):
                return key
            
            # Nếu key trong reserve cũng bị blocked, đưa lại vào reserve (hoặc bỏ qua)
            self.reserve_queue.put_nowait(key)
            self._keys_in_reserve.add(key)
            
        # Cuối cùng: tìm key phục hồi sớm nhất
        return self._get_earliest_recovery_key_internal()

    def _get_earliest_recovery_key_internal(self) -> Optional[str]:
        """Lấy bất kỳ key nào đang free và không bị block."""
        assigned = set(self.worker_keys.values())
        for key in self._all_keys:
            if key not in assigned and not self._state.is_key_blocked(key):
                return key
        return None

    def _move_to_error_pool(self, key: str, error_type: str, error_message: str = ""):
        """Deprecated: trạng thái key do _state (APIKeyManager) quản lý. Giữ no-op cho tương thích."""
        pass

    def _get_pool_name(self, error_type: str, error_message: str) -> str:
        """Determine which error pool to use."""
        error_message_lower = error_message.lower()
        error_type_lower = error_type.lower()

        if "quota" in error_type_lower or "quota" in error_message_lower or "429" in error_message:
            return "quota"
        if "rate" in error_type_lower or "rate" in error_message_lower:
            return "rate_limit"
        if "timeout" in error_type_lower or "timeout" in error_message_lower or \
           "deadline" in error_message_lower or "expired" in error_message_lower:
            return "timeout"
        if "503" in error_message or "unavailable" in error_message_lower or \
           "502" in error_message or "504" in error_message or \
           "overloaded" in error_message_lower or "server" in error_type_lower:
            return "server_error"
            
        return "server_error"

    def _get_earliest_recovery_key(self) -> Optional[str]:
        """Lấy bất kỳ key nào đang free và không bị block (trạng thái từ _state)."""
        assigned = set(self.worker_keys.values())
        for key in self._all_keys:
            if key not in assigned and not self._state.is_key_blocked(key):
                return key
        return None

    # =========================================================================
    # AUTO-RECOVERY BACKGROUND TASK
    # =========================================================================

    async def start_recovery_task(self):
        """Start the background recovery task."""
        self._running = True
        self._recovery_task_handle = asyncio.create_task(self._recovery_task())
        logger.debug("Tác vụ phục hồi đã bắt đầu")

    async def stop_recovery_task(self):
        """Stop the background recovery task."""
        self._running = False
        if self._recovery_task_handle:
            self._recovery_task_handle.cancel()
            try:
                await self._recovery_task_handle
            except asyncio.CancelledError:
                pass
        logger.debug("Tác vụ phục hồi đã dừng")

    async def _recovery_task(self):
        """
        Background task chạy liên tục với smart interval.

        Thay vì check cố định 1s, tính interval dựa trên earliest recovery time.
        """
        while self._running:
            try:
                # Tìm thời gian recovery sớm nhất
                earliest = self._get_earliest_recovery_time()

                if earliest:
                    wait_time = (earliest - datetime.now()).total_seconds()
                    # Clamp: min 1s, max 30s
                    wait_time = max(1, min(wait_time, 30))
                else:
                    wait_time = 5  # Default nếu không có key nào đang cooldown

                await asyncio.sleep(wait_time)

                # Process recovered keys
                await self._process_recovered_keys()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery task error: {e}")
                await asyncio.sleep(5)

    def _get_earliest_recovery_time(self) -> Optional[datetime]:
        """Thời điểm key sớm nhất hết block (từ _state)."""
        return self._state.get_earliest_reset_time()

    async def _process_recovered_keys(self):
        """Đưa key đã hết block (theo _state) trở lại reserve queue."""
        assigned = set(self.worker_keys.values())
        for key in self._all_keys:
            if key in assigned or key in self._keys_in_reserve or self._state.is_key_blocked(key):
                continue
            self.reserve_queue.put_nowait(key)
            self._keys_in_reserve.add(key)
            self.stats["keys_recovered"] += 1
            logger.info(f"🔄 Key {key[:10]}... đã phục hồi, trở lại kho dự phòng.")

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def mark_request_success(self, key: str):
        """Delegate tới _state."""
        self._state.mark_request_success(key)

    async def mark_request_error(self, key: str, error_type: str, error_message: str = ""):
        """Delegate tới _state; sync invalid_keys nếu key bị deactivate."""
        await self._state.mark_request_error(key, error_type, error_message)
        if key in self._state.key_statuses and not self._state.key_statuses[key].is_active:
            self.invalid_keys.add(key)

    def handle_exception(self, key: str, exc: Exception) -> str:
        """
        Phân loại exception; trạng thái key do return_key cập nhật (translator gọi tiếp return_key).
        """
        return self._state.handle_exception(key, exc)

    async def get_available_key(self) -> Optional[str]:
        """Lấy key khả dụng từ reserve (bỏ qua key bị block) hoặc từ _all_keys."""
        async with self._async_lock:
            while True:
                try:
                    key = self.reserve_queue.get_nowait()
                    self._keys_in_reserve.discard(key)
                except asyncio.QueueEmpty:
                    break
                if not self._state.is_key_blocked(key):
                    return key
                self.reserve_queue.put_nowait(key)
                self._keys_in_reserve.add(key)
            return self._get_earliest_recovery_key()

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary; active_keys từ _state."""
        total_keys = len(self._all_keys)
        active_keys = self._state.get_active_key_count()
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "invalid_keys": len(self.invalid_keys),
            "reserve_queue_size": self.reserve_queue.qsize(),
            "error_pools": {name: len(pool) for name, pool in self.error_pools.items()},
            "statistics": self.stats,
        }

    @property
    def api_keys(self) -> List[str]:
        """Compatibility property."""
        return self._all_keys

    def _mask_key(self, key: str) -> str:
        """Mask key for logging (delegated to _state)."""
        return self._state._mask_key(key)

    def get_quota_status_summary(self) -> Dict[str, Any]:
        """Delegate tới _state (translator compatibility)."""
        return self._state.get_quota_status_summary()

    # =========================================================================
    # COMPATIBILITY & DYNAMIC ADJUSTMENT
    # =========================================================================

    async def return_key(
        self,
        worker_id: int,
        key: str,
        is_error: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Trả key sau khi sử dụng. Trạng thái cập nhật qua _state (APIKeyManager).
        """
        await self._state.return_key(
            worker_id, key, is_error, error_type or "", error_message or ""
        )
        self.worker_keys.pop(worker_id, None)
        if is_error and key in self._state.key_statuses and not self._state.key_statuses[key].is_active:
            self.invalid_keys.add(key)
        if not is_error:
            self.reserve_queue.put_nowait(key)
            self._keys_in_reserve.add(key)

    def get_active_key_count(self) -> int:
        """Delegate tới _state."""
        return self._state.get_active_key_count()

    def is_key_blocked(self, key: str) -> bool:
        """Check if key is blocked."""
        return not self._is_key_available(key)

    def is_pro_available(self, key: str) -> bool:
        """Compatibility: Assume active keys support requested model."""
        return self._is_key_available(key)

    def is_flash_available(self, key: str) -> bool:
        """Compatibility."""
        return self._is_key_available(key)

    async def update_allocation(self, num_chunks: int):
        """
        Cập nhật allocation khi biết số lượng chunk thực tế.

        Args:
            num_chunks: Số lượng chunks cần dịch
        """
        with self._lock:
            # Recalculate allocation
            allocation = self._calculate_optimal_workers(num_chunks, len(self._all_keys))
            self.num_chunks = num_chunks

            # Note: Việc re-shuffle và re-assign toàn bộ pools là phức tạp
            # vì các keys đang được hold bởi worker.
            # Ở đây ta chỉ cập nhật stats và đảm bảo reserve queue đủ.

            # Simple rebalancing:
            # Nếu dư workers (workers > chunks), ta có thể thu hồi keys?
            # Hiện tại sticky assignment sẽ giữ key.
            # Nếu thiếu, lần request key tiếp theo sẽ lấy từ pool (nếu còn) hoặc reserve.

            logger.info(
                f"Đã cập nhật phân bổ cho {num_chunks} phân đoạn: "
                f"{allocation['translation_workers']} dịch, "
                f"{allocation['editor_workers']} biên tập, "
                f"{allocation['reserve_keys']} dự phòng"
            )

            # TODO: Implement full rebalancing if strictly needed (reset pools but keep worker_keys)
            # For now, just logging internal state update.

    def get_key_distribution_status(self) -> Dict[str, int]:
        """Return current key distribution counts."""
        return {
            "translation": len(self.translation_keys),
            "editor": len(self.editor_keys),
            "reserve": self.reserve_queue.qsize(),
        }
