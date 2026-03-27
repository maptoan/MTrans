# Rà soát & Kế hoạch: Bảo lưu/Phục hồi layout EPUB đầu vào (text-based)

**Mục tiêu:** File ebook tạo ra phải bảo lưu/phục hồi được format layout của file input EPUB text-based.  
**Ngày:** 2026-03-14  
**Trạng thái:** Phân tích + Kế hoạch chi tiết.

---

## 1. Rà soát hiện trạng

### 1.1 Hai luồng xử lý khi input là EPUB

| Luồng | Điều kiện | Parser | Chunking | Output chính |
|-------|-----------|--------|----------|--------------|
| **A – Mặc định** | `preprocessing.epub.preserve_layout` = false hoặc không set | `file_parser.parse_epub()` | `SmartChunker.chunk_novel(cleaned_text)` | TXT tổng → (tùy chọn) pandoc TXT→EPUB |
| **B – Layout** | `preprocessing.epub.preserve_layout` = true | `epub_layout_parser.parse_epub_with_layout()` | `chunker_epub.build_chunks_from_text_map()` | Chỉ **master.html** (không ghi file .epub) |

### 1.2 Luồng A (mặc định) – Vì sao mất layout

- `parse_epub()` (và zip fallback) đọc spine → từng item XHTML → BeautifulSoup → **`get_text()`** từ từng block → ghép thành **một chuỗi `full_text`**.
- Toàn bộ cấu trúc (tag, class, id, ảnh, CSS) bị bỏ; không có mapping đoạn text ↔ node DOM.
- Chunking và merge chỉ làm việc với text thuần → output TXT → pandoc TXT→EPUB tạo EPUB **mới** từ markdown/plain, **không** phục hồi layout gốc.

**Kết luận:** Ở luồng A, layout không thể phục hồi vì thông tin layout đã bị loại bỏ ngay từ bước parse.

### 1.3 Luồng B (preserve_layout) – Đã giữ DOM nhưng chưa xuất EPUB đúng

- Parser: `parse_epub_with_layout()` → **TEXT_MAP** (text_id, chapter_id, original_text) + **chapters_html** (chapter_id → HTML đã gán `data-ntid`).
- Chunker: `build_chunks_from_text_map()` → chunks có `text_ids` và delimiter `[TX:id]`.
- Sau dịch: `build_translation_map_from_chunks()` → `translation_map` (text_id → bản dịch).
- Re-inject: `apply_translations_to_chapters()` + `build_html_master()` → **một file HTML** (master.html) gộp tất cả chương.

Điểm thiếu sót:

1. **Không ghi file .epub** trong nhánh finalize. Chỉ ghi `master_path` (master.html). Để có EPUB, user phải chọn Option 4 → `export_master_html_to_epub()` → **pandoc convert 1 file HTML → EPUB**.
2. Pandoc HTML→EPUB tạo EPUB từ **một** document HTML; không tạo **một file XHTML per chapter** như EPUB gốc, không copy **CSS/ảnh/font** từ EPUB gốc.
3. **CSS/ảnh/font của EPUB gốc** không được đưa vào output. `build_html_master()` tạo HTML tối giản (meta, title, `<main>`, `<section>`), không tham chiếu đến styles hay assets của EPUB gốc.

**Kết luận:** Luồng B đã giữ được cấu trúc DOM (thẻ, section) và re-inject đúng theo text_id, nhưng **thiếu bước xuất EPUB “đúng kiểu”**: nhiều file XHTML (một chương một file) + copy manifest/CSS/images từ EPUB gốc. Hiện chỉ xuất một master.html rồi dùng pandoc → layout “giống sách” nhưng không phải layout **file-per-chapter + assets** của EPUB gốc.

---

## 2. Nguyên nhân gốc rễ (tóm tắt)

