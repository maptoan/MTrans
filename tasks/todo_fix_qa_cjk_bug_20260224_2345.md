# Project: Novel Translator - Bug Fix
# Date: 2026-02-24
# Task: Fix QA Editor failure when cleaning CJK characters.

## 🎯 Task Overview
**Bug:** The QA Editor process, triggered by remaining CJK characters in a translated chunk, is failing its own validation ("reasoning leakage or truncation"). This causes the system to fall back to the original, flawed draft, leaving the CJK characters in the final text.
**Example:** Chunk-2 in the provided log.
**Goal:** Identify the root cause of the QA Editor failure and implement a robust fix to ensure CJK characters are successfully removed.

## 📋 Plan

### Phase 1: Investigation
- [ ] **Locate QA Logic:** Search the codebase for the log message "QA result failed validation" and related terms (`qa_editor`, `gate 3`) to pinpoint the exact Python module and function responsible for the QA pass and its validation.
- [ ] **Find Full Log:** Search for the most recent and relevant log file in the `logs/` directory to get more context around the failure.
- [ ] **Inspect Failed Chunk:**
    - List the contents of `data/progress/` to identify the file(s) corresponding to `Chunk-2`.
    - Read the content of the failed chunk file. This file should contain the original source, the flawed "draft" translation, and potentially the failed "qa" output.
- [ ] **Review QA Prompt:** Locate the prompt template used for the QA Editor pass (likely in the `prompts/` directory or configured in `config.yaml`) and analyze its structure.

### Phase 2: Root Cause Analysis
- [ ] **Analyze QA Validation Failure:** Based on the failed chunk's content and the QA logic, determine why the output was considered invalid. "Reasoning leakage" suggests the model included its thought process in the final output. "Truncation" suggests the output was incomplete.
- [ ] **Analyze Initial CJK Leak:** Examine the draft translation and the initial translation prompt to hypothesize why Chinese characters were present in the first place.
- [ ] **Formulate Hypothesis:** Conclude with a clear hypothesis for the failure (e.g., "The QA prompt is not strict enough in defining the output format, causing the model to leak reasoning, which fails the validation check.").

### Phase 3: Implementation
- [ ] **Propose a Fix:** Based on the root cause, propose a solution. Potential fixes include:
    1.  **Prompt Engineering (Most Likely):** Refine the QA Editor prompt to be more explicit about the desired output format, instructing it to *only* return the cleaned text and nothing else.
    2.  **Strengthen Validation Logic:** Make the validation logic smarter. For example, it could attempt to parse the "good" part of a QA output even if there's some reasoning leakage.
    3.  **Add a Fallback:** If the primary QA Editor fails, trigger a simpler, more reliable secondary cleanup mechanism (e.g., a regex or direct string replacement for the few remaining CJK characters).
- [ ] **Implement the Chosen Fix:** Apply the code changes to the relevant modules.

### Phase 4: Verification
- [ ] **Isolate the Test Case:** If possible, create a test script that specifically runs the translation and QA process only on the problematic `Chunk-2` content.
- [ ] **Run Full Process (if isolation is not possible):** Re-run the entire translation process using the original input file that produced the error.
- [ ] **Verify the Fix:**
    - Check the new log files to confirm that `Chunk-2` is processed without the "QA result failed validation" error.
    - Verify that the log shows 0 CJK characters remaining for `Chunk-2`.
    - Manually inspect the final output file (`.txt` or `.docx`) to confirm the content of `Chunk-2` is correct and clean.

### Phase 5: Finalization
- [ ] Update the `tasks/lessons.md` file with a new entry detailing the bug, the root cause, and the rule to prevent similar issues.
- [ ] Revert any changes made to `config.yaml` or test scripts during the verification phase.
- [ ] Mark this task as complete.

## 🔍 Quality Checklist
- [ ] The final output must contain zero CJK characters for the previously failed chunks.
- [ ] The QA Editor pass must complete successfully without validation errors.
- [ ] The fix should not negatively impact the translation quality of other, non-problematic chunks.
- [ ] The implemented solution must be robust and address the root cause, not just the symptom.
