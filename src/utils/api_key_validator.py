# -*- coding: utf-8 -*-

"""
Module xác thực API key cho Google Gemini API.

Các chức năng chính:
- Kiểm tra tính hợp lệ của API keys
- Đo response time của mỗi key
- Phân loại keys thành valid/invalid
- Sử dụng 'gemini-2.5-flash' để đảm bảo tương thích với ứng dụng chính
"""

import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.logger import suppress_grpc_logging

from ..services.genai_adapter import create_client

logger = logging.getLogger("NovelTranslator")


@dataclass
class APIKeyStatus:
    """
    Data class để lưu trữ trạng thái của một API key sau khi kiểm tra.

    Attributes:
        key_masked: API key đã được mask (chỉ hiển thị 8 ký tự đầu và 4 ký tự cuối)
        full_key: API key đầy đủ (không nên log hoặc expose)
        is_valid: True nếu key hợp lệ, False nếu không
        response_time: Thời gian phản hồi tính bằng giây (None nếu key không hợp lệ)
        error_message: Thông báo lỗi nếu key không hợp lệ (None nếu key hợp lệ)
        tested_at: Timestamp khi key được kiểm tra (ISO format)
        account_type: Loại tài khoản: "free_tier", "paid_tier_required", "restricted", "unknown"
    """

    key_masked: str
    full_key: str
    is_valid: bool
    response_time: Optional[float]
    error_message: Optional[str]
    tested_at: str
    account_type: str = "unknown"  # free_tier, paid_tier_required, restricted, unknown

    def to_dict(self, hide_full_key: bool = True) -> Dict[str, Any]:
        """
        Chuyển đổi đối tượng sang dictionary.

        Args:
            hide_full_key: Nếu True, loại bỏ 'full_key' khỏi dictionary (mặc định: True)

        Returns:
            Dictionary chứa các thuộc tính của APIKeyStatus

        Example:
            >>> status = APIKeyStatus(...)
            >>> data = status.to_dict(hide_full_key=True)
            >>> # 'full_key' sẽ không có trong data
        """
        data = asdict(self)
        if hide_full_key:
            data.pop("full_key", None)
        return data


