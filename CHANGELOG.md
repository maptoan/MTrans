## Unreleased

### **Cải tiến / Sửa lỗi:**

- ✅ **Marker guardrail gating (missing markers fix):**
  - Bật marker guardrail theo công thức `use_markers_config OR original_has_markers`.
  - Khi guardrail tắt: bỏ qua marker-first validation và không trigger vòng re-translation vì “thiếu marker” (tránh false-positive khi `use_markers=false`).
  - Khi guardrail bật: giữ strict marker validation như hiện tại (không nới lỏng).
- ✅ **Sub-chunk Fallback marker preservation (khi `use_markers=true`):**
  - Tránh tách đôi START/END khi split sub-chunk: gắn START vào phần A và END vào phần B.
  - PromptBuilder kích hoạt hướng dẫn preserve marker cả trường hợp chỉ có START hoặc chỉ có END.

- ✅ **Script compatibility refresh (`*.bat`, `*.sh`):**
  - `run.bat`: fallback khi thiếu `tools/version_manager.py`, hỗ trợ truyền tham số `%*`, chuẩn hóa môi trường UTF-8.
  - `run_debug.bat`: tự tạo/kích hoạt venv nếu thiếu, chạy bằng python trong venv, nhận tham số dòng lệnh.
  - `data/metadata/run_csv_fixer.bat`: chạy ổn định theo thư mục script (`%~dp0`) để tránh lỗi CWD.
  - `scripts/nas_backup.sh`: thêm `set -euo pipefail`, cập nhật version và đồng bộ exclude theo cấu trúc mới.
  - `scripts/session_quick.sh`: auto cd project root, tự chọn `python3/python`.

---

## v9.5 (2026-03-27) - Docs Sync & README Onboarding Refresh

### **Cải tiến / Sửa lỗi:**

- ✅ **README onboarding rewrite:** Viết lại phần hướng dẫn sử dụng theo luồng "fork → cấu hình tối thiểu → chạy nhanh", giảm độ phức tạp cho người dùng mới.
- ✅ **Core docs synchronization:** Đồng bộ phiên bản/trạng thái giữa `README.md`, `PROJECT_CONTEXT.md`, `WORKFLOW_DOCUMENTATION.md`, `DOCUMENTATION_INDEX.md`.
- ✅ **Source-of-truth clarification:** Chuẩn hóa thứ tự tài liệu ưu tiên khi tra cứu (`README` → `PROJECT_CONTEXT` → `WORKFLOW_DOCUMENTATION` → `CHANGELOG`).

---

## v9.4 (2026-03-27) - Workspace Reorg Safety Baseline

### **Cải tiến / Sửa lỗi:**

- ✅ **Workspace baseline report:** Bổ sung `docs/WORKSPACE_REORG_BASELINE.md` để chốt trạng thái trước cải tổ.
- ✅ **Artifact policy hardening:** Chuẩn hóa `.gitignore` cho `backup/`, `data/output/**`, `data/reports/**` và giữ `.gitkeep` cho runtime dirs rỗng.
- ✅ **Backup script policy:** Cập nhật `scripts/nas_backup.py` và `scripts/nas_backup.sh` để loại trừ toàn bộ `data/*` (backup chỉ codebase/docs).
- ✅ **Path contract helper:** Bổ sung `src/utils/path_manager.py` và tích hợp vào các module lõi:
  - `src/managers/progress_manager.py`
  - `src/output/formatter.py`
  - `src/preprocessing/metadata_generator.py`
  - `src/services/gemini_api_service.py`
  - `src/translation/translator.py`
- ✅ **Script path alignment:** Chuẩn hóa đường dẫn theo project root cho:
  - `scripts/mass_key_benchmark_v2.py`
  - `scripts/extract_metadata_sequential.py`
  - `scripts/init_session.py`
  - `scripts/cleanup_project.py`

---

## v9.3 (2026-03-20) - Aggressive Table Reset & Reporting Fix

### **Cải tiến / Sửa lỗi:**

