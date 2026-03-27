# Rà soát: Quản lý / phân phối / cooldown API key thống nhất cho mọi workflow dùng AI

**Ngày:** 2026-03-15  
**Mục tiêu:** Đảm bảo mọi workflow chính và phụ có gọi AI đều dùng chung APIKeyManager / SmartKeyDistributor (quản lý, phân phối key, cooldown, RPD-block).

---

## 1. Nguồn key_manager trong luồng chính

| Nguồn | Khi nào |
|-------|--------|
| **main_async** | Tạo `shared_key_manager = SmartKeyDistributor(api_keys, num_chunks=9999, config)` một lần. |
| **detect_and_preprocess_input** | Nhận `key_manager=shared_key_manager` từ main, truyền xuống `ocr_file(..., key_manager=key_manager)`. |
| **InitializationService** | Nhận `existing_key_manager=shared_key_manager` → dùng luôn, không tạo key_manager mới. |
| **NovelTranslator** | Nhận `key_manager` từ `shared_resources["key_manager"]` (cùng một shared_key_manager). |
| **MetadataGenerator** (menu 2) | Nhận `key_manager=shared_key_manager` khi main tạo generator. |
| **GlossaryManager / RelationManager** | Nhận `key_manager=key_manager` từ InitializationService (key_manager từ shared). |
| **CSVAIFixer** | Nhận `key_manager` từ GlossaryManager / RelationManager khi họ tạo fixer. |

→ Mọi luồng chính đều dùng **cùng một** SmartKeyDistributor (và _state là APIKeyManager).

---

## 2. Ma trận workflow dùng AI vs quản lý key

| Workflow | Module / Hàm | Lấy key | Trả key | handle_exception | add_delay | Worker ID | Ghi chú |
|----------|--------------|---------|---------|------------------|-----------|-----------|---------|
| **Dịch chunk** | translator → model_router → GeminiAPIService | `get_key_for_worker(worker_id)` | `return_key(worker_id, key, is_error, ...)` | Có (trong translator) | Có (translator + distributor) | 0..N-1 | ✅ Thống nhất |
| **Batch QA** | translator._run_batch_qa_editor | `get_available_key()` | `return_key(999, key, ...)` + handle_exception khi lỗi | Có | (dùng chung key, delay trong service nếu có) | 999 | ✅ Thống nhất |
| **Metadata (menu 2)** | MetadataGenerator._call_gemini_async | `get_available_key()` | `return_key(999, key, ...)` | Có | GeminiAPIService (distributor) gọi add_delay | 999 | ✅ Thống nhất |
| **AI Cleanup (OCR/Pre-clean)** | ai_processor.ai_cleanup_text, _ai_cleanup_parallel | `get_available_key()` | `return_key(998, key, ...)` | Có | (delay trong add_delay nếu gọi từ distributor; cleanup dùng key_manager) | 998 | ✅ Thống nhất |
| **AI Spell check (OCR/Pre-clean)** | ai_processor.ai_spell_check_and_paragraph_restore, _ai_spell_check_parallel | `get_available_key()` | `return_key(997, key, ...)` | Có | delay giữa request trong loop | 997 | ✅ Thống nhất |
| **DOCX cleanup từng đoạn** | docx_processor.cleanup_paragraph_with_hints | `get_available_key()` | `return_key(998, key, ...)` | Có | (sync, gọi từ PDF/DOCX flow) | 998 | ✅ Thống nhất |
| **CSV AI Fixer** | csv_ai_fixer._call_ai_async | `get_available_key()` | `return_key(996, key, ...)` | Có | (async, gọi từ glossary/relation) | 996 | ✅ Thống nhất |
| **AI Table Recovery** | ai_table_recovery.recover_tables_to_csv | `get_available_key()` (khi key_manager) | `return_key(995, key, ...)` | Có | (sync, asyncio.run(return_key)) | 995 | ✅ Hỗ trợ key_manager; **caller phải truyền key_manager khi gọi từ luồng có shared_key_manager** |
| **Per-chunk QA Editor** | qa_editor (qua PromptOrchestrator / translator) | Dùng key của chunk (cùng worker_id) | Cùng return_key với chunk | Có | Cùng delay với dịch | worker_id chunk | ✅ Thống nhất (đi chung luồng dịch) |

---

## 3. Worker ID dùng cho quy trình phụ (tránh trùng translation)

| Worker ID | Workflow |
|-----------|----------|
| 998 | AI Cleanup (ocr + docx_processor) |
| 997 | AI Spell check |
| 999 | Metadata generation + Batch QA |
| 996 | CSVAIFixer |
| 995 | AITableRecovery |
| 0..N-1 | Translation workers (get_key_for_worker) |

---

