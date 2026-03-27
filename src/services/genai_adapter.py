# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Adapter layer để hỗ trợ migration từ google-generativeai sang google-genai.

Module này cung cấp unified interface để code hiện tại có thể hoạt động với cả 2 SDKs,
giúp migration an toàn và dễ dàng rollback nếu cần.

Các chức năng chính:
- Unified client initialization
- Unified generate_content (sync & async)
- Unified file operations (upload/get)
- Safety settings conversion
- Response object wrapping để tương thích
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("NovelTranslator")
DEFAULT_TIMEOUT = 600  # 10 minutes timeout for large chunks

# Try import new SDK first
try:
    from google import genai as new_genai

    NEW_SDK_AVAILABLE = True
except ImportError:
    NEW_SDK_AVAILABLE = False
    new_genai = None
    logger.warning("Google GenAI SDK (new) không khả dụng. Sẽ dùng SDK cũ nếu có.")

# Fallback to old SDK
try:
    import google.generativeai as old_genai
    from google.generativeai.types import HarmBlockThreshold, HarmCategory

    OLD_SDK_AVAILABLE = True
except ImportError:
    OLD_SDK_AVAILABLE = False
    old_genai = None
    HarmCategory = None
    HarmBlockThreshold = None
    logger.warning("google-generativeai SDK (old) không khả dụng.")


