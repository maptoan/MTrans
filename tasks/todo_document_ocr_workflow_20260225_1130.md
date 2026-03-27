# Project: Novel Translator - Documentation
# Date: 2026-02-25
# Task: Trình bày workflow xử lý PDF scan (OCR).

## 🎯 Task Overview
**Mục tiêu:** Phân tích và mô tả chi tiết cách hệ thống xử lý một tệp PDF không có text layer (scan), từ khâu nhận diện, bóc tách ảnh, chạy OCR đến khi dọn dẹp bằng AI và đưa vào luồng dịch.

## 📋 Plan

### Phase 1: Research (Phân tích mã nguồn)
- [ ] **Phân tích `src/preprocessing/input_preprocessor.py`:** Xem cách hệ thống nhận diện loại tệp PDF và quyết định chạy luồng OCR.
- [ ] **Phân tích `src/preprocessing/ocr_reader.py`:** 
    - Xem quy trình render PDF sang ảnh (`pdf2image`).
    - Xem cách sử dụng `Tesseract` và `OpenCV` để trích xuất văn bản.
    - Xem luồng **AI Cleanup** và **AI Spell Check** sử dụng Gemini API.
- [ ] **Phân tích `src/preprocessing/text_cleaner.py`:** Xem cách dọn dẹp hậu OCR (loại bỏ noise, header/footer).

### Phase 2: Documentation (Xây dựng Workflow)
- [ ] Tổng hợp thông tin thành một sơ đồ luồng logic.
- [ ] Giải thích chi tiết từng bước:
    1. Detection (Nhận diện).
    2. Vision/OCR (Trích xuất).
    3. AI Post-processing (Dọn dẹp & sửa lỗi).
    4. Integration (Tích hợp vào luồng dịch chuẩn).

### Phase 3: Verification (Xác minh)
- [ ] Đối chiếu tài liệu vừa viết với các tham số trong `config.yaml` để đảm bảo tính nhất quán (ví dụ: `ocr.enabled`, `ai_cleanup.enabled`).

### Phase 4: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Trình bày kết quả cho người dùng.

## 🔍 Quality Checklist
- [ ] Workflow phải thể hiện rõ sự khác biệt giữa xử lý PDF text-based và PDF scan.
- [ ] Phải nêu bật được vai trò của AI trong việc nâng cao chất lượng OCR.
- [ ] Các thành phần kỹ thuật (Tesseract, OpenCV, pdf2image) phải được đề cập đúng vị trí.