## 4. Điểm đã thống nhất

- **Lấy key:** Hoặc `get_key_for_worker(worker_id)` (dịch), hoặc `get_available_key()` (phụ). Cả hai đều từ SmartKeyDistributor / APIKeyManager (_state).
- **Trả key:** Mọi nơi đều gọi `return_key(worker_id, key, is_error=..., error_type=..., error_message=...)` khi xong (thành công hoặc lỗi).
- **Cooldown / RPD:** `handle_exception(key, exc)` phân loại lỗi; `return_key(..., is_error=True, error_type=...)` cập nhật trạng thái key (block, rpd_blocked_until) trong APIKeyManager. SmartKeyDistributor delegate xuống _state.
- **Delay:** Translator gọi `add_delay_between_requests(current_key)` trước mỗi request; GeminiAPIService (có distributor) cũng gọi `distributor.add_delay_between_requests(self.current_key)` → thống nhất rate limit (5 RPM/key, 12s khi dùng performance config free tier).

---

## 5. Luồng không dùng key_manager (theo thiết kế)

| Luồng | Lý do |
|-------|--------|
| **api_key_validator** (startup) | Kiểm tra key lúc khởi động, không nằm trong pool dịch. |
| **Context cache init** (InitializationService) | Dùng một key tạm (api_keys[0]) để tạo cache, một lần. |
| **AITableRecovery khi không truyền key_manager** | Fallback rotate api_keys nội bộ; khi gọi từ luồng có shared_key_manager thì nên truyền key_manager. |

---

## 6. Caller phải truyền key_manager khi có

- **ocr_file** (ocr_reader): Nhận `key_manager` từ `detect_and_preprocess_input` → truyền vào `ai_cleanup_text`, `ai_spell_check_and_paragraph_restore`. ✅ Đã truyền từ main.
- **cleanup_paragraph_with_hints / spell_check_paragraph** (docx_processor): Được gọi từ `_hybrid_workflow_pdf_to_docx` (pdf_processor) với `key_manager=key_manager`; pdf_processor nhận key_manager từ ocr_reader / hybrid workflow. Cần đảm bảo **hybrid_workflow_pdf_to_docx** nhận và truyền key_manager.
- **AITableRecovery**: Hiện không thấy chỗ nào trong code instantiate `AITableRecovery(...)`. Khi có chỗ gọi (vd. từ ocr hoặc tool khác), **caller phải truyền `key_manager=shared_key_manager`** (hoặc key_manager tương ứng) nếu chạy trong luồng có shared key manager.
- **GlossaryManager / RelationManager**: Khi tạo CSVAIFixer để sửa file CSV bằng AI, đã truyền `key_manager=self.key_manager`. ✅ Init service truyền key_manager vào cả hai manager.
- **hybrid_workflow_pdf_to_docx**: Trong ocr_reader khi chạy từ **CLI** (__main__, PDF text-based → DOCX), gọi `hybrid_workflow_pdf_to_docx(..., pages_list)` **không truyền key_manager** → cleanup paragraph dùng fallback api_keys. Chấp nhận được cho chế độ standalone. Nếu sau này gọi từ luồng có shared_key_manager thì nên truyền `key_manager=...`.

---

## 7. Kiểm tra hybrid_workflow_pdf_to_docx có truyền key_manager

- **ocr_reader._hybrid_workflow_pdf_to_docx** nhận `key_manager: Any = None` và gọi `cleanup_paragraph_with_hints(para, ocr_cfg, key_manager=key_manager)`. ✅
- **pdf_processor.hybrid_workflow_pdf_to_docx** nhận `key_manager: Any = None` và gọi `cleanup_paragraph_with_hints(para, ocr_cfg, key_manager=key_manager)`. ✅
- **ocr_reader** gọi `_hybrid_workflow_pdf_to_docx(..., key_manager=key_manager)` khi có. ✅ (cần xác nhận tại chỗ gọi)

---

## 8. Kết luận

- Toàn bộ workflow chính và phụ **có dùng AI** đều được thiết kế để:
  - Dùng chung **một** SmartKeyDistributor (và APIKeyManager bên trong) khi chạy từ main.
  - Lấy key qua `get_key_for_worker` hoặc `get_available_key`, trả key qua `return_key`, phân loại lỗi qua `handle_exception`, và áp dụng delay qua `add_delay_between_requests`.
- Worker ID cho quy trình phụ (998, 997, 999, 996, 995) thống nhất, không trùng với translation workers.
- **Khuyến nghị:** Khi bổ sung gọi **AITableRecovery** từ luồng có shared key (vd. OCR/preprocess), cần instantiate với `key_manager=shared_key_manager` (hoặc key_manager tương ứng) và truyền xuống.
