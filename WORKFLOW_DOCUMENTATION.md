# 📋 Tài Liệu Chi Tiết Các Workflow - MTranslator

**Ngày tạo:** 2026-01-09  
**Cập nhật lần cuối:** 2026-03-27  
**Phiên bản:** v9.4  
**Mục đích:** Liệt kê và giải thích chi tiết tất cả các luồng workflow chính và phụ của chương trình

**Ghi chú đồng bộ tài liệu (2026-03-27):**
- `README.md` là tài liệu ưu tiên cho onboarding/chạy nhanh sau khi fork.
- `PROJECT_CONTEXT.md` dùng cho bối cảnh kiến trúc và chính sách runtime.
- `CHANGELOG.md` là nguồn sự thật về timeline thay đổi theo phiên bản.


---

## 📑 Mục Lục

1. [Workflow Chính](#1-workflow-chính)
   - [1.1. Main Translation Workflow](#11-main-translation-workflow)
   - [1.2. Chunking Workflow](#12-chunking-workflow)
   - [1.3. Translation Execution Workflow](#13-translation-execution-workflow)
   - [1.4. Chunk Merging & Validation Workflow](#14-chunk-merging--validation-workflow)
   - [1.5. Output Formatting Workflow](#15-output-formatting-workflow)
   - [1.6. EPUB Layout-Preserving Workflow](#16-epub-layout-preserving-workflow)

2. [Workflow Phụ](#2-workflow-phụ)
   - [2.1. Input Preprocessing Workflow](#21-input-preprocessing-workflow)
   - [2.2. OCR Workflow](#22-ocr-workflow)
   - [2.3. API Key Initialization Workflow](#23-api-key-initialization-workflow)
   - [2.4. Metadata Loading Workflow](#24-metadata-loading-workflow)
   - [2.5. Post-EPUB Conversion Workflow](#25-post-epub-conversion-workflow)
   - [2.6. Periodic Flush Workflow](#26-periodic-flush-workflow)
   - [2.7. Gemini Context Caching Workflow](#27-gemini-context-caching-workflow)
   - [2.8. Adaptive Rate Limiting & Admission Control (Phase 4 & 6)](#28-adaptive-rate-limiting--admission-control)
   - [2.9. Dynamic Work Stealing Workflow (Phase 7)](#29-dynamic-work-stealing-workflow)
   - [2.10. Specialized QA Editor Pipeline Workflow (Phase 7.5)](#210-specialized-qa-editor-pipeline-workflow)

3. [Workflow Tương Tác](#3-workflow-tương-tác)
   - [3.1. Review & User Choice Workflow](#31-review--user-choice-workflow)
   - [3.2. Progress Resume Workflow](#32-progress-resume-workflow)

---

## 1. Workflow Chính

### 1.1. Main Translation Workflow

**Mục đích:** Quy trình dịch thuật chính từ đầu đến cuối

**Entry Point:** `main.py` → `main_async()` → `NovelTranslator.run_translation_cycle_with_review()` (core engine của MTranslator)

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN TRANSLATION WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION (main_sync)
   ├─ Load config.yaml
   ├─ Validate API keys (nếu không dùng optimized workflow)
   └─ Return config và valid_keys

2. ASYNC INITIALIZATION (main_async)
   ├─ Input Preprocessing
   │  └─ detect_and_preprocess_input()
   │     ├─ Detect file type
   │     ├─ PDF scan → OCR workflow (xem 2.2)
   │     └─ Return processed file path
   │
   ├─ Initialize NovelTranslator (Facade)
   │  └─ **setup_resources_async()**
   │     └─ **InitializationService.initialize_all()**
   │        ├─ Initialize HybridKeyManager (Optimized Workflow)
   │        ├─ Load metadata (Style, Glossary, Relations)
   │        ├─ Initialize managers (Progress, Prompt, Model Router)
   │        ├─ Initialize GeminiAPIService
   │        └─ Return resources dict
   │
   └─ Start translation cycle

3. TRANSLATION CYCLE (run_translation_cycle_with_review)
   ├─ **Metadata Check** (InitializationService.check_metadata)
   ├─ Parse input file → Extract text
   ├─ Clean text (remove noise, normalize)
   ├─ Chunk novel (SmartChunker - paragraph-aware)
   ├─ **warm_up_resources** (InitializationService.warm_up_resources)
   │  ├─ Build static prefix (instructions, metadata)
   │  └─ Create/Retrieve context caches per key
   ├─ Load progress (nếu có)
   ├─ **Execute Translation** (ExecutionManager.translate_all)
   │  └─ Coordinate workers with key-affinity
   ├─ Merge chunks → Validate
   ├─ Format output → Save TXT/DOCX
   └─ Convert to EPUB (nếu cần)

4. COMPLETION
   ├─ Generate completion report
   ├─ Ask for additional formats (DOCX, PDF)
   └─ Cleanup resources
```

**Files liên quan:**
- `main.py` - Entry point
- `src/translation/translator.py` - Core translation logic
- `src/preprocessing/input_preprocessor.py` - Input detection & preprocessing

**Điều kiện thành công:**
- Tất cả chunks được dịch thành công
- Merge và validation pass
- Output file được tạo thành công

---

### 1.2. Chunking Workflow

**Mục đích:** Chia văn bản thành các chunks phù hợp để dịch

**Entry Point:** `SmartChunker.chunk_novel()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      CHUNKING WORKFLOW                           │
└─────────────────────────────────────────────────────────────────┘

1. INPUT VALIDATION
   ├─ Check novel_text không rỗng
   └─ Check novel_text là string

2. PARAGRAPH SPLITTING
   ├─ _split_into_paragraphs()
   │  ├─ Split by '\n' (line breaks)
   │  ├─ Preserve empty lines
   │  └─ Return list of paragraphs
   │
   └─ Log: Số paragraphs được phát hiện

3. CHUNK ACCUMULATION (Paragraph-Aware)
   ├─ Initialize:
   │  ├─ chunks = []
   │  ├─ chunk_id = 0
   │  ├─ current_chunk_paragraphs = []
   │  └─ current_tokens = 0
   │
   ├─ For each paragraph:
   │  ├─ Count tokens (với cache)
   │  │
   │  ├─ IF paragraph quá dài (> hard_limit):
   │  │  ├─ Chốt chunk hiện tại (nếu có)
   │  │  ├─ _split_long_paragraph() → sentences
   │  │  └─ Add sentences vào chunks
   │  │
   │  └─ ELSE (paragraph bình thường):
   │     ├─ IF current_tokens + para_tokens > hard_limit:
   │     │  ├─ Check incomplete paragraph
   │     │  ├─ IF incomplete → Add next para (continue)
   │     │  └─ ELSE → Chốt chunk hiện tại
   │     │
   │     └─ Add paragraph vào current_chunk
   │
   └─ Add final chunk (nếu có)

4. MARKER WRAPPING (nếu use_markers = True)
   ├─ _create_chunk_markers(chunk_id)
   │  ├─ Format: simple → [CHUNK:{id}:START/END]
   │  └─ Format: uuid → [CHUNK_START:{id}_{uuid}]
   │
   └─ _wrap_chunk_with_markers()
      └─ Return: start_marker + text + end_marker

5. VALIDATION
   ├─ _validate_chunks_no_duplicate()
   │  ├─ Check overlap giữa chunks liên tiếp (hash-based)
   │  ├─ Check total length consistency
   │  └─ Check paragraph occurrences
   │
   └─ Log warnings nếu có issues

6. RETURN
   └─ List[Dict] với structure:
      ├─ 'global_id': int
      ├─ 'text': str (với markers)
      ├─ 'text_original': str (không có markers)
      └─ 'tokens': int
```

**Files liên quan:**
- `src/preprocessing/chunker.py` - SmartChunker class

**Tối ưu hóa:**
- Token counting cache
- Regex compilation một lần
- Join paragraphs cache
- Hash-based validation

**Đặc điểm:**
- Paragraph-aware (không cắt giữa paragraph)
- Xử lý paragraphs quá dài (split thành sentences)
- Xử lý paragraphs bị cắt (thêm paragraph tiếp theo)
- Marker-based tracking (nếu bật)

---

### 1.3. Translation Execution Workflow

**Mục đích:** Dịch các chunks song song với context awareness

**Entry Point:** `NovelTranslator._translate_all_chunks()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                 TRANSLATION EXECUTION WORKFLOW                   │
└─────────────────────────────────────────────────────────────────┘

1. PREPARATION (NovelTranslator._translate_all_chunks)
   ├─ **InitializationService.warm_up_resources()** (if not done)
   ├─ **ExecutionManager.translate_all()**
   │  ├─ Filter chunks cần dịch
   │  ├─ Partition chunks (Segment-based for key affinity)
   │  └─ Initialize workers (max_parallel_workers)

2. PARALLEL TRANSLATION (ExecutionManager._dedicated_worker_consumer)
   ├─ For each worker (async):
   │  ├─ Staggered startup (random jitter)
   │  ├─ Acquire API key từ HybridKeyManager (get_key_for_worker)
   │  │  ├─ Key-Affinity (preferred dedicated key)
   │  │  ├─ Fallback to Shared Pool
   │  │  └─ **Global Round Robin Scan** (Fallback if dedicated key fails)
   │  │
   │  ├─ Rate limiting
   │  │  └─ await asyncio.sleep(delay_between_requests)
   │  │
   │  ├─ Build context (với context optimization)
   │  │  ├─ Get context chunks (cached)
   │  │  │  ├─ Original context chunks (trước/sau)
   │  │  │  ├─ Translated context chunks (nếu có)
   │  │  │  ├─ Context break detection (chapter/scene changes)
   │  │  │  └─ Best context selection (proximity + relevance)
   │  │  │
   │  │  ├─ Style analysis (nếu có translated context)
   │  │  │  ├─ Pace (average sentence length)
   │  │  │  ├─ Tone (formal/informal/neutral)
   │  │  │  ├─ Register (formal/informal)
   │  │  │  └─ Dialogue ratio
   │  │  │
   │  │  ├─ Relevant glossary terms
   │  │  └─ Active characters (nếu document_type = "novel")
   │  │
   │  ├─ PROMPT BUILDING
   │  │  ├─ IF context_cache_active (context_cache_name is not None):
   │  │  │  └─ build_dynamic_prompt() (Gồm: dynamic context, chunk text)
   │  │  ├─ ELSE:
   │  │  │  └─ build_main_prompt() (Full prompt: instructions + metadata + context + chunk)
   │  │  │
   │  │  ├─ Context integration
   │  │  ├─ Style analysis adaptation (nếu enabled)
   │  │  ├─ Document type guidelines
   │  │  └─ Marker preservation (nếu bật)
   │  │
   │  ├─ Analyze complexity
   │  │  └─ Determine model (Flash vs Pro)
   │  │
   │  ├─ Translate (SmartModelRouter với Google GenAI SDK support)
   │  │  ├─ Pass cached_content reference (nếu context_cache_active)
   │  │  ├─ Auto-detect SDK (google-genai mới hoặc google-generativeai cũ)
   │  │  ├─ Try Flash model first
   │  │  ├─ Fallback Pro model (nếu cần)
   │  │  └─ Handle errors (quota, rate limit, etc.) với error classification
   │  │
   │  ├─ [PHASE 7.5] QA EDITOR PASS (BẮT BUỘC nếu enabled)
   │  │  ├─ If enabled OR CJK detected:
   │  │  │  ├─ Detect Active Characters (RelationManager)
   │  │  │  ├─ Build Editor Prompt (Strict checks & Addressing rules)
   │  │  │  ├─ Execute QA with Key Rotation retry
   │  │  │  └─ Re-validate CJK & Commit
   │  │
   │  ├─ Validate result
   │  │  ├─ Check main_result không None
   │  │  ├─ Check có 'translation' key
   │  │  └─ Check translation không rỗng
   │  │
   │  ├─ Save chunk (batch write với periodic flush)
   │  │  └─ progress_manager.save_chunk_result()
   │  │     ├─ Add to write buffer
   │  │     ├─ Flush nếu buffer đầy (batch_write_size)
   │  │     └─ Flush nếu đã qua flush_interval (5 phút)
   │  │
   │  └─ Return key to HybridKeyManager
   │
   └─ Track progress (completed, failed)

3. ERROR HANDLING
   ├─ API key errors (với error classification)
   │  ├─ Quota exceeded → Parse retryDelay, mark key cool-down (dynamic)
   │  ├─ Rate limit → Parse retryDelay, mark key rate-limited (dynamic)
   │  ├─ Invalid key → Mark key inactive (no retry)
   │  ├─ Network error → Mark key cool-down (1 minute)
   │  ├─ Timeout → Mark key cool-down (30 seconds)
   │  ├─ Generation error → Mark key cool-down (5 minutes)
   │  ├─ Server error → Mark key cool-down (2 minutes)
   │  └─ Unknown error → Mark key cool-down (1 minute)
   │
   ├─ Translation errors
   │  ├─ Retry với exponential backoff
   │  ├─ Fallback to Pro model (nếu Flash fails)
   │  └─ Mark chunk as failed sau max retries
   │
   └─ Network errors
      ├─ Retry với backoff
      └─ Mark chunk as failed sau max retries

4. COMPLETION REPORT
   ├─ Count completed chunks
   ├─ Count failed chunks
   ├─ Calculate statistics
   └─ Log completion report
```

**Files liên quan:**
- `src/translation/translator.py` - NovelTranslator class
- `src/translation/prompt_builder.py` - Prompt building
- `src/translation/model_router.py` - Model routing
- `src/services/hybrid_key_manager.py` - API key management

**Đặc điểm:**
- Parallel execution (async/await)
- Context-aware translation
- Metadata integration
- Real-time progress tracking
- Automatic error recovery

---

### 1.4. Chunk Merging & Validation Workflow

**Mục đích:** Ghép các chunks đã dịch và validate tính toàn vẹn

**Entry Point:** `NovelTranslator._merge_all_chunks()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│            CHUNK MERGING & VALIDATION WORKFLOW                  │
└─────────────────────────────────────────────────────────────────┘

1. SYNC COMPLETED CHUNKS (_sync_completed_chunks)
   ├─ Scan disk cho chunk files (.txt, .txt.gz)
   ├─ Update completed_chunks dict (file-first approach)
   └─ Return sync result

2. PARALLEL LOAD CHUNKS (_parallel_load_chunks)
   ├─ Load chunks từ disk song song (với semaphore)
   ├─ Support lazy loading (individual_files strategy)
   └─ Return list of (chunk, translation) tuples

3. CLASSIFY CHUNKS
   ├─ complete_chunks: Có translation đầy đủ
   ├─ missing_chunks: Không có file hoặc translation
   └─ empty_chunks: File tồn tại nhưng rỗng

4. INCREMENTAL MERGE (complete_chunks)
   ├─ Merge complete chunks vào partial_content_parts
   └─ Track merge progress

5. RETRY FAILED CHUNKS (_retry_failed_chunks)
   ├─ IF missing_chunks hoặc empty_chunks:
   │  ├─ Retry translation với exponential backoff
   │  ├─ Track retried_success count
   │  └─ Track still_failed list
   │
   ├─ IF retry fails và allow_partial_merge = False:
   │  └─ STOP process (không merge)
   │
   └─ IF retry fails và allow_partial_merge = True:
      └─ Merge available chunks + marker cho missing

6. VALIDATION (_validate_and_merge_chunks_optimized)
   ├─ Marker-first validation
   │  ├─ _validate_with_markers()
   │  │  ├─ Check missing markers
   │  │  ├─ Check duplicate markers
   │  │  └─ Remove markers nếu valid
   │  │
   │  └─ IF markers invalid:
   │     ├─ _fix_duplicate_markers() (nếu có duplicate)
   │     ├─ Delete chunks với missing markers
   │     ├─ Remove từ progress_manager
   │     └─ _retry_failed_chunks() để dịch lại
   │
   ├─ Similarity-based validation (fallback)
   │  └─ _validate_and_merge_with_similarity()
   │     ├─ Check sentence overlap (Jaccard similarity)
   │     └─ Check paragraph overlap
   │
   └─ Merge chunks
      └─ _merge_with_markers() hoặc simple join

7. FINAL VALIDATION
   ├─ Check chunk count consistency
   ├─ Check không có empty chunks
   └─ Check full_content không rỗng

8. RETURN
   └─ Merged text (str) hoặc None (nếu validation fails)
```

**Files liên quan:**
- `src/translation/translator.py` - Merge logic
- `src/managers/progress_manager.py` - Chunk loading

**Đặc điểm:**
- File-first sync approach
- Parallel loading
- Incremental merging
- Marker-based validation
- Automatic re-translation cho failed chunks
- Hard stop nếu không thể dịch lại

---

### 1.5. Output Formatting Workflow

**Mục đích:** Định dạng và lưu bản dịch cuối cùng

**Entry Point:** `NovelTranslator._handle_option_1()` hoặc `_handle_option_2()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FORMATTING WORKFLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. FORMAT TEXT (OutputFormatter.format_and_save)
   ├─ Normalize paragraphs
   │  ├─ Strict "no merge, no split" policy
   │  ├─ Only normalize titles
   │  └─ Preserve paragraph structure
   │
   ├─ Save TXT file
   └─ Save DOCX file (nếu cần)

2. CONVERT TO EPUB
   ├─ Check config: auto_convert_epub
   ├─ Convert TXT → EPUB (pypandoc)
   │  ├─ Generate table of contents
   │  ├─ Set metadata
   │  └─ Save EPUB file
   │
   └─ Log EPUB path

3. ASK ADDITIONAL FORMATS (_ask_additional_formats)
   ├─ Prompt user (30s timeout):
   │  ├─ Convert to DOCX? (nếu chưa có)
   │  └─ Convert to PDF?
   │
   ├─ IF user chooses DOCX:
   │  └─ _convert_to_docx() (pypandoc)
   │
   └─ IF user chooses PDF:
      └─ _convert_to_pdf() (pypandoc)

4. COMPLETION
   └─ Return output file paths
```

**Files liên quan:**
- `src/output/formatter.py` - Output formatting
- `tools/convert.py` - Format conversion utilities

**Đặc điểm:**
- Strict paragraph preservation
- Multiple output formats
- Interactive user prompts
- Automatic EPUB conversion

---

### 1.6. EPUB Layout-Preserving Workflow

**Mục đích:** Khi input là file EPUB (text-based) và bật `preprocessing.epub.preserve_layout`, bảo lưu và phục hồi format/layout của EPUB gốc (file-per-chapter, CSS, ảnh, font) trong output.

**Entry Point:** `NovelTranslator._prepare_translation()` (rẽ nhánh EPUB layout) → `_finalize_translation()` (xuất EPUB + master.html).

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                 EPUB LAYOUT-PRESERVING WORKFLOW                  │
└─────────────────────────────────────────────────────────────────┘

1. ĐIỀU KIỆN
   ├─ input.novel_path kết thúc bằng .epub
   └─ config.preprocessing.epub.preserve_layout = true

2. PREPARE (parse_epub_with_layout)
   ├─ Đọc EPUB gốc (ebooklib)
   ├─ Spine → TEXT_MAP (text_id, chapter_id, original_text) + chapters_html (DOM đã gán data-ntid)
   └─ Chunk từ TEXT_MAP (chunker_epub) → all_chunks có text_ids

3. DỊCH (giống luồng chính)
   └─ Dịch từng chunk, lưu bản dịch theo global_id

4. FINALIZE (nhánh _epub_layout_state)
   ├─ build_translation_map_from_chunks → text_id → bản dịch
   ├─ apply_translations_to_chapters → chapter_id → HTML đã dịch
   ├─ Nếu output.epub_reinject.output_html_master: build_html_master → lưu master.html (progress_dir)
   └─ Nếu output.epub_reinject.output_epub: write_epub_from_translated_chapters
      ├─ Đọc lại EPUB gốc
      ├─ Thay nội dung từng chương XHTML bằng HTML đã dịch
      ├─ Copy nguyên CSS, ảnh, font, nav, toc
      └─ Ghi file {novel_name}_translated.epub tại epub_output_dir (mặc định output_path)
```

**Files liên quan:**
- `src/preprocessing/epub_layout_parser.py` - Parse EPUB → TEXT_MAP + chapters_html
- `src/preprocessing/chunker_epub.py` - Chunk từ TEXT_MAP
- `src/output/epub_reinject.py` - apply_translations_to_chapters, build_html_master, write_epub_from_translated_chapters
- `src/translation/translator.py` - Rẽ nhánh prepare/finalize

**Config:** `preprocessing.epub.preserve_layout`, `output.epub_reinject.output_epub`, `output.epub_reinject.output_html_master`, `output.epub_reinject.epub_output_dir`

**Đặc điểm:**
- Output EPUB giữ cấu trúc file-per-chapter và assets gốc
- Tùy chọn vẫn xuất master.html (Option 4 có thể export thêm từ master bằng pandoc)

---

## 2. Workflow Phụ

### 2.1. Input Preprocessing Workflow

**Mục đích:** Tự động phát hiện và tiền xử lý file đầu vào

**Entry Point:** `detect_and_preprocess_input()` trong `main_async()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                 INPUT PREPROCESSING WORKFLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. FILE TYPE DETECTION
   ├─ Check file extension
   ├─ IF not PDF:
   │  └─ Return original path (không cần preprocessing)
   │
   └─ IF PDF:
      └─ Continue to PDF type detection

2. PDF TYPE DETECTION
   ├─ detect_pdf_type()
   │  ├─ Try PyPDF2 (fastest)
   │  ├─ Try pdfplumber (fallback)
   │  └─ Determine: "scan" hoặc "text-based"
   │
   ├─ IF text-based:
   │  └─ Return original path (không cần OCR)
   │
   └─ IF scan:
      └─ Continue to OCR workflow

3. PROCESSED FILE CHECK
   ├─ Check if processed file exists
   ├─ IF exists:
   │  ├─ Ask user: reuse hay re-run OCR?
   │  └─ IF reuse:
   │     └─ Return processed file path
   │
   └─ IF not exists hoặc re-run:
      └─ Continue to OCR

4. OCR EXECUTION
   ├─ ocr_file() với skip_completion_menu=True
   │  └─ (Xem OCR Workflow 2.2)
   │
   ├─ Save processed TXT file
   └─ Return processed file path

5. FALLBACK (nếu OCR fails)
   ├─ Try extract_text_from_pdf()
   ├─ IF success:
   │  └─ Save và return processed file
   │
   └─ IF fails:
      └─ Raise error
```

**Files liên quan:**
- `src/preprocessing/input_preprocessor.py` - Input detection
- `src/preprocessing/ocr_reader.py` - OCR execution

**Đặc điểm:**
- Automatic detection
- User interaction cho reuse decision
- Fallback mechanism
- Seamless integration với main workflow

---

### 2.2. OCR Workflow

**Mục đích:** Nhận dạng văn bản từ PDF scan hoặc hình ảnh

**Entry Point:** `ocr_file()` trong `ocr_reader.py`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        OCR WORKFLOW                              │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION
   ├─ Load OCR config
   ├─ Detect bundled binaries (Tesseract, Poppler)
   ├─ Check dependencies
   └─ Initialize OCR engine

2. PDF TO IMAGES
   ├─ Convert PDF → Images (pdf2image)
   │  ├─ DPI: 250 (configurable)
   │  ├─ Format: JPEG (memory optimization)
   │  └─ Batch rendering (nếu nhiều pages)
   │
   └─ Cache images (nếu cần)

3. IMAGE PREPROCESSING (nếu enabled)
   ├─ For each image:
   │  ├─ Grayscale conversion (nếu enabled)
   │  ├─ Contrast enhancement (1.2x)
   │  └─ Sharpness enhancement (1.1x)
   │
   └─ Save preprocessed images

4. OCR EXECUTION
   ├─ For each page (parallel nếu có thể):
   │  ├─ Detect language (VN, EN, CN)
   │  ├─ Set PSM mode:
   │  │  ├─ PSM 3 (auto) cho Chinese
   │  │  └─ PSM 6 cho simple text
   │  │
   │  ├─ Run Tesseract OCR
   │  └─ Extract text
   │
   └─ Combine all pages → raw_text

5. AI CLEANUP (nếu enabled)
   ├─ Split text ở ranh giới câu
   ├─ Parallel cleanup với Gemini API:
   │  ├─ Remove headers/footers/page numbers
   │  ├─ Fix OCR errors
   │  └─ Remove noise
   │
   └─ Combine cleaned chunks → cleaned_text

6. AI SPELL CHECK (nếu enabled)
   ├─ Split text ở ranh giới câu
   ├─ Parallel spell check với Gemini API:
   │  ├─ Fix spelling errors
   │  ├─ Fix OCR character confusion
   │  └─ Restore paragraph structure
   │
   └─ Combine checked chunks → final_text

7. SAVE & COMPLETION
   ├─ Save processed TXT file
   ├─ IF skip_completion_menu:
   │  └─ Return text (auto-save)
   │
   └─ ELSE:
      ├─ Show completion menu
      ├─ Auto-save sau 10 phút (nếu không tương tác)
      └─ Return text
```

**Files liên quan:**
- `src/preprocessing/ocr_reader.py` - OCR module

**Đặc điểm:**
- Image preprocessing
- Language auto-detection
- PSM mode optimization
- Parallel AI cleanup/spell check
- Check & Resume support
- Memory optimization

---

### 2.3. API Key Initialization Workflow

**Mục đích:** Test và gán API keys tối ưu khi khởi động

**Entry Point:** `KeyInitializationWorkflow.test_and_assign_keys()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│            API KEY INITIALIZATION WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. SEQUENTIAL KEY TESTING
   ├─ For each API key (tuần tự):
   │  ├─ Test với GeminiAPIChecker
   │  │  ├─ Send test request
   │  │  ├─ Measure response time
   │  │  └─ Classify error (nếu có)
   │  │
   │  ├─ IF valid:
   │  │  ├─ Add to assigned_keys (nếu chưa đủ max_workers)
   │  │  └─ Add to pending_keys (nếu đã đủ)
   │  │
   │  └─ IF invalid:
   │     ├─ Classify error type
   │     ├─ Calculate cool-down delay
   │     └─ Add to cool_down_keys
   │
   └─ Delay giữa các tests (tránh rate limit)

2. KEY ASSIGNMENT
   ├─ Assign keys cho workers (đến max_workers)
   │  └─ assigned_keys: List[str]
   │
   └─ Remaining valid keys → pending_keys

3. COOL-DOWN MANAGEMENT
   ├─ For each cool-down key:
   │  ├─ Determine error type:
   │  │  ├─ invalid_key → No retry
   │  │  ├─ quota_exceeded → 1 hour
   │  │  ├─ rate_limit → 5 minutes
   │  │  ├─ network_error → 1 minute
   │  │  └─ timeout → 30 seconds
   │  │
   │  └─ Set cool-down until time
   │
   └─ Return cool-down info

4. STRICT ENFORCEMENT & ADAPTIVE SCALING (New in v5.1)
   ├─ Check Active Keys:
   │  └─ count = key_manager.get_active_key_count()
   │
   ├─ IF count == 0:
   │  ├─ Calculate min_wait_time (từ rate_limit_reset của các keys)
   │  ├─ IF min_wait < 5 minutes:
   │  │  ├─ Log "Sleeping X seconds..."
   │  │  ├─ **asyncio.sleep(min_wait)**
   │  │  └─ Retry check active keys
   │  │
   │  └─ IF min_wait > 5 minutes OR Retry Failed:
   │     └─ **Raise ResourceExhaustedError** ("CRITICAL: No available API keys") -> STOP
   │
   └─ IF count > 0:
      ├─ **Set max_workers = count** (Adaptive Scaling)
      └─ Return initialized key_manager

5. RETURN RESULT
   └─ KeyManager ready for ExecutionManager
```

**Files liên quan:**
- `src/services/key_initialization_workflow.py` - Key initialization
- `src/utils/api_key_validator.py` - Key validation
- `src/services/hybrid_key_manager.py` - Key management

**Đặc điểm:**
- Sequential testing (tránh rate limit)
- Smart error classification
- Dynamic cool-down periods
- Worker assignment optimization

---

### 2.4. Metadata Loading Workflow

**Mục đích:** Tải và validate metadata (style, glossary, relations)

**Entry Point:** `NovelTranslator.setup_resources_async()` → `InitializationService.initialize_all()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                  METADATA LOADING WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION (via InitializationService.initialize_all)
   ├─ **StyleManager.__init__()**
   │  ├─ Load style profile JSON
   │  ├─ Normalize keys (VN -> EN)
   │  └─ Store in self.profile
   │
   ├─ **GlossaryManager.__init__()**
   │  ├─ Load glossary CSV
   │  ├─ AI fix CSV errors (nếu có)
   │  ├─ Build lookup & regex patterns
   │  └─ Store in self.glossary_df
   │
   ├─ **RelationManager.__init__()**
   │  ├─ Load relations CSV
   │  ├─ AI fix CSV errors (nếu có)
   │  ├─ Build character patterns
   │  └─ Store in self.relations_df

2. METADATA COMPLIANCE CHECK (InitializationService.check_metadata)
   ├─ Standardized `is_loaded()` check cho tất cả managers
   ├─ Check style profile:
   │  ├─ IF loaded: Log ✅ Loaded (N entries)
   │  └─ ELSE: Log ⚠️ Not loaded
   │
   ├─ Check glossary:
   │  ├─ IF loaded: Log ✅ Loaded (N terms)
   │  └─ ELSE: Log ⚠️ Not loaded
   │
   ├─ Check character relations:
   │  ├─ IF loaded: Log ✅ Loaded (N relations)
   │  └─ ELSE: Log ℹ️ No relations defined

3. WARNING SUMMARY
   ├─ IF không có metadata nào:
   │  └─ Log: ❌ CẢNH BÁO: Không có metadata
   │
   └─ IF thiếu glossary:
      └─ Log: ⚠️ CẢNH BÁO: Glossary thiếu

4. MARK AS CHECKED
   └─ Set _metadata_checked = True (chỉ check một lần)
```

**Files liên quan:**
- `src/managers/style_manager.py` - Style profile
- `src/managers/glossary_manager.py` - Glossary
- `src/managers/relation_manager.py` - Character relations
- `src/utils/csv_ai_fixer.py` - CSV error fixing

**Đặc điểm:**
- Lazy loading
- AI-powered CSV fixing
- Single check (không nhắc lại)
- Clear warnings

---

### 2.5. Post-EPUB Conversion Workflow

**Mục đích:** Hỏi người dùng về các format bổ sung sau EPUB

**Entry Point:** `NovelTranslator._ask_additional_formats()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│              POST-EPUB CONVERSION WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. PROMPT USER
   ├─ Display options:
   │  ├─ Convert to DOCX? (nếu chưa có)
   │  └─ Convert to PDF?
   │
   ├─ Timeout: 30 seconds
   └─ Default: Skip (nếu timeout)

2. DOCX CONVERSION (_convert_to_docx)
   ├─ IF user chooses DOCX:
   │  ├─ Check pypandoc available
   │  ├─ Convert TXT → DOCX (pypandoc)
   │  ├─ Save DOCX file
   │  └─ Log success
   │
   └─ Return DOCX path (hoặc None)

3. PDF CONVERSION (_convert_to_pdf)
   ├─ IF user chooses PDF:
   │  ├─ Check pypandoc available
   │  ├─ Convert TXT → PDF (pypandoc)
   │  ├─ Save PDF file
   │  └─ Log success
   │
   └─ Return PDF path (hoặc None)

4. COMPLETION
   └─ Log all output file paths
```

**Files liên quan:**
- `src/translation/translator.py` - Conversion methods
- `tools/convert.py` - Conversion utilities

**Đặc điểm:**
- Interactive prompts
- Timeout handling
- Multiple format support
- Optional conversions

---

### 2.6. Periodic Flush Workflow

**Mục đích:** Batch save với periodic flush để cân bằng performance và data safety

**Entry Point:** `ProgressManager.save_chunk_result()` → `_flush_buffer()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERIODIC FLUSH WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. SAVE CHUNK (save_chunk_result)
   ├─ Add chunk to write buffer (_write_buffer)
   │  └─ _write_buffer[chunk_id] = translation_text
   │
   ├─ Check buffer size
   │  ├─ IF len(_write_buffer) >= batch_write_size (10):
   │  │  └─ Trigger flush
   │  │
   │  └─ ELSE:
   │     └─ Check time interval
   │
   └─ Check time interval
      ├─ Calculate time_diff = current_time - _last_flush_time
      │
      ├─ IF time_diff < 0 (clock skew):
      │  ├─ Reset _last_flush_time = current_time
      │  └─ Log warning
      │
      ├─ IF time_diff > flush_interval * 2 (large time difference):
      │  └─ Force flush (safety measure)
      │
      └─ IF time_diff >= flush_interval (5 phút):
         └─ Trigger flush

2. FLUSH BUFFER (_flush_buffer)
   ├─ Try flush:
   │  ├─ For each chunk in buffer:
   │  │  ├─ Write to file (individual_files strategy)
   │  │  │  ├─ Normal file: chunk_{id}.txt
   │  │  │  └─ Compressed: chunk_{id}.txt.gz (nếu enabled)
   │  │  │
   │  │  └─ Update completed_chunks dict
   │  │
   │  ├─ Update _last_flush_time = current_time
   │  └─ Clear _write_buffer
   │
   └─ IF flush fails (OSError/Exception):
      ├─ Log error
      ├─ Keep buffer (không clear)
      ├─ Keep _last_flush_time (không update)
      └─ Retry ở lần tiếp theo

3. FLUSH ALL (flush_all)
   ├─ Called on:
   │  ├─ Program exit (atexit.register)
   │  ├─ Ctrl+C (signal handler)
   │  └─ Manual call
   │
   └─ Force flush tất cả chunks trong buffer
      └─ (Same logic as _flush_buffer)
```

**Files liên quan:**
- `src/managers/progress_manager.py` - ProgressManager class

**Đặc điểm:**
- Batch write: Giảm I/O operations
- Periodic flush: Flush mỗi 5 phút để giảm data loss risk
- Error recovery: Tự động retry nếu flush fail
- Edge cases: Xử lý clock skew và large time differences
- Config validation: Đảm bảo config values hợp lệ

**Config:**
- `storage.batch_write_size`: 10 (số chunks trong buffer)
- `storage.flush_interval`: 300 (5 phút, tính bằng giây)

---

### 2.7. Error Recovery Workflow

**Mục đích:** Xử lý và phục hồi từ các lỗi trong quá trình dịch

**Entry Point:** Various error handlers trong `translator.py`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERROR RECOVERY WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. API KEY ERRORS (với error classification)
   ├─ Quota Exceeded:
   │  ├─ Parse retryDelay từ API response (nếu có)
   │  ├─ Calculate dynamic delay (dựa trên quota status)
   │  ├─ Mark key as quota_exceeded
   │  ├─ Set cool-down time (dynamic hoặc 1 hour default)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Rate Limit:
   │  ├─ Parse retryDelay từ API response (nếu có)
   │  ├─ Mark key as rate_limited
   │  ├─ Set cool-down time (dynamic hoặc 5 minutes default)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Invalid Key:
   │  ├─ Mark key as inactive (no retry)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Network Error:
   │  ├─ Mark key cool-down (1 minute)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Timeout:
   │  ├─ Mark key cool-down (30 seconds)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Generation Error:
   │  ├─ Mark key cool-down (5 minutes)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   ├─ Server Error:
   │  ├─ Mark key cool-down (2 minutes)
   │  ├─ Get new key từ shared pool
   │  └─ Retry request
   │
   └─ Unknown Error:
      ├─ Mark key cool-down (1 minute)
      ├─ Get new key từ shared pool
      └─ Retry request

2. TRANSLATION ERRORS
   ├─ Content Blocked:
   │  ├─ Log warning
   │  ├─ Mark chunk as failed
   │  └─ Continue với chunk tiếp theo
   │
   ├─ Generation Error:
   │  ├─ Retry với exponential backoff
   │  ├─ Fallback to Pro model (nếu Flash fails)
   │  └─ Mark as failed sau max retries
   │
   └─ Network Error:
      ├─ Retry với exponential backoff
      └─ Mark as failed sau max retries

3. CHUNK VALIDATION ERRORS
   ├─ Missing Markers:
   │  ├─ Delete chunk file
   │  ├─ Remove từ progress_manager
   │  └─ Re-translate chunk
   │
   ├─ Duplicate Markers:
   │  ├─ Fix duplicate markers
   │  └─ Re-validate
   │
   └─ Missing Content:
      ├─ Detect missing chunks
      └─ Re-translate với retry logic

4. MERGE ERRORS
   ├─ IF missing chunks:
   │  ├─ Retry translation
   │  ├─ IF retry fails và allow_partial_merge = False:
   │  │  └─ STOP process
   │  │
   │  └─ IF retry fails và allow_partial_merge = True:
   │     └─ Merge available + marker cho missing
   │
   └─ IF validation fails:
      └─ Return None (không merge)
```

**Files liên quan:**
- `src/translation/translator.py` - Error handlers
- `src/services/hybrid_key_manager.py` - Key error handling
- `src/translation/model_router.py` - Translation error handling

**Đặc điểm:**
- Automatic retry
- Exponential backoff
- Fallback mechanisms
- Graceful degradation

---

### 2.8. Adaptive Rate Limiting & Admission Control
(Phases 4 & 6)

**Mục đích:** Kiểm soát tốc độ gửi request, ngăn chặn lỗi 429 và quá tải hệ thống.

**Cơ chế:**
1. **Token Bucket Algorithm (Phase 4):**
   - Mỗi API Key quản lý một `TokenBucket`.
   - Giới hạn RPM (Requests Per Minute) mềm dẻo, cho phép burst ngắn hạn nhưng đảm bảo long-term stability.
   - Thay thế `asyncio.sleep()` tĩnh bằng `bucket.wait_for_tokens()`.

2. **Adaptive Admission Control (Phase 6):**
   - `APIKeyManager` theo dõi tỷ lệ "Healthy Keys" (Active & No Cooldown).
   - `AdmissionController` chặn worker tham gia nếu hệ thống quá tải (<30% healthy keys).
   - Worker tự động "ngủ đông" (sleep) thay vì crash khi gặp bão lỗi.

---

### 2.9. Dynamic Work Stealing Workflow
(Phase 7)

**Mục đích:** Tối ưu hóa việc sử dụng tài nguyên API keys, loại bỏ thời gian chết (idle time).

**Thay đổi so với Partitioning cũ:**
- **Cũ:** Chia đều chunks cho workers. Worker nhanh làm xong -> Ngồi chơi.
- **Mới (Work Stealing):**
  - Tất cả chunks vào `asyncio.PriorityQueue` (ưu tiên theo ID).
  - Workers liên tục "cướp" (pull) task từ hàng đợi.
  - Worker nhanh làm nhiều, worker chậm làm ít -> Tổng thời gian ngắn nhất.

**Context Preservation Strategy:**
- Khi worker lấy Chunk N, nó query `translated_chunks_map` để lấy context Chunk N-1.
- **Fallback:** Nếu N-1 chưa xong (do parallel race), tự động dùng **Original Text** của N-1 làm context (kết hợp với Glossary để đảm bảo nhất quán entity).

---

## 3. Workflow Tương Tác

### 3.1. Review & User Choice Workflow

**Mục đích:** Cho phép người dùng review và chọn hành động tiếp theo

**Entry Point:** `NovelTranslator.run_translation_cycle_with_review()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│              REVIEW & USER CHOICE WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. TRANSLATION CYCLE
   └─ Run translation → Get failed_chunks và docx_path

2. COMPLETION CHECK
   ├─ IF not failed_chunks và docx_path:
   │  └─ Success → Continue to review
   │
   └─ ELSE:
      └─ Error → Stop process

3. USER MENU
   ├─ Display options:
   │  ├─ Option 1: Dịch lại từ đầu
   │  ├─ Option 2: Dịch lại chunks bị xóa
   │  └─ Option 3: Thoát
   │
   └─ Get user choice

4. HANDLE OPTION
   ├─ Option 1 (_handle_option_1):
   │  ├─ Clear progress
   │  ├─ Re-translate all chunks
   │  ├─ Merge và format
   │  └─ Ask additional formats
   │
   ├─ Option 2 (_handle_option_2):
   │  ├─ Detect deleted chunks
   │  ├─ Re-translate deleted chunks
   │  ├─ Merge và format
   │  └─ Ask additional formats
   │
   └─ Option 3:
      └─ Exit
```

**Files liên quan:**
- `src/translation/translator.py` - Review workflow

**Đặc điểm:**
- Interactive menu
- Multiple options
- Progress preservation
- User-friendly prompts

---

### 3.2. Progress Resume Workflow

**Mục đích:** Tiếp tục dịch từ điểm đã dừng

**Entry Point:** `NovelTranslator._translate_all_chunks()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│                  PROGRESS RESUME WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. LOAD PROGRESS
   ├─ progress_manager.load_progress()
   │  ├─ Load progress JSON
   │  ├─ Load completed chunks
   │  └─ Load chunk files (lazy loading)
   │
   └─ Return progress state

2. FILTER CHUNKS
   ├─ For each chunk:
   │  ├─ Check if already completed
   │  ├─ Check if file exists
   │  └─ IF completed:
   │     └─ Skip translation
   │
   └─ Only translate incomplete chunks

3. RESUME TRANSLATION
   ├─ Translate only incomplete chunks
   ├─ Save progress (batch write với periodic flush)
   │  ├─ Add to write buffer
   │  ├─ Flush nếu buffer đầy (batch_write_size)
   │  └─ Flush nếu đã qua flush_interval (5 phút)
   └─ Update progress state

4. COMPLETION
   └─ All chunks completed → Ready for merge
```

**Files liên quan:**
- `src/managers/progress_manager.py` - Progress management

**Đặc điểm:**
- Automatic resume
- Lazy loading
- Incremental save
- Progress preservation

---

## 📊 Tổng Kết

### **Workflow Chính (5):**
1. Main Translation Workflow
2. Chunking Workflow
3. Translation Execution Workflow
4. Chunk Merging & Validation Workflow
5. Output Formatting Workflow

### **Workflow Phụ (7):**
1. Input Preprocessing Workflow
2. OCR Workflow
3. API Key Initialization Workflow
4. Metadata Loading Workflow
5. Post-EPUB Conversion Workflow
6. Periodic Flush Workflow
7. Error Recovery Workflow

### **Workflow Tương Tác (2):**
1. Review & User Choice Workflow
2. Progress Resume Workflow

---

## 🔗 Liên Kết Giữa Các Workflow

```
Main Translation Workflow
├─→ Input Preprocessing Workflow
│  └─→ OCR Workflow (nếu PDF scan)
│
├─→ API Key Initialization Workflow (startup)
│
├─→ Metadata Loading Workflow (startup)
│
├─→ Chunking Workflow
│
├─→ Translation Execution Workflow
│  ├─→ Periodic Flush Workflow (batch save)
│  ├─→ Error Recovery Workflow (on errors)
│  └─→ Progress Resume Workflow (if resuming)
│
├─→ Chunk Merging & Validation Workflow
│  └─→ Error Recovery Workflow (on validation errors)
│
├─→ Output Formatting Workflow
│  └─→ Post-EPUB Conversion Workflow
│
└─→ Review & User Choice Workflow
   └─→ (Loop back to Translation Execution)
```

---

---

## 📝 Các Cải Tiến v2.0+

### **1. Periodic Flush**
- Batch save với periodic flush (5 phút interval)
- Error recovery: Tự động retry nếu flush fail
- Edge cases: Xử lý clock skew và large time differences
- Config validation: Đảm bảo config values hợp lệ

### **2. Google GenAI SDK Support**
- Hỗ trợ SDK mới (`google-genai`) và SDK cũ (`google-generativeai`)
- Auto-detection SDK availability
- Unified adapter interface

### **3. Context Optimization**
- Context break detection (chapter/scene changes)
- Best context selection (proximity + relevance)
- Enhanced style analysis (pace, tone, register, dialogue ratio)

### **4. Error Classification**
- 8 error types: invalid_key, quota_exceeded, rate_limit, timeout, network_error, generation_error, server_error, unknown
- Dynamic cooldown times (parse retryDelay từ API response)
- Specific handling cho từng error type

### **5. Ctrl+C Handling**
- Graceful shutdown với progress saving
- Signal handlers (SIGINT, SIGTERM)
- Automatic flush on exit

### **6. Circuit Breaker Pattern (Phase 3)**
- Key-specific circuit breakers
- Configurable threshold và cooldown
- Auto-recovery mechanism (CLOSED → OPEN → HALF_OPEN → CLOSED)
- State tracking và statistics
- Integration vào `hybrid_key_manager.py`

### **7. Metrics Collection (Phase 3)**
- Success rate per chunk
- Average time per chunk
- API key usage statistics
- Error rate by type
- Flush operation metrics
- Periodic export to file (JSON format)
- Integration vào `translator.py` và `progress_manager.py`

### **8. Adaptive Timeout (Phase 2)**
- Calculate timeout dựa trên chunk size
- Adjust based on historical response times
- Max/min timeout limits (configurable)
- Exponential smoothing cho historical data
- Integration vào `model_router.py` (ready for use)

### **9. Decoupled Architecture (Phase 7)**
- **Service-Oriented Design**: Tách biệt `NovelTranslator` (God Object) thành các dịch vụ chuyên biệt.
- **InitializationService**: Quản lý toàn bộ luồng khởi tạo tài nguyên và warm-up bất đồng bộ.
- **ExecutionManager**: Điều phối luồng dịch thuật, quản lý workers và worker-key affinity.
- **Improved Reliability**: Xử lý triệt để các lỗi `IndentationError`, `AttributeError` và rò rỉ tài nguyên async.
- **Standardized API**: Thống nhất phương thức `is_loaded()` cho tất cả managers phục vụ việc kiểm tra sức khỏe hệ thống.

### 2.11. Thread-Safe Logging Suppression Workflow (v8.2)

**Mục đích:** Chặn các log rác từ thư viện Google (gRPC, absl) một cách an toàn trong môi trường đa luồng/bất đồng bộ.

**Cơ chế:**
1. **Thread-Safe Initialization**: Sử dụng `threading.Lock` để đảm bảo việc thay thế `sys.stderr` và `sys.stdout` chỉ diễn ra một lần, tránh tranh chấp tài nguyên (Race Condition) khi nhiều workers cùng khởi chạy.
2. **NoisyMessageFilter**: Một wrapper thông minh bọc quanh `sys.stderr`. Nó phân tích nội dung ghi ra, nếu khớp với các patterns rác (ví dụ: ALTS credentials warnings) thì sẽ nuốt chửng (suppress), ngược lại thì ghi ra stream gốc.
3. **Robust Error Handling**: Cơ chế `try...except` bọc quanh lệnh ghi để đảm bảo dù stream gốc có lỗi (ví dụ: bị đóng đột ngột), chương trình chính vẫn không bị crash.
4. **Idempotency**: Hàm `_suppress_google_logs()` có thể được gọi nhiều lần từ nhiều nơi nhưng chỉ thực thi logic cấu hình một lần duy nhất nhờ các cờ trạng thái toàn cục.

**Lợi ích:**
- Giảm nhiễu console đáng kể, giúp người dùng tập trung vào tiến độ dịch thuật.
- Đảm bảo tính ổn định của hệ thống khi chạy song song 40+ workers.
- Không làm rò rỉ tài nguyên khi stream bị thay thế.

---

### 2.7. Gemini Context Caching Workflow

**Mục đích:** Cache các phần tĩnh của prompt để tối ưu token consumption và cost (tiết kiệm 75-90% input tokens).

**Entry Point:** `NovelTranslator._setup_context_cache()`

**Luồng hoạt động:**

```
┌─────────────────────────────────────────────────────────────────┐
│              GEMINI CONTEXT CACHING WORKFLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. PREPARATION (build_cacheable_prefix)
   ├─ Get static instructions (system instructions, CJK guardrails, checklists)
   ├─ Get full style guide
   ├─ Get full glossary (glossary_manager.get_full_glossary_dict)
   ├─ Get full character relations (relation_manager.get_full_relation_text)
   └─ Combine into static prefix text

2. CACHE INITIALIZATION (InitializationService.warm_up_resources)
   ├─ IF context_caching.enabled is False → Skip
   ├─ parallel warm_up_one() cho từng API key:
   │  ├─ Staggered delay (tránh API burst)
   │  ├─ Acquire request semaphore
   │  ├─ Create/Retrieve context cache via GeminiAPIService
   │  │  ├─ Model: gemini-1.5-flash-002 (ưu tiên độ ổn định)
   │  │  └─ Content: cacheable static prefix
   │  └─ Store cache_id in worker_caches map

3. DYNAMIC TRANSLATION (per-chunk)
   ├─ IF self.context_cache_name exists:
   │  ├─ PromptBuilder.build_dynamic_prompt()
   │  │  └─ Gồm: dynamic context, chunk text
   │  └─ ModelRouter: call API với cached_content=self.context_cache_name
   │
   └─ ELSE:
      └─ Fallback to build_main_prompt() (không dùng cache)

4. TERMINATION (End of session)
   └─ Cache tự động hết hạn trên server dựa trên TTL (mặc định 60-300 phút)
```

**Files liên quan:**
- `src/translation/translator.py` - Orchestrator
- `src/services/gemini_api_service.py` - Lifecycle management
- `src/translation/prompt_builder.py` - Prefix vs Dynamic prompt logic
- `src/services/genai_adapter.py` - API integration
- `data/cache/gemini_context_caches.json` - Persistent metadata

**Path contract (runtime):**
- Runtime paths được resolve theo project root qua `src/utils/path_manager.py` (không phụ thuộc CWD).
- `data/output` và `data/reports` được xem là artifacts; có thể để ngoài vòng đời git/repo.

**Ưu điểm:**
- Tiết kiệm đáng kể chi phí (input tokens cho metadata chỉ tính phí cache, rẻ hơn 10x).
- Giảm độ trễ processing cho các metadata lớn.
- Khả năng resume và reuse cache giữa các lần chạy (nếu metadata không đổi).

---

**Lưu ý:** Tài liệu này mô tả các workflow ở mức cao. Để hiểu chi tiết implementation, vui lòng tham khảo source code trong các file tương ứng.

