# Rà soát thuật toán: Bảo lưu / Phục hồi / Tạo layout và format cho master.html → EPUB

**Vấn đề:** EPUB tạo từ nguồn master.html không có khác biệt so với file TXT tổng.

---

## 1. Luồng hiện tại

| Bước | Vị trí | Mô tả |
|------|--------|--------|
| 1 | `translator._finalize_translation` | `full_content = await _merge_all_chunks(...)` (nội dung ghép từ chunks, **chưa** chuẩn hóa). |
| 2 | `output_formatter.save(full_content, novel_name)` | Gọi `_normalize_paragraphs(full_content)` → thêm/bọc **[H1]/[H2]/[H3]** theo mẫu tiêu đề → ghi **TXT**. File TXT trên đĩa **có** marker. |
| 3 | `build_html_master_from_flat_text(full_content, novel_name)` | Nhận **cùng** `full_content` gốc (chưa normalize) → parse theo `[H1]...[/H1]` → build HTML. |
| 4 | Option 4 / `export_master_html_to_epub` | Đọc file master.html → pandoc `convert_file(html, format="html", to="epub")`. |

---

## 2. Lỗi chính (nguồn nội dung master.html)

### 2.1 Master.html dùng nội dung **chưa** chuẩn hóa

- **TXT lưu:** `save()` dùng `content = _normalize_paragraphs(full_content)` rồi mới ghi file → file TXT **có** `[H1]...[/H1]`.
- **Master.html:** Gọi `build_html_master_from_flat_text(full_content, ...)` với **full_content gốc** (trước normalize).

Hệ quả:

- Nếu merge/chunk **không** trả về sẵn dòng dạng `[H1]...[/H1]` (chỉ có "Chương 1", "Hồi 2", v.v.) thì `build_html_master_from_flat_text` **không** tìm thấy H1.
- Khi không có H1: toàn bộ nội dung rơi vào **một** block → một `<section>` duy nhất hoặc không tách chương → HTML gần như một khối văn bản → EPUB từ master giống TXT phẳng.

**Kết luận:** Cần dùng **cùng nội dung đã chuẩn hóa** (sau `_normalize_paragraphs`) cho cả lưu TXT và build master.html.

---

## 3. Thuật toán build_html_master_from_flat_text

### 3.1 Đúng

- Parse theo dòng; dòng **một dòng** `[H1]...[/H1]` → bắt đầu section mới.
- Mỗi section → `<section id="chapter-{idx}">`, bên trong `<h1 data-role="chapter-title">` + các `<p>`.
- Skeleton: `<!DOCTYPE html>`, `<main id="nt-content">`, lang, meta, title.

### 3.2 Hạn chế

- **Chỉ nhận diện H1** (một dòng, bắt đầu `[H1]` và kết thúc `[/H1]`). **[H2]/[H3]** không được map sang `<h2>`/`<h3>` → mất cấu trúc con (tập, phần nhỏ).
- **H1 nhiều dòng:** Nếu `[H1]` và `[/H1]` nằm trên hai dòng khác nhau, điều kiện `stripped.startswith("[H1]") and stripped.endswith("[/H1]")` sai → không nhận là tiêu đề.
- **Regex an toàn:** Có thể dùng regex `\[H1\](.*?)\[/H1\]` (kể cả multiline nếu cần) để tránh lệ thuộc “một dòng”.

---

## 4. Pandoc HTML → EPUB

- Tài liệu / cộng đồng: Pandoc thường dùng **heading trực tiếp dưới body** để tách chương (ví dụ `<body><h1>...</h1>...`).
- Hiện tại: Cấu trúc là `body > main#nt-content > section > h1, p...` → h1 **nằm trong** main/section. Một số phiên bản/option pandoc có thể vẫn nhận diện `<h1>` để tạo ToC nhưng **có thể không** tách file chương theo `<section>`.
- Hệ quả: Dù master.html có nhiều `<section><h1>`, EPUB vẫn có thể ra **một** file XHTML (một “chương” lớn) → cảm giác giống đọc TXT.

Đề xuất (tùy chọn sau): Thử pandoc với `--epub-chapter-level=1` hoặc cấu trúc HTML đơn giản hơn (ví dụ h1 là con trực tiếp của body) nếu cần tách chương rõ trong EPUB.

---

## 5. So sánh TXT → EPUB và HTML (master) → EPUB

- **TXT → EPUB:** `convert_txt_to_epub` đọc TXT (đã có [H1]/[H2]/[H3]), thay `[H1]` → `# \1` (markdown), rồi pandoc `convert_text(..., format="markdown+hard_line_breaks", to="epub")` → pandoc tạo heading và có thể tách chương từ markdown.
- **Master → EPUB:** Đầu vào là HTML. Nếu master chỉ có một khối (do thiếu [H1] ở bước build) thì nội dung EPUB từ master sẽ phẳng; nếu cấu trúc section không được pandoc dùng để tách file thì kết quả cũng gần giống một file duy nhất.

→ **Khác biệt không thấy** là do: (1) master được build từ nội dung **không** có [H1], và/hoặc (2) pandoc không tách chương theo `<section>` của chúng ta.

---

## 6. Hành động đề xuất

| Ưu tiên | Hành động |
|--------|-----------|
| **P0** | Dùng **nội dung đã chuẩn hóa** (sau `_normalize_paragraphs`) cho `build_html_master_from_flat_text`: trong `_finalize_translation` lấy `normalized_content = self.output_formatter._normalize_paragraphs(full_content)`, dùng cho cả `save(normalized_content, ...)` và `build_html_master_from_flat_text(normalized_content, ...)`. |
| P1 | (Tùy chọn) Hỗ trợ **[H2]/[H3]** trong `build_html_master_from_flat_text`: map sang `<h2>`/`<h3>` trong section tương ứng. |
| P2 | (Tùy chọn) Cho phép H1 nhiều dòng (regex `\[H1\](.*?)\[/H1\]` với DOTALL). |
| P3 | (Tùy chọn) Kiểm tra pandoc: thử `--epub-chapter-level=1` hoặc cấu trúc HTML với `<h1>` trực tiếp dưới `<body>` để EPUB tách chương đúng. |

---

## 7. Đã sửa (P0)

- Trong `translator._finalize_translation`: tính `normalized_content = self.output_formatter._normalize_paragraphs(full_content)` một lần; dùng cho cả `save(normalized_content, ...)` và `build_html_master_from_flat_text(normalized_content, ...)`. Master.html giờ được build từ cùng nội dung có marker [H1] như file TXT → nhiều `<section>` tương ứng chương → EPUB từ master có cấu trúc chương khác với TXT phẳng.

---

## 8. Files liên quan

- `src/translation/translator.py`: `_finalize_translation` (merge → save → build master).
- `src/output/formatter.py`: `save()`, `_normalize_paragraphs()`.
- `src/output/html_master_builder.py`: `build_html_master_from_flat_text()`.
- `src/output/html_exporter.py`: `export_master_html_to_epub()` (pandoc).