- ✅ **Aggressive Table Reset:** Triển khai bộ CSS Reset với `!important` trong `epub_reinject.py` để ép định dạng bảng trên EPUB3, giải quyết triệt để lỗi bảng "xô lệch thành khối text".
- ✅ **Fixed False Failure Reporting (v9.2.3):** Sửa lỗi gán nhầm `all_chunks` vào `failed_chunks` trong `translator.py` khiến hệ thống báo cáo sai tỷ lệ thất bại.
- ✅ **Byte Corruption Recovery (v9.2.1):** Phục hồi tệp `translator.py` bị suy hao dữ liệu tại dòng 1220.
- ✅ **Sync Integration Tests:** Cập nhật bộ test tích hợp (`tests/`) để khớp với logic trả về của runner mới.

---

## v9.2 (2026-03-19) - Unified Layout & Quality (Preserve Tables, Headings, Images)

### **Cải tiến / Sửa lỗi:**

- ✅ **EPUB Table Preservation:** Sửa lỗi mất định dạng bảng mầu/viền trong EPUB bằng cách bảo tồn attributes của thẻ `<td>` và `<th>` trong `epub_layout_parser.py`.
- ✅ **Master HTML Content Recovery:** Phục hồi ảnh và tiêu đề chương (headings) bị mất khi build Master HTML bằng cách duyệt `contents` thay vì `children` của body trong `epub_reinject.py`.
- ✅ **English Skip Logic Optimization:** Nới lỏng ngưỡng `_check_content_coverage` (0.3 -> 0.25) cho các sách gốc Latin để tránh việc AI skip nhầm các đoạn chưa dịch hết trong `translator.py`.
- ✅ **Marker Recovery System:** Phục hồi 100% các markers bị "strip" nhầm do logic cleanup cũ qua tool `recover_markers.py`.

### **Files thay đổi:**

- `src/preprocessing/epub_layout_parser.py`: Cập nhật `reinject_translations_to_html` (Table support).
- `src/output/epub_reinject.py`: Cập nhật `build_html_master` (Headings & Images support).
- `src/translation/translator.py`: Điều chỉnh `_check_content_coverage` thresholds.
- `recover_markers.py`: Tool phục hồi markers khẩn cấp.

---


### **Cải tiến / Sửa lỗi:**

- ✅ **Free-tier state_config:** SmartKeyDistributor build `state_config` ưu tiên `performance`: `min_delay_between_requests` = 12.0s, `max_requests_per_minute` = `max_requests_per_minute_per_key` = 5 (per-key). Config: `performance.max_requests_per_minute_per_key: 5`; `key_management.min_delay` không còn ghi đè delay/RPM per-key.
- ✅ **Spell check không treo sau Cleanup:** AI Soát lỗi chính tả thêm phase timeout (mặc định 3600s) và tối đa 20 lần chờ key/chunk; hết thời gian hoặc quá 20 lần thì bỏ qua chunk, trả về phần đã xử lý. Config: `ocr.ai_spell_check.phase_timeout_seconds: 3600`.

### **Files thay đổi:**

- `src/services/smart_key_distributor.py`: state_config merge (key_management trước, performance ghi đè min_delay + max_rpm_per_key).
- `config/config.yaml`: performance.max_requests_per_minute_per_key, key_management comment; ocr.ai_spell_check.phase_timeout_seconds.
- `src/preprocessing/ocr/ai_processor.py`: _ai_spell_check_parallel phase_timeout_seconds, deadline_ts, max_no_key_waits; ai_spell_check_and_paragraph_restore truyền phase_timeout_s.

---

## v9.1.1 (2026-03-14) - Master.html / EPUB layout (fix nguồn nội dung)

### **Sửa lỗi:**

