# Project: Novel Translator - Formatting Integrity Fix
# Date: 2026-02-25
# Task: Sửa lỗi gộp đoạn văn khi tạo file EPUB/DOCX/PDF.

## 🎯 Task Overview
**Vấn đề:** Các dòng đơn trong TXT bị Pandoc và hệ thống convert gộp lại thành một đoạn văn duy nhất trong ebook, làm mất cấu trúc danh sách và tiêu đề phụ.
**Mục tiêu:** Đảm bảo mọi ngắt dòng trong bản dịch gốc được bảo toàn 100% trên tất cả định dạng đầu ra.

## 📋 Plan

### Phase 1: Investigation (Rà soát logic Paragraph)
- [ ] **Kiểm tra `src/utils/paragraph_preserver.py`:** Xem cách hệ thống đang bảo tồn đoạn văn khi ghép các chunks.
- [ ] **Kiểm tra `src/utils/format_normalizer.py`:** Xem liệu có bước nào đang xóa nhầm các dấu xuống dòng đơn không.

### Phase 2: Implementation (Sửa lỗi)
- [ ] **Gia cố `OutputFormatter._normalize_paragraphs`:** 
    - Chuyển đổi mọi dấu xuống dòng đơn (`
`) thành xuống dòng đôi (`

`) đối với các khối nội dung không phải là Heading, hoặc sử dụng cấu hình `hard_line_breaks` cho Pandoc.
    - **Giải pháp ưu tiên:** Đảm bảo tệp TXT trung gian sử dụng định dạng Markdown chuẩn (double-newline cho paragraph).
- [ ] **Cập nhật `convert_txt_to_epub` và `convert_txt_to_pdf`:** Thêm extension `+hard_line_breaks` vào format reader của Pandoc để nó tôn trọng mọi dấu xuống dòng trong tệp TXT.
- [ ] **Gia cố `save_as_docx`:** Đảm bảo mỗi dòng trong TXT là một `add_paragraph()` riêng biệt trong Word.

### Phase 3: Verification (Kiểm chứng)
- [ ] Chạy test với đoạn văn bản người dùng cung cấp.
- [ ] Kiểm tra kết quả convert xem danh sách 1, 2, 3 đã nằm trên các dòng riêng biệt chưa.

### Phase 4: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