class GenAIClient:
    """
    Unified client interface cho cả 2 SDKs (google-genai và google-generativeai).
    """

    def __init__(self, api_key: str, use_new_sdk: bool = True, timeout: Optional[float] = None) -> None:
        """
        Khởi tạo GenAI Client với unified interface.
        """
        # [v7.6] CRITICAL: Strict API Key validation
        if not api_key:
            logger.error("GenAIClient received empty/None api_key.")
            raise ValueError("API Key is required to initialize GenAIClient.")

        # Ensure api_key is a string, not a coroutine
        if asyncio.iscoroutine(api_key):
            # This is a critical error - __init__ cannot be async.
            # The caller MUST await the key first.
            logger.critical(
                f"CRITICAL: api_key passed to GenAIClient is a coroutine (unawaited). Type: {type(api_key)}"
            )
            raise TypeError("api_key cannot be a coroutine. Please await it first.")

        if not isinstance(api_key, str) and api_key is not None:
            # Try to convert to string, but log a warning
            logger.debug(f"Converting api_key of type {type(api_key)} to string")
            api_key = str(api_key)

        # Strip whitespace from api_key
        if isinstance(api_key, str):
            api_key = api_key.strip()

        self.api_key: str = api_key
        self.client: Optional[Any] = None  # Ensure initialized safely
        self.use_new_sdk: bool = use_new_sdk and NEW_SDK_AVAILABLE

        if self.use_new_sdk:
            try:
                # CRITICAL FIX: Do NOT pass timeout in http_options - it breaks async calls!
                # The SDK has internal timeout handling that works correctly.
                # Passing http_options={"timeout": X} causes immediate TimeoutError.
                # See: scripts/debug_new_sdk.py for verification
                self.client = new_genai.Client(api_key=api_key)
                logger.debug("Using Google GenAI SDK (new) - default timeout")
            except Exception as e:
                logger.error(f"Failed to initialize new SDK: {e}")
                self.use_new_sdk = False
                self.client = None

    def generate_content(
        self,
        prompt: Union[str, List],
        model_name: str = "gemini-2.5-flash",
        safety_settings: Optional[List[Dict[str, Any]]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Sync version of generate_content.
        """
        if self.use_new_sdk:
            if self.client is None:
                self.use_new_sdk = False
                if OLD_SDK_AVAILABLE:
                    old_genai.configure(api_key=self.api_key)
                else:
                    raise RuntimeError("New SDK failed and old SDK is not available.")

            config_dict = dict(generation_config) if generation_config else {}
            cached_content = config_dict.pop("cached_content", None)

            final_config = config_dict if config_dict else {}
            if cached_content:
                final_config["cached_content"] = cached_content

            # CRITICAL FIX: Pass safety_settings to new SDK config
            if safety_settings:
                final_config["safety_settings"] = safety_settings

            try:
                # Wrap prompt if string to ensure compatibility
                request_contents = prompt
                if isinstance(prompt, str):
                    request_contents = [
                        new_genai.types.Content(
                            role="user",
                            parts=[new_genai.types.Part.from_text(text=prompt)],
                        )
                    ]

                response = self.client.models.generate_content(
                    model=model_name, contents=request_contents, config=final_config
                )
                return self._wrap_new_response(response)
            except Exception as e:
                raise e

        else:
            # Old SDK fallback
            if not OLD_SDK_AVAILABLE:
                raise RuntimeError("New SDK failed and old SDK is not available.")
            old_genai.configure(api_key=self.api_key)
            model = old_genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
            return model.generate_content(prompt)

    async def generate_content_async(
        self,
        prompt: Union[str, List],
        model_name: str = "gemini-2.5-flash",
        safety_settings: Optional[List[Dict[str, Any]]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        # Handle cases where 'model' is passed instead of 'model_name'
        if "model" in kwargs and not model_name:
            model_name = kwargs.pop("model")
        elif "model" in kwargs:
            kwargs.pop("model")

        if self.use_new_sdk:
            if self.client is None:
                self.use_new_sdk = False
                if OLD_SDK_AVAILABLE:
                    old_genai.configure(api_key=self.api_key)
                else:
                    raise RuntimeError("New SDK failed and old SDK is not available.")

            config_dict = dict(generation_config) if generation_config else {}
            cached_content = config_dict.pop("cached_content", None)

            final_config = config_dict if config_dict else {}
            if cached_content:
                final_config["cached_content"] = cached_content

            # CRITICAL FIX: Pass safety_settings to new SDK config
            if safety_settings:
                # New SDK expects safety_settings in the config dictionary
                final_config["safety_settings"] = safety_settings

            try:
                response = await self.client.aio.models.generate_content(
                    model=model_name, contents=prompt, config=final_config
                )
                return self._wrap_new_response(response)
            except Exception as e:
                # Log detailed error for debugging
                logger.error(f"GenAI API Error [{model_name}]: {type(e).__name__}: {str(e)[:200]}")
                raise
        else:
            if not OLD_SDK_AVAILABLE:
                raise RuntimeError("New SDK failed and old SDK is not available.")
            old_genai.configure(api_key=self.api_key)
            model = old_genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
            if hasattr(model, "generate_content_async"):
                return await model.generate_content_async(prompt)
            else:
                return await asyncio.get_event_loop().run_in_executor(None, lambda: model.generate_content(prompt))

    async def batch_generate_content_async(
        self,
        prompts: List[Union[str, List]],
        model_name: str = "gemini-2.1-flash",
        **kwargs,
    ) -> List[Any]:
        tasks = [self.generate_content_async(p, model_name=model_name, **kwargs) for p in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def upload_file(self, file_path: str) -> Any:
        if self.use_new_sdk:
            return self.client.files.upload(path=file_path)
        else:
            return old_genai.upload_file(file_path)

    async def upload_file_async(self, file_path: str) -> Any:
        if self.use_new_sdk and hasattr(self.client.files, "upload_async"):
            return await self.client.files.upload_async(path=file_path)
        return await asyncio.get_event_loop().run_in_executor(None, lambda: self.upload_file(file_path))

    def delete_file(self, file_name: str) -> bool:
        try:
            if self.use_new_sdk:
                self.client.files.delete(name=file_name)
            else:
                old_genai.delete_file(file_name)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete file {file_name}: {e}")
            return False

    async def delete_file_async(self, file_name: str) -> bool:
        if self.use_new_sdk and hasattr(self.client.files, "delete_async"):
            try:
                await self.client.files.delete_async(name=file_name)
                return True
            except Exception as e:
                logger.warning(f"Failed to delete file async {file_name}: {e}")
                return False
        return await asyncio.get_event_loop().run_in_executor(None, lambda: self.delete_file(file_name))

    def get_file(self, file_name: str) -> Any:
        if self.use_new_sdk:
            return self.client.files.get(name=file_name)
        else:
            return old_genai.get_file(file_name)

    def create_context_cache(
        self,
        content: str,
        ttl_minutes: int = 60,
        model_name: str = "gemini-2.5-flash",
        system_instruction: Optional[str] = None,
    ) -> Any:
        """
        Create context cache following official SDK documentation.
        """
        if self.use_new_sdk:
            try:
                ttl_str = f"{ttl_minutes * 60}s"
                cache_config = {
                    "contents": [{"role": "user", "parts": [{"text": content}]}],
                    "ttl": ttl_str,
                }
                if system_instruction:
                    cache_config["system_instruction"] = system_instruction

                return self.client.caches.create(model=model_name, config=cache_config)
            except Exception as e:
                logger.warning(f"Failed to create context cache: {e}")
                return None
        return None

    def delete_context_cache(self, cache_name: str) -> bool:
        try:
            if self.use_new_sdk:
                self.client.caches.delete(name=cache_name)
            else:
                from google.generativeai import caching

                caching.CachedContent.delete(cache_name)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete context cache {cache_name}: {e}")
            return False

    async def delete_context_cache_async(self, cache_name: str) -> bool:
        if self.use_new_sdk and hasattr(self.client.caches, "delete_async"):
            try:
                await self.client.caches.delete_async(name=cache_name)
                return True
            except Exception as e:
                logger.warning(f"Failed to delete cache async {cache_name}: {e}")
                return False
        return await asyncio.get_event_loop().run_in_executor(None, lambda: self.delete_context_cache(cache_name))

    async def count_tokens_async(self, contents: Union[str, List[Any]], model_name: str = "gemini-2.5-flash") -> int:
        if self.use_new_sdk:
            try:
                response = await self.client.aio.models.count_tokens(model=model_name, contents=contents)
                return response.total_tokens
            except Exception as e:
                logger.warning(f"Failed to count tokens async: {e}")
                return 0
        else:
            try:
                model = old_genai.GenerativeModel(model_name)
                response = await model.count_tokens_async(contents)
                return response.total_tokens
            except Exception:
                return 0

    def _wrap_new_response(self, response: Any) -> Any:
        return response

    async def aclose(self) -> None:
        if getattr(self, "use_new_sdk", False) and getattr(self, "client", None):
            try:
                if hasattr(self.client, "aclose"):
                    await self.client.aclose()
                elif hasattr(self.client, "close"):
                    await asyncio.get_event_loop().run_in_executor(None, self.client.close)
            except (AttributeError, Exception) as e:
                # Catching AttributeError specifically handles the SDK internal bug
                logger.debug(f"Safe cleanup: Suppressed error during client.aclose(): {e}")
            finally:
                self.client = None

    def close(self) -> None:
        # getattr: __init__ có thể raise trước khi gán use_new_sdk
        if getattr(self, "use_new_sdk", False) and getattr(self, "client", None):
            try:
                if hasattr(self.client, "close"):
                    self.client.close()
            except Exception:
                pass
            finally:
                self.client = None

    def __del__(self) -> None:
        self.close()


def create_client(api_key: str, use_new_sdk: bool = True, timeout: Optional[float] = DEFAULT_TIMEOUT) -> GenAIClient:
    return GenAIClient(api_key=api_key, use_new_sdk=use_new_sdk, timeout=timeout)


GenAIAdapter = GenAIClient
