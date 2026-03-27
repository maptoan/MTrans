# Rà soát workflow – Tránh treo và thống nhất module

**Ngày:** 2026-03-15  
**Mục tiêu:** Đảm bảo tính tương thích async/sync, thống nhất giữa các module, và tính trơn mượt của toàn bộ workflow (chính + phụ).

---

## 1. Bản đồ workflow chính và phụ

### 1.1 Luồng chính (main.py → main_async)

| Bước | Module / Hàm | Ghi chú |
|------|----------------|--------|
| Khởi tạo key | SmartKeyDistributor | Sync, chạy trong main thread |
| Preprocess | `detect_and_preprocess_input` | **Chạy trong `asyncio.to_thread()`** → không block event loop |
| Init resources | InitializationService.initialize_shared_resources | Async task chạy song song với preprocess |
| Dịch | NovelTranslator.run_translation_cycle_with_review | Async; có timeout per-chunk, segment wait |
| Menu sau dịch | UIHandler.ask_completion_menu | **Timeout 60 phút** (_get_user_choice_with_timeout) |
| Option 1/2: Convert TXT→EPUB | FormatConverter.convert_to_epub | **Đã dùng to_thread** (output_formatter.convert_txt_to_epub) |
| Option 4: Export master.html→EPUB | html_exporter.export_master_html_to_epub | **Đã sửa: pandoc chạy trong to_thread** |
| Menu DOCX/PDF | UIHandler.ask_additional_formats | Timeout 60 phút |
| Option 3: DOCX + PDF | FormatConverter.convert_to_docx, convert_to_pdf | **Đã sửa: cả hai chạy trong to_thread**, gather song song |

### 1.2 Luồng phụ (trong preprocess / OCR)

| Bước | Module / Hàm | Ghi chú |
|------|----------------|--------|
| OCR + Cleanup + Spell check | ocr_reader.ocr_file, ai_processor | Gọi từ `detect_and_preprocess_input` (đang chạy trong thread) |
| AI Cleanup | ai_processor.ai_cleanup_text | asyncio.run(_ai_cleanup_parallel); **phase_timeout** + **max_no_key_waits** |
| AI Spell check | ai_processor.ai_spell_check_and_paragraph_restore | asyncio.run(_ai_spell_check_parallel); **phase_timeout** + **max_no_key_waits** |
| Hỏi reuse file | input_preprocessor._ask_user_yes_no | input() không timeout (chạy trong preprocess thread; chờ user là hợp lý) |
| DOCX cleanup từng đoạn | docx_processor.cleanup_paragraph_with_hints | asyncio.run từ sync; thường gọi từ luồng DOCX (sync) |

---

## 2. Các điểm đã xử lý (tránh treo)

### 2.1 Blocking I/O trong async (đã sửa)

- **FormatConverter.convert_to_docx / convert_to_pdf**  
  `pypandoc.convert_file` blocking → chuyển sang `_convert_to_*_sync` + `asyncio.to_thread()`.  
  Khi chọn "Convert cả DOCX và PDF", hai tác vụ chạy song song trong thread pool, không block event loop.

- **html_exporter.export_master_html_to_epub**  
  `pypandoc.convert_file` blocking → chuyển sang `_convert_master_html_to_epub_sync` + `asyncio.to_thread()`.  
  Option 4 (Export EPUB từ master.html) không còn treo.

- **FormatConverter.convert_to_epub**  
  Đã dùng `asyncio.to_thread(self.output_formatter.convert_txt_to_epub, ...)` từ trước.

### 2.2 Phase timeout và giới hạn chờ key (đã có)

- **AI Cleanup:** `phase_timeout_seconds` (mặc định 3600), `max_no_key_waits` (20/chunk).  
- **AI Spell check:** `phase_timeout_seconds` (3600), `max_no_key_waits` (20/chunk).  
→ Tránh treo khi hết key hoặc 429 liên tục.

### 2.3 Preprocess không block event loop

- **main_async** gọi `detect_and_preprocess_input` qua `asyncio.to_thread(...)` → OCR/AI cleanup/spell check chạy trong thread riêng, init resources chạy song song.

### 2.4 User input có timeout (menu chính)

- **UIHandler:** Tất cả menu sau dịch dùng `_get_user_choice_with_timeout` (timeout 60 phút, default choice).  
- **input_preprocessor._ask_user_yes_no:** Không timeout; dùng khi đã có file processed (reuse hay re-run), chạy trong preprocess thread; chờ user là mong muốn.

---

## 3. Chuẩn áp dụng cho tương lai

1. **Blocking pandoc/subprocess trong async:** Luôn bọc trong `asyncio.to_thread(sync_fn, ...)` hoặc sync helper + `to_thread`.
2. **Phase AI dài (cleanup, spell check, v.v.):** Có `phase_timeout_seconds` và giới hạn chờ key (max_no_key_waits) hoặc tương đương.
3. **Menu người dùng trong luồng chính:** Dùng cơ chế có timeout (ví dụ _get_user_choice_with_timeout) để tránh treo vô hạn.
4. **Preprocess nặng gọi từ main_async:** Chạy trong `asyncio.to_thread(...)` để không block event loop.

---

## 4. Điểm không đổi (theo thiết kế)

- **ocr_reader khi chạy CLI (__main__):** Có `input()` không timeout cho menu resume (1/2/3/4) và PDF text-based (1 hoặc 2). Đây là chế độ tương tác, giữ nguyên.
- **relation_manager / glossary_manager:** `input()` khi thiếu file/cấu hình; dùng trong ngữ cảnh có người dùng, giữ nguyên trừ khi thêm chế độ headless.
- **docx_processor.convert_docx_to_epub:** Sync, thường gọi từ luồng OCR/DOCX (sync); nếu sau này gọi từ async thì cần bọc to_thread.

---

## 5. Tóm tắt file đã sửa (liên quan treo)

| File | Thay đổi |
|------|----------|
| `src/translation/format_converter.py` | convert_to_docx/convert_to_pdf: sync helper + asyncio.to_thread |
| `src/output/html_exporter.py` | export_master_html_to_epub: sync helper + asyncio.to_thread cho pandoc |
| `src/preprocessing/ocr/ai_processor.py` | (trước đó) Spell check: phase_timeout + max_no_key_waits |
| `src/services/smart_key_distributor.py` | (trước đó) state_config ưu tiên performance (free tier 5 RPM, 12s) |
| `config/config.yaml` | (trước đó) phase_timeout_seconds, max_requests_per_minute_per_key |

---

**Kết luận:** Các vị trí đã biết gây treo (menu convert DOCX/PDF, export master.html→EPUB, AI cleanup/spell check không thoát) đã được xử lý bằng timeout, giới hạn chờ key và chạy blocking I/O trong thread. Workflow chính và phụ thống nhất theo chuẩn trên.
