# 📋 PROJECT CONTEXT - MTranslator

> **Mục đích:** File này tổng hợp toàn bộ thông tin quan trọng về dự án để AI có thể nắm bắt lại ngay khi quay trở lại.

**Cập nhật lần cuối:** 2026-03-28  
**Bàn giao gần nhất:** OCR scan — worker Tesseract độc lập với pool API key; commit `285c69a`.  
**Phiên bản hiện tại:** v9.5 (2026-03-27) - STABLE — *tháng 3/2026: đã siết chia chunk khi dùng Structured IR*

---

## 🎯 **TỔNG QUAN DỰ ÁN**

### **Mục đích:**

Công cụ dịch tiểu thuyết/tài liệu tự động sử dụng Gemini API với các tính năng:

- Dịch thuật song song với context awareness
- OCR cho PDF scan và hình ảnh
- AI cleanup và spell check
- Hỗ trợ nhiều loại tài liệu (novel, technical_doc, academic_paper, manual, medical, general)
- Export sang EPUB/PDF với mục lục tự động và self-healing tags thông qua `master.html`

### **Tình trạng hiện tại (v9.5 - Docs & Script compatibility)**

- Đã triển khai pipeline mới dựa trên `master.html`:
  - `EPUB (gốc) → TEXT_MAP + DOM → dịch → master.html (giữ layout) → EPUB + PDF`.
  - `TXT/DOCX/PDF text-based/scan-based → dịch → TXT tổng → master.html (heading-based) → EPUB + PDF`.
- Hoàn thành các phase kỹ thuật chính:
  - Phase 0–4: Parser EPUB v2, chunker theo TEXT_ID, translation map, re-inject, HTML master template.
  - Phase 5: Tích hợp vào `NovelTranslator` với flag `preprocessing.epub.preserve_layout`.
  - Phase 6: Chuẩn hoá HTML master (`<!DOCTYPE html>`, `<main id="nt-content">`, `<section>` theo chương).
  - Phase 7–8: `build_html_master_from_flat_text` + finalize text-based/scan-based tạo `{novel_name}_master.html` từ TXT tổng (heading-based) trong `progress_dir`.
  - Phase 9–11: QA per-chunk (config overlap), Batch QA, helper HTML→EPUB + option 4 trong UIHandler.
  - Phase 12: Integration test end-to-end cho pipeline TXT → finalize → TXT + master.html → option 4 export; và pipeline EPUB layout → master.html → option 4 export (`tests/test_integration_master_txt_pipeline.py`).
  - Phase 13: Quality profile – `quality_profile.name` trong config (fast_low_cost | balanced_default | max_quality) được áp dụng lên config khi khởi tạo NovelTranslator (`src.utils.quality_profile.apply_quality_profile`).
  - Phase 14 (v9.2/v9.3): Unified Layout & Quality Audit. Khắc phục lỗi re-injection bảng biểu (EPUB) bằng **Aggressive CSS Reset (!important)**, phục hồi headings/images (Master HTML) và tối ưu hóa ngưỡng skip logic cho sách tiếng Anh. Cơ chế báo cáo success/failed cũng được chuẩn hóa.
- Kế hoạch tiếp theo:
  - Tùy chọn khác theo nhu cầu (A/B test profile, thêm profile tùy biến).
  - Tối ưu hóa hiệu năng nạp CSS.
  - Duy trì đồng bộ tài liệu lõi và script khởi chạy/backup theo path contract.

### **Chia nhỏ văn khi dùng Structured IR (cập nhật 2026-03-28)**

- Khi bật cấu trúc IR, chương trình gom theo tiêu đề rồi chia nhỏ. Nếu một đoạn vẫn quá dài (ví dụ PDF ít dấu chấm phẩy), sẽ **cắt thêm theo độ dài** rồi **kiểm tra lần cuối** để mỗi mảnh không vượt ngưỡng an toàn đã cấu hình.

### **OCR PDF scan (cập nhật 2026-03-28)**

- **Bộ nhớ:** Không còn render cả quyển PDF vào RAM qua stdout của Poppler. Mỗi trang ghi file tạm (JPEG/PNG theo `ocr.image_format`), OCR bằng Tesseract, xóa file trước trang sau.
- **Ngôn ngữ:** Trong `config`, `ocr.lang` có thể dùng dạng ngắn `EN`, `VN`, `CN+EN` — chuỗi được map sang `eng`, `vie`, v.v. trước khi gọi Tesseract (không dùng nhầm `EN.traineddata`).
- **Song song:** OCR từng trang qua `ThreadPoolExecutor` — `ocr.pdf_ocr_max_workers` (tuỳ chọn) cùng trần CPU/config (`tesseract_max_workers`, `tesseract_workers_per_cpu`); tùy chọn `tesseract_cap_from_performance` để min với `performance.max_parallel_workers`. Ghép text đúng thứ tự trang (không liên quan pool API key).