- ✅ **EPUB từ master.html giống TXT tổng:** Master.html được build từ **nội dung chưa chuẩn hóa** (không có [H1]) → một section duy nhất → EPUB phẳng. Đã sửa: dùng **cùng nội dung đã chuẩn hóa** (`_normalize_paragraphs`) cho cả lưu TXT và `build_html_master_from_flat_text` → master có nhiều `<section>` tương ứng chương.
- ✅ **Tài liệu:** `docs/AUDIT_MASTER_HTML_EPUB_LAYOUT.md` – rà soát thuật toán bảo lưu/phục hồi layout master.html → EPUB.

### **Files thay đổi:**

- `src/translation/translator.py`: _finalize_translation – normalized_content cho save + build_html_master_from_flat_text.
- `docs/AUDIT_MASTER_HTML_EPUB_LAYOUT.md` (mới).

---

## v9.1 (2026-03-14) - RPD-block & Chuẩn hóa Key State (APIKeyManager làm nguồn sự thật)

### **Cải tiến:**

- ✅ **APIKeyManager – RPD-block (quota/ngày)**:
  - `APIKeyStatus.rpd_blocked_until`: key hết quota kiểu "plan and billing" bị block tới ngày hôm sau.
  - `mark_request_error`: nhận diện "you exceeded your current quota" + "plan and billing" → set `rpd_blocked_until`; `_is_key_available` / `get_active_key_count` bỏ qua key đang RPD-block.
  - `get_quota_status_summary()`, `handle_exception(key, exc)`, `get_earliest_reset_time()`; `get_available_key()` không trả key đang block.
- ✅ **SmartKeyDistributor dùng APIKeyManager làm nguồn sự thật**:
  - `_state: APIKeyManager` trong `__init__`; trạng thái blocked/usable, quota, RPD đọc từ `_state`.
  - `_is_key_available(key)` → `not _state.is_key_blocked(key)`; `return_key` / `mark_request_error` delegate tới `_state`; recovery task refill reserve từ key không bị block.
  - `key_statuses` là property trả về `_state.key_statuses`; `error_pools` giữ cấu trúc (deprecated), `_move_to_error_pool` thành no-op.
- ✅ **Tests**: `tests/test_api_key_rpd_quota.py` (RPD, get_quota_status_summary, handle_exception); `test_smart_key_distributor_errors.py` cập nhật assert theo _state; `test_execution_manager` điều chỉnh mock get_available_key.

### **Files thay đổi:**

- `src/services/api_key_manager.py`: rpd_blocked_until, RPD detection, get_quota_status_summary, handle_exception, get_earliest_reset_time; mark_request_success sync.
- `src/services/smart_key_distributor.py`: _state (APIKeyManager), _keys_in_reserve, delegate availability/return_key/get_quota/get_active/add_delay/recovery; key_statuses property.
- `src/services/gemini_api_service.py`: await mark_request_error.
- `tests/test_api_key_rpd_quota.py` (mới), `tests/test_smart_key_distributor_errors.py`, `tests/test_execution_manager.py`.

---

## v9.0 (2026-03-14) - MTranslator master.html Workflow (STABLE)

### **Cải tiến chính:**

- ✅ **Đổi tên dự án thành MTranslator** trong tài liệu và metadata (PROJECT_CONTEXT, README, AGENTS, DOCUMENTATION_INDEX, v.v.).
- ✅ **EPUB Layout Preservation (Phase 0–6)**:
  - Parser EPUB v2 (`parse_epub_with_layout`) trích `text_map` + `chapters_html` theo đúng spine order.
  - Chunker EPUB (`build_chunks_from_text_map`) với `text_ids` + delimiter `[TX:{id}]`.
  - Translation map từ chunks (`build_translation_map_from_chunks`) và re-inject (`apply_translations_to_chapters`).
  - HTML master template chuẩn (`<!DOCTYPE html>`, `<meta charset>`, `<main id="nt-content">`, `<section>` theo chương).
- ✅ **Tích hợp vào Translator (Phase 5)**:
  - Nhánh `preprocessing.epub.preserve_layout` để đi pipeline: `EPUB → TEXT_MAP → dịch → master.html`.
  - `_finalize_translation` save `master.html` và trả về đường dẫn HTML master thay vì chỉ TXT/EPUB cũ.
