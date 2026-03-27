# Project: Novel Translator - EPUB Quality Audit
# Date: 2026-02-25
# Task: Tối ưu thuật toán tạo EPUB để đảm bảo tính toàn vẹn và cấu trúc chuyên nghiệp.

## 📋 Plan

### Phase 1: Implementation (Gia cố Code)
- [ ] **Gia cố Input Validation (`src/translation/format_converter.py`):**
    - Thêm bước kiểm tra tag-mismatch (ví dụ: `[H1]` không có `[/H1]`) trước khi convert.
    - Tự động sửa các lỗi tag phổ biến của AI.
- [ ] **Tối ưu Segmentation & TOC (`src/output/formatter.py`):**
    - Đảm bảo Pandoc sử dụng thuộc tính `split-level=1` để mỗi chương là một file riêng biệt trong EPUB (giúp load nhanh hơn).
    - Đồng bộ hóa logic nhận diện Heading giữa TXT và EPUB.
- [ ] **Cải thiện Metadata:**
    - Cho phép tự động điền Tên truyện và Tác giả từ Style Profile nếu `epub_options` bị trống.

### Phase 2: Verification (Kiểm chứng)
- [ ] Tạo file TXT test với Heading lỗi font và tag bị lệch.
- [ ] Chạy convert và giải nén file EPUB để kiểm tra cấu trúc `.xhtml` bên trong.
- [ ] Kiểm tra file `nav.xhtml` (Mục lục) xem các đề mục đặc biệt có xuất hiện không.

### Phase 3: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
