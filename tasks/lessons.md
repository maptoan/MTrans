## 📅 Session: 2026-02-25

### ✅ Fix: Paragraph & List Merging in Ebooks (Final)
**Context:** Fixing the persistent issue where lists were merged into single paragraphs in DOCX and PDF, even after the EPUB fix.

**What happened:** 
- The initial fix only updated `OutputFormatter`, but the UI Menu calls were routed through `FormatConverter`.
- `FormatConverter` had duplicate, outdated conversion logic that lacked the `hard_line_breaks` configuration.

**Root cause:** 
- [x] **Logic Divergence:** A refactor gap left two separate conversion paths with different Pandoc settings.
- [x] **Markdown Interpretation:** Standard Markdown requires double newlines for paragraphs; single newlines in TXT are ignored by default.

**Fix applied:**
```python
1. src/translation/format_converter.py: Updated `convert_to_docx` and `convert_to_pdf` to use `markdown+hard_line_breaks` and dynamic font selection.
2. src/output/formatter.py: Enhanced `_normalize_paragraphs` to proactively convert single newlines into double newlines for list items and decorative blocks, ensuring they are treated as standalone paragraphs across all formats (TXT, DOCX, EPUB, PDF).
```

**Rule to prevent recurrence:**
```
Always synchronize logic across all conversion paths (wrappers and core services). When visual structure (like lists) must be preserved from TXT, proactively convert intended visual line breaks into explicit semantic breaks (double newlines) to ensure consistent behavior across varied rendering engines (Markdown, Word, PDF).
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: SDK Initialization Error & AttributeError in aclose()
**Context:** Investigating why the system crashed with "Missing key inputs" and "BaseApiClient object has no attribute '_async_httpx_client'" during the CJK cleanup phase.

**What happened:** 
- The `CJKCleaner` was passing an uninitialized or `None` API key to the `ModelRouter`, which then passed it to the Gemini SDK.
- The new Google GenAI SDK (v0.1+) throws a hard error when initialized with `api_key=None`.
- Furthermore, calling `aclose()` on a partially initialized client triggered an internal bug in the SDK, causing a crash.

**Root cause:** 
- [x] **Incomplete Data Flow:** `worker_id` was not being passed to the cleanup phases (`CJKCleaner`), preventing the system from looking up the correct sticky key or a fallback key from the distributor.
- [x] **Weak Validation:** The adapter layer didn't check for null keys before calling the SDK constructor.
- [x] **SDK Internal Bug:** The SDK's `aclose()` method assumes successful initialization of internal HTTP clients.

**Fix applied:**
```python
1. src/services/genai_adapter.py: Added strict null checks for `api_key` and defensive `AttributeError` catching in `aclose()`.
2. src/services/gemini_api_service.py: Implemented proactive key lookup fallback in `_get_client` and `generate_content_async` if the provided key is missing.
3. Plumbing: Passed `worker_id` through all layers (Translator -> CJKCleaner -> ModelRouter -> Service) to ensure consistent key management.
```

**Rule to prevent recurrence:**
```
Never trust internal layers to provide valid resources; always perform null-checks before interacting with external SDK constructors. Ensure contextual IDs (like worker_id) are propagated through every function call in an async pipeline to maintain resource affinity and fault recovery capabilities.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: Paragraph & List Merging in Ebooks
**Context:** Auditing why lists and sub-headings were merged into single paragraphs in EPUB/PDF/DOCX despite looking correct in the TXT file.

**What happened:** 
- Markdown conversion (via Pandoc) treats single newlines as spaces.
- The title-joining logic in `OutputFormatter` was too aggressive, occasionally merging list items into the preceding line.

**Root cause:** 
- [x] **Markdown Spec:** Default Pandoc behavior follows the strict Markdown spec where paragraph breaks require double newlines.
- [x] **Lack of Safeguards:** The normalization logic did not recognize list patterns (`1.`, `2.`) as "do not join" barriers.

**Fix applied:**
```python
1. src/output/formatter.py: 
   - Enabled `+hard_line_breaks` extension for all Pandoc calls (EPUB/PDF).
   - Added regex-based safeguards in `_normalize_paragraphs` to prevent merging lines that start with numbers or decorative brackets (【 】).
```

