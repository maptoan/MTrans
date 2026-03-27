# Kế hoạch chi tiết: Giữ format và layout từ EPUB gốc (TEXT_ID + DOM re-injection)

**Mục tiêu:** Dịch nội dung sách nhưng **giữ 100% format/layout EPUB gốc** (tiêu đề, đoạn, in đậm, bảng, ảnh, CSS).  
**Phương án:** Trích text gắn TEXT_ID → dịch theo chunk (text thuần) → bơm bản dịch lại vào DOM → xuất EPUB/HTML.

**Ngày lập:** 2026-03-14  
**Trạng thái:** Kế hoạch – chưa triển khai.

---

## 1. Hiện trạng (để so sánh)

| Bước | Hiện tại | Hạn chế |
|------|----------|--------|
| **Input EPUB** | `file_parser.parse_epub()` / zip fallback: đọc spine → BeautifulSoup → `get_text()` từ từng block (`p`, `div`, `h1`…) → ghép chapter → **một chuỗi `full_text`** | Mất hết cấu trúc (tag, class, ảnh). Không biết đoạn nào ứng với element nào. |
| **Chunking** | `SmartChunker.chunk_novel(cleaned_text)` → danh sách chunk `{ global_id, text, text_original, tokens }` | Chunk chỉ là đoạn text, không gắn với DOM. |
| **Dịch** | Dịch từng chunk (text + marker), lưu bản dịch theo `chunk_id`. | Ổn định, giữ nguyên. |
| **Merge** | Nối bản dịch theo thứ tự `global_id` → một chuỗi `full_content`. | Chỉ có chuỗi thuần. |
| **Output** | Lưu TXT → (tùy chọn) `pandoc` TXT → EPUB. | EPUB mới **không** giữ layout gốc (mất heading/paragraph/style). |

---

## 2. Kiến trúc mới (tóm tắt)

```
EPUB gốc
   → [Parser EPUB v2] → DOM từng chương + TEXT_MAP (text_id, chapter_id, order, text, node_ref)
   → [Chunker EPUB]   → Chunks vẫn (global_id, text_original, text) + metadata: text_ids[], delimiter
   → [Translator]     → Không đổi: dịch chunk, marker, CJK, retry
   → [Split & Map]    → Từ bản dịch chunk + text_ids → Map: text_id → translated_text
   → [Re-inject]      → Clone DOM từng chương, thay text node theo text_id → HTML/EPUB
   → Output: EPUB dịch (layout như gốc) + optional HTML master
```

---

## 3. Cấu trúc dữ liệu chuẩn

### 3.1. TEXT_MAP (bảng text trích từ EPUB)

Dùng khi **input là EPUB** và bật chế độ giữ layout.

| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `text_id` | str | ID duy nhất toàn cục, ví dụ `c1_p003_002` (chapter 1, block thứ 3, text node thứ 2) hoặc `TEXT-000001`. |
| `chapter_id` | str | ID chương trong EPUB (spine idref hoặc file name), ví dụ `ch01.xhtml`. |
| `order` | int | Thứ tự trong chương (0, 1, 2, …). |
| `original_text` | str | Nội dung text gốc (đã strip). |
| `node_ref` | str hoặc dict | Tham chiếu để tìm lại node khi re-inject: có thể là `css_selector`, hoặc `(xpath, position)` hoặc id/attribute ta gán vào DOM. |
| `tag_name` | str (optional) | Tag gốc (`p`, `h1`, `span`, …) để log/debug. |

Lưu trữ: list of dict, hoặc DataFrame; có thể kèm theo từng chapter (ví dụ `TEXT_MAP[chapter_id] = [entry, ...]`).

### 3.2. Chunk (chế độ EPUB layout)

Ngoài các trường hiện có (`global_id`, `text`, `text_original`, `tokens`, `type`), thêm:

| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `text_ids` | List[str] | Danh sách `text_id` theo thứ tự nằm trong chunk này. |
| `text_delimiter` | str | Chuỗi dùng để nối/ tách giữa các đoạn trong chunk, ví dụ `\n[TID:{}]\n` với placeholder cho text_id. |

