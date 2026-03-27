# Implement Token Optimization (Compression & Minification)

## Goal
Reduce token usage by "compressing" (minifying) the context and metadata sent to the Gemini API, without sacrificing translation quality or safety. This responds to the user's request for "data compression" for chunks, prompts, and context.

## User Review Required
> [!IMPORTANT]
> **Compression Strategy**: We are NOT using binary compression (gzip) as LLMs work with tokens/text. Instead, we are using **Text Minification** (removing whitespace, dense formatting) and **Compact Metadata** (condensing JSON/lists).
>
> **Impact**:
> - **Input Chunk**: **No change** (must preserve original formatting).
> - **Context**: Aggressive minification (newlines removed/merged).
> - **Glossary/Style**: Dense string format instead of verbose Markdown/JSON.

## Proposed Changes

### 1. New Utility: `src/utils/token_optimizer.py`
Create a new class `TokenOptimizer` that handles text minification.
- `minify_text(text)`: Removes multi-newlines, standardizes whitespace.
- `minify_context_chunk(text)`: More aggressive; flattens paragraphs into lines, removes Markdown stylistic syntax (like `**`, `__` if valid).
- `compact_list(items)`: Joins list items with ` | ` or `; ` instead of newlines.
- `compact_dict(data)`: Serializes dictionary to `key:val; ` format.

### 2. Update `src/managers/glossary_manager.py`
Add `build_compact_prompt_section()` method.
- **Current**:
  ```markdown
  **ITEM:**
  - Sword (Jian) -> **Kiếm** // Sharp
  ```
- **New (Compact)**:
  ```text
  ITEMS: Sword(Jian)->Kiếm[Sharp]; ...
  ```

### 3. Update `src/translation/prompt_builder.py`
Integrate `TokenOptimizer` to optionally minify parts of the prompt.
- Add `use_compact_format` flag to `__init__`.
- Update `build_main_prompt` to:
    - Flatten `original_context_chunks` and `translated_context_chunks`.
    - Use `glossary_manager.build_compact_prompt_section` if enabled.
    - Minify guidelines sections (remove excessive newlines in the static strings).

### 4. Configuration Update
Add `translation.prompt.compact_mode` to `config/config.yaml`.

## Verification Plan

### Automated Tests
I will create a reproduction script `tests/test_token_optimization.py` that:
1.  Loads a sample text and glossary.
2.  Generates a prompt **without** optimization.
3.  Generates a prompt **with** optimization.
4.  Compares the character count (and estimated token count) to verify savings.
5.  Asserts that essential information (terms, context content) is still present.

### Manual Verification
1.  Run the translation on a small chapter (5 chunks).
2.  Check logs to see "Token Savings: X%".
3.  Verify the translation quality is not degraded (especially context awareness).
