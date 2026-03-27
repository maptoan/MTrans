# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NovelTranslator")


class QAEditor:
    """
    Handles the Smart Editor Pipeline (PHASE 7.5).
    Responsible for rà soát, sửa lỗi, and CJK repair via API calls.
    """

    def __init__(
        self, config: Dict[str, Any], gemini_service: Any, prompt_builder: Any
    ):
        self.config = config
        self.gemini_service = gemini_service
        self.prompt_builder = prompt_builder

    async def perform_qa_edit(
        self,
        draft_translation: str,
        relevant_terms: List[Dict],
        api_key: str,
        chunk_id: int,
        source_text: str = "",
        cjk_remaining: List[str] = None,
        character_relations: str = "",
        worker_id: Optional[int] = None,
    ) -> str:
        """
        Smart Editor Pipeline.
        """
        if not draft_translation:
            return ""

        # Build prompt for Editor
        style_guide = self.prompt_builder.style_manager.get_style_summary()
        editor_prompt = self.prompt_builder.build_editor_prompt(
            draft_translation=draft_translation,
            glossary_terms=relevant_terms,
            style_guide=style_guide,
            source_text=source_text,
            cjk_remaining=cjk_remaining,
            character_relations=character_relations,
        )

        try:
            # Call Gemini API via service
            response_text = await self.gemini_service.generate_content_async(
                prompt=editor_prompt,
                api_key=api_key,
                chunk_id=chunk_id,
                worker_id=worker_id,
                is_qa_edit=True,
            )

            if response_text:
                # [FIX] Clean reasoning leakage
                cleaned_text = self._clean_qa_response(response_text)
                
                # [VALIDATION] If cleaned text is too short or suspiciously different, reject it
                if self._is_valid_qa_result(cleaned_text, draft_translation):
                    return cleaned_text
                else:
                    logger.warning(
                        f"[Chunk {chunk_id}] QA result failed validation (reasoning leakage or truncation), keeping draft."
                    )
                    return draft_translation

            logger.warning(
                f"[Chunk {chunk_id}] QA Editor trả về kết quả rỗng, giữ nguyên Draft."
            )
            return draft_translation

        except Exception as e:
            logger.error(f"[Chunk {chunk_id}] Lỗi trong quá trình QA Editor: {e}")
            return draft_translation

    def _clean_qa_response(self, text: str) -> str:
        """
        Strips reasoning notes, wait-comments, and conversational filler.
        """
        if not text:
            return ""
            
        lines = text.split('\n')
        cleaned_lines = []
        
        # Patterns to skip (highly aggressive)
        skip_words = [
            "Wait,", "Thinking,", "I should", "Actually,", "Correction:", 
            "Let's check", "Revised:", "Polished:", "Okay,", "Here is",
            "Final output", "Translation:", "Bản dịch:", "Sửa lại:",
            "Wait...", "I will", "Now I", "Hmm,", "Looking at",
            "*Wait", "* (Final", "Wait!", "One more", "I'll", "I'm"
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines at start
            if not stripped and not cleaned_lines:
                continue
                
            # Skip lines starting with specific markers or containing obvious reasoning
            lower_stripped = stripped.lower()
            
            # Skip obvious reasoning lines
            is_reasoning = any(w.lower() in lower_stripped for w in skip_words)
            
            # SPECIAL CASE: If line starts with * and is short, it's almost certainly reasoning
            if stripped.startswith("*") and len(stripped) < 150 and is_reasoning:
                continue
                
            # Skip common "Wait," or "Thinking" lines even if they don't start with *
            if any(lower_stripped.startswith(w.lower()) for w in ["wait,", "thinking,", "correction:", "actually,"]):
                continue

            # Skip lines that are just markdown formatting or AI filler
            if stripped in ["```", "```json", "```msg"]:
                continue

            cleaned_lines.append(line)
            
        result = "\n".join(cleaned_lines).strip()
        
        # Intermediate step: Remove markdown block markers if they were skipped partially
        if result.startswith("```") and "```" in result[3:]:
            # Try to extract content between first and last ```
            parts = result.split("```")
            if len(parts) >= 3:
                result = parts[1].strip()
                # If first block was 'json' or 'markdown', strip it
                if result.startswith("json") or result.startswith("markdown"):
                    result = result.split('\n', 1)[1].strip()
        
        # Final cleanup: Remove [CHUNK:START] markers if AI added them back (redundant) - Support all ID formats
        result = re.sub(r"\[CHUNK:.*?:START\]", "", result)
        result = re.sub(r"\[CHUNK:.*?:END\]", "", result)
        
        return result.strip()

    def _is_valid_qa_result(self, cleaned: str, original: str) -> bool:
        """
        More intelligent quality gate for QA results. Instead of a naive length
        check, it verifies that the cleaned text preserves a significant portion
        of the original's word content.
        """
        if not cleaned:
            return False

        # 1. Placeholder/Thinking check (quick failure)
        if "Wait," in cleaned[:50] or "Thinking" in cleaned[:50]:
            logger.debug("QA result invalid: Contains reasoning markers.")
            return False

        # 2. Word Overlap Check (more robust than simple length)
        try:
            original_words = set(re.findall(r'\w+', original.lower()))
            cleaned_words = set(re.findall(r'\w+', cleaned.lower()))

            if not original_words:
                return True # Original was empty or junk, any cleaned output is fine

            intersection = original_words.intersection(cleaned_words)
            overlap_ratio = len(intersection) / len(original_words)

            # Đọc ngưỡng từ config (fallback = 0.5 nếu không thiết lập)
            default_ratio = 0.5
            qa_cfg = (
                self.config.get("translation", {})
                .get("qa_editor", {})
            )
            try:
                min_overlap = float(qa_cfg.get("min_word_overlap_ratio", default_ratio))
            except (TypeError, ValueError):
                min_overlap = default_ratio

            # The QA result is valid if it contains at least `min_overlap` of the original words.
            # Mức mặc định 0.5 cho phép editor sửa/phrasal lại khá mạnh tay mà vẫn được chấp nhận,
            # giảm bớt false negative cho các bản edit hợp lệ.
            if overlap_ratio < min_overlap:
                logger.warning(
                    f"QA result invalid: Word overlap is too low ({overlap_ratio:.2f}). "
                    "Indicates potential truncation or excessive changes."
                )
                return False

        except Exception as e:
            logger.error(f"Error during QA validation word overlap check: {e}")
            # Fail safe: fall back to a simple length check in case of regex errors
            if len(cleaned) < len(original) * 0.2:
                return False

        return True
