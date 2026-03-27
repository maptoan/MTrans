#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Gemini API Service với API key rotation và quota management.

Module này cung cấp unified interface để gọi Gemini API với:
- API key rotation tự động
- Quota management
- Retry logic với exponential backoff
- File upload và caching
- Fallback model support

Tích hợp với APIKeyManager để quản lý multiple keys và theo dõi usage.
"""

import asyncio
import hashlib
import json as _json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .api_key_manager import APIKeyManager
from .genai_adapter import GenAIClient, create_client
from src.utils.path_manager import get_cache_dir

logger = logging.getLogger("NovelTranslator")

# --- Constants ---

DEFAULT_MODEL_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# Safety settings (string-based context for SDK compatibility)
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

QUOTA_ERROR_INDICATORS = [
    "quota",
    "rate limit",
    "429",
    "resource exhausted",
    "resource_exhausted",
    "too many requests",
    "rate_limit_exceeded",
]


class GeminiAPIService:
    """
    Gemini API Service với API key rotation và quota management.

    Sử dụng GenAI Adapter để hỗ trợ cả SDK mới (google-genai) và SDK cũ (google-generativeai).
    Tự động rotate API keys, quản lý quota, và retry với exponential backoff.
    """

    def __init__(
        self,
        api_keys: List[str],
        config: Optional[Dict[str, Any]] = None,
        use_new_sdk: bool = True,
        distributor: Optional[Any] = None,
    ) -> None:
        """
        Khởi tạo Gemini API Service.

        Args:
            api_keys: Danh sách API keys để sử dụng (rotate tự động)
            config: Optional configuration dict
            use_new_sdk: True để dùng SDK mới (google-genai), False để dùng SDK cũ
            distributor: SmartKeyDistributor instance (v7.5)

        Raises:
            ValueError: Nếu api_keys rỗng
        """
        if not api_keys:
            raise ValueError("api_keys không được rỗng")

        self.api_keys: List[str] = api_keys
        self.config: Dict[str, Any] = config or {}
        self.use_new_sdk: bool = use_new_sdk
        self.distributor = distributor
        self.cache_dir: Path = get_cache_dir(self.config)

        # Initialize API key manager
        # [v9.1] Unified: Nếu có distributor, dùng chung _state của nó thay vì tạo mới
        if distributor and hasattr(distributor, "_state"):
            self.key_manager = distributor._state
            logger.info("GeminiAPIService: Unified APIKeyManager with distributor state.")
        else:
            self.key_manager: APIKeyManager = APIKeyManager(api_keys, config)

        # Gemini configuration
        self.model_config: Dict[str, Any] = {
            "temperature": self.config.get(
                "temperature", DEFAULT_MODEL_CONFIG["temperature"]
            ),
            "top_p": self.config.get("top_p", DEFAULT_MODEL_CONFIG["top_p"]),
            "top_k": self.config.get("top_k", DEFAULT_MODEL_CONFIG["top_k"]),
            "max_output_tokens": self.config.get(
                "max_output_tokens", DEFAULT_MODEL_CONFIG["max_output_tokens"]
            ),
        }

        # Use module constant
        self.safety_settings: List[Dict[str, Any]] = SAFETY_SETTINGS

        # Current active key và client
        self.current_key: Optional[str] = None
        self.current_client: Optional[GenAIClient] = None

        # Initialize caches
        self._initialize_caches()

        # [PHASE 9] Centralized Model Config
        self.default_model: str = self.config.get("models", {}).get(
            "default", "gemini-2.5-flash"
        )

        logger.info(
            f"GeminiAPIService initialized with {len(api_keys)} API keys (use_new_sdk={use_new_sdk})"
        )

    async def cleanup(self) -> None:
        """
        Cleanup resources - đóng clients trước khi destroy.
        """
        if self.current_client:
            try:
                await self.current_client.aclose()
            except Exception as e:
                logger.debug(f"Error cleaning up GeminiAPIService client: {e}")
            finally:
                self.current_client = None
        self.current_key = None

    def __del__(self) -> None:
        """
        Destructor để cleanup khi object bị garbage collected.
        """
        if self.current_client:
            try:
                self.current_client.close()
            except Exception:
                pass
            finally:
                self.current_client = None

        # Cache paths được khởi tạo tại _initialize_caches()

    async def _get_client(self) -> GenAIClient:
        """
        Lấy hoặc tạo GenAI Client với current API key.
        """
        # [v7.6] Ensure current_key is valid
        if not self.current_key:
            if self.distributor:
                # [v9.1] get_available_key now async
                self.current_key = await self.distributor.get_available_key()
            else:
                self.current_key = self.key_manager.get_available_key()
                
        if not self.current_key:
            raise ValueError("No available API keys to create client.")

        # Tạo client mới nếu chưa có hoặc key đã thay đổi
        if not self.current_client or self.current_client.api_key != self.current_key:
            # [v7.5] Giảm timeout mặc định xuống 90s (tránh treo 600s như trước)
            request_timeout = self.config.get("performance", {}).get(
                "http_request_timeout", 90
            )

            self.current_client = create_client(
                api_key=self.current_key,
                use_new_sdk=self.use_new_sdk,
                timeout=request_timeout,
            )

        return self.current_client

    def _detect_error_type(
        self, exception: Exception, error_msg: str, error_type_name: str
    ) -> str:
        """
        Phát hiện loại lỗi từ exception để xử lý đúng cách.

        Args:
            exception: Exception object
            error_msg: Error message string
            error_type_name: Type name của exception

        Returns:
            Error type string: "quota_exceeded", "rate_limit", "invalid_key", "network_error", "generation_error"
        """
        error_msg_lower = error_msg.lower()
        error_type_name.lower()

        # CRITICAL: Check exception cause chain (new SDK wraps 429 as TimeoutError)
        # Walk through the exception chain to find the root cause
        cause = exception
        full_error_chain = error_msg_lower
        while cause is not None:
            cause_msg = str(cause).lower()
            cause_type = type(cause).__name__
            full_error_chain += " " + cause_msg

            # Check if any cause indicates quota/rate limit
            if (
                "429" in cause_msg
                or "quota" in cause_msg
                or "resourceexhausted" in cause_type.lower()
            ):
                logger.debug(
                    f"Found quota error in exception chain: {cause_type}: {cause_msg[:100]}"
                )
                return "quota_exceeded"

            cause = getattr(cause, "__cause__", None) or getattr(
                cause, "__context__", None
            )

        # Check quota/rate limit errors in full error chain
        if any(indicator in full_error_chain for indicator in QUOTA_ERROR_INDICATORS):
            return "quota_exceeded"
        if "429" in error_msg or "429" in error_type_name:
            return "quota_exceeded"

        # Check invalid key errors
        invalid_key_indicators = [
            "invalid",
            "401",
            "unauthorized",
            "api key",
            "authentication",
            "permission denied",
            "forbidden",
            "403",
        ]
        if any(indicator in error_msg_lower for indicator in invalid_key_indicators):
            if "401" in error_msg or "401" in error_type_name:
                return "invalid_key"
            if "403" in error_msg or "403" in error_type_name:
                return "invalid_key"

        # Check network/timeout errors - but only if not quota-related
        network_indicators = [
            "timeout",
            "deadline exceeded",
            "connection",
            "network",
            "unavailable",
            "service unavailable",
            "503",
            "502",
            "500",
        ]
        if any(indicator in error_msg_lower for indicator in network_indicators):
            return "network_error"

        # Check SDK-specific exceptions
        # SDK cũ: google.api_core.exceptions.ResourceExhausted
        if "ResourceExhausted" in error_type_name:
            return "quota_exceeded"

        # Default: generation error
        return "generation_error"

    def _extract_text(self, response: Any) -> Optional[str]:
        """
        Extract text từ response object của Gemini SDK.

        Hỗ trợ nhiều cấu trúc response khác nhau để đảm bảo tương thích
        với cả SDK mới và SDK cũ.

        Args:
            response: Response object từ Gemini API

        Returns:
            Extracted text string hoặc None nếu không tìm thấy
        """
        try:
            # Trường hợp phổ biến: response.text
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            pass

        # Thử duyệt candidates → content → parts
        try:
            candidates = getattr(response, "candidates", None)
            if candidates:
                parts = getattr(candidates[0], "content", None)
                if parts and hasattr(parts, "parts"):
                    texts: List[str] = []
                    for part in parts.parts:
                        t = getattr(part, "text", None)
                        if t:
                            texts.append(t)
                    if texts:
                        return "\n".join(texts)
        except Exception:
            pass

        # Thử chuyển sang dict và đọc các trường quen thuộc
        try:
            as_dict: Optional[Dict[str, Any]] = None
            if hasattr(response, "to_dict"):
                as_dict = response.to_dict()
            elif isinstance(response, dict):
                as_dict = response
            if as_dict:
                # Tìm text trong các paths phổ biến
                if "text" in as_dict and as_dict["text"]:
                    return as_dict["text"]
                # candidates[0].content.parts[].text
                candidates = as_dict.get("candidates") or []
                if candidates:
                    content = candidates[0].get("content") or {}
                    parts = content.get("parts") or []
                    texts = [
                        p.get("text")
                        for p in parts
                        if isinstance(p, dict) and p.get("text")
                    ]
                    if texts:
                        return "\n".join(texts)
        except Exception:
            pass

        return None

    async def generate_content_async(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        max_retries: int = 3,
        response_mime_type: Optional[str] = None,
        max_output_tokens_override: Optional[int] = None,
        api_key: Optional[str] = None,
        worker_id: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate content với API key rotation và retry logic.
        """
        failed_key = None

        for attempt in range(max_retries):
            try:
                # [PHASE 9] Use default model if not provided
                target_model = model_name or self.default_model

                # [PHASE 13] Support specific api_key for worker affinity
                # [v7.5] Cải tiến: Nếu là retry, BẮT BUỘC dùng key mới nếu distributor khả dụng
                # [v7.6] FIX: Nếu api_key truyền vào là None, phải lấy key mới thay thế
                if self.distributor and worker_id is not None:
                    self.current_key = await self.distributor.get_key_for_worker(worker_id)
                elif api_key and attempt == 0:
                    self.current_key = api_key
                
                # [v7.6] Last resort fallback if key is still missing
                # [v9.1] get_available_key is async & preference to distributor for locking
                if not self.current_key:
                    if self.distributor:
                        self.current_key = await self.distributor.get_available_key()
                    else:
                        self.current_key = self.key_manager.get_available_key(exclude_key=failed_key)
                
                if not self.current_key:
                    raise ValueError("No available API keys in pool")

                # CRITICAL: Add delay TRƯỚC KHI gửi request để tránh rate limit
                if self.distributor:
                    await self.distributor.add_delay_between_requests(self.current_key)
                else:
                    await self.key_manager.add_delay_between_requests(self.current_key)

                # Get client (now async)
                client = await self._get_client()

                # Build generation config
                gen_cfg = dict(self.model_config)
                if response_mime_type:
                    gen_cfg["response_mime_type"] = response_mime_type
                if max_output_tokens_override:
                    gen_cfg["max_output_tokens"] = max_output_tokens_override

                # Generate content
                logger.debug(
                    f"[{self.__class__.__name__}] [ALLOC] "
                    f"Worker {worker_id if worker_id is not None else 'N/A'}: "
                    f"Sử dụng Key {self.key_manager._mask_key(self.current_key)} (attempt {attempt + 1}/{max_retries})"
                )

                response = await client.generate_content_async(
                    prompt=prompt,
                    model_name=target_model,
                    safety_settings=self.safety_settings,
                    generation_config=gen_cfg,
                )

                extracted = self._extract_text(response) if response else None
                if extracted:
                    # Mark success
                    if self.distributor:
                        self.distributor.mark_request_success(self.current_key)
                    else:
                        await self.key_manager.mark_request_success(self.current_key)

                    logger.debug(
                        f"[{self.__class__.__name__}] [SUCCESS] "
                        f"Worker {worker_id if worker_id is not None else 'N/A'}: "
                        f"Hoàn thành với Key {self.key_manager._mask_key(self.current_key)}"
                    )
                    return extracted
                else:
                    # Nếu không có text, thử đọc finish_reason để quyết định retry / fallback
                    finish_reason: Optional[str] = None
                    try:
                        if hasattr(response, "candidates") and response.candidates:
                            finish_reason = getattr(
                                response.candidates[0], "finish_reason", None
                            )
                        elif isinstance(response, dict):
                            cands = response.get("candidates") or []
                            if cands:
                                finish_reason = cands[0].get("finish_reason")
                    except Exception:
                        pass

                    raise ValueError(
                        f"Empty response from Gemini (finish_reason={finish_reason})"
                    )

            except Exception as e:
                error_msg = str(e)
                error_type_name = type(e).__name__

                # Detect error type từ exception message và type
                error_type = self._detect_error_type(e, error_msg, error_type_name)
                failed_key = self.current_key

                from ..utils.error_formatter import format_exception_for_logging

                error_info = format_exception_for_logging(
                    e,
                    context=f"Worker {worker_id}, Key {self.key_manager._mask_key(failed_key) if failed_key else 'None'} (attempt {attempt + 1})",
                )
                logger.warning(
                    f"[{self.__class__.__name__}] [ERROR] "
                    f"Key {self.key_manager._mask_key(failed_key) if failed_key else 'None'}: "
                    f"{error_type} - {error_info['short']}"
                )
                logger.debug(error_info["full"])

                # Mark error với detected error type
                if failed_key:
                    if self.distributor:
                        await self.distributor.mark_request_error(failed_key, error_type, error_msg)
                        
                        # [v7.5] QUAN TRỌNG: Kích hoạt xoay key lập tức cho Worker nếu lỗi có thể phục hồi
                        # (429, 503, 500, timeout)
                        retryable_errors = ["quota_exceeded", "rate_limit", "network_error", "timeout"]
                        if error_type in retryable_errors or "deadline" in error_msg.lower():
                            logger.warning(f"🔄 Worker {worker_id}: Phát hiện lỗi phục hồi được ({error_type}). Yêu cầu đổi Key...")
                            await self.distributor.replace_worker_key(worker_id or 0, failed_key, error_type, error_msg)
                    else:
                        await self.key_manager.mark_request_error(failed_key, error_type, error_msg)

                # Check if we should try another key
                if attempt < max_retries - 1:
                    # Logic xoay key nhanh
                    if not self.distributor:
                        # Fallback logic cũ nếu không dùng Distributor
                        # [v9.1] Use distributor for locking if available
                        if self.distributor:
                            new_key = await self.distributor.get_available_key()
                        else:
                            new_key = self.key_manager.get_available_key(exclude_key=failed_key)
                        if new_key:
                            self.current_key = new_key
                            logger.info(f"🔄 Switched to new key: {self.current_key[:10]}")
                            continue
                        else:
                            # Chờ cooldown
                            retry_wait = self.key_manager._extract_retry_delay(error_msg) or 60
                            wait_time = max(retry_wait, 2**attempt)
                            logger.info(f"⏳ Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                    else:
                        # Với Distributor, key mới đã được gán vào worker_keys bởi replace_worker_key ở trên
                        # Vòng lặp tiếp theo sẽ tự động lấy key mới qua get_key_for_worker
                        continue
                else:
                    logger.error(f"All attempts failed. Last error: {error_msg}")
                    raise Exception(
                        f"Failed to generate content after {max_retries} attempts: {error_msg}"
                    )

        raise ValueError("No available API keys after all attempts")


        raise ValueError("No available API keys after all attempts")

    # ===== Files cache support =====
    def _hash_file(self, path: str) -> str:
        """
        Hash file để dùng làm cache key.

        Args:
            path: Đường dẫn file

        Returns:
            SHA256 hash string
        """
        p = Path(path)
        h = hashlib.sha256()
        h.update(str(p.resolve()).encode("utf-8"))
        try:
            h.update(str(p.stat().st_mtime_ns).encode("utf-8"))
            h.update(str(p.stat().st_size).encode("utf-8"))
        except (OSError, FileNotFoundError):
            pass
        return h.hexdigest()

    def _initialize_caches(self) -> None:
        """Initialize all caches."""
        # Files cache
        self.files_cache_path: Path = self.cache_dir / "gemini_files.json"
        self.files_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._files_cache: Dict[str, Any] = self._load_files_cache()

        # Context cache
        self.context_cache_path: Path = self.cache_dir / "gemini_context_caches.json"
        self._context_cache: Dict[str, Any] = self._load_context_cache()

    def _load_files_cache(self) -> Dict[str, Any]:
        """Load files cache from disk."""
        if self.files_cache_path.exists():
            try:
                data = _json.loads(self.files_cache_path.read_text(encoding="utf-8"))
                # Migration: if any top level key's value is not a dict of dicts, it's old
                if data and not all(isinstance(v, dict) for v in data.values()):
                    logger.warning("Old files cache format detected, resetting.")
                    return {}
                return data
            except Exception as e:
                logger.warning(f"Failed to load files cache: {e}")
                return {}
        return {}

    def _load_context_cache(self) -> Dict[str, Any]:
        """Load context cache from disk."""
        if self.context_cache_path.exists():
            try:
                data = _json.loads(self.context_cache_path.read_text(encoding="utf-8"))
                # Migration: if any top level key's value is not a dict, it's the old format
                # We'll just clear it or handle it. Clearing is safer since schemas changed.
                if data and not all(isinstance(v, dict) for v in data.values()):
                    logger.warning("Old context cache format detected, resetting.")
                    return {}
                return data
            except Exception as e:
                logger.warning(f"Failed to load context cache: {e}")
                return {}
        return {}

    def _save_files_cache(self) -> None:
        """
        Save files cache ra disk.

        Returns:
            None
        """
        try:
            self.files_cache_path.write_text(
                _json.dumps(self._files_cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning(f"Failed to save files cache: {e}", exc_info=True)

    def _save_context_cache(self) -> None:
        """Save context cache to disk."""
        try:
            self.context_cache_path.write_text(
                _json.dumps(self._context_cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save context cache: {e}", exc_info=True)

    async def get_or_create_context_cache(
        self,
        content: str,
        ttl_minutes: int = 60,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get existing active context cache or create a new one for a specific API key.

        Args:
            content: The huge text content to cache.
            ttl_minutes: TTL in minutes.
            model_name: Target model name.
            api_key: Optional API key. If not provided, uses current_key.

        Returns:
            The resource name of the cache (e.g. 'cachedContents/xxxx') or None if failed.
        """
        if not self.use_new_sdk:
            return None

        # Determine which key to use
        target_key = api_key or self.current_key
        if not target_key:
            if self.distributor:
                target_key = await self.distributor.get_available_key()
            else:
                target_key = self.key_manager.get_available_key()
            self.current_key = target_key

        # Hash API key to use as index (don't store raw key in JSON if possible, but hash is fine)
        key_hash = hashlib.md5(target_key.encode()).hexdigest()

        # Hash content to check existence (and model dependence)
        target_model = model_name or self.default_model
        h = hashlib.sha256()
        h.update(content.encode("utf-8"))
        h.update(f"model:{target_model}".encode("utf-8"))
        cache_key = h.hexdigest()

        # Check local cache
        cache_entry = self._context_cache.get(cache_key, {})
        cached_info = cache_entry.get(key_hash)

        if cached_info:
            # Check expiration
            expire_time_str = cached_info.get("expire_time")  # ISO format
            if expire_time_str:
                try:
                    expire_time = datetime.fromisoformat(expire_time_str)
                    # Add buffer of 5 minutes to be safe
                    if datetime.now(timezone.utc) < expire_time - timedelta(minutes=5):
                        logger.debug(
                            f"Using existing context cache for key {key_hash[:8]}: {cached_info['name']}"
                        )
                        return cached_info["name"]
                    else:
                        logger.debug(
                            f"Context cache for key {key_hash[:8]} expired, creating new one."
                        )
                except Exception:
                    logger.warning(
                        f"Invalid expire_time in cache for key {key_hash[:8]}, creating new one."
                    )

        # Create new cache
        try:
            # Get client for the specific key
            # We temporarily swap current_key to get the right client
            self.current_key = target_key
            client = await self._get_client()

            cache_obj = client.create_context_cache(
                content=content, ttl_minutes=ttl_minutes, model_name=target_model
            )

            # Restore original key (or keep target_key if it was current)
            # self.current_key = original_key

            if cache_obj and hasattr(cache_obj, "name"):
                # Calculate expiration time locally (approximate)
                expire_time = datetime.now(timezone.utc) + timedelta(
                    minutes=ttl_minutes
                )

                if cache_key not in self._context_cache:
                    self._context_cache[cache_key] = {}

                self._context_cache[cache_key][key_hash] = {
                    "name": cache_obj.name,
                    "expire_time": expire_time.isoformat(),
                    "model": target_model,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self._save_context_cache()
                logger.info(
                    f"Created context cache for key {key_hash[:8]}: {cache_obj.name}"
                )
                return cache_obj.name

        except Exception as e:
            logger.warning(
                f"Failed to create context cache for key {key_hash[:8]}: {e}"
            )
            from ..utils.error_formatter import format_exception_for_logging

            logger.debug(
                format_exception_for_logging(e, context="Context Cache Creation")[
                    "full"
                ]
            )

        return None

    async def get_or_upload_file(
        self, file_path: str, api_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Get hoặc upload file lên Gemini và cache kết quả cho một API key cụ thể.

        Nếu file đã được upload trước đó (dựa trên hash), trả về cached file name.
        Nếu chưa, upload file mới và cache kết quả.

        Args:
            file_path: Đường dẫn file cần upload
            api_key: Optional API key.

        Returns:
            Gemini file name (usable với client.get_file()) hoặc None nếu thất bại
        """
        try:
            # Determine which key to use
            target_key = api_key or self.current_key
            if not target_key:
                if self.distributor:
                    target_key = await self.distributor.get_available_key()
                else:
                    target_key = self.key_manager.get_available_key()
                self.current_key = target_key

            key_hash = hashlib.md5(target_key.encode()).hexdigest()
            file_hash = self._hash_file(file_path)

            file_entry = self._files_cache.get(file_hash, {})
            cached = file_entry.get(key_hash)

            if cached:
                cached_name = cached.get("name")
                if cached_name:
                    logger.debug(
                        f"Using cached file for key {key_hash[:8]}: {cached_name}"
                    )
                    return cached_name

            # Get client với target API key
            self.current_key = target_key
            client = await self._get_client()

            # Upload file
            uploaded = client.upload_file(file_path)

            if hasattr(uploaded, "name"):
                if file_hash not in self._files_cache:
                    self._files_cache[file_hash] = {}

                self._files_cache[file_hash][key_hash] = {
                    "name": uploaded.name,
                    "path": str(Path(file_path).resolve()),
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                }
                self._save_files_cache()
                logger.info(f"Uploaded file for key {key_hash[:8]}: {uploaded.name}")
                return uploaded.name
            else:
                logger.warning("Uploaded file không có attribute 'name'")
                return None
        except Exception as e:
            logger.warning(f"Failed to upload file {file_path}: {e}")
            return None

    async def delete_context_cache(
        self, cache_name: str, api_key: Optional[str] = None
    ) -> bool:
        """
        Delete a context cache from Gemini and local registry.
        """
        try:
            target_key = api_key or self.current_key
            if not target_key:
                return False

            self.current_key = target_key
            client = self._get_client()

            success = client.delete_context_cache(cache_name)

            if success:
                # Remove from local registry
                # Need to find it in _context_cache
                keys_to_remove = []
                for content_hash, keys_dict in self._context_cache.items():
                    key_hash = hashlib.md5(target_key.encode()).hexdigest()
                    if (
                        key_hash in keys_dict
                        and keys_dict[key_hash].get("name") == cache_name
                    ):
                        del keys_dict[key_hash]
                        if not keys_dict:
                            keys_to_remove.append(content_hash)

                for k in keys_to_remove:
                    del self._context_cache[k]

                self._save_context_cache()
                logger.info(f"Deleted context cache: {cache_name}")

            return success
        except Exception as e:
            logger.warning(f"Error in delete_context_cache: {e}")
            return False

    async def count_tokens_async(
        self,
        contents: Union[str, List[Any]],
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> int:
        """
        Đếm số lượng tokens của nội dung.
        """
        try:
            target_key = api_key or self.current_key
            if not target_key:
                if self.distributor:
                    target_key = await self.distributor.get_available_key()
                else:
                    target_key = self.key_manager.get_available_key()

            # Temporary swap
            self.current_key = target_key
            client = await self._get_client()

            target_model = model_name or self.default_model
            tokens = await client.count_tokens_async(contents, target_model)

            # Restore
            # self.current_key = original_key

            return tokens
        except Exception as e:
            logger.warning(f"Error in count_tokens_async: {e}")
            return 0

    async def generate_content_with_files_async(
        self,
        prompt: str,
        file_names: List[str],
        model_name: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Generate content với attached files (by Gemini file names).

        Args:
            prompt: Prompt string
            file_names: List các Gemini file names đã upload
            model_name: Tên model (mặc định: "gemini-2.5-flash")
            response_mime_type: Optional response MIME type
            max_retries: Số lần retry tối đa (mặc định: 3)

        Returns:
            Generated text content

        Raises:
            ValueError: Nếu không có API key khả dụng
            Exception: Nếu tất cả attempts đều thất bại
        """
        for attempt in range(max_retries):
            try:
                self.current_key = self.key_manager.get_available_key()
                if not self.current_key:
                    raise ValueError("No available API keys")

                self.key_manager.add_delay_between_requests(self.current_key)

                # Get client
                client = self._get_client()

                # Build generation config
                gen_cfg = dict(self.model_config)
                if response_mime_type:
                    gen_cfg["response_mime_type"] = response_mime_type

                # Get files
                def _get_files() -> List[Any]:
                    files: List[Any] = []
                    for name in file_names or []:
                        try:
                            file_obj = client.get_file(name)
                            files.append(file_obj)
                        except Exception as e:
                            logger.warning(f"Failed to get file {name}: {e}")
                            continue
                    return files

                # Build parts: prompt + files
                files = await asyncio.get_event_loop().run_in_executor(None, _get_files)
                parts: List[Any] = [prompt] + files

                # Generate content
                # [PHASE 9] Use default model if not provided
                target_model = model_name or self.default_model
                response = await client.generate_content_async(
                    prompt=parts,
                    model_name=target_model,
                    safety_settings=self.safety_settings,
                    generation_config=gen_cfg,
                )

                extracted = self._extract_text(response) if response else None
                if extracted:
                    self.key_manager.mark_request_success(self.current_key)
                    return extracted
                else:
                    raise ValueError("Empty response from Gemini (files)")

            except Exception as e:
                error_msg = str(e)
                error_type_name = type(e).__name__
                error_type = self._detect_error_type(e, error_msg, error_type_name)

                logger.warning(
                    f"Attempt {attempt + 1} with files failed: {error_type} - {error_msg}",
                    exc_info=True,
                )
                if self.current_key:
                    await self.key_manager.mark_request_error(
                        self.current_key, error_type, error_msg
                    )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise Exception(
                        f"Failed with files after {max_retries} attempts: {error_msg}"
                    )

        raise ValueError("No available API keys after all attempts")

    async def generate_content_with_fallback(
        self,
        prompt: str,
        primary_model: str = "gemini-2.5-flash",
        fallback_model: str = "gemini-2.5-pro",
        response_mime_type: Optional[str] = None,
    ) -> str:
        """
        Generate content với fallback model nếu primary model fails.

        Args:
            prompt: Prompt string
            primary_model: Model chính để thử trước (mặc định: "gemini-2.5-flash")
            fallback_model: Model fallback nếu primary fails (mặc định: "gemini-2.5-pro")
            response_mime_type: Optional response MIME type

        Returns:
            Generated text content

        Raises:
            Exception: Nếu cả 2 models đều thất bại
        """
        try:
            return await self.generate_content_async(
                prompt, primary_model, response_mime_type=response_mime_type
            )
        except Exception as e:
            logger.warning(
                f"Primary model {primary_model} failed, trying fallback {fallback_model}: {e}"
            )
            try:
                return await self.generate_content_async(
                    prompt, fallback_model, response_mime_type=response_mime_type
                )
            except Exception as e2:
                logger.error(
                    f"Both models failed. Primary: {e}, Fallback: {e2}", exc_info=True
                )
                raise e2

    def get_api_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái API keys.

        Returns:
            Dictionary chứa status summary từ key_manager
        """
        return self.key_manager.get_status_summary()

    def get_quota_warning(self) -> Optional[str]:
        """
        Lấy cảnh báo quota nếu có.

        Returns:
            Warning message string hoặc None nếu không có cảnh báo
        """
        return self.key_manager.get_quota_warning()

    def reset_all_keys(self) -> None:
        """
        Reset tất cả API keys về trạng thái ban đầu.

        Returns:
            None
        """
        self.key_manager.reset_all_keys()

    def get_available_keys_count(self) -> int:
        """
        Lấy số lượng keys khả dụng.

        Returns:
            Số lượng active keys
        """
        return sum(
            1 for status in self.key_manager.key_statuses.values() if status.is_active
        )

    def is_quota_available(self) -> bool:
        """
        Kiểm tra xem còn quota không.

        Returns:
            True nếu còn ít nhất 1 active key, False nếu không
        """
        return self.get_available_keys_count() > 0

    async def test_api_keys(self) -> Dict[str, bool]:
        """
        Test tất cả API keys để kiểm tra tính khả dụng
        """
        test_prompt = "Test API key. Respond with 'OK' only."
        results = {}

        for key in self.api_keys:
            try:
                # Temporarily set current key
                original_key = self.current_key
                self.current_key = key

                # Test with a simple request
                response = await self.generate_content_async(test_prompt, max_retries=1)

                if response and "OK" in response:
                    results[key] = True
                    logger.info(f"API key test passed: {key[:10]}...")
                else:
                    results[key] = False
                    logger.warning(
                        f"API key test failed (invalid response): {key[:10]}..."
                    )

                # Restore original key
                self.current_key = original_key

            except Exception as e:
                results[key] = False
                logger.warning(f"API key test failed: {key[:10]}... - {e}")

        return results

    def get_usage_recommendations(self) -> List[str]:
        """
        Lấy khuyến nghị sử dụng dựa trên trạng thái hiện tại
        """
        recommendations = []
        status = self.get_api_status()

        # Check quota usage
        quota_percent = status.get("quota_usage_percent", 0)
        if quota_percent >= 90:
            recommendations.append(
                "⚠️ Quota usage critical - consider reducing request frequency"
            )
        elif quota_percent >= 75:
            recommendations.append("⚠️ Quota usage high - monitor usage closely")

        # Check active keys
        active_keys = status.get("active_keys", 0)
        total_keys = status.get("total_keys", 0)

        if active_keys < total_keys * 0.5:
            recommendations.append("⚠️ Many API keys are inactive - check key validity")

        if active_keys == 0:
            recommendations.append("❌ No active API keys - check configuration")

        # Check error rate
        total_requests = status.get("total_requests", 0)
        total_errors = status.get("total_errors", 0)

        if total_requests > 0:
            error_rate = (total_errors / total_requests) * 100
            if error_rate > 20:
                recommendations.append(
                    "⚠️ High error rate - check API key validity and rate limits"
                )

        return recommendations