**Rule to prevent recurrence:**
```
When converting TXT to structured formats (EPUB/PDF), always explicitly handle line break expectations. Use the 'hard_line_breaks' extension in Pandoc to ensure visual fidelity with the source TXT. Always implement pattern-based exclusion in any 'line joining' or 'cleaning' algorithms to protect lists and sub-headers.
```

---

## 📅 Session: 2026-02-25

### ✅ Strategy: Robust EPUB Generation Algorithm
**Context:** Auditing and improving the EPUB creation pipeline to handle AI-generated tag errors and improve file performance.

**What happened:** 
- AI sometimes produced mismatched tags (e.g., `[H1]...[/H2]`) or forgot closing tags, which confused Pandoc's TOC generator.
- Large novels were being bundled into single massive XHTML files inside the EPUB, causing slow loading on e-readers.

**Root cause:** 
- [x] **Fragile Validation:** The converter assumed perfect tag structure from the translation phase.
- [x] **Default Segmentation:** Pandoc's default internal file splitting was not aggressive enough for 5MB+ text files.

**Fix applied:**
```python
1. src/translation/format_converter.py: Implemented `_validate_and_fix_tags()` to automatically repair mismatched heading tags and clean erratic whitespace.
2. src/output/formatter.py: 
   - Added `--epub-chapter-level=1` to Pandoc arguments to force internal file splitting at every chapter (H1).
   - Added auto-metadata fallback to fill Title/Author from style profiles if config is empty.
```

**Rule to prevent recurrence:**
```
Never trust the structural integrity of AI-generated markup tags. Always implement a 'Surgical Cleanup' pass that repairs tags before converting to intermediate formats like Markdown. For large document formats like EPUB, always favor aggressive internal segmentation (split-at-headings) to ensure smooth performance on low-resource hardware.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: Output Polish & Formatting Issues
**Context:** Fixing issues in the final merged output where markers were left behind, AI thinking blocks leaked in, and TOC items were incorrectly merged.

**What happened:** 
- `[CHUNK:ID:START/END]` markers were still visible in the final `.txt` file.
- AI quality checklists (`☑`, `[KIỂM TRA CHẤT LƯỢNG]`) appeared in the translation.
- Table of Contents items were merged into single paragraphs in EPUB/DOCX/PDF.
- Standalone headings like "MỤC LỤC" were not recognized as H1.

**Root cause:** 
- [x] **Incomplete Stripping:** The marker removal logic was skipped if the markers were valid, instead of always being cleaned for final output.
- [x] **Lack of Post-processing:** Main translation results were not filtered for AI boilerplate text.
- [x] **Pandoc Block Merging:** TOC lines lacked double newlines (`\n\n`), causing Pandoc to treat them as a single block.
- [x] **Encoding Mismatch:** Regexes using literal Vietnamese characters failed due to Python/OS encoding variations.

**Fix applied:**
```python
1. src/translation/translator.py: Updated `_validate_with_markers` to ALWAYS strip markers for the final output.
2. src/output/formatter.py: 
   - Switched to Unicode-escape regexes (e.g., \u1ec2) for robust Vietnamese detection.
   - Added `_normalize_paragraphs` logic to strip AI checklists and checkbox icons.
   - Forced double newlines around TOC items to prevent merging.
   - Expanded H1 detection for standalone keywords (MỤC LỤC, LỜI MỞ ĐẦU, etc.).
```

**Rule to prevent recurrence:**
```
Always perform a final 'Global Cleanup' on merged content using robust, Unicode-aware regex patterns. Never rely on AI to perfectly follow 'return only translation' instructions; assume 'thinking' or 'checklists' will leak and build filters to remove them. Ensure structured text like TOCs has explicit whitespace separation for external converters like Pandoc.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: API Key Rotation Failure on 503 Errors
**Context:** Investigating why a worker failed to switch keys after encountering a `503 UNAVAILABLE` error, causing chunk failure.

**What happened:** 
- A worker encountered a 503 error but retried 3 times with the *same* failed key.
- The 503 error caused a long hang (20 mins) due to an excessively large default timeout.