- ✅ **Flat Text / Scan-based master.html (Phase 7–8)**:
  - `build_html_master_from_flat_text` chuyển TXT tổng (đã qua OutputFormatter, có marker `[H1]...[/H1]`) thành `master.html` theo heading.
  - Nhánh `_finalize_translation` cho input text-based/scan-based luôn build và lưu `{novel_name}_master.html` trong `progress.progress_dir` song song với TXT tổng.
- ✅ **Chuẩn bị cho unified workflow EPUB/PDF**:
  - Đã tạo `epub_reinject.py`, `epub_layout_parser.py`, `chunker_epub.py`, `translation_map_epub.py` với test TDD đầy đủ.
  - Kế hoạch Phase 9+: QA đa tầng (per-chunk + Batch QA), helper HTML→EPUB/PDF từ `master.html`.
- ✅ **Phase 13 – Quality profile (v9.0)**:
  - Cấu hình `quality_profile.name` (fast_low_cost | balanced_default | max_quality) áp dụng overlay lên config khi khởi tạo NovelTranslator.
  - Module `src.utils.quality_profile.apply_quality_profile`; tests trong `tests/test_quality_profile_phase13.py`.

---

## v8.4 (2026-03-14) - Key Management & Partial Fallback

### **Cải tiến:**

- ✅ **Fallback Partial khi hết key**: Khi 100% key bị quota mà chunk đã có bản dịch nháp, lưu bản nháp với `status=partial` và trả về partial thay vì failed; merge vẫn dùng được bản partial.
- ✅ **return_key(error_message)**: Thêm tham số tùy chọn `error_message` vào `return_key`; translator truyền `str(e)` để distributor log chi tiết.
- ✅ **Giảm log lặp RPD**: Log "Key đã vượt quá X lần thử lại vì lỗi quota" chỉ xuất khi lần đầu đạt ngưỡng RPD hoặc mỗi 10 lần.

### **Files thay đổi:**

- `src/translation/translator.py`: draft_translation, partial save/return, error_message trong return_key.
- `src/translation/execution_manager.py`: coi partial như success cho merge.
- `src/services/smart_key_distributor.py`: return_key(error_message), giảm log RPD.
- `src/services/api_key_manager.py`: return_key(error_message).
- `docs/PLAN_KEY_IMPROVEMENTS.md`: kế hoạch chi tiết; `ALGORITHM_DOCUMENTATION.md`: mục 13.3 cập nhật.

---

## v8.2 (2026-02-24) - Unicode Fix & Documentation Sync

### **Major Improvements:**

#### **1. Unicode Fix for PowerShell Scripts**

- ✅ **PowerShell 5.1 UTF-8 Support**: Fixed Vietnamese display issues by setting `$OutputEncoding`, `[Console]::InputEncoding`, `[Console]::OutputEncoding` and `chcp 65001` command.
- ✅ **Script Encoding**: Updated all PowerShell scripts to save in UTF-8 with BOM format.
- ✅ **Impact**: Vietnamese characters now display correctly in PowerShell output.

#### **2. Algorithm Documentation**

- ✅ **ALGORITHM_DOCUMENTATION.md**: Created comprehensive documentation of the API Key Management & Chunking Optimization Algorithm.
- ✅ **Gemini 3 Flash Preview Support**: Documented limits (RPM, TPM, RPD) and optimization strategies.
- ✅ **Content Includes**:
  - Smart Chunking Layer (Adaptive sizing, Paragraph-aware splitting, Balancing)
  - Key Distribution Layer (Worker-Key Affinity, Global Rate Limiter, Zero-Wait Replacement)
  - Gemini API Layer (Token Bucket, Context Caching, Auto-Retry + Backoff)

#### **3. Trifecta Pipeline v7.0 (Auto-healing)**