### **Marker Guardrail (Unreleased) — Bảo toàn tính toàn vẹn chunk**

- **Guardrail theo markers chỉ bật đúng ngữ cảnh:**
  - `guardrail_enabled = preprocessing.chunking.use_markers OR original_has_markers`.
  - Khi `guardrail_enabled=false`: finalize/merge **bỏ qua** marker-first validation và **không** trigger vòng “missing markers → xóa chunk → dịch lại”.
  - Khi `guardrail_enabled=true`: giữ strict marker validation như thiết kế (không nới lỏng guardrail).
- **Sub-chunk Fallback (khi chunk lớn fail Gate 2):**
  - Đã vá để không làm marker START/END bị tách đôi: gắn START vào sub-chunk A, END vào sub-chunk B.
  - Prompt instruction được nâng để preserve marker ngay cả khi input chỉ có START hoặc chỉ có END (case sub-chunk).

### **Reliability Features (v8.3):** ⭐ (MỚI)

- **Zero-Wait Key Rotation:** Tích hợp trực tiếp SmartKeyDistributor vào GeminiAPIService. Tự động đổi Key và retry ngay lập tức khi gặp lỗi 503/Timeout.
- **Fuzzy CJK Glossary Matching:** Nhận diện thuật ngữ thông minh xuyên khoảng trắng, đảm bảo tuân thủ metadata tuyệt đối.
- **Recency-Optimized Prompts:** Tối ưu hóa vị trí các chỉ dẫn quan trọng (Recency Bias) để AI bám sát quy tắc văn phong.
- **Surgical Output Polishing:** Tự động lọc rác AI (Checklists, Thinking) và sửa lỗi ngắt đoạn/Heading chuẩn xác cho Ebooks.

### **Tech Stack:**

- **Language:** Python 3.11+
- **AI API:** Google Gemini API (gemini-2.5-flash, gemini-1.5-pro)
- **SDK:** Google GenAI SDK mới (`google-genai`) và SDK cũ (`google-generativeai`) với auto-detection
- **OCR:** Tesseract OCR + pytesseract + OCRmyPDF
- **PDF Processing:** pdf2image, PyPDF2, pdfplumber
- **Image Processing:** Pillow (PIL)
- **Config:** YAML (PyYAML)
- **EPUB:** pandoc
- **Async:** asyncio với parallel processing

---

## 📁 **CẤU TRÚC DỰ ÁN**

```text
MTranslator/
├── main.py                    # Entry point chính
├── gui.py                     # GUI interface (nếu có)
├── config/
│   └── config.yaml           # Config chính (QUAN TRỌNG)
├── src/
│   ├── translation/          # Core translation logic
│   │   ├── translator.py     # NovelTranslator class
│   │   ├── prompt_builder.py # Build AI prompts
│   │   └── model_router.py   # Route requests to Gemini API
│   ├── preprocessing/        # Input processing
│   │   ├── file_parser.py    # Parse TXT/EPUB/DOCX/PDF
│   │   ├── text_cleaner.py   # Clean text
│   │   ├── chunker.py        # SmartChunker — chia đoạn; nhánh IR có cắt theo ngưỡng khi đoạn quá dài
│   │   ├── ocr_reader.py     # OCR module (QUAN TRỌNG)
│   │   └── input_preprocessor.py  # Detect & preprocess input
│   ├── managers/             # Metadata managers
│   │   ├── style_manager.py  # Style profile manager
│   │   ├── glossary_manager.py # Glossary manager
│   │   ├── relation_manager.py # Character relations manager
│   │   └── progress_manager.py # Progress tracking với periodic flush
│   ├── services/             # API services
│   │   ├── gemini_api_service.py # Gemini API wrapper
│   │   ├── hybrid_key_manager.py # API key management
│   │   └── genai_adapter.py  # SDK adapter (mới/cũ)
│   ├── output/               # Output formatting
│   │   └── formatter.py      # Format conversion
│   └── utils/                # Utilities
│       ├── free_tier_filter.py # Free tier filtering
│       ├── account_deduplicator.py # Account deduplication
│       ├── error_formatter.py # Error formatting
│       ├── context_break_detector.py # Context break detection
│       ├── context_selector.py # Context selection
│       ├── style_analyzer.py # Style analysis
│       └── csv_ai_fixer.py   # AI CSV repair (QUAN TRỌNG)
├── scripts/                  # Helper scripts
│   └── diagnose_api_keys.py  # Diagnose API keys & models
├── docs/                     # Documentation
│   └── archive/              # Archived documentation
├── data/                     # Runtime data directories
│   ├── input/                # Input files
│   ├── output/               # Output artifacts (không bắt buộc track git)
│   ├── progress/             # Progress tracking
│   ├── reports/              # Report artifacts (không bắt buộc track git)
│   └── cache/                # Cache files
```

