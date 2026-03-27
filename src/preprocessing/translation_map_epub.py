from __future__ import annotations

import re
from typing import Any, Dict, List

MARKER_PATTERN = re.compile(r"\[TX:(?P<id>[^\]]+)\]")


def build_translation_map_from_chunks(
    chunks: List[Dict[str, Any]],
    translated_by_chunk: Dict[int, str],
) -> Dict[str, str]:
    """
    Phase 3: Xây dựng map text_id -> bản dịch từ kết quả dịch từng chunk.

    Giả định happy-path:
    - Bản dịch giữ nguyên marker [TX:<id>] sau mỗi đoạn tương ứng.
    - Với mỗi chunk:
        translation = SEG0 + [TX:id0] + SEG1 + [TX:id1] + ...
      Ta tách SEGk và map với text_ids[k].
    """
    translation_map: Dict[str, str] = {}

    for chunk in chunks:
        chunk_id = chunk.get("global_id")
        if chunk_id is None:
            continue

        translated = translated_by_chunk.get(chunk_id)
        if not translated:
            continue

        text_ids: List[str] = chunk.get("text_ids", [])
        if not text_ids:
            continue

        segments = _split_by_markers(translated)

        # segments là list các (id, text) theo thứ tự marker.
        for text_id, text in segments:
            if text_id in text_ids:
                translation_map[text_id] = text

    return translation_map


def _split_by_markers(text: str) -> List[tuple[str, str]]:
    """
    Tách text theo pattern [TX:id], trả về danh sách (id, đoạn_trước_marker).
    Ví dụ:
      \"A\\n[TX:t0]\\nB\\n[TX:t1]\\n\" -> [(\"t0\", \"A\"), (\"t1\", \"B\")]
    """
    results: List[tuple[str, str]] = []
    last_pos = 0

    for match in MARKER_PATTERN.finditer(text):
        marker_start = match.start()
        marker_id = match.group("id")

        # Đoạn text ngay TRƯỚC marker thuộc về chính marker_id đó.
        # Ví dụ: "A\n[TX:t0]\n" -> segment "A" map với "t0".
        segment = text[last_pos:marker_start]
        cleaned = segment.strip()
        if cleaned:
            results.append((marker_id, cleaned))

        # Cập nhật last_pos ngay sau marker
        last_pos = match.end()

    # Phần cuối sau marker cuối cùng (nếu có) không có id để ánh xạ rõ ràng → bỏ qua (happy-path).
    return results


