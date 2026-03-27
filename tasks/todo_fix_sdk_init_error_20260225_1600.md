# Project: Novel Translator - SDK Stability Fix
# Date: 2026-02-25
# Task: Sửa lỗi khởi tạo SDK Gemini (Missing api_key) và AttributeError trong aclose().

## 🎯 Task Overview
**Vấn đề:** 
1. `GeminiAPIService` đôi khi nhận `api_key` là `None` trong luồng cleanup, gây lỗi khởi tạo SDK.
2. SDK crash khi đóng một Client chưa được khởi tạo hoàn chỉnh.
**Mục tiêu:** Đảm bảo `api_key` luôn hợp lệ trước khi tạo Client và xử lý lỗi dọn dẹp Client an toàn.

## 📋 Plan

### Phase 1: Investigation (Rà soát code)
- [ ] **Kiểm tra `src/services/genai_adapter.py`**: Xem logic `create_client` có kiểm tra null cho `api_key` không.
- [ ] **Kiểm tra `src/services/gemini_api_service.py`**: 
    - Rà soát hàm `_get_client()` và `generate_content_async()`.
    - Tìm hiểu tại sao `current_key` có thể bị `None`.
- [ ] **Kiểm tra `src/translation/cjk_cleaner.py`**: Xem cách nó gọi `gemini_service.generate_content_async`.

### Phase 2: Implementation (Sửa lỗi)
- [ ] **Gia cố `create_client`**: Thêm kiểm tra `if not api_key: raise ValueError`.
- [ ] **Gia cố `GeminiAPIService`**: 
    - Đảm bảo luôn lấy key từ `distributor` hoặc `key_manager` nếu `api_key` truyền vào bị trống.
    - Thêm khối `try/except` bao quanh lệnh `await self.current_client.aclose()` để tránh crash hệ thống khi SDK bị lỗi nội bộ.
- [ ] **Sửa luồng gọi cleanup**: Đảm bảo `worker_id` luôn được truyền đi để lấy key từ distributor.

### Phase 3: Verification (Kiểm chứng)
- [ ] **Tạo script test giả lập Key None**: Chạy thử xem hệ thống có tự lấy key thay thế thay vì crash SDK không.

### Phase 4: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Đánh dấu hoàn thành.
