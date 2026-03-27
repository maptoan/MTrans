from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def _default_token_counter(text: str) -> int:
    """
    Bộ đếm token đơn giản cho Phase 2:
    - 1 ký tự ≈ 1 token (đủ dùng cho logic chia nhỏ POC).
    """
    return max(1, len(text))


def build_chunks_from_text_map(
    text_map: List[Dict[str, Any]],
    max_tokens: int,
    token_counter: Optional[Callable[[str], int]] = None,
) -> List[Dict[str, Any]]:
    """
    Phase 2: Chunker từ TEXT_MAP.

    - Nhận danh sách bản ghi TEXT_MAP (đã được parse từ EPUB).
    - Gộp các bản ghi liên tiếp vào cùng một chunk sao cho tổng token ≤ max_tokens.
    - Mỗi chunk lưu:
        - global_id: int
        - text_original: text nối từ các original_text với delimiter
        - text: bằng text_original (marker CHUNK sẽ được thêm ở tầng khác)
        - tokens: số token ước tính
        - text_ids: List[str] của TEXT_ID theo thứ tự
        - text_delimiter: chuỗi delimiter dùng để nối, mặc định: \"\\n[TX:{id}]\\n\"
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens phải > 0")

    counter = token_counter or _default_token_counter

    chunks: List[Dict[str, Any]] = []
    current_ids: List[str] = []
    current_texts: List[str] = []
    current_tokens = 0
    delimiter_template = "\n[TX:{id}]\n"
    global_id = 1

    for entry in text_map:
        text_id = entry["text_id"]
        text = entry["original_text"]

        # Token của đoạn mới
        text_tokens = counter(text)

        # Nếu chunk hiện tại rỗng → luôn thêm vào
        if not current_ids:
            current_ids.append(text_id)
            current_texts.append(text)
            current_tokens = text_tokens
            continue

        # Nếu thêm đoạn mới vào vượt quá max_tokens → đóng chunk hiện tại, mở chunk mới
        if current_tokens + text_tokens > max_tokens:
            joined = _join_with_delimiter(current_ids, current_texts, delimiter_template)
            chunks.append(
                {
                    "global_id": global_id,
                    "text_original": joined,
                    "text": joined,
                    "tokens": current_tokens,
                    "text_ids": list(current_ids),
                    "text_delimiter": delimiter_template,
                }
            )
            global_id += 1
            # Reset cho chunk mới
            current_ids = [text_id]
            current_texts = [text]
            current_tokens = text_tokens
        else:
            # Vẫn còn chỗ trong chunk hiện tại
            current_ids.append(text_id)
            current_texts.append(text)
            current_tokens += text_tokens

    # Đóng chunk cuối cùng nếu còn dữ liệu
    if current_ids:
        joined = _join_with_delimiter(current_ids, current_texts, delimiter_template)
        chunks.append(
            {
                "global_id": global_id,
                "text_original": joined,
                "text": joined,
                "tokens": current_tokens,
                "text_ids": list(current_ids),
                "text_delimiter": delimiter_template,
            }
        )

    return chunks


def _join_with_delimiter(
    text_ids: List[str],
    texts: List[str],
    delimiter_template: str,
) -> str:
    """
    Nối danh sách texts theo thứ tự, chèn delimiter [TX:{id}] giữa các đoạn.
    Ví dụ:
      texts = [\"A\", \"B\"], ids = [\"t0\", \"t1\"]
      → \"A\\n[TX:t0]\\nB\\n[TX:t1]\\n\"
    """
    parts: List[str] = []
    for tid, txt in zip(text_ids, texts):
        parts.append(txt)
        parts.append(delimiter_template.format(id=tid))
    return "".join(parts)

