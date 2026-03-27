# Project: Novel Translator - Reliability Improvement
# Date: 2026-02-25
# Task: Rà soát và sửa lỗi thuật toán xoay vòng API key khi gặp lỗi 503/Timeout.

## 🎯 Task Overview
**Vấn đề:** Khi một Worker gặp lỗi API (như 503 UNAVAILABLE hoặc Timeout), hệ thống không lập tức cấp phát key mới từ quỹ dự phòng để thử lại, dẫn đến thất bại của phân đoạn dịch (Chunk).
**Mục tiêu:** Đảm bảo mọi lỗi "có thể phục hồi" (Retryable Errors) đều kích hoạt cơ chế đổi key ngay lập tức và ghi log chi tiết trạng thái key.

## 📋 Plan

### Phase 1: Investigation (Rà soát logic quản lý Key)
- [ ] **Xác định module quản lý Key:** Tìm kiếm trong `src/services/` để tìm `APIKeyManager` hoặc `GeminiAPIService`.
- [ ] **Xác định module điều phối dịch:** Xem `src/translation/translator.py` hoặc `execution_manager.py` để xem cách lỗi được bắt và xử lý.
- [ ] **Phân tích logic xử lý lỗi:** 
    - Xem danh sách các lỗi được coi là "Retryable".
    - Kiểm tra xem lỗi `503` có đang nằm trong danh sách kích hoạt đổi key hay không.
    - Tại sao thời gian chờ lại lên tới 20 phút (21:33 -> 21:53) mới báo lỗi? Kiểm tra cấu hình `timeout`.

### Phase 2: Root Cause Analysis (Xác định nguyên nhân)
- [ ] Tại sao log báo "No Fallback available"? Liệu quỹ dự phòng thực sự hết hay do logic cấp phát bị chặn?
- [ ] Kiểm tra cơ chế "Key Rotation" trong luồng `contextual_sentence` cleanup (vì lỗi xảy ra trong bước "Dịch lại theo ngữ cảnh").

### Phase 3: Implementation (Sửa đổi & Tối ưu)
- [ ] **Cập nhật `APIKeyManager`:** 
    - Đưa lỗi 503 vào danh sách "Immediate Rotation".
    - Thực hiện "Cool-down" cho key bị lỗi thay vì vô hiệu hóa hoàn toàn.
- [ ] **Cập nhật `NovelTranslator` / `GeminiService`:** 
    - Đảm bảo khi một request thất bại, nó yêu cầu một key *mới* (khác với key cũ) trước khi retry.
    - Giảm `timeout` xuống mức hợp lý (ví dụ 60-120s) để tránh treo worker quá lâu.
- [ ] **Ghi log chi tiết:** Thêm log: `[Rotation] Key {old_key} failed with 503. Replacing with {new_key} from pool.`

### Phase 4: Verification (Kiểm chứng)
- [ ] **Tạo script mock lỗi (`scripts/test_key_rotation.py`):** Giả lập một lỗi 503 và kiểm tra xem hệ thống có tự đổi sang key tiếp theo trong danh sách không.
- [ ] Kiểm tra trạng thái Key Pool sau khi lỗi xảy ra.

### Phase 5: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Đánh dấu hoàn thành.

## 🔍 Quality Checklist
- [ ] 100% lỗi 503 và 429 phải dẫn đến việc xoay vòng key.
- [ ] Không có worker nào bị "treo" quá 5 phút cho một request duy nhất.
- [ ] Log phải thể hiện rõ việc đổi key.
