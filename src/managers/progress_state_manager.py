# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Progress State Manager
======================
Thread-safe progress state management với atomic operations, state persistence,
và checkpoint/resume support.

PHIÊN BẢN: v2.0+
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger("NovelTranslator")


class ProgressStateManager:
    """
    Thread-safe progress state manager với atomic operations.

    Features:
    - Thread-safe state operations
    - Atomic state updates
    - State persistence
    - Checkpoint/resume support
    - State validation và recovery

    Attributes:
        state_file: Path to state file
        _state: Internal state dict
        _lock: Thread lock for thread-safety
        _dirty: Flag to track if state needs saving
    """

    def __init__(self, state_file: str, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo ProgressStateManager.

        Args:
            state_file: Path to state file (JSON)
            config: Optional configuration dict
        """
        self.config = config or {}
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for thread-safety
        self._lock = threading.RLock()

        # Internal state
        self._state: Dict[str, Any] = {
            "completed_chunks": {},  # chunk_id -> translation
            "failed_chunks": set(),  # Set of failed chunk IDs
            "checkpoints": [],  # List of checkpoint timestamps
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": None,
                "version": "2.0+",
            },
        }

        # Dirty flag để track nếu state cần save
        self._dirty = False

        # Auto-save interval (seconds)
        self.auto_save_interval = self.config.get("auto_save_interval", 60)
        self._last_save_time = time.time()

        # Load existing state nếu có
        self._load_state()

        logger.debug(f"Đã khởi tạo ProgressStateManager: {self.state_file}")

    def _load_state(self) -> None:
        """
        Load state từ file.

        Returns:
            None
        """
        if not self.state_file.exists():
            logger.debug(f"State file không tồn tại: {self.state_file}")
            return

        try:
            with self._lock:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded_state = json.load(f)

                # Validate và merge state
                if isinstance(loaded_state, dict):
                    # Merge completed_chunks
                    if "completed_chunks" in loaded_state:
                        self._state["completed_chunks"].update(loaded_state["completed_chunks"])

                    # Merge failed_chunks (convert list to set)
                    if "failed_chunks" in loaded_state:
                        if isinstance(loaded_state["failed_chunks"], list):
                            self._state["failed_chunks"].update(loaded_state["failed_chunks"])
                        elif isinstance(loaded_state["failed_chunks"], set):
                            self._state["failed_chunks"].update(loaded_state["failed_chunks"])

                    # Update metadata
                    if "metadata" in loaded_state:
                        self._state["metadata"].update(loaded_state["metadata"])

                    # Load checkpoints
                    if "checkpoints" in loaded_state:
                        self._state["checkpoints"] = loaded_state["checkpoints"]

                    logger.info(
                        f"Đã tải state: {len(self._state['completed_chunks'])} hoàn thành, "
                        f"{len(self._state['failed_chunks'])} thất bại"
                    )
                else:
                    logger.warning(f"Định dạng file state không hợp lệ: {self.state_file}")

        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.error(f"Lỗi khi tải file state: {e}", exc_info=True)
            # Keep default state nếu load fail

    def _save_state(self, force: bool = False) -> bool:
        """
        Save state to file với atomic write.

        Args:
            force: Force save even if not dirty

        Returns:
            True nếu save thành công, False nếu fail
        """
        if not self._dirty and not force:
            return True

        try:
            with self._lock:
                # Prepare state for serialization
                state_to_save = {
                    "completed_chunks": self._state["completed_chunks"],
                    "failed_chunks": list(self._state["failed_chunks"]),  # Convert set to list
                    "checkpoints": self._state["checkpoints"],
                    "metadata": {
                        **self._state["metadata"],
                        "last_updated": datetime.now().isoformat(),
                    },
                }

                # Atomic write: write to temp file first, then rename
                temp_file = self.state_file.with_suffix(".tmp")

                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(state_to_save, f, indent=2, ensure_ascii=False)

                # Atomic rename
                temp_file.replace(self.state_file)

                self._dirty = False
                self._last_save_time = time.time()

                logger.debug(f"Đã lưu state: {self.state_file}")
                return True

        except (IOError, OSError) as e:
            logger.error(f"Lỗi khi lưu file state: {e}", exc_info=True)
            return False

    def mark_chunk_completed(self, chunk_id: int, translation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark chunk as completed với atomic operation.

        Args:
            chunk_id: Chunk ID
            translation: Translation text
            metadata: Optional metadata
        """
        with self._lock:
            chunk_id_str = str(chunk_id)
            self._state["completed_chunks"][chunk_id_str] = translation

            # Remove from failed nếu có
            if chunk_id in self._state["failed_chunks"]:
                self._state["failed_chunks"].discard(chunk_id)

            # Update metadata nếu có
            if metadata:
                # Store metadata separately (có thể extend sau)
                pass

            self._dirty = True

            # Auto-save nếu đã qua interval
            if time.time() - self._last_save_time >= self.auto_save_interval:
                self._save_state()

    def mark_chunk_failed(self, chunk_id: int, error: Optional[str] = None) -> None:
        """
        Mark chunk as failed với atomic operation.

        Args:
            chunk_id: Chunk ID
            error: Optional error message
        """
        with self._lock:
            self._state["failed_chunks"].add(chunk_id)

            # Remove from completed nếu có
            chunk_id_str = str(chunk_id)
            if chunk_id_str in self._state["completed_chunks"]:
                del self._state["completed_chunks"][chunk_id_str]

            self._dirty = True

            # Auto-save nếu đã qua interval
            if time.time() - self._last_save_time >= self.auto_save_interval:
                self._save_state()

    def is_chunk_completed(self, chunk_id: int) -> bool:
        """
        Check nếu chunk đã completed.

        Args:
            chunk_id: Chunk ID

        Returns:
            True nếu completed, False nếu không
        """
        with self._lock:
            return str(chunk_id) in self._state["completed_chunks"]

    def is_chunk_failed(self, chunk_id: int) -> bool:
        """
        Check nếu chunk đã failed.

        Args:
            chunk_id: Chunk ID

        Returns:
            True nếu failed, False nếu không
        """
        with self._lock:
            return chunk_id in self._state["failed_chunks"]

    def get_completed_chunks(self) -> Dict[str, str]:
        """
        Get all completed chunks.

        Returns:
            Dict[chunk_id, translation]
        """
        with self._lock:
            return dict(self._state["completed_chunks"])

    def get_failed_chunks(self) -> Set[int]:
        """
        Get all failed chunk IDs.

        Returns:
            Set of failed chunk IDs
        """
        with self._lock:
            return set(self._state["failed_chunks"])

    def get_chunk_translation(self, chunk_id: int) -> Optional[str]:
        """
        Get translation cho chunk.

        Args:
            chunk_id: Chunk ID

        Returns:
            Translation text hoặc None nếu không có
        """
        with self._lock:
            return self._state["completed_chunks"].get(str(chunk_id))

    def create_checkpoint(self, description: Optional[str] = None) -> str:
        """
        Create checkpoint với timestamp.

        Args:
            description: Optional checkpoint description

        Returns:
            Checkpoint ID (timestamp)
        """
        with self._lock:
            checkpoint_id = datetime.now().isoformat()
            checkpoint = {
                "id": checkpoint_id,
                "timestamp": time.time(),
                "description": description,
                "completed_count": len(self._state["completed_chunks"]),
                "failed_count": len(self._state["failed_chunks"]),
            }

            self._state["checkpoints"].append(checkpoint)

            # Keep only last N checkpoints (default: 10)
            max_checkpoints = self.config.get("max_checkpoints", 10)
            if len(self._state["checkpoints"]) > max_checkpoints:
                self._state["checkpoints"] = self._state["checkpoints"][-max_checkpoints:]

            self._dirty = True
            self._save_state(force=True)

            logger.debug(f"Đã tạo checkpoint: {checkpoint_id}")
            return checkpoint_id

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get state summary.

        Returns:
            Dict với state summary
        """
        with self._lock:
            return {
                "completed_count": len(self._state["completed_chunks"]),
                "failed_count": len(self._state["failed_chunks"]),
                "checkpoint_count": len(self._state["checkpoints"]),
                "last_checkpoint": (self._state["checkpoints"][-1] if self._state["checkpoints"] else None),
                "metadata": dict(self._state["metadata"]),
            }

    def validate_state(self) -> Tuple[bool, Optional[str]]:
        """
        Validate state consistency.

        Returns:
            Tuple (is_valid, error_message)
        """
        with self._lock:
            # Check completed_chunks và failed_chunks không overlap
            completed_ids = set(int(k) for k in self._state["completed_chunks"].keys())
            failed_ids = self._state["failed_chunks"]

            overlap = completed_ids & failed_ids
            if overlap:
                return (
                    False,
                    f"State không nhất quán: chunks {overlap} vừa hoàn thành vừa thất bại",
                )

            # Check metadata
            if "metadata" not in self._state:
                return False, "Thiếu metadata trong state"

            return True, None

    def recover_state(self) -> bool:
        """
        Recover state nếu có corruption.

        Returns:
            True nếu recovery thành công, False nếu fail
        """
        with self._lock:
            is_valid, error_msg = self.validate_state()

            if is_valid:
                return True

            logger.warning(f"State validation failed: {error_msg}. Attempting recovery...")

            # Recovery strategy: Remove overlaps
            completed_ids = set(int(k) for k in self._state["completed_chunks"].keys())
            failed_ids = self._state["failed_chunks"]

            overlap = completed_ids & failed_ids
            if overlap:
                # Keep completed, remove from failed
                for chunk_id in overlap:
                    self._state["failed_chunks"].discard(chunk_id)
                logger.info(f"Recovered: Removed {len(overlap)} chunks from failed list")

            # Re-validate
            is_valid, error_msg = self.validate_state()
            if is_valid:
                self._dirty = True
                self._save_state(force=True)
                logger.info("State recovery successful")
                return True
            else:
                logger.error(f"State recovery failed: {error_msg}")
                return False

    def flush(self) -> bool:
        """
        Flush state to disk (force save).

        Returns:
            True nếu flush thành công, False nếu fail
        """
        return self._save_state(force=True)

    def clear_state(self) -> None:
        """
        Clear all state (use with caution).

        Returns:
            None
        """
        with self._lock:
            self._state = {
                "completed_chunks": {},
                "failed_chunks": set(),
                "checkpoints": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": None,
                    "version": "2.0+",
                },
            }
            self._dirty = True
            self._save_state(force=True)
            logger.warning("Đã xóa toàn bộ state")