---

## 🧭 **PATH CONTRACT & WORKSPACE POLICY**

- Nguồn cấu hình runtime chuẩn: `config/config.yaml`.
- Resolve đường dẫn nội bộ theo project root qua `src/utils/path_manager.py`.
- Giữ ổn định contract cho runtime chính:
  - `data/input`
  - `data/progress`
  - `data/metadata`
  - `data/cache`
- Artifacts lớn nên tách khỏi lifecycle repo:
  - `backup/*`
  - `data/output/*`
  - `data/reports/*`

---

## 🔑 **CÁC TÍNH NĂNG CHÍNH**

### **1. Translation Engine**

- **Contextual Translation:** Sử dụng context từ chunks trước/sau
- **Document Type Customization:** Khác nhau cho novel, technical, medical, etc.
- **Metadata Integration:** Style profile, glossary, character relations
- **Gemini Context Caching:** Cache static prompt elements (system instructions, CJK guardrails, full glossary, relations) to reduce token costs by 75-90%.
- **High-Throughput (v8.0):** Tối ưu hóa cho chunks **20,000 tokens** (v3 logic), pacing RPM/RPD chặt chẽ.
- **3-Tier Quality Gate:** Structural, Coverage (paragraphs + headers), CJK Residual checks.
- **Sub-chunk Fallback:** Tự động chia nhỏ và dịch tuần tự với context chaining khi chunk lớn fail Gate 2.
- **Prompt Refinement (v8.1):** Tối ưu hóa prompt size, loại bỏ hướng dẫn dư thừa, và tích hợp cơ chế xưng hô tự động theo thể loại (Genre-Aware Addressing).
- **Hybrid Logic:** Lưu ngay khi hoàn thành + báo cáo batch
- **QA Editor (v9.0, Phase 9–10):**
  - Per-chunk QA với word-overlap gating, cho phép cấu hình `translation.qa_editor.min_word_overlap_ratio` để tinh chỉnh độ khắt khe khi chấp nhận bản edit.
  - Batch QA hậu kỳ: gom các câu còn sót CJK từ nhiều chunks, xử lý theo batch (cấu hình `translation.qa_editor.max_batch_size`), rồi tự động áp dụng sửa đổi trở lại `all_chunks`.
 - **HTML → EPUB Helper (Phase 11):** Tách riêng helper `export_master_html_to_epub(master.html → EPUB)` để có thể convert trực tiếp từ `master.html` đã giữ layout, dùng cấu hình `output.html_master_epub_output` (mặc định `output_path`).

### **2. OCR Module** ⭐ (QUAN TRỌNG)

- **Input:** PDF scan, images (JPG, PNG, WEBP, BMP, TIFF)
- **Languages:** VN, EN, CN (auto-detect Simplified/Traditional Chinese)
- **Workflow:**
  1. OCR với Tesseract (PSM 3 cho Chinese, có image preprocessing)
  2. AI Cleanup (loại bỏ header/footer/noise, sửa lỗi OCR) — có phase timeout và giới hạn chờ key
  3. AI Spell Check (sửa lỗi chính tả, phục hồi cấu trúc) — có phase timeout và max no-key waits (tránh treo sau cleanup)
- **Features:**
  - Image preprocessing (grayscale, contrast, sharpness enhancement)
  - Chunking ở ranh giới câu (không cắt giữa câu)
  - Check & Resume (tự động phát hiện và tiếp tục từ bước đã hoàn tất)
  - Auto-retry failed chunks
  - Phase timeout và giới hạn chờ key cho Cleanup/Spell check (config: `phase_timeout_seconds`, mặc định 3600s)
  - Memory optimization (batch rendering, JPEG caching)

### **3. Document Type System**