class GeminiAPIChecker:
    """
    Lớp thực hiện việc kiểm tra API key của Google Gemini một cách tuần tự.

    Tập trung vào độ tin cậy và tuân thủ giới hạn tần suất.
    Sử dụng 'gemini-2.5-flash' để kiểm tra tương thích với ứng dụng chính.
    """

    def __init__(
        self, api_keys: List[str], config: Dict[str, Any], use_new_sdk: bool = True
    ) -> None:
        """
        Khởi tạo checker.

        Args:
            api_keys: Danh sách các API key cần kiểm tra
            config: Dictionary chứa cấu hình chính của ứng dụng
            use_new_sdk: True để dùng SDK mới, False để dùng SDK cũ

        Note:
            Tự động lọc bỏ các key rỗng hoặc placeholder ("YOUR_GOOGLE_API_KEY").
        """
        self.api_keys: List[str] = [
            key for key in api_keys if key and "YOUR_GOOGLE_API_KEY" not in key
        ]
        # [STRICT UPDATE] Prompt Level 7 (~150 từ) - Đã verify thực tế với toàn bộ 11 keys.
        # Đây là ngưỡng tối thiểu để Google API chặn tất cả các key đã hết quota (bao gồm cả soft limit).
        self.test_prompt: str = (
            "Translate: The sun rises in the east and sets in the west every single day. Nature's rhythm is consistent, "
            "providing light and warmth to all living creatures on Earth. This cycle has continued for billions of years, "
            "sustaining life and driving weather patterns across the globe, influencing agriculture, migration, and human activities "
            "throughout history and into the future. Artificial intelligence is transforming the world. Machine learning algorithms "
            "optimize processes and create new opportunities for innovation across various industries. The integration of AI into daily life "
            "is accelerating. From smart assistants at home to autonomous vehicles on the roads, technology is reshaping how we live and work. "
            "Ethical considerations regarding data privacy and algorithmic bias are becoming increasingly important topics of global discussion. "
            "Governments and organizations are establishing regulatory frameworks to ensure responsible development and deployment involving rigorous testing and transparency."
        )
        self.suppress_logs: bool = config.get("performance", {}).get(
            "suppress_native_logs", True
        )
        self.delay_between_checks: float = (
            2.0  # 2 giây nghỉ để tránh rate limit (tăng từ 1s → 2s)
        )
        self.use_new_sdk: bool = use_new_sdk

        # [PHASE 9] Centralized Model Config
        self.validator_model: str = config.get("models", {}).get(
            "validator", "gemini-2.5-flash"
        )

    def _mask_key(self, key: str) -> str:
        """
        Che giấu API key để bảo mật, chỉ hiển thị 8 ký tự đầu và 4 ký tự cuối.

        Args:
            key: API key cần mask

        Returns:
            API key đã được mask (ví dụ: "AIzaSyAF...wVE")

        Example:
            >>> checker = GeminiAPIChecker([], {})
            >>> masked = checker._mask_key("TEST_GEMINI_API_KEY_EXAMPLE_1234567890")
            >>> print(masked)
            "TEST_GEM...7890"
        """
        if len(key) <= 12:
            return key
        return key[:8] + "..." + key[-4:]

    def _check_single_key(
        self, api_key: str, key_manager: Optional[Any] = None
    ) -> APIKeyStatus:
        """
        Thực hiện kiểm tra một API key bằng cách gọi API thực tế.

        Đây là cách chính xác nhất để xác định một key có hoạt động hay không.
        Sử dụng 'gemini-2.5-flash' với prompt đơn giản để kiểm tra.

        Args:
            api_key: API key cần kiểm tra

        Returns:
            APIKeyStatus object chứa kết quả kiểm tra (valid/invalid, response_time, error_message)

        Note:
            - Đo response time của API call
            - Phân loại lỗi thành các loại: Invalid Key, Model Not Found, Rate Limit, etc.
            - Luôn trả về APIKeyStatus, không raise exception
        """
        masked_key = self._mask_key(api_key)
        start_time = time.time()

        # OPTIMIZATION: Check quota trước khi test (nếu có key_manager)
        if key_manager:
            if not key_manager._is_key_available(api_key):
                status = key_manager.key_statuses.get(api_key)
                if status:
                    quota_remaining = status.daily_quota_limit - status.daily_quota_used
                    return APIKeyStatus(
                        key_masked=masked_key,
                        full_key=api_key,
                        is_valid=False,
                        response_time=None,
                        error_message=f"Quota exceeded or rate limited (quota: {status.daily_quota_used}/{status.daily_quota_limit}, remaining: {quota_remaining})",
                        tested_at=datetime.now().isoformat(),
                        account_type="free_tier",  # Có free tier nhưng quota hết
                    )

        with (
            suppress_grpc_logging()
            if self.suppress_logs
            else open(os.devnull, "w", encoding="utf-8")
        ):
            try:
                # Sử dụng adapter để tạo client với timeout an toàn cho validation (30s)
                client = create_client(
                    api_key=api_key, use_new_sdk=self.use_new_sdk, timeout=30
                )

                # Sử dụng model từ config để kiểm tra
                # Điều này đảm bảo key tương thích với model được cấu hình
                response = client.generate_content(
                    prompt=self.test_prompt, model_name=self.validator_model
                )

                if not response or not hasattr(response, "text") or not response.text:
                    raise ValueError("Phản hồi trống hoặc không hợp lệ từ API.")

                response_time = time.time() - start_time

                # OPTIMIZATION: Track quota usage sau khi test thành công
                if key_manager:
                    key_manager.mark_request_success(api_key)

                # Nếu API call thành công → có free tier (hoặc paid tier đã có billing)
                # Không thể phân biệt chính xác, nhưng nếu không có billing error → free tier
                account_type = "free_tier"  # Mặc định là free tier nếu hoạt động

                return APIKeyStatus(
                    key_masked=masked_key,
                    full_key=api_key,
                    is_valid=True,
                    response_time=round(response_time, 3),
                    error_message=None,
                    tested_at=datetime.now().isoformat(),
                    account_type=account_type,
                )
            except Exception as e:
                error_msg = str(e)
                error_type = "Unknown Error"
                account_type = "unknown"

                # Phân loại lỗi dựa trên error message và detect account type
                error_msg_lower = error_msg.lower()

                if (
                    "API_KEY_INVALID" in error_msg
                    or "PERMISSION_DENIED" in error_msg.upper()
                    or "permission" in error_msg.lower()
                ):
                    error_type = "Invalid API Key or Permission Denied"
                    # Check if it's restricted account
                    if (
                        "access denied" in error_msg_lower
                        or "region" in error_msg_lower
                        or "not available" in error_msg_lower
                    ):
                        account_type = "restricted"
                elif (
                    "NOT_FOUND" in error_msg.upper()
                    or "model" in error_msg.lower()
                    and "not found" in error_msg.lower()
                ):
                    error_type = "Model Not Found / API Version Mismatch"
                elif (
                    "429" in error_msg
                    or "RESOURCE_EXHAUSTED" in error_msg.upper()
                    or "quota" in error_msg.lower()
                    or "rate limit" in error_msg.lower()
                ):
                    error_type = "Quota Exceeded or Rate Limit"
                    # Quota error có thể là free tier (quota hết) hoặc paid tier (chưa có billing)
                    # Nếu có "billing" trong error → paid_tier_required
                    if "billing" in error_msg_lower or "payment" in error_msg_lower:
                        account_type = "paid_tier_required"
                    else:
                        # Quota hết nhưng không có billing error → có thể là free tier (quota đã dùng hết)
                        account_type = "free_tier"  # Có free tier nhưng quota hết
                elif (
                    "billing" in error_msg_lower
                    or "payment" in error_msg_lower
                    or "requires billing" in error_msg_lower
                ):
                    error_type = "Billing Account Required"
                    account_type = "paid_tier_required"

                return APIKeyStatus(
                    key_masked=masked_key,
                    full_key=api_key,
                    is_valid=False,
                    response_time=None,
                    error_message=f"{error_type}: {error_msg[:200]}",
                    tested_at=datetime.now().isoformat(),
                    account_type=account_type,
                )

    def run_checks(self) -> List[APIKeyStatus]:
        """
        Chạy kiểm tra tuần tự cho tất cả các API key.

        Kiểm tra từng key một cách tuần tự với delay giữa các lần kiểm tra
        để tránh rate limit.

        Returns:
            List các APIKeyStatus objects, mỗi object chứa kết quả kiểm tra một key

        Note:
            - Delay giữa các lần kiểm tra: `delay_between_checks` giây
            - Không delay sau key cuối cùng
        """
        results: List[APIKeyStatus] = []
        total_keys = len(self.api_keys)
        logger.info(f"Bắt đầu kiểm tra tuần tự {total_keys} API key...")

        for index, key in enumerate(self.api_keys):
            logger.info(
                f"Đang kiểm tra key {index + 1}/{total_keys} (key: {self._mask_key(key)})..."
            )
            result = self._check_single_key(key)
            results.append(result)

            # Delay giữa các lần kiểm tra (trừ key cuối cùng)
            if index < total_keys - 1:
                time.sleep(self.delay_between_checks)

        return results


