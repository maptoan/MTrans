from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from src.preprocessing.file_parser import parse_file_advanced
from src.preprocessing.text_cleaner import clean_text
from src.preprocessing.chunker import SmartChunker


def _load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    config["config_path"] = config_path
    return config


def run_baseline(input_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    parser_start = time.perf_counter()
    parsed = parse_file_advanced(input_path, config)
    parse_ms = (time.perf_counter() - parser_start) * 1000.0

    clean_start = time.perf_counter()
    cleaned = clean_text(parsed.get("text", ""), config)
    clean_ms = (time.perf_counter() - clean_start) * 1000.0

    chunker = SmartChunker(config)
    chunk_start = time.perf_counter()
    chunks = chunker.chunk_novel(cleaned)
    chunk_ms = (time.perf_counter() - chunk_start) * 1000.0

    token_sum = sum(chunk.get("tokens", 0) for chunk in chunks) if chunks else 0
    avg_tokens = (token_sum / len(chunks)) if chunks else 0.0
    utilization = (
        avg_tokens / float(max(1, chunker.max_effective_tokens))
        if chunks
        else 0.0
    )
    return {
        "input_path": input_path,
        "format": parsed.get("format"),
        "parse_ms": round(parse_ms, 2),
        "clean_ms": round(clean_ms, 2),
        "chunk_ms": round(chunk_ms, 2),
        "char_count_raw": len(parsed.get("text", "")),
        "char_count_cleaned": len(cleaned),
        "chunk_count": len(chunks),
        "avg_chunk_tokens": round(avg_tokens, 2),
        "token_utilization": round(utilization, 4),
        "structured_ir_blocks": len(parsed.get("structured_ir") or []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocessing baseline benchmark")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/reports/preprocessing_baseline.json")
    args = parser.parse_args()

    config = _load_config(args.config)
    result = run_baseline(args.input, config)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
