# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def get_project_root() -> Path:
    """Trả về thư mục gốc dự án dựa trên vị trí file hiện tại."""
    return Path(__file__).resolve().parents[2]


def resolve_path(path_value: Optional[str], default_relative: str) -> Path:
    """
    Resolve path theo project root để không phụ thuộc current working directory.

    - Nếu `path_value` rỗng: dùng `default_relative`.
    - Nếu là absolute path: giữ nguyên.
    - Nếu là relative path: resolve theo project root.
    """
    raw = (path_value or "").strip() or default_relative
    path = Path(raw)
    if not path.is_absolute():
        path = get_project_root() / path
    return path


def get_progress_dir(config: Dict[str, Any]) -> Path:
    """Ưu tiên storage.progress_path, fallback progress.progress_dir."""
    storage_cfg = config.get("storage", {})
    progress_cfg = config.get("progress", {})
    raw = storage_cfg.get("progress_path") or progress_cfg.get("progress_dir")
    return resolve_path(raw, "data/progress")


def get_output_dir(config: Dict[str, Any]) -> Path:
    out_cfg = config.get("output", {})
    return resolve_path(out_cfg.get("output_path"), "data/output")


def get_cache_dir(config: Dict[str, Any]) -> Path:
    storage_cfg = config.get("storage", {})
    return resolve_path(storage_cfg.get("cache_path"), "data/cache")


def get_metadata_dir(config: Dict[str, Any], novel_name: str) -> Path:
    """
    Resolve thư mục metadata theo config hiện hành.
    Ưu tiên parent của style_profile_path để tương thích ngược.
    """
    meta_cfg = config.get("metadata", {})
    style_path = meta_cfg.get("style_profile_path")
    if style_path:
        return resolve_path(style_path, f"data/metadata/{novel_name}").parent
    return resolve_path(None, f"data/metadata/{novel_name}")