- **novel:** Tối ưu cho tiểu thuyết (nhịp điệu, đa dạng hội thoại)
- **technical_doc:** Tối ưu cho tài liệu kỹ thuật (chính xác, thuật ngữ)
- **academic_paper:** Tối ưu cho bài báo khoa học (formal, citations)
- **manual:** Tối ưu cho hướng dẫn (rõ ràng, từng bước)
- **medical:** Tối ưu cho tài liệu y học (thuật ngữ chuyên ngành)
- **general:** Mặc định cho các loại khác

### **4. Metadata Extraction**

- **Style Profile:** Phong cách dịch (formal/casual, tone, etc.)
- **Glossary:** Thuật ngữ và bản dịch tương ứng
- **Character Relations:** Mối quan hệ nhân vật (cho novel)

---

## 🔄 **WORKFLOW CHÍNH**

### **Workflow dịch thuật:**

```text
1. Input Detection (input_preprocessor.py)
   ├─ PDF scan → OCR workflow → TXT processed
   ├─ PDF text-based → Extract text trực tiếp
   └─ TXT/EPUB/DOCX → Parse trực tiếp

2. Preprocessing
   ├─ Parse file → Extract text
   ├─ Clean text (text_cleaner.py)
   └─ Chunk novel (SmartChunker - paragraph-aware)

3. Metadata Loading
   ├─ Style profile (nếu có)
   ├─ Glossary (nếu có)
   └─ Character relations (nếu có)

4. Translation & Caching
   ├─ Setup Context Cache (_setup_context_cache):
   │  ├─ Build static prefix (instructions, full metadata)
   │  └─ Create/Retrieve Gemini Context Cache
   ├─ For each chunk:
   │  ├─ Build dynamic prompt (context, chunk text)
   │  ├─ Route to Gemini API with cached_content reference
   │  ├─ Save chunks ngay khi hoàn thành
   │  └─ Track progress (progress_manager.py)

5. Output
   ├─ Format final text (formatter.py)
   ├─ Merge chunks → TXT
   └─ Convert to EPUB (nếu cần)
```

### **OCR Workflow:**

```text
1. Detect PDF type (scan vs text-based)
2. Nếu scan:
   ├─ Convert PDF → Images (pdf2image)
   ├─ Preprocess images (grayscale, contrast, sharpness)
   ├─ OCR với Tesseract (PSM 3, language auto-detect)
   ├─ Chia chunks ở ranh giới câu
   ├─ AI Cleanup (loại bỏ noise, sửa lỗi OCR)
   ├─ AI Spell Check (sửa lỗi chính tả, phục hồi cấu trúc)
   └─ Save processed TXT
3. Nếu text-based:
   └─ Extract text trực tiếp (PyPDF2/pdfplumber)
```

---

## ⚙️ **CẤU HÌNH QUAN TRỌNG**

### **config/config.yaml - Các section chính:**

#### **1. API Keys:**

```yaml
api_keys:
  - "your-gemini-api-key-1"
  - "your-gemini-api-key-2"  # Hỗ trợ nhiều keys để load balancing
```

#### **2. Input:**

```yaml
input:
  novel_path: "data/input/novel.txt"
  document_type: "novel"  # novel, technical_doc, academic_paper, manual, medical, general
```

#### **3. OCR:**

```yaml
ocr:
  enabled: true
  tesseract_cmd: "C:/Program Files/Tesseract-OCR/tesseract.exe"
  poppler_path: "C:/Program Files/poppler-24.08.0/Library/bin"
  lang: "CN"  # VN, EN, CN, VN+EN, CN+EN
  psm: 3  # 3 (auto) cho Chinese, 6 cho simple text
  dpi: 250
  preprocess_image: true
  preprocess_grayscale: true
  preprocess_enhance_contrast: true
  preprocess_enhance_sharpness: true
  ai_cleanup:
    enabled: true
    model: "gemini-2.5-flash"
    chunk_size: 50000
  ai_spell_check:
    enabled: true
    model: "gemini-2.5-flash"
    chunk_size: 50000
```

#### **4. Translation:**

```yaml
translation:
  model: "gemini-2.5-flash"  # hoặc "gemini-1.5-pro"
  max_parallel_workers: 5
  context_chunks: 2  # Số chunks context trước/sau
  enable_final_cleanup_pass: false
```

---

## 🐛 **CÁC VẤN ĐỀ ĐÃ GIẢI QUYẾT**

### **1. Paragraph Merging Issue**

- **Vấn đề:** Paragraph ngắn bị merge không đúng trong file TXT tổng
- **Giải pháp:** Strict "no merge, no split" policy trong `formatter.py`
- **File:** `src/output/formatter.py` - `_normalize_paragraphs()`

