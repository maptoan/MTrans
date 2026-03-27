# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NovelTranslator")


class CJKCleaner:
    """
    Handles complex surgical repair for remaining CJK terms:
    - Sentence-based contextual retry
    - Legacy micro-translation
    - Fallback transliteration
    - Residual tracking (JSONL)
    """

    def __init__(self, config: Dict[str, Any], model_router: Any):
        self.config = config
        self.model_router = model_router
        self.translation_config = config.get("translation", {})
        self.collect_residuals = self.translation_config.get("collect_residuals", True)
        self.cjk_pattern = re.compile(r"[一-鿿㐀-䶿豈-﫿]+")

    async def final_cleanup_pass(self, text: str, api_key: Optional[str], chunk_id: int, worker_id: Optional[int] = None) -> str:
        """
        Dịch lại theo câu thay vì từng từ riêng lẻ.
        Tối ưu hóa API quota bằng cách áp dụng ngưỡng kích hoạt.
        Nếu api_key None/trống thì bỏ qua cleanup và trả về text (tránh GenAIClient nhận None).
        """
        if not api_key or not api_key.strip():
            logger.warning(f"[Chunk {chunk_id}] Bỏ qua Surgical CJK Cleanup: không có API key.")
            return text

        min_cjk_to_trigger = int(self.translation_config.get("cleanup", {}).get("min_cjk_to_trigger", 3))
        
        missed_terms = self.cjk_pattern.findall(text)
        if len(missed_terms) < min_cjk_to_trigger and len(missed_terms) > 0:
            logger.info(f"[Chunk {chunk_id}] Sót {len(missed_terms)} từ CJK (< ngưỡng {min_cjk_to_trigger}). Sử dụng micro-translation để tiết kiệm.")
            return await self._legacy_micro_translation(text, api_key, missed_terms, worker_id=worker_id)

        if not missed_terms:
            return text

        max_cleanup_attempts = max(
            1,
            int(
                self.translation_config.get("cleanup", {}).get(
                    "max_retries_per_sentence", 1
                )
            ),
        )
        current_text = text

        for attempt in range(max_cleanup_attempts):
            missed_terms = self.cjk_pattern.findall(current_text)
            unique_missed_terms = sorted(list(set(missed_terms)), key=len, reverse=True)

            if not unique_missed_terms:
                return current_text

            logger.warning(
                f"Lần {attempt + 1}: Phát hiện sót từ: {unique_missed_terms}. Dịch lại theo ngữ cảnh..."
            )

            sentences_with_missed = self._find_sentences_with_missed_terms(
                current_text, unique_missed_terms
            )

            if not sentences_with_missed:
                current_text = await self._legacy_micro_translation(
                    current_text, api_key, unique_missed_terms, worker_id=worker_id
                )
            else:
                contextual_prompt = self._build_contextual_translation_prompt(
                    sentences_with_missed
                )

                try:
                    contextual_result = await self.model_router.translate_chunk_async(
                        prompt=contextual_prompt,
                        complexity_score=0,
                        api_key=api_key,
                        force_model="flash",
                        worker_id=worker_id,
                    )
                    current_text = self._process_contextual_translation(
                        current_text, contextual_result["translation"]
                    )
                except Exception as e:
                    logger.error(f"Lỗi dịch theo ngữ cảnh: {e}")
                    current_text = await self._legacy_micro_translation(
                        current_text, api_key, unique_missed_terms, worker_id=worker_id
                    )

            if self._verify_no_cjk_remaining(current_text):
                return current_text

        # Fallback: Transliteration
        final_missed = self.cjk_pattern.findall(current_text)
        if final_missed:
            try:
                current_text = await self._fallback_transliterate_pass(
                    current_text, final_missed, api_key, worker_id=worker_id
                )
            except Exception as e:
                logger.error(f"Transliteration Fallback thất bại: {e}")

        # Final check
        final_missed = self.cjk_pattern.findall(current_text)
        if final_missed:
            if self.collect_residuals:
                try:
                    sentences = self._find_sentences_with_missed_terms(
                        current_text, sorted(list(set(final_missed)))
                    )
                    if sentences:
                        self._append_residual_entries(chunk_id, sentences)
                except Exception as e:
                    logger.error(f"Ghi residual thất bại: {e}")

            raise ValueError(
                f"Vẫn còn {len(final_missed)} từ CJK: {final_missed[:5]}..."
            )

        return current_text

    def _find_sentences_with_missed_terms(
        self, text: str, missed_terms: List[str]
    ) -> List[Dict]:
        """
        Tìm các câu chứa từ sót.
        """
        if not text:
            return []

        # Tách câu đơn giản bằng regex
        import re

        sentence_ends = re.compile(r"([.!?。！？\n])")
        parts = sentence_ends.split(text)

        sentences = []

        for i in range(0, len(parts) - 1, 2):
            s = parts[i] + parts[i + 1]
            if any(term in s for term in missed_terms):
                found_in_sentence = [term for term in missed_terms if term in s]
                sentences.append(
                    {"original": s.strip(), "missed_terms": found_in_sentence}
                )

        # Handle last part if no trailing punctuation
        if parts[-1].strip():
            s = parts[-1]
            if any(term in s for term in missed_terms):
                found_in_sentence = [term for term in missed_terms if term in s]
                sentences.append(
                    {"original": s.strip(), "missed_terms": found_in_sentence}
                )

        return sentences

    def _build_contextual_translation_prompt(
        self, sentences_with_missed: List[Dict]
    ) -> str:
        """
        Tạo prompt dịch lại các câu sót từ.
        """
        instructions = [
            "Dưới đây là một số câu trong bản dịch tiếng Việt vẫn còn sót từ tiếng Trung.",
            "Hãy dịch lại các câu này sang tiếng Việt hoàn chỉnh, đảm bảo tự nhiên và đúng ngữ cảnh.",
            'Yêu cầu TRẢ VỀ kết quả dưới dạng JSON array: [{"original": "...", "translation": "..."}]',
            "CÁC CÂU CẦN DỊCH LẠI:",
        ]

        for idx, item in enumerate(sentences_with_missed):
            instructions.append(f"{idx + 1}. Câu gốc: {item['original']}")
            instructions.append(f"   Từ sót: {', '.join(item['missed_terms'])}")

        return "\n".join(instructions)

    def _process_contextual_translation(
        self, text: str, translation_result: str
    ) -> str:
        """
        Thay thế kết quả dịch lại vào văn bản.
        """
        import json

        try:
            # Clean up potential markdown blocks
            json_str = translation_result.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("\n", 1)[0]
                if json_str.startswith("json"):
                    json_str = json_str.split("\n", 1)[1]

            data = json.loads(json_str)
            new_text = text
            for item in data:
                orig = item.get("original")
                trans = item.get("translation")
                if orig and trans:
                    new_text = new_text.replace(orig, trans)
            return new_text
        except Exception:
            # Fallback: simple replacement if AI didn't follow JSON format perfectly
            return text

    async def _legacy_micro_translation(
        self, text: str, api_key: str, missed_terms: List[str], worker_id: Optional[int] = None
    ) -> str:
        """
        Dịch từng từ riêng lẻ (phương pháp cũ).
        """
        fixed_text = text
        for term in missed_terms:
            prompt = f"Dịch từ tiếng Trung sau sang tiếng Việt (chỉ trả về kết quả dịch): {term}"
            res = await self.model_router.translate_chunk_async(
                prompt=prompt, complexity_score=0, api_key=api_key, force_model="flash", worker_id=worker_id
            )
            trans = res["translation"].strip()
            if trans:
                fixed_text = fixed_text.replace(term, trans)
        return fixed_text

    def _verify_no_cjk_remaining(self, text: str) -> bool:
        return not bool(self.cjk_pattern.search(text))

    async def _fallback_transliterate_pass(
        self, text: str, missed_terms: List[str], api_key: str, worker_id: Optional[int] = None
    ) -> str:
        """
        Dịch Hán Việt cho các từ cứng đầu.
        """
        unique_terms = sorted(list(set(missed_terms)), key=len, reverse=True)
        prompt = (
            "Chuyển đổi các từ tiếng Trung sau sang âm Hán Việt.\n"
            'Trả về JSON: {"term": "han_viet"}\n'
            "DANH SÁCH: " + ", ".join(unique_terms)
        )

        res = await self.model_router.translate_chunk_async(
            prompt=prompt, complexity_score=0, api_key=api_key, force_model="flash", worker_id=worker_id
        )

        try:
            json_str = res["translation"].strip()
            # Basic cleanup
            if "{" in json_str:
                json_str = "{" + json_str.split("{", 1)[1].rsplit("}", 1)[0] + "}"

            mapping = json.loads(json_str)
            fixed_text = text
            for term, hv in mapping.items():
                fixed_text = fixed_text.replace(term, hv)
            return fixed_text
        except Exception:
            return text

    def _append_residual_entries(self, chunk_id: int, entries: List[Dict]):
        """
        Lưu các câu sót vào file JSONL.
        """
        residual_file = "logs/residuals.jsonl"
        os.makedirs("logs", exist_ok=True)
        with open(residual_file, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(
                    json.dumps(
                        {
                            "chunk_id": chunk_id,
                            "original": entry["original"],
                            "missed": entry["missed_terms"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
