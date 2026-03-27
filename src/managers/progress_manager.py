# -*- coding: utf-8 -*-
from __future__ import annotations

"""
PHIÊN BẢN v1.7.stable - STABLE (2025-10-27)
=================================================
Module quản lý tiến độ với:
- Metadata tracking (timestamp, model, quality score)
- Compression cho large translations
- Memory-efficient loading
- Backup mechanism
- Chunk file existence check (chunk_file_exists) - ĐÃ SỬA TÊN FILE
- Completed chunks count (get_completed_chunks_count)
- Fix logic kiểm tra file chunk tồn tại
"""

import asyncio
import atexit
import gzip
import json
import logging
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from .progress_state_manager import ProgressStateManager
from src.utils.path_manager import get_progress_dir

logger = logging.getLogger("NovelTranslator")


class ProgressManager:
    """
    Quản lý tiến độ với metadata tracking và compression.
    """

    def __init__(self, config: Dict[str, Any], novel_name: str):
        self.storage_config = config.get("storage", {})
        self.strategy = self.storage_config.get("chunk_storage_strategy", "individual_files")
        self.progress_dir = str(get_progress_dir(config))
        self.novel_name = novel_name
        self.enable_compression = self.storage_config.get("enable_compression", False)
        self.track_metadata = self.storage_config.get("track_metadata", True)

        # OPTIMIZATION 2.2: Batch write buffer với periodic flush
        self._write_buffer: Dict[int, str] = {}

        # Configuration & Validation
        self._validate_and_configure()

        # CRITICAL: Register atexit để flush buffer khi terminate
        # Đảm bảo không mất dữ liệu khi chương trình bị interrupt
        # NOTE: Signal handlers được xử lý ở main.py để tránh conflict
        try:
            atexit.register(self.flush_all)
        except Exception as e:
            logger.debug(f"Không thể register atexit handler: {e}")

        if self.strategy == "individual_files":
            self.chunks_dir = os.path.join(self.progress_dir, f"{self.novel_name}_chunks")
            os.makedirs(self.chunks_dir, exist_ok=True)

            # Metadata directory
            if self.track_metadata:
                self.metadata_dir = os.path.join(self.progress_dir, f"{self.novel_name}_metadata")
                os.makedirs(self.metadata_dir, exist_ok=True)
        else:
            self.progress_file = os.path.join(self.progress_dir, f"{self.novel_name}_progress.json")
            self.metadata_file = os.path.join(self.progress_dir, f"{self.novel_name}_metadata.json")

        self.completed_chunks = self._load_progress()
        self.chunk_metadata = self._load_metadata() if self.track_metadata else {}
        # Chunk draft (partial) lưu tạm, không đưa vào file tổng; chờ key phục hồi để dịch hoàn tất
        self.partial_chunks: Dict[str, str] = self._load_partial_chunks()

        # Phase 1.2: Initialize Progress State Manager (optional, dùng song song)
        progress_state_config = config.get("progress_state", {})
        state_file_path = os.path.join(self.progress_dir, f"{self.novel_name}_state.json")
        self.state_manager = ProgressStateManager(state_file_path, progress_state_config)

        # Sync existing completed chunks vào state manager
        for chunk_id_str, translation in self.completed_chunks.items():
            try:
                chunk_id = int(chunk_id_str)
                self.state_manager.mark_chunk_completed(chunk_id, translation)
            except (ValueError, TypeError):
                pass  # Skip invalid chunk IDs

        # Thread safety và Background saving
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)  # 2 threads cho ghi file

        successful_chunks = len([c for c in self.completed_chunks.values() if c])
        logger.info(f"Đã tải {successful_chunks} chunk đã xử lý, trong đó có {successful_chunks} chunk thành công.")

    def _validate_and_configure(self) -> None:
        """Validate configuration values and set defaults."""
        # Phase 3: Config Validation với type hints
        buffer_size_raw = self.storage_config.get("batch_write_size", 10)
        try:
            self._buffer_size: int = int(buffer_size_raw)
        except (TypeError, ValueError):
            logger.warning(f"batch_write_size không hợp lệ: {buffer_size_raw}. Sử dụng mặc định: 10")
            self._buffer_size = 10

        if self._buffer_size <= 0:
            logger.warning(f"batch_write_size phải là số dương: {self._buffer_size}. Sử dụng mặc định: 10")
            self._buffer_size = 10

        # Periodic flush: Flush buffer mỗi N giây để giảm data loss risk
        flush_interval_raw = self.storage_config.get("flush_interval", 300)
        try:
            self._flush_interval: int = int(flush_interval_raw)
        except (TypeError, ValueError):
            logger.warning(f"flush_interval không hợp lệ: {flush_interval_raw}. Sử dụng mặc định: 300")
            self._flush_interval = 300

        if self._flush_interval <= 0:
            logger.warning(f"flush_interval phải là số dương: {self._flush_interval}. Sử dụng mặc định: 300")
            self._flush_interval = 300

        self._last_flush_time = time.time()  # Track thời gian flush cuối cùng

    def _load_progress(self) -> Dict[str, str]:
        """Load progress với compression support."""
        if self.strategy == "individual_files":
            return self._load_individual_files()
        else:
            return self._load_single_json()

    def _load_individual_files(self) -> Dict[str, str]:
        """Load từ individual files với lazy loading."""
        completed = {}

        if not os.path.exists(self.chunks_dir):
            return completed

        # Only load chunk IDs, not full content (memory efficient)
        for filename in os.listdir(self.chunks_dir):
            if filename.endswith(".txt") or filename.endswith(".txt.gz"):
                chunk_id_str = filename.replace(".txt.gz", "").replace(".txt", "")
                # Store empty string as placeholder - will load on demand
                completed[chunk_id_str] = ""

        logger.info(f"Phát hiện {len(completed)} chunks đã hoàn thành")
        return completed

    def _load_single_json(self) -> Dict[str, str]:
        """Load từ single JSON file."""
        if not os.path.exists(self.progress_file):
            return {}

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Lỗi khi tải tiến độ: {e}")
            return {}

    def _partial_file_path(self) -> str:
        """Đường dẫn file lưu tạm draft (partial) chunks."""
        return os.path.join(self.progress_dir, f"{self.novel_name}_partial.json")

    def _load_partial_chunks(self) -> Dict[str, str]:
        """Load danh sách chunk draft (partial) từ disk. Chỉ lưu tạm, không ghép vào file tổng."""
        path = self._partial_file_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Không tải được partial chunks: {e}")
            return {}

    def _save_partial_chunks(self) -> None:
        """Ghi partial_chunks ra disk."""
        path = self._partial_file_path()
        try:
            with self._lock:
                data = dict(self.partial_chunks)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=0)
        except IOError as e:
            logger.warning(f"Không ghi được partial chunks: {e}")

    def get_partial_chunk_ids(self) -> List[int]:
        """Trả về danh sách chunk_id đang lưu tạm (draft), cần dịch hoàn tất khi có key."""
        with self._lock:
            return [int(k) for k in self.partial_chunks if str(k).isdigit()]

    def _load_metadata(self) -> Dict[str, Dict]:
        """Load metadata cho chunks."""
        if self.strategy == "individual_files":
            metadata = {}
            if os.path.exists(self.metadata_dir):
                for filename in os.listdir(self.metadata_dir):
                    if filename.endswith(".json"):
                        chunk_id = filename.replace(".json", "")
                        filepath = os.path.join(self.metadata_dir, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                metadata[chunk_id] = json.load(f)
                        except Exception:
                            continue
            return metadata
        else:
            if os.path.exists(self.metadata_file):
                try:
                    with open(self.metadata_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return {}
            return {}

    def chunk_file_exists(self, chunk_id: int) -> bool:
        """Kiểm tra xem file chunk có tồn tại không"""
        chunk_id_str = str(chunk_id)

        # Kiểm tra xem chunk có trong completed_chunks không
        if chunk_id_str not in self.completed_chunks:
            return False

        if self.strategy == "individual_files":
            # Kiểm tra file tồn tại (phải khớp với tên file trong save_chunk_result)
            chunk_file = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt")
            chunk_file_gz = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt.gz")
            return os.path.exists(chunk_file) or os.path.exists(chunk_file_gz)
        else:
            # Với single file strategy, nếu trong completed_chunks thì đã tồn tại
            return True

    def get_chunk_translation(self, chunk_id: int) -> Optional[str]:
        """
        Lazy load chunk translation on demand (memory efficient).
        """
        chunk_id_str = str(chunk_id)

        if chunk_id_str not in self.completed_chunks:
            return None

        # If already loaded in memory, return it
        if self.completed_chunks[chunk_id_str]:
            return self.completed_chunks[chunk_id_str]

        # Otherwise, load from disk
        if self.strategy == "individual_files":
            content = self._load_chunk_from_disk(chunk_id_str)
            if content is not None:
                self.completed_chunks[chunk_id_str] = content
                return content

        return None

    def _load_chunk_from_disk(self, chunk_id_str: str) -> Optional[str]:
        """Helper to load chunk content from disk (compressed or plain)."""
        # Try compressed first
        filepath_gz = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt.gz")
        if os.path.exists(filepath_gz):
            try:
                with gzip.open(filepath_gz, "rt", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Không thể đọc chunk nén {chunk_id_str}: {e}")

        # Try uncompressed
        filepath = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Không thể đọc chunk {chunk_id_str}: {e}")

        return None

    async def get_chunk_translation_async(self, chunk_id: int) -> Optional[str]:
        """
        Async version of get_chunk_translation to avoid blocking the event loop.
        """
        return await asyncio.to_thread(self.get_chunk_translation, chunk_id)

    def is_chunk_completed(self, chunk_id: int) -> bool:
        """Check nếu chunk đã completed."""
        return str(chunk_id) in self.completed_chunks

    def save_chunk_result(self, chunk_id: int, translation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save chunk result với metadata tracking và batch writing.

        Nếu metadata.status == "partial": chỉ lưu tạm vào partial_chunks (không đưa vào
        completed_chunks, tuyệt đối không ghép vào file tổng). Chờ key phục hồi để dịch hoàn tất.

        OPTIMIZATION 2.2: Batch writes để giảm I/O operations.
        ENHANCEMENT: Periodic flush để giảm data loss risk.

        Args:
            chunk_id: Chunk ID
            translation: Bản dịch
            metadata: Optional metadata dict với keys:
                - status: "partial" = lưu tạm draft, không merge
                - model, strategy, timestamp, quality_score, retry_count
        """
        chunk_id_str = str(chunk_id)

        # Partial (draft): lưu tạm riêng, không đưa vào completed_chunks / file tổng
        if metadata and metadata.get("status") == "partial":
            with self._lock:
                self.partial_chunks[chunk_id_str] = translation
            self._save_partial_chunks()
            logger.debug(f"Đã lưu tạm draft chunk {chunk_id} (chờ key phục hồi để dịch hoàn tất).")
            return

        # Success: ghi vào completed_chunks; nếu trước đó là partial thì xóa khỏi partial
        need_save_partial = False
        with self._lock:
            if chunk_id_str in self.partial_chunks:
                del self.partial_chunks[chunk_id_str]
                need_save_partial = True
            if self.strategy != "individual_files":
                self._write_buffer[chunk_id] = translation
            self.completed_chunks[chunk_id_str] = translation
        if need_save_partial:
            self._save_partial_chunks()

        # HYBRID SAVING: Lưu file .txt ngay lập tức trong background thread
        # Điều này đảm bảo an toàn dữ liệu nếu crash giữa chừng
        if self.strategy == "individual_files":
            self._executor.submit(self._save_individual_chunk_immediate, chunk_id, translation)

        # Phase 1.2: Sync với Progress State Manager
        try:
            self.state_manager.mark_chunk_completed(chunk_id, translation, metadata)
        except Exception as e:
            logger.debug(f"Lỗi khi sync với state manager: {e}")

        # Phase 2: Edge Cases - Xử lý clock skew và large time differences
        current_time = time.time()
        time_diff = current_time - self._last_flush_time

        # Handle clock skew: Nếu time_diff < 0 (clock đi ngược)
        if time_diff < 0:
            logger.warning(f"Phát hiện lệch đồng hồ: time_diff={time_diff}s. Đặt lại bộ đếm thời gian flush.")
            self._last_flush_time = current_time
            should_flush = len(self._write_buffer) >= self._buffer_size
        elif time_diff > self._flush_interval * 2:
            # Có thể do program pause/resume hoặc clock jump
            logger.debug(f"Phát hiện chênh lệch thời gian lớn: {time_diff}s. Bắt buộc flush.")
            should_flush = True
        else:
            should_flush = len(self._write_buffer) >= self._buffer_size or time_diff >= self._flush_interval

        # Phase 1: Error Handling - Thêm try-except với phân biệt OSError/Exception
        if should_flush:
            try:
                self._flush_buffer()
                self._last_flush_time = current_time
            except OSError as e:
                # File system errors (disk full, permission, etc.)
                logger.error(f"Lỗi I/O khi flush buffer: {e}", exc_info=True)
                # Không update _last_flush_time → sẽ retry tự động ở lần tiếp theo
            except Exception as e:
                # Unexpected errors
                logger.error(f"Lỗi không mong đợi khi flush buffer: {e}", exc_info=True)
                # Không update _last_flush_time → sẽ retry tự động ở lần tiếp theo

    def _flush_buffer(self) -> None:
        """
        OPTIMIZATION 2.2: Write tất cả chunks trong buffer với atomic writes và backup.
        ENHANCEMENT: Atomic writes với backup mechanism để đảm bảo data integrity.

        Returns:
            None
        """
        if not self._write_buffer:
            return

        # Phase 3: Record flush metrics
        time.time()
        chunks_to_flush = len(self._write_buffer)

        # Log flush nếu có chunks
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Đang flush buffer: {chunks_to_flush} chunks")

        if self.strategy == "individual_files":
            for chunk_id, translation in self._write_buffer.items():
                chunk_id_str = str(chunk_id)
                self._save_individual_chunk_atomic(chunk_id_str, translation)
        else:
            # OPTIMIZATION 2.2: Atomic write for single file
            self._save_single_json_atomic()

        # Clear buffer chỉ khi tất cả writes thành công (hoặc logic save handle errors)
        self._write_buffer.clear()

        # Phase 1.2: Flush state manager sau khi flush buffer
        try:
            self.state_manager.flush()
        except Exception as e:
            logger.debug(f"Lỗi khi flush state manager: {e}")

    def _save_individual_chunk_atomic(self, chunk_id_str: str, translation: str) -> None:
        """Helper để save individual chunk atomic."""
        try:
            # Ensure directory exists
            os.makedirs(self.chunks_dir, exist_ok=True)
            if self.enable_compression and len(translation) > 5000:
                # Compressed file
                final_filepath = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt.gz")
                temp_filepath = final_filepath + (".tmp")
                backup_filepath = final_filepath + ".bak"

                # Write to temp file
                with gzip.open(temp_filepath, "wt", encoding="utf-8") as f:
                    f.write(translation)

                # Verify data integrity
                temp_size = os.path.getsize(temp_filepath)
                if temp_size == 0:
                    raise ValueError(f"Temp file is empty: {temp_filepath}")

                # Backup existing file
                if os.path.exists(final_filepath):
                    try:
                        shutil.copy2(final_filepath, backup_filepath)
                    except (OSError, IOError) as backup_error:
                        logger.warning(f"Could not create backup: {backup_error}")

                # Atomic rename
                os.replace(temp_filepath, final_filepath)

                # Cleanup old backup
                if os.path.exists(backup_filepath):
                    backup_age = time.time() - os.path.getmtime(backup_filepath)
                    if backup_age > 3600:
                        try:
                            os.remove(backup_filepath)
                        except OSError:
                            pass
            else:
                # Normal file
                final_filepath = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt")
                temp_filepath = final_filepath + ".tmp"
                backup_filepath = final_filepath + ".bak"

                # Write to temp file
                with open(temp_filepath, "w", encoding="utf-8") as f:
                    f.write(translation)

                # Verify data integrity
                temp_size = os.path.getsize(temp_filepath)
                if temp_size == 0:
                    raise ValueError(f"Temp file is empty: {temp_filepath}")

                # Backup existing file
                if os.path.exists(final_filepath):
                    try:
                        shutil.copy2(final_filepath, backup_filepath)
                    except (OSError, IOError) as backup_error:
                        logger.warning(f"Could not create backup: {backup_error}")

                # Atomic rename
                os.replace(temp_filepath, final_filepath)

                # Cleanup old backup
                if os.path.exists(backup_filepath):
                    backup_age = time.time() - os.path.getmtime(backup_filepath)
                    if backup_age > 3600:
                        try:
                            os.remove(backup_filepath)
                        except OSError:
                            pass

            # Update completed_chunks dict
            self.completed_chunks[chunk_id_str] = translation

        except (OSError, IOError, ValueError) as write_error:
            logger.error(f"Error writing chunk {chunk_id_str}: {write_error}", exc_info=True)
            raise

    def _save_single_json_atomic(self) -> None:
        """
        Atomic write cho single JSON file mode.
        """
        try:
            # Atomic write: write to temp file first, then rename
            temp_filepath = self.progress_file + ".tmp"
            backup_filepath = self.progress_file + ".bak"

            # Serialize
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(self.completed_chunks, f, indent=2, ensure_ascii=False)

            # Verify
            if os.path.getsize(temp_filepath) == 0:
                raise ValueError(f"Temp file empty: {temp_filepath}")

            # Backup
            if os.path.exists(self.progress_file):
                try:
                    shutil.copy2(self.progress_file, backup_filepath)
                except Exception as e:
                    logger.warning(f"Backup failed: {e}")

            # Rename
            os.replace(temp_filepath, self.progress_file)

            logger.debug(f"Đã lưu tiến độ vào {self.progress_file}")

        except Exception as e:
            logger.error(f"Lỗi khi lưu progress JSON đơn: {e}", exc_info=True)
            raise

    def flush_all(self) -> None:
        """
        OPTIMIZATION 2.2: Flush tất cả chunks còn lại trong buffer.

        CRITICAL: Method này được gọi trong:
        - finally block của _translate_all_chunks()
        - signal handler (SIGTERM/SIGINT)
        - atexit handler

        Returns:
            None
        """
        try:
            self._flush_buffer()
        except Exception as e:
            logger.error(f"Lỗi khi flush all buffers: {e}", exc_info=True)

        # Phase 1.2: Flush state manager
        try:
            self.state_manager.flush()
        except Exception as e:
            logger.debug(f"Lỗi khi flush state manager: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics về progress."""
        total_chunks = len(self.completed_chunks)

        if not self.track_metadata or not self.chunk_metadata:
            return {"total_chunks": total_chunks, "completed_chunks": total_chunks}

        # Analyze metadata
        strategies = {}
        models = {}
        total_quality = 0
        quality_count = 0
        total_retries = 0

        for chunk_meta in self.chunk_metadata.values():
            strategy = chunk_meta.get("strategy", "unknown")
            strategies[strategy] = strategies.get(strategy, 0) + 1

            model = chunk_meta.get("model", "unknown")
            models[model] = models.get(model, 0) + 1

            if chunk_meta.get("quality_score") is not None:
                total_quality += chunk_meta["quality_score"]
                quality_count += 1

            total_retries += chunk_meta.get("retry_count", 0)

        avg_quality = total_quality / quality_count if quality_count > 0 else None

        return {
            "total_chunks": total_chunks,
            "completed_chunks": total_chunks,
            "strategies": strategies,
            "models": models,
            "average_quality_score": avg_quality,
            "total_retries": total_retries,
        }

    def create_backup(self):
        """Create backup của progress hiện tại."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.progress_dir, f"backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)

        if self.strategy == "individual_files":
            import shutil

            shutil.copytree(self.chunks_dir, os.path.join(backup_dir, "chunks"))
            if self.track_metadata:
                shutil.copytree(self.metadata_dir, os.path.join(backup_dir, "metadata"))
        else:
            import shutil

            if os.path.exists(self.progress_file):
                shutil.copy2(self.progress_file, backup_dir)
            if os.path.exists(self.metadata_file):
                shutil.copy2(self.metadata_file, backup_dir)

        logger.info(f"✓ Đã tạo backup tại: {backup_dir}")

    def get_completed_chunks_count(self) -> int:
        """Trả về số lượng chunks đã hoàn thành"""
        return len(self.completed_chunks)

    def _save_individual_chunk_immediate(self, chunk_id: int, translation: str) -> None:
        """
        Lưu một chunk duy nhất ngay lập tức (Hybrid Saving).
        Hàm này thường được gọi từ ThreadPoolExecutor.
        """
        chunk_id_str = str(chunk_id)
        if self.strategy != "individual_files":
            return

        try:
            # Ensure directory exists (may have been cleaned between init and background write)
            os.makedirs(self.chunks_dir, exist_ok=True)

            # Atomic write với .tmp file
            final_filepath = os.path.join(self.chunks_dir, f"{chunk_id_str}.txt")
            if self.enable_compression and len(translation) > 5000:
                final_filepath += ".gz"
                temp_filepath = final_filepath + ".tmp"
                with gzip.open(temp_filepath, "wt", encoding="utf-8") as f:
                    f.write(translation)
            else:
                temp_filepath = final_filepath + ".tmp"
                with open(temp_filepath, "w", encoding="utf-8") as f:
                    f.write(translation)

            # Atomic rename
            if os.path.exists(temp_filepath):
                os.replace(temp_filepath, final_filepath)
        except Exception as e:
            # Log lỗi nhưng không chặn luồng chính
            logger.error(f"Error in hybrid saving for chunk {chunk_id}: {e}")