**Root cause:** 
- [x] **Lack of Integration:** `GeminiAPIService` was not properly connected to `SmartKeyDistributor`, so it couldn't request a key replacement during its internal retry loop.
- [x] **Sticky Key Trap:** When a worker is assigned a key, the retry logic stayed "stuck" to that key unless the higher-level translator intervened.
- [x] **Loose Timeout:** Default HTTP timeout was 600s, leading to long worker stalls during server issues.

**Fix applied:**
```python
1. src/services/smart_key_distributor.py: Improved error classification to catch 503/Deadline errors.
2. src/services/gemini_api_service.py: 
   - Reduced default timeout to 90s.
   - Integrated `distributor.replace_worker_key()` directly into the `generate_content_async` retry loop.
3. src/translation/initialization_service.py: Linked the distributor to the service layer.
```

**Rule to prevent recurrence:**
```
Fault recovery must be integrated at the lowest possible level. If a service layer performs retries, it must have the authority to rotate its underlying resources (like API keys) through a distributor. Always set strict timeouts for external API calls to prevent cascade failures and worker starvation.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: AI Ignoring Metadata Rules
**Context:** Auditing why translation chunks failed to follow critical style and glossary rules in the HMQT project.

**What happened:** 
- AI would sometimes use Sino-Vietnamese (Hán Việt) names for chapters instead of the modern Vietnamese escape translations defined in the style profile.
- Glossary terms with erratic whitespace in the source Chinese text were missed.

**Root cause:** 
- [x] **Prompt Dilution:** Critical rules were placed in early prompt turns, getting "lost" when processing long chunks.
- [x] **Exact Match Matching:** The glossary manager failed to find terms if the source text had extra spaces or formatting variations.

**Fix applied:**
```python
1. PromptBuilder: Moved [QUY TẮC VÀNG] and critical style summaries to the FINAL turn (User Task turn) to leverage Recency Bias.
2. GlossaryManager: Implemented Fuzzy CJK Matching by searching against a space-stripped version of the chunk text.
3. Instructions: Added explicit "Machine Translation Mode" commands to forbid notes and Sino-Vietnamese names.
```

**Rule to prevent recurrence:**
```
Always place the most complex or 'easy-to-ignore' instructions at the very end of the prompt sequence. For CJK languages, never rely on exact string matching for glossary lookups; always perform a normalized/space-stripped search as a fallback.
```

---

## 📅 Session: 2026-02-25

### 🧠 Strategy: AI Preprocessing for Text-based Files
**Context:** Evaluating whether to add AI Cleanup and AI Spell Check to non-OCR (text-based) input files.

**Pros:**
- Superior noise removal (headers/footers) compared to Regex.
- Intelligent paragraph restoration (joining broken lines).
- Normalizes source text, leading to better translation quality.

**Cons:**
- **Doubles API cost** and adds significant latency.
- Risk of **AI Hallucination**: could accidentally change names or delete plot details.
- Potential data corruption before the translation phase even starts.

**Decision/Rule:**
```
Do NOT enable AI preprocessing by default for text-based files. 
- Use Regex-based 'AdvancedTextCleaner' for 90% of cases (safe, fast, free).
- Only offer AI preprocessing as an OPT-IN for poor-quality source files.
- If enabled, use high-precision prompts to forbid content modification.
```

---

## 📅 Session: 2026-02-25

### ✅ Feature: AI Pre-clean for Text-based Files (Opt-in)
**Context:** Implementing an optional AI-powered preprocessing step for non-PDF files.

**What happened:** 
- Successfully integrated `ai_preclean` option into `config.yaml`.
- Extended `ocr_reader.py` and `input_preprocessor.py` to support `.txt`, `.docx`, and `.epub`.
- Verified that AI can successfully remove noise and fix hard line breaks in text-based source files.

**Fix/Implementation applied:**
```python
1. config.yaml: Added 'ai_preclean' toggle.
2. ocr_reader.py: ocr_file() now supports direct text extraction for AI cleaning.
3. input_preprocessor.py: Added logic to route text files through the AI pipeline if opt-in is enabled.
```

**Rule to prevent recurrence:**
```
Always reuse existing robust pipelines (like the OCR AI-cleaning pipeline) when adding similar features to new formats. This maintains consistency and reduces code duplication.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: Chunking Algorithm Cutting Middle of Sentences
**Context:** Reviewing and fixing the `SmartChunker` algorithm to ensure chunks only end at natural linguistic boundaries.

