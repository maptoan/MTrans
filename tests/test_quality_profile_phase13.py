# -*- coding: utf-8 -*-
"""
Phase 13 – Quality profile: test apply_quality_profile overlay.
TDD: Test viết trước; implementation trong src.utils.quality_profile.
"""
from __future__ import annotations

import copy
from typing import Any, Dict

import pytest

from src.utils.quality_profile import apply_quality_profile

# Base config mẫu (có thể khác với balanced_default)
BASE: Dict[str, Any] = {
    "translation": {
        "qa_editor": {
            "min_word_overlap_ratio": 0.5,
            "max_batch_size": 30,
        },
        "enable_final_cleanup_pass": True,
        "collect_residuals": True,
        "residual_retry": {"max_global_retries_per_sentence": 3},
    },
}


def test_fast_low_cost_overrides() -> None:
    """Profile fast_low_cost phải override: overlap thấp, batch lớn, tắt cleanup/residuals."""
    config = apply_quality_profile(copy.deepcopy(BASE), "fast_low_cost")
    qa = config.get("translation", {}).get("qa_editor", {})
    assert qa.get("min_word_overlap_ratio") == 0.35
    assert qa.get("max_batch_size") == 50
    assert config.get("translation", {}).get("enable_final_cleanup_pass") is False
    assert config.get("translation", {}).get("collect_residuals") is False


def test_max_quality_overrides() -> None:
    """Profile max_quality phải override: overlap cao, batch nhỏ, retry cao."""
    config = apply_quality_profile(copy.deepcopy(BASE), "max_quality")
    qa = config.get("translation", {}).get("qa_editor", {})
    assert qa.get("min_word_overlap_ratio") == 0.7
    assert qa.get("max_batch_size") == 20
    assert config.get("translation", {}).get("enable_final_cleanup_pass") is True
    residual = config.get("translation", {}).get("residual_retry", {})
    assert residual.get("max_global_retries_per_sentence") == 5


def test_balanced_default_overrides() -> None:
    """Profile balanced_default giữ giá trị cân bằng (0.5, 30, bật cleanup/residuals)."""
    config = apply_quality_profile(copy.deepcopy(BASE), "balanced_default")
    qa = config.get("translation", {}).get("qa_editor", {})
    assert qa.get("min_word_overlap_ratio") == 0.5
    assert qa.get("max_batch_size") == 30
    assert config.get("translation", {}).get("enable_final_cleanup_pass") is True
    assert config.get("translation", {}).get("collect_residuals") is True


def test_unknown_profile_falls_back_to_balanced() -> None:
    """Profile không tồn tại hoặc rỗng → áp dụng balanced_default."""
    config1 = apply_quality_profile(copy.deepcopy(BASE), "unknown_profile")
    config2 = apply_quality_profile(copy.deepcopy(BASE), "")
    config3 = apply_quality_profile(copy.deepcopy(BASE), None)
    for c in (config1, config2, config3):
        assert c.get("translation", {}).get("qa_editor", {}).get("min_word_overlap_ratio") == 0.5
        assert c.get("translation", {}).get("qa_editor", {}).get("max_batch_size") == 30


def test_apply_quality_profile_does_not_mutate_input() -> None:
    """apply_quality_profile không sửa config gốc (merge vào bản copy)."""
    original = copy.deepcopy(BASE)
    applied = apply_quality_profile(original, "fast_low_cost")
    assert original["translation"]["qa_editor"]["min_word_overlap_ratio"] == 0.5
    assert applied["translation"]["qa_editor"]["min_word_overlap_ratio"] == 0.35


def test_profile_from_config_key() -> None:
    """Khi truyền config có quality_profile.name, dùng tên đó."""
    config_with_profile = copy.deepcopy(BASE)
    config_with_profile["quality_profile"] = {"name": "max_quality"}
    config = apply_quality_profile(config_with_profile)
    assert config.get("translation", {}).get("qa_editor", {}).get("min_word_overlap_ratio") == 0.7
