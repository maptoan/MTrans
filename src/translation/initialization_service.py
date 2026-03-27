# -*- coding: utf-8 -*-

"""
InitializationService: Tách biệt logic khởi tạo tài nguyên, warm-up và kiểm tra metadata.
Giúp NovelTranslator (God Object) trở nên gọn nhẹ hơn.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    pass

from .exceptions import ConfigurationError, ResourceExhaustedError, TranslationError

logger = logging.getLogger("NovelTranslator")


class InitializationService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_config = config.get("performance", {})
        self.translation_config = config.get("translation", {})
        self.metadata_config = config.get("metadata", {})

    async def initialize_shared_resources(
        self, valid_api_keys: List[str], existing_key_manager: Any = None
    ) -> Dict[str, Any]:
        """
        Khởi tạo các tài nguyên CHUNG (không phụ thuộc vào novel_name).
        Có thể chạy song song với input preprocessing.
        Nếu existing_key_manager được truyền (từ main), dùng chung thay vì tạo mới.
        """
        logger.info("Initializing Shared Resources (Parallel)...")

        # Lazy imports to speed up startup
        from ..managers.glossary_manager import GlossaryManager
        from ..managers.relation_manager import RelationManager
        from ..managers.style_manager import StyleManager
        from ..output.formatter import OutputFormatter
        from ..preprocessing.chunker import SmartChunker
        from ..services.gemini_api_service import GeminiAPIService
        from ..translation.model_router import SmartModelRouter
        from ..translation.prompt_builder import PromptBuilder
        from ..utils.error_handler import CentralizedErrorHandler
        from ..utils.metrics_collector import MetricsCollector
        from .context_manager import ContextManager
        from .prompt_orchestrator import PromptOrchestrator
        from .quota_detector import QuotaDetector
        from .result_handler import ResultHandler

        # 1. Key Manager: dùng chung nếu main đã tạo (để preprocessing/metadata/translation dùng chung)
        if existing_key_manager is not None:
            key_manager = existing_key_manager
            logger.info("Sử dụng key_manager chung (từ main) cho translation.")
        else:
            key_manager = await self._init_key_manager(valid_api_keys)

        # 2. Initialize Core Services
        metrics_collector = MetricsCollector(self.config)
        error_handler = CentralizedErrorHandler(self.config)

        use_new_sdk = self.translation_config.get("use_new_sdk", True)
        model_router = SmartModelRouter(self.config, use_new_sdk=use_new_sdk)
        chunker = SmartChunker(self.config)

        # 3. Initialize Managers (Metadata)
        forced_encoding = self.config.get("preprocessing", {}).get("force_encoding")
        style_profile_path = self.metadata_config.get("style_profile_path")
        glossary_path = self.metadata_config.get("glossary_path")
        character_relations_path = self.metadata_config.get("character_relations_path")

        style_manager = StyleManager(style_profile_path, encoding=forced_encoding)
        glossary_manager = GlossaryManager(
            glossary_path,
            encoding=forced_encoding,
            api_keys=valid_api_keys,
            key_manager=key_manager,
        )
        relation_manager = RelationManager(
            character_relations_path,
            glossary_manager,
            encoding=forced_encoding,
            api_keys=valid_api_keys,
            key_manager=key_manager,
        )

        document_type = self.metadata_config.get("document_type", "novel")
        prompt_builder = PromptBuilder(
            style_manager,
            glossary_manager,
            relation_manager,
            document_type=document_type,
            config=self.config,
        )

        output_formatter = OutputFormatter(self.config)

        # 3.5. Initialize Context Management (Stage 5B)
        context_manager = ContextManager(self.config)

        # 4. Initialize GeminiAPIService
        gemini_service = GeminiAPIService(
            valid_api_keys, 
            config=self.config, 
            use_new_sdk=use_new_sdk,
            distributor=key_manager
        )

        max_concurrent_requests = self.performance_config.get(
            "max_concurrent_requests", 3
        )
        request_semaphore = asyncio.Semaphore(max_concurrent_requests)

        # 6. Initialize Stage 5A Orchestrators
        quota_detector = QuotaDetector()
        prompt_orchestrator = PromptOrchestrator(
            glossary_manager=glossary_manager,
            relation_manager=relation_manager,
            prompt_builder=prompt_builder,
            gemini_service=gemini_service,
            config=self.config,
            document_type=document_type
        )
        result_handler = ResultHandler(metrics_collector=metrics_collector)

        return {
            "key_manager": key_manager,
            "metrics_collector": metrics_collector,
            "error_handler": error_handler,
            "model_router": model_router,
            "chunker": chunker,
            "style_manager": style_manager,
            "glossary_manager": glossary_manager,
            "relation_manager": relation_manager,
            "prompt_builder": prompt_builder,
            "output_formatter": output_formatter,
            "gemini_service": gemini_service,
            "request_semaphore": request_semaphore,
            "document_type": document_type,
            "context_manager": context_manager,
            "quota_detector": quota_detector,
            "prompt_orchestrator": prompt_orchestrator,
            "result_handler": result_handler,
        }

    async def initialize_novel_specific_resources(
        self, shared_resources: Dict[str, Any], novel_name: str
    ) -> Dict[str, Any]:
        """
        Khởi tạo các tài nguyên CỤ THỂ theo novel (ProgressManager, OutputManager, UIHandler).
        Chạy sau khi đã có novel_name (sau preprocessing).
        """
        logger.info(f"Initializing Novel Specific Resources for '{novel_name}'...")
        from ..managers.progress_manager import ProgressManager
        from .format_converter import FormatConverter
        from .output_manager import OutputManager
        from .ui_handler import UIHandler

        progress_manager = ProgressManager(self.config, novel_name)
        
        # Phase 8A: Initialize OutputManager
        output_manager = OutputManager(
            progress_manager=progress_manager,
            output_formatter=shared_resources["output_formatter"],
            novel_name=novel_name,
            config=self.config,
        )
        
        # Phase 8B: Initialize UIHandler
        ui_handler = UIHandler(
            output_formatter=shared_resources["output_formatter"],
            novel_name=novel_name,
            config=self.config,
        )
        
        # Phase 10.1: Initialize FormatConverter
        from .format_converter import FormatConverter
        format_converter = FormatConverter(
            output_formatter=shared_resources["output_formatter"],
            config=self.config,
        )

        # Phase 11: Initialize BatchQAProcessor
        from .batch_qa_processor import BatchQAProcessor
        batch_qa_processor = BatchQAProcessor(
            self.config, 
            shared_resources["prompt_builder"],
            shared_resources["gemini_service"]
        )

        # Merge shared and specific resources
        resources = shared_resources.copy()
        resources["progress_manager"] = progress_manager
        resources["output_manager"] = output_manager
        resources["ui_handler"] = ui_handler
        resources["format_converter"] = format_converter
        resources["batch_qa_processor"] = batch_qa_processor
        return resources




    async def initialize_all(
        self, valid_api_keys: List[str], novel_name: str
    ) -> Dict[str, Any]:
        """
        Khởi tạo tất cả (Wrapper cho backward compatibility).
        """
        shared = await self.initialize_shared_resources(valid_api_keys)
        return await self.initialize_novel_specific_resources(shared, novel_name)

    async def _init_key_manager(self, valid_api_keys: List[str]) -> Any:
        """Khởi tạo Key Manager với SmartKeyDistributor v7.0."""
        # [Adaptive Scaling]
        # Thay vì giới hạn cứng max_workers = 5, ta set bằng số lượng keys hợp lệ.
        # ExecutionManager sẽ spawn số workers tương ứng.
        max_workers = len(valid_api_keys)
        if max_workers == 0:
            max_workers = 1  # Fallback an toàn

        # Config logging
        logger.info(
            f"⚡ Adaptive Scaling: Configured {max_workers} potential workers based on available keys."
        )

        # NOTE: KeyInitializationWorkflow (legacy) đã bị disable để dùng SmartKeyDistributor.
        # SmartKeyDistributor sẽ tự động phân bổ worker dựa trên chunks.

        # Khởi tạo SmartKeyDistributor
        # num_chunks=9999: Optimistic allocation (giả định nhiều chunk) để ưu tiên translation keys (70%)
        # Allocation thực tế sẽ được update lại trong Translator.translate_novel
        from ..services.smart_key_distributor import SmartKeyDistributor

        # [Fix] Pass key_management config section explicitly
        key_mgmt_config = self.config.get("key_management", {})

        key_manager = SmartKeyDistributor(
            api_keys=valid_api_keys, num_chunks=9999, config=self.config
        )

        return key_manager

        # Log summary of key assignments (optimization: replaces 60 individual logs)
        if (
            hasattr(key_manager, "_key_assignment_count")
            and key_manager._key_assignment_count > 0
        ):
            logger.info(
                f"✅ Assigned {key_manager._key_assignment_count} API keys to workers"
            )

        # [Strict Logic Step 3 & 4]
        # Kiểm tra ngay lập tức xem có key nào sống không
        active_count = key_manager.get_active_key_count()
        if active_count == 0:
            logger.warning("⚠️ Không có key nào SẴN SÀNG NGAY LẬP TỨC.")

            # Kiểm tra thời gian cooldown của các key
            key_manager.get_status_summary()
            # Tìm key có thời gian chờ thấp nhất
            min_wait = float("inf")
            import datetime

            now = datetime.datetime.now()

            for key, status in key_manager.key_statuses.items():
                if status.rate_limit_reset and status.rate_limit_reset > now:
                    wait = (status.rate_limit_reset - now).total_seconds()
                    if wait < min_wait:
                        min_wait = wait

            # Nếu min_wait < 5 phút (300s) -> Chờ và retry
            if min_wait < 300:  # 5 minutes
                logger.info(
                    f"⏳ Thời gian chờ ngắn nhất: {min_wait:.1f}s (< 5 phút). Đang chờ để retry..."
                )
                # Cap minimum wait to 5s to be safe
                sleep_time = max(5, int(min_wait) + 5)
                logger.info(f"💤 Sleeping {sleep_time}s...")
                await asyncio.sleep(sleep_time)

                # Check lại lần nữa
                active_count = key_manager.get_active_key_count()
                if active_count > 0:
                    logger.info(f"✅ Đã có {active_count} key hồi phục sau khi chờ!")
                    return key_manager

            # Nếu vẫn = 0 -> STOP
            logger.error("❌ KHÔNG CÓ KEY NÀO KHẢ DỤNG.")
            logger.error(
                "   - Tất cả module đều dead hoặc đang cooldown quá lâu (>5ph)."
            )
            logger.error("   - Vui lòng kiểm tra lại quota hoặc bổ sung key mới.")
            raise ResourceExhaustedError(
                "Đã sử dụng hết tất cả API Keys! Vui lòng chờ reset quota hoặc thêm key mới."
            )

        return key_manager

    async def warm_up_resources(
        self, resources: Dict[str, Any], api_keys: List[str]
    ) -> Dict[str, str]:
        """Thực hiện warm-up (context caching) cho các API keys."""
        use_cache = self.translation_config.get("context_caching", {}).get(
            "enabled", False
        )
        if not use_cache or not api_keys:
            return {}

        logger.info(f"🔥 Warming up resources for {len(api_keys)} workers...")

        gemini_service = resources["gemini_service"]
        prompt_builder = resources["prompt_builder"]
        glossary_manager = resources["glossary_manager"]
        relation_manager = resources["relation_manager"]
        request_semaphore = resources["request_semaphore"]

        # Build Static Prefix Content
        full_glossary = glossary_manager.get_full_glossary_dict()
        full_relations = relation_manager.get_full_relation_text()

        static_prefix = prompt_builder.build_cacheable_prefix(
            full_glossary=full_glossary, full_relations=full_relations
        )

        # Token count check (optimization)
        try:
            est_tokens = await gemini_service.count_tokens_async(
                static_prefix, api_key=api_keys[0]
            )
            logger.info(f"Context Cache Prefix Size: {est_tokens} tokens")
        except Exception:
            est_tokens = len(static_prefix) // 4
            logger.debug(f"Estimated Prefix Size: ~{est_tokens} tokens")

        ttl_minutes = self.translation_config.get("context_caching", {}).get(
            "ttl_minutes", 60
        )

        caching_model = self.translation_config.get("context_caching", {}).get(
            "model", "gemini-2.5-flash"
        )

        key_cache_map = {}

        async def warm_up_one(key: str, index: int):
            try:
                # Staggered delay để tránh burst quota
                if index > 0:
                    await asyncio.sleep(index * 1.5)

                async with request_semaphore:
                    # Gọi service để tạo hoặc lấy cache (now async)
                    cache_name = await gemini_service.get_or_create_context_cache(
                        content=static_prefix,
                        ttl_minutes=ttl_minutes,
                        model_name=caching_model,
                        api_key=key,
                    )
                    if cache_name:
                        key_cache_map[key] = cache_name
            except Exception as e:
                logger.warning(f"Failed to warm up key {key[:8]}...: {e}")

        # Chạy rải đều các keys
        await asyncio.gather(*(warm_up_one(k, i) for i, k in enumerate(api_keys)))

        logger.info(
            f"✅ Context warm-up completed: {len(key_cache_map)} caches active."
        )
        return key_cache_map

    def check_metadata(self, resources: Dict[str, Any]) -> None:
        """Kiểm tra và log trạng thái metadata."""
        logger.info("=" * 80)
        logger.info("📋 METADATA COMPLIANCE CHECK")
        logger.info("=" * 80)

        style_manager = resources["style_manager"]
        glossary_manager = resources["glossary_manager"]
        relation_manager = resources["relation_manager"]

        if style_manager.is_loaded():
            logger.info(
                f"✅ Style profile: Loaded ({len(style_manager.profile)} entries)"
            )
        else:
            logger.warning("⚠️ Style profile: Not loaded or empty")

        if glossary_manager.is_loaded():
            logger.info(
                f"✅ Glossary: Loaded ({len(glossary_manager.glossary_df)} terms)"
            )
        else:
            logger.warning("⚠️ Glossary: Not loaded or empty")

        if relation_manager.is_loaded():
            logger.info(
                f"✅ Character relations: Loaded ({len(relation_manager.relations_df)} relations)"
            )
        else:
            logger.info("ℹ️ Character relations: No relations defined")

        logger.info("=" * 80)
