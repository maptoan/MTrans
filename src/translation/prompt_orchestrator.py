# -*- coding: utf-8 -*-
"""
PromptOrchestrator: Phối hợp các thành phần (Glossary, Relations, PromptBuilder) 
để tạo ra prompt hoàn chỉnh cho AI.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class PromptOrchestrator:
    """
    Chịu trách nhiệm điều phối việc xây dựng prompt, bao gồm tìm kiếm metadata
    và kiểm tra giới hạn token.
    """

    def __init__(
        self,
        glossary_manager: Any,
        relation_manager: Any,
        prompt_builder: Any,
        gemini_service: Any,
        config: Dict[str, Any],
        document_type: str = "novel",
    ):
        self.glossary_manager = glossary_manager
        self.relation_manager = relation_manager
        self.prompt_builder = prompt_builder
        self.gemini_service = gemini_service
        self.config = config
        self.translation_config = config.get("translation", {})
        self.document_type = document_type
        
        # Regex pattern để nhận diện tiêu đề chương (tránh dịch tiêu đề thành văn bản thường)
        self.title_pattern = re.compile(
            r"^(?:Chapter|Chương|Hồi|Quyển|Book|Vol|Volume)\s+\d+|^\d+\.\s+(?:Chapter|Chương)|^(?:Chapter|Chương)\s+\d+\s*:",
            re.IGNORECASE | re.MULTILINE,
        )

    async def build_translation_prompt(
        self,
        chunk_id: int,
        text_to_translate: str,
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        cache_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[Any, Optional[str], List[Dict], List[str]]:
        """
        Xây dựng prompt dịch thuật với ngữ cảnh và metadata.
        Bao gồm cả logic kiểm tra va truncate token nếu cần.
        """
        # 1. Tìm kiếm metadata
        full_context_text = (
            "\n".join(original_context_chunks or []) + "\n" + text_to_translate
        )
        relevant_terms = self.glossary_manager.find_terms_in_chunk(full_context_text)

        # Character detection (chỉ dành cho novel)
        if self.document_type == "novel":
            scene_characters = self.relation_manager.find_active_characters(
                full_context_text
            )
        else:
            scene_characters = []

        contains_potential_title = bool(self.title_pattern.search(text_to_translate))

        if relevant_terms or scene_characters:
            logger.debug(
                f"[Chunk {chunk_id}] Metadata: {len(relevant_terms)} terms, {len(scene_characters)} characters"
            )

        # 2. Xây dựng prompt cơ bản
        use_multi_turn = self.translation_config.get("use_multi_turn", True)
        override_instructions = self.translation_config.get("override_instructions")

        main_prompt, cached_content_arg = self._generate_prompt_content(
            text_to_translate,
            original_context_chunks,
            translated_context_chunks,
            scene_characters,
            relevant_terms,
            contains_potential_title,
            cache_name,
            use_multi_turn,
            override_instructions,
        )

        # 3. Token Pre-Check (Kiểm soát chi phí và giới hạn context)
        main_prompt = await self._perform_token_safety_check(
            chunk_id,
            main_prompt,
            text_to_translate,
            translated_context_chunks,
            scene_characters,
            relevant_terms,
            contains_potential_title,
            use_multi_turn,
            override_instructions,
            api_key
        )

        return main_prompt, cached_content_arg, relevant_terms, scene_characters

    def _generate_prompt_content(
        self,
        text_to_translate: str,
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        scene_characters: List[str],
        relevant_terms: List[Dict],
        contains_potential_title: bool,
        cache_name: Optional[str],
        use_multi_turn: bool,
        override_instructions: Optional[str],
    ) -> Tuple[Any, Optional[str]]:
        """Lớp helper để gọi PromptBuilder."""
        if cache_name:
            if use_multi_turn:
                main_prompt = self.prompt_builder.build_multi_turn_prompt(
                    chunk_text=text_to_translate,
                    original_context_chunks=original_context_chunks,
                    translated_context_chunks=translated_context_chunks,
                    active_characters=list(set(scene_characters)),
                    override_instructions=override_instructions,
                )
            else:
                main_prompt = self.prompt_builder.build_dynamic_prompt(
                    chunk_text=text_to_translate,
                    translated_context_chunks=translated_context_chunks,
                    active_characters=list(set(scene_characters)),
                    override_instructions=override_instructions,
                )
            cached_content_arg = cache_name
        else:
            if hasattr(self.prompt_builder, "build_main_messages"):
                main_prompt = self.prompt_builder.build_main_messages(
                    chunk_text=text_to_translate,
                    original_context_chunks=original_context_chunks,
                    translated_context_chunks=translated_context_chunks,
                    relevant_terms=relevant_terms,
                    active_characters=list(set(scene_characters)),
                    contains_potential_title=contains_potential_title,
                )
            else:
                main_prompt = self.prompt_builder.build_main_prompt(
                    chunk_text=text_to_translate,
                    original_context_chunks=original_context_chunks,
                    translated_context_chunks=translated_context_chunks,
                    relevant_terms=relevant_terms,
                    active_characters=list(set(scene_characters)),
                    contains_potential_title=contains_potential_title,
                )
            cached_content_arg = None
        
        return main_prompt, cached_content_arg

    async def _perform_token_safety_check(
        self,
        chunk_id: int,
        main_prompt: Any,
        text_to_translate: str,
        translated_context_chunks: List[str],
        scene_characters: List[str],
        relevant_terms: List[Dict],
        contains_potential_title: bool,
        use_multi_turn: bool,
        override_instructions: Optional[str],
        api_key: Optional[str] = None,
    ) -> Any:
        """Kiểm tra và xử lý nếu prompt quá lớn."""
        try:
            # Ước tính nhanh (4 chars ~ 1 token)
            est_tokens = len(str(main_prompt)) // 4
            if est_tokens > 500000:  # Threshold an toàn
                logger.warning(
                    f"[Chunk {chunk_id}] Prompt might be too large (~{est_tokens} tokens). Checking exact count..."
                )
                exact_tokens = await self.gemini_service.count_tokens_async(
                    main_prompt, api_key=api_key
                )
                
                if exact_tokens > 900000:  # Gần giới hạn 1M
                    logger.error(
                        f"[Chunk {chunk_id}] Prompt TOO LARGE ({exact_tokens} > 900k). Truncating context."
                    )
                    # Rebuild prompt không có original context để tiết kiệm không gian
                    if hasattr(self.prompt_builder, "build_main_messages"):
                        main_prompt = self.prompt_builder.build_main_messages(
                            chunk_text=text_to_translate,
                            original_context_chunks=[],
                            translated_context_chunks=translated_context_chunks[-1:]
                            if translated_context_chunks else [],
                            relevant_terms=relevant_terms,
                            active_characters=list(set(scene_characters)),
                            contains_potential_title=contains_potential_title,
                        )
                    else:
                        main_prompt = self.prompt_builder.build_main_prompt(
                            chunk_text=text_to_translate,
                            original_context_chunks=[],
                            translated_context_chunks=translated_context_chunks[-1:]
                            if translated_context_chunks else [],
                            relevant_terms=relevant_terms,
                            active_characters=list(set(scene_characters)),
                            contains_potential_title=contains_potential_title,
                        )
        except Exception as e:
            logger.debug(f"[Chunk {chunk_id}] Token pre-check skipped: {e}")
            
        return main_prompt
