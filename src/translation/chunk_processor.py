# -*- coding: utf-8 -*-

"""
Chunk Processor
===============
[Phase 8C] Manages chunk preparation and batch processing.

Extracted from NovelTranslator to reduce translator.py size.

Responsibilities:
- Prepare chunks for translation
- Coordinate batch processing
- Handle chunk validation and filtering
- Manage chunk retry logic coordination

PHIÊN BẢN: v8.0+
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class ChunkProcessor:
    """
    [Phase 8C] Manages chunk preparation and batch processing.
    
    Provides simplified pipeline for chunk-level operations.
    Delegates core translation to translator instance.
    """

    def __init__(
        self,
        chunker: Any,
        progress_manager: Any,
        config: Dict[str, Any],
    ):
        """
        Initialize ChunkProcessor.
        
        Args:
            chunker: SmartChunker instance for chunking.
            progress_manager: ProgressManager instance for tracking.
            config: Configuration dictionary.
        """
        self.chunker = chunker
        self.progress_manager = progress_manager
        self.config = config
        self.performance_config = config.get("performance", {})
        
        # Callbacks to translator methods (set via set_callbacks)
        self._translate_all_chunks: Optional[Callable] = None
        self._retry_failed_chunks: Optional[Callable] = None

    def set_callbacks(
        self,
        translate_all_chunks: Callable,
        retry_failed_chunks: Callable,
    ) -> None:
        """Set callback functions that delegate to translator methods."""
        self._translate_all_chunks = translate_all_chunks
        self._retry_failed_chunks = retry_failed_chunks

    def prepare_chunks(
        self, novel_path: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Prepare chunks from novel file.
        
        Phase 1: Read file, clean text, chunk content.
        
        Args:
            novel_path: Path to novel file.
            config: Configuration dictionary.
            
        Returns:
            Tuple of (all_chunks, cleaned_text) or ([], None) on error.
        """
        # Lazy imports for file parsing
        from src.preprocessing.file_parser import parse_file
        from src.preprocessing.text_cleaner import clean_text

        logger.info(f"Đang đọc và tiền xử lý tệp tiểu thuyết: {novel_path}")
        raw_text = parse_file(novel_path, config)
        cleaned_text = clean_text(raw_text)
        all_chunks = self.chunker.chunk_novel(cleaned_text)

        if len(all_chunks) == 0:
            logger.warning("Không tìm thấy nội dung nào để chia chunk.")
            return [], None

        logger.info(f"📦 Đã chia thành {len(all_chunks)} chunks, sẵn sàng dịch.")
        return all_chunks, cleaned_text

    async def execute_translation(
        self, all_chunks: List[Dict]
    ) -> Tuple[List[Dict], float]:
        """
        Execute translation for all chunks.
        
        Phase 2: Translate chunks and retry failed ones.
        
        Args:
            all_chunks: List of chunks to translate.
            
        Returns:
            Tuple of (failed_chunks, translation_time).
        """
        start_time = time.time()

        # Translate chunks
        failed_chunks = await self._translate_all_chunks(all_chunks)

        # Calculate translation time
        translation_time = time.time() - start_time

        # CRITICAL: Retry failed chunks BEFORE checking and merging
        if failed_chunks:
            logger.warning("")
            logger.warning("=" * 60)
            logger.warning("🔄 PHÁT HIỆN CHUNKS THẤT BẠI - ĐANG THỬ LẠI...")
            logger.warning("=" * 60)

            # Retry failed chunks with exponential backoff
            max_retry_attempts = self.performance_config.get("max_retries_per_chunk", 2)
            retry_result = await self._retry_failed_chunks(
                failed_chunks, all_chunks, max_retry_attempts
            )

            # Update failed_chunks after retry
            failed_chunks = retry_result.get("still_failed", failed_chunks)
            retried_success = retry_result.get("retried_success", 0)

            if retried_success > 0:
                logger.info(f"✅ Đã retry thành công {retried_success} chunks")

        return failed_chunks, translation_time

    def filter_pending_chunks(self, all_chunks: List[Dict]) -> List[Dict]:
        """
        Filter chunks that need translation (not yet completed).
        
        Args:
            all_chunks: All chunks.
            
        Returns:
            List of pending chunks.
        """
        pending_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk.get("global_id") or chunk.get("chunk_id")
            if chunk_id is None:
                continue
            
            # Check if already completed
            chunk_id_str = str(chunk_id)
            if chunk_id_str not in self.progress_manager.completed_chunks:
                pending_chunks.append(chunk)
            
        return pending_chunks

    def get_chunk_batch(
        self, 
        all_chunks: List[Dict], 
        batch_size: int = 10,
        start_index: int = 0
    ) -> List[Dict]:
        """
        Get a batch of chunks for processing.
        
        Args:
            all_chunks: All chunks.
            batch_size: Number of chunks per batch.
            start_index: Starting index.
            
        Returns:
            Batch of chunks.
        """
        end_index = min(start_index + batch_size, len(all_chunks))
        return all_chunks[start_index:end_index]

    def validate_chunks(self, all_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Validate chunks for translation readiness.
        
        Args:
            all_chunks: All chunks.
            
        Returns:
            Validation result with stats.
        """
        valid_count = 0
        invalid_count = 0
        issues = []
        
        for chunk in all_chunks:
            chunk_id = chunk.get("global_id") or chunk.get("chunk_id")
            content = chunk.get("content", "")
            
            if chunk_id is None:
                invalid_count += 1
                issues.append("Chunk missing ID")
                continue
                
            if not content or len(content.strip()) < 10:
                invalid_count += 1
                issues.append(f"Chunk {chunk_id}: content too short")
                continue
                
            valid_count += 1
        
        return {
            "valid": invalid_count == 0,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "issues": issues[:5],  # Limit issues for brevity
            "total": len(all_chunks),
        }