Cách dựng `text_original` cho chunk:

- Nối: `original_1 + text_delimiter.format(id1) + original_2 + text_delimiter.format(id2) + ...`
- Khi gửi model: có thể dùng delimiter “vô hình” đơn giản (ví dụ `\n\u200B\u200B\n` U+200B zero-width space x2) và lưu mapping `chunk_id -> [(text_id, length)]` để split theo độ dài tương đối nếu cần; hoặc dùng delimiter có `[TID:id]` để split chính xác sau khi dịch.

Khuyến nghị: dùng **delimiter có chứa text_id** (ví dụ `\n[TX:id123]\n`) để sau khi dịch ta split bằng regex và map 1-1 với `text_ids`.

### 3.3. Bản dịch theo TEXT_ID

Sau khi dịch xong từng chunk:

- Với mỗi chunk: split bản dịch theo delimiter → danh sách chuỗi (theo thứ tự).
- Zip với `chunk["text_ids"]` → `(text_id, translated_text)`.
- Gộp vào một map: `translation_by_text_id: Dict[str, str]`.

---

## 4. Các module / thay đổi theo từng phase

### Phase 0: POC (Proof of Concept)

**Mục đích:** Kiểm chứng end-to-end trên 1 EPUB nhỏ (1–2 chương).

**Công việc:**

1. Chọn 1 file EPUB mẫu (ít chương, ít ảnh).
2. Viết script độc lập (không nhúng vào Novel Translator):
   - Parse EPUB (ebooklib hoặc zip) → với 1 chương: giữ BeautifulSoup/DOM, duyệt mọi text node (hoặc block element), gán `data-tid="TEXT-001"`, …; build TEXT_MAP (text_id, original_text, node_ref đơn giản).
   - Tạo 1 “chunk” giả gồm toàn bộ text của chương (hoặc vài block), format có delimiter `[TX:id]\n`.
   - Gọi 1 lần dịch (mock hoặc API thật) → nhận bản dịch.
   - Split bản dịch theo `[TX:id]` → map text_id → translated.
   - Clone DOM chương đó, thay nội dung từng node có `data-tid` bằng bản dịch tương ứng.
   - Ghi ra 1 file HTML (chương dịch). So sánh với HTML gốc: layout giữ nguyên, chỉ đổi ngôn ngữ.

**Kết quả kỳ vọng:** Một file HTML 1 chương có layout giống gốc, nội dung đã dịch. Không cần tích hợp pipeline.

**Thư mục / file gợi ý:** `tools/poc_epub_layout/` (script + 1 EPUB mẫu trong `data/input/`).

---

### Phase 1: Parser EPUB v2 (TEXT_MAP + DOM)

**Mục đích:** Khi input là EPUB, có thể lấy (1) full text phẳng (như cũ) **hoặc** (2) TEXT_MAP + DOM từng chương để giữ layout.

**Công việc:**

1. **Module mới:** `src/preprocessing/epub_layout_parser.py` (hoặc mở rộng `file_parser` với nhánh “layout mode”).
   - Đọc EPUB (ebooklib + fallback zip như hiện tại).
   - Với mỗi spine item (XHTML):
     - Parse thành DOM (BeautifulSoup hoặc lưu raw HTML).
     - Duyệt từng phần tử chứa text (ví dụ `p`, `h1`–`h6`, `li`, `blockquote`, `td`, …; có thể cấu hình).
     - Với mỗi element: lấy `get_text()` làm một bản ghi TEXT_MAP; sinh `text_id` (ví dụ `{chapter_ref}_{index}`); lưu `node_ref` (ví dụ tag + index, hoặc gán `data-tid` vào bản copy DOM).
   - Trả về:
     - `full_text_flat`: nối toàn bộ `original_text` (để tương thích cũ / fallback).
     - `text_map`: List[dict] như mục 3.1.
     - `chapters_dom`: Dict[chapter_id, DOM hoặc HTML string] – DOM đã gán `data-tid` cho từng node tương ứng.
   - Metadata: giữ như hiện tại (title, author, chapter_count, …).

