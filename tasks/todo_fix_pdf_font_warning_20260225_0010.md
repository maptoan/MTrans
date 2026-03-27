# Project: Novel Translator - Bug Fix
# Date: 2026-02-25
# Task: Fix "Missing character" warnings during PDF conversion.

## 🎯 Task Overview
**Bug:** During the TXT to PDF conversion process, `pypandoc` (using a LaTeX engine) throws "[WARNING] Missing character" for circled numbers (①, ②, etc.).
**Root Cause:** The default font used by the LaTeX engine (`lmroman10-regular`) does not contain glyphs for these specific Unicode characters.
**Goal:** Modify the PDF conversion logic to specify a font with broad Unicode support, thereby eliminating the warnings and ensuring characters are rendered correctly in the final PDF.

## 📋 Plan

### Phase 1: Investigation
- [x] Identify the error from the user-provided log (`[WARNING] Missing character: There is no ①...`).
- [x] Pinpoint the responsible code module: `src/output/formatter.py`, specifically the `convert_txt_to_pdf` method.
- [ ] Analyze the existing `pypandoc` call within `convert_txt_to_pdf` to confirm no font is explicitly set, leading to the problematic default.

### Phase 2: Implementation
- [ ] **Import `sys` module:** Add `import sys` at the top of `src/output/formatter.py` to detect the operating system.
- [ ] **Modify `convert_txt_to_pdf`:**
    - Inside this method, right before the `pypandoc.convert_file` call, add logic to determine the best system font.
    - Create a `font_arg` list.
    - Use an `if/elif/else` based on `sys.platform`:
        - `if sys.platform == "win32"`: Use `-V mainfont:"Arial"`.
        - `elif sys.platform == "darwin"`: Use `-V mainfont:"Helvetica Neue"`.
        - `else`: Use `-V mainfont:"DejaVu Sans"` as a general fallback for Linux/other OSes.
    - Extend the `extra_args` list with this `font_arg`.
- [ ] Add a code comment explaining this OS-aware font selection strategy. This approach respects the user's feedback on preferring system fonts and relying on the LaTeX engine's automatic font subsetting to keep file sizes optimized.

### Phase 3: Verification
- [ ] **Prepare Test Data:**
    - Create a new test file at `data/input/test_pdf_chars.txt`.
    - This file will contain the characters that caused the warnings: ①, ②, ③, ④, ⑤, along with some regular text.
- [ ] **Configure for Test:**
    - Temporarily modify `config/config.yaml` to set `input.novel_path` to the new test file.
    - Ensure `'pdf'` is present in the `output.formats` list.
- [ ] **Execute:**
    - Run the main script `python main.py`.
- [ ] **Verify Result:**
    - Carefully check the execution log. The primary success condition is the **complete absence** of the `[WARNING] Missing character` messages.
    - (Optional, for user) Ask the user to visually inspect the generated PDF `data/output/test_pdf_chars_translated.pdf` to confirm the circled numbers are rendered correctly.

### Phase 4: Finalization & Cleanup
- [ ] Revert the changes made to `config.yaml` (`novel_path` and `formats`).
- [ ] Delete the temporary test file `data/input/test_pdf_chars.txt`.
- [ ] Update `tasks/lessons.md` with the lesson learned about ensuring appropriate fonts for PDF generation pipelines.
- [ ] Mark this task as complete.

## 🔍 Quality Checklist
- [ ] The `[WARNING] Missing character` messages for circled numbers are gone from the log.
- [ ] The PDF generation process still completes successfully.
- [ ] The fix does not introduce any new errors or warnings.
- [ ] The code change is clean, commented, and targets only the necessary function.