- ✅ **Self-Healing Loop**: Pipeline automatically detects errors via `checklist.py` and triggers OpenCode to fix (max 3 retries).
- ✅ **JSON Reporting**: Stores run history and validation results to `data/reports/trifecta_results.json`.
- ✅ **Smart Context Refinement**: Automatically extracts error logs from previous run to use as context for next fix.

---

## v8.1.2 (2026-02-12) - EPUB Order Fix & Architecture Docs

### **Major Improvements:**

#### **1. EPUB Content Order Fix**

- ✅ **Reading Order Restoration**: Fixed a critical bug in `file_parser.py` where chapters were extracted in arbitrary hash order. Replaced `get_items_of_type(ITEM_DOCUMENT)` with `book.spine` iteration to respect the EPUB's internal reading order.
- ✅ **Chapter Sequence Validation**: Verified parsing of 301+ chapters in correct sequence (vol_01 -> vol_02 -> vol_03).

#### **2. Architecture Documentation**

- ✅ **API & Worker Orchestration**: Created a comprehensive guide ([docs/API_WORKER_ORCHESTRATION.md](./docs/API_WORKER_ORCHESTRATION.md)) detailing the High-Availability algorithms (Affinity, Scaling, Pacing).
- ✅ **Efficiency Benchmarking**: Added a comparative analysis showing 6-8x throughput increase (from 2-3 to 15-20 chunks/min) with the new orchestration logic.

#### **3. Critical Bug Fixes (Maintenance)**

- 🐛 **Batch QA Crash**: Fixed `TypeError` in `translator.py` due to invalid `worker_id` kwarg in sync `get_available_key`.
- 🐛 **Stale Cache Merge Failure**: Implemented cache invalidation for retried chunks to prevent "Missing END marker" false positives.
- 🐛 **Logger Method Cleanup**: Replaced 55+ instances of `logger.success()` with `logger.info()` to prevent `AttributeError` crashes.
- 🐛 **Sub-chunk Fallback Fix**: Fixed crash when reporting fallback status via invalid logger level.

---

## v8.1 (2026-02-11) - Prompt Optimization & Character Compliance Fixes

---

## v8.0 (2026-02-10) - API Throughput v3 Optimization

### **Major Improvements:**

#### **1. High-Throughput Optimization (v3)**

- ✅ **Massive Throughput**: Optimized for a 60-key architecture, enabling up to **2.4M tokens/day** on the Gemini Free Tier.
- ✅ **Chunk Upsizing**: Increased `max_chunk_tokens` from 6,000 to **20,000**, reducing total API requests by ~3.3x.
- ✅ **Parallel Worker Scaling**: Calibrated `max_parallel_workers` to **42** (70% utilization) to maintain stability.
- ✅ **RPM & RPD Management**:
  - Enforced a system-wide **250 RPM** limit.
  - Implemented **12s delay per request** to perfectly match the 5 RPM/key limit.
  - Strict **20 RPD (Requests Per Day)** hardcap per key with 80% usage warnings.

#### **2. 3-Tier Quality Gate**

- ✅ **Gate 1 (Structural)**: Enhanced checks for marker integrity, length ratio, and mid-sentence truncation.
- ✅ **Gate 2 (Content Coverage)**: New validation for paragraph density (≥ 70%) and chapter header consistency.
- ✅ **Gate 3 (CJK Residuals)**: Smart threshold (> 5 characters) to trigger the QA Editor pass only when necessary.

#### **3. Intelligent Fallback & Efficiency**

- ✅ **Sub-chunk Fallback**: Implemented automatic splitting of failed 20K chunks into 2x10K sequential sub-chunks using **Context Chaining** (Sub-A results feed into Sub-B context).
- ✅ **QA Conditional Gating**: Strategy to skip the QA Editor pass for "clean" chunks (low CJK + glossary compliant), saving substantial API quota.
- ✅ **CJK Self-Healing**: Integrated "Zero Tolerance" CJK instructions directly into the primary translation prompt.

#### **4. Reliability & Audit Fixes**