2. **Cấu hình:** Trong `config`, ví dụ:
   - `preprocessing.epub.preserve_layout: true/false` (mặc định false để không đổi hành vi hiện tại).
   - Khi `preserve_layout: true` và `format == "epub"`, pipeline dùng output (2) thay vì chỉ `full_text_flat`.

3. **Tests:** Unit test: cho 1 file XHTML mẫu, parse ra TEXT_MAP và kiểm tra số lượng bản ghi, `text_id` duy nhất, `original_text` khớp với nội dung.

**Rủi ro:** Một số EPUB dùng cấu trúc phức tạp (nested div, span). Có thể chỉ extract ở level block (p, h*, li) trước; span/strong/em giữ trong 1 block gộp chung, vẫn đúng với “chỉ thay text trong node”.

---

### Phase 2: Chunker chế độ EPUB (text_ids + delimiter)

**Mục đích:** Từ TEXT_MAP tạo ra chunks giống format hiện tại nhưng có thêm `text_ids` và dùng delimiter trong `text_original` để sau dịch có thể tách lại theo từng text_id.

**Công việc:**

1. **Module mới hoặc mode trong SmartChunker:** ví dụ `chunk_from_text_map(text_map, config)`.
   - Input: `text_map` (list dict có `text_id`, `original_text`, `chapter_id`, `order`).
   - Logic: ghép liên tiếp các `original_text` thành “đoạn” theo giới hạn token (dùng cùng `max_chunk_tokens` / logic hiện tại). Mỗi lần gộp thêm một bản ghi TEXT_MAP thì thêm `text_id` vào list và nối text với delimiter.
   - Delimiter đề xuất: `\n[TX:{text_id}]\n` (model có thể giữ nguyên hoặc bỏ; nếu bỏ thì cần fallback split theo thứ tự text_ids và độ dài tương đối).
   - Output: list chunk dict: `global_id`, `text_original`, `text` (có marker chunk như hiện tại), `tokens`, `text_ids`, `text_delimiter` (pattern).

2. **Tích hợp:** Khi `preserve_layout` và có `text_map`, `_prepare_translation()` (hoặc bước tương đương) gọi `chunk_from_text_map(...)` thay vì `chunker.chunk_novel(cleaned_text)`. Cần truyền thêm `text_map` và `chapters_dom` (hoặc đường dẫn lưu DOM) xuống các bước sau.

3. **Tests:** Cho TEXT_MAP giả (5–10 bản ghi), chunk với max_tokens nhỏ → kiểm tra mỗi chunk có `text_ids`, và nối lại từ `text_original` + split bằng delimiter thì ra đúng từng đoạn tương ứng text_id.

---

### Phase 3: Post-translation: Chunk → Map text_id → bản dịch

**Mục đích:** Từ bản dịch từng chunk (đã lưu trong progress_manager / completed_chunks) và metadata `text_ids` + delimiter, xây dựng `translation_by_text_id: Dict[str, str]`.

**Công việc:**

1. **Module hoặc hàm:** ví dụ `build_translation_map_from_chunks(all_chunks, completed_translations, delimiter_pattern)`.
   - Với mỗi chunk: lấy bản dịch tương ứng (từ `completed_chunks` hoặc `translated_chunks_map`).
   - Split bản dịch theo delimiter (regex `\[TX:([^\]]+)\]` hoặc tương đương). Nếu số phần sau split ≠ len(text_ids), dùng fallback: chia đều theo số lượng text_ids (theo ký tự hoặc theo dòng).
   - Gán `translation_by_text_id[text_id] = translated_segment`.
   - Trả về dict.

2. **Lưu ý:** Prompt có thể yêu cầu model “giữ nguyên chuỗi [TX:xxx] trong bản dịch” để split chính xác. Nếu không, fallback split theo thứ tự và độ dài tương đối so với bản gốc.