### **2. PDF Page Break Chunking**

- **Vấn đề:** Chunks bị cắt giữa paragraph do page break
- **Giải pháp:** SmartChunker tôn trọng paragraph boundaries
- **File:** `src/preprocessing/chunker.py`

### **3. Header/Footer Cleanup**

- **Vấn đề:** Header/footer trong PDF làm suy giảm chất lượng dịch
- **Giải pháp:** AI cleanup với prompt cụ thể, có "golden rule" giữ lại nếu không chắc chắn
- **File:** `src/translation/prompt_builder.py` - `_build_header_footer_cleanup_section()`

### **4. OCR Quality cho Chinese Text**

- **Vấn đề:** Chất lượng OCR thấp cho PDF scan tiếng Trung
- **Giải pháp:**
  - Image preprocessing (grayscale, contrast, sharpness)
  - PSM 3 (auto) thay vì PSM 6
  - Cleanup prompt cụ thể cho Chinese OCR errors
  - Spell check prompt tập trung vào sửa lỗi OCR
- **File:** `src/preprocessing/ocr_reader.py`

### **5. CSV Parsing Errors**

- **Vấn đề:** CSV files (glossary, relations) bị parse lỗi
- **Giải pháp:** AI CSV fixer tự động sửa lỗi parsing
- **File:** `src/utils/csv_ai_fixer.py`

### **6. OCR Integration vào Main Workflow**

- **Vấn đề:** OCR module không tích hợp tự động vào workflow dịch
- **Giải pháp:** `input_preprocessor.py` tự động detect và preprocess
- **File:** `src/preprocessing/input_preprocessor.py`, `main.py`

---

## 📝 **CÁC CẢI TIẾN GẦN ĐÂY**

### **v8.2 Improvements (Latest - 2026-02-24)**

#### **1. Unicode Fix for PowerShell Scripts**

- ✅ **PowerShell 5.1 UTF-8 Support**: Fixed Vietnamese display issues by setting `$OutputEncoding`, `[Console]::InputEncoding`, `[Console]::OutputEncoding` and `chcp 65001` command.
- ✅ **Script Encoding**: Updated all PowerShell scripts to save in UTF-8 with BOM format.

#### **2. Algorithm Documentation**

- ✅ **ALGORITHM_DOCUMENTATION.md**: Created comprehensive documentation of the API Key Management & Chunking Optimization Algorithm.
- ✅ **Gemini 3 Flash Preview Support**: Documented limits (RPM, TPM, RPD) and optimization strategies.

#### **3. Trifecta Pipeline v7.0 (Auto-healing)**

- ✅ **Self-Healing Loop**: Pipeline tự động phát hiện lỗi qua `checklist.py` và kích hoạt OpenCode sửa lỗi (tối đa 3 lần thử).
- ✅ **JSON Reporting**: Lưu trữ lịch sử chạy và kết quả kiểm định vào `data/reports/trifecta_results.json`.
- ✅ **Smart Context Refinement**: Tự động trích xuất log lỗi từ lần chạy trước để làm context cho lần sửa lỗi tiếp theo.

#### **4. Centralized Memory (v8.0)**

- ✅ **AGENTS.md**: Thiết lập file bộ nhớ trung tâm để điều phối thông tin giữa Gemini CLI, OpenCode và Antigravity.
- ✅ **Auto-Update**: Pipeline tự động cập nhật trạng thái Task và Last Update vào `AGENTS.md` sau khi hoàn thành.

### **v8.1.2 Improvements (2026-02-12):**

#### **1. EPUB Reading Order Fix**

- ✅ **Structural Accuracy**: Sửa lỗi xáo trộn nội dung chương khi parse EPUB. Chuyển từ `get_items_of_type` sang `book.spine` để tuân thủ thứ tự đọc chuẩn của file.
- ✅ **Sequential Consistency**: Đảm bảo volume/chapter được ghép nối chính xác tuyệt đối (1->2->3).

#### **2. Architecture Documentation**

- ✅ **API Orchestration Guide**: Tài liệu hóa chi tiết cơ chế điều phối API và Worker tại `docs/API_WORKER_ORCHESTRATION.md`.
- ✅ **High-Availability Algorithms**: Giải trình các thuật toán Affinity, Adaptive Scaling, và Zero-Wait Replacement.

### **v8.1 Improvements (2026-02-11):**

### **v8.0 Improvements (2026-02-10):**

### **v7.2 Improvements (2026-02-08):**