- ✅ **Sub-chunk Bug Fix**: Resolved critical dead code causing sub-chunk failures to return partial text instead of retrying.
- ✅ **Performance Cleanup**: Refactored `translator.py` to eliminate duplicate expensive calls to CJK detection and glossary validation.
- ✅ **Config Standardization**: Synchronized configuration comments with actual constant values (RPD 20).

---

## v7.2 (2026-02-08) - Non-Fiction Support & Stability Hardening

### **Major Improvements:**

#### **1. Non-Fiction & Academic Document Support**

- ✅ **Specialized Pipelines**: Added dedicated processing logic for Non-Fiction genres (Academic, Technical, Medical, Legal).
- ✅ **Adaptive Prompts**: `PromptBuilder` now dynamically adjusts instructions based on `document_type`, prioritizing accuracy and terminology over literary flair for non-fiction.
- ✅ **Metadata Mapping**: Updated `StyleManager` and `GlossaryManager` to correctly map Non-Fiction metadata columns (Methodology, Terminology) instead of literary ones.

#### **2. API Key Management Hardening**

- ✅ **Zombie Key Detection**: Fixed `AttributeError` in blocked key check; identifying keys with high error rates (10+ consecutive failures) as "Zombie/Blocked" to exclude from pool.
- ✅ **Pool Health Metrics**: `get_active_key_count` now reflects true usable capacity, preventing "False Healthy" status.

#### **3. Advanced CJK Validation (Strict Mode)**

- ✅ **Zero Tolerance Policy**: `_final_cleanup_pass` now raises specific errors if CJK characters persist, forcing a retry instead of silently saving "dirty" chunks.
- ✅ **Surgical Repair Optimizations**:
  - **Contextual Retry**: First attempt to fix with surrounding context.
  - **Transliteration Fallback**: If AI refuses to translate, automatically transliterate remaining characters to Sino-Vietnamese/Pinyin to guarantee 100% Latin output (saving token costs on full retries).

#### **4. UX & Bug Fixes**

- ✅ **Zero-Touch Startup**: Removed interactive menu at startup; program now defaults to "Translation Mode" immediately for faster automation.
- ✅ **EPUB Conversion Fix**: Resolved `AttributeError: module 'convert_module' has no attribute 'build_pandoc_args'` by refactoring legacy import logic to use `OutputFormatter`.
- ✅ **Codebase Cleanup**: Removed obsolete `_verify_chunk_sizes` logic to prevent false positives with new semantic chunking.

---

## v7.1 (2026-02-05) - Metadata & Prompt Refinement

### **Major Improvements:**

#### **1. Prompt Engineering Refactoring**

- ✅ **Show, Don't Tell**: Replaced theoretical literary guidelines in `PromptBuilder` with concise **Example Matrices** (Bad vs Good examples).
- ✅ **Golden Rules**: Simplified editing commands to 3 core rules (Title, Dialogue, Anti-Redundancy).
- ✅ **Token Optimization**: Reduced prompt size significantly while improving AI pattern matching.

#### **2. Metadata Generation Workflow**

- ✅ **NotebookLM Integration**: Created `METADATA_PROMPT_NOTEBOOKLM.md` with specialized prompts for extracting Style Profile, Glossary, and Relations from raw text.
- ✅ **Smart Sampling**: Strategy for sampling text to stay within context limits while maximizing coverage.

#### **3. Debugging & Logging**

- ✅ **Anti-Spam Logging**: Downgraded "Worker key blocked" logs to DEBUG level.
- ✅ **Health Monitoring**: Added periodic **Pool Health Checks** (active/total keys) to `execution_manager` and `api_key_manager`.

---

## v7.0 (2026-02-01) - Performance & Reliability Update

### **Major Improvements:**

#### **1. Performance Optimization (High Impact)**

- ✅ **Glossary & Relation Matching**: Optimized generic regex matching with **Substring Pre-check (O(1))** and **Lazy Regex Evaluation**.
  - **Result**: Speedup **7x - 100x** for pre-translation analysis steps depending on glossary size.
  - **Benchmarks**: Verified with 500+ terms, reduced validation time from ~18ms to ~2ms per call.