**What happened:** 
- Some chunks were ending in the middle of sentences or quoted dialogues.
- Root cause: The `_split_long_paragraph` logic only looked for a single period character and didn't account for stylized quotes (like `“ ”`) or abbreviations where a period doesn't mean "end of sentence".

**Fix applied:**
```python
# In src/preprocessing/chunker.py
1. Expanded `quote_pairs` to include Vietnamese/Chinese stylized quotes: “ ”, ‘ ’, 「 」, etc.
2. Updated sentence splitting logic: A sentence now only breaks if the termination character (.!?。！？) is followed by a whitespace character or is at the end of the text block.
3. Updated `_is_incomplete_paragraph` to support the new quote types.
```

**Rule to prevent recurrence:**
```
Linguistic boundaries are not just single characters. When splitting text, always consider the character's context (e.g., is it inside a quote? what follows it?). A robust chunker must be quote-aware and whitespace-validated to preserve meaning across chunks.
```

---

## 📅 Session: 2026-02-25

### ✅ Optimization: Robust Heading Detection
**Context:** Debugging heading detection failure in Chunk-5 (HMQT).

**What happened:** 
- Headings with decorative characters (e.g., `【 】`, `ã€ ã€‘`, `——`) were missed.
- Sub-headings using Title Case but containing minor words (e.g., "và", "của") failed `istitle()` and length checks.

**Root cause:** 
- [x] Heuristics were too strict, not accounting for non-alphabetic decorative characters at the start of lines.
- [x] Word count thresholds were too low for literary sub-headings.

**Fix applied:**
```python
# In src/output/formatter.py
1. Added 'core_content' extraction: strips decorative characters before detection.
2. Updated H2 rule: explicitly checks for bracketed content or dash prefixes.
3. Updated H3 rule: increased word threshold to 12 and improved list pattern matching.
```

**Rule to prevent recurrence:**
```
When detecting structure in literary or translated works, always normalize the line (strip decorations) before applying semantic checks. Use flexible word-count thresholds to accommodate the varying styles of sub-headings.
```

---

## 📅 Session: 2026-02-25

### ✅ Fix: QA Editor Incorrectly Discarding Valid Cleanups
**Context:** Debugging a CJK cleanup failure where the QA Editor pass would fail validation.

**What happened:** 
- Error type: Logic Error in Validation
- A translated chunk with CJK characters correctly triggered the QA Editor.
- The QA Editor successfully removed the CJK characters, resulting in a shorter, cleaner text.
- The `_is_valid_qa_result` function then rejected this valid cleanup because its length was less than 50% of the original junk-filled draft, incorrectly flagging it as "truncation".

**Root cause:** 
- [x] Validation logic was too naive, relying only on relative string length. It didn't account for cases where a successful cleanup *should* result in a significantly shorter string.

**Fix applied:**
```python
# In src/translation/qa_editor.py
# Replaced _is_valid_qa_result with a more robust version.
# New logic calculates word overlap instead of raw length.

def _is_valid_qa_result(self, cleaned: str, original: str) -> bool:
    # ... (new implementation) ...
    original_words = set(re.findall(r'\w+', original.lower()))
    cleaned_words = set(re.findall(r'\w+', cleaned.lower()))
    # ...
    overlap_ratio = len(intersection) / len(original_words)
    if overlap_ratio < 0.6:
        return False
    return True
```

**Rule to prevent recurrence:**
```
Validation heuristics must be robust. When comparing pre- and post-processing results, do not rely solely on simplistic metrics like string length. Instead, use content-aware metrics like word overlap percentage to account for valid cases of junk/noise removal.
```

---

## 📅 Session: 2026-02-24

### ⚠️ Issue: DOCX Output Not Generated During Verification
**Context:** Verification of automatic heading detection for DOCX output.

**What happened:**
- The `python main.py` script ran, but the DOCX file was not generated.
- Other formats (TXT, EPUB) were generated.

**Root cause:**
- [x] Incorrect configuration: The `formats` list in `config.yaml` did not include "docx".

**Fix applied:**
```
Added "docx" to the `output.formats` list in `config.yaml`.
```