#### **1. Non-Fiction & Academic Support**

- ✅ **Specialized Pipelines**: Dedicated logic for Academic, Technical, Medical docs.
- ✅ **Adaptive Prompts**: `PromptBuilder` prioritizes accuracy and terminology over literary flair for non-fiction.
- ✅ **Metadata Mapping**: Support for non-fiction metadata columns.

#### **2. Advanced CJK Validation (Strict Mode)**

- ✅ **Zero Tolerance**: Raise specific errors if CJK characters persist.
- ✅ **Contextual Retry**: Surgical repair with surrounding context.
- ✅ **Transliteration Fallback**: Auto-transliterate if translation fails.

#### **3. API Key Management Hardening**

- ✅ **Zombie Key Detection**: Identify and exclude keys with high error rates.
- ✅ **Pool Health Metrics**: Better tracking of active vs total keys.

### **v7.0 Improvements (2026-02-01):**

#### **1. Hyper-Optimized Performance**

- ✅ **Glossary & Relations:** Speedup **7x-100x** bằng cách dùng Substring Pre-check & Lazy Regex.
- ✅ **Result:** Giảm đáng kể overhead CPU trong phase phân tích metadata.

#### **2. Critical Reliability Fixes**

- ✅ **SmartKeyDistributor Fix:** Sửa lỗi crash `AttributeError` khi hết quota.
- ✅ **Robust Quota Handling:** Hệ thống giờ đây chờ đợi hoặc dừng an toàn thay vì crash.
- ✅ **Async File I/O:** Chuyển các tác vụ đọc file nặng sang async thread pool.

#### **3. Full Refactoring**

- ✅ **Modules:** Clean up translation, managers, utils modules.
- ✅ **Type Hints:** Thêm type hints đầy đủ cho maintenance dễ dàng hơn.

### **v6.0 Improvements (Phase 7.5 - 2026-01-29):**

#### **1. Mandatory QA Editor Pipeline**

- ✅ **Workflow Overhaul**: QA Editor pass giờ đây chạy **BẮT BUỘC** cho mọi chunk (nếu enabled) thay vì chỉ chạy khi sót CJK. Điều này tạo ra sự phân hóa chuyên môn trong worker: Dịch thô (Draft) -> Biên tập (Editor).
- ✅ **Character Addressing (Xưng hô)**: Tích hợp `RelationManager` vào QA; Editor giờ đây nhận diện được các nhân vật trong đoạn văn và áp dụng đúng quy tắc xưng hô từ `character_relations.csv`.

#### **2. Robust QA Execution**

- ✅ **Retry & Key Rotation logic**: QA Editor được bổ sung cơ chế retry với key rotation. Nếu API call fail, hệ thống tự động báo cáo lỗi khóa, lấy khóa mới và thử lại tối đa 3 lần.

#### **3. Antigravity Kit Integration**

- ✅ **Intelligence Boost**: Tích hợp bộ công cụ Antigravity (Skills, Agents, Workflows) để hỗ trợ phát triển, gỡ lỗi và tự động hóa quy trình dịch thuật.

### **v5.5 Improvements (Latest - 2026-01-29):**

#### **1. AutoFix Compliance Recovery**

- ✅ **Post-Validation Recovery:** Nếu chunk vi phạm glossary, hệ thống tự động sửa bằng regex và re-validate. Giảm tỉ lệ FAILED do AI quên thuật ngữ.
- ✅ **Smart Validation:** Chỉ coi là vi phạm nếu CN/Pinyin vẫn còn sót trong bản dịch.

#### **2. Optimized CJK Handling (Smart QA Editor)**

- ✅ **CJK Detection:** Tự động phát hiện mọi ký tự Trung/Nhật/Hàn còn sót trong bản dịch.
- ✅ **Context-Aware Fix:** QA Editor nhận diện CJK sót + Source Text + Glossary + Style để dịch bổ sung chính xác 100%.
- ✅ **Full Style Injection:** Đảm bảo QA Editor nhận đủ 315+ dòng style profile (không còn bị trôi văn phong).

#### **3. Smart Chunk Balancing**

- ✅ **Dynamic Merging:** Tự động gộp các chunks nhỏ (<100 tokens) để tiết kiệm quota API (tối ưu cho Gemini Flash).
- ✅ **Genre-Aware Prompts:** Inject hướng dẫn xưng hô/văn phong theo thể loại tiểu thuyết (Xianxia, Wuxia, etc.).

### **v2.0+ Improvements (Latest - 2025-01-09):**

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