3. **Tests:** Với 2 chunk giả, mỗi chunk có 2 text_ids, bản dịch giả có chèn đúng delimiter → kiểm tra `build_translation_map_from_chunks` trả về đúng 4 cặp text_id → translated.

---

### Phase 4: Re-inject vào DOM và xuất EPUB / HTML

**Mục đích:** Clone DOM từng chương, thay nội dung text node theo `translation_by_text_id`, rồi ghi EPUB (hoặc HTML master).

**Công việc:**

1. **Module mới:** `src/output/epub_reinject.py` (hoặc nằm trong `output/`).
   - Hàm chính: `reinject_translations_into_epub(epub_path_original, translation_by_text_id, chapters_dom_or_path, output_epub_path, options)`.
   - Với mỗi chương: load DOM (từ `chapters_dom` đã lưu hoặc đọc lại từ EPUB), duyệt mọi node có `data-tid` (hoặc node_ref tương đương), lấy `translation_by_text_id[tid]` và gán lại `node.string` / `node.replace_with` text đã dịch (escape HTML nếu cần).
   - Xuất:
     - **EPUB:** Ghi lại các file XHTML đã sửa + copy nguyên manifest/CSS/images vào EPUB mới (zip), cập nhật metadata nếu cần. Có thể dùng ebooklib để tạo EPUB từ các item đã chỉnh.
     - **HTML master:** Gộp toàn bộ chương thành một file HTML (template với `<head>` + CSS, từng chương trong `<section>`), ảnh có thể giữ link tương đối hoặc base64 (tùy chọn sau).

2. **Xử lý thiếu bản dịch:** Nếu một `text_id` không có trong `translation_by_text_id` (chunk failed), giữ nguyên text gốc và log warning.

3. **Tests:** Cho 1 file HTML + 1 dict text_id → translated, reinject vào bản copy HTML → so sánh DOM: chỉ nội dung text thay đổi, tag và structure giữ nguyên.

---

### Phase 5: Tích hợp vào luồng Translator

**Mục đích:** Khi input là EPUB và bật `preserve_layout`, toàn bộ luồng dùng TEXT_MAP → chunk (có text_ids) → dịch → build translation map → re-inject → output EPUB/HTML; vẫn tương thích với resume, retry, partial.

**Công việc:**

1. **Điều kiện rẽ nhánh:** Trong `_prepare_translation()` (hoặc nơi gọi parse + chunk):
   - Nếu `novel_path` kết thúc bằng `.epub` và config `preprocessing.epub.preserve_layout` (hoặc tương đương) = true:
     - Gọi parser EPUB v2 → nhận `full_text_flat`, `text_map`, `chapters_dom`.
     - Gọi `chunk_from_text_map(text_map, config)` → `all_chunks`.
     - Lưu `chapters_dom` và `text_map` vào instance (ví dụ `self._epub_layout_state`) để dùng ở bước finalize.
   - Ngược lại: giữ luồng cũ (parse_file → clean_text → chunk_novel).

2. **Sau khi dịch xong:** Trong `_finalize_translation()`:
   - Nếu có `_epub_layout_state`:
     - Gọi `build_translation_map_from_chunks(all_chunks, completed_translations, ...)` → `translation_by_text_id`.
     - Gọi `reinject_translations_into_epub(...)` → xuất EPUB dịch (+ optional HTML master).
     - Vẫn có thể lưu thêm file TXT “phẳng” (full_content nối từ translation map) để tương thích với UI/convert sau này.
   - Nếu không: giữ hành vi cũ (merge → TXT → convert_to_epub bằng pandoc).

3. **Progress / resume:** Chunks vẫn key bởi `global_id`; progress_manager không cần đổi. Chỉ khi finalize mới cần `text_map` + `chapters_dom` (có thể lưu vào `data/progress/` hoặc metadata khi bắt đầu job).

