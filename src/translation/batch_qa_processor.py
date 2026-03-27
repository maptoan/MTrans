# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")

class BatchQAProcessor:
    """
    Handles Strategy B: Sentence-Level Extraction & Batching (PHASE 11).
    Collects problematic sentences from multiple chunks and batches them for efficient QA.
    """

    def __init__(self, config: Dict[str, Any], prompt_builder: Any, gemini_service: Any):
        self.config = config
        self.prompt_builder = prompt_builder
        self.gemini_service = gemini_service
        self.qa_config = config.get("translation", {}).get("qa_editor", {})
        self.context_window = int(self.qa_config.get("context_window", 2))
        self.cjk_pattern = re.compile(r"[一-鿿㐀-䶿豈-﫿]+")

    def extract_issues(self, chunk_id: int, translation: str) -> List[Dict[str, Any]]:
        """
        Trích xuất các đoạn văn chứa từ CJK kèm ngữ cảnh ±N câu.
        """
        if not translation:
            return []

        # Tách câu (cực kỳ cơ bản)
        sentences = re.split(r"([.!?。！？\n])", translation)
        # Gộp dấu câu lại với câu trước
        merged_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            merged_sentences.append(sentences[i] + sentences[i+1])
        if len(sentences) % 2 == 1 and sentences[-1]:
            merged_sentences.append(sentences[-1])

        issues = []
        for i, sent in enumerate(merged_sentences):
            missed = self.cjk_pattern.findall(sent)
            if missed:
                # Lấy context window
                start = max(0, i - self.context_window)
                end = min(len(merged_sentences), i + self.context_window + 1)
                
                context_segment = "".join(merged_sentences[start:end])
                
                issues.append({
                    "chunk_id": chunk_id,
                    "sentence_idx": i,
                    "original_segment": context_segment,
                    "target_sentence": sent,
                    "missed_terms": sorted(list(set(missed)))
                })
        
        return issues

    async def process_batch(self, batch_issues: List[Dict[str, Any]], api_key: str) -> Dict[int, List[Dict[str, str]]]:
        """
        Gửi batch issues sang AI để sửa.
        Returns: Dict { chunk_id: [ { "old": "...", "new": "..." } ] }
        """
        if not batch_issues:
            return {}

        prompt = self._build_batch_prompt(batch_issues)
        
        try:
            response_text = await self.gemini_service.generate_content_async(
                prompt=prompt,
                api_key=api_key,
                is_qa_edit=True
            )
            
            if not response_text:
                return {}

            return self._parse_batch_response(response_text)
        except Exception as e:
            logger.error(f"Batch QA failed: {e}")
            return {}

    def _build_batch_prompt(self, issues: List[Dict[str, Any]]) -> str:
        """
        Xây dựng prompt tối ưu cho batch QA.
        """
        instructions = [
            "Dưới đây là danh sách các đoạn văn bị sót từ tiếng Trung (CJK) từ nhiều phân đoạn khác nhau.",
            f"Nhiệm vụ: Dịch lại các đoạn này sang tiếng Việt hoàn chỉnh, giữ đúng ngữ cảnh ±{self.context_window} câu.",
            "Yêu cầu: TRẢ VỀ kết quả duy nhất ở định dạng JSON để hệ thống có thể tự động thay thế.",
            "",
            "FORMAT JSON YÊU CẦU:",
            '[{"chunk_id": ..., "sentence": "...", "fixed_translation": "..."}]',
            "",
            "DANH SÁCH CẦN SỬA:"
        ]

        for idx, issue in enumerate(issues):
            instructions.append(f"--- Issue {idx} (Chunk {issue['chunk_id']}) ---")
            instructions.append(f"Đoạn văn: {issue['original_segment']}")
            instructions.append(f"Từ sót: {', '.join(issue['missed_terms'])}")

        return "\n".join(instructions)

    def _parse_batch_response(self, text: str) -> Dict[int, List[Dict[str, str]]]:
        """
        Parse kết quả JSON từ AI.
        """
        try:
            # Tìm JSON trong text (nếu AI bọc trong markdown)
            json_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
            if not json_match:
                return {}
            
            data = json.loads(json_match.group(0))
            
            results = {}
            for item in data:
                cid = item.get("chunk_id")
                old = item.get("sentence")
                new = item.get("fixed_translation")
                
                # [SECURITY] Ensure terms are strings and cid is valid
                if isinstance(cid, (int, float)) and old and new:
                    cid = int(cid)
                    if cid not in results:
                        results[cid] = []
                    
                    # [CLEANUP] Remove obvious reasoning leakage from the 'new' text
                    cleaned_new = str(new).strip()
                    # Remove common "Wait," or "Thinking" prefixes if AI leaked them into the field
                    for prefix in ["Wait,", "Thinking,", "Actually,", "Correction:", "Revised:", "Polished:"]:
                        if cleaned_new.lower().startswith(prefix.lower()):
                            cleaned_new = cleaned_new[len(prefix):].strip()
                    
                    # Remove potential markdown formatting if AI added it INSIDE the JSON value
                    cleaned_new = cleaned_new.replace("```", "").strip()

                    results[cid].append({"old": str(old).strip(), "new": cleaned_new})
            
            return results
        except Exception as e:
            logger.error(f"Error parsing batch QA response: {e}")
            return {}
