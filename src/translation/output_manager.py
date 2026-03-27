# -*- coding: utf-8 -*-

"""
Output Manager
==============
[Phase 8A] Manages output generation, chunk merging, and finalization.

Extracted from NovelTranslator to reduce translator.py size.

Responsibilities:
- Merge translated chunks into final content
- Validate chunk continuity and markers
- Generate completion reports
- Coordinate finalization workflow

PHIÊN BẢN: v8.0+
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class OutputManager:
    """
    [Phase 8A] Manages output generation and chunk merging.
    
    Handles:
    - Chunk merging and validation
    - Completion report generation
    - Finalization workflow coordination
    
    Uses delegation pattern for complex operations requiring translator context.
    """

    def __init__(
        self,
        progress_manager: Any,
        output_formatter: Any,
        novel_name: str,
        config: Dict[str, Any],
        translator_instance: Optional[Any] = None,
    ):
        """
        Initialize OutputManager.
        
        Args:
            progress_manager: ProgressManager instance for chunk tracking.
            output_formatter: OutputFormatter instance for saving files.
            novel_name: Name of the novel being translated.
            config: Configuration dictionary.
            translator_instance: Optional NovelTranslator for delegation (set later).
        """
        self.progress_manager = progress_manager
        self.output_formatter = output_formatter
        self.novel_name = novel_name
        self.config = config
        self.performance_config = config.get("performance", {})
        self._translator = translator_instance
        
        # Compiled regex patterns cache for marker validation
        self._marker_patterns_cache: Dict[int, Tuple[re.Pattern, re.Pattern]] = {}
        
        # Marker format from config
        chunking_config = config.get("preprocessing", {}).get("chunking", {})
        self.use_markers = chunking_config.get("use_markers", True)
        self.marker_format = chunking_config.get("marker_format", "simple")
    
    def set_translator(self, translator_instance: Any) -> None:
        """Set translator instance for delegation."""
        self._translator = translator_instance


    async def generate_completion_report(
        self,
        all_chunks: List[Dict],
        failed_chunks: List[Dict],
        translation_time: float,
        is_success: bool = True,
    ) -> None:
        """
        Generate translation completion report.
        
        Args:
            all_chunks: All chunks (translated and failed).
            failed_chunks: List of failed chunks.
            translation_time: Translation duration in seconds.
            is_success: True if fully successful, False otherwise.
        """
        completed_chunks = self.progress_manager.get_completed_chunks_count()
        total_chunks = len(all_chunks)
        success_rate = (
            (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0
        )

        # Format time
        hours = int(translation_time // 3600)
        minutes = int((translation_time % 3600) // 60)
        seconds = int(translation_time % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        # Report header
        logger.info("=" * 60)
        
        # Ensure failed_chunks is a list
        if failed_chunks is None:
            failed_chunks = []
        missing_count = total_chunks - completed_chunks

        # Determine success status
        if (
            is_success
            and len(failed_chunks) == 0
            and missing_count == 0
            and completed_chunks == total_chunks
        ):
            logger.info("🎉 HOÀN THÀNH DỊCH THUẬT - 100% thành công")
        else:
            if missing_count > 0:
                logger.error(
                    f"❌ KHÔNG HOÀN TẤT - {missing_count} chunks thiếu/thất bại ({100 - success_rate:.0f}%)"
                )
            else:
                logger.error(
                    f"❌ KHÔNG HOÀN TẤT - {len(failed_chunks)} chunks thất bại ({100 - success_rate:.0f}%)"
                )
        
        logger.info(
            f"⏱️  Thời gian: {time_str} | 📊 Tổng: {total_chunks} | "
            f"✅ Hoàn thành: {completed_chunks} | ❌ Thất bại: {len(failed_chunks)} | "
            f"📈 Tỷ lệ: {success_rate:.0f}%"
        )

        if failed_chunks:
            failed_chunk_ids = [
                c.get("chunk_id") for c in failed_chunks if c.get("chunk_id")
            ]
            failed_ids_str = str(failed_chunk_ids[:5])
            if len(failed_chunk_ids) > 5:
                failed_ids_str += f", ... (+{len(failed_chunk_ids) - 5} more)"
            logger.error(f"📋 Chunks thất bại: {failed_ids_str}")
            
            if logger.isEnabledFor(logging.DEBUG):
                for i, chunk_id in enumerate(failed_chunk_ids, 1):
                    logger.debug(f"  {i}. Chunk {chunk_id}")

        logger.info("=" * 60)

    async def sync_completed_chunks(self, all_chunks: List[Dict]) -> Dict[str, str]:
        """
        Sync completed_chunks with files on disk (file-first approach).
        
        Args:
            all_chunks: List of all chunks.
            
        Returns:
            Dictionary containing synced chunks with content.
        """
        synced_chunks: Dict[str, str] = {}
        
        for chunk in all_chunks:
            chunk_id = chunk.get("global_id") or chunk.get("chunk_id")
            if chunk_id is None:
                continue
                
            # Check if chunk file exists and load content
            content = self.progress_manager.get_chunk_content(chunk_id)
            if content:
                synced_chunks[str(chunk_id)] = content
                
        return synced_chunks

    async def parallel_load_chunks(
        self,
        all_chunks: List[Dict],
        synced_chunks: Dict[str, str],
        max_concurrent: int = 10,
    ) -> List[Tuple[Dict, str]]:
        """
        Load chunks from disk in parallel with semaphore.
        
        Args:
            all_chunks: List of all chunks.
            synced_chunks: Already synced chunks.
            max_concurrent: Maximum concurrent loads.
            
        Returns:
            List of (chunk, content) tuples.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results: List[Tuple[Dict, str]] = []
        
        async def load_chunk(chunk: Dict) -> Optional[Tuple[Dict, str]]:
            chunk_id = chunk.get("global_id") or chunk.get("chunk_id")
            if chunk_id is None:
                return None
                
            async with semaphore:
                # Check synced first
                content = synced_chunks.get(str(chunk_id))
                if content:
                    return (chunk, content)
                    
                # Load from disk
                content = self.progress_manager.get_chunk_content(chunk_id)
                if content:
                    return (chunk, content)
                    
                return None
        
        tasks = [load_chunk(chunk) for chunk in all_chunks]
        loaded = await asyncio.gather(*tasks)
        
        for result in loaded:
            if result:
                results.append(result)
                
        return results

    def get_marker_patterns(self, chunk_id: int) -> Tuple[re.Pattern, re.Pattern]:
        """
        Get compiled regex patterns for chunk markers.
        
        Caches patterns to avoid recompilation.
        
        Args:
            chunk_id: ID of the chunk.
            
        Returns:
            Tuple (start_pattern, end_pattern) - compiled regex patterns.
        """
        if chunk_id in self._marker_patterns_cache:
            return self._marker_patterns_cache[chunk_id]
        
        if self.marker_format == "simple":
            # Hỗ trợ cả [CHUNK:id:START] và [CHUNK:anything:id:START] (tránh lỗi do AI tự thêm session ID)
            # re.escape giúp xử lý an toàn nếu id là chuỗi (EPUB)
            escaped_id = re.escape(str(chunk_id))
            start_pattern = re.compile(
                rf"\[CHUNK:(?:[^\]]*?:)?{escaped_id}:START\]", re.IGNORECASE
            )
            end_pattern = re.compile(
                rf"\[CHUNK:(?:[^\]]*?:)?{escaped_id}:END\]", re.IGNORECASE
            )
        else:
            # UUID format
            start_pattern = re.compile(
                rf"\[CHUNK_START:{chunk_id:08X}\]", re.IGNORECASE
            )
            end_pattern = re.compile(
                rf"\[CHUNK_END:{chunk_id:08X}\]", re.IGNORECASE
            )
        
        self._marker_patterns_cache[chunk_id] = (start_pattern, end_pattern)
        return start_pattern, end_pattern

    def validate_with_markers(
        self,
        translated_parts: List[str],
        original_chunks: List[Dict],
        marker_guardrail_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Validate chunks using markers (O(n) - fast).
        
        Args:
            translated_parts: List of translated content.
            original_chunks: Original chunks for reference.
            
        Returns:
            Dict with:
                - valid: True if all chunks have valid markers
                - cleaned_chunks: List of cleaned content (markers removed)
                - suspicious_chunks: List of indices with issues
        """
        if marker_guardrail_enabled is None:
            marker_guardrail_enabled = bool(self.use_markers)

        cleaned_chunks: List[str] = []
        suspicious_chunks: List[int] = []

        if not marker_guardrail_enabled:
            return {
                "valid": True,
                "cleaned_chunks": [content.strip() for content in translated_parts],
                "suspicious_chunks": [],
            }
        
        for idx, (content, chunk) in enumerate(zip(translated_parts, original_chunks)):
            chunk_id = chunk.get("global_id") or chunk.get("chunk_id")
            if chunk_id is None:
                suspicious_chunks.append(idx)
                cleaned_chunks.append(content)
                continue
            
            start_pattern, end_pattern = self.get_marker_patterns(chunk_id)
            
            # Count markers
            start_count = len(start_pattern.findall(content))
            end_count = len(end_pattern.findall(content))
            
            if start_count == 1 and end_count == 1:
                # Valid - remove markers
                cleaned = start_pattern.sub("", content)
                cleaned = end_pattern.sub("", cleaned)
                cleaned_chunks.append(cleaned.strip())
            elif start_count == 0 and end_count == 0:
                # No markers - might be okay for short chunks
                cleaned_chunks.append(content.strip())
            else:
                # Suspicious - multiple or mismatched markers
                suspicious_chunks.append(idx)
                # Still clean what we can
                cleaned = start_pattern.sub("", content)
                cleaned = end_pattern.sub("", cleaned)
                cleaned_chunks.append(cleaned.strip())
        
        return {
            "valid": len(suspicious_chunks) == 0,
            "cleaned_chunks": cleaned_chunks,
            "suspicious_chunks": suspicious_chunks,
        }

    def merge_with_markers(self, cleaned_chunks: List[str]) -> str:
        """
        Merge cleaned chunks with preserved paragraph breaks.
        
        Args:
            cleaned_chunks: List of cleaned chunk content.
            
        Returns:
            Merged content with preserved formatting.
        """
        # Join with double newline for paragraph separation
        merged = "\n\n".join(
            chunk for chunk in cleaned_chunks if chunk.strip()
        )
        
        # Normalize excessive newlines
        merged = re.sub(r"\n{3,}", "\n\n", merged)
        
        return merged.strip()

    def calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """
        Calculate similarity between two sentences (0-1).
        
        Uses simple Jaccard similarity based on words.
        
        Args:
            sent1: First sentence.
            sent2: Second sentence.
            
        Returns:
            Similarity score between 0 and 1.
        """
        words1 = set(sent1.lower().split())
        words2 = set(sent2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