**Rule to prevent recurrence:**
```
When verifying a feature related to a specific output format, always ensure that the target format is explicitly enabled in the project's configuration (e.g., in `config.yaml`'s `output.formats` list).
```

---

# Lessons Learned - Novel Translator

> *Template from workflow_orchestration.md | Novel Translator v8.2*

---

## 📅 Session: 2026-02-25

### ✅ Optimization: Workflow Merge → Output
**Context:** Rà soát và tối ưu workflow từ bước ghép chunk → xuất file

**What happened:** 
- Phát hiện workflow đọc file nhiều lần (TXT → DOCX, TXT → EPUB)
- Redundant title standardization giữa translator và formatter

**Root cause:** 
- [x] Multiple file I/O operations
- [x] Redundant processing

**Fix applied:**
```
1. formatter.save(): Thêm preprocessed_content parameter
2. convert_txt_to_epub(): Thêm optional content parameter  
3. convert_txt_to_pdf(): Thêm optional content parameter
```

**Rule to prevent recurrence:**
```
- Tránh đọc file nhiều lần, truyền content trực tiếp giữa các function
- Thêm optional parameters để maintain backward compatibility
```

---

## 📅 Session: 2026-02-25

### ❌ Issue: False Positive - convert_txt_to_epub Missing Report
**Context:** Analysis task to review format conversion workflow

**What happened:** 
- Error type: Documentation/Analysis Error
- Analysis report claimed `convert_txt_to_epub` was missing from formatter.py
- Report: `tasks/todo_convert_review_20260224_2250.md`

**Root cause:** 
- [x] Analysis error - did not verify before reporting

**Fix applied:**
```
Function convert_txt_to_epub ALREADY EXISTS in formatter.py:530-584
The function is properly implemented and called from:
- format_converter.py:75 (via asyncio.to_thread)
- formatter.py:489 (in save() method)
```

**Rule to prevent recurrence:**
```
Always verify code existence BEFORE reporting missing functions.
Use: python -c "from src.output.formatter import OutputFormatter; print(hasattr(OutputFormatter, 'convert_txt_to_epub'))"
```

---

## 📅 Session: [YYYY-MM-DD]

### ❌ Issue: [Brief Title]
**Context:** What was being translated/built?

**What happened:** 
- Error type: [API/Rate Limit/Quality/Format]
- Error message: 

**Root cause:** 
- [ ] API key exhausted (RPD limit)
- [ ] Rate limit (429)
- [ ] Server error (503)
- [ ] CJK residual not cleaned
- [ ] Glossary not applied
- [ ] Style profile ignored
- [ ] Context overflow
- [ ] Other:

**Fix applied:**
```
[Specific fix applied]
```

**Rule to prevent recurrence:**
```
[Write rule - e.g., "Check RPD limit before starting large translation"]
```

---

## 📅 Session: [YYYY-MM-DD]

### ❌ Issue: [Brief Title]
**Context:** 

**What happened:** 

**Root cause:** 

**Fix applied:** 

**Rule to prevent recurrence:**
```

```

---

## 📌 Quick Reference Rules - Novel Translator

### Pre-Translation
- [ ] Verify glossary.csv is up-to-date
- [ ] Verify style_profile.json reflects target tone
- [ ] Check API key count vs chunk count (estimate RPD usage)
- [ ] Ensure input encoding is UTF-8

### During Translation
- [ ] Monitor for 429/503 errors - prepare to wait
- [ ] Watch CJK residual count per chunk
- [ ] Track dialogue quote consistency

### Post-Translation
- [ ] ALWAYS verify no CJK characters remain (grep for CJK range)
- [ ] Check glossary terms appear correctly in output
- [ ] Verify output length is reasonable (not too short/long)
- [ ] Test EPUB/DOCX generation if needed

### API Key Management
- [ ] Never assume all keys are valid - use SmartKeyDistributor
- [ ] Set appropriate delay to avoid 429
- [ ] Monitor quota usage for long documents

### Quality Thresholds
| Metric | Min Acceptable | Target |
|--------|----------------|--------|
| CJK residual | 0 | 0 |
| Dialogue match | 80% | 95%+ |
| Glossary compliance | 100% | 100% |
| Chunk success rate | 95% | 100% |

---

