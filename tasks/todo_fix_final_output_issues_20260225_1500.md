# Project: Novel Translator - Final Polish & Bug Fix
# Date: 2026-02-25
# Task: Khắc phục 5 lỗi nghiêm trọng trong tệp kết quả cuối cùng (HMQT).

## 🎯 Task Overview
**Mục tiêu:** Đảm bảo tệp kết quả cuối cùng sạch sẽ, không còn rác AI, không còn marker, ranh giới câu chuẩn xác và định dạng Heading hoàn hảo trên mọi định dạng (TXT, DOCX, EPUB, PDF).

## 📋 Plan

### Phase 1: Investigation (Rà soát tệp lỗi & Code)
- [ ] **Đọc tệp kết quả lỗi:** Sử dụng `type` để xem nội dung `data/output/HMQT_translated.txt` để xác nhận các lỗi 1, 3, 4.
- [ ] **Rà soát logic Merge:** Xem `NovelTranslator._merge_all_chunks` và `OutputFormatter.save` để tìm lý do tại sao Marker không bị xóa.
- [ ] **Rà soát logic Cleanup:** Xem tại sao nội dung `[KIỂM TRA CHẤT LƯỢNG]` bị lọt vào bản dịch.
- [ ] **Rà soát logic Chunker:** Kiểm tra lại `SmartChunker` với tệp nguồn thực tế để tìm điểm cắt lỗi.

### Phase 2: Implementation (Sửa lỗi)
- [ ] **Lỗi 1 (Markers):** Cập nhật logic ghép file để tự động xóa sạch `[CHUNK:ID:START/END]` trước khi ghi file.
- [ ] **Lỗi 2 (Chunk Boundary):** Tinh chỉnh thêm `SmartChunker`, tăng cường độ ưu tiên cho dấu câu kết thúc paragraph.
- [ ] **Lỗi 3 (Thinking Leakage):** 
    - Thêm bước hậu xử lý (Post-process) cưỡng bứa để xóa bỏ các khối `[KIỂM TRA CHẤT LƯỢNG]` hoặc `☑`.
    - Cập nhật System Prompt để AI tuyệt đối không trả về phần checklist này.
- [ ] **Lỗi 4 & 5 (Headings & TOC):**
    - Đảm bảo `OutputFormatter.save` gọi đúng logic chuẩn hóa Heading cho mọi định dạng.
    - Sửa lỗi gộp mục lục: Đảm bảo các dòng tiêu đề trong tệp TXT trung gian có đủ dấu xuống dòng (`

`) để Pandoc không gộp chúng lại.
    - Cập nhật logic convert sang EPUB/PDF để sử dụng Markdown Heading (`#`, `##`) thay vì chỉ phụ thuộc vào tags.

### Phase 3: Verification (Kiểm chứng)
- [ ] **Tạo kịch bản test tổng hợp:** Chạy lại toàn bộ quy trình Finalize cho HMQT.
- [ ] **Kiểm tra tệp TXT:** Đảm bảo không còn marker, không còn checklist, Heading được nhận diện.
- [ ] **Kiểm tra tệp DOCX/EPUB/PDF:** Mở file (hoặc kiểm tra metadata) để xác nhận cấu trúc Heading và Mục lục (TOC).

### Phase 4: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Đánh dấu hoàn thành.

## 🔍 Quality Checklist
- [ ] Không còn bất kỳ dấu vết của `[CHUNK:...]`.
- [ ] Không còn ký tự `☑` hay `[KIỂM TRA CHẤT LƯỢNG]` trong bản dịch.
- [ ] Mỗi chương phải bắt đầu ở một trang mới (với DOCX/PDF) hoặc có Heading chuẩn (EPUB).
- [ ] Mục lục (TOC) phải hiển thị rời rạc, không bị dính chùm.
