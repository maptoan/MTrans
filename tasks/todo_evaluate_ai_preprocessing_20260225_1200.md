# Project: Novel Translator - Strategic Evaluation
# Date: 2026-02-25
# Task: Đánh giá việc bổ sung AI Cleanup/Spell Check cho tệp Text-based.

## 🎯 Task Overview
**Mục tiêu:** Phân tích lợi ích và rủi ro khi dùng AI để "dọn dẹp" văn bản nguồn (không phải scan) trước khi dịch. Đây là một bước quan trọng để quyết định có nên biến nó thành tiêu chuẩn cho mọi loại file hay không.

## 📋 Plan

### Phase 1: Research (Phân tích ngữ cảnh kỹ thuật)
- [x] Đã nắm rõ cơ chế AI Cleanup/Spell Check hiện tại (qua task trước).
- [ ] **Kiểm tra `src/preprocessing/text_cleaner.py`:** Xem các quy tắc dọn dẹp bằng Regex hiện có để so sánh với năng lực của AI.
- [ ] **Xem xét `config.yaml`:** Xác định chi phí tài nguyên (API keys, RPD) nếu kích hoạt tính năng này cho các tệp văn bản lớn (novel hàng triệu chữ).

### Phase 2: Evaluation (Đánh giá chi tiết)
- [ ] **Phân tích Ưu điểm:**
    *   Chất lượng văn bản nguồn (Normalizing).
    *   Phục hồi cấu trúc (Paragraph restoration).
    *   Loại bỏ nhiễu (Noise removal: headers, footers, page numbers).
- [ ] **Phân tích Nhược điểm:**
    *   Chi phí (Cost - Token usage).
    *   Thời gian (Latency).
    *   Rủi ro sai lệch (Hallucination/Corruption).
    *   Vấn đề về Token Limit và Context Window.

### Phase 3: Synthesis & Recommendation (Tổng hợp & Đề xuất)
- [ ] Đưa ra kết luận: Khi nào nên bật, khi nào nên tắt.
- [ ] Đề xuất cấu hình tối ưu (Hybrid approach).

### Phase 4: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Trình bày báo cáo đánh giá cho người dùng.

## 🔍 Quality Checklist
- [ ] Đánh giá phải dựa trên dữ liệu thực tế từ codebase (ví dụ: tốc độ xử lý của Gemini).
- [ ] Phải cân nhắc đến bài toán kinh tế (Free Tier API limits).
- [ ] Đề xuất phải mang tính thực tiễn cao cho dự án Novel Translator.
