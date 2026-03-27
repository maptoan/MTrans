# Walkthrough - Phase 7.5: Enhanced Quality Control (v6.0)

Bản cập nhật v6.0 tập trung vào việc nâng cao chất lượng dịch thuật thông qua quy trình **Biên tập chuyên sâu (Specialized QA Pipeline)** và kiểm soát xưng hô nhân vật.

## 1. Luồng QA Editor Bắt buộc (Mandatory QA Pass)
Trước đây, QA Editor chỉ chạy khi phát hiện lỗi CJK sót. Giờ đây, khi bật `qa_editor: enabled: true`, mọi chunk đều đi qua bước biên tập.

### **Kết quả mong đợi:**
- **Draft Stage:** AI tập trung dịch sát nghĩa nhất.
- **QA Stage:** Một AI "Senior Editor" rà soát lại toàn bộ bản dịch, sửa lỗi chính tả, chuẩn hóa văn phong và kiểm tra glossary.

## 2. Kiểm soát xưng hô thông minh (Character Addressing)
Hệ thống tích hợp `RelationManager` để tìm nạp các quy tắc xưng hô cụ thể cho các nhân vật xuất hiện trong văn bản.

### **Ví dụ thực tế:**
- **Source:** "Qi Ji said to Lu Chen: 'Brother, come here.'"
- **Metadata:** Qi Ji gọi Lu Chen là "Huynh".
- **QA fix:** Đảm bảo bản dịch là "Kỳ Cơ nói với Lục Trần: 'Huynh, lại đây.'" thay vì dùng "Anh" hoặc "Cậu" ngẫu nhiên.

## 3. Cơ chế Khắc phục lỗi (Robust QA Retry)
QA Editor giờ đây không còn là "điểm chết" của hệ thống nếu gặp lỗi API.

### **Cơ chế:**
- Nếu call QA fail (429, Quota, v.v.), hệ thống sẽ:
  1. Đánh dấu key hiện tại là bị lỗi.
  2. Lấy **Key mới (Rotation)** từ pool.
  3. Thử lại tối đa 3 lần.

## 4. Tích hợp Antigravity Kit
Bộ kỹ năng mới giúp việc debug và phát triển nhanh hơn:
- `/debug`: Gỡ lỗi hệ thống.
- `/enhance`: Nâng cấp tính năng.
- `/test`: Chạy và tạo test cases.

---
*Tham khảo [README.md](./README.md) và [CHANGELOG.md](./CHANGELOG.md) để biết thêm chi tiết.*
