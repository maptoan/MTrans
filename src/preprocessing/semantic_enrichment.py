from __future__ import annotations

from typing import Any, Dict, List


def enrich_structured_ir(
    blocks: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Optional semantic enrichment pass.

    Current scope is intentionally lightweight and safe:
    - Add provenance metadata.
    - Keep behavior no-op unless semantic_enrichment.enabled=true.
    """
    enrichment_cfg = (config.get("preprocessing") or {}).get("semantic_enrichment") or {}
    if not enrichment_cfg.get("enabled", False):
        return blocks

    enriched: List[Dict[str, Any]] = []
    for block in blocks:
        cloned = dict(block)
        meta = dict(cloned.get("metadata") or {})
        meta["enriched"] = True
        meta["enrichment_source"] = "internal_semantic_enrichment"
        cloned["metadata"] = meta
        enriched.append(cloned)
    return enriched
