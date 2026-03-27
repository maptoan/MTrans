# Project: Novel Translator - Refactor
# Date: 2026-02-24
# Task: Tối ưu hóa việc áp dụng format tự động Heading 1, 2, 3 khi tạo ebook.

## 🎯 Task Overview
**Mục tiêu:** Refactor lại lớp `OutputFormatter` trong `src/output/formatter.py` để tự động phát hiện và áp dụng các style `Heading 1`, `Heading 2`, `Heading 3` cho các khối văn bản phù hợp khi tạo tệp `.docx`. Loại bỏ sự phụ thuộc vào các thẻ thủ công như `[H1]`.

## 📋 Plan

### Phase 1: Investigation & Planning (Đã hoàn thành)
- [x] Rà soát codebase để xác định module chịu trách nhiệm tạo file DOCX (`src/output/formatter.py`).
- [x] Phân tích logic hiện tại (dựa trên thẻ `[H1]`, `[H2]`).
- [x] Xây dựng bộ quy tắc (heuristics) để nhận diện heading tự động.
- [x] Lập kế hoạch chi tiết các bước thực hiện trong tệp này.

### Phase 2: Implementation
- [ ] **Tạo hàm nhận diện Heading:**
    - Trong `src/output/formatter.py`, tạo một phương thức private mới, ví dụ: `_detect_heading_level(self, line: str) -> int`.
    - Phương thức này sẽ trả về `1` cho Heading 1, `2` cho Heading 2, `3` cho Heading 3, và `0` cho văn bản thường.
    - **Quy tắc nhận diện:**
        - **Heading 1:**
            - Dòng bắt đầu bằng "Chương " theo sau là số.
            - Dòng bắt đầu bằng "Phần " theo sau là số hoặc chữ La Mã.
            - Dòng viết hoa toàn bộ và có ít hơn 10 từ.
        - **Heading 2:**
            - Dòng ngắn (dưới 15 từ), không có dấu câu kết thúc.
            - Viết hoa kiểu tiêu đề (Title Case).
            - Không phải là Heading 1.
        - **Heading 3:**
            - Dòng bắt đầu bằng các mẫu như `I.`, `II.`, `1.`, `a.`, `a)`.
            - Không phải là Heading 1 hoặc 2.
- [ ] **Cập nhật logic `save_as_docx`:**
    - Mở phương thức `save_as_docx` trong `formatter.py`.
    - Xóa bỏ logic cũ tìm kiếm thẻ `[H1]`, `[H2]`, `[H3]`.
    - Trong vòng lặp xử lý từng đoạn văn, gọi `_detect_heading_level()` để xác định cấp độ.
    - Dùng cấu trúc `if/elif/else` để áp dụng style phù hợp từ thư viện `python-docx`: `doc.add_paragraph(text, style='Heading 1')`.

### Phase 3: Verification
- [ ] **Chuẩn bị dữ liệu test:**
    - Tạo một tệp văn bản mới tại `data/input/test_headings.txt`.
    - Tệp này sẽ chứa nhiều định dạng khác nhau: tiêu đề chương, tiêu đề phụ, danh sách, và các đoạn văn thường để kiểm thử mọi trường hợp.
- [ ] **Thực thi:**
    - Cập nhật `config/config.yaml` để trỏ `novel_path` đến tệp `test_headings.txt`.
    - Chạy chương trình `main.py` để tạo file DOCX.
- [ ] **Kiểm tra kết quả:**
    - Mở tệp DOCX được tạo ra trong `data/output/`.
    - **Quan trọng:** Kiểm tra bằng mắt thường xem các style `Heading 1`, `Heading 2`, `Heading 3` và `Normal` có được áp dụng chính xác cho đúng các đoạn văn bản theo quy tắc đã định nghĩa hay không.
    - Báo cáo kết quả (chụp ảnh màn hình nếu có thể).

### Phase 4: Finalization & Cleanup
- [ ] Hoàn tác các thay đổi trong `config/config.yaml`.
- [ ] Xóa tệp test `test_headings.txt` nếu cần.
- [ ] Cập nhật lại `tasks/lessons.md` nếu có bất kỳ bài học hoặc sự điều chỉnh nào trong quá trình thực hiện.
- [ ] Đánh dấu task này là hoàn thành.

## 🔍 Quality Checklist
- [ ] Logic nhận diện heading phải chính xác và không áp dụng sai cho các đoạn văn thường.
- [ ] Các style `Heading 1`, `Heading 2`, `Heading 3` được áp dụng đúng trong file DOCX cuối cùng.
- [ ] Code mới phải sạch, dễ đọc và có comment giải thích các quy tắc nhận diện nếu cần.
- [ ] Không làm ảnh hưởng đến các chức năng khác của `OutputFormatter` (như tạo file TXT, EPUB).
