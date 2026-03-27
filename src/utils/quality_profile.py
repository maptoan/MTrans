# -*- coding: utf-8 -*-
"""
Phase 13 – Quality profile: overlay cấu hình theo profile (fast_low_cost, balanced_default, max_quality).

Không thay đổi logic pipeline; chỉ ghi đè các key trong config khi khởi tạo.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Optional

# Định nghĩa overlay cho từng profile (chỉ các key cần override)
PROFILE_OVERLAYS: Dict[str, Dict[str, Any]] = {
    "fast_low_cost": {
        "translation": {
            "qa_editor": {
                "min_word_overlap_ratio": 0.35,
                "max_batch_size": 50,
            },
            "enable_final_cleanup_pass": False,
            "collect_residuals": False,
        },
    },
    "balanced_default": {
        "translation": {
            "qa_editor": {
                "min_word_overlap_ratio": 0.5,
                "max_batch_size": 30,
            },
            "enable_final_cleanup_pass": True,
            "collect_residuals": True,
        },
    },
    "max_quality": {
        "translation": {
            "qa_editor": {
                "min_word_overlap_ratio": 0.7,
                "max_batch_size": 20,
            },
            "enable_final_cleanup_pass": True,
            "collect_residuals": True,
            "residual_retry": {
                "max_global_retries_per_sentence": 5,
            },
        },
    },
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Gộp overlay vào base (đệ quy). overlay ghi đè base; base giữ nguyên key không có trong overlay."""
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def apply_quality_profile(
    config: Dict[str, Any],
    profile_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Áp dụng profile chất lượng lên config (không sửa config gốc).

    Args:
        config: Cấu hình gốc (sẽ được copy và merge).
        profile_name: Tên profile ("fast_low_cost" | "balanced_default" | "max_quality").
                     Nếu None, lấy từ config["quality_profile"]["name"]; nếu thiếu hoặc không hợp lệ → "balanced_default".

    Returns:
        Config mới đã merge overlay của profile.
    """
    if profile_name is None:
        profile_name = (config.get("quality_profile") or {}).get("name") or "balanced_default"
    if not isinstance(profile_name, str):
        profile_name = "balanced_default"
    profile_name = profile_name.strip().lower()
    if profile_name not in PROFILE_OVERLAYS:
        profile_name = "balanced_default"

    overlay = PROFILE_OVERLAYS[profile_name]
    return _deep_merge(config, overlay)