| # | Nguyên nhân | Luồng | Mô tả ngắn |
|---|-------------|--------|------------|
| 1 | Parse chỉ lấy plain text, vứt DOM | A | `parse_epub()` / zip fallback chỉ xuất `full_text` → mất hết cấu trúc. |
| 2 | Output chỉ TXT rồi pandoc TXT→EPUB | A | EPUB ra từ markdown/plain, không phải từ DOM gốc. |
| 3 | Layout branch không ghi .epub | B | Finalize chỉ lưu master.html; không có bước ghi file .epub từ chapters + assets. |
| 4 | EPUB từ master = pandoc 1 HTML → 1 EPUB | B | Cấu trúc “một file XHTML per chapter” và assets gốc không được tái tạo. |
| 5 | Assets gốc (CSS, ảnh, font) không copy | B | Không có logic copy manifest/CSS/images từ EPUB gốc sang EPUB dịch. |

---

## 3. Thảo luận & phản biện phương án

### 3.1 Phương án 1: Chỉ sửa luồng A (parse EPUB giữ cấu trúc nhẹ)

- **Ý tưởng:** Khi input EPUB, luôn dùng parser kiểu “layout” (TEXT_MAP + chapters_html), nhưng vẫn chunk giống hiện tại (chỉ dùng full_text_flat) và output như cũ (TXT + pandoc TXT→EPUB).
- **Phản biện:** Không đủ. TXT và pandoc TXT→EPUB vẫn không mang theo cấu trúc chương/đoạn/class; chỉ có thêm dữ liệu TEXT_MAP/chapters_html mà không dùng đến khi xuất. **Bỏ.**

### 3.2 Phương án 2: Chỉ cải thiện master.html → EPUB (pandoc)

- **Ý tưởng:** Giữ nguyên luồng B, cải thiện cấu trúc HTML (h1 trực tiếp dưới body, `--epub-chapter-level=1`) và/hoặc CSS để pandoc tạo EPUB “đẹp hơn”.
- **Phản biện:** Có thể cải thiện trải nghiệm đọc, nhưng **không** đạt “bảo lưu layout file input”: vẫn một (hoặc vài) file nội dung do pandoc sinh, không phải “cùng số file XHTML, cùng manifest, cùng CSS/ảnh như gốc”. **Không đủ cho mục tiêu “phục hồi layout”.**

### 3.3 Phương án 3: Xuất EPUB từ chapters + copy assets (đúng với PLAN Phase 4)

- **Ý tưởng:** Trong luồng B, sau khi có `translated_chapters` (chapter_id → HTML đã dịch):
  - Tạo EPUB mới (ebooklib hoặc zip) với **một item XHTML per chapter** (spine giữ thứ tự gốc).
  - **Copy** từ EPUB gốc: CSS, images, fonts (theo manifest), container/package cơ bản; chỉ thay nội dung các file XHTML bằng HTML đã reinject.
- **Ưu điểm:** Layout “file-per-chapter” và assets gốc được bảo lưu; output EPUB gần với cấu trúc input. Đúng với mục tiêu “bảo lưu/phục hồi format layout”.
- **Rủi ro:** Cần xử lý manifest/spine đúng, encoding, và các item không phải XHTML (nav, toc, cover). Có thể làm từng bước: trước mắt chỉ thay thế các spine item là XHTML đã có trong `chapters_html`, giữ nguyên item khác (nav, toc, cover, CSS, images).

**Kết luận:** Đây là **phương án tối ưu** để đạt mục tiêu: kết hợp luồng B hiện có + bước xuất EPUB “structure-preserving” + copy assets.

### 3.4 Phương án 4: Luôn dùng luồng B khi input là EPUB

- **Ý tưởng:** Khi input là .epub, luôn bật preserve_layout (hoặc bỏ config, mặc định true cho .epub).
- **Phản biện:** Có thể làm tùy chọn (config) vì một số user có thể chỉ cần “dịch nhanh ra TXT/EPUB đơn giản” không cần giữ layout. **Giữ config** `preprocessing.epub.preserve_layout`; mặc định có thể để `true` cho .epub nếu product muốn ưu tiên layout.

---

## 4. Phương án tối ưu (đề xuất)

