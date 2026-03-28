from __future__ import annotations

import copy
from typing import Any, Dict


PREPROCESSING_STRATEGY_OVERLAYS: Dict[str, Dict[str, Any]] = {
    "legacy": {},
    "ai_ready_balanced": {
        "preprocessing": {
            "ai_preclean": {"enabled": True},
            "chunking": {
                "adaptive_mode": True,
                "enable_balancing": True,
            },
            "structured_ir": {"enabled": True},
            "cleaning": {"profile": "safe"},
        }
    },
    "ocr_heavy": {
        "preprocessing": {
            "ai_preclean": {"enabled": True},
            "chunking": {"adaptive_mode": False, "enable_balancing": True},
            "cleaning": {"profile": "aggressive"},
            "semantic_enrichment": {"enabled": False},
        },
        "ocr": {
            "enabled": True,
            "ai_cleanup": {"enabled": True},
            "ai_spell_check": {"enabled": True},
        },
    },
    "layout_strict": {
        "preprocessing": {
            "epub": {"preserve_layout": True},
            "structured_ir": {"enabled": True},
            "cleaning": {"profile": "safe"},
        }
    },
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def resolve_preprocessing_strategy(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve preprocessing strategy as additive config overlay.

    Unknown/empty strategy falls back to legacy without breaking old configs.
    """
    resolved = copy.deepcopy(config)
    preprocessing = resolved.setdefault("preprocessing", {})
    strategy = (preprocessing.get("strategy") or "legacy").strip().lower()
    if strategy not in PREPROCESSING_STRATEGY_OVERLAYS:
        strategy = "legacy"
    preprocessing["strategy"] = strategy
    overlay = PREPROCESSING_STRATEGY_OVERLAYS[strategy]
    if not overlay:
        return resolved
    return _deep_merge(resolved, overlay)