def validate_api_keys(
    api_keys: List[str], config: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Hàm helper để khởi tạo và chạy GeminiAPIChecker, sau đó báo cáo kết quả.

    Args:
        api_keys: Danh sách các API key cần kiểm tra
        config: Dictionary chứa cấu hình chính của ứng dụng

    Returns:
        Dictionary chứa:
            - 'valid_keys': List các API key hợp lệ
            - 'invalid_keys': List các API key không hợp lệ
            - 'free_tier_keys': List các API key có free tier
            - 'paid_tier_keys': List các API key cần billing
            - 'restricted_keys': List các API key bị giới hạn

    Example:
        >>> config = {'performance': {'suppress_native_logs': True}}
        >>> result = validate_api_keys(['key1', 'key2'], config)
        >>> print(result['free_tier_keys'])
        ['key1', 'key2']
    """
    if not api_keys:
        logger.warning("Không có API key nào để kiểm tra")
        return {
            "valid_keys": [],
            "invalid_keys": [],
            "free_tier_keys": [],
            "paid_tier_keys": [],
            "restricted_keys": [],
        }

    checker = GeminiAPIChecker(api_keys, config)
    results = checker.run_checks()

    valid_keys: List[str] = []
    invalid_keys: List[str] = []
    free_tier_keys: List[str] = []
    paid_tier_keys: List[str] = []
    restricted_keys: List[str] = []

    logger.info("--- BÁO CÁO KIỂM TRA API KEY ---")
    for result in sorted(results, key=lambda r: not r.is_valid):
        if result.is_valid:
            logger.info(
                f"  [✓] Key {result.key_masked}: Hợp lệ - "
                f"Thời gian phản hồi: {result.response_time}s - "
                f"Loại: {result.account_type}"
            )
            valid_keys.append(result.full_key)

            # Phân loại theo account type
            if result.account_type == "free_tier":
                free_tier_keys.append(result.full_key)
            elif result.account_type == "paid_tier_required":
                paid_tier_keys.append(result.full_key)
            elif result.account_type == "restricted":
                restricted_keys.append(result.full_key)
        else:
            logger.warning(
                f"  [✗] Key {result.key_masked}: KHÔNG HỢP LỆ - "
                f"{result.error_message} - Loại: {result.account_type}"
            )
            invalid_keys.append(result.full_key)

            # Phân loại theo account type (ngay cả khi invalid)
            if result.account_type == "free_tier":
                free_tier_keys.append(
                    result.full_key
                )  # Có thể là free tier nhưng quota hết
            elif result.account_type == "paid_tier_required":
                paid_tier_keys.append(result.full_key)
            elif result.account_type == "restricted":
                restricted_keys.append(result.full_key)

    logger.info("---------------------------------")
    logger.info("Tổng kết:")
    logger.info(f"  - Hợp lệ: {len(valid_keys)} keys")
    logger.info(f"  - Không hợp lệ: {len(invalid_keys)} keys")
    logger.info(f"  - Free tier: {len(free_tier_keys)} keys")
    logger.info(f"  - Cần billing: {len(paid_tier_keys)} keys")
    logger.info(f"  - Bị giới hạn: {len(restricted_keys)} keys")

    return {
        "valid_keys": valid_keys,
        "invalid_keys": invalid_keys,
        "free_tier_keys": free_tier_keys,
        "paid_tier_keys": paid_tier_keys,
        "restricted_keys": restricted_keys,
    }
