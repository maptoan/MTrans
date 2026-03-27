# Project: Novel Translator - Debugging
# Date: 2026-02-25
# Task: Điều tra và sửa lỗi nhận diện Heading tại Chunk-5 (HMQT).

## 🎯 Task Overview
**Vấn đề:** Chương trình không nhận diện được các cấp độ Heading (1, 2, 3) trong tệp `data/progress/HMQT_chunks/5.txt`, dẫn đến việc xuất file DOCX/PDF thiếu định dạng cấu trúc.
**Mục tiêu:** Phân tích cấu trúc tệp, xác định điểm yếu của logic nhận diện hiện tại và cập nhật code để xử lý chính xác.

## 📋 Plan

### Phase 1: Investigation (Phân tích cấu trúc và định dạng)
- [ ] **Đọc nội dung thô của Chunk-5:** Sử dụng lệnh `type` để xem nội dung thực tế bao gồm cả khoảng trắng, ký tự đặc biệt và encoding.
- [ ] **Kiểm tra Encoding và Line Endings:** Xác định xem có phải do ký tự xuống dòng (LF vs CRLF) hoặc khoảng trắng đầu dòng lạ làm lệch Regex không.
- [ ] **Trích xuất các mẫu Heading tiềm năng:** Liệt kê các dòng trong `5.txt` mà mắt thường nhận diện là tiêu đề nhưng code bỏ qua.
- [ ] **Đối chiếu với `_detect_heading_level`:** Chạy thử các dòng đó qua logic regex hiện có trong `src/output/formatter.py` để tìm điểm không khớp.

### Phase 2: Root Cause Analysis (Xác định nguyên nhân)
- [ ] Kiểm tra độ dài dòng (Heuristic hiện tại giới hạn < 10 hoặc < 15 từ).
- [ ] Kiểm tra tính chất viết hoa (isupper, istitle).
- [ ] Kiểm tra các từ khóa (Chương, Phần, Hồi...) và các ký tự đặc biệt bao quanh (ví dụ: `【...】`, `---`).

### Phase 3: Implementation (Cập nhật logic)
- [ ] **Tối ưu hóa Regex:** Cập nhật `_detect_heading_level` để linh hoạt hơn với khoảng trắng và các ký tự bao bọc tiêu đề (như dấu ngoặc vuông Trung Quốc `【 】`).
- [ ] **Bổ sung Heuristics:** Thêm quy tắc nhận diện cho các dòng bắt đầu bằng ký hiệu mưu kế hoặc định dạng đặc trưng của tài liệu này.
- [ ] **Xử lý khoảng trắng:** Đảm bảo `strip()` hoạt động triệt để với các loại khoảng trắng Unicode.

### Phase 4: Verification (Kiểm chứng)
- [ ] **Tạo kịch bản test:** Chạy lại bước tạo DOCX/PDF cho đúng Chunk-5 này.
- [ ] **Kiểm tra log:** Xác nhận các dòng tiêu đề đã được nhận diện (log "Applying Heading X style").
- [ ] **Xác nhận thủ công:** Xem file output để đảm bảo định dạng hiển thị đúng.

### Phase 5: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Đánh dấu hoàn thành.

## 🔍 Quality Checklist
- [ ] Không nhận diện nhầm các đoạn văn thường thành Heading.
- [ ] Hỗ trợ các ký tự trang trí tiêu đề thường gặp trong tiểu thuyết/tài liệu Trung Quốc.
- [ ] Code vẫn giữ được hiệu năng và tính ổn định.