#### **4. Documentation Cleanup**

- ✅ Dọn dẹp và archive các files lạc hậu (64 files archived)
- ✅ Cập nhật toàn bộ documentation
- ✅ Tạo DOCUMENTATION_INDEX.md

### **v5.1 Improvements (2026-01-24):**

#### **1. Strict Key Enforcement**

- ✅ **Chặn & Chờ:** Nếu 0 key active, hệ thống tự động tính toán thời gian chờ.
- ✅ **Smart Wait:** Nếu cooldown < 5 phút, tự động ngủ đông chờ key hồi phục.
- ✅ **Hard Stop:** Nếu cooldown > 5 phút, dừng chương trình ngay lập tức để tránh treo.

#### **2. Adaptive Worker Scaling**

- ✅ **Dynamic Max Workers:** Số lượng worker tối đa = Số lượng key hợp lệ (xóa bỏ giới hạn cứng 5).
- ✅ **Full Utilization:** Tận dụng 100% tài nguyên key có sẵn (ví dụ: 11 keys -> 11 dedicated threads).

#### **3. Friendly Error Handling**

- ✅ **ResourceExhaustedError:** Exception riêng cho trường hợp hết key.
- ✅ **User-friendly Message:** Thông báo lỗi rõ ràng, gợi ý giải pháp thay vì traceback loằng ngoằng.

#### **4. GenAI Adapter Fixes**

- ✅ Khôi phục toàn bộ các method bị thiếu trong `genai_adapter.py`.
- ✅ Chuẩn hóa việc sử dụng `gemini-2.5-flash` làm mặc định.

### **OCR Improvements (v1.8.stable):**

1. **Image Preprocessing:**
   - Grayscale conversion
   - Contrast enhancement (1.2x)
   - Sharpness enhancement (1.1x)

2. **PSM Mode:**
   - Từ PSM 6 → PSM 3 cho Chinese text
   - Auto-detect layout tốt hơn

3. **Cleanup Prompt:**
   - Prompt cụ thể cho Chinese OCR errors
   - Ví dụ cụ thể về các loại noise
   - Quy tắc "nếu không chắc chắn thì giữ lại"

4. **Spell Check Prompt:**
   - Tập trung vào sửa lỗi OCR thay vì nối câu
   - Danh sách ký tự thường bị nhầm lẫn
   - Nguyên tắc bảo toàn nội dung

### **Workflow Improvements:**

1. **Auto-save trong OCR:**
   - Tự động lưu sau 10 phút nếu không có tương tác
   - Non-blocking input để timer hoạt động

2. **Skip Completion Menu:**
   - `skip_completion_menu` parameter để không block workflow
   - Tự động lưu file khi được gọi từ main workflow

3. **Periodic Flush:**
   - Buffer flush khi đầy (10 chunks) HOẶC đã qua 5 phút
   - Error recovery: Tự động retry nếu flush fail
   - Clock skew handling: Reset timer nếu clock đi ngược

---

## 🔧 **DEPENDENCIES**

### **Core:**

- `google-genai` - Google GenAI SDK mới (khuyến nghị)
- `google-generativeai` - Google GenerativeAI SDK cũ (fallback)
- `PyYAML` - Config parsing
- `tqdm` - Progress bars
- `asyncio` - Async processing

### **OCR:**

- `pytesseract` - Tesseract OCR wrapper
- `pdf2image` - PDF to images
- `Pillow` - Image processing
- `pdfplumber` / `PyPDF2` - PDF text extraction

### **File Processing:**

- `ebooklib` / `BeautifulSoup4` - EPUB parsing
- `python-docx` - DOCX parsing
- `chardet` - Encoding detection

### **Output:**

- `pandoc` (external) - EPUB conversion

---

## 📚 **DOCUMENTATION FILES**

### **Core Documentation:**

- `README.md` - Hướng dẫn cài đặt/sử dụng nhanh sau khi fork
- `PROJECT_CONTEXT.md` - Bối cảnh kỹ thuật tổng quan
- `WORKFLOW_DOCUMENTATION.md` - Workflow chi tiết
- `CHANGELOG.md` - Lịch sử thay đổi theo phiên bản
- `DOCUMENTATION_INDEX.md` - Chỉ mục tài liệu
- `CONVERSATION_HISTORY.md` - Lịch sử các phiên làm việc
- `PROJECT_HANDOVER.md` - Tài liệu bàn giao

### **Guides:**