- **Giữ nguyên** luồng A khi `preserve_layout` = false (hoặc input không phải .epub).
- **Bổ sung** vào luồng B:
  1. **Xuất EPUB “structure-preserving”** từ `translated_chapters` + EPUB gốc:
     - Đọc lại EPUB gốc (ebooklib hoặc zip).
     - Với mỗi spine item là document (XHTML): nếu có trong `translated_chapters` thì dùng HTML đã dịch; không thì giữ nội dung gốc (hoặc bỏ qua nếu không nằm trong TEXT_MAP).
     - Copy toàn bộ item không phải document (CSS, images, fonts, nav, toc, …) từ EPUB gốc.
     - Ghi EPUB mới (ebooklib hoặc zip) với metadata có thể cập nhật (title, language, v.v.).
  2. **Tùy chọn:** Vẫn ghi **master.html** như hiện tại (để Option 4 pandoc vẫn dùng được).
  3. **Config:** Ví dụ `output.epub_reinject.output_epub: true`, `output.epub_reinject.output_html_master: true`, đường dẫn thư mục xuất EPUB.

Như vậy:
- **Input EPUB (text-based) + preserve_layout = true** → output có **EPUB dịch giữ layout** (file-per-chapter + assets) + optional master.html.
- **Input TXT/DOCX/PDF** hoặc **EPUB với preserve_layout = false** → hành vi như hiện tại (TXT ± pandoc TXT→EPUB).

---

## 5. Kế hoạch chi tiết (implementation)

### 5.1 Cấu hình (config)

Thêm/chuẩn hóa trong `config.yaml`:

```yaml
preprocessing:
  epub:
    preserve_layout: true   # Khi input .epub: true = giữ layout (TEXT_MAP + xuất EPUB structure-preserving)

output:
  epub_reinject:
    output_epub: true       # Ghi file .epub từ chapters + copy assets (luồng B)
    output_html_master: true
    epub_output_dir: ""    # Để trống = dùng output_path hoặc progress_dir
```

### 5.2 Module / file

| Công việc | Vị trí | Mô tả |
|-----------|--------|--------|
| **EPUB writer từ chapters** | `src/output/epub_reinject.py` (hoặc `epub_writer.py`) | Hàm mới: `write_epub_from_translated_chapters(original_epub_path, translated_chapters: Dict[str, str], metadata, output_epub_path, options)`. Đọc EPUB gốc (ebooklib), thay nội dung các item tương ứng chương bằng HTML đã dịch, copy mọi item khác (CSS, images, fonts, nav, toc), ghi EPUB mới. |
| **Gọi writer trong finalize** | `src/translation/translator.py` | Trong nhánh `_epub_preserve_layout and _epub_layout_state`: sau khi có `translated_chapters` và (tùy chọn) đã ghi master.html, nếu `output.epub_reinject.output_epub` = true thì gọi `write_epub_from_translated_chapters(...)`, dùng `original_epub_path = self.novel_path`, output path từ config. |
| **Config & default** | `config/config.yaml` | Thêm `preprocessing.epub.preserve_layout`, `output.epub_reinject.output_epub`, `output_epub_output_dir`, v.v. |
| **Fallback khi thiếu bản dịch** | `epub_reinject` / writer | Với chapter có trong spine nhưng không có trong `translated_chapters` (hoặc HTML rỗng): giữ nguyên nội dung gốc từ EPUB và log warning. |

### 5.3 Chi tiết kỹ thuật `write_epub_from_translated_chapters`

- **Đọc EPUB gốc:** `ebooklib.epub.read_epub(original_epub_path)`.
- **Spine:** Duyệt `book.spine` theo thứ tự. Với mỗi `itemref`:
  - Lấy item (get_item_with_id).
  - Nếu là document (application/xhtml+xml hoặc text/html): nếu `item.get_name()` (hoặc id) có trong `translated_chapters` thì thay content bằng `translated_chapters[chapter_id]` (encode UTF-8); không thì giữ content gốc.
  - Nếu không phải document (image, css, font, nav, toc): thêm vào book mới nguyên bản (hoặc copy bytes).