4. **Config:**
   - `preprocessing.epub.preserve_layout: true/false`
   - `output.epub_reinject.output_html_master: true/false`
   - `output.epub_reinject.keep_flat_txt: true/false`

**Tests:** Integration test: mock parse trả về text_map + 1 chương DOM, mock dịch 1 chunk → finalize → kiểm tra reinject được gọi và file output tồn tại.

---

### Phase 6 (tùy chọn): HTML master template + export DOCX/PDF

**Mục đích:** Có file HTML “master” đẹp (CSS, TOC) và tùy chọn convert sang DOCX/PDF.

**Công việc:**

1. Template HTML: file mẫu `templates/master_layout.html` với placeholder cho title, CSS, body (nội dung từng chương).
2. Sau reinject: gộp các chương đã dịch vào template, xuất `{novel_name}_master.html`.
3. Tùy chọn: gọi Pandoc/WeasyPrint để convert HTML → DOCX/PDF (có thể để sau khi POC và 4 phase trên ổn định).

---

## 5. Thứ tự triển khai và milestone

| Milestone | Nội dung | Phụ thuộc |
|-----------|----------|-----------|
| **M0** | POC script (Phase 0) chạy thành công trên 1 EPUB mẫu | Không |
| **M1** | Parser EPUB v2 (Phase 1) + test | M0 |
| **M2** | Chunker từ TEXT_MAP (Phase 2) + test | M1 |
| **M3** | Build translation map từ chunks (Phase 3) + test | M2 |
| **M4** | Re-inject module, xuất EPUB + HTML (Phase 4) + test | M3 |
| **M5** | Tích hợp vào Translator (Phase 5), config, integration test | M4 |
| **M6** | (Tùy chọn) HTML master template + DOCX/PDF export (Phase 6) | M5 |

---

## 6. Rủi ro và giảm thiểu

| Rủi ro | Cách giảm thiểu |
|--------|-------------------|
| Model xóa hoặc sửa delimiter `[TX:id]` | Prompt rõ ràng “giữ nguyên mọi chuỗi [TX:...]”; fallback split theo thứ tự + độ dài tương đối. |
| EPUB cấu trúc phức tạp (nested, span) | Phase 1 chỉ extract block-level; nếu cần có thể mở rộng từng text node con sau. |
| File EPUB lớn, DOM tốn bộ nhớ | Lưu DOM từng chương ra file tạm (HTML) thay vì giữ hết trong RAM; reinject đọc từng file. |
| Resume job: cần text_map/chapters_dom | Lưu `text_map` + ref đến chapters_dom (hoặc path) vào metadata progress khi bắt đầu; khi resume load lại. |

---

## 7. Tệp và thư mục dự kiến

```
src/preprocessing/
  epub_layout_parser.py   # Phase 1: parse EPUB → TEXT_MAP + chapters_dom
  chunker_epub.py         # Phase 2: chunk_from_text_map (hoặc nằm trong chunker.py)

src/translation/
  (translator.py: nhánh prepare + finalize cho epub layout)  # Phase 5

src/output/
  epub_reinject.py        # Phase 4: reinject + write EPUB/HTML
  (formatter.py: có thể gọi epub_reinject khi output epub layout)

tools/poc_epub_layout/   # Phase 0
  run_poc.py
  data/ (epub mẫu)

docs/
  PLAN_EPUB_LAYOUT_PRESERVATION.md  # (file này)
```

---

## 8. Tiêu chí hoàn thành POC (Phase 0)

- [ ] Có 1 EPUB mẫu (ít nhất 1 chương).
- [ ] Script: parse → TEXT_MAP + DOM 1 chương, gán data-tid.
- [ ] Script: tạo 1 chunk có delimiter, gọi dịch (mock hoặc thật), split theo delimiter.
- [ ] Script: reinject vào DOM chương đó, ghi HTML.
- [ ] So sánh thủ công: mở HTML gốc và HTML dịch → layout giống nhau, chỉ khác ngôn ngữ.

Sau khi POC đạt, triển khai tuần tự Phase 1 → 5 theo milestone trên.
