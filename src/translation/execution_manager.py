# -*- coding: utf-8 -*-

"""
ExecutionManager: Quản lý việc thực thi dịch thuật, điều phối workers và xử lý retry.
Tách biệt khỏi God Object NovelTranslator.
"""

import asyncio
import logging
import random
from typing import Any, Dict, List

from tqdm import tqdm

logger = logging.getLogger("NovelTranslator")


class ExecutionManager:
    def __init__(self, resources: Dict[str, Any], config: Dict[str, Any]):
        self.resources = resources
        self.config = config
        self.performance_config = config.get("performance", {})

        # [NUCLEAR DEBUG] Verify injected config
        logger.info(
            f"🚨 [DEBUG_EXEC] max_parallel_workers from performance_config: {self.performance_config.get('max_parallel_workers', 'NOT FOUND')}"
        )
        logger.info(f"🚨 [DEBUG_EXEC] full config keys: {list(config.keys())}")

        # DEBUG INIT [Turbo Scaling Investigation]
        logger.info(
            f"DEBUG_INIT: performance_config_keys={list(self.performance_config.keys())}, max_parallel_workers={self.performance_config.get('max_parallel_workers')}"
        )

        # Shortcuts to resources
        self.key_manager = resources["key_manager"]
        self.progress_manager = resources["progress_manager"]
        self.metrics_collector = resources["metrics_collector"]

        # Phase 6: Adaptive Scaling
        self._admission_lock = asyncio.Lock()
        self._active_workers_count = 0

        # Phase 7: Throughput Controller
        self._last_scaling_check = 0.0
        self._scaling_check_interval = 30.0  # Check every 30 seconds
        self._current_scaling_factor = 1.0  # 1.0 = full speed, 0.5 = half speed
        self._slow_start_mode = False
        self._slow_start_factor = 0.3  # Start at 30% capacity after recovery

        # Phase 13: Segment-Parallel (Option H+)
        self._chunk_events: Dict[int, asyncio.Event] = {}
        self._context_lag_window = config.get("translation", {}).get("context_lag_window", 3)
        # Tránh kẹt vô hạn: timeout toàn bộ 1 lần dịch 1 chunk và timeout chờ dependency
        self._translation_task_timeout = self.performance_config.get("translation_task_timeout", 900)
        self._segment_wait_timeout = self.performance_config.get("segment_wait_timeout", 300)

    async def _check_admission(self) -> bool:
        """
        [Phase 6] Kiểm tra xem worker có được phép chạy không dựa trên số lượng Active Keys.
        """
        active_keys = self.key_manager.get_active_key_count()
        # Nếu active_keys = 0, vẫn cho phép tối thiểu 1 worker để retry
        max(1, active_keys)

        # Simple admission: Nếu số worker đang active < limit -> OK
        # Nhưng ở đây ta không track global active workers realtime chính xác tuyệt đối mà chỉ estimate.
        # Với mô hình affinity, nếu key chết -> worker tự sleep.
        # Nhưng ta muốn worker detect "System Unhealthy" để giãn cách thêm.

        # Logic:
        # Nếu (current_active_workers > active_keys) -> Xác suất bị reject cao.
        # Nhưng worker hiện tại đang giữ 1 slot.

        # Simplified Logic for Phase 6:
        # Worker chỉ chạy nếu tỉ lệ Blocked Keys < 50%.
        # Hoặc worker check chính key của mình.

        # Let's trust the "Worker-Key Affinity" + "Token Bucket".
        # Additional Adaptive Logic:
        # Nếu system health thấp (< 3 keys), tăng delay giữa các chunks.
        return True

    async def _acquire_admission(self):
        """Wait until system is healthy enough."""
        while True:
            active_keys = self.key_manager.get_active_key_count()
            total_keys = len(self.key_manager.api_keys)

            health_ratio = active_keys / max(1, total_keys)

            if health_ratio < 0.3:  # Critical health (<30%)
                await asyncio.sleep(5)
                # Phase 7: Enter slow start mode when recovering
                self._slow_start_mode = True
            elif health_ratio < 0.6:  # Warning health
                await asyncio.sleep(1)
            else:
                # Health is good, check if we need to exit slow start
                if self._slow_start_mode and health_ratio > 0.7:
                    logger.info("📈 System health recovered. Exiting Slow Start mode.")
                    self._slow_start_mode = False

            return

    # =========================================================================
    # Phase 7.1: Throughput Controller
    # =========================================================================

    def _calculate_optimal_workers(self) -> int:
        """
        [Phase 7.1] Calculate optimal number of workers based on system health.

        Uses MetricsCollector data to dynamically adjust throughput.
        """
        import time

        # Get metrics
        stats = self.metrics_collector.get_statistics() if self.metrics_collector else {}

        # Base worker count from config
        max_workers = self.performance_config.get("max_parallel_workers", 4)
        active_keys = self.key_manager.get_active_key_count()

        # DEBUG LOG [Turbo Scaling Investigation]
        logger.debug(
            f"DEBUG_WORKERS: max_workers_from_config={max_workers}, active_keys_from_manager={active_keys}, performance_config_keys={list(self.performance_config.keys())}"
        )

        base_workers = min(max_workers, active_keys)

        if not stats or stats.get("chunk_count", 0) == 0:
            return base_workers

        # Factor 1: Success rate
        success_rate = stats.get("success_rate", 1.0)

        # Factor 2: 429 error rate (Quota/Rate Limit)
        error_types = stats.get("error_types", {})
        total_chunks = stats.get("chunk_count", 1)
        quota_errors = (
            error_types.get("quota_exceeded", 0) + error_types.get("rate_limit", 0) + error_types.get("429", 0)
        )
        quota_error_rate = quota_errors / max(1, total_chunks)

        # Calculate scaling factor
        scaling_factor = 1.0

        # Reduce if success rate is low
        if success_rate < 0.8:
            scaling_factor *= 0.5
            logger.debug(f"Throughput Controller: Low success rate ({success_rate:.1%}), reducing to 50%")
        elif success_rate < 0.95:
            scaling_factor *= 0.75

        # Reduce significantly if quota errors are high
        if quota_error_rate > 0.1:  # >10% quota errors
            scaling_factor *= 0.3
            logger.warning(f"Throughput Controller: High quota error rate ({quota_error_rate:.1%}), reducing to 30%")
        elif quota_error_rate > 0.05:  # >5% quota errors
            scaling_factor *= 0.5

        # Apply slow start if recovering
        if self._slow_start_mode:
            scaling_factor *= self._slow_start_factor
            logger.debug(f"Throughput Controller: Slow Start mode active, factor={self._slow_start_factor}")

        self._current_scaling_factor = scaling_factor

        # Calculate final worker count
        optimal_workers = max(1, int(base_workers * scaling_factor))

        return optimal_workers

    def _check_system_health(self) -> Dict[str, Any]:
        """
        [Phase 7.3] Inline system health check.

        Returns:
            Dict with health status and recommendations.
        """
        active_keys = self.key_manager.get_active_key_count()
        total_keys = len(self.key_manager.api_keys)
        health_ratio = active_keys / max(1, total_keys)

        stats = self.metrics_collector.get_statistics() if self.metrics_collector else {}
        success_rate = stats.get("success_rate", 1.0)

        # Determine health status
        if health_ratio < 0.3 or success_rate < 0.5:
            status = "critical"
        elif health_ratio < 0.6 or success_rate < 0.8:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "active_keys": active_keys,
            "total_keys": total_keys,
            "key_health_ratio": health_ratio,
            "success_rate": success_rate,
            "scaling_factor": self._current_scaling_factor,
            "slow_start_mode": self._slow_start_mode,
        }

    async def translate_all(self, all_chunks: List[Dict[str, Any]], translator_instance: Any):
        """
        [Phase 7] Điều phối quá trình dịch sử dụng Dynamic Queue (Work Stealing).
        """
        chunks_to_translate = [c for c in all_chunks if not self.progress_manager.is_chunk_completed(c["global_id"])]
        chunks_to_translate_count = len(chunks_to_translate)

        if chunks_to_translate_count == 0:
            logger.info("✅ Tất cả phân đoạn đã được dịch từ trước!")
            return []

        logger.info(f"🚀 Bắt đầu dịch {chunks_to_translate_count}/{len(all_chunks)} phân đoạn với Dynamic Queue...")

        # Setup Queue (Priority by Chunk ID)
        queue = asyncio.PriorityQueue()
        for chunk in chunks_to_translate:
            # Priority = chunk_id (nhỏ làm trước để giữ mạch)
            # Item = (priority, chunk)
            await queue.put((chunk["global_id"], chunk))

        translated_chunks_map = self.progress_manager.completed_chunks.copy()
        failed_chunks = []

        # Phase 7.1: Use Throughput Controller for dynamic worker count
        optimal_workers = self._calculate_optimal_workers()
        all_keys = self.key_manager.api_keys
        num_workers = min(optimal_workers, len(all_keys))

        # Log health status
        health = self._check_system_health()
        logger.info(
            f"🚀 Chiến lược: Dynamic Queue + Throughput Controller | "
            f"{num_workers} workers (scaling={self._current_scaling_factor:.0%})"
        )
        if health["status"] != "healthy":
            logger.warning(
                f"⚠️ Trạng thái hệ thống: {health['status'].upper()} | "
                f"Keys: {health['active_keys']}/{health['total_keys']} | "
                f"Tỷ lệ thành công: {health['success_rate']:.1%}"
            )

        # Setup Progress Bar
        # FIX: Removed TqdmToLogger to prevent duplicate/spam logs

        # Phase 13: Option H+ Segment Discovery
        segments = self._split_into_segments(chunks_to_translate)
        logger.info(f"📦 Tài liệu được chia thành {len(segments)} segments để tối ưu ngữ cảnh.")

        # Initialize Events for all chunks in this session
        self._chunk_events = {c["global_id"]: asyncio.Event() for c in chunks_to_translate}

        with tqdm(total=chunks_to_translate_count, desc="Tiến độ dịch", mininterval=1.0) as pbar:
            workers = []
            for i in range(num_workers):
                worker_task = asyncio.create_task(
                    self._context_aware_worker(
                        worker_id=i,
                        queue=queue,
                        all_chunks=all_chunks,
                        translated_chunks_map=translated_chunks_map,
                        pbar=pbar,
                        failed_chunks=failed_chunks,
                        translator_instance=translator_instance,
                        segments=segments,
                    )
                )
                workers.append(worker_task)

            if workers:
                await asyncio.gather(*workers)

        return failed_chunks

    async def _context_aware_worker(
        self,
        worker_id: int,
        queue: asyncio.PriorityQueue,
        all_chunks: List[Dict[str, Any]],
        translated_chunks_map: Dict[str, str],
        pbar: Any,
        failed_chunks: List[Dict[str, Any]],
        translator_instance: Any,
        segments: List[List[Dict[str, Any]]] = None,
    ):
        """
        [Phase 7] Worker lấy chunk từ Queue và xử lý với Context Awareness.
        """
        # Jitter startup
        jitter_config = self.performance_config.get("startup_jitter", {})
        await asyncio.sleep(random.uniform(jitter_config.get("min", 0.1), jitter_config.get("max", 1.5)))

        # Gán key cố định (Affinity)
        api_key = await self.key_manager.get_key_for_worker(worker_id)

        while not queue.empty():
            # [Phase 6] Adaptive Admission & Pacing
            await self._acquire_admission()

            try:
                # Non-blocking get incase another worker emptied queue
                _, chunk = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            chunk_id = chunk["global_id"]

            # [Phase 13] Sliding Window logic (Option H+)
            current_segment = None
            idx_in_segment = -1
            segment_id = -1

            if segments:
                for s_idx, seg in enumerate(segments):
                    for i, c in enumerate(seg):
                        if c["global_id"] == chunk_id:
                            current_segment = seg
                            idx_in_segment = i
                            segment_id = s_idx
                            break
                    if current_segment:
                        break

            # Internal helper for translation with retries
            async def translate_chunk(current_api_key):
                nonlocal api_key
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    if not current_api_key or self.key_manager.is_key_blocked(current_api_key):
                        logger.debug(f"Worker {worker_id} key bị block. Đang chờ trong hàng đợi...")
                        current_api_key = await self._wait_for_available_key(worker_id)
                        api_key = current_api_key

                    cache_name = translator_instance.worker_caches.get(current_api_key)

                    try:
                        global_index = next((idx for idx, c in enumerate(all_chunks) if c["global_id"] == chunk_id), -1)
                        original_context, translated_context = translator_instance._get_context_chunks(
                            global_index, all_chunks, translated_chunks_map
                        )

                        result = await translator_instance._translate_one_chunk_worker(
                            chunk,
                            original_context,
                            translated_context,
                            worker_id=worker_id,
                            api_key=current_api_key,
                            cache_name=cache_name,
                        )

                        if result and result.get("status") == "success":
                            translation = result["translation"]
                            translated_chunks_map[str(chunk_id)] = translation
                            self.progress_manager.save_chunk_result(chunk_id, translation)
                            if chunk_id in self._chunk_events:
                                self._chunk_events[chunk_id].set()
                            pbar.update(1)
                            queue.task_done()
                            return True
                        # partial: draft chỉ lưu tạm, không ghép vào file tổng
                        if result and result.get("status") == "partial":
                            # [v9.1.3] Don't append to failed_chunks here, wait for retry or final executor status
                            # failed_chunks.append(result or {"chunk_id": chunk_id, "status": "partial"})
                            if chunk_id in self._chunk_events:
                                self._chunk_events[chunk_id].set()
                            pbar.update(1)
                            queue.task_done()
                            return False
                        else:
                            retry_count += 1
                            if retry_count < max_retries:
                                await asyncio.sleep(2**retry_count)
                            else:
                                failed_chunks.append(
                                    result or {"chunk_id": chunk_id, "status": "failed", "error": "Unknown"}
                                )
                                if chunk_id in self._chunk_events:
                                    self._chunk_events[chunk_id].set()
                                pbar.update(1)
                                queue.task_done()
                                return False
                    except Exception as e:
                        logger.error(f"Worker {worker_id} lỗi tại phân đoạn {chunk_id}: {e}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            if chunk_id in self._chunk_events:
                                self._chunk_events[chunk_id].set()
                            pbar.update(1)
                            queue.task_done()
                            return False
                        await asyncio.sleep(5)
                return False

            if current_segment:
                if not hasattr(self, "_segment_sems"):
                    self._segment_sems = {}
                if segment_id not in self._segment_sems:
                    self._segment_sems[segment_id] = asyncio.Semaphore(self._context_lag_window + 1)

                async with self._segment_sems[segment_id]:
                    if idx_in_segment >= self._context_lag_window:
                        dependency_chunk = current_segment[idx_in_segment - self._context_lag_window]
                        dep_id = dependency_chunk["global_id"]
                        if dep_id in self._chunk_events and not self._chunk_events[dep_id].is_set():
                            try:
                                await asyncio.wait_for(
                                    self._chunk_events[dep_id].wait(),
                                    timeout=self._segment_wait_timeout,
                                )
                            except asyncio.TimeoutError:
                                logger.warning(
                                    f"Worker {worker_id} hết thời gian chờ Phân đoạn {dep_id}. Sử dụng context tốt nhất có thể."
                                )

                    if not self.progress_manager.is_chunk_completed(chunk_id):
                        try:
                            await asyncio.wait_for(
                                translate_chunk(api_key),
                                timeout=self._translation_task_timeout,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Worker {worker_id} timeout dịch chunk {chunk_id} sau {self._translation_task_timeout}s. Đưa vào failed để retry."
                            )
                            failed_chunks.append(
                                {
                                    "chunk_id": chunk_id,
                                    "status": "timeout",
                                    "error": f"Timeout after {self._translation_task_timeout}s",
                                }
                            )
                            if chunk_id in self._chunk_events:
                                self._chunk_events[chunk_id].set()
                            pbar.update(1)
                            queue.task_done()
                    else:
                        pbar.update(1)
                        queue.task_done()
            else:
                if not self.progress_manager.is_chunk_completed(chunk_id):
                    try:
                        await asyncio.wait_for(
                            translate_chunk(api_key),
                            timeout=self._translation_task_timeout,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Worker {worker_id} timeout dịch chunk {chunk_id} sau {self._translation_task_timeout}s."
                        )
                        # [v9.1.3] Check again if completed before appending to failed
                        if not self.progress_manager.is_chunk_completed(chunk_id):
                            failed_chunks.append(
                                {
                                    "chunk_id": chunk_id,
                                    "status": "timeout",
                                    "error": f"Timeout after {self._translation_task_timeout}s",
                                }
                            )
                        if chunk_id in self._chunk_events:
                            self._chunk_events[chunk_id].set()
                        pbar.update(1)
                        queue.task_done()
                else:
                    pbar.update(1)
                    queue.task_done()

    async def _wait_for_available_key(self, worker_id: int) -> str:
        """Đợi cho đến khi có API key khả dụng cho worker."""
        wait_time = 0
        max_wait = 3600  # 1 hour max

        while wait_time < max_wait:
            # Ưu tiên lấy key từ pool (tránh dùng lại key vừa 429/quota sau cooldown)
            # [v9.1] get_available_key now async
            shared_key = await self.key_manager.get_available_key()
            if shared_key:
                logger.debug(f"Worker {worker_id} lấy key từ pool (ưu tiên xoay key sau lỗi).")
                return shared_key

            # Fallback: key cố định theo worker (affinity)
            api_key = await self.key_manager.get_key_for_worker(worker_id)
            if api_key and not self.key_manager.is_key_blocked(api_key):
                return api_key

            # Đợi
            sleep_interval = 15 + random.uniform(1, 5)
            logger.debug(f"Worker {worker_id} still waiting for key... ({wait_time}s elapsed)")
            await asyncio.sleep(sleep_interval)
            wait_time += sleep_interval

            # [Fix User Request] Log periodic status if waiting too long
            if wait_time > 60 and int(wait_time) % 60 < 20:  # Log roughly every minute
                active = self.key_manager.get_active_key_count()
                total = len(self.key_manager.api_keys)
                logger.warning(
                    f"Worker {worker_id} waiting >{int(wait_time)}s. Pool Health: {active}/{total} keys active."
                )

        raise RuntimeError(f"Worker {worker_id} timed out waiting for an available API key.")

    def _split_into_segments(self, chunks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        [Phase 13] Chia danh sách chunks thành các segments dựa trên natural breaks.
        """
        from .context_break_detector import ContextBreakDetector

        detector = ContextBreakDetector(self.config if hasattr(self, "config") else {})

        segments = []
        current_segment = []

        for i, chunk in enumerate(chunks):
            if i > 0:
                prev_chunk = chunks[i - 1]
                if detector.detect(prev_chunk.get("text", ""), chunk.get("text", "")):
                    if current_segment:
                        segments.append(current_segment)
                        current_segment = []

            current_segment.append(chunk)

        if current_segment:
            segments.append(current_segment)

        return segments
