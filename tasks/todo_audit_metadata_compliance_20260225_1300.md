# Project: Novel Translator - Quality Audit
# Date: 2026-02-25
# Task: Rà soát và sửa lỗi không tuân thủ metadata (HMQT).

## 🎯 Task Overview
**Vấn đề:** Một số chunk dịch không tuân thủ đầy đủ Glossary, Style Profile và Character Relations đã định nghĩa trong thư mục `data/metadata/HMQT`.
**Mục tiêu:** Tìm ra nguyên nhân tại sao AI "phớt lờ" chỉ dẫn và tối ưu hóa quy trình nhúng metadata vào Prompt để đảm bảo sự tuân thủ tuyệt đối.

## 📋 Plan

### Phase 1: Investigation (Phân tích Metadata & Code)
- [ ] **Đọc tệp metadata của HMQT:** Kiểm tra nội dung `glossary.csv`, `style_profile.json`, và `character_relations.csv` để hiểu các quy tắc đang áp dụng.
- [ ] **Rà soát `src/managers/`:** Phân tích cách `GlossaryManager`, `StyleManager`, và `RelationManager` tải và lọc dữ liệu.
- [ ] **Phân tích `src/translation/prompt_builder.py`:** Đây là khâu then chốt. Xem cách metadata được format và nhúng vào System/User Prompt.
- [ ] **Kiểm tra logic lọc thuật ngữ:** Xem hệ thống có lọc đúng các thuật ngữ xuất hiện trong chunk hiện tại hay không (để tránh làm loãng prompt).

### Phase 2: Root Cause Analysis (Xác định nguyên nhân)
- [ ] **Kiểm tra độ ưu tiên của Prompt:** Liệu các chỉ dẫn chung có đang "đè" lên quy tắc đặc thù trong metadata không?
- [ ] **Vấn đề Token Limit:** Nếu Glossary quá dài, liệu nó có bị cắt bớt hoặc làm AI bị "ngợp" (Lost in the Middle)?
- [ ] **Định dạng dữ liệu:** Xem định dạng nhúng (JSON vs CSV vs Plain Text) cái nào hiệu quả hơn cho Gemini.

### Phase 3: Implementation (Tối ưu hóa & Sửa lỗi)
- [ ] **Cải thiện Prompt Template:** Sử dụng các kỹ thuật như "Chain of Thought" hoặc "Instruction Anchoring" để buộc AI ưu tiên Glossary.
- [ ] **Tối ưu hóa Glossary Injection:** Chỉ nhúng các thuật ngữ thực sự có trong chunk (Relevant Glossary) nhưng với định dạng rõ ràng hơn.
- [ ] **Thêm bước Validation:** Cập nhật logic kiểm tra sau khi dịch để phát hiện vi phạm Glossary ngay lập tức.

### Phase 4: Verification (Kiểm chứng)
- [ ] **Chạy Test Prompt:** Sử dụng một chunk thực tế của HMQT và in ra prompt cuối cùng để kiểm tra bằng mắt.
- [ ] **Dịch thử nghiệm:** Chạy lại chunk bị lỗi và xác nhận các thuật ngữ đã được áp dụng đúng.

### Phase 5: Finalization
- [ ] Cập nhật `tasks/lessons.md`.
- [ ] Đánh dấu hoàn thành.

## 🔍 Quality Checklist
- [ ] Thuật ngữ trong Glossary phải được áp dụng chính xác 100%.
- [ ] Văn phong (Style) phải đồng nhất theo Profile.
- [ ] Cách xưng hô (Relations) phải khớp với bảng quan hệ nhân vật.
- [ ] Không làm tăng quá mức lượng token tiêu thụ không cần thiết.
