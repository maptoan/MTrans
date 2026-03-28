# -*- coding: utf-8 -*-
from __future__ import annotations

"""
PHIÊN BẢN v1.7.stable - STABLE (2025-10-27)
=================================================
Module NovelTranslator với thuật toán dịch theo ngữ cảnh (contextual) đã ổn định.

CẬP NHẬT v1.7.stable:
- Workflow mới với review và lựa chọn người dùng (1/2/3)
- Hybrid logic: lưu ngay (as_completed) + báo cáo batch
- Báo cáo tổng thời gian và chunk status chi tiết
- Fix lỗi chunks không được lưu vào progress
- Fix lỗi nhận diện sai số lượng chunk dịch bị xóa
- Fix lỗi option 3 không dịch lại chunks bị xóa
- Fix lỗi tên file chunk không khớp
- Menu lựa chọn ngắn gọn với số 1/2/3

LƯU Ý: Đây là phiên bản ổn định với workflow review hoàn chỉnh.
"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import google.api_core.exceptions

from src.utils.logger import suppress_grpc_logging
from src.utils.path_manager import get_output_dir, get_progress_dir

if TYPE_CHECKING:
    pass

logger = logging.getLogger("NovelTranslator")

# Regex pattern để nhận diện tiêu đề chương (tránh dịch tiêu đề thành văn bản thường)
TITLE_PATTERN = re.compile(
    r"^(?:Chapter|Chương|Hồi|Quyển|Book|Vol|Volume)\s+\d+|^\d+\.\s+(?:Chapter|Chương)|^(?:Chapter|Chương)\s+\d+\s*:",
    re.IGNORECASE | re.MULTILINE,
)


class NovelTranslator:
    def __init__(self, config: Dict[str, Any], valid_api_keys: List[str]):
        # Lazy imports for startup performance
        from src.preprocessing.chunker import SmartChunker
        from src.preprocessing.strategy_resolver import resolve_preprocessing_strategy
        from src.translation.initialization_service import InitializationService
        from src.utils.quality_profile import apply_quality_profile
        from src.utils.translation_validator import TranslationValidator

        self.config = resolve_preprocessing_strategy(apply_quality_profile(config))
        self.novel_path = self.config["input"]["novel_path"]
        self.novel_name = os.path.splitext(os.path.basename(self.novel_path))[0]
        self.valid_api_keys = valid_api_keys
        self._warm_up_completed = False

        # Phase 7: Initialization via Service
        self.init_service = InitializationService(self.config)

        # Sẽ được khởi tạo sau trong async.run hoặc setup_resources_async
        self.resources: Dict[str, Any] = {}
        self.key_manager = None
        self.metrics_collector = None
        self.error_handler = None
        self.model_router = None
        self.chunker = SmartChunker(self.config)
        self.style_manager = None
        self.glossary_manager = None
        self.relation_manager = None
        self.prompt_builder = None
        self.progress_manager = None
        self.output_formatter = None
        self.gemini_service = None
        self._request_semaphore = None
        self.context_manager = None

        self.worker_caches: Dict[str, str] = {}

        # Cache for compiled marker patterns (used in merge validation)
        self._marker_pattern_cache: Dict[int, Tuple[Any, Any]] = {}

        # Cache for convert utils module (used for EPUB conversion)
        self._convert_utils_cache = None

        # Phase 3.1: Translation Validator
        self.validator = TranslationValidator(self.config.get("validation", {}))

        # Phase 11: Batch QA issues collection
        self.batch_qa_issues = []
        self._batch_qa_lock = asyncio.Lock()

        # [REFACTOR] Modularized components initialized in setup_resources_async
        self.refiner = None
        self.qa_editor = None
        self.cjk_cleaner = None

        # Legacy/Compatibility attributes (needed for now)
        self.translation_config = self.config.get("translation", {})
        self.performance_config = self.config.get("performance", {})
        self.delay_between_requests = self.performance_config.get("delay_between_requests", 1.0)
        self.rate_limit_backoff_delay = self.performance_config.get("rate_limit_backoff_delay", 10)
        self.enable_final_cleanup_pass = self.translation_config.get("enable_final_cleanup_pass", False)
        self.suppress_logs = self.config.get("logging", {}).get("suppress_grpc_logs", True)
        self.show_chunk_progress = self.config.get("logging", {}).get("show_chunk_progress", True)

        # Output conversion cache
        self._pypandoc_cache = None

        # Use module constant
        self.title_pattern = TITLE_PATTERN

        # Residual retry pass config (v5.3 fix)
        self.residual_retry_pass_enabled = self.translation_config.get("residual_retry_pass", False)
        self.residual_retry_config = self.translation_config.get("residual_retry", {})

        # [CRITICAL UPDATE] Explicitly define CJK Pattern for validation
        # Range: Common CJK Unified Ideographs + Extensions + Compatibility
        self.cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")

        self.residual_todo_path = str(get_progress_dir(self.config) / f"{self.novel_name}_residual_todo.jsonl")

        chunking_cfg = self.config.get("preprocessing", {}).get("chunking", {})
        self.use_markers = bool(chunking_cfg.get("use_markers", True))

        # EPUB layout-preservation state (Phase 5)
        epub_cfg = self.config.get("preprocessing", {}).get("epub", {})
        self._epub_preserve_layout: bool = bool(epub_cfg.get("preserve_layout", False))
        self._epub_layout_state: Optional[Dict[str, Any]] = None

    async def setup_resources_async(self, shared_resources: Optional[Dict[str, Any]] = None) -> None:
        """Khởi tạo tài nguyên asynchronously (thay thế cho logic cũ trong __init__)."""
        from src.translation.execution_manager import ExecutionManager

        if self.resources:
            return

        if shared_resources:
            logger.info("Đang sử dụng tài nguyên chung đã khởi tạo...")
            self.resources = await self.init_service.initialize_novel_specific_resources(
                shared_resources, self.novel_name
            )
        else:
            self.resources = await self.init_service.initialize_all(self.valid_api_keys, self.novel_name)

        # Map resources back to instance for compatibility
        self.key_manager = self.resources["key_manager"]
        self.metrics_collector = self.resources["metrics_collector"]
        self.error_handler = self.resources["error_handler"]
        self.model_router = self.resources["model_router"]
        self.style_manager = self.resources["style_manager"]
        self.glossary_manager = self.resources["glossary_manager"]
        self.relation_manager = self.resources["relation_manager"]
        self.prompt_builder = self.resources["prompt_builder"]
        self.progress_manager = self.resources["progress_manager"]
        self.output_formatter = self.resources["output_formatter"]
        self.gemini_service = self.resources["gemini_service"]
        self._request_semaphore = self.resources["request_semaphore"]
        self.context_manager = self.resources["context_manager"]
        self.document_type = self.resources["document_type"]
        self.quota_detector = self.resources["quota_detector"]
        self.prompt_orchestrator = self.resources["prompt_orchestrator"]
        self.result_handler = self.resources["result_handler"]
        self.ui_handler = self.resources["ui_handler"]
        self.format_converter = self.resources["format_converter"]

        # [REFACTOR] Initialize modular components AFTER resources are fully loaded
        from src.translation.cjk_cleaner import CJKCleaner
        from src.translation.qa_editor import QAEditor
        from src.translation.refiners import TranslationRefiner

        self.refiner = TranslationRefiner(self.config, self.relation_manager)
        self.qa_editor = QAEditor(self.config, self.gemini_service, self.prompt_builder)
        self.cjk_cleaner = CJKCleaner(self.config, self.model_router)
        self.batch_qa_processor = self.resources["batch_qa_processor"]

        # Khởi tạo Execution Manager
        self.executor = ExecutionManager(self.resources, self.config)

        # Wire UIHandler callbacks
        self.ui_handler.set_callbacks(
            convert_to_epub=lambda txt: self.format_converter.convert_to_epub(txt, self.novel_name),
            convert_to_docx=self.format_converter.convert_to_docx,
            convert_to_pdf=self.format_converter.convert_to_pdf,
            merge_all_chunks=self._merge_all_chunks,
            translate_all_chunks=self._translate_all_chunks,
            find_deleted_chunks=self._find_deleted_chunks,
            progress_manager=self.progress_manager,
            export_master_html_to_epub=self._export_master_html_to_epub,
        )

        # KIỂM TRA METADATA CHỈ MỘT LẦN BAN ĐẦU
        self.init_service.check_metadata(self.resources)

        logger.info("Khởi tạo tài nguyên NovelTranslator thành công.")

    async def _warm_up_workers(self, api_keys: List[str]) -> Dict[str, str]:
        """Wrapper for InitializationService.warm_up_resources (Phase 8.3 Self-Healing)"""
        return await self.init_service.warm_up_resources(self.resources, api_keys)

    async def _recover_context_cache(self, api_key: str) -> Optional[str]:
        """
        [Phase 7.2] Recover context cache for a specific API key.

        Called when encountering 404 (cache expired) or similar errors.
        Rebuilds the static prefix cache using glossary and relations.

        Args:
            api_key: The API key that needs cache recovery.

        Returns:
            Cache name if recovery successful, None otherwise.
        """
        try:
            full_glossary = self.glossary_manager.get_full_glossary_dict()
            full_relations = self.relation_manager.get_full_relation_text()

            static_prefix = self.prompt_builder.build_cacheable_prefix(
                full_glossary=full_glossary, full_relations=full_relations
            )

            caching_config = self.translation_config.get("context_caching", {})
            ttl_minutes = caching_config.get("ttl_minutes", 60)
            # Phase 7.2: Use centralized model config
            cache_model = caching_config.get(
                "model", self.config.get("models", {}).get("flash", "gemini-3-flash-preview")
            )

            logger.warning(f"🔄 Đang khôi phục context cache cho key {api_key[:8]}...")
            cache_name = await self.gemini_service.get_or_create_context_cache(
                content=static_prefix,
                ttl_minutes=ttl_minutes,
                model_name=cache_model,
                api_key=api_key,
            )

            if cache_name:
                self.worker_caches[api_key] = cache_name
                logger.info(f"✅ Đã khôi phục cache cho key {api_key[:8]}: {cache_name}")
                return cache_name
            else:
                logger.warning(f"⚠️ Khôi phục cache trả về None cho key {api_key[:8]}")
        except Exception as e:
            logger.error(f"❌ Khôi phục cache thất bại cho key {api_key[:8]}: {e}")
        return None

    async def _get_worker_id(self) -> int:
        """
        Lấy worker ID duy nhất cho worker hiện tại.

        Returns:
            Worker ID
        """
        async with self._worker_id_lock:
            worker_id = self._worker_id_counter
            self._worker_id_counter += 1
            return worker_id

    # ==========================================
    # v5.3 HELPER METHODS FOR CHUNK TRANSLATION
    # ==========================================

    async def _build_translation_prompt(
        self,
        chunk_id: int,
        text_to_translate: str,
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        cache_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[Any, Optional[str], List[Dict], List[str]]:
        """v5.3: Build translation prompt. Delegated to prompt_orchestrator."""
        if not self.prompt_orchestrator:
            # Fallback initialization for Stage 5A migration period if needed
            from src.translation.prompt_orchestrator import PromptOrchestrator

            self.prompt_orchestrator = PromptOrchestrator(
                self.glossary_manager,
                self.relation_manager,
                self.prompt_builder,
                self.gemini_service,
                self.config,
                self.document_type,
            )

        return await self.prompt_orchestrator.build_translation_prompt(
            chunk_id, text_to_translate, original_context_chunks, translated_context_chunks, cache_name, api_key
        )

    def _validate_translation_result(
        self, chunk_id: int, main_result: Optional[Dict[str, Any]], text_to_translate: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """v5.3: Validate translation result. Delegated to result_handler."""
        if not self.result_handler:
            from src.translation.result_handler import ResultHandler

            self.result_handler = ResultHandler(self.metrics_collector)

        return self.result_handler.validate_translation_result(chunk_id, main_result, text_to_translate)

    def _record_token_usage(self, chunk_id: int, main_result: Dict[str, Any]) -> None:
        """v5.3: Record token usage metrics. Delegated to result_handler."""
        if not self.result_handler:
            from src.translation.result_handler import ResultHandler

            self.result_handler = ResultHandler(self.metrics_collector)

        self.result_handler.record_token_usage(chunk_id, main_result)

    async def _translate_one_chunk_worker(
        self,
        chunk: Dict[str, Any],
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        worker_id: Optional[int] = None,
        api_key: Optional[str] = None,
        cache_name: Optional[str] = None,
    ):
        """
        [WRAPPER] Delegates to _translate_one_chunk_worker_internal.
        This wrapper ensures compatibility with execution_manager.py.
        """
        return await self._translate_one_chunk_worker_internal(
            chunk,
            original_context_chunks,
            translated_context_chunks,
            worker_id=worker_id,
            api_key=api_key,
            cache_name=cache_name,
        )

    async def _translate_one_chunk_worker_internal(
        self,
        chunk: Dict[str, Any],
        original_context_chunks: List[str],
        translated_context_chunks: List[str],
        worker_id: Optional[int] = None,
        api_key: Optional[str] = None,
        cache_name: Optional[str] = None,
    ):
        # Lazy imports for method-level dependencies
        from src.utils.error_handler import ErrorContext

        from .exceptions import ContentBlockedError

        # Lấy worker_id nếu chưa có
        if worker_id is None:
            worker_id = await self._get_worker_id()

        chunk_id = chunk["global_id"]
        # Dynamic max_retries based on pool size to ensure rotation
        pool_size = len(self.valid_api_keys) if self.valid_api_keys else 1
        max_retries = max(5, pool_size * 2)

        attempt = 0
        draft_translation: Optional[str] = None  # Fallback partial: lưu bản nháp khi 100% quota
        while attempt < max_retries:
            with logger.context(f"Chunk-{chunk_id}"):
                with suppress_grpc_logging() if self.suppress_logs else open(os.devnull, "w", encoding="utf-8"):
                    try:
                        # Lấy key (ưu tiên key được truyền vào từ dedicated worker)
                        current_key = api_key or await self.key_manager.get_key_for_worker(worker_id)

                        if not current_key:
                            if attempt >= max_retries - 1:
                                logger.error("Không có API key khả dụng")
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": "No API key",
                                }
                            await asyncio.sleep(5)
                            attempt += 1
                            continue

                        text_to_translate = chunk["text"]
                        chunk_start_time = time.time()

                        # OPTIMIZATION: Global rate limiter + delay TRƯỚC KHI gửi request
                        async with self._request_semaphore:
                            await self.key_manager.add_delay_between_requests(current_key)

                            # --- BƯỚC 1: DỊCH & HOÀN THIỆN ---
                            # Sử dụng PromptOrchestrator để build prompt và check tokens
                            (
                                main_prompt,
                                cached_content_arg,
                                relevant_terms,
                                scene_characters,
                            ) = await self._build_translation_prompt(
                                chunk_id,
                                text_to_translate,
                                original_context_chunks,
                                translated_context_chunks,
                                cache_name=cache_name,
                                api_key=current_key,
                            )

                            # Log chunk start
                            logger.start("Bắt đầu dịch...")

                            complexity = self.model_router.analyze_chunk_complexity(
                                text_to_translate, len(relevant_terms)
                            )

                            complexity = self.model_router.analyze_chunk_complexity(
                                text_to_translate, len(relevant_terms)
                            )

                            main_result = await self.model_router.translate_chunk_async(
                                main_prompt,
                                complexity,
                                current_key,
                                cached_content=cached_content_arg,
                                key_manager=self.key_manager,
                            )

                        # Dọn dẹp rác Marker do AI sinh ra (nếu có) để tránh lọt vào bản dịch
                        if main_result and main_result.get("translation"):
                            # Hỗ trợ xóa chèn đầu/cuối của marker dạng [CHUNK:...]
                            cleaned_trans = re.sub(r"\[CHUNK:.*?\]\n?", "", main_result["translation"], flags=re.IGNORECASE).strip()
                            main_result["translation"] = cleaned_trans

                        # VALIDATION (Gate 1): Kiểm tra kết cấu hợp lệ
                        is_valid, final_translation, error_msg = self._validate_translation_result(
                            chunk_id, main_result, text_to_translate
                        )

                        if not is_valid:
                            logger.error(f"Gate 1 Fail (Cấu trúc): {error_msg}. Đang thử lại...")
                            # Return key trước khi tiếp tục retry
                            await self.key_manager.return_key(worker_id, current_key, is_error=True)
                            api_key = None  # Force key rotation
                            attempt += 1
                            continue

                        # VALIDATION (Gate 2): [v3] Kiểm tra Content Coverage (Paragraph Ratio)
                        if not self._check_content_coverage(final_translation, text_to_translate):
                            # Trigger Sub-chunk Fallback!
                            fallback_result = await self._translate_with_sub_chunk_fallback(
                                chunk,
                                text_to_translate,
                                original_context_chunks,
                                translated_context_chunks,
                                worker_id,
                                current_key,
                                cache_name,
                            )
                            if fallback_result:
                                final_translation = fallback_result
                                logger.info(f"Gate 2 đã phục hồi bằng Sub-chunk Fallback cho Chunk {chunk_id}.")
                            else:
                                logger.error(
                                    f"Gate 2 Fail: Sub-chunk Fallback cũng thất bại cho Chunk {chunk_id}. Đang thử lại..."
                                )
                                await self.key_manager.return_key(worker_id, current_key, is_error=True)
                                api_key = None
                                attempt += 1
                                continue
                        draft_translation = final_translation  # Fallback partial: cập nhật bản nháp sau Gate 1+2

                        # Ghi nhận token usage
                        self._record_token_usage(chunk_id, main_result)

                        # HẬU XỬ LÝ 1: Cưỡng bức nhất quán đại từ ở TRẦN THUẬT
                        try:
                            final_translation = self.refiner.enforce_narrative_terms(final_translation)
                        except Exception as e:
                            logger.warning(f"Lỗi khi thực thi đại từ trần thuật: {e}")

                        # HẬU XỬ LÝ 2: Enhanced Auto-Fix Glossary (Updated: Phase 11)
                        if self.config.get("translation", {}).get("auto_fix_glossary", True):
                            try:
                                fixed_translation, fix_count = self.refiner.auto_fix_glossary_enhanced(
                                    final_translation, relevant_terms, max_passes=2
                                )
                                if fix_count > 0:
                                    logger.info(
                                        f"[Chunk {chunk_id}] Multi-pass Auto-fix: Đã sửa {fix_count} thuật ngữ."
                                    )
                                    final_translation = fixed_translation
                            except Exception as e:
                                logger.warning(f"Lỗi khi chạy Enhanced Auto-fix: {e}")

                        # [HẬU XỬ LÝ 3] CJK DETECTION (Phase 11)
                        # Detection runs once here, result reused by QA Conditional Gate below.
                        qa_config = self.config.get("translation", {}).get("qa_editor", {})
                        remaining_cjk = self.refiner.detect_cjk_remaining(final_translation)
                        # [v3] Pre-compute compliance for reuse in QA Conditional Gate (avoid duplicate call)
                        is_glossary_compliant_precheck = True

                        chunk_issues = []
                        if remaining_cjk:
                            unique_cjk_count = len(set(remaining_cjk))
                            logger.info(f"[Chunk {chunk_id}] Phát hiện {unique_cjk_count} ký tự CJK còn sót.")

                            # Luôn thu thập issues cho Batch QA nếu enabled
                            if qa_config.get("enabled", False):
                                chunk_issues = self.batch_qa_processor.extract_issues(chunk_id, final_translation)

                        if chunk_issues:
                            async with self._batch_qa_lock:
                                self.batch_qa_issues.extend(chunk_issues)

                        # VALIDATION: Kiểm tra AI compliance với metadata
                        try:
                            is_compliant = self.refiner.validate_metadata_compliance(
                                final_translation,
                                relevant_terms,
                                scene_characters,
                                chunk_id,
                            )
                            is_glossary_compliant_precheck = is_compliant  # Cache for QA gate reuse

                            # [Phase 2] Strict Glossary Compliance
                            # Nếu vi phạm glossary -> Thử AutoFix lần cuối trước khi FAIL
                            strict_compliance = self.config.get("translation", {}).get(
                                "strict_glossary_compliance", True
                            )
                            if not is_compliant and strict_compliance:
                                error_msg = "Không tuân thủ Glossary/Metadata (Chế độ Strict)"

                                # [CẢI TIẾN - Tổ Chuyên Gia] Thử AutoFix lần cuối trước khi FAIL
                                fixed_translation, fix_count = self.refiner.auto_fix_glossary(
                                    final_translation, relevant_terms
                                )
                                if fix_count > 0:
                                    final_translation = fixed_translation
                                    logger.info(f"Post-validation Auto-fix: Đã sửa {fix_count} thuật ngữ.")
                                    # Re-validate với bản dịch đã fix
                                    is_compliant = self.refiner.validate_metadata_compliance(
                                        final_translation,
                                        relevant_terms,
                                        scene_characters,
                                        chunk_id,
                                    )

                                # Kiểm tra lại sau khi AutoFix
                                if not is_compliant:
                                    logger.error(f"{error_msg}. Đang thử lại...")

                                    # Return key as error
                                    await self.key_manager.return_key(worker_id, current_key, is_error=True)
                                    api_key = None
                                    attempt += 1
                                    continue
                                else:
                                    # Đã compliant sau khi fix -> Continue
                                    logger.info("Tuân thủ Metadata được khôi phục sau khi sửa lỗi Post-validation!")

                            # (Old block ends here)
                            # strict_compliance = self.config.get('translation', {}).get('strict_glossary_compliance', True)
                            # if not is_compliant and strict_compliance:

                        except Exception as e:
                            logger.warning(f"Lỗi khi validate metadata compliance: {e}")
                            # Tiếp tục nếu lỗi hệ thống validation (fail safe)

                        # (LOGIC MỚI - STRICT) --- BƯỚC 2: DỌN DẸP CƯỠNG BỨC ---
                        # Nếu bật cleanup, bắt buộc phải thành công. Nếu thất bại -> Failed Chunk.
                        if self.enable_final_cleanup_pass:
                            try:
                                final_translation = await self.cjk_cleaner.final_cleanup_pass(
                                    final_translation, api_key, chunk_id
                                )
                            except ValueError as ve:
                                # Critical: Cleanup thất bại (vẫn còn CJK) -> Fail Chunk để retry
                                error_msg = f"Dọn dẹp cuối cùng thất bại: {ve}"
                                logger.error(f"❌ {error_msg}")
                                # Trả key và báo lỗi
                                await self.key_manager.return_key(worker_id, current_key, is_error=True)
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": error_msg,
                                }
                            except Exception as e:
                                logger.warning(f"Lỗi hệ thống trong quá trình dọn dẹp cuối cùng: {e}")
                                # Lỗi khác (network/system) thì có thể retry hoặc ignore tùy policy.
                                # Ở đây chọn an toàn: Fail chunk để retry cho chắc chắn.
                                await self.key_manager.return_key(worker_id, current_key, is_error=True)
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": f"System Error during Cleanup: {e}",
                                }

                        # PHASE 3.1: Validating Structural Integrity
                        validation_result = self.validator.validate(text_to_translate, final_translation)
                        if not validation_result["is_valid"]:
                            error_issues = "; ".join(validation_result["issues"])
                            logger.info(f"Phát hiện vấn đề validation (kích hoạt tự động sửa): {error_issues}")

                            # Nếu là lỗi nghiêm trọng (critical), coi như failed để retry
                            if validation_result.get("has_critical_error"):
                                # Return key trước khi return failed
                                await self.key_manager.return_key(
                                    worker_id, current_key, is_error=True
                                )  # Coi như lỗi logic, trả key nhưng có thể không cần mark error API
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": f"Lỗi Validation: {error_issues}",
                                }

                        # VALIDATION: Kiểm tra lại sau cleanup
                        try:
                            if not final_translation or not final_translation.strip():
                                error_msg = "final_translation bị rỗng sau khi dọn dẹp"
                                logger.error(error_msg)
                                raise ValueError(error_msg)
                        except ValueError as validation_error:
                            # Return failed chunk thay vì raise để tránh crash
                            error_msg = str(validation_error)
                            logger.error(f"Lỗi validation sau khi dọn dẹp: {error_msg}")
                            # Return key trước khi return failed
                            await self.key_manager.return_key(worker_id, current_key, is_error=True)
                            return {
                                "chunk_id": chunk_id,
                                "status": "failed",
                                "translation": None,
                                "error": error_msg,
                            }

                        # [PHASE 7.5 ENHANCED] QA EDITOR PIPELINE
                        # Reuse qa_config, remaining_cjk, is_glossary_compliant from earlier blocks (avoid duplicate calls)
                        qa_enabled = qa_config.get("enabled", False)
                        cjk_remaining = remaining_cjk  # Reuse from L495

                        # [v3 Optimization Strategy B] QA Conditional Gate & Gate 3
                        is_glossary_compliant = is_glossary_compliant_precheck  # Reuse from L510-518

                        # Gate 3: CJK threshold (≤ 5 is acceptable for names/glossary)
                        has_gate3_issues = cjk_remaining and len(cjk_remaining) > 5

                        # Decide whether to run QA Editor
                        if qa_enabled:
                            # Nếu mandatory QA: Chỉ skip nếu glossary OK VÀ CJK <= 5
                            should_run_qa = (not is_glossary_compliant) or has_gate3_issues
                        else:
                            # Nếu không mandatory: Chỉ trigger nếu CJK > 5
                            should_run_qa = has_gate3_issues

                        if should_run_qa:
                            # Determine trigger reason for logging
                            reason = []
                            if qa_enabled:
                                if not is_glossary_compliant:
                                    reason.append("Vi phạm Glossary")
                                if has_gate3_issues:
                                    reason.append(f"Gate 3 Fail (CJK: {len(cjk_remaining)})")
                                if not reason:
                                    reason.append("QA Bắt buộc")
                            else:
                                reason.append(f"Phát hiện CJK ({len(cjk_remaining)})")
                            reason_str = ", ".join(reason)

                            logger.start(f"Kích hoạt QA Editor Pass [{reason_str}]...")

                            # 1. Detect Active Characters & Relations (for Role Check)
                            relations_text = ""
                            if hasattr(self, "relation_manager") and self.relation_manager.is_loaded():
                                try:
                                    # Scan draft for names to get relevant addressing rules
                                    active_chars = self.relation_manager.find_active_characters(final_translation)
                                    if active_chars:
                                        relations_text = self.relation_manager.build_prompt_section(active_chars)
                                        narrative_text = self.relation_manager.build_narrative_prompt_section(
                                            active_chars
                                        )
                                        if narrative_text:
                                            relations_text = (
                                                (relations_text + "\n\n" + narrative_text)
                                                if relations_text
                                                else narrative_text
                                            )
                                except Exception as re_err:
                                    logger.warning(f"Không thể tạo relations cho QA: {re_err}")

                            # 2. Execute QA Pass
                            fixed_translation = await self.qa_editor.perform_qa_edit(
                                draft_translation=final_translation,
                                relevant_terms=relevant_terms,
                                api_key=current_key,
                                chunk_id=chunk_id,
                                source_text=text_to_translate,
                                cjk_remaining=cjk_remaining,
                                character_relations=relations_text,
                                worker_id=worker_id,
                            )

                            # 3. Validation & Commit
                            if fixed_translation and fixed_translation != final_translation:
                                # Re-check CJK
                                cjk_after = self.refiner.detect_cjk_remaining(fixed_translation)
                                if len(cjk_after) < len(cjk_remaining):
                                    logger.info(f"QA CJK Fix: {len(cjk_remaining)} -> {len(cjk_after)}")

                                final_translation = fixed_translation
                            else:
                                logger.info("QA Pass giữ nguyên bản nháp gốc (không có thay đổi hoặc đã hủy).")
                            draft_translation = final_translation  # Fallback partial: cập nhật sau QA
                        elif qa_enabled:
                            logger.debug("[v3 Optimization] Bỏ qua QA Editor: Chunk sạch (Không CJK, Glossary OK).")
                        else:
                            logger.debug("Bỏ qua QA Editor (Đã tắt & Không CJK).")

                        # Phase 14: Surgical CJK Cleanup Pass (Contextual Sentence)
                        # Only runs if enable_final_cleanup_pass is True in config
                        cleanup_enabled = self.config.get("translation", {}).get("enable_final_cleanup_pass", False)
                        if cleanup_enabled and hasattr(self, "cjk_cleaner") and self.cjk_cleaner and current_key:
                            try:
                                logger.start(f"[Chunk {chunk_id}] Khởi chạy Surgical CJK Cleanup...")
                                cleaned_translation = await self.cjk_cleaner.final_cleanup_pass(
                                    final_translation, current_key, chunk_id, worker_id=worker_id
                                )
                                if cleaned_translation != final_translation:
                                    logger.info(f"[Chunk {chunk_id}] Đã áp dụng Surgical CJK Cleanup.")
                                    final_translation = cleaned_translation
                            except Exception as cjk_err:
                                logger.error(f"Surgical CJK Cleanup thất bại: {cjk_err}")
                            draft_translation = final_translation  # Fallback partial: cập nhật sau cleanup

                        # Phase 14: Final Integrity Guard
                        if not self._validate_translated_content(final_translation, text_to_translate):
                            raise ValueError(
                                f"Bản dịch Chunk {chunk_id} không đạt yêu cầu chất lượng (Content Loss hoặc thiếu Marker)."
                            )

                        # Log chunk completion với thống kê chi tiết (rút gọn)

                        chunk_tokens = self._count_tokens(final_translation)
                        chunk_duration = time.time() - chunk_start_time
                        chunk_speed = chunk_tokens / chunk_duration if chunk_duration > 0 else 0

                        # Phase 3: Record metrics
                        model_used = main_result.get("model_used", "unknown")
                        self.metrics_collector.record_chunk_translation(
                            chunk_id=chunk_id,
                            status="success",
                            duration=chunk_duration,
                            model_used=model_used,
                        )
                        self.metrics_collector.record_api_key_usage(
                            key=current_key, success=True, duration=chunk_duration
                        )

                        if getattr(self, "show_chunk_progress", True):
                            logger.info(f"Dịch xong ({chunk_tokens}t, {chunk_duration:.1f}s)")
                        else:
                            logger.debug(f"Hoàn thành ({chunk_tokens}t, {chunk_duration:.1f}s, {chunk_speed:.1f}t/s)")

                        # Mark success và trả key (dedicated key sẽ được giữ lại)
                        self.key_manager.mark_request_success(current_key)  # Sync function - no await
                        await self.key_manager.return_key(worker_id, current_key, is_error=False)

                        return {
                            "chunk_id": chunk_id,
                            "status": "success",
                            "translation": final_translation,
                            "error": None,
                        }

                    except google.api_core.exceptions.ResourceExhausted as e:
                        # Kiểm tra xem có phải quota/rate limit error không (cả SDK cũ và mới)
                        error_type_name = type(e).__name__
                        error_msg = str(e)
                        error_msg_lower = error_msg.lower()

                        # OPTIMIZATION 2.2: Fast quota error detection với early exit
                        is_quota_error = self._is_quota_error_fast(e, error_type_name, error_msg, error_msg_lower)

                        if is_quota_error:
                            # Phase 1.1: Use Centralized Error Handler để normalize error type
                            error_context = ErrorContext(
                                chunk_id=chunk_id,
                                api_key=api_key,
                                worker_id=worker_id,
                                retry_count=attempt,
                            )
                            error_info = self.error_handler.handle_error(
                                error=e, context=error_context, error_message=error_msg
                            )
                            normalized_error_type = error_info.get("error_type", "quota_exceeded")

                            from src.utils.error_formatter import format_api_error

                            error_short = format_api_error(e, context=f"Chunk {chunk_id}")
                            # Chỉ log warning một lần cho mỗi chunk
                            if attempt == 0:
                                logger.warning(f"[Chunk {chunk_id}] {error_short}")
                            else:
                                logger.debug(f"[Chunk {chunk_id}] {error_short}")

                            if current_key:
                                # Chỉ return_key; mark_request_error được gọi bên trong return_key (tránh đếm trùng)
                                await self.key_manager.return_key(
                                    worker_id,
                                    current_key,
                                    is_error=True,
                                    error_type=normalized_error_type,
                                    error_message=str(e),
                                )

                            # Force rotation for next attempt
                            api_key = None

                            # Lấy thống kê quota status (chỉ log một lần)
                            quota_status = self.key_manager.get_quota_status_summary()
                            quota_blocked_ratio = quota_status.get("quota_blocked_ratio", 0)
                            available_keys = quota_status.get("available_keys", 0)

                            # Nếu 100% keys bị quota hoặc không có keys khả dụng
                            if quota_blocked_ratio >= 1.0 or available_keys == 0:
                                if quota_status.get("earliest_reset_time"):
                                    wait_minutes = (
                                        quota_status["earliest_reset_time"] - datetime.now()
                                    ).total_seconds() / 60
                                else:
                                    wait_minutes = 0

                                # Fallback partial: nếu đã có bản nháp thì lưu và trả partial thay vì failed
                                if draft_translation and draft_translation.strip():
                                    logger.warning(
                                        f"⚠️ [Chunk {chunk_id}] 100% keys quota. Lưu bản nháp (partial) thay vì failed."
                                    )
                                    self.progress_manager.save_chunk_result(
                                        chunk_id,
                                        draft_translation,
                                        metadata={"status": "partial", "reason": "quota_exceeded"},
                                    )
                                    chunk_duration = time.time() - chunk_start_time
                                    self.metrics_collector.record_chunk_translation(
                                        chunk_id=chunk_id,
                                        status="partial",
                                        duration=chunk_duration,
                                        error_type="quota_exceeded",
                                    )
                                    if current_key:
                                        self.metrics_collector.record_api_key_usage(
                                            key=current_key,
                                            success=False,
                                            duration=chunk_duration,
                                            error_type="quota_exceeded",
                                        )
                                    await self.key_manager.return_key(
                                        worker_id,
                                        current_key,
                                        is_error=True,
                                        error_type="quota_exceeded",
                                        error_message=str(e),
                                    )
                                    return {
                                        "chunk_id": chunk_id,
                                        "status": "partial",
                                        "translation": draft_translation,
                                        "error": f"100% keys quota; saved draft (reset in {wait_minutes:.0f} min)",
                                    }

                                logger.error(
                                    f"❌ [Chunk {chunk_id}] Không có keys khả dụng! "
                                    f"(100% keys bị quota: {quota_status['quota_blocked_keys']}/{quota_status['total_keys']})"
                                )
                                if wait_minutes > 0:
                                    logger.error(f"⏰ Keys sẽ reset sau {wait_minutes:.0f} phút")

                                # Phase 3: Record metrics for failed chunk (không có draft)
                                chunk_duration = time.time() - chunk_start_time
                                self.metrics_collector.record_chunk_translation(
                                    chunk_id=chunk_id,
                                    status="failed",
                                    duration=chunk_duration,
                                    error_type="quota_exceeded",
                                )
                                if current_key:
                                    self.metrics_collector.record_api_key_usage(
                                        key=current_key,
                                        success=False,
                                        duration=chunk_duration,
                                        error_type="quota_exceeded",
                                    )
                                await self.key_manager.return_key(
                                    worker_id,
                                    current_key,
                                    is_error=True,
                                    error_type="quota_exceeded",
                                    error_message=str(e),
                                )
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": f"No available API keys (100% quota exceeded, reset in {wait_minutes:.0f} minutes)",
                                }

                            if quota_blocked_ratio > 0.5 and attempt == 0:
                                logger.error(
                                    f"⚠️ {quota_blocked_ratio:.0%} keys bị quota "
                                    f"({quota_status['quota_blocked_keys']}/{quota_status['total_keys']})"
                                )
                                if quota_status.get("earliest_reset_time"):
                                    wait_minutes = (
                                        quota_status["earliest_reset_time"] - datetime.now()
                                    ).total_seconds() / 60
                                    logger.info(f"⏰ Reset sau {wait_minutes:.0f} phút")

                            api_key = None

                            # Dynamic delay dựa trên quota status + Jitter để tránh thundering herd
                            import random

                            jitter = random.uniform(0.8, 1.2)

                            if quota_blocked_ratio > 0.7:
                                delay = self.rate_limit_backoff_delay * 2 * jitter
                                if attempt == 0:
                                    logger.warning(f"[Chunk {chunk_id}] Nhiều keys bị quota, tạm dừng {delay:.1f}s")
                            else:
                                delay = self.rate_limit_backoff_delay * jitter
                                logger.debug(f"[Chunk {chunk_id}] Tạm dừng {delay:.1f}s")

                            await asyncio.sleep(delay)
                            logger.debug(f"[Chunk {chunk_id}] Thử lại với key khác...")
                            continue

                        # Nếu không phải quota error, tiếp tục xử lý như exception khác
                        raise

                    except google.api_core.exceptions.NotFound as e:
                        # Self-healing for expired/invalid context cache (Stage 4)
                        error_msg = str(e).lower()
                        if ("cache" in error_msg or "context" in error_msg) and cache_name:
                            logger.warning(
                                f"⚠️ [Chunk {chunk_id}] Cache {cache_name} không tìm thấy (có thể đã hết hạn). Đang khởi tạo lại..."
                            )
                            # Xóa cache lỗi khỏi registry local
                            self.gemini_service.delete_context_cache(cache_name, api_key=current_key)
                            # Re-warm up key này
                            new_caches = await self._warm_up_workers([current_key])
                            if current_key in new_caches:
                                cache_name = new_caches[current_key]
                                logger.info(f"✅ [Chunk {chunk_id}] Đã tạo cache mới: {cache_name}")

                            attempt += 1
                            await asyncio.sleep(2)
                            continue
                        raise

                    except (
                        google.api_core.exceptions.DeadlineExceeded,
                        google.api_core.exceptions.ServiceUnavailable,
                        google.api_core.exceptions.InternalServerError,
                        ContentBlockedError,
                    ) as e:
                        # Phase 1.1: Use Centralized Error Handler
                        error_context = ErrorContext(
                            chunk_id=chunk_id,
                            api_key=api_key,
                            worker_id=worker_id,
                            retry_count=attempt,
                        )
                        error_info = self.error_handler.handle_error(
                            error=e, context=error_context, error_message=str(e)
                        )
                        normalized_error_type = error_info.get("error_type", "unknown")

                        attempt += 1
                        error_type = "PROHIBITED_CONTENT" if isinstance(e, ContentBlockedError) else type(e).__name__
                        # Rút gọn: chỉ log khi attempt đầu tiên hoặc cuối cùng
                        if attempt == 1 or attempt == max_retries:
                            logger.warning(f"[Chunk {chunk_id}] {error_type}, retry {attempt}/{max_retries}")
                        else:
                            logger.debug(f"[Chunk {chunk_id}] {error_type}, retry {attempt}/{max_retries}")
                        if current_key:
                            # Chỉ return_key; mark_request_error được gọi bên trong return_key (tránh đếm trùng)
                            await self.key_manager.return_key(
                                worker_id,
                                current_key,
                                is_error=True,
                                error_type=normalized_error_type,
                                error_message=str(e),
                            )

                        # Force rotation
                        api_key = None

                        # KIỂM TRA CHIẾN LƯỢC PHỤC HỒI
                        recovery_strategy = error_info.get("recovery_strategy", {})
                        if not recovery_strategy.get("should_retry", True):
                            logger.error(f"[Chunk {chunk_id}] Lỗi không thể hồi phục ({normalized_error_type}): {e}")
                            return {
                                "chunk_id": chunk_id,
                                "status": "failed",
                                "translation": None,
                                "error": f"Lỗi không thể hồi phục: {e}",
                            }

                        # PHASE 2.1: Tiered Retry Strategy (Fast/Slow)
                        base_cooldown = recovery_strategy.get("cooldown_time", 5)
                        # Nếu cooldown nhỏ (Fast Retry), tăng dần theo attempt (linear backoff)
                        if base_cooldown < 10:
                            actual_delay = base_cooldown * attempt
                        else:
                            # Nếu cooldown lớn (Slow Retry like Quota), giữ nguyên
                            actual_delay = base_cooldown

                        # Add Jitter
                        import random

                        actual_delay += random.uniform(0.1, 1.0)

                        logger.debug(f"[Chunk {chunk_id}] Sleeping {actual_delay:.1f}s before retry...")
                        await asyncio.sleep(actual_delay)
                        continue

                    except ValueError as e:
                        # Phase 14: Save Guard validation failure — retryable
                        attempt += 1
                        logger.warning(f"[Chunk {chunk_id}] Validation failed (retry {attempt}/{max_retries}): {e}")
                        if attempt >= max_retries:
                            logger.error(f"[Chunk {chunk_id}] Validation failed after {max_retries} retries.")
                            return {
                                "chunk_id": chunk_id,
                                "status": "failed",
                                "translation": None,
                                "error": f"Content validation failed: {e}",
                            }
                        await asyncio.sleep(2)
                        continue

                    except Exception as e:
                        # [PHASE 10] Robust Error Handling for all SDKs
                        error_type_name = type(e).__name__
                        error_msg = str(e)
                        error_msg_lower = error_msg.lower()

                        # Detect Quota Error specifically (handle errors from both old/new SDKs)
                        is_quota_error = self._is_quota_error_fast(e, error_type_name, error_msg, error_msg_lower)

                        if is_quota_error:
                            # Re-use quota handling logic
                            error_context = ErrorContext(
                                chunk_id=chunk_id,
                                api_key=api_key,
                                worker_id=worker_id,
                                retry_count=attempt,
                            )
                            error_info = self.error_handler.handle_error(
                                error=e, context=error_context, error_message=error_msg
                            )
                            normalized_error_type = error_info.get("error_type", "quota_exceeded")

                            from src.utils.error_formatter import format_api_error

                            error_short = format_api_error(e, context=f"Chunk {chunk_id}")
                            logger.warning(f"[Chunk {chunk_id}] Quota error detected: {error_short}")

                            if current_key:
                                # Cập nhật trạng thái key với classifier tập trung
                                classified_error_type = self.key_manager.handle_exception(current_key, e)
                                await self.key_manager.return_key(
                                    worker_id,
                                    current_key,
                                    is_error=True,
                                    error_type=classified_error_type,
                                    error_message=str(e),
                                )

                            # Force rotation
                            api_key = None

                            # Check system-wide quota
                            quota_status = self.key_manager.get_quota_status_summary()
                            quota_blocked_ratio = quota_status.get("quota_blocked_ratio", 0)
                            available_keys = quota_status.get("available_keys", 0)

                            if quota_blocked_ratio >= 1.0 or available_keys == 0:
                                # Fallback partial: nếu đã có bản nháp thì lưu và trả partial
                                if draft_translation and draft_translation.strip():
                                    logger.warning(
                                        f"⚠️ [Chunk {chunk_id}] 100% keys quota. Lưu bản nháp (partial) thay vì failed."
                                    )
                                    self.progress_manager.save_chunk_result(
                                        chunk_id,
                                        draft_translation,
                                        metadata={"status": "partial", "reason": "quota_exceeded"},
                                    )
                                    await self.key_manager.return_key(
                                        worker_id,
                                        current_key,
                                        is_error=True,
                                        error_type=classified_error_type,
                                        error_message=str(e),
                                    )
                                    return {
                                        "chunk_id": chunk_id,
                                        "status": "partial",
                                        "translation": draft_translation,
                                        "error": "100% keys quota; saved draft",
                                    }
                                logger.error(f"❌ [Chunk {chunk_id}] 100% keys bị quota. Failing chunk.")
                                return {
                                    "chunk_id": chunk_id,
                                    "status": "failed",
                                    "translation": None,
                                    "error": "No available API keys (100% quota exceeded)",
                                }

                            # Continue to retry with new key
                            await asyncio.sleep(self.rate_limit_backoff_delay)
                            continue

                        # Phase 1.1: Use Centralized Error Handler for other errors
                        error_context = ErrorContext(
                            chunk_id=chunk_id,
                            api_key=api_key,
                            worker_id=worker_id,
                            retry_count=attempt,
                        )
                        error_info_handler = self.error_handler.handle_error(
                            error=e, context=error_context, error_message=error_msg
                        )
                        normalized_error_type = error_info_handler.get("error_type", "unknown")

                        # RECOVERY LOGIC: Cache Not Found
                        if normalized_error_type == "cache_not_found" and api_key:
                            logger.warning(f"[Chunk {chunk_id}] Cache missing/expired. Recovering...")
                            new_cache = await self._recover_context_cache(api_key)
                            if new_cache:
                                cache_name = new_cache
                                attempt += 1
                                await asyncio.sleep(2)
                                continue

                        from src.utils.error_formatter import (
                            format_exception_for_logging,
                        )

                        error_info = format_exception_for_logging(e, context=f"Chunk {chunk_id}")

                        error_type = error_info["type"]
                        error_msg = error_info["message"]
                        if current_key:
                            classified_error_type = self.key_manager.handle_exception(current_key, e)
                            await self.key_manager.return_key(
                                worker_id,
                                current_key,
                                is_error=True,
                                error_type=classified_error_type,
                                error_message=str(e),
                            )

                        # Force rotation
                        api_key = None

                        logger.error(f"[Chunk {chunk_id}] Lỗi không thể thử lại: {error_info['short']}")
                        logger.debug(f"[Chunk {chunk_id}] Full error details:\n{error_info['full']}")
                        return {
                            "chunk_id": chunk_id,
                            "status": "failed",
                            "translation": None,
                            "error": f"Lỗi không thể thử lại: {error_type}: {error_msg}",
                        }

        final_error_reason = f"Thất bại sau {max_retries} lần thử (Timeout/Bị chặn)"
        logger.error(f"[Chunk {chunk_id}] Thất bại hoàn toàn sau {max_retries} lần thử lại dịch thuật.")
        return {
            "chunk_id": chunk_id,
            "status": "failed",
            "translation": None,
            "error": final_error_reason,
        }

    # --- MODULARIZED METHODS (Moved to refiners.py, qa_editor.py, cjk_cleaner.py) ---

    def _is_quota_error_fast(
        self,
        exception: Exception,
        error_type_name: str,
        error_msg: str,
        error_msg_lower: str,
    ) -> bool:
        """OPTIMIZATION 2.2: Fast quota error detection. Delegated to quota_detector."""
        if not self.quota_detector:
            from src.translation.quota_detector import QuotaDetector

            self.quota_detector = QuotaDetector()

        return self.quota_detector.is_quota_error(exception, error_type_name, error_msg)

    def _count_tokens(self, text: str) -> int:
        """
        Đếm số tokens trong text (sử dụng cùng logic với chunker).
        """
        return self.chunker._count_tokens(text)

    def _validate_translated_content(self, translation: str, original_text: str) -> bool:
        """
        [Phase 14] Kiểm tra tính hợp lệ của bản dịch (Gate 1):
        1. Không được rỗng.
        2. Phải chứa marker END (nếu sử dụng markers).
        3. Độ dài không được quá ngắn so với bản gốc (tránh truncation/content loss).
        4. [v3] Kiểm tra cắt cụt giữa câu (phải kết thúc bằng dấu câu hoặc marker).
        """
        if not translation or len(translation.strip()) < 10:
            logger.warning("Bản dịch rỗng hoặc quá ngắn.")
            return False

        if getattr(self, "use_markers", False):
            # CẬP NHẬT: Sử dụng regex linh hoạt hỗ trợ tiền tố (session_id:chunk_id)
            if not re.search(r"\[CHUNK:.*?:START\]", translation) or not re.search(r"\[CHUNK:.*?:END\]", translation):
                # Fallback: Kiểm tra format đơn giản nếu regex phức tạp không khớp (cho an toàn)
                if "[CHUNK:" not in translation or ":END]" not in translation:
                    logger.warning("Bản dịch thiếu marker [CHUNK:ID:END]. Nghi ngờ bị cắt cụt.")
                    return False

        # Kiểm tra tỷ lệ độ dài (Vietnamese thường dài hơn hoặc tương đương Chinese chars)
        # Nếu bản dịch < 20% bản gốc -> Nghi ngờ content loss
        if len(translation) < len(original_text) * 0.2:
            logger.warning(
                "Tỷ lệ bản dịch quá ngắn so với gốc."
            )
            return False

        return True

    def _check_content_coverage(self, original_text: str, translation: str) -> bool:
        """
        Kiểm tra xem bản dịch có khả năng bị mất nội dung khi dịch chunk lớn (20K).

        Sử dụng 3 metrics:
        1. Character length ratio (primary) — đáng tin cậy nhất cho CJK→Vi
        2. Paragraph count ratio (secondary, relaxed) — phát hiện mất đoạn nghiêm trọng
        3. Chapter header count — phát hiện mất tiêu đề chương
        """
        orig_paras = [p for p in original_text.split("\n") if p.strip()]
        trans_paras = [p for p in translation.split("\n") if p.strip()]

        if not orig_paras:
            return True

        # 1. Kiểm tra Character Length Ratio (primary metric)
        # Vietnamese translation thường dài bằng hoặc hơn CJK gốc.
        # Tuy nhiên, với tiếng Anh (Latin) -> Tiếng Việt, tỷ lệ này có thể thấp hơn (0.6 - 0.9)
        # nhưng hiếm khi < 0.3 trừ khi bị mất nội dung.
        orig_len = max(len(original_text.strip()), 1)
        char_ratio = len(translation.strip()) / orig_len
        
        # [v9.2.0] Relaxed threshold for non-CJK sources or general robustness
        # Nếu là tiếng Anh, char_ratio khoảng 0.7 - 1.2 là bình thường.
        # Nếu là tiếng Trung, char_ratio thường > 1.5.
        # Ta dùng ngưỡng 0.25 để an toàn cho cả hai.
        min_char_ratio = 0.25
        
        if char_ratio < min_char_ratio:
            logger.warning(
                f"Content Coverage Fail (char ratio): {char_ratio:.1%} — bản dịch quá ngắn so với gốc. (Threshold: {min_char_ratio})"
            )
            return False
            
        # 2. Kiểm tra Paragraph Ratio (secondary, relaxed threshold)
        # CJK text thường có 1 câu/dòng, Vietnamese gộp thành ít đoạn hơn.
        # Với English source, paragraphs thường dài sẵn nên ratio sẽ cao hơn (>0.8).
        # Tuy nhiên, để tránh skip nhầm, ta giảm ngưỡng xuống 0.25 cho an toàn.
        ratio = len(trans_paras) / len(orig_paras)
        min_para_ratio = 0.25
        
        if ratio < min_para_ratio:
            logger.warning(
                f"Content Coverage Fail (para ratio): {len(trans_paras)}/{len(orig_paras)} paragraphs ({ratio:.1%}). (Threshold: {min_para_ratio})"
            )
            return False

        # 3. Kiểm tra Chapter Header Count (Strategy E Gap Fix)
        orig_titles = TITLE_PATTERN.findall(original_text)
        trans_titles = TITLE_PATTERN.findall(translation)

        if len(orig_titles) > 0 and len(trans_titles) != len(orig_titles):
            logger.warning(
                f"Chapter Header Mismatch: {len(trans_titles)} in translation vs {len(orig_titles)} in original. Triggering Sub-chunk Fallback!"
            )
            return False

        return True

    async def _translate_with_sub_chunk_fallback(
        self,
        chunk: Dict[str, Any],
        text_to_translate: str,
        original_context: List[str],
        translated_context: List[str],
        worker_id: int,
        api_key: str,
        cache_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        [v3 Optimization] Sub-chunk Fallback: Chia nhỏ chunk 20K thành 2x10K và dịch tuần tự với context chaining.
        """
        chunk_id = chunk["global_id"]
        logger.info(f"🔄 [Sub-chunk Fallback] Chia nhỏ Chunk {chunk_id} thành 2 phần...")

        # Khi dùng markers, tránh để START/END bị tách ra hai nửa khiến AI không được ép preserve marker.
        # Cách làm: bóc marker ra khỏi text, split nội dung thuần, rồi gắn START vào A và END vào B.
        if getattr(self, "use_markers", False):
            start_marker = f"[CHUNK:{chunk_id}:START]"
            end_marker = f"[CHUNK:{chunk_id}:END]"

            # bóc marker (best-effort)
            text_core = text_to_translate.replace(start_marker, "").replace(end_marker, "").strip()
        else:
            start_marker = ""
            end_marker = ""
            text_core = text_to_translate

        # 1. Tìm điểm chia tại paragraph break gần giữa nhất
        mid = len(text_core) // 2
        # Tìm '\n\n' hoặc '\n' trong khoảng ±2000 chars từ điểm giữa
        break_pos = text_core.rfind("\n", max(0, mid - 2000), mid + 2000)

        if break_pos == -1:
            break_pos = mid  # Không tìm thấy paragraph break, chia đôi cứng

        text_a = text_core[:break_pos].strip()
        text_b = text_core[break_pos:].strip()

        if start_marker:
            text_a = f"{start_marker}\n{text_a}".strip()
        if end_marker:
            text_b = f"{text_b}\n{end_marker}".strip()

        logger.info(f"Sub-chunk A: {len(text_a)} chars, Sub-chunk B: {len(text_b)} chars.")

        # 2. Dịch Sub-chunk A (Context = Chunk N-1 cũ)
        # Tạo bản sao chunk để không ảnh hưởng gốc
        chunk_a = chunk.copy()
        chunk_a["text"] = text_a

        # Gọi _translate_one_chunk_worker_internal trực tiếp nhưng cẩn thận loop
        # Chúng ta dùng helper đơn giản hơn để tránh recursion phức tạp
        res_a = await self.model_router.translate_chunk_async(
            await self._build_simple_prompt(text_a, original_context, translated_context),
            "fast",
            api_key,
            cached_content=None,
            key_manager=self.key_manager,
        )

        translation_a = res_a.get("translation") if res_a else None
        if not translation_a:
            logger.error("Dịch Sub-chunk A thất bại.")
            return None

        # 3. Dịch Sub-chunk B (Context = Kết quả Sub-chunk A)
        # Quan trọng: original_context=[text_a], translated_context=[translation_a]
        res_b = await self.model_router.translate_chunk_async(
            await self._build_simple_prompt(text_b, [text_a], [translation_a]),
            "fast",
            api_key,
            cached_content=None,
            key_manager=self.key_manager,
        )

        translation_b = res_b.get("translation") if res_b else None
        if not translation_b:
            logger.error("Dịch Sub-chunk B thất bại. Retry toàn chunk.")
            return None  # Return None để retry toàn bộ chunk (theo plan)

        # 4. Merge kết quả
        merged = translation_a.strip() + "\n\n" + translation_b.strip()
        logger.info(f"✅ Sub-chunk Fallback hoàn tất cho Chunk {chunk_id}.")
        return merged

    async def _build_simple_prompt(self, text: str, orig_ctx: List[str], trans_ctx: List[str]) -> str:
        """Helper to build a simple prompt for sub-chunks without full orchestrator overhead."""
        # Tái sử dụng logic build prompt nhưng rút gọn
        prompt, _, _, _ = await self._build_translation_prompt(
            -1, text, orig_ctx, trans_ctx, cache_name=None, api_key=None
        )
        return prompt

    async def _prepare_translation(self) -> Tuple[List[Dict], Optional[str]]:
        """
        Phase 1: Chuẩn bị dữ liệu cho quá trình dịch.
        - Nếu EPUB + preserve_layout: dùng parser/layout pipeline.
        - Ngược lại: dùng luồng TXT cũ (parse_file + clean_text + chunk_novel).

        Returns:
            Tuple[List[Dict], Optional[str]]: (all_chunks, cleaned_text) hoặc ([], None) nếu lỗi
        """
        _prep_t0 = time.perf_counter()
        _prep_strategy = (self.config.get("preprocessing") or {}).get("strategy") or "legacy"

        # EPUB layout-preservation branch
        if self._epub_preserve_layout and self.novel_path.lower().endswith(".epub"):
            from src.preprocessing.chunker_epub import build_chunks_from_text_map
            from src.preprocessing.epub_layout_parser import parse_epub_with_layout

            logger.info("📚 Đang đọc EPUB với chế độ preserve_layout (EPUB Layout Mode).")

            layout_result = parse_epub_with_layout(self.novel_path)
            text_map: List[Dict[str, Any]] = layout_result.get("text_map", [])
            chapters_html: Dict[str, str] = layout_result.get("chapters_html", {})
            metadata: Dict[str, Any] = layout_result.get("metadata", {})

            if not text_map or not chapters_html:
                logger.warning("⚠️ EPUB layout parser không tìm thấy nội dung hợp lệ. Fallback về luồng TXT.")
            else:
                # Lưu state để dùng ở Phase 3 (finalize)
                self._epub_layout_state = {
                    "text_map": text_map,
                    "chapters_html": chapters_html,
                    "metadata": metadata,
                }

                chunk_cfg = self.config.get("preprocessing", {}).get("chunking", {})
                try:
                    max_tokens = int(chunk_cfg.get("max_chunk_tokens", 10000))
                except (TypeError, ValueError):
                    max_tokens = 10000

                all_chunks = build_chunks_from_text_map(text_map, max_tokens, token_counter=None)

                if not all_chunks:
                    logger.warning("Không tạo được chunk nào từ TEXT_MAP EPUB.")
                    return [], None

                logger.info(f"📦 [EPUB Layout] Đã chia thành {len(all_chunks)} chunks từ TEXT_MAP, sẵn sàng dịch.")
                _prep_ms = (time.perf_counter() - _prep_t0) * 1000.0
                logger.info(
                    "Preprocess metrics: strategy=%s path=epub_layout text_map_entries=%d chunks=%d elapsed_ms=%.1f",
                    _prep_strategy,
                    len(text_map),
                    len(all_chunks),
                    _prep_ms,
                )
                # cleaned_text không còn ý nghĩa trong chế độ EPUB layout
                return all_chunks, None

        # Fallback / luồng cũ: xử lý như TXT
        from src.preprocessing.file_parser import parse_file_advanced
        from src.preprocessing.semantic_enrichment import enrich_structured_ir
        from src.preprocessing.text_cleaner import clean_text

        logger.info(f"Đang đọc và tiền xử lý tệp tiểu thuyết: {self.novel_path}")
        parsed = parse_file_advanced(self.novel_path, self.config)
        raw_text = parsed.get("text", "")
        cleaned_text = clean_text(raw_text, self.config)
        structured_ir = parsed.get("structured_ir") or []
        if structured_ir:
            for block in structured_ir:
                block_text = (block.get("text") or "").strip()
                if not block_text:
                    continue
                block["text"] = clean_text(block_text, self.config)
            structured_ir = enrich_structured_ir(structured_ir, self.config)
            all_chunks = self.chunker.chunk_from_structured_ir(structured_ir)
        else:
            all_chunks = self.chunker.chunk_novel(cleaned_text)

        if len(all_chunks) == 0:
            logger.warning("Không tìm thấy nội dung nào để chia chunk.")
            return [], None

        logger.info(f"📦 Đã chia thành {len(all_chunks)} chunks, sẵn sàng dịch.")
        _prep_ms = (time.perf_counter() - _prep_t0) * 1000.0
        _chunk_mode = "structured_ir" if structured_ir else "plain"
        logger.info(
            "Preprocess metrics: strategy=%s path=flat chunk_mode=%s structured_ir_blocks=%d chunks=%d elapsed_ms=%.1f",
            _prep_strategy,
            _chunk_mode,
            len(structured_ir) if structured_ir else 0,
            len(all_chunks),
            _prep_ms,
        )
        return all_chunks, cleaned_text

    async def _execute_translation(self, all_chunks: List[Dict]) -> Tuple[List[Dict], float]:
        """
        Phase 2: Thực hiện dịch thuật và retry failed chunks.

        Args:
            all_chunks: Danh sách tất cả chunks cần dịch

        Returns:
            Tuple[List[Dict], float]: (failed_chunks, translation_time)
        """
        start_time = time.time()

        # Dịch các chunks
        failed_chunks = await self._translate_all_chunks(all_chunks)

        # [REMOVED] Chunk size validation logic has been removed as per user request (legacy logic).
        # See conversation history or git log for details.

        # Tính thời gian dịch
        translation_time = time.time() - start_time

        # CRITICAL: Retry failed chunks TRƯỚC khi kiểm tra và merge
        if failed_chunks:
            logger.warning("")
            logger.warning("=" * 60)
            logger.warning("🔄 PHÁT HIỆN CHUNKS THẤT BẠI - ĐANG THỬ LẠI...")
            logger.warning("=" * 60)

            # Retry failed chunks với exponential backoff
            max_retry_attempts = self.performance_config.get("max_retries_per_chunk", 2)
            retry_result = await self._retry_failed_chunks(failed_chunks, all_chunks, max_retry_attempts)

            # Cập nhật failed_chunks sau retry
            failed_chunks = retry_result.get("still_failed", failed_chunks)
            retried_success = retry_result.get("retried_success", 0)

            if retried_success > 0:
                logger.info(f"✅ Đã retry thành công {retried_success} chunks")

        return failed_chunks, translation_time

    async def _finalize_translation(
        self, all_chunks: List[Dict], failed_chunks: List[Dict], translation_time: float
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Phase 3: Hoàn thiện quá trình dịch.
        Merge chunks, lưu file, convert sang EPUB.

        Args:
            all_chunks: Danh sách tất cả chunks
            failed_chunks: Danh sách chunks thất bại
            translation_time: Thời gian dịch (giây)

        Returns:
            Tuple[List[Dict], Optional[str]]: (result_chunks, output_path)
        """
        # Phase 11: Execute Batch QA if issues were collected
        if self.batch_qa_issues:
            await self._run_batch_qa_pass(all_chunks)

        # Nếu còn failed chunks sau retry, báo lỗi và dừng
        if failed_chunks:
            failed_chunk_ids = [c.get("chunk_id") for c in failed_chunks if c.get("chunk_id")]
            failed_ids_str = str(failed_chunk_ids[:5])
            if len(failed_chunk_ids) > 5:
                failed_ids_str += f", ... (+{len(failed_chunk_ids) - 5} more)"
            logger.error("")
            logger.error("❌ QUÁ TRÌNH DỊCH THUẬT KHÔNG HOÀN TẤT!")
            logger.error(f"Có {len(failed_chunks)} chunks thất bại sau retry: {failed_ids_str}")
            logger.error("⚠️ KHÔNG THỂ GHÉP FILE TỔNG VÀ CONVERT EPUB!")
            logger.error("Vui lòng: 1) Kiểm tra chunks thất bại, 2) Dịch lại (option 3), 3) Kiểm tra API keys/quota")
            return all_chunks, None

        logger.info("")
        logger.info("-" * 30)
        logger.info("🎬 Bắt đầu giai đoạn Finalize (Phase 3)...")

        # 0. Sắp xếp chunks theo global_id (đề phòng parallel return out of order)
        all_chunks.sort(key=lambda x: x.get("chunk_id", 0))

        # Tạo báo cáo hoàn thành (delegated to UIHandler)
        await self.ui_handler.generate_completion_report(all_chunks, failed_chunks, translation_time, is_success=True)

        # EPUB layout-preservation finalize branch (trước khi ghép TXT)
        if self._epub_preserve_layout and self._epub_layout_state is not None:
            from src.output.epub_reinject import (
                apply_translations_to_chapters,
                build_html_master,
                write_epub_from_translated_chapters,
            )
            from src.preprocessing.translation_map_epub import build_translation_map_from_chunks

            logger.info("📚 Đang finalize theo chế độ EPUB Layout (không ghép TXT).")

            # Lấy bản dịch của từng chunk từ ProgressManager
            translated_by_chunk: Dict[int, str] = {}
            if self.progress_manager is not None:
                # Ưu tiên completed_chunks (vì đã được flush)
                completed = getattr(self.progress_manager, "completed_chunks", {}) or {}
                for chunk in all_chunks:
                    gid = chunk.get("global_id") or chunk.get("chunk_id")
                    if gid is None:
                        continue
                    gid_str = str(gid)
                    text = completed.get(gid_str)
                    if not text and hasattr(self.progress_manager, "get_chunk_translation"):
                        try:
                            text = self.progress_manager.get_chunk_translation(gid)  # type: ignore[arg-type]
                        except Exception:
                            text = None
                    if text:
                        translated_by_chunk[gid] = text

            # Xây translation map theo text_id từ từng chunk
            translation_map = build_translation_map_from_chunks(all_chunks, translated_by_chunk)

            chapters_html = self._epub_layout_state.get("chapters_html", {})
            translated_chapters = apply_translations_to_chapters(chapters_html, translation_map)

            layout_meta = self._epub_layout_state.get("metadata") or {}
            title = layout_meta.get("title") or self.novel_name

            # Lưu HTML master (nếu config bật)
            reinject_cfg = self.config.get("output", {}).get("epub_reinject", {})
            master_path: Optional[str] = None
            if reinject_cfg.get("output_html_master", True):
                master_html = build_html_master(translated_chapters, title=title)
                progress_dir = get_progress_dir(self.config)
                os.makedirs(progress_dir, exist_ok=True)
                master_path = str(progress_dir / f"{self.novel_name}_master.html")
                try:
                    with open(master_path, "w", encoding="utf-8") as f:
                        f.write(master_html)
                    logger.info(f"✅ Đã lưu HTML master (EPUB Layout) tại: {master_path}")
                except Exception as e:
                    logger.error(f"❌ Lỗi khi lưu HTML master: {e}")

            # Xuất EPUB giữ layout (file-per-chapter + copy assets)
            if reinject_cfg.get("output_epub", True) and self.novel_path and os.path.isfile(self.novel_path):
                epub_out_dir = reinject_cfg.get("epub_output_dir", "").strip()
                if not epub_out_dir:
                    epub_out_dir = str(get_output_dir(self.config))
                os.makedirs(epub_out_dir, exist_ok=True)
                out_epub_path = os.path.join(epub_out_dir, f"{self.novel_name}_translated.epub")
                try:
                    write_epub_from_translated_chapters(
                        self.novel_path,
                        translated_chapters,
                        metadata={
                            "title": title,
                            "author": layout_meta.get("author"),
                            "language": layout_meta.get("language"),
                        },
                        output_epub_path=out_epub_path,
                    )
                except Exception as e:
                    logger.error("❌ Lỗi khi ghi EPUB layout-preserving: %s", e)

            return failed_chunks, master_path

        # Merge và tạo file TXT tổng
        logger.info("🔄 Đang ghép file txt tổng...")
        full_content = await self._merge_all_chunks(all_chunks)
        if not full_content:
            logger.error("❌ KHÔNG THỂ GHÉP CHUNKS!")
            logger.error("Có thể do: chunks thiếu/không hợp lệ, lỗi load từ disk, hoặc lỗi validation")
            logger.error("⚠️ QUÁ TRÌNH DỊCH THUẬT KHÔNG HOÀN TẤT! Vui lòng kiểm tra logs và dịch lại chunks thiếu.")
            return [], None

        # Chuẩn hóa một lần: [H1]/[H2]/[H3] cho tiêu đề → dùng cho cả TXT và master.html (tránh EPUB từ master = TXT phẳng)
        normalized_content = self.output_formatter._normalize_paragraphs(full_content)

        # Lưu file txt (đã chuẩn hóa)
        txt_path = self.output_formatter.save(normalized_content, self.novel_name)
        logger.info(f"✅ Đã lưu file txt tổng: {txt_path}")
        logger.info("")

        # Phase 8: Build và lưu HTML master từ flat text (cùng nội dung đã chuẩn hóa = có [H1])
        progress_dir = get_progress_dir(self.config)
        os.makedirs(progress_dir, exist_ok=True)
        try:
            from src.output.html_master_builder import build_html_master_from_flat_text

            master_html = build_html_master_from_flat_text(normalized_content, self.novel_name)
            master_path = str(progress_dir / f"{self.novel_name}_master.html")
            with open(master_path, "w", encoding="utf-8") as f:
                f.write(master_html)
            section_count = master_html.count("<section")
            logger.info(f"✅ Đã lưu HTML master (flat text) tại: {master_path} (số chương: {section_count})")
        except Exception as e:
            logger.error(f"❌ Lỗi khi build/lưu HTML master từ flat text: {e}")

        # Delegate toàn bộ flow review/convert sang UIHandler
        return await self.ui_handler.show_user_options(all_chunks, failed_chunks, txt_path)

    async def _run_batch_qa_pass(self, all_chunks: List[Dict]):
        """
        Thực hiện Batch QA cho tất cả issues đã thu thập được.
        """
        if not self.batch_qa_issues:
            return

        logger.info("")
        logger.info("🛡️ ĐANG CHẠY BATCH QA KIỂM SOÁT CHẤT LƯỢNG...")
        logger.info(f"🔍 Thu thập được {len(self.batch_qa_issues)} câu có vấn đề.")

        # Lấy API key tạm thời để chạy batch QA (get_available_key is async)
        api_key = await self.key_manager.get_available_key()
        if not api_key:
            logger.warning("⚠️ Không lấy được API key cho Batch QA. Bỏ qua bước này.")
            return

        batch_qa_error = None
        try:
            # Chia nhỏ batch issues nếu quá lớn (max 30k tokens hoặc 50 issues)
            batch_size = int(self.config.get("translation", {}).get("qa_editor", {}).get("max_batch_size", 30))
            total_fixes = 0
            chunks_updated = 0

            for i in range(0, len(self.batch_qa_issues), batch_size):
                current_batch = self.batch_qa_issues[i : i + batch_size]
                logger.info(f"📦 Đang xử lý Batch {i // batch_size + 1} ({len(current_batch)} issues)...")

                results = await self.batch_qa_processor.process_batch(current_batch, api_key)

                if results:
                    # Áp dụng thay thế vào all_chunks
                    for cid, fixes in results.items():
                        # Tìm chunk tương ứng
                        chunk_target = next((c for f in all_chunks if (c := f) and c.get("chunk_id") == cid), None)
                        if chunk_target and "translation" in chunk_target:
                            orig_text = chunk_target["translation"]
                            new_text = orig_text
                            for fix in fixes:
                                new_text = new_text.replace(fix["old"], fix["new"])

                            if new_text != orig_text:
                                chunk_target["translation"] = new_text
                                total_fixes += len(fixes)
                                chunks_updated += 1
                                logger.info(f"✅ Đã áp dụng {len(fixes)} sửa đổi cho Chunk {cid}")

            if total_fixes or chunks_updated:
                logger.info(f"✨ Hoàn tất Batch QA: đã áp dụng {total_fixes} sửa đổi cho {chunks_updated} chunks.")
            else:
                logger.info("✨ Hoàn tất Batch QA. Bản dịch đã được tinh chỉnh.")
        except Exception as e:
            batch_qa_error = e
            logger.error(f"❌ Lỗi nghiêm trọng trong Batch QA: {e}")
        finally:
            # Trả lại key sau khi chạy Batch QA; báo lỗi để key_manager áp dụng cooldown thống nhất
            try:
                return_key = getattr(self.key_manager, "return_key", None)
                if return_key is not None and api_key:
                    is_err = batch_qa_error is not None
                    err_type = ""
                    err_msg = ""
                    if batch_qa_error is not None and hasattr(self.key_manager, "handle_exception"):
                        err_type = self.key_manager.handle_exception(api_key, batch_qa_error)
                        err_msg = str(batch_qa_error)
                    result = return_key(999, api_key, is_error=is_err, error_type=err_type, error_message=err_msg)
                    if hasattr(result, "__await__"):
                        await result  # type: ignore[func-returns-value]
            except Exception as e:
                logger.warning(f"⚠️ Không thể trả lại key sau Batch QA: {e}")

    async def run_translation_cycle_with_review(
        self,
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Chạy chu trình dịch với workflow review và lựa chọn của người dùng.

        Workflow được chia thành 3 phase:
        1. _prepare_translation: Đọc file, làm sạch, chia chunks
        2. _execute_translation: Dịch chunks, retry failed
        3. _finalize_translation: Merge, lưu file, convert EPUB
        """
        # Metadata đã được kiểm tra trong setup_resources_async()

        # Phase 1: Chuẩn bị
        all_chunks, cleaned_text = await self._prepare_translation()
        if not all_chunks:
            return [], None

        # Phase 2: Dịch thuật
        failed_chunks, translation_time = await self._execute_translation(all_chunks)

        # Phase 3: Hoàn thiện
        return await self._finalize_translation(all_chunks, failed_chunks, translation_time)

    async def _translate_all_chunks(self, all_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dịch tất cả chunks sử dụng ExecutionManager."""
        await self.setup_resources_async()

        num_chunks = len(all_chunks)
        if self.key_manager and hasattr(self.key_manager, "update_allocation"):
            await self.key_manager.update_allocation(num_chunks)
            health = self.key_manager.get_quota_status_summary()
            logger.info(f"📊 Smart Distribution: Allocation updated. Pool Health: {health}")

        # [SmartKeyDistributor] Start Recovery Task in background
        if self.key_manager and hasattr(self.key_manager, "start_recovery_task"):
            await self.key_manager.start_recovery_task()

        # 0. WARM-UP (Context Caching)
        if not self._warm_up_completed:
            self.worker_caches = await self.init_service.warm_up_resources(self.resources, self.valid_api_keys)
            self._warm_up_completed = True

        # 1. EXECUTE TRANSLATION
        try:
            failed_chunks = await self.executor.translate_all(all_chunks, self)
            return failed_chunks
        finally:
            # [SmartKeyDistributor] Stop Recovery Task when done
            if self.key_manager and hasattr(self.key_manager, "stop_recovery_task"):
                await self.key_manager.stop_recovery_task()

    def _get_context_chunks(
        self,
        chunk_index: int,
        all_chunks: List[Dict[str, Any]],
        translated_chunks_map: Dict[str, str],
    ) -> Tuple[List[str], List[str]]:
        """v5.3: Get context chunks. Delegated to context_manager."""
        if not self.context_manager:
            from src.translation.context_manager import ContextManager

            self.context_manager = ContextManager(self.config)

        return self.context_manager.get_context_chunks(chunk_index, all_chunks, translated_chunks_map)

    async def _retry_failed_chunks(
        self,
        failed_chunks: List[Dict[str, Any]],
        all_chunks: List[Dict[str, Any]],
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        """
        Retry dịch các chunks thất bại với exponential backoff.

        Args:
            failed_chunks: Danh sách chunks thất bại
            all_chunks: Tất cả chunks (để tìm context)
            max_attempts: Số lần retry tối đa

        Returns:
            Dict với keys: 'still_failed', 'retried_success'
        """
        if not failed_chunks:
            return {"still_failed": [], "retried_success": 0}

        still_failed = []
        retried_success = 0

        # Safety check
        if all_chunks and isinstance(all_chunks[0], tuple):
            all_chunks = [c[1] if isinstance(c, tuple) and len(c) > 1 else c for c in all_chunks]

        # Tạo map để tìm chunk gốc nhanh
        chunk_map = {chunk["global_id"]: chunk for chunk in all_chunks}

        for attempt in range(1, max_attempts + 1):
            if not failed_chunks:
                break

            logger.info(f"🔄 Retry attempt {attempt}/{max_attempts} cho {len(failed_chunks)} chunks...")

            # Exponential backoff
            if attempt > 1:
                backoff_delay = 5 * (2 ** (attempt - 2))  # 5s, 10s, 20s...
                logger.debug(f"⏳ Đợi {backoff_delay}s trước khi retry...")
                await asyncio.sleep(backoff_delay)

            # OPTIMIZATION 2.1: Parallel retry failed chunks
            retry_tasks = []
            translated_chunks_map = self.progress_manager.completed_chunks.copy()

            for failed_chunk in failed_chunks:
                chunk_id = failed_chunk.get("chunk_id")
                if not chunk_id:
                    continue

                # Tìm chunk gốc
                original_chunk = chunk_map.get(chunk_id)
                if not original_chunk:
                    logger.warning(f"⚠️ Không tìm thấy chunk {chunk_id} trong all_chunks")
                    still_failed.append(failed_chunk)
                    continue

                # Xây dựng context (sử dụng cached method)
                chunk_index = all_chunks.index(original_chunk)
                original_context_chunks, translated_context_chunks = self._get_context_chunks(
                    chunk_index, all_chunks, translated_chunks_map
                )

                # Tạo task retry
                worker_id = chunk_index % self.performance_config.get("max_parallel_workers", 5)
                task = self._translate_one_chunk_worker(
                    original_chunk,
                    original_context_chunks,
                    translated_context_chunks,
                    worker_id=worker_id,
                )
                retry_tasks.append((failed_chunk, task))

            # OPTIMIZATION 2.1: Chạy retry tasks song song với semaphore
            max_parallel_retries = min(self.performance_config.get("max_parallel_workers", 5), len(retry_tasks))
            semaphore = asyncio.Semaphore(max_parallel_retries)

            async def retry_with_semaphore(failed_chunk, task):
                async with semaphore:
                    try:
                        result = await task
                        return failed_chunk, result
                    except Exception as e:
                        from src.utils.error_formatter import (
                            format_exception_for_logging,
                        )

                        error_info = format_exception_for_logging(
                            e, context=f"Retry chunk {failed_chunk.get('chunk_id')}"
                        )
                        logger.error(f"❌ Retry chunk {failed_chunk.get('chunk_id')} lỗi: {error_info['short']}")
                        return failed_chunk, None

            # Execute parallel retries
            retry_results = await asyncio.gather(
                *[retry_with_semaphore(fc, task) for fc, task in retry_tasks],
                return_exceptions=True,
            )

            # Process results
            for retry_result in retry_results:
                if isinstance(retry_result, Exception):
                    logger.error(f"❌ Retry exception: {retry_result}")
                    continue

                failed_chunk, result = retry_result
                # Chỉ coi success là xong; partial vẫn nằm trong failed để retry khi có key
                if result and result.get("status") == "success":
                    chunk_id = result.get("chunk_id")
                    translation = result.get("translation")
                    if translation:
                        self.progress_manager.save_chunk_result(chunk_id, translation)
                        retried_success += 1
                        logger.info(f"✅ Retry thành công chunk {chunk_id}")
                        failed_chunks = [fc for fc in failed_chunks if fc.get("chunk_id") != chunk_id]
                    else:
                        still_failed.append(failed_chunk)
                else:
                    # partial hoặc failed: giữ trong danh sách retry
                    still_failed.append(failed_chunk)

            # Cập nhật failed_chunks cho lần retry tiếp theo
            failed_chunks = still_failed
            still_failed = []

        return {"still_failed": failed_chunks, "retried_success": retried_success}

    def _sync_completed_chunks(self, all_chunks: List[Dict]) -> Dict[str, str]:
        """
        Sync completed_chunks với files trên disk (file-first approach).

        Args:
            all_chunks: Danh sách tất cả chunks

        Returns:
            Dictionary chứa synced chunks với content
        """
        synced_chunks = {}

        logger.debug("🔄 Đang đồng bộ completed_chunks với files...")

        for chunk in all_chunks:
            chunk_id = chunk["global_id"]
            chunk_id_str = str(chunk_id)

            # File-first approach: Kiểm tra file trước
            if self.progress_manager.chunk_file_exists(chunk_id):
                content = self.progress_manager.get_chunk_translation(chunk_id)
                if content and content.strip():
                    synced_chunks[chunk_id_str] = content
                else:
                    # File tồn tại nhưng rỗng → đánh dấu cần dịch lại
                    logger.warning(f"Chunk {chunk_id} file rỗng, cần dịch lại")
            elif chunk_id_str in self.progress_manager.completed_chunks:
                # Có trong completed_chunks nhưng không có file → xóa khỏi completed
                logger.warning(f"Chunk {chunk_id} có trong completed_chunks nhưng không có file, sẽ được dịch lại")

        logger.debug(f"✅ Đã đồng bộ {len(synced_chunks)}/{len(all_chunks)} chunks")
        return synced_chunks

    async def _parallel_load_chunks(
        self,
        all_chunks: List[Dict],
        synced_chunks: Dict[str, str],
        max_concurrent: int = 10,
    ) -> List[Tuple[Dict, Optional[str]]]:
        """
        Load chunks từ disk song song với semaphore.

        Args:
            all_chunks: Danh sách tất cả chunks
            synced_chunks: Chunks đã được sync
            max_concurrent: Số lượng concurrent loads tối đa

        Returns:
            List các tuple (chunk, content)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def load_chunk(chunk: Dict) -> Tuple[Dict, Optional[str]]:
            """Load một chunk từ disk."""
            async with semaphore:
                chunk_id = chunk["global_id"]
                chunk_id_str = str(chunk_id)

                # Nếu đã có trong synced_chunks, return ngay
                if chunk_id_str in synced_chunks:
                    return chunk, synced_chunks[chunk_id_str]

                # Load từ disk
                content = self.progress_manager.get_chunk_translation(chunk_id)
                return chunk, content

        # Load song song
        tasks = [load_chunk(chunk) for chunk in all_chunks]
        loaded_chunks = await asyncio.gather(*tasks)

        return loaded_chunks

    async def _export_master_html_to_epub(self, master_html_path: str) -> Optional[str]:
        """
        Export file master.html sang EPUB (Phase 11). Dùng cho option 4 trong UIHandler.
        """
        from src.output import html_exporter

        output_dir = self.config.get("output", {}).get("html_master_epub_output") or str(
            get_output_dir(self.config)
        )
        epub_options = self.config.get("output", {}).get("epub_options", {})
        return await html_exporter.export_master_html_to_epub(
            master_html_path, self.novel_name, output_dir, epub_options, self.config
        )

    async def _merge_all_chunks(self, all_chunks: List[Dict]) -> Optional[str]:
        """
        Ghép tất cả chunks thành nội dung hoàn chỉnh (OPTIMIZED VERSION).

        Workflow tối ưu hóa:
        1. Sync completed_chunks với files (file-first approach)
        2. Parallel load chunks từ disk
        3. Phân loại chunks (complete/missing/empty)
        4. Incremental merge (merge phần đã có trước)
        5. Dịch bổ sung chunks thiếu/rỗng với retry
        6. Marker-first validation với phát hiện trùng lặp và thiếu marker

        CRITICAL: Đảm bảo tất cả chunks đều hợp lệ và đầy đủ.
        - Phát hiện chunks có nội dung trùng lặp
        - Phát hiện chunks thiếu marker (start hoặc end)
        - Nếu có chunk thiếu, tự động dịch bổ sung
        - Nếu không thể dịch, báo lỗi và dừng (không ghép file)

        Returns:
            Nội dung đã ghép hoặc None nếu có lỗi không thể khắc phục
        """
        try:
            # OPTIMIZATION 2.2: Cache content trong quá trình merge
            content_cache: Dict[int, str] = {}

            def get_cached_content(chunk_id: int) -> Optional[str]:
                """Get content từ cache hoặc load từ disk."""
                if chunk_id in content_cache:
                    return content_cache[chunk_id]
                content = self.progress_manager.get_chunk_translation(chunk_id)
                if content:
                    content_cache[chunk_id] = content
                return content

            # BƯỚC 1: Sync completed_chunks với files (file-first approach)
            logger.info("🔄 Đang đồng bộ completed_chunks với files...")
            synced_chunks = self._sync_completed_chunks(all_chunks)

            # Cache synced chunks
            for chunk_id_str, content in synced_chunks.items():
                try:
                    chunk_id = int(chunk_id_str)
                    content_cache[chunk_id] = content
                except (ValueError, TypeError):
                    pass

            # BƯỚC 2: Parallel load chunks từ disk
            logger.info("📥 Đang load chunks từ disk (parallel)...")
            loaded_chunks = await self._parallel_load_chunks(all_chunks, synced_chunks)

            # BƯỚC 3: Phân loại chunks
            complete_chunks = []
            missing_chunks = []
            empty_chunks = []

            for chunk, content in loaded_chunks:
                chunk_id = chunk["global_id"]
                if content and content.strip():
                    complete_chunks.append((chunk, content))
                elif not content:
                    missing_chunks.append(chunk)
                else:
                    empty_chunks.append(chunk)

            logger.info(
                f"📊 Phân loại: {len(complete_chunks)} hoàn thiện, "
                f"{len(missing_chunks)} thiếu, {len(empty_chunks)} rỗng"
            )

            # BƯỚC 4: Merge phần đã có trước (incremental merge)
            if complete_chunks:
                logger.debug(f"✅ Đang merge {len(complete_chunks)} chunks hoàn thiện...")
                # Sort theo chunk_id để đảm bảo thứ tự
                complete_chunks.sort(key=lambda x: x[0]["global_id"])
                partial_content_parts = [content for _, content in complete_chunks]
            else:
                partial_content_parts = []
                logger.warning("⚠️ Không có chunks hoàn thiện nào để merge")

            # BƯỚC 5: Dịch bổ sung chunks thiếu/rỗng với retry mechanism
            chunks_to_retranslate = missing_chunks + empty_chunks

            if chunks_to_retranslate:
                logger.warning(f"⚠️ Phát hiện {len(missing_chunks)} chunks thiếu và {len(empty_chunks)} chunks rỗng")
                logger.info("🔄 Đang tự động dịch bổ sung các chunks thiếu/rỗng...")

                # Dịch với retry mechanism - sử dụng _retry_failed_chunks
                # Convert chunks_to_retranslate thành format failed_chunks
                failed_chunks_format = [
                    {
                        "chunk_id": chunk["global_id"],
                        "status": "failed",
                        "error": "Missing chunk",
                    }
                    for chunk in chunks_to_retranslate
                ]

                retry_result = await self._retry_failed_chunks(failed_chunks_format, all_chunks, max_attempts=3)

                # Kiểm tra kết quả retry - _retry_failed_chunks trả về 'still_failed' và 'retried_success'
                retried_success_count = retry_result.get("retried_success", 0)
                still_failed_list = retry_result.get("still_failed", [])

                # Load lại các chunks đã dịch bổ sung (nếu có)
                if retried_success_count > 0:
                    logger.debug("🔄 Đang load lại các chunks đã dịch bổ sung...")
                    additional_chunks = []
                    for chunk in chunks_to_retranslate:
                        chunk_id = chunk["global_id"]
                        content = self.progress_manager.get_chunk_translation(chunk_id)
                        if content and content.strip():
                            additional_chunks.append((chunk, content))
                            logger.debug(f"✅ Đã load lại chunk {chunk_id}")

                    # Chỉ merge các chunks đã dịch thành công
                    if additional_chunks:
                        additional_chunks.sort(key=lambda x: x[0]["global_id"])
                        additional_content_parts = [content for _, content in additional_chunks]
                        full_content_parts = partial_content_parts + additional_content_parts
                        logger.info(f"✅ Đã dịch bổ sung {len(additional_chunks)}/{len(chunks_to_retranslate)} chunks")
                    else:
                        # Không có chunk nào được dịch thành công
                        logger.error("❌ Không có chunk nào được dịch bổ sung thành công")
                        full_content_parts = partial_content_parts
                else:
                    # Không có chunk nào được retry thành công
                    full_content_parts = partial_content_parts

                # Kiểm tra nếu vẫn còn chunks thất bại
                if still_failed_list:
                    failed_chunk_ids = [c.get("chunk_id") for c in still_failed_list if c.get("chunk_id")]
                    if failed_chunk_ids:
                        failed_ids_str = str(failed_chunk_ids[:5])
                        if len(failed_chunk_ids) > 5:
                            failed_ids_str += f", ... (+{len(failed_chunk_ids) - 5} more)"
                        logger.error(f"❌ KHÔNG THỂ DỊCH BỔ SUNG {len(failed_chunk_ids)} chunks: {failed_ids_str}")
                    else:
                        logger.error(f"❌ KHÔNG THỂ DỊCH BỔ SUNG {len(still_failed_list)} chunks")

                    # v5.3 STRICT MODE: Không cho phép ghép file nếu còn chunks thất bại
                    # File merging sẽ KHÔNG diễn ra nếu bất kỳ chunk nào chưa dịch hoàn tất
                    logger.error("")
                    logger.error("=" * 60)
                    logger.error("❌ KHÔNG THỂ GHÉP FILE - CÒN CHUNKS CHƯA DỊCH!")
                    logger.error("=" * 60)
                    logger.error(f"Số chunks thất bại: {len(failed_chunk_ids)}")
                    logger.error(f"IDs: {failed_ids_str}")
                    logger.error("")
                    logger.error("Hướng dẫn:")
                    logger.error("  1. Kiểm tra trạng thái API keys (quota, rate limit)")
                    logger.error("  2. Dịch lại các chunks thất bại (Option 3 trong menu)")
                    logger.error("  3. Đảm bảo tất cả chunks hoàn tất trước khi ghép file")
                    logger.error("=" * 60)
                    return None
            else:
                # Không có chunks thiếu/rỗng → sử dụng phần đã có
                full_content_parts = partial_content_parts

            # BƯỚC 6: Validation số lượng và empty chunks
            # Loại bỏ missing marker khỏi count nếu có
            actual_chunk_count = len([p for p in full_content_parts if not p.startswith("[CHUNKS THIẾU:")])

            if actual_chunk_count != len(all_chunks):
                logger.error(
                    f"❌ LỖI NGHIÊM TRỌNG: Số chunks đã ghép ({actual_chunk_count}) "
                    f"không khớp với số chunks gốc ({len(all_chunks)}). "
                    f"Dừng quá trình ghép file."
                )
                return None

            # Kiểm tra không có chunk nào rỗng (trừ missing marker)
            empty_chunks_found = []
            for i, part in enumerate(full_content_parts):
                if part.startswith("[CHUNKS THIẾU:"):
                    continue  # Bỏ qua missing marker
                if not part or not part.strip():
                    # Tìm chunk_id tương ứng
                    if i < len(complete_chunks):
                        empty_chunks_found.append(complete_chunks[i][0]["global_id"])
                    elif i < len(complete_chunks) + len(chunks_to_retranslate):
                        idx = i - len(complete_chunks)
                        if idx < len(chunks_to_retranslate):
                            empty_chunks_found.append(chunks_to_retranslate[idx]["global_id"])

            if empty_chunks_found:
                logger.error(
                    f"❌ LỖI NGHIÊM TRỌNG: Phát hiện {len(empty_chunks_found)} chunks rỗng: "
                    f"{empty_chunks_found}. Dừng quá trình ghép file."
                )
                return None

            marker_guardrail_enabled = self._is_marker_guardrail_enabled(all_chunks)

            # BƯỚC 7: Marker-first validation với phát hiện trùng lặp và thiếu marker
            logger.debug("🔍 Đang validate chunks với marker-first approach...")
            full_content = self._validate_and_merge_chunks_optimized(
                full_content_parts,
                all_chunks,
                marker_guardrail_enabled=marker_guardrail_enabled,
            )

            if full_content is None:
                if not marker_guardrail_enabled:
                    logger.error(
                        "❌ Merge thất bại do validation không-marker, không kích hoạt nhánh retry theo marker."
                    )
                    return None

                # Validation phát hiện chunks thiếu markers → xóa và dịch lại
                logger.warning(
                    "⚠️ Validation phát hiện chunks thiếu markers. Đang xóa các chunk files lỗi và dịch lại..."
                )

                # Xác định chunks thiếu markers
                marker_validation_result = self._validate_with_markers(full_content_parts, all_chunks)

                missing_marker_chunk_ids = []
                for idx in marker_validation_result.get("suspicious_chunks", []):
                    if idx < len(all_chunks):
                        chunk_id = all_chunks[idx]["global_id"]
                        chunk_content = full_content_parts[idx] if idx < len(full_content_parts) else ""

                        # Bổ sung logic check marker linh hoạt (Hỗ trợ tiền tố session_id)
                        import re
                        escaped_chunk_id = re.escape(str(chunk_id))
                        # Cho phép định dạng [CHUNK:anything:id:START]
                        flexible_start = rf"\[CHUNK:(?:[^\]]*?:)?{escaped_chunk_id}:START\]"
                        flexible_end = rf"\[CHUNK:(?:[^\]]*?:)?{escaped_chunk_id}:END\]"

                        start_pattern = re.compile(flexible_start, re.IGNORECASE)
                        end_pattern = re.compile(flexible_end, re.IGNORECASE)

                        # Check bằng 'in' operator (rút gọn)
                        has_start = start_pattern.search(chunk_content) is not None
                        has_end = end_pattern.search(chunk_content) is not None

                        # Check bằng regex (findall để đếm)
                        start_matches = start_pattern.findall(chunk_content)
                        end_matches = end_pattern.findall(chunk_content)

                        # Nếu regex tìm thấy nhưng 'in' không tìm thấy → có thể có vấn đề encoding
                        # → Coi như có markers
                        if len(start_matches) > 0:
                            has_start = True
                        if len(end_matches) > 0:
                            has_end = True

                        # Chỉ xử lý missing markers, không phải duplicate
                        start_marker = f"[CHUNK:{chunk_id}:START]"
                        end_marker = f"[CHUNK:{chunk_id}:END]"
                        start_count = len(start_matches) if start_matches else chunk_content.count(start_marker)
                        end_count = len(end_matches) if end_matches else chunk_content.count(end_marker)

                        # DEBUG: Log chi tiết nếu phát hiện missing
                        if (not has_start or not has_end) and start_count <= 1 and end_count <= 1:
                            content_preview = chunk_content[:200] if len(chunk_content) > 200 else chunk_content
                            logger.debug(
                                f"🔍 DEBUG Chunk {chunk_id} missing markers: "
                                f"START={'✓' if has_start else '✗'} (count={start_count}), "
                                f"END={'✓' if has_end else '✗'} (count={end_count}), "
                                f"Content preview: {repr(content_preview)}"
                            )
                            missing_marker_chunk_ids.append(chunk_id)

                if missing_marker_chunk_ids:
                    logger.info(
                        f"🔄 Đang xóa {len(missing_marker_chunk_ids)} chunks lỗi markers: "
                        f"{missing_marker_chunk_ids[:10]}{'...' if len(missing_marker_chunk_ids) > 10 else ''}"
                    )

                    # Xóa chunk files lỗi
                    chunks_to_retranslate = []
                    for chunk in all_chunks:
                        if chunk["global_id"] in missing_marker_chunk_ids:
                            # Xóa file chunk
                            self._delete_chunk_file(chunk["global_id"])
                            # Xóa khỏi completed_chunks
                            chunk_id_str = str(chunk["global_id"])
                            if chunk_id_str in self.progress_manager.completed_chunks:
                                del self.progress_manager.completed_chunks[chunk_id_str]
                            chunks_to_retranslate.append(chunk)

                    # Dịch lại các chunks đã xóa
                    if chunks_to_retranslate:
                        logger.info(f"🔄 Đang dịch lại {len(chunks_to_retranslate)} chunks...")
                        # Convert chunks_to_retranslate thành format failed_chunks
                        failed_chunks_format = [
                            {
                                "chunk_id": chunk["global_id"],
                                "status": "failed",
                                "error": "Missing markers",
                            }
                            for chunk in chunks_to_retranslate
                        ]
                        retry_result = await self._retry_failed_chunks(failed_chunks_format, all_chunks, max_attempts=2)

                        retried_success_count = retry_result.get("retried_success", 0)
                        still_failed_list = retry_result.get("still_failed", [])

                        if retried_success_count > 0:
                            logger.info(f"✅ Đã dịch lại thành công {retried_success_count} chunks")

                            # Load lại chunks đã dịch và rebuild full_content_parts
                            # CRITICAL: Invalidate cache cho chunks đã dịch lại
                            # để đảm bảo load fresh data từ disk
                            for retried_chunk in chunks_to_retranslate:
                                retried_id = retried_chunk["global_id"]
                                if retried_id in content_cache:
                                    del content_cache[retried_id]

                            full_content_parts = []
                            for chunk in all_chunks:
                                chunk_id = chunk["global_id"]
                                chunk_id_str = str(chunk_id)
                                # Load từ disk cho retried chunks, cache cho còn lại
                                translation = get_cached_content(chunk_id)
                                if translation:
                                    full_content_parts.append(translation)
                                else:
                                    # Nếu chunk vẫn chưa có translation, thêm placeholder
                                    logger.warning(f"⚠️ Chunk {chunk_id} vẫn chưa có translation sau khi dịch lại")
                                    full_content_parts.append("")

                            # Validate lại sau khi dịch lại
                            full_content = self._validate_and_merge_chunks_optimized(full_content_parts, all_chunks)

                            if full_content is None:
                                logger.error(
                                    "❌ Vẫn còn chunks thiếu markers sau khi dịch lại. Vui lòng kiểm tra logs."
                                )
                                return None
                        else:
                            logger.error(
                                f"❌ Không thể dịch lại {len(chunks_to_retranslate)} chunks. "
                                "Vui lòng kiểm tra logs và thử lại."
                            )
                            return None
                else:
                    logger.error("❌ Không thể xác định chunks thiếu markers. Vui lòng kiểm tra logs.")
                    return None

            # BƯỚC 8: Final validation
            if not full_content or not full_content.strip():
                logger.error("❌ LỖI NGHIÊM TRỌNG: Nội dung ghép cuối cùng rỗng. Dừng quá trình ghép file.")
                return None

            # BƯỚC 9: Normalize format giữa các chunks
            logger.info("🔧 Đang normalize format giữa các chunks...")
            try:
                from ..utils.format_normalizer import FormatNormalizer

                normalizer = FormatNormalizer(self.config)

                # FIX: Không split bằng "\n\n" vì có thể làm mất paragraph breaks
                # Thay vào đó, normalize format trên toàn bộ content
                # (format normalizer sẽ xử lý headings, không ảnh hưởng paragraph breaks)

                # Normalize format trên toàn bộ content (không split)
                # Tạo một "chunk giả" chứa toàn bộ content
                fake_chunks = [full_content]
                normalized_chunks, analysis_report = normalizer.normalize_all_chunks(fake_chunks, analyze_first_n=1)

                # Lấy content đã normalize
                full_content = normalized_chunks[0] if normalized_chunks else full_content

                # Lấy content đã normalize
                full_content = normalized_chunks[0] if normalized_chunks else full_content

                # logger.info(f"✅ Đã normalize...") -> Removed to prevent duplicate logs (already logged in FormatNormalizer)
                logger.debug(
                    f"📊 Format consistency: "
                    f"H1={analysis_report['format_patterns']['format_consistency']['H1']:.2%}, "
                    f"H2={analysis_report['format_patterns']['format_consistency']['H2']:.2%}, "
                    f"H3={analysis_report['format_patterns']['format_consistency']['H3']:.2%}"
                )
            except Exception as e:
                logger.warning(f"⚠️ Không thể normalize format: {str(e)}. Tiếp tục với format gốc.")
                # Tiếp tục với full_content gốc nếu normalize fail

            logger.info(f"✅ Tổng độ dài nội dung ghép: {len(full_content)} ký tự")
            logger.info(f"✅ Số chunks đã ghép: {actual_chunk_count}/{len(all_chunks)}")
            logger.info("✅ Tất cả chunks đã được validate và ghép thành công!")

            return full_content

        except Exception as e:
            from ..utils.error_formatter import format_exception_for_logging

            error_info = format_exception_for_logging(e, context="Merge chunks")
            logger.error(error_info["short"])
            logger.debug(error_info["full"])
            return None

    def _validate_and_merge_chunks(self, translated_parts: List[str], original_chunks: List[Dict]) -> str:
        """
        Validate và merge chunks, phát hiện và sửa overlap/missing content.

        Args:
            translated_parts: Danh sách nội dung đã dịch của các chunks
            original_chunks: Danh sách chunks gốc để so sánh

        Returns:
            str: Nội dung đã được validate và merge
        """
        if not translated_parts:
            return ""

        # Kiểm tra overlap: Tìm các đoạn text lặp lại giữa các chunks liên tiếp
        cleaned_parts = []
        overlap_count = 0

        for i, part in enumerate(translated_parts):
            if not part or not part.strip():
                continue

            # So sánh với chunk trước để tìm overlap
            if i > 0 and cleaned_parts:
                prev_part = cleaned_parts[-1]

                # Tìm overlap: Kiểm tra xem phần cuối của chunk trước có trùng với phần đầu của chunk hiện tại không
                # Overlap có thể là 1-3 câu hoặc 1-2 đoạn văn

                # Phương pháp 1: Kiểm tra overlap theo câu
                prev_sentences = [s.strip() for s in prev_part.split(". ") if s.strip()]
                current_sentences = [s.strip() for s in part.split(". ") if s.strip()]

                if len(prev_sentences) > 0 and len(current_sentences) > 0:
                    # Kiểm tra từ 1-3 câu cuối của prev với 1-3 câu đầu của current
                    max_overlap_sentences = min(3, len(prev_sentences), len(current_sentences))
                    overlap_found = False
                    overlap_sentences = 0

                    for check_len in range(1, max_overlap_sentences + 1):
                        prev_end = " ".join(prev_sentences[-check_len:])
                        current_start = " ".join(current_sentences[:check_len])

                        similarity = self._calculate_sentence_similarity(prev_end, current_start)
                        if similarity > 0.75:  # 75% giống nhau → overlap
                            overlap_found = True
                            overlap_sentences = check_len
                            break

                    if overlap_found:
                        # Rút gọn: chỉ log ở DEBUG
                        logger.debug(f"⚠️ Overlap {overlap_sentences} câu giữa chunk {i - 1} và chunk {i}")
                        # Loại bỏ các câu bị overlap ở đầu current_part
                        if len(current_sentences) > overlap_sentences:
                            part = ". ".join(current_sentences[overlap_sentences:])
                            overlap_count += 1
                        else:
                            # Nếu toàn bộ chunk bị overlap → bỏ chunk này
                            logger.warning(f"⚠️ Chunk {i} bị overlap hoàn toàn với chunk {i - 1}, bỏ qua")
                            continue

                    # Phương pháp 2: Kiểm tra overlap theo đoạn văn (nếu không tìm thấy overlap theo câu)
                    if not overlap_found:
                        prev_paragraphs = [p.strip() for p in prev_part.split("\n\n") if p.strip()]
                        current_paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]

                        if len(prev_paragraphs) > 0 and len(current_paragraphs) > 0:
                            # Kiểm tra đoạn cuối của prev với đoạn đầu của current
                            prev_last_para = prev_paragraphs[-1]
                            current_first_para = current_paragraphs[0]

                            similarity = self._calculate_sentence_similarity(
                                prev_last_para[:200], current_first_para[:200]
                            )
                            if similarity > 0.8:  # 80% giống nhau → overlap đoạn văn
                                logger.debug(f"⚠️ Overlap đoạn văn giữa chunk {i - 1} và chunk {i}")
                                # Loại bỏ đoạn đầu của current_part
                                if len(current_paragraphs) > 1:
                                    part = "\n\n".join(current_paragraphs[1:])
                                    overlap_count += 1
                                else:
                                    logger.warning(f"⚠️ Chunk {i} chỉ có 1 đoạn và bị overlap hoàn toàn, bỏ qua")
                                    continue

            cleaned_parts.append(part)

        if overlap_count > 0:
            logger.warning(f"⚠️ Đã sửa {overlap_count} overlap(s) giữa các chunks")

        # Kiểm tra missing content: So sánh tổng độ dài với original
        total_translated_length = sum(len(p) for p in cleaned_parts)
        total_original_length = sum(len(chunk.get("text", "")) for chunk in original_chunks)

        if total_original_length > 0:
            ratio = total_translated_length / total_original_length
            if ratio < 0.7:  # Nếu dịch ngắn hơn 30% so với gốc → có thể thiếu
                logger.warning(
                    f"⚠️ Cảnh báo: Nội dung dịch có thể bị thiếu. Gốc: {total_original_length} chars, Dịch: {total_translated_length} chars (tỷ lệ: {ratio:.1%})"
                )
            elif ratio > 1.5:  # Nếu dịch dài hơn 50% so với gốc → có thể có vấn đề
                logger.warning(
                    f"⚠️ Cảnh báo: Nội dung dịch dài bất thường. Gốc: {total_original_length} chars, Dịch: {total_translated_length} chars (tỷ lệ: {ratio:.1%})"
                )

        # Merge với separator
        full_content = "\n\n".join(cleaned_parts)
        return full_content

    def _detect_original_markers(self, original_chunks: List[Dict]) -> bool:
        """Kiểm tra original chunks có chứa marker guardrail hay không."""
        marker_pattern = re.compile(r"\[CHUNK(?::|_START:|_END:)", re.IGNORECASE)
        for chunk in original_chunks:
            chunk_text = chunk.get("text", "") or ""
            chunk_original = chunk.get("text_original", "") or ""
            if marker_pattern.search(chunk_text) or marker_pattern.search(chunk_original):
                return True
        return False

    def _is_marker_guardrail_enabled(self, original_chunks: List[Dict]) -> bool:
        """Nguồn sự thật duy nhất cho bật/tắt marker guardrail."""
        use_markers_config = bool(getattr(self, "use_markers", True))
        original_has_markers = self._detect_original_markers(original_chunks)
        return use_markers_config or original_has_markers

    def _validate_and_merge_chunks_optimized(
        self,
        translated_parts: List[str],
        original_chunks: List[Dict],
        marker_guardrail_enabled: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Validate và merge chunks với marker-first approach (OPTIMIZED).

        Ưu tiên marker-based validation (O(n)) thay vì similarity (O(n²)).
        Phát hiện:
        - Chunks có nội dung trùng lặp (duplicate markers)
        - Chunks thiếu marker (không có start hoặc end marker)

        Args:
            translated_parts: Danh sách nội dung đã dịch của các chunks
            original_chunks: Danh sách chunks gốc để so sánh

        Returns:
            str: Nội dung đã được validate và merge, hoặc None nếu có chunks thiếu markers
        """
        if not translated_parts:
            return ""

        if marker_guardrail_enabled is None:
            marker_guardrail_enabled = self._is_marker_guardrail_enabled(original_chunks)

        if not marker_guardrail_enabled:
            logger.info("ℹ️ Marker guardrail tắt (config/input), bỏ qua marker-first validation.")
            return self._validate_and_merge_chunks(translated_parts, original_chunks)

        # BƯỚC 1: Marker-based validation (O(n) - nhanh)
        marker_validation_result = self._validate_with_markers(translated_parts, original_chunks)

        if marker_validation_result["is_valid"]:
            # Markers hợp lệ → merge trực tiếp
            logger.info("✅ Marker validation passed, merge trực tiếp")
            return self._merge_with_markers(marker_validation_result["chunks"])

        # BƯỚC 2: Xử lý chunks có vấn đề với markers
        suspicious_chunks = marker_validation_result.get("suspicious_chunks", [])

        if suspicious_chunks:
            logger.warning(f"⚠️ Phát hiện {len(suspicious_chunks)} chunks có vấn đề với markers: {suspicious_chunks}")

            # Phân loại vấn đề
            duplicate_marker_chunks = []
            missing_marker_chunks = []

            for idx in suspicious_chunks:
                if idx >= len(original_chunks):
                    continue
                chunk_content = translated_parts[idx]
                chunk_id = original_chunks[idx]["global_id"]

                # Kiểm tra duplicate markers
                start_marker = f"[CHUNK:{chunk_id}:START]"
                end_marker = f"[CHUNK:{chunk_id}:END]"
                start_marker_count = chunk_content.count(start_marker)
                end_marker_count = chunk_content.count(end_marker)

                if start_marker_count > 1 or end_marker_count > 1:
                    duplicate_marker_chunks.append((idx, chunk_id, start_marker_count, end_marker_count))
                    # Rút gọn: chỉ log summary
                    logger.error(
                        f"❌ Chunk {chunk_id}: markers trùng lặp (START={start_marker_count}, END={end_marker_count})"
                    )

                # Kiểm tra missing markers - FIX: Check chính xác hơn
                # Sử dụng exact string match thay vì 'in' operator để tránh false positive
                has_start = start_marker in chunk_content
                has_end = end_marker in chunk_content

                # DEBUG: Log chi tiết nếu phát hiện missing markers
                if not has_start or not has_end:
                    # Log sample content để debug
                    content_preview = chunk_content[:200] if len(chunk_content) > 200 else chunk_content
                    logger.debug(
                        f"🔍 DEBUG Chunk {chunk_id}: "
                        f"START={'✓' if has_start else '✗'}, END={'✓' if has_end else '✗'}, "
                        f"Content preview: {repr(content_preview)}"
                    )

                    # Double-check: Có thể marker bị wrap trong whitespace hoặc có vấn đề encoding
                    # Tìm tất cả occurrences của pattern tương tự
                    import re

                    start_pattern = re.compile(re.escape(start_marker))
                    end_pattern = re.compile(re.escape(end_marker))

                    start_matches = start_pattern.findall(chunk_content)
                    end_matches = end_pattern.findall(chunk_content)

                    # Nếu tìm thấy bằng regex nhưng không tìm thấy bằng 'in', có thể có vấn đề encoding
                    if len(start_matches) > 0 and not has_start:
                        logger.warning(
                            f"⚠️ Chunk {chunk_id}: Regex tìm thấy {len(start_matches)} START markers "
                            f"nhưng 'in' operator không tìm thấy. Có thể có vấn đề encoding."
                        )
                        has_start = True  # Override: Nếu regex tìm thấy thì coi như có

                    if len(end_matches) > 0 and not has_end:
                        logger.warning(
                            f"⚠️ Chunk {chunk_id}: Regex tìm thấy {len(end_matches)} END markers "
                            f"nhưng 'in' operator không tìm thấy. Có thể có vấn đề encoding."
                        )
                        has_end = True  # Override: Nếu regex tìm thấy thì coi như có

                # Chỉ báo missing nếu thực sự không có (sau khi double-check)
                if not has_start or not has_end:
                    missing_marker_chunks.append((idx, chunk_id, has_start, has_end))
                    # Rút gọn: chỉ log summary
                    logger.error(
                        f"❌ Chunk {chunk_id}: thiếu markers (START={'✓' if has_start else '✗'}, END={'✓' if has_end else '✗'})"
                    )

            # Xử lý duplicate markers: Loại bỏ phần trùng lặp
            if duplicate_marker_chunks:
                logger.warning(f"⚠️ Đang xử lý {len(duplicate_marker_chunks)} chunks có markers trùng lặp...")
                translated_parts = self._fix_duplicate_markers(
                    translated_parts, duplicate_marker_chunks, original_chunks
                )
                # Validate lại sau khi fix
                marker_validation_result = self._validate_with_markers(translated_parts, original_chunks)
                if marker_validation_result["is_valid"]:
                    return self._merge_with_markers(marker_validation_result["chunks"])

            # Xử lý missing markers: Return None để trigger re-translation
            if missing_marker_chunks:
                # Rút gọn message
                logger.error(f"❌ {len(missing_marker_chunks)} chunks thiếu markers, cần dịch lại")
                return None

        # BƯỚC 3: Similarity-based validation (O(n²) - chậm, chỉ khi cần)
        # Chỉ check similarity cho chunks nghi ngờ
        if suspicious_chunks:
            logger.debug("🔍 Đang kiểm tra similarity cho chunks nghi ngờ...")
            similarity_result = self._validate_with_similarity_selective(
                translated_parts, suspicious_chunks, original_chunks
            )
            return self._merge_with_similarity(similarity_result["chunks"])

        # BƯỚC 4: Fallback: Merge đơn giản
        logger.debug("⚠️ Fallback: Merge đơn giản không có validation")
        return "\n\n".join(translated_parts)

    def _validate_with_markers(self, translated_parts: List[str], original_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Validate chunks sử dụng markers (O(n) - nhanh).
        """
        cleaned_chunks = []
        suspicious_chunks = []

        for i, (part, chunk) in enumerate(zip(translated_parts, original_chunks)):
            # Bỏ qua missing marker
            if part.startswith("[CHUNKS THIẾU:"):
                continue

            chunk_id = chunk["global_id"]
            start_pattern, end_pattern = self._get_marker_patterns(chunk_id)

            # Check markers
            has_start = bool(start_pattern.search(part))
            has_end = bool(end_pattern.search(part))

            # [v7.6] ALWAYS CLEAN MARKERS regardless of validity for the final output
            cleaned_part = part
            cleaned_part = start_pattern.sub("", cleaned_part)
            cleaned_part = end_pattern.sub("", cleaned_part)

            # Bảo hiểm: Quét triệt để bất kỳ marker nào còn sót bằng regex tổng quát
            # Loại bỏ marker trước khi ghép (hỗ trợ cả ID số, chữ và compound ID để dọn dẹp triệt để)
            cleaned_part = re.sub(r"\[CHUNK:.*?:(START|END)\]", "", cleaned_part).strip()
            cleaned_chunks.append(cleaned_part)

            # Track suspicious for validation reporting
            if not has_start or not has_end or len(start_pattern.findall(part)) > 1:
                suspicious_chunks.append(i)

        return {
            "is_valid": len(suspicious_chunks) == 0,
            "chunks": cleaned_chunks,
            "suspicious_chunks": suspicious_chunks,
        }

    def _get_marker_patterns(self, chunk_id: int) -> Tuple[Any, Any]:
        """
        OPTIMIZATION 1.2: Get compiled regex patterns cho chunk markers.

        Cache patterns để tránh recompile mỗi lần validate.

        Args:
            chunk_id: ID của chunk

        Returns:
            Tuple (start_pattern, end_pattern) - compiled regex patterns
        """
        import re

        # Check cache (đã được khởi tạo trong __init__)
        # Check cache
        if chunk_id in self._marker_pattern_cache:
            return self._marker_pattern_cache[chunk_id]

        # Compile patterns
        start_marker = f"[CHUNK:{chunk_id}:START]"
        end_marker = f"[CHUNK:{chunk_id}:END]"

        start_pattern = re.compile(re.escape(start_marker))
        end_pattern = re.compile(re.escape(end_marker))

        # Cache patterns (giới hạn cache size để tránh memory leak)
        if len(self._marker_pattern_cache) < 1000:  # Giới hạn 1000 entries
            self._marker_pattern_cache[chunk_id] = (start_pattern, end_pattern)

        return start_pattern, end_pattern

    def _merge_with_markers(self, cleaned_chunks: List[str]) -> str:
        """
        Merge chunks đã được clean từ markers với bảo toàn paragraph breaks.

        Args:
            cleaned_chunks: List chunks đã được remove markers

        Returns:
            Merged content với paragraph breaks được preserve
        """
        # FIX: Sử dụng ParagraphPreserver để đảm bảo paragraph breaks được preserve
        try:
            from ..utils.paragraph_preserver import ParagraphPreserver

            preserver = ParagraphPreserver(self.config)
            return preserver.merge_chunks_with_paragraph_preservation(cleaned_chunks)
        except Exception as e:
            logger.warning(f"⚠️ Không thể sử dụng ParagraphPreserver: {e}. Fallback về merge đơn giản.")
            # Fallback: merge đơn giản với paragraph breaks
            return "\n\n".join(cleaned_chunks)

    def _fix_duplicate_markers(
        self,
        translated_parts: List[str],
        duplicate_chunks: List[Tuple[int, int, int, int]],
        original_chunks: List[Dict],
    ) -> List[str]:
        """
        Sửa chunks có duplicate markers bằng cách loại bỏ phần trùng lặp.

        Args:
            translated_parts: List chunks đã dịch
            duplicate_chunks: List (idx, chunk_id, start_count, end_count)
            original_chunks: List chunks gốc

        Returns:
            List chunks đã được fix
        """
        fixed_parts = translated_parts.copy()

        for idx, chunk_id, start_count, end_count in duplicate_chunks:
            if idx >= len(fixed_parts):
                continue

            part = fixed_parts[idx]
            start_marker = f"[CHUNK:{chunk_id}:START]"
            end_marker = f"[CHUNK:{chunk_id}:END]"

            # Tìm vị trí các markers
            start_positions = []
            end_positions = []

            pos = 0
            while True:
                pos = part.find(start_marker, pos)
                if pos == -1:
                    break
                start_positions.append(pos)
                pos += len(start_marker)

            pos = 0
            while True:
                pos = part.find(end_marker, pos)
                if pos == -1:
                    break
                end_positions.append(pos)
                pos += len(end_marker)

            # Nếu có duplicate, giữ marker đầu tiên và cuối cùng
            if len(start_positions) > 1:
                # Loại bỏ các start markers trùng lặp (giữ marker đầu tiên)
                for pos in reversed(start_positions[1:]):
                    part = part[:pos] + part[pos + len(start_marker) :]

            if len(end_positions) > 1:
                # Loại bỏ các end markers trùng lặp (giữ marker cuối cùng)
                for pos in reversed(end_positions[:-1]):
                    part = part[:pos] + part[pos + len(end_marker) :]

            fixed_parts[idx] = part
            logger.debug(f"✅ Đã sửa duplicate markers cho chunk {chunk_id}")

        return fixed_parts

    def _validate_with_similarity_selective(
        self,
        translated_parts: List[str],
        suspicious_indices: List[int],
        original_chunks: List[Dict],
    ) -> Dict[str, Any]:
        """
        Validate chunks nghi ngờ sử dụng similarity (chỉ check selective chunks).

        Args:
            translated_parts: List chunks đã dịch
            suspicious_indices: List indices của chunks nghi ngờ
            original_chunks: List chunks gốc

        Returns:
            Dictionary chứa cleaned chunks
        """
        # Chỉ check similarity cho chunks nghi ngờ và chunks liền kề
        chunks_to_check = set(suspicious_indices)
        for idx in suspicious_indices:
            if idx > 0:
                chunks_to_check.add(idx - 1)
            if idx < len(translated_parts) - 1:
                chunks_to_check.add(idx + 1)

        # Sử dụng similarity check cho các chunks này
        cleaned_parts = []
        overlap_count = 0

        for i, part in enumerate(translated_parts):
            if not part or not part.strip():
                continue

            # Chỉ check similarity cho chunks nghi ngờ và liền kề
            if i in chunks_to_check and i > 0 and cleaned_parts:
                prev_part = cleaned_parts[-1]

                # Similarity check logic
                prev_sentences = [s.strip() for s in prev_part.split(". ") if s.strip()]
                current_sentences = [s.strip() for s in part.split(". ") if s.strip()]

                if len(prev_sentences) > 0 and len(current_sentences) > 0:
                    max_overlap_sentences = min(3, len(prev_sentences), len(current_sentences))
                    overlap_found = False
                    overlap_sentences = 0

                    for check_len in range(1, max_overlap_sentences + 1):
                        prev_end = " ".join(prev_sentences[-check_len:])
                        current_start = " ".join(current_sentences[:check_len])

                        similarity = self._calculate_sentence_similarity(prev_end, current_start)
                        if similarity > 0.75:  # 75% giống nhau → overlap
                            overlap_found = True
                            overlap_sentences = check_len
                            break

                    if overlap_found:
                        logger.warning(
                            f"⚠️ [Similarity] Phát hiện overlap {overlap_sentences} câu giữa chunk {i - 1} và chunk {i}"
                        )
                        if len(current_sentences) > overlap_sentences:
                            part = ". ".join(current_sentences[overlap_sentences:])
                            overlap_count += 1
                        else:
                            logger.warning(f"⚠️ Chunk {i} bị overlap hoàn toàn với chunk {i - 1}, bỏ qua")
                            continue

            cleaned_parts.append(part)

        if overlap_count > 0:
            logger.warning(f"⚠️ Đã phát hiện và sửa {overlap_count} overlap(s) bằng similarity check")

        return {"chunks": cleaned_parts}

    def _merge_with_similarity(self, cleaned_chunks: List[str]) -> str:
        """
        Merge chunks đã được clean từ similarity check.

        Args:
            cleaned_chunks: List chunks đã được clean

        Returns:
            Merged content
        """
        return "\n\n".join(cleaned_chunks)

    def _validate_and_merge_with_similarity(self, translated_parts: List[str], original_chunks: List[Dict]) -> str:
        """
        Validate và merge chunks sử dụng similarity-based approach (fallback).
        """
        # Kiểm tra overlap: Tìm các đoạn text lặp lại giữa các chunks liên tiếp
        cleaned_parts = []
        overlap_count = 0

        for i, part in enumerate(translated_parts):
            if not part or not part.strip():
                continue

            # So sánh với chunk trước để tìm overlap
            if i > 0 and cleaned_parts:
                prev_part = cleaned_parts[-1]

                # Tìm overlap: Kiểm tra xem phần cuối của chunk trước có trùng với phần đầu của chunk hiện tại không
                # Overlap có thể là 1-3 câu hoặc 1-2 đoạn văn

                # Phương pháp 1: Kiểm tra overlap theo câu
                prev_sentences = [s.strip() for s in prev_part.split(". ") if s.strip()]
                current_sentences = [s.strip() for s in part.split(". ") if s.strip()]

                if len(prev_sentences) > 0 and len(current_sentences) > 0:
                    # Kiểm tra từ 1-3 câu cuối của prev với 1-3 câu đầu của current
                    max_overlap_sentences = min(3, len(prev_sentences), len(current_sentences))
                    overlap_found = False
                    overlap_sentences = 0

                    for check_len in range(1, max_overlap_sentences + 1):
                        prev_end = " ".join(prev_sentences[-check_len:])
                        current_start = " ".join(current_sentences[:check_len])

                        similarity = self._calculate_sentence_similarity(prev_end, current_start)
                        if similarity > 0.75:  # 75% giống nhau → overlap
                            overlap_found = True
                            overlap_sentences = check_len
                            break

                    if overlap_found:
                        # Rút gọn: chỉ log ở DEBUG
                        logger.debug(f"⚠️ [Similarity] Overlap {overlap_sentences} câu giữa chunk {i - 1} và chunk {i}")
                        # Loại bỏ các câu bị overlap ở đầu current_part
                        if len(current_sentences) > overlap_sentences:
                            part = ". ".join(current_sentences[overlap_sentences:])
                            overlap_count += 1
                        else:
                            # Nếu toàn bộ chunk bị overlap → bỏ chunk này
                            logger.warning(f"⚠️ Chunk {i} bị overlap hoàn toàn với chunk {i - 1}, bỏ qua")
                            continue

                    # Phương pháp 2: Kiểm tra overlap theo đoạn văn (nếu không tìm thấy overlap theo câu)
                    if not overlap_found:
                        prev_paragraphs = [p.strip() for p in prev_part.split("\n\n") if p.strip()]
                        current_paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]

                        if len(prev_paragraphs) > 0 and len(current_paragraphs) > 0:
                            # Kiểm tra đoạn cuối của prev với đoạn đầu của current
                            prev_last_para = prev_paragraphs[-1]
                            current_first_para = current_paragraphs[0]

                            similarity = self._calculate_sentence_similarity(
                                prev_last_para[:200], current_first_para[:200]
                            )
                            if similarity > 0.8:  # 80% giống nhau → overlap đoạn văn
                                logger.debug(f"⚠️ [Similarity] Overlap đoạn văn giữa chunk {i - 1} và chunk {i}")
                                # Loại bỏ đoạn đầu của current_part
                                if len(current_paragraphs) > 1:
                                    part = "\n\n".join(current_paragraphs[1:])
                                    overlap_count += 1
                                else:
                                    logger.warning(f"⚠️ Chunk {i} chỉ có 1 đoạn và bị overlap hoàn toàn, bỏ qua")
                                    continue

            cleaned_parts.append(part)

        if overlap_count > 0:
            logger.warning(f"⚠️ [Similarity] Đã sửa {overlap_count} overlap(s)")

        # Kiểm tra missing content: So sánh tổng độ dài với original
        total_translated_length = sum(len(p) for p in cleaned_parts)
        total_original_length = sum(len(chunk.get("text_original", chunk.get("text", ""))) for chunk in original_chunks)

        if total_original_length > 0:
            ratio = total_translated_length / total_original_length
            if ratio < 0.7:  # Nếu dịch ngắn hơn 30% so với gốc → có thể thiếu
                logger.warning(
                    f"⚠️ Cảnh báo: Nội dung dịch có thể bị thiếu. Gốc: {total_original_length} chars, Dịch: {total_translated_length} chars (tỷ lệ: {ratio:.1%})"
                )
            elif ratio > 1.5:  # Nếu dịch dài hơn 50% so với gốc → có thể có vấn đề
                logger.warning(
                    f"⚠️ Cảnh báo: Nội dung dịch dài bất thường. Gốc: {total_original_length} chars, Dịch: {total_translated_length} chars (tỷ lệ: {ratio:.1%})"
                )

        # Merge với separator
        full_content = "\n\n".join(cleaned_parts)
        return full_content

    def _calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """
        Tính độ tương đồng giữa 2 câu (0-1).
        Sử dụng Jaccard similarity đơn giản dựa trên words.
        """
        if not sent1 or not sent2:
            return 0.0

        # Normalize: lowercase, remove punctuation
        import re

        words1 = set(re.findall(r"\w+", sent1.lower()))
        words2 = set(re.findall(r"\w+", sent2.lower()))

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    # [REMOVED] _verify_chunk_sizes method removed.

    def _delete_chunk_file(self, chunk_id: int) -> None:
        """
        Xóa chunk file và metadata file từ disk.

        Args:
            chunk_id: ID của chunk cần xóa
        """
        chunk_id_str = str(chunk_id)
        strategy = self.progress_manager.storage_config.get("chunk_storage_strategy", "individual_files")

        if strategy == "individual_files":
            chunks_dir = self.progress_manager.chunks_dir
            metadata_dir = getattr(self.progress_manager, "metadata_dir", None)

            # Xóa chunk file (.txt và .txt.gz)
            chunk_file = os.path.join(chunks_dir, f"{chunk_id_str}.txt")
            chunk_file_gz = os.path.join(chunks_dir, f"{chunk_id_str}.txt.gz")

            if os.path.exists(chunk_file):
                try:
                    os.remove(chunk_file)
                    logger.debug(f"Đã xóa chunk file: {chunk_file}")
                except Exception as e:
                    logger.warning(f"Không thể xóa chunk file {chunk_file}: {e}")

            if os.path.exists(chunk_file_gz):
                try:
                    os.remove(chunk_file_gz)
                    logger.debug(f"Đã xóa chunk file: {chunk_file_gz}")
                except Exception as e:
                    logger.warning(f"Không thể xóa chunk file {chunk_file_gz}: {e}")

            # Xóa metadata file nếu có
            if metadata_dir and os.path.exists(metadata_dir):
                metadata_file = os.path.join(metadata_dir, f"{chunk_id_str}.json")
                if os.path.exists(metadata_file):
                    try:
                        os.remove(metadata_file)
                        logger.debug(f"Đã xóa metadata file: {metadata_file}")
                    except Exception as e:
                        logger.warning(f"Không thể xóa metadata file {metadata_file}: {e}")
        else:
            # Với single file strategy, chỉ cần xóa khỏi completed_chunks
            # File sẽ được cập nhật khi save
            logger.debug(f"Chunk {chunk_id} sẽ được xóa khỏi single file khi save")

    def _find_deleted_chunks(self, all_chunks: List[Dict]) -> List[Dict]:
        """Tìm các chunks bị xóa trong quá trình review"""
        deleted_chunks = []

        for chunk in all_chunks:
            chunk_id = chunk["global_id"]

            # Chỉ tìm chunks đã được lưu trong completed_chunks
            if self.progress_manager.is_chunk_completed(chunk_id):
                # Nhưng file không tồn tại (bị xóa thủ công)
                if not self.progress_manager.chunk_file_exists(chunk_id):
                    deleted_chunks.append(chunk)

        return deleted_chunks
