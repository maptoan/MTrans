#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Module Smart Router để chọn model và gọi API bất đồng bộ.

Module này cung cấp intelligent model routing dựa trên:
- Complexity score của chunk
- Force model option (pro/flash)
- Automatic fallback mechanism
- Dynamic safety settings

Sử dụng GenAI Adapter để hỗ trợ cả SDK mới và SDK cũ.
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Union

from ..services.genai_adapter import GenAIClient, create_client
from ..utils.adaptive_timeout import AdaptiveTimeoutCalculator
from .exceptions import APIError, ContentBlockedError, ResourceExhaustedError

logger = logging.getLogger("NovelTranslator")

# --- Constants ---

EMOTIONAL_KEYWORDS = ["泪", "哭", "笑", "怒", "惊", "心痛", "爱", "恨"]
POETIC_MARKERS = ["如", "似", "般", "之", "乎", "者", "也"]

DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]




class SmartModelRouter:
    """
    Lớp chọn model và gọi API bất đồng bộ, với cấu hình an toàn động.

    Tự động chọn model (Pro hoặc Flash) dựa trên complexity score,
    với khả năng force model và fallback mechanism.
    """

    def __init__(self, config: Dict[str, Any], use_new_sdk: bool = True) -> None:
        """
        Khởi tạo Smart Model Router.

        Args:
            config: Configuration dictionary
            use_new_sdk: True để dùng SDK mới, False để dùng SDK cũ
        """
        self.config: Dict[str, Any] = config.get("translation", {})
        self.router_config: Dict[str, Any] = self.config.get("router", {})
        self.complexity_threshold: int = self.router_config.get(
            "complexity_threshold", 70
        )
        self.use_new_sdk: bool = use_new_sdk

        # Client cache to avoid creating new clients per request
        self._client_cache: Dict[str, GenAIClient] = {}

        # OPTIMIZATION 1.3: Complexity score cache để tránh recalculate
        self._complexity_cache: Dict[str, int] = {}

        # Phase 2: Initialize Adaptive Timeout Calculator
        self.config.get("timeout", {})
        self.timeout_calculator = AdaptiveTimeoutCalculator(config)

        safety_level: str = self.config.get("safety_level", "BLOCK_ONLY_HIGH").upper()
        # Use constant template but update threshold dynamically if needed
        self.safety_settings: List[Dict[str, str]] = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": safety_level},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": safety_level},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": safety_level},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": safety_level},
        ]

        # [PHASE 9] Centralized Model Config
        self.config_models: Dict[str, str] = config.get("models", {})
        self.flash_model: str = self.config_models.get("flash", "gemini-2.5-flash")
        self.pro_model: str = self.config_models.get(
            "pro", "gemini-2.5-flash"
        )  # Default to Flash if not set (Flash-Only)

    async def cleanup(self) -> None:
        """
        Cleanup all cached clients. Call this when shutting down.
        """
        for api_key, client in list(self._client_cache.items()):
            try:
                await client.aclose()
            except Exception:
                try:
                    client.close()
                except Exception:
                    pass
        self._client_cache.clear()
        logger.debug("SmartModelRouter: All cached clients cleaned up.")

    def __del__(self) -> None:
        """Destructor - cleanup clients synchronously if possible."""
        for client in self._client_cache.values():
            try:
                client.close()
            except Exception:
                pass
        self._client_cache.clear()

    def analyze_chunk_complexity(
        self, chunk_text: str, relevant_terms_count: int
    ) -> int:
        """
        Phân tích và cho điểm độ phức tạp của một chunk.

        OPTIMIZATION 1.3: Cache complexity score dựa trên chunk text hash.

        Tính điểm dựa trên:
        - Số lượng relevant terms (glossary terms)
        - Emotional keywords
        - Dialogue markers
        - Poetic markers

        Args:
            chunk_text: Text của chunk cần phân tích
            relevant_terms_count: Số lượng glossary terms có trong chunk

        Returns:
            Complexity score (0-100)
        """
        # OPTIMIZATION 1.3: Create cache key
        cache_key = hashlib.md5(
            f"{chunk_text[:500]}_{relevant_terms_count}".encode()
        ).hexdigest()

        # Check cache
        if cache_key in self._complexity_cache:
            return self._complexity_cache[cache_key]

        # Calculate complexity
        score: int = 0
        score += min(relevant_terms_count * 5, 30)

        emotion_count: int = sum(chunk_text.count(kw) for kw in EMOTIONAL_KEYWORDS)
        score += min(emotion_count * 8, 40)

        dialogue_markers: int = chunk_text.count('"') + chunk_text.count('"')
        if dialogue_markers > 4:
            score += 15

        poetic_count: int = sum(chunk_text.count(kw) for kw in POETIC_MARKERS)
        score += min(poetic_count * 3, 15)

        final_score = min(score, 100)

        # Cache result (giới hạn cache size để tránh memory leak)
        if len(self._complexity_cache) < 1000:  # Giới hạn 1000 entries
            self._complexity_cache[cache_key] = final_score

        return final_score

    async def _generate_async(
        self,
        client: GenAIClient,
        prompt: str,
        model_name: str,
        safety_settings: List[Dict[str, str]],
        timeout: Optional[float] = None,
        cached_content: Optional[str] = None,
        worker_id: Optional[int] = None,
    ) -> str:
        """
        Gọi API bất đồng bộ và ném ra exception nếu bị chặn.
        """
        # Use adaptive timeout nếu không có timeout được chỉ định
        if timeout is None:
            if isinstance(prompt, str):
                chunk_size = len(prompt)
            else:
                # Calculate size of multi-turn messages
                chunk_size = sum(
                    len(part.get("text", ""))
                    for msg in prompt
                    for part in msg.get("parts", [])
                )
            timeout = self.timeout_calculator.calculate_timeout(chunk_size, model_name)

        # Prepare config for cached content
        config = None
        if cached_content:
            config = {"cached_content": cached_content}

        # CRITICAL FIX: Do NOT wrap with asyncio.wait_for - let SDK handle timeouts internally
        # The SDK (google-genai) has built-in retry logic and timeout handling.
        # External timeout wrappers can cause premature TimeoutError.
        response = await client.generate_content_async(
            prompt=prompt,  # GenAIClient adapter expects 'prompt' param
            model_name=model_name,
            safety_settings=safety_settings,
            generation_config=config,
            worker_id=worker_id,
        )

        if not response.candidates:
            block_reason: str = "Không rõ"
            try:
                if hasattr(response, "prompt_feedback") and hasattr(
                    response.prompt_feedback, "block_reason"
                ):
                    block_reason = response.prompt_feedback.block_reason.name
            except Exception:
                pass

            raise ContentBlockedError(block_reason)

        translation = response.text
        
        # [CRITICAL UPDATE] Kiểm tra MAX_TOKENS truncation (dù có trả về text hay không)
        finish_reason = "unknown"
        try:
            if hasattr(response, "candidates") and response.candidates:
                # Trích xuất finish_reason an toàn từ object hoặc dict
                if hasattr(response.candidates[0], "finish_reason"):
                    fr = getattr(response.candidates[0], "finish_reason")
                    finish_reason = getattr(fr, "name", str(fr))
                    
                # SDK enum 2 = MAX_TOKENS
                if "MAX_TOKENS" in finish_reason.upper() or finish_reason == "2":
                    error_msg = f"Bản dịch bị cắt cụt do vượt MAX_TOKENS (Finish Reason: {finish_reason})"
                    logger.error(f"❌ {error_msg}")
                    raise ContentBlockedError(error_msg)
        except ContentBlockedError:
            raise
        except Exception as e:
            logger.debug(f"Không thể kiểm tra finish_reason: {e}")

        if not translation or not translation.strip():
            error_msg = f"Model returned empty translation (Finish Reason: {finish_reason})"
            logger.error(f"❌ {error_msg}")
            raise APIError(error_msg)

        return translation, getattr(response, "usage_metadata", None)

    async def translate_chunk_async(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        complexity_score: int,
        api_key: str,
        force_model: Optional[str] = None,
        cached_content: Optional[str] = None,
        key_manager: Any = None,
        worker_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dịch một chunk bất đồng bộ với một API key cụ thể.
        """
        # --- CLIENT CACHING ---
        if api_key in self._client_cache:
            client = self._client_cache[api_key]
            # CRITICAL: Validate cached client - nếu client không hợp lệ (None client với new SDK),
            # invalidate cache và tạo client mới
            if client.use_new_sdk and client.client is None:
                logger.warning(
                    f"Invalid cached client for key {api_key[:10]}... (client=None). Recreating..."
                )
                del self._client_cache[api_key]
                client = create_client(api_key=api_key, use_new_sdk=self.use_new_sdk)
                self._client_cache[api_key] = client
        else:
            # Get timeout from config if available, else default
            timeout = self.config.get("performance", {}).get(
                "http_request_timeout", 600
            )
            client = create_client(
                api_key=api_key, use_new_sdk=self.use_new_sdk, timeout=timeout
            )
            self._client_cache[api_key] = client

        # [PHASE 9] Use models from config
        pro_model_name: str = self.pro_model
        flash_model_name: str = self.flash_model

        # Chọn model dựa trên Strategy & Complexity
        model_name_str: str = ""
        strategy = self.config.get("strategy", "balanced")

        if force_model:
            model_name_str = (
                pro_model_name if force_model == "pro" else flash_model_name
            )
            if force_model == "pro" and strategy == "flash_only":
                logger.warning("Force 'pro' requested despite 'flash_only' strategy.")
        else:
            if strategy == "flash_only":
                model_name_str = flash_model_name
            elif strategy == "pro_only":
                model_name_str = pro_model_name
            else:  # balanced / hybrid
                if complexity_score >= self.complexity_threshold:
                    model_name_str = pro_model_name
                    logger.info(
                        f"⚡ Smart Routing: Complexity {complexity_score} >= {self.complexity_threshold} -> Using Pro Model"
                    )
                else:
                    model_name_str = flash_model_name

        # [PROACTIVE FALLBACK] Kiểm tra xem Pro model có bị quota blocked không trước khi gọi
        if (
            model_name_str == pro_model_name
            and key_manager
            and pro_model_name != flash_model_name
        ):
            if not key_manager.is_pro_available(api_key):
                if strategy in ["balanced", "hybrid"] and not force_model:
                    logger.warning(
                        f"⏩ Proactive Short-circuit: Key {api_key[:10]}... Pro is blocked. Switching to Flash."
                    )
                    model_name_str = flash_model_name
                else:
                    # Nếu force_model='pro' hoặc strategy='pro_only' mà pro bị blocked -> Ném lỗi ResourceExhausted mock
                    logger.error(
                        f"❌ Key {api_key[:10]}... Pro is blocked but Flash fallback not allowed/requested."
                    )
                    raise ResourceExhaustedError(
                        f"Pro model is blocked for key {api_key[:10]}",
                        context=f"Key: {api_key[:10]}..."
                    )

        # Calculate adaptive timeout dựa trên chunk size
        if isinstance(prompt, str):
            chunk_size = len(prompt)
        else:
            chunk_size = sum(
                len(part.get("text", ""))
                for msg in prompt
                for part in msg.get("parts", [])
            )

        timeout = self.timeout_calculator.calculate_timeout(chunk_size, model_name_str)

        start_time = time.time()
        try:
            translation, usage = await self._generate_async(
                client=client,
                prompt=prompt,
                model_name=model_name_str,
                safety_settings=self.safety_settings,
                timeout=timeout,
                cached_content=cached_content,
                worker_id=worker_id,
            )

            # Record response time để cải thiện timeout calculation
            response_time = time.time() - start_time
            self.timeout_calculator.record_response_time(
                chunk_size, response_time, model_name_str
            )

            return {
                "translation": translation,
                "model_used": model_name_str,
                "usage": usage,
            }
        except Exception as e:
            # Fallback logic for Balanced Mode: Pro -> Flash
            if model_name_str == pro_model_name and strategy in ["balanced", "hybrid"]:
                logger.warning(
                    f"⚠️ Pro model failed ({str(e)[:100]}). Falling back to Flash..."
                )
                try:
                    # Retry with Flash (force_model='flash')
                    return await self.translate_chunk_async(
                        prompt,
                        complexity_score,
                        api_key,
                        force_model="flash",
                        cached_content=cached_content,
                        key_manager=key_manager,
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"❌ Fallback to Flash also failed: {str(fallback_error)[:100]}"
                    )
                    raise fallback_error  # Raise original or new error? Raise new one.

            # [STRICT UPDATE] Đã tắt Fallback sang Pro model.
            # Nếu Flash lỗi -> Ném lỗi ra ngoài để retry hoặc xử lý ở cấp manager.

            from ..utils.error_formatter import format_exception_for_logging

            error_info = format_exception_for_logging(
                e, context=f"Model {model_name_str}"
            )

            logger.warning(
                f"Lỗi khi dịch (No Fallback available): "
                f"{error_info['type']}: {error_info['message'][:100]}"
            )

            # Re-raise exception để manager xử lý (retry/fail chunk)
            raise e
        # NOTE: Client is cached and reused across requests.
        # Do NOT close client here - it will be cleaned up when SmartModelRouter is destroyed.

    def _is_api_key_related_error(self, exception: Exception) -> bool:
        """
        Kiểm tra xem lỗi có liên quan đến API key không.

        Các lỗi liên quan đến API key:
        - invalid_key: Key không hợp lệ, dead, hoặc không có quyền
        - quota_exceeded: Key đã vượt quota
        - rate_limit: Key đang bị rate limit (có thể đang chờ cool down)

        Args:
            exception: Exception object

        Returns:
            True nếu lỗi liên quan đến API key, False nếu không
        """
        error_type = type(exception).__name__
        error_msg = str(exception).lower()

        # Check invalid key errors (401, 403, invalid, unauthorized, etc.)
        invalid_key_indicators = [
            "invalid",
            "401",
            "unauthorized",
            "api key",
            "authentication",
            "permission denied",
            "forbidden",
            "403",
            "dead",
        ]
        if any(indicator in error_msg for indicator in invalid_key_indicators):
            return True
        if "401" in str(exception) or "403" in str(exception):
            return True

        # Check quota/rate limit errors (429, quota exceeded, rate limit)
        quota_indicators = [
            "quota",
            "rate limit",
            "429",
            "resource exhausted",
            "resource_exhausted",
            "too many requests",
            "rate_limit_exceeded",
            "exceeded.*quota",
            "cool.*down",
        ]
        if any(indicator in error_msg for indicator in quota_indicators):
            return True
        if "429" in str(exception):
            return True

        # Check SDK-specific exceptions
        if "ResourceExhausted" in error_type:
            return True

        # Network errors (503, 502, 500) và generation errors KHÔNG liên quan đến API key
        # → Có thể fallback
        return False