- **Tạo EPUB mới:** Tạo `epub.EpubBook()` mới; thêm từng item (đã thay nội dung hoặc copy); set spine, metadata; `epub.write_epub(output_epub_path, book)`.
- **Lưu ý:** ebooklib có thể đọc/sửa từng item; cần map đúng `chapter_id` (tên file, ví dụ `chapter1.xhtml`) với key trong `translated_chapters` (đã dùng trong `parse_epub_with_layout` là `item.get_name() or itemref`).

### 5.4 Thứ tự triển khai (đề xuất)

1. **Bước 1:** Thêm config `preprocessing.epub.preserve_layout`, `output.epub_reinject.output_epub`, `epub_output_dir` (và đọc trong translator).
2. **Bước 2:** Implement `write_epub_from_translated_chapters` trong `src/output/epub_reinject.py` (đọc EPUB gốc, thay content từng document tương ứng chương, copy item khác, ghi EPUB). Unit test: mock EPUB 1 chương + 1 translated_chapters → kiểm tra file ra là EPUB và chứa nội dung đã dịch.
3. **Bước 3:** Trong `_finalize_translation`, sau khi có `translated_chapters` và (nếu bật) đã ghi master.html, gọi `write_epub_from_translated_chapters` khi `output.epub_reinject.output_epub` = true; set `original_epub_path = self.novel_path`, output path từ config (mặc định có thể `output_path` hoặc `progress_dir`).
4. **Bước 4:** Kiểm tra end-to-end: input EPUB (2–3 chương) + preserve_layout true → dịch → kiểm tra file .epub ra: mở bằng reader, so sánh cấu trúc (số chương, styles, ảnh) với gốc.
5. **Bước 5 (tùy chọn):** Cập nhật UI/option (ví dụ thông báo “Đã xuất EPUB layout tại …” khi dùng Option 4 hoặc sau khi finalize).

### 5.5 Rủi ro và giảm thiểu

| Rủi ro | Giảm thiểu |
|--------|------------|
| EPUB gốc dùng cấu trúc phức tạp (nested, nhiều file) | Phase 1 chỉ thay thế item có trong spine và có trong `chapters_html`; item khác copy nguyên. |
| Encoding / BOM / XML declaration | Ghi nội dung XHTML với encoding UTF-8 và declaration phù hợp khi thay content. |
| Nav/TOC trỏ đến id chương | Giữ nguyên file nav/toc từ gốc (copy); hoặc sau này cập nhật nếu cần. |
| Model xóa delimiter [TX:id] | Đã có trong PLAN: prompt giữ marker; fallback split theo thứ tự/độ dài trong `build_translation_map_from_chunks`. |

---

## 6. Checklist hoàn thành (tóm tắt)

- [x] Config: `preprocessing.epub.preserve_layout`, `output.epub_reinject.output_epub`, `epub_output_dir` (đã thêm trong config.yaml).
- [x] `write_epub_from_translated_chapters(...)` trong `src/output/epub_reinject.py`.
- [x] Finalize (translator): gọi writer khi layout branch + output_epub = true.
- [x] Unit test: `test_write_epub_from_translated_chapters` trong test_epub_reinject_phase4.
- [x] Integration: test_epub_integration_phase5, test_integration_master_txt_pipeline.
- [ ] Doc: cập nhật README hoặc WORKFLOW nêu rõ “input EPUB + preserve layout → output EPUB giữ layout (file-per-chapter + assets)”.

---

**Kết luận:** Nguyên nhân ebook tạo ra không bảo lưu/phục hồi layout EPUB input là (1) luồng mặc định bỏ hết cấu trúc khi parse; (2) luồng layout chỉ xuất master.html và dựa vào pandoc 1 HTML→EPUB nên không tái tạo cấu trúc file-per-chapter và assets. Phương án tối ưu là bổ sung bước **xuất EPUB từ translated_chapters + copy assets từ EPUB gốc** trong luồng preserve_layout, và gọi bước này trong finalize khi config bật. Kế hoạch trên đủ để triển khai từng bước theo đúng mục tiêu.