- `VENV_SETUP_GUIDE.md` - Hướng dẫn setup môi trường Python
- `docs/ACCOUNT_DEDUPLICATION_GUIDE.md` - Hướng dẫn lọc key trùng
- `FORMAT_NORMALIZATION_GUIDE.md` - Hướng dẫn chuẩn hóa format
- `PROMPT_REFERENCE_GUIDE.md` - Prompt reference
- `PROMPT_QUICK_REFERENCE.md` - Prompt quick reference
- `docs/NAS_BACKUP_GUIDE.md` - Hướng dẫn backup stable

### **Recent Analysis & Plan (tiêu biểu):**

- `docs/WORKSPACE_REORG_BASELINE.md` - Baseline an toàn trước/sau workspace reorg
- `docs/AUDIT_AI_KEY_MANAGEMENT.md` - Audit key management
- `docs/EPUB_LAYOUT_ANALYSIS_AND_PLAN.md` - Phân tích và kế hoạch EPUB layout
- `docs/WORKFLOW_AUDIT_HANG_FIXES.md` - Audit/plan khắc phục treo workflow

### **Archive:**

- `docs/archive/` - Archived documentation (64 files)
  - `completed/` - Completed optimization reports
  - `fixes/` - Fix reports
  - `analysis/` - Analysis reports
  - `audits/` - Audit reports
  - `optimizations/` - Optimization reports
  - `reviews/` - Review reports

---

## 🚨 **LƯU Ý QUAN TRỌNG**

### **1. OCR Module:**

- Cần cài đặt Tesseract OCR và Poppler
- Config `tesseract_cmd` và `poppler_path` trong `config.yaml`
- Language packs cho Tesseract (chi_sim, chi_tra cho Chinese)

### **2. Paragraph Handling:**

- **KHÔNG merge/split paragraphs** trong formatter
- Chỉ normalize titles
- Strict preservation của paragraph structure

### **3. Chinese OCR:**

- Dùng PSM 3 (auto) cho layout phức tạp
- Image preprocessing rất quan trọng
- Cleanup và spell check prompts được tối ưu cho Chinese

### **4. API Keys:**

- Hỗ trợ nhiều API keys để load balancing
- Free tier filtering và account deduplication
- Intelligent key management với quota tracking
- Safety settings có thể set `BLOCK_NONE` nếu cần

### **5. Error Handling:**

- CSV parsing errors → Auto-fix với AI
- OCR failures → Auto-retry failed chunks
- Translation failures → Contextual retry với context
- Flush failures → Auto-retry ở lần tiếp theo
- Clock skew → Reset timer và log warning

### **6. Periodic Flush:**

- Buffer flush khi đầy (10 chunks) HOẶC đã qua 5 phút
- Error recovery: Tự động retry nếu flush fail
- Clock skew handling: Reset timer nếu clock đi ngược
- Config: `batch_write_size: 10`, `flush_interval: 300` (5 phút)

---

## 🔍 **CÁCH TÌM HIỂU THÊM**

### **Khi cần hiểu một tính năng:**

1. Đọc file code chính (ví dụ: `ocr_reader.py` cho OCR)
2. Đọc documentation files tương ứng
3. Kiểm tra config trong `config.yaml`
4. Xem các analysis files nếu có

### **Khi cần debug:**

1. Kiểm tra logs (console output)
2. Kiểm tra intermediate files (`_ocred.txt`, `_cleanup.txt`)
3. Kiểm tra progress files trong `data/output/`
4. Xem error messages và stack traces

### **Khi cần cải thiện:**

1. Xem các analysis files để hiểu design decisions
2. Kiểm tra TODO comments trong code
3. Xem các issue đã giải quyết trong CHANGELOG
4. Tham khảo prompt reference guide

---

## 📌 **CHECKLIST KHI QUAY LẠI**

- [ ] Đọc file này (PROJECT_CONTEXT.md)
- [ ] Đọc README.md (v9.4)
- [ ] Đọc DOCUMENTATION_INDEX.md để navigate documentation
- [ ] Kiểm tra config/config.yaml (mục `context_caching`)
- [ ] Kiểm tra dependencies (requirements.txt) - Đã có google-genai
- [ ] Xem CHANGELOG.md để biết các thay đổi mới (v9.4+)
- [ ] Kiểm tra CONVERSATION_HISTORY.md để biết session mới nhất
- [ ] Kiểm tra các file documentation liên quan đến task hiện tại

---

**Lưu ý:** File này nên được cập nhật mỗi khi có thay đổi lớn về:

- Architecture
- Workflow
- Config structure
- Dependencies
- Major bug fixes
