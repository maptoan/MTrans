# -*- coding: utf-8 -*-
from __future__ import annotations

"""
PHIÊN BẢN v.1.3 - STABLE (2025-10-15)
=====================================
Module xây dựng prompt nâng cao, bổ sung rào chắn CJK và tương thích contextual JSON.

CẬP NHẬT v.1.3:
- Bổ sung rào chắn chống sót ký tự CJK trong prompt chính.
- Giữ tương thích với cơ chế contextual JSON của translator v.1.3.
"""

import logging
from typing import Any, Dict, List

from src.managers.glossary_manager import GlossaryManager
from src.managers.relation_manager import RelationManager
from src.managers.style_manager import StyleManager
from src.utils.token_optimizer import TokenOptimizer

from .prompt import EditingCommandsBuilder, GuidelinesBuilder, PromptFormatter

logger = logging.getLogger("NovelTranslator")


class PromptBuilder:
    """
    Lớp xây dựng prompt với trọng tâm là tính văn học và tự nhiên,
    hướng dẫn AI thông qua một quy trình biên tập chuyên nghiệp.
    """

    def __init__(
        self,
        style_manager: StyleManager,
        glossary_manager: GlossaryManager,
        relation_manager: RelationManager,
        document_type: str = "novel",
        config: Dict[str, Any] = None,
    ):
        self.style_manager = style_manager
        self.glossary_manager = glossary_manager
        self.relation_manager = relation_manager
        self.document_type = document_type.lower()  # novel, technical_doc, academic_paper, manual, general
        self.config = config or {}
        # Đọc cấu hình cleanup header/footer/page number
        translation_config = self.config.get("translation", {})
        self.remove_header_footer_page_number = translation_config.get("remove_header_footer_page_number", True)

        # Đọc cấu hình marker-based validation
        chunking_config = self.config.get("preprocessing", {}).get("chunking", {})
        self.use_markers = chunking_config.get("use_markers", True)
        self.marker_format = chunking_config.get("marker_format", "simple")

        # Flag để track xem đã log warning về metadata chưa (chỉ log 1 lần)
        self._metadata_warning_logged = False

        # OPTIMIZATION 1.2: Prompt template cache để tránh rebuild các phần static
        self._template_cache: Dict[str, Dict[str, str]] = {}

        # Phase 1: Initialize StyleAnalyzer
        from ..utils.style_analyzer import StyleAnalyzer

        context_config = translation_config.get("context", {})
        self.style_analyzer = StyleAnalyzer(context_config)

        # Phase 2: Style cache để tránh rebuild style analysis nhiều lần
        self._style_cache: Dict[int, Dict[str, Any]] = {}

        # Phase 2: Token Optimization - Config toggles (default True for efficiency)
        self.prompt_compact_format = translation_config.get("prompt_compact_format", True)
        self.remove_redundant_instructions = translation_config.get("remove_redundant_instructions", True)

        # Initialize specialized builders
        self.guidelines_builder = GuidelinesBuilder(
            document_type=self.document_type, config=self.config, style_manager=self.style_manager
        )
        self.editing_commands_builder = EditingCommandsBuilder(
            document_type=self.document_type, remove_redundant_instructions=self.remove_redundant_instructions
        )
        self.prompt_formatter = PromptFormatter(use_markers=self.use_markers)

        logger.info(
            f"PromptBuilder đã khởi tạo (document_type: {self.document_type}, remove_header_footer_page_number: {self.remove_header_footer_page_number}, use_markers: {self.use_markers}, compact_format: {self.prompt_compact_format})."
        )

    def build_editor_prompt(
        self,
        draft_translation: str,
        glossary_terms: List[Dict],
        style_guide: str = "",
        source_text: str = "",
        cjk_remaining: List[str] = None,
        character_relations: str = "",
    ) -> str:
        """
        [PHASE 7.5] Xây dựng prompt cho Smart QA Editor - Enhanced Quality Control.
        Nhiệm vụ: Soát lỗi toàn diện (Chính tả, Format, Văn phong, Glossary, Xưng hô), DỊCH BÙ và FIX CJK.

        Args:
            cjk_remaining: Danh sách từ CJK sót.
            character_relations: Thông tin quan hệ nhân vật để check xưng hô.
        """
        glossary_text = self._format_glossary_for_prompt(glossary_terms)

        # 2. Build Prompt (với thông tin CJK sót và style guide)
        prompt = f"""
ROLE: You are a meticulous Senior Editor for a Vietnamese novel translation project (Kind: {self.document_type}).
TASK: Perfect the DRAFT TRANSLATION. Your goal is distinct from the translator: focus on QUALITY CONTROL and CONSISTENCY.
"""

        # Marker Preservation (CRITICAL for pipeline integrity)
        if self.use_markers:
            marker_inst = self._build_marker_preservation_instruction(draft_translation)
            if marker_inst:
                prompt += f"\n{marker_inst}\n"

        # Inject Source if available (Smart Mode)
        if source_text:
            prompt += """
GOAL: 
1. **Compare** DRAFT with ORIGINAL SOURCE to ensure NO MISSING MEANING.
2. **Fill in** missing details (Supplementary Translation).
3. **Correct** Character Addressing (Xưng hô) based on relationships.
4. **Fix** all spelling, grammar, and formatting errors.
5. **Ensure** absolute Glossary Consistency.
"""
        else:
            prompt += """
GOAL: Fix spelling/grammar, correct character addressing, enforce glossary, and polish flow WITHOUT changing meaning.
"""

        # CJK Warning
        if cjk_remaining and len(cjk_remaining) > 0:
            cjk_list = ", ".join(cjk_remaining[:10])
            if len(cjk_remaining) > 10:
                cjk_list += f" (and {len(cjk_remaining) - 10} more)"
            prompt += f"""
⚠️ CRITICAL - UNTRANSLATED CONTENT:
Detected untranslated CJK terms: [{cjk_list}]
ACTION: Translate these immediately into natural Vietnamese within context.
"""

        prompt += f"""
INPUT DATA:
---
[GLOSSARY GUIDELINES]
{glossary_text}
---
[STYLE & TONE]
{style_guide}
---
"""

        if character_relations:
            prompt += f"""[CHARACTER RELATIONS & ADDRESSING]
{character_relations}
*RULE: Check every dialogue line. Ensure characters use correct pronouns (Huynh/Đệ, Ta/Ngươi, Chàng/Nàng) consistent with their relationship and hierarchy.*
---
"""

        if source_text:
            prompt += f"""[ORIGINAL SOURCE]
{source_text}
---
"""

        prompt += f"""[DRAFT TRANSLATION]
{draft_translation}
---

STRICT EDITING CHECKLIST:

1. **Accuracy & Completeness**: 
   - Compare with Source (if avail). If Draft skipped a sentence, TRANSLATE & INSERT it.
   - Do NOT summarize. Keep full details.

2. **Character Addressing (Xưng hô)**:
   - Verify all pronouns match the [CHARACTER RELATIONS].
   - Detect inconsistency (e.g., A calling B "ty tỷ" then "cô nương" in same context). Fix it.

3. **Glossary Consistency**: 
   - Terms in [GLOSSARY GUIDELINES] must be exact.
   - Fix "Half-translated" terms (e.g. Pinyin or Sino-Vietnamese that should be Pure Vietnamese).

4. **Formatting & Presentation**:
   - Ensure standard Vietnamese punctuation info.
   - Fix broken paragraph breaks.
   - Ensure dialogue quotes are consistent.
"""

        if self.use_markers:
            prompt += "   - **PRESERVE MARKERS**: Do NOT remove [CHUNK:ID:START] and [CHUNK:ID:END].\n"

        output_marker = "BẮT ĐẦU BẢN BIÊN TẬP NGAY DƯỚI ĐÂY (KHÔNG ghi chú):"
        prompt += """
5. **Spelling & Grammar**:
   - Fix typos (teencode, misspelled words).
   - Fix "Vietlish" or stiff sentence structures.

OUTPUT FORMAT:
Return ONLY the polished translation. 
- DO NOT include reasoning, thinking notes, or "Wait, ..." comments.
- DO NOT add conversational filler.
- DO NOT wrap in markdown code blocks unless the original had them.
"""
        if self.use_markers:
            prompt += "   - **PRESERVE MARKERS**: Maintain the [CHUNK:ID:START] and [CHUNK:ID:END] markers at the EXACT start and end of the output.\n"

        prompt += f"""
{output_marker}
"""
        return prompt.strip()

    def _format_glossary_for_prompt(self, glossary_terms: List[Dict]) -> str:
        """
        Format glossary terms for use in prompts.
        """
        return self.prompt_formatter.format_glossary_for_prompt(glossary_terms)

    def _build_guidelines_by_document_type(self) -> str:
        """
        Xây dựng các nguyên tắc phù hợp với loại tài liệu.
        """
        return self.guidelines_builder.build_guidelines()

    def _build_editing_commands(self, contains_potential_title: bool) -> str:
        """
        Xây dựng các mệnh lệnh biên tập cụ thể, có cấu trúc tuần tự với ví dụ.
        Sử dụng logic tối ưu để tiết kiệm tokens.
        """
        return self.editing_commands_builder.build_editing_commands(contains_potential_title)

    def _build_quality_checklist_compact(self) -> str:
        """
        Checklist rút gọn - chỉ giữ các điểm quan trọng nhất.
        """
        return self.editing_commands_builder.build_quality_checklist()

    def _build_summary_section(self, contains_potential_title: bool) -> str:
        """
        Tạo summary section ngắn gọn ở đầu prompt để AI nắm tổng quan.
        """
        return self.prompt_formatter.build_summary_section(contains_potential_title)

    def _build_cjk_guardrail_compact(self) -> str:
        """
        CJK guardrail rút gọn.
        """
        return self.prompt_formatter.build_cjk_guardrail()

    def _build_glossary_section_compact(self, glossary_section: str) -> str:
        """
        Glossary section rút gọn - Tăng cường tính bắt buộc.
        """
        return self.prompt_formatter.build_glossary_section_compact(glossary_section)

    def _build_header_footer_cleanup_section_compact(self) -> str:
        """
        Cleanup section rút gọn - chỉ giữ thông tin quan trọng nhất.
        """
        return """[CLEANUP HEADER/FOOTER/PAGE NUMBER]
→ CHỈ xóa nếu CHẮC CHẮN 100%. Nếu NGHI NGỜ → GIỮ LẠI.

XÓA NẾU:
- Dòng ngắn (≤50 ký tự) + Lặp lại ≥3 lần + Ở đầu/cuối + Không có ngữ cảnh
- Số trang: "1", "Page 1", "Trang 1", "第1页" (≤20 ký tự)

KHÔNG XÓA:
- Đoạn văn dài (>50 ký tự) hoặc có ngữ cảnh
- Tiêu đề chương (pattern "Chương X", "Chapter X", "第X章")
- Đoạn văn không lặp lại hoặc có liên kết với nội dung

→ Khi NGHI NGỜ → GIỮ LẠI và DỊCH"""

    def _build_marker_preservation_instruction(self, chunk_text: str) -> str:
        """
        Xây dựng hướng dẫn bảo toàn marker cho AI.
        
        Args:
            chunk_text: Text của chunk (có thể chứa markers)
            
        Returns:
            Instruction string hoặc empty string nếu không có markers
        """
        has_chunk_start = "[CHUNK:" in chunk_text and ":START]" in chunk_text
        has_chunk_end = "[CHUNK:" in chunk_text and ":END]" in chunk_text
        has_chunk_marker = has_chunk_start or has_chunk_end
        has_tx_marker = "[TX:" in chunk_text

        if not has_chunk_marker and not has_tx_marker:
            return ""

        instruction = """
⚠️ QUAN TRỌNG: BẢO TOÀN CẤU TRÚC ĐOẠN VĂN & MARKER ⚠️
"""

        if has_chunk_marker:
            instruction += """
1. **Bảo tồn Marker CHUNK:**
   - GIỮ NGUYÊN HOÀN TOÀN các marker này. KHÔNG xóa, thay đổi, dịch, hoặc di chuyển vị trí.
   - Mỗi `[CHUNK:ID:START]` phải có một `[CHUNK:ID:END]` tương ứng.
"""

            if has_chunk_start and not has_chunk_end:
                instruction += """
   - Trường hợp đặc biệt (Sub-chunk): Output PHẢI GIỮ marker START và KHÔNG được tự ý thêm marker END vào phần này.
"""
            elif has_chunk_end and not has_chunk_start:
                instruction += """
   - Trường hợp đặc biệt (Sub-chunk): Output PHẢI GIỮ marker END và KHÔNG được tự ý thêm marker START vào phần này.
"""

        instruction += """
2. **Bảo tồn Cấu trúc Đoạn văn (CỰC KỲ QUAN TRỌNG):**
   - TUYỆT ĐỐI KHÔNG gộp các đoạn văn lại với nhau.
   - PHẢI dùng 2 dấu xuống dòng (\\n\\n) để phân tách các đoạn văn rõ ràng.
   - Bản dịch PHẢI có số lượng đoạn văn tương ứng hoàn toàn với bản gốc.
"""

        if has_tx_marker:
            instruction += """
🔴 QUY TẮC MARKER VĂN BẢN (TEXT ID - [TX:id]):
- Nếu thấy marker dạng `[TX:id]`, hãy GIỮ NGUYÊN HOÀN TOÀN.
- Marker `[TX:id]` luôn nằm SAU đoạn văn tương đương. Hãy trả về marker y như vị trí trong bản gốc.
- TUYỆT ĐỐI KHÔNG được chuyển đổi `[TX:id]` sang định dạng `[CHUNK:...]`. KHÔNG gộp vào chunk.
"""
        return instruction
    def _analyze_context_style(self, translated_context_chunks: List[str]) -> Dict[str, Any]:
        """
        Phân tích phong cách từ các đoạn ngữ cảnh trước để duy trì sự nhất quán.
        Sử dụng StyleAnalyzer class với caching (Phase 2: Lazy evaluation).

        Args:
            translated_context_chunks: List các chunk đã dịch

        Returns:
            Dict với các metrics: pace, avg_length, tone, register, etc.
        """
        if not translated_context_chunks:
            return {}

        # Phase 2: Cache key dựa trên content hash (đơn giản)
        # Chỉ cache nếu có ít nhất 2 chunks (để tránh cache quá nhiều)
        if len(translated_context_chunks) >= 2:
            cache_key = hash(tuple(translated_context_chunks[-2:]))
            if cache_key in self._style_cache:
                return self._style_cache[cache_key]

        # Delegate to StyleAnalyzer
        result = self.style_analyzer.analyze(translated_context_chunks)

        # Cache result (giới hạn cache size)
        if len(translated_context_chunks) >= 2 and len(self._style_cache) < 500:
            self._style_cache[cache_key] = result

        return result

    def _build_translation_command(self) -> str:
        """
        Yêu cầu dịch thuật compact — chống tóm tắt/cắt bớt.
        """
        return """
[NHIỆM VỤ DỊCH — BẮT BUỘC]
• Dịch TỪNG CÂU, ±20% độ dài gốc, giữ nguyên số đoạn văn
• Tuân thủ [QUY TẮC XƯNG HÔ] + [QUY TẮC TRẦN THUẬT]
• Hội thoại: dấu ngoặc kép "..."
• KHÔNG tóm tắt, KHÔNG ghi chú, KHÔNG giải thích
• Câu cuối phải hoàn chỉnh, có dấu câu kết thúc
"""

    def build_main_messages(
        self,
        chunk_text: str,
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        relevant_terms: List[Dict],
        active_characters: List[str],
        contains_potential_title: bool,
    ) -> List[Dict[str, Any]]:
        """
        Xây dựng prompt theo phong cách Multi-turn JSON.
        Chia nhỏ instructions thành các turn để model bám sát hơn.
        """
        if not chunk_text or not chunk_text.strip():
            logger.warning("Empty chunk_text received in build_main_messages")
            return []

        if len(chunk_text) > 50000:
            logger.warning(f"Very long chunk_text: {len(chunk_text)} chars in build_main_messages")

        messages = []

        # Turn 1: Core instructions and guidelines
        core_parts = []
        core_parts.append(self._build_summary_section(contains_potential_title))

        marker_inst = self._build_marker_preservation_instruction(chunk_text)
        if marker_inst:
            core_parts.append(marker_inst)

        core_parts.append(self._build_cjk_guardrail_compact())

        template = self._get_cached_template()
        if template.get("document_guidelines"):
            core_parts.append(template["document_guidelines"])
        if template.get("style_instructions"):
            core_parts.append(template["style_instructions"])
        if template.get("verb_guide"):
            core_parts.append(template["verb_guide"])

        messages.append(
            {
                "role": "user",
                "parts": [{"text": "\n\n".join(core_parts) + "\n\nXác nhận nếu bạn đã hiểu các nguyên tắc này."}],
            }
        )
        messages.append(
            {
                "role": "model",
                "parts": [
                    {
                        "text": "Tôi đã nắm rõ các nguyên tắc văn học, rào chắn CJK và yêu cầu bảo toàn marker. Tôi sẵn sàng dịch theo phong cách chuyên nghiệp."
                    }
                ],
            }
        )

        # Turn 2: Metadata and Editing Workflow
        meta_parts = []
        if relevant_terms:
            if hasattr(self.glossary_manager, "build_compact_prompt_section"):
                glossary_section = self.glossary_manager.build_compact_prompt_section(relevant_terms)
            else:
                glossary_section = self.glossary_manager.build_prompt_section(relevant_terms)
                glossary_section = self._build_glossary_section_compact(glossary_section) if glossary_section else ""
            if glossary_section:
                meta_parts.append(glossary_section)

        relation_section = self.relation_manager.build_prompt_section(active_characters)
        if relation_section:
            meta_parts.append(f"[QUY TẮC XƯNG HÔ]\n{relation_section}")

        narrative_section = self.relation_manager.build_narrative_prompt_section(active_characters)
        if narrative_section:
            meta_parts.append(f"[QUY TẮC TRẦN THUẬT]\n{narrative_section}")

        meta_parts.append(self._build_editing_commands(contains_potential_title))

        messages.append(
            {
                "role": "user",
                "parts": [{"text": "\n\n".join(meta_parts) + "\n\nGhi nhớ thuật ngữ và quy trình biên tập này."}],
            }
        )
        messages.append(
            {
                "role": "model",
                "parts": [{"text": "Đã ghi nhớ thuật ngữ và quy trình. Tôi sẽ áp dụng chúng vào bản dịch."}],
            }
        )

        # Turn 3: Context and Task
        task_parts = []

        # [v7.6] High-Priority Metadata Reinforcement (Move from Turn 1 to Turn 3)
        # These are rules that AI often misses due to long contexts
        if self.style_manager.is_loaded():
            style_summary = self.style_manager.get_style_summary()
            if style_summary:
                task_parts.append(f"[QUY TẮC VÀNG - BẮT BUỘC TUÂN THỦ TUYỆT ĐỐI]\n{style_summary}")

        # [PHASE 13.5] Restore Bilingual Context Pairing (Anti-Regression)
        if original_context_chunks:
            context_items = []
            valid_translations = (
                [c for c in translated_context_chunks if c is not None] if translated_context_chunks else []
            )
            # Use style analyzer for dynamic tone maintenance
            style_analysis = self._analyze_context_style(valid_translations) if valid_translations else {}

            # Show up to last 2 chunks as pairs for compact but effective context
            display_count = min(2, len(original_context_chunks))
            for i in range(len(original_context_chunks) - display_count, len(original_context_chunks)):
                orig = original_context_chunks[i]
                trans = (
                    translated_context_chunks[i]
                    if (translated_context_chunks and i < len(translated_context_chunks))
                    else None
                )

                # Truncate context source if too long to save tokens
                orig_snippet = orig[:500] + "..." if len(orig) > 500 else orig

                pair_text = f"Nguồn: {orig_snippet}"
                if trans:
                    pair_text += f"\nBản dịch: {trans}"
                else:
                    pair_text += "\nBản dịch: [Đang xử lý song song - tham khảo nội dung gốc]"

                context_items.append(pair_text)

            context_body = "\n---\n".join(context_items)
            task_parts.append(
                f"[NGỮ CẢNH TRƯỚC ĐÓ (SONG NGỮ)]\n---\n{context_body}\n---\n→ Duy trì văn phong: {style_analysis.get('tone', 'tự nhiên')}"
            )

        task_parts.append("""
[CHỈ DẪN CUỐI - CHẾ ĐỘ MÁY DỊCH]
Bạn là một công cụ dịch thuật chuyên nghiệp. 
1. TUÂN THỦ 100% Glossary và Quy tắc Vàng ở trên.
2. KHÔNG được dùng âm Hán Việt cho các tên Cục/Mưu kế (phải dịch thoát ý).
3. CHỈ TRẢ VỀ bản dịch thuần túy, không giải thích, không ghi chú.
""")

        task_parts.append(f"[ĐOẠN VĂN BẢN CẦN DỊCH]\n---\n{chunk_text}\n---")
        task_parts.append(self._build_quality_checklist_compact())
        task_parts.append("\nBẮT ĐẦU BẢN DỊCH NGAY DƯỚI ĐÂY (KHÔNG ghi chú):")

        messages.append({"role": "user", "parts": [{"text": "\n\n".join(task_parts)}]})

        return messages

    def build_main_prompt(
        self,
        chunk_text: str,
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        relevant_terms: List[Dict],
        active_characters: List[str],
        contains_potential_title: bool,
    ) -> str:
        """
        Backward compatibility: Trả về prompt dạng string duy nhất.
        """
        messages = self.build_main_messages(
            chunk_text,
            original_context_chunks,
            translated_context_chunks,
            relevant_terms,
            active_characters,
            contains_potential_title,
        )
        # Ghép lại thành string
        full_text = []
        for msg in messages:
            role = "USER" if msg["role"] == "user" else "AI"
            content = msg["parts"][0]["text"]
            full_text.append(f"### {role}:\n{content}")

        return "\n\n".join(full_text)

    # Legacy build_main_prompt_legacy removed

    def build_micro_translation_prompt(self, terms_to_translate: List[str]) -> str:
        """
        Xây dựng một prompt cực kỳ đơn giản và hiệu quả để dịch các từ/cụm từ đơn lẻ
        cho bước "Thay thế cưỡng bức".
        """
        prompt = "Bạn là công cụ dịch thuật Trung-Việt. Dịch các thuật ngữ sau.\n"
        prompt += "QUY TẮC: Mỗi dòng theo định dạng 'Từ gốc | Bản dịch'\n\n"

        for term in terms_to_translate:
            prompt += f"{term} | \n"

        logger.info(f"Đã tạo prompt dịch vi mô cho {len(terms_to_translate)} từ.")
        return prompt.strip()

    def _get_cached_template(self) -> Dict[str, str]:
        """
        OPTIMIZATION 1.2: Get cached template parts (document guidelines, verb guide, style instructions).

        Cache key dựa trên document_type và style profile hash để đảm bảo cache invalidate
        khi style thay đổi.

        Returns:
            Dict với keys: 'document_guidelines', 'verb_guide', 'style_instructions'
        """
        # Tạo cache key dựa trên document_type và style profile
        import hashlib

        style_hash = hashlib.md5(
            str(self.style_manager.profile).encode() if self.style_manager.profile else b""
        ).hexdigest()[:8]
        cache_key = f"{self.document_type}_{style_hash}_{self.remove_header_footer_page_number}"

        # Check cache
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Build và cache template parts
        document_guidelines = self.guidelines_builder.build_guidelines()
        verb_guide = self.guidelines_builder._build_verb_variation_guide() if self.document_type == "novel" else ""

        style_instructions = self.style_manager.build_style_instructions()

        template = {
            "document_guidelines": document_guidelines,
            "verb_guide": verb_guide,
            "style_instructions": style_instructions,
        }

        # Cache result (giới hạn cache size để tránh memory leak)
        if len(self._template_cache) < 10:  # Giới hạn 10 entries (đủ cho nhiều document types)
            self._template_cache[cache_key] = template

        return template

    # Legacy _format_glossary_compact removed

    def _format_context_compact(self, translated_context_chunks: List[str], style_analysis: Dict[str, Any]) -> str:
        """
        Phase 2: Format context theo compact format để tiết kiệm tokens.
        Sử dụng TokenOptimizer để minify context text.

        Format:
        [CTX]
        ...minified context...
        [/CTX]
        STYLE: {pace, tone, register}
        """
        # Minify context chunks
        minified_chunks = [
            TokenOptimizer.minify_context_chunk(c) for c in translated_context_chunks[-2:]
        ]  # Keep last 2
        context_text = "\n---\n".join(minified_chunks)

        # Build style compact
        style_parts = []
        if style_analysis.get("pace"):
            style_parts.append(f"Pace:{style_analysis.get('pace')}")
        if style_analysis.get("avg_length"):
            style_parts.append(f"Len:{style_analysis.get('avg_length')}")
        if style_analysis.get("tone"):
            style_parts.append(f"Tone:{style_analysis.get('tone')}")

        style_str = "; ".join(style_parts) if style_parts else "Standard"

        compact = f"""[PREV_CTX]
{context_text}
[/PREV_CTX]
STYLE: {style_str} -> DUY TRÌ"""
        return compact

    def build_cacheable_prefix(self, full_glossary: Dict[str, str] = None, full_relations: List[str] = None) -> str:
        """
        Builds the static part of the prompt for Context Caching.
        This content is intended to be cached and reused across multiple requests.

        Includes:
        - Role definition (implicitly via guidelines)
        - Guidelines by document type
        - Verb variation guide (if novel)
        - Style instructions (Global)
        - Editing Commands (Generic, assuming titles possible)
        - CJK Guardrails (Compact)
        - Full Metadata (Glossary + Relations) if provided
        """
        prompt_parts = []

        # 0. Role & Intent
        prompt_parts.append("BẠN LÀ CHUYÊN GIA DỊCH THUẬT VÀ BIÊN TẬP CAO CẤP.\n")

        # 1. Guidelines & Rules (Static)
        prompt_parts.append(self.guidelines_builder.build_guidelines())

        if self.document_type == "novel":
            prompt_parts.append(self.guidelines_builder._build_verb_variation_guide())

        prompt_parts.append(self.style_manager.build_style_instructions())

        # 2. Cleanup & Editing (Static)
        if self.remove_header_footer_page_number:
            prompt_parts.append(self.editing_commands_builder._build_header_footer_cleanup_section_compact())

        # For cached prompt, we assume titles MIGHT exist, so we enable title checking
        prompt_parts.append(self.editing_commands_builder.build_editing_commands(contains_potential_title=True))

        # 3. Translation Command (Static) - CRITICAL: Anti-summarization guardrails
        prompt_parts.append(self.editing_commands_builder._build_translation_command())

        # 4. Guardrails (Static)
        if hasattr(self, "_build_cjk_guardrail_compact"):
            prompt_parts.append(self._build_cjk_guardrail_compact())

        # 4. Global Metadata (Static for the context)
        # Using Full Glossary/Relations here instead of per-chunk
        prompt_parts.append("[NGỮ CẢNH KỸ THUẬT - TOÀN CỤC]\n")

        # Glossary
        glossary_text = "Không có"
        if full_glossary:
            # Sort for stability
            sorted_items = sorted(full_glossary.items(), key=lambda x: len(x[0]), reverse=True)
            glossary_lines = [f"{k} → {v}" for k, v in sorted_items]
            glossary_text = "\n".join(glossary_lines)

        prompt_parts.append(f"[BẢNG THUẬT NGỮ (Dùng khi xuất hiện)]\n{glossary_text}\n")

        # Relations
        relations_text = "Không có hoặc chưa xác định."
        if full_relations:
            relations_text = "\n".join(full_relations)

        prompt_parts.append(f"[QUAN HỆ NHÂN VẬT (Tham khảo)]\n{relations_text}\n")

        # 5. Quality Checklist (Static)
        prompt_parts.append(self._build_quality_checklist_compact())

        return "\n\n".join(prompt_parts)

    def build_dynamic_prompt(
        self,
        chunk_text: str,
        translated_context_chunks: List[str] = None,
        active_characters: List[str] = None,
        override_instructions: str = None,
    ) -> str:
        """
        Builds the dynamic part (Task) to append to the cached prefix.
        """
        prompt_parts = []

        if not chunk_text or not chunk_text.strip():
            logger.warning("Empty chunk_text received in build_dynamic_prompt")
            return "[CẢNH BÁO: ĐOẠN VĂN TRỐNG]"

        if len(chunk_text) > 50000:
            logger.warning(f"Very long chunk_text: {len(chunk_text)} chars in build_dynamic_prompt")

        # 0. Override (Hot-patch)
        if override_instructions:
            prompt_parts.append(f"[LƯU Ý CẬP NHẬT - ƯU TIÊN CAO]\n{override_instructions}")

        # 1. Context (Dynamic)
        if translated_context_chunks:
            style_analysis = self._analyze_context_style(translated_context_chunks)

            if self.prompt_compact_format:
                context_section = self._format_context_compact(translated_context_chunks, style_analysis)
            else:
                # Standard format
                context_text = "\n...\n".join(translated_context_chunks[-2:])
                guidance = f"Style: pace={style_analysis.get('pace', 'avg')}"
                context_section = f"[NGỮ CẢNH TRƯỚC]\n---\n{context_text}\n---\n→ {guidance}"

            prompt_parts.append(context_section)

        # 2. Active Characters Reinforcement (Dynamic)
        if active_characters:
            prompt_parts.append(f"[NHÂN VẬT ĐANG XUẤT HIỆN]\n{', '.join(active_characters)}")

        # 2.5 Style Reminder (v6.2) - Reinforce style in every chunk
        if self.style_manager.is_loaded():
            style_summary = self.style_manager.get_style_summary()
            if style_summary:
                prompt_parts.append(f"""[NHẮC LẠI VĂN PHONG - BẮT BUỘC TUÂN THỦ]
{style_summary}
→ TUÂN THỦ 100% xưng hô và giọng điệu này trong bản dịch.""")

        # 3. Main Task (Dynamic)
        if self.remove_redundant_instructions:
            task_section = f"""[ĐOẠN VĂN BẢN CẦN DỊCH]
---
{chunk_text}
---

THỰC HIỆN: Cleanup → Dịch → Biên tập (theo [MỆNH LỆNH BIÊN TẬP] đã cache)
ĐẦU RA: Bản dịch tiếng Việt thuần túy, đúng format."""
        else:
            task_section = f"""[ĐOẠN VĂN BẢN CẦN DỊCH]
---
{chunk_text}
---

NHIỆM VỤ:
1. Dựa trên Bảng Thuật Ngữ và Nguyên Tắc đã cung cấp (trong Context Cache).
2. Dịch đoạn văn trên sang tiếng Việt.
3. Thực hiện biên tập theo [MỆNH LỆNH BIÊN TẬP].
4. Đảm bảo KHÔNG CÒN CJK và TUÂN THỦ checklist.

CHỈ TRẢ VỀ BẢN DỊCH CUỐI CÙNG."""

        prompt_parts.append(task_section)

        return "\n\n".join(prompt_parts)

    def build_multi_turn_prompt(
        self,
        chunk_text: str,
        translated_context_chunks: List[str] = None,
        original_context_chunks: List[str] = None,
        active_characters: List[str] = None,
        override_instructions: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Builds a multi-turn conversation format for Gemini.
        If original_context_chunks and translated_context_chunks are provided,
        it builds them as turns: user (original) -> model (translation).
        """
        messages = []

        # 1. Provide Context as Turns (if available and matching)
        if (
            original_context_chunks
            and translated_context_chunks
            and len(original_context_chunks) == len(translated_context_chunks)
        ):
            for orig, tran in zip(original_context_chunks, translated_context_chunks):
                messages.append({"role": "user", "parts": [{"text": f"Dịch đoạn này:\n{orig}"}]})
                messages.append({"role": "model", "parts": [{"text": tran}]})

        # 2. Final Turn: Task
        # [FIX] Do not re-inject translated_context_chunks as text because they are already turns
        task_text = self.build_dynamic_prompt(
            chunk_text,
            translated_context_chunks=None,  # Already injected as turns
            active_characters=active_characters,
            override_instructions=override_instructions,
        )
        messages.append({"role": "user", "parts": [{"text": task_text}]})

        return messages
