# Hướng Dẫn Format Normalization

## Vấn Đề

Khi dịch nhiều chunks, mỗi chunk có thể format headings khác nhau:
- Có chunk dùng `[H1]` cho tiêu đề chương
- Có chunk lại dùng `[H1]` cho cả đề mục nhỏ
- Tài liệu có đề mục lặp lại nhưng mỗi chunk format khác nhau

→ Kết quả: Format tổng thể của ebook bị lộn xộn, không thống nhất.

## Giải Pháp

### 1. Format Normalizer Module

Module `src/utils/format_normalizer.py` tự động:
1. **Phân tích format** của các chunks đã dịch
2. **Xác định format pattern** phổ biến nhất
3. **Normalize format** của tất cả chunks theo pattern đó

### 2. Cải Thiện Prompt

Prompt đã được cải thiện với hướng dẫn rõ ràng về format headings:
- `[H1]` → Chỉ dùng cho tiêu đề chương (Chapter/Chương/第X章)
- `[H2]` → Chỉ dùng cho tiêu đề mục (Section/Mục/1.1)
- `[H3]` → Chỉ dùng cho tiêu đề tiểu mục (Subsection/1.1.1)

### 3. Tích Hợp Vào Workflow

Format normalization được tích hợp vào `_merge_all_chunks()`:
- Sau khi merge và validate chunks
- Trước khi return final content
- Tự động normalize format của tất cả chunks

## Cách Hoạt Động

### 1. Phân Tích Format

```python
from src.utils.format_normalizer import FormatNormalizer

normalizer = FormatNormalizer(config)
format_patterns = normalizer.analyze_format_patterns(chunks)
```

**Output:**
```python
{
    'heading_formats': {
        'H1': ['Chương 1', 'Chương 2', ...],
        'H2': ['1.1 Giới thiệu', '1.2 Nội dung', ...],
        'H3': ['1.1.1 Chi tiết', ...],
    },
    'most_common_format': {
        'H1': 'Chương X',
        'H2': '1.1',
        'H3': '1.1.1',
    },
    'format_consistency': {
        'H1': 0.95,  # 95% chunks dùng format giống nhau
        'H2': 0.80,
        'H3': 0.90,
        'overall': 0.88,
    },
}
```

### 2. Normalize Format

```python
normalized_chunks, report = normalizer.normalize_all_chunks(chunks)
```

**Logic:**
1. Phân tích format từ các chunks đầu tiên (default: 10 chunks)
2. Xác định format phổ biến nhất cho mỗi level (H1/H2/H3)
3. Normalize tất cả chunks theo format đó:
   - Xác định loại heading (chapter/section/subsection)
   - Áp dụng level phù hợp (H1/H2/H3)
   - Đảm bảo format nhất quán

### 3. Tự Động Trong Workflow

Format normalization được gọi tự động trong `_merge_all_chunks()`:

```python
# BƯỚC 9: Normalize format giữa các chunks
logger.info("🔧 Đang normalize format giữa các chunks...")
normalizer = FormatNormalizer(self.config)
normalized_chunks, analysis_report = normalizer.normalize_all_chunks(chunks_list)
full_content = "\n\n".join(normalized_chunks)
```

## Cấu Hình

### Config (config.yaml)

```yaml
format_normalizer:
  heading_patterns:
    chapter:
      - '^第?\s*\d+\s*章[：:]?\s*'  # 第1章, 第一章
      - '^[Cc]hapter\s+\d+[：:]?\s*'  # Chapter 1
      - '^[Cc]hương\s+\d+[：:]?\s*'  # Chương 1
    section:
      - '^第?\s*\d+[\.、]\s*\d+[：:]?\s*'  # 1.1
      - '^[Ss]ection\s+\d+[：:]?\s*'  # Section 1
    subsection:
      - '^第?\s*\d+[\.、]\s*\d+[\.、]\s*\d+[：:]?\s*'  # 1.1.1
  heading_levels:
    chapter: 'H1'
    section: 'H2'
    subsection: 'H3'
  min_heading_length: 3
  max_heading_length: 100
```

## Ví Dụ

### Trước Normalization

**Chunk 1:**
```
[H1]Chương 1: Khởi đầu[/H1]
[H1]1.1 Giới thiệu[/H1]  ← Sai: 1.1 phải là [H2]
```

**Chunk 2:**
```
[H1]Chương 2: Tiếp tục[/H1]
[H2]2.1 Nội dung[/H2]  ← Đúng
```

### Sau Normalization

**Chunk 1:**
```
[H1]Chương 1: Khởi đầu[/H1]
[H2]1.1 Giới thiệu[/H2]  ← Đã sửa thành [H2]
```

**Chunk 2:**
```
[H1]Chương 2: Tiếp tục[/H1]
[H2]2.1 Nội dung[/H2]  ← Giữ nguyên (đã đúng)
```

## Logs

Khi normalize format, logs sẽ hiển thị:

```
📊 Format analysis: H1 consistency: 95.00%, H2 consistency: 80.00%, H3 consistency: 90.00%, Overall: 88.33%
✅ Normalized 15/100 chunks
📊 Format consistency: H1=95.00%, H2=80.00%, H3=90.00%
```

## Lưu Ý

1. **Phân tích từ chunks đầu tiên**: Normalizer phân tích format từ các chunks đầu tiên (default: 10) để xác định format phổ biến nhất.

2. **Heuristic classification**: Nếu không match pattern, normalizer dùng heuristic để phân loại heading:
   - Heading ngắn, không có dấu chấm → có thể là chapter
   - Có pattern "1.1" → section
   - Có pattern "1.1.1" → subsection

3. **Fallback**: Nếu normalize fail, workflow sẽ tiếp tục với format gốc (không throw error).

4. **Performance**: Normalization chạy sau khi merge, không ảnh hưởng đến tốc độ dịch.

## Troubleshooting

### Vấn đề: Format vẫn không thống nhất

**Nguyên nhân:**
- Prompt không đủ rõ ràng
- Chunks đầu tiên có format sai → normalizer học sai pattern

**Giải pháp:**
1. Kiểm tra prompt có hướng dẫn rõ ràng về format không
2. Tăng số chunks để phân tích (`analyze_first_n`)
3. Review và sửa thủ công các chunks đầu tiên nếu cần

### Vấn đề: Normalize sai level

**Nguyên nhân:**
- Pattern matching không chính xác
- Heuristic classification sai

**Giải pháp:**
1. Thêm pattern vào config nếu cần
2. Điều chỉnh heuristic trong `_classify_heading()`
3. Review và sửa thủ công nếu cần

## Tương Lai

Có thể mở rộng:
1. **Learning từ user feedback**: Học format từ user corrections
2. **Multi-document consistency**: Đảm bảo format nhất quán giữa nhiều documents
3. **Custom format rules**: Cho phép user định nghĩa format rules riêng
