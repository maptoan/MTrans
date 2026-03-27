# Project: Novel Translator - Bug Fix
# Date: 2026-02-25
# Task: Sửa lỗi thuật toán chunking cắt ở giữa câu.

## 🎯 Task Overview
**Bug:** Thuật toán `SmartChunker` đôi khi cắt văn bản tại những điểm không tối ưu (ví dụ: giữa một câu), làm mất ngữ cảnh cho mô hình AI và gây ra lỗi dịch thuật.
**Mục tiêu:** Đảm bảo mỗi chunk luôn kết thúc tại một ranh giới tự nhiên: Cuối chương (Chapter), cuối đoạn (Paragraph), hoặc ít nhất là cuối câu (Sentence).

## 📋 Plan

### Phase 1: Investigation (Phân tích thuật toán hiện tại)
- [ ] **Đọc mã nguồn `src/preprocessing/chunker.py`:** Tập trung vào các phương thức `chunk_text`, `_find_safe_split_point` hoặc tương đương.
- [ ] **Xác định các tiêu chí cắt hiện tại:** Xem thuật toán đang ưu tiên những ký tự nào (ví dụ: `
`, `.`, `?`, `!`).
- [ ] **Kiểm tra cơ chế đếm token:** Đảm bảo việc đếm token không gây ra sai số khiến điểm cắt bị đẩy vào giữa câu.

### Phase 2: Root Cause Analysis (Xác định nguyên nhân)
- [ ] **Tạo script tái hiện lỗi (`scripts/reproduce_chunk_bug.py`):**
    - Sử dụng một đoạn văn bản dài có nhiều câu phức tạp.
    - Cấu hình `max_tokens` nhỏ để ép thuật toán phải cắt.
    - Kiểm tra xem kết quả chunk cuối có bị cắt ngang câu không.
- [ ] **Phân tích log:** Xem tại sao các điểm cắt tự nhiên bị bỏ qua.

### Phase 3: Implementation (Tối ưu hóa thuật toán)
- [ ] **Cải thiện logic `_find_safe_split_point`:**
    - Cấp độ 1: Tìm ranh giới chương/hồi (Header markers).
    - Cấp độ 2: Tìm ranh giới đoạn văn (`

` hoặc `
`).
    - Cấp độ 3: Tìm ranh giới câu (Dấu chấm, dấu hỏi, dấu cảm thán theo sau là khoảng trắng).
    - Cấp độ 4 (Fallback): Tìm khoảng trắng gần nhất (tránh cắt giữa từ).
- [ ] **Xử lý trích dẫn (Quotes):** Tránh cắt ở giữa một đoạn hội thoại nằm trong dấu ngoặc kép.

### Phase 4: Verification (Kiểm chứng)
- [ ] **Chạy lại script tái hiện:** Đảm bảo tất cả các điểm cắt đều rơi vào ranh giới câu hoặc đoạn.
- [ ] **Kiểm tra với dữ liệu thực tế (HMQT):** Chạy thử với cấu hình thực tế và kiểm tra 5-10 chunk ngẫu nhiên.

### Phase 5: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Xóa các script test tạm thời.
- [ ] Đánh dấu hoàn thành.

## 🔍 Quality Checklist
- [ ] Không có chunk nào kết thúc bằng một từ dở dang.
- [ ] Không có chunk nào kết thúc ở giữa một câu (trừ khi câu đó dài hơn cả `max_tokens` - trường hợp cực hiếm).
- [ ] Logic mới không làm giảm đáng kể hiệu suất chia chunk.
