from __future__ import annotations

import copy

from src.preprocessing.strategy_resolver import resolve_preprocessing_strategy
from src.utils.quality_profile import apply_quality_profile


def _base_config() -> dict:
    return {
        "preprocessing": {
            "strategy": "legacy",
            "chunking": {"max_chunk_tokens": 9000, "adaptive_mode": False},
            "ai_preclean": {"enabled": False},
            "epub": {"preserve_layout": False},
        },
        "ocr": {"ai_cleanup": {"enabled": False}},
    }


def test_legacy_keeps_original_values() -> None:
    config = _base_config()
    resolved = resolve_preprocessing_strategy(config)
    assert resolved["preprocessing"]["chunking"]["max_chunk_tokens"] == 9000
    assert resolved["preprocessing"]["ai_preclean"]["enabled"] is False


def test_ai_ready_balanced_applies_additive_overrides() -> None:
    config = _base_config()
    config["preprocessing"]["strategy"] = "ai_ready_balanced"
    resolved = resolve_preprocessing_strategy(config)
    assert resolved["preprocessing"]["ai_preclean"]["enabled"] is True
    assert resolved["preprocessing"]["chunking"]["adaptive_mode"] is True
    assert resolved["preprocessing"]["chunking"]["enable_balancing"] is True


def test_unknown_strategy_falls_back_to_legacy() -> None:
    config = _base_config()
    config["preprocessing"]["strategy"] = "not_exists"
    resolved = resolve_preprocessing_strategy(config)
    assert resolved["preprocessing"]["strategy"] == "legacy"


def test_resolve_after_quality_profile_keeps_translation_overlay() -> None:
    """Same order as NovelTranslator: quality profile then preprocessing strategy."""
    base = copy.deepcopy(_base_config())
    base["quality_profile"] = {"name": "fast_low_cost"}
    base["translation"] = {
        "enable_final_cleanup_pass": True,
        "collect_residuals": True,
        "qa_editor": {"min_word_overlap_ratio": 0.5, "max_batch_size": 30},
    }
    merged = resolve_preprocessing_strategy(apply_quality_profile(base))
    assert merged["translation"]["enable_final_cleanup_pass"] is False
    assert merged["preprocessing"]["strategy"] == "legacy"