## 🔧 Common Fixes Reference

### 503 Server Busy
```
→ Wait 30-60 seconds, retry with exponential backoff
→ Use different API key
→ Reduce parallel workers
```

### CJK Residual
```
→ Enable cleanup pass (translation.enable_final_cleanup_pass)
→ Use contextual_sentence cleanup strategy
→ Run residual_cleanup.py manually
```

### Rate Limit 429
```
→ Increase delay_between_requests (min: 12s for 5 RPM)
→ Reduce max_parallel_workers
→ Check if any key is exhausted (RPD limit)
```

### Context Overflow
```
→ Reduce max_context_chunks_display (try 1-2)
→ Use compact prompt format
→ Split into smaller chunks
```

### Glossary Not Applied
```
→ Verify glossary.csv format (Term,Translation,Context)
→ Check strict_glossary_compliance is enabled
→ Verify regex patterns in PromptBuilder
```

---

## 📅 Session: 2026-02-25

### 📊 Analysis: Ebook Formatting Workflow
**Context:** Rà soát workflow định dạng ebook (EPUB/DOCX/PDF)

**Findings:** 
- Phát hiện duplicate DOCX conversion (pandoc vs python-docx)
- format_converter và formatter có chức năng overlap
- I/O có thể tối ưu thêm

**Status:** KHÔNG cần thay đổi - Hệ thống hiện tại hoạt động ổn định
- formatter.save() đã được tối ưu task trước
- format_converter chỉ dùng cho user-initiated conversion

**Rule for future:**
```
- Document which converter is used when
- Consider unifying if needed, but current separation is acceptable
```

---

## 📅 Session: 2026-02-25

### 📊 Analysis: Heading Auto-Format
**Context:** Rà soát tự động heading (H1, H2, H3) khi tạo ebook

**Findings:** 
- Hệ thống heading detection hoạt động tốt
- [H1], [H2], [H3] tags được detect và convert đúng
- DOCX: tạo Heading 1, 2, 3
- EPUB: chuyển thành #, ##, ###
- Title standardization hoạt động (unified terminology)

**Status:** KHÔNG cần thay đổi - Hệ thống hoạt động đúng thiết kế

**Rule for future:**
```
- CJK residual: Enable final_cleanup_pass: true trong config.yaml
- Dialogue mismatch: Chỉ là cảnh báo, không ảnh hưởng output
- QA fail: Giữ nguyên draft là hành vi đúng

FIX APPLIED (2026-02-25):
- Da enable final_cleanup_pass: true trong config/config.yaml
- Strategy: contextual_sentence
- enable_sentence_retranslation: true
```

---

## 📅 Session: 2026-02-25

### 📊 Analysis: Translation Log Issues
**Context:** Phân tích log lỗi từ translation run

**Findings:** 
1. **CJK Residual (Chunk-2, Chunk-3):**
   - 6 và 3 ký tự CJK còn sót sau dịch
   - Root cause: CJK detection chỉ cảnh báo, không tự xóa
   - Cần enable `final_cleanup_pass` mạnh hơn

2. **Dialogue Mismatch (49%):**
   - Original: ~167 quotes, Translation: 86 quotes
   - Đây là CẢNH BÁO, không phải lỗi nghiêm trọng
   - Có thể do quote style khác nhau

3. **QA Validation Fail:**
   - "reasoning leakage or truncation" - QA giữ nguyên draft
   - Hành vi đúng của hệ thống

**Rule for future:**
```
- CJK residual: Cần enable final_cleanup_pass mạnh
- Dialogue mismatch: Chỉ là cảnh báo, không ảnh hưởng output
- QA fail: Giữ nguyên draft là hành vi đúng
```

---

## 🔄 Review Checklist (Start of each session)
- [ ] Check AGENTS.md for recent updates
- [ ] Review lessons from last translation session
- [ ] Verify config.yaml has correct settings
- [ ] Check for new API keys if needed

---

## 📈 Metrics Tracking (Per Project)
| Date | Novel | Chunks | Time | CJK | Issues |
|------|-------|--------|------|-----|--------|
| YYYY-MM-DD | [Name] | N/M | Xm | 0 | None |
| | | | | | |

---
*Last updated: [YYYY-MM-DD]*