#### **2. Critical Fixes**

- ✅ **SmartKeyDistributor Crash**: Fixed critical `AttributeError: 'SmartKeyDistributor' object has no attribute 'get_quota_status_summary'` which caused workers to crash during quota exhaustion events.
- ✅ **Quota Handling**: Restored correct 429 backoff logic; system now waits or reports "No keys available" properly instead of crashing.
- ✅ **Async File I/O**: Implemented `get_chunk_translation_async` in `ProgressManager` to prevent blocking the event loop during heavy I/O operations.

#### **3. Full Codebase Refactoring**

- ✅ **Comprehensive Cleanup**: Completed refactoring for `src/translation`, `src/managers`, `src/utils`, and `main.py`.
- ✅ **Type Safety**: Added extensive type hints (`Optional`, `List`, `Dict`) across the codebase.
- ✅ **Cleaner Architecture**: Extracted constants, centralized configuration logic, and unified docstrings.

---

## v6.0 (2026-01-29) - Phase 7.5: Enhanced Quality Control

### **Major Improvements:**

#### **1. Mandatory QA Editor Pipeline**

- ✅ **Workflow Overhaul**: QA Editor pass giờ đây chạy **BẮT BUỘC** cho mọi chunk (nếu enabled) thay vì chỉ chạy khi sót CJK.
- ✅ **Worker Specialization**: Phân tách vai trò Draft và Editor trong cùng một flow để tối ưu văn phong và sửa lỗi.
- ✅ **Character Addressing (Xưng hô)**: Tích hợp `RelationManager` vào QA; Editor giờ đây nhận biết được các nhân vật trong đoạn văn và áp dụng đúng quy tắc xưng hô (Huynh/Đệ, Ta/Nàng...).

#### **2. Robust QA Execution**

- ✅ **Retry & Rotation logic**: QA Editor được bổ sung cơ chế retry với key rotation. Nếu API call fail, hệ thống tự động đổi khóa và thử lại tối đa 3 lần.
- ✅ **Shared Configuration**: Hợp nhất model và retry settings của QA Editor vào cấu hình chung (`models.flash`, `translation.max_retries`).

#### **3. Antigravity Kit Integration**

- ✅ **Embedded Intelligence**: Tích hợp bộ công cụ Antigravity (Skills, Agents, Workflows) để hỗ trợ phát triển và debug hệ thống.
- ✅ **Documentation**: Cập nhật `.Antigravity/GUIDE.md` hướng dẫn sử dụng các kỹ năng chuyên sâu.

---

## v5.5 (2026-01-29)

### **Improvements:**

#### **1. AutoFix Compliance Recovery**

- ✅ Sửa lỗi logic khiến các chunk vi phạm glossary bị FAIL ngay lập tức.
- ✅ Implement Post-Validation AutoFix: Tự động sửa lỗi glossary sau khi validation fail và re-validate.
- ✅ Cải thiện `_validate_metadata_compliance`: Chỉ phạt khi CN/Pinyin vẫn còn trong bản dịch.

#### **2. Optimized CJK Handling**

- ✅ Thêm cơ chế phát hiện ký tự CJK còn sót (`_detect_cjk_remaining`).
- ✅ Mở rộng QA Editor: Tự động dịch các từ CJK bị sót dựa trên ngữ cảnh gốc.
- ✅ Full Style Injection: QA Editor giờ nhận đầy đủ style instructions (315+ dòng) thay vì chỉ vài fields cơ bản.

#### **3. Smart Chunk Balancing & Genre Prompts**

- ✅ Tự động gộp các chunks nhỏ để tối ưu quota API.
- ✅ Hỗ trợ prompt linh hoạt theo thể loại (novel_genre).

---

## v4.0 (2026-01-22)

### **Major Improvements:**

#### **1. Periodic Flush với Error Handling**

