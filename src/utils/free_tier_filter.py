# -*- coding: utf-8 -*-

"""
Free Tier Filter - Lọc tự động các API key có free tier.

Tính năng:
- Tự động detect và phân loại API keys theo account type
- Lọc và chỉ sử dụng keys có free tier
- Báo cáo chi tiết về các loại keys
"""

import logging
from typing import Any, Dict, List

from .api_key_validator import GeminiAPIChecker, validate_api_keys

logger = logging.getLogger("NovelTranslator")


def filter_free_tier_keys(
    api_keys: List[str], config: Dict[str, Any], auto_filter: bool = True
) -> Dict[str, Any]:
    """
    Lọc tự động các API key có free tier.

    Args:
        api_keys: Danh sách các API key cần kiểm tra
        config: Configuration dictionary
        auto_filter: Nếu True, chỉ trả về free tier keys. Nếu False, trả về tất cả với phân loại

    Returns:
        Dictionary chứa:
            - 'free_tier_keys': List các API key có free tier (valid)
            - 'all_keys': Dictionary với phân loại đầy đủ
            - 'summary': Thống kê về các loại keys
    """
    if not api_keys:
        logger.warning("Không có API key nào để lọc")
        return {
            "free_tier_keys": [],
            "all_keys": {
                "free_tier_keys": [],
                "paid_tier_keys": [],
                "restricted_keys": [],
                "unknown_keys": [],
            },
            "summary": {
                "total": 0,
                "free_tier": 0,
                "paid_tier": 0,
                "restricted": 0,
                "unknown": 0,
            },
        }

    logger.info(f"🔍 Bắt đầu lọc {len(api_keys)} API keys để tìm free tier keys...")

    # Validate và phân loại keys
    validation_result = validate_api_keys(api_keys, config)

    # Lọc chỉ lấy free tier keys (valid và có account_type = "free_tier")
    checker = GeminiAPIChecker(api_keys, config)
    results = checker.run_checks()

    free_tier_valid_keys: List[str] = []
    free_tier_invalid_keys: List[str] = []  # Có thể là free tier nhưng quota hết

    for result in results:
        if result.account_type == "free_tier":
            if result.is_valid:
                free_tier_valid_keys.append(result.full_key)
            else:
                # Có thể là free tier nhưng quota hết hoặc rate limit
                if "quota" in (result.error_message or "").lower() or "429" in (
                    result.error_message or ""
                ):
                    free_tier_invalid_keys.append(result.full_key)
                    logger.debug(
                        f"Key {result.key_masked} có free tier nhưng quota hết: {result.error_message}"
                    )

    # Tổng hợp kết quả
    all_keys = {
        "free_tier_keys": validation_result.get("free_tier_keys", []),
        "paid_tier_keys": validation_result.get("paid_tier_keys", []),
        "restricted_keys": validation_result.get("restricted_keys", []),
        "unknown_keys": [
            key
            for key in api_keys
            if key not in validation_result.get("free_tier_keys", [])
            and key not in validation_result.get("paid_tier_keys", [])
            and key not in validation_result.get("restricted_keys", [])
        ],
    }

    summary = {
        "total": len(api_keys),
        "free_tier": len(all_keys["free_tier_keys"]),
        "paid_tier": len(all_keys["paid_tier_keys"]),
        "restricted": len(all_keys["restricted_keys"]),
        "unknown": len(all_keys["unknown_keys"]),
        "free_tier_valid": len(free_tier_valid_keys),
        "free_tier_invalid": len(free_tier_invalid_keys),
    }

    # Log kết quả
    logger.info("=" * 60)
    logger.info("📊 KẾT QUẢ LỌC FREE TIER KEYS:")
    logger.info(f"  ✅ Free tier (valid): {summary['free_tier_valid']} keys")
    if summary["free_tier_invalid"] > 0:
        logger.info(f"  ⚠️  Free tier (quota hết): {summary['free_tier_invalid']} keys")
    logger.info(f"  💳 Cần billing: {summary['paid_tier']} keys")
    logger.info(f"  🚫 Bị giới hạn: {summary['restricted']} keys")
    logger.info(f"  ❓ Không xác định: {summary['unknown']} keys")
    logger.info("=" * 60)

    # Trả về kết quả
    if auto_filter:
        # Chỉ trả về free tier keys (valid)
        return {
            "free_tier_keys": free_tier_valid_keys,
            "all_keys": all_keys,
            "summary": summary,
        }
    else:
        # Trả về tất cả với phân loại
        return {
            "free_tier_keys": free_tier_valid_keys,
            "all_keys": all_keys,
            "summary": summary,
            "validation_result": validation_result,
        }


def get_free_tier_keys_only(api_keys: List[str], config: Dict[str, Any]) -> List[str]:
    """
    Helper function để chỉ lấy danh sách free tier keys (valid).

    Args:
        api_keys: Danh sách các API key
        config: Configuration dictionary

    Returns:
        List các API key có free tier và valid
    """
    result = filter_free_tier_keys(api_keys, config, auto_filter=True)
    return result["free_tier_keys"]
