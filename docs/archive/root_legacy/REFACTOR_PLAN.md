# REFACTOR_PLAN.md - Cleanup & Standardization Strategy

**Date:** 2026-02-17
**Status:** Approved
**Target:** `src/`, `docs/`, `prompts/`

## 1. Overview
This plan outlines the steps to clean up the Novel Translator codebase, remove legacy artifacts, and enforce coding standards. The primary goal is to reduce technical debt and ensure the project is ready for future feature development (Phase 8+).

## 2. Cleanup Strategy (Safe Delete)
The following directories and files have been identified as legacy or dead code and will be removed:

| Path | Reason | Verification |
|------|--------|--------------|
| `src_BROKEN_REFACTOR/` | Failed/Abandoned refactor attempt. `main.py` uses `src/`. | Confirmed `src/` has newer files (e.g., `ui/`) and `src_BROKEN_REFACTOR` is a stale copy. |
| `prompts/old/` | Deprecated prompts. | Confirmed valid prompts are in `src/translation/prompt/` or `prompts/`. |
| `__pycache__/` | Compiled python files. | Safe to delete, will regenerate. |

**Action:**
- `rm -rf src_BROKEN_REFACTOR`
- `rm -rf prompts/old`
- `find . -name "__pycache__" -type d -exec rm -rf {} +`

## 3. Standardization (Ruff & Mypy)
We will enforce strict coding standards using `ruff` and `mypy` on the active `src/` directory.

### 3.1 Ruff (Linting & Formatting)
- **Target:** `src/`, `scripts/`, `tests/`, `main.py`
- **Config:** `ruff.toml` (already exists)
- **Fixes:**
  - Auto-fix import sorting (`I`).
  - Auto-fix whitespace/formatting (`F`).
  - Auto-fix unused imports/variables.
  - Manual fix for complexity/logic issues (if critical).

### 3.2 Mypy (Type Checking)
- **Target:** `src/`
- **Config:** `pyproject.toml` or default.
- **Goal:** Ensure no critical type errors that could cause runtime crashes.
- **Action:** Run `mypy src/` and fix high-priority errors.

## 4. Documentation Synchronization
Ensure documentation reflects the cleaned state.

- **PROJECT_CONTEXT.md:** Remove references to `src_BROKEN_REFACTOR` if any (checked: found 1 reference). Update version/date.
- **README.md:** Verify structure.

## 5. Verification Plan
After cleanup and standardization, we must verify system integrity.

- **Trifecta Check:** Run `python checklist.py` (must pass 100%).
- **Unit Tests:** Run `pytest tests/` (must pass).
- **Manual Smoke Test:** Run `python main.py --help` to ensure entry point works.

## 6. Execution Order
1.  **Delete** legacy folders.
2.  **Run** `ruff check . --fix`.
3.  **Run** `mypy src/`.
4.  **Update** documentation.
5.  **Run** verification suite.