- ✅ Batch save với periodic flush (5 phút interval) để cân bằng performance và data safety
- ✅ Error handling: Tự động retry nếu flush fail
- ✅ Edge cases: Xử lý clock skew và large time differences
- ✅ Config validation: Đảm bảo config values hợp lệ
- **Impact:** Data loss risk: MEDIUM → LOW, Performance: Không ảnh hưởng (< 1%)

#### **2. Google GenAI SDK Support**

- ✅ Hỗ trợ SDK mới (`google-genai`) và SDK cũ (`google-generativeai`)
- ✅ Auto-detection SDK availability khi activate venv
- ✅ Unified adapter interface cho cả 2 SDKs
- **Files:** `venv/Scripts/Activate.ps1`, `requirements.txt`, `src/services/genai_adapter.py`

#### **3. Coding Standards Compliance**

- ✅ Đánh giá và cải thiện coding standards (8.4/10 → 9.5/10)
- ✅ Error handling, edge cases, config validation, docstring enhancement
- ✅ Hội đồng 3 chuyên gia phản biện và phê duyệt

#### **4. Gemini Context Caching Implementation**

- ✅ Triển khai **Context Caching** để tối ưu token consumption và cost (tiết kiệm 75-90% input tokens).
- ✅ Quản lý lifecycle của cache (create, retrieve, metadata persistence) trong `GeminiAPIService`.
- ✅ Refactor prompt construction thành **Cacheable Prefix** (static) và **Dynamic Prompt** (per-chunk).
- ✅ Tích hợp cache reference (`cached_content`) vào API calls thông qua `model_router` và `genai_adapter`.
- ✅ Persistent storage cho cache metadata tại `data/cache/gemini_context_caches.json`.
- **Impact:** Cost reduction: HIGH, Latency: MEDIUM reduction.

#### **5. Documentation Cleanup**

- ✅ Dọn dẹp và archive các files lạc hậu
- ✅ Cập nhật toàn bộ documentation
- ✅ Tạo documentation index

### **Technical Details:**

- Periodic flush: Buffer flush khi đầy (10 chunks) HOẶC đã qua 5 phút
- Error recovery: Tự động retry nếu flush fail
- Clock skew handling: Reset timer nếu clock đi ngược
- Config validation: Type hints và validation cho batch_write_size và flush_interval

### **Documentation:**

- `VENV_SETUP_GUIDE.md` - Hướng dẫn setup venv
- `BATCH_VS_IMMEDIATE_SAVE_ANALYSIS.md` - Phân tích batch vs immediate save
- `PERIODIC_FLUSH_IMPLEMENTATION.md` - Tài liệu triển khai periodic flush
- `PERIODIC_FLUSH_EXPERT_REVIEW.md` - Phản biện của 3 chuyên gia
- `ASYNC_CLEANUP_WARNING_ANALYSIS.md` - Phân tích async cleanup warning

---

## v1.8.stable (2025-10-30)

- Enhanced logging with chunk-scoped messages: [Chunk X] start/complete, progress summaries, batch results, and metadata compliance notices.
- Paragraph-aware chunking: preserve original paragraph breaks, split only when needed, handle long paragraphs safely.
- Metadata compliance improvements: stronger glossary/character detection, prompt prioritization, and post-translation validation.
- Minor fixes and cleanup: consistent token counting across components, clearer progress reporting, and safer error logs.

Notes:

- Backup created under `backups/stable/` with versioned filename.
- Dependencies unchanged from v1.7.stable.

---

## v1.7.5.stable (2025-10-30)

- Enhanced logging with chunk-scoped messages: [Chunk X] start/complete, progress summaries, batch results, and metadata compliance notices.
- Paragraph-aware chunking: preserve original paragraph breaks, split only when needed, handle long paragraphs safely.
- Metadata compliance improvements: stronger glossary/character detection, prompt prioritization, and post-translation validation.
- Minor fixes and cleanup: consistent token counting across components, clearer progress reporting, and safer error logs.

Notes:

- Backup created under `backups/stable/` with versioned filename.
- Dependencies unchanged from v1.7.stable.
