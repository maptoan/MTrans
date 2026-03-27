# MTranslator Coding Standards & Best Practices

**Version:** 4.0
**Last Updated:** 2026-01-22
**Architecture:** Python-based Translation Tool with Gemini API

---

## Project Configuration

| Setting | Value | Options |
|---------|-------|---------|
| **Language** | `Python` | Python 3.11+ |
| **Package Manager** | `pip` | pip, poetry (optional) |
| **Backend Framework** | `Custom` | Async/await with asyncio |
| **Frontend Framework** | `None` | CLI-based tool |
| **Database/ORM** | `None` | File-based storage (JSON, CSV, TXT) |
| **Testing Framework** | `pytest` | pytest, pytest-asyncio |
| **Linter/Formatter** | `Ruff` | Ruff, mypy (type checking) |
| **API Integration** | `Gemini API` | Google Generative AI |

---

## Table of Contents

1. [Technology Selection Guidelines](#1-technology-selection-guidelines)
2. [Naming Conventions](#2-naming-conventions)
3. [Python-Specific Standards](#3-python-specific-standards)
4. [Project Structure](#4-project-structure)
5. [Async/Await Patterns](#5-asyncawait-patterns)
6. [Error Handling](#6-error-handling)
7. [Testing Standards](#7-testing-standards)
8. [SOLID Principles](#8-solid-principles)
9. [Security Best Practices](#9-security-best-practices)
10. [Documentation Standards](#10-documentation-standards)
11. [Git Workflow](#11-git-workflow)
12. [AI Agent Workflow](#12-ai-agent-workflow)
    - [12.0 TDD-First Principle (ABSOLUTE REQUIREMENT)](#120-tdd-first-principle-absolute-requirement)
    - [12.0.1 Zero-Impact Implementation (ABSOLUTE REQUIREMENT)](#1201-zero-impact-implementation-absolute-requirement)
13. [Project-Specific Patterns](#13-project-specific-patterns)

---

## 1. Technology Selection Guidelines

### Selection Criteria

| Priority | Criteria | Description |
|----------|----------|-------------|
| 1 | **Recency** | Prefer technologies released/updated within last 3 years |
| 2 | **Active Maintenance** | Active development, regular releases, responsive maintainers |
| 3 | **Community Adoption** | Growing community, good documentation, ecosystem support |
| 4 | **Type Safety** | First-class type support (type hints, generics) |
| 5 | **Performance** | Modern optimizations (async/await, lazy loading) |

### Preferred Modern Stack for This Project

| Category | Preferred | Avoid |
|----------|-----------|-------|
| Runtime | Python 3.11+ | Python < 3.9 |
| Async | asyncio, aiohttp | requests (sync only) |
| Validation | Pydantic v2 | Pydantic v1 |
| Testing | pytest, pytest-asyncio | unittest |
| Linting | Ruff, mypy | flake8, pylint |
| Package Manager | pip, poetry | pip alone (for now) |
| API Client | google-generativeai | Manual HTTP calls |

---

## 2. Naming Conventions

### 2.1 Files and Directories

| Type | Convention | Example |
|------|------------|---------|
| General files | `snake_case` | `ocr_reader.py`, `chunker.py` |
| Modules | `snake_case` | `prompt_builder.py`, `translator.py` |
| Entry points | `main.py`, `gui.py` | `main.py`, `gui.py` |
| Tests | `test_*.py` hoặc `*_test.py` | `test_translator.py`, `chunker_test.py` |
| Directories | `snake_case` | `preprocessing/`, `translation/` |
| Config files | `snake_case.yaml` | `config.yaml`, `ocr_config.yaml` |

### 2.2 Variables and Functions

| Language | Variables | Constants | Functions |
|----------|-----------|-----------|-----------|
| Python | `snake_case` | `SCREAMING_SNAKE_CASE` | `snake_case` |

### 2.3 Function Naming Prefixes

| Prefix | Usage | Example |
|--------|-------|---------|
| `get` | Retrieve data | `get_chunk_translation()` |
| `set` | Set/assign value | `set_user_name()` |
| `fetch` | API/network call | `fetch_user_data()` |
| `create` | Create new entity | `create_chunk()` |
| `update` | Modify existing | `update_translation()` |
| `delete` | Remove entity | `delete_chunk()` |
| `validate` | Validation logic | `validate_translation()` |
| `handle` | Event handlers | `handle_error()` |
| `is/has/can` | Boolean checks | `is_chunk_completed()`, `has_markers()` |
| `build` | Build/construct | `build_main_prompt()` |
| `load` | Load from storage | `load_progress()` |
| `save` | Save to storage | `save_chunk_result()` |

### 2.4 Class Naming

| Type | Convention | Example |
|------|------------|---------|
| Classes | `PascalCase` | `NovelTranslator`, `PromptBuilder` |
| Private methods | `_leading_underscore` | `_build_prompt()`, `_validate_chunk()` |

---

## 3. Python-Specific Standards

### 3.1 Type Hints (MANDATORY)

**Always use type hints for function parameters and return types:**

```python
from typing import Dict, List, Optional, Any, Tuple

def translate_chunk(
    chunk_text: str,
    context: Optional[List[str]] = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Translate a chunk of text."""
    pass
```

### 3.2 Code Style

```toml
# pyproject.toml (recommended)
[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.mypy]
strict = true
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

**Rules:**
- Use type hints everywhere
- Use `async/await` for I/O operations (API calls, file I/O)
- Use Pydantic for data validation (if needed)
- Use `Optional[T]` instead of `T | None` for Python < 3.10 compatibility
- Use `Dict[str, Any]` for flexible dictionaries
- Use `List[T]` instead of `list[T]` for Python < 3.9 compatibility

### 3.3 Import Organization

```python
# 1. Standard library
import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

# 2. Third-party
import google.generativeai as genai
import asyncio
from pydantic import BaseModel

# 3. Local imports
from src.translation.translator import NovelTranslator
from src.managers.progress_manager import ProgressManager
```

---

## 4. Project Structure

```
novel-translator/
├── main.py                 # Entry point
├── gui.py                  # GUI entry point (if exists)
├── config/
│   └── config.yaml         # Main configuration
├── src/
│   ├── translation/        # Translation logic
│   │   ├── translator.py
│   │   ├── prompt_builder.py
│   │   └── model_router.py
│   ├── preprocessing/      # Preprocessing (OCR, chunking)
│   │   ├── ocr_reader.py
│   │   ├── chunker.py
│   │   └── input_preprocessor.py
│   ├── managers/           # Resource managers
│   │   ├── progress_manager.py
│   │   ├── style_manager.py
│   │   ├── glossary_manager.py
│   │   └── relation_manager.py
│   ├── output/             # Output formatting
│   │   └── formatter.py
│   └── utils/              # Utilities
│       ├── helpers.py
│       └── csv_ai_fixer.py
├── data/
│   ├── input/              # Input files
│   ├── output/             # Output files
│   ├── progress/           # Progress tracking
│   └── metadata/           # Metadata (glossary, style, etc.)
├── tests/                  # Test files
├── tools/                  # Utility tools
└── logs/                   # Log files
```

---

## 5. Async/Await Patterns

### 5.1 Async Function Structure

```python
async def translate_chunk_async(
    chunk: Dict[str, Any],
    api_key: str,
    context: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Translate a chunk asynchronously.
    
    Args:
        chunk: Chunk dictionary with 'text' and 'global_id'
        api_key: Gemini API key
        context: Optional context chunks
    
    Returns:
        Dictionary with 'translation' and 'status'
    
    Raises:
        ValueError: If chunk is invalid
        APIError: If API call fails
    """
    try:
        # Validate input
        if not chunk.get('text'):
            raise ValueError("Chunk text is empty")
        
        # Build prompt
        prompt = build_prompt(chunk['text'], context)
        
        # Call API
        result = await call_gemini_api(prompt, api_key)
        
        return {
            'translation': result,
            'status': 'success',
            'chunk_id': chunk['global_id']
        }
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return {
            'translation': None,
            'status': 'failed',
            'error': str(e),
            'chunk_id': chunk['global_id']
        }
```

### 5.2 Batch Processing with asyncio

```python
async def translate_all_chunks(
    chunks: List[Dict[str, Any]],
    api_keys: List[str],
    max_workers: int = 5
) -> List[Dict[str, Any]]:
    """Translate all chunks in parallel."""
    semaphore = asyncio.Semaphore(max_workers)
    key_queue = asyncio.Queue()
    
    # Fill key queue
    for key in api_keys:
        await key_queue.put(key)
    
    async def translate_with_semaphore(chunk: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            api_key = await key_queue.get()
            try:
                result = await translate_chunk_async(chunk, api_key)
                return result
            finally:
                await key_queue.put(api_key)
    
    tasks = [translate_with_semaphore(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [r for r in results if not isinstance(r, Exception)]
```

---

## 6. Error Handling

### 6.1 Exception Handling Pattern

```python
import logging
from typing import Optional

logger = logging.getLogger("NovelTranslator")

async def process_chunk(chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a chunk with proper error handling."""
    try:
        # Main logic
        result = await translate_chunk(chunk)
        return result
    except ValueError as e:
        # Validation errors - log and return None
        logger.warning(f"Invalid chunk: {e}")
        return None
    except google.api_core.exceptions.ResourceExhausted as e:
        # Rate limit - retry later
        logger.warning(f"Rate limit exceeded: {e}")
        raise  # Re-raise to allow retry logic
    except Exception as e:
        # Unexpected errors - log and handle gracefully
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
            'chunk_id': chunk.get('global_id')
        }
```

### 6.2 Retry Logic

```python
import asyncio
from typing import Callable, TypeVar, Optional

T = TypeVar('T')

async def retry_async(
    func: Callable[[], T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Optional[T]:
    """Retry an async function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                return None
            wait_time = delay * (backoff ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    return None
```

---

## 7. Testing Standards

### 7.1 Test-Driven Development (TDD) - MANDATORY

**TEST-DRIVEN DEVELOPMENT IS NON-NEGOTIABLE. NO EXCEPTIONS. EVER.**

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  CRITICAL: TDD IS MANDATORY FOR ALL WORK               │
│                                                             │
│  This applies to:                                           │
│  • Every feature implementation                             │
│  • Every bug fix                                            │
│  • Every refactoring                                        │
│  • Every code change, no matter how small                   │
│                                                             │
│  NO CODE SHALL BE WRITTEN WITHOUT A FAILING TEST FIRST      │
└─────────────────────────────────────────────────────────────┘
```

#### TDD Cycle - MUST Follow Strictly

```
RED → GREEN → REFACTOR → REPEAT
```

1. **RED**: Write a failing test FIRST
2. **GREEN**: Write minimum code to pass
3. **REFACTOR**: Improve code quality while tests stay green

### 7.2 Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.translation.translator import NovelTranslator

class TestNovelTranslator:
    """Test suite for NovelTranslator."""
    
    @pytest.fixture
    def translator(self):
        """Create a translator instance for testing."""
        config = {
            'api_keys': ['test_key'],
            'translation': {'max_retries': 3}
        }
        return NovelTranslator(config, ['test_key'])
    
    @pytest.mark.asyncio
    async def test_translate_chunk_success(self, translator):
        """Test successful chunk translation."""
        chunk = {
            'global_id': 1,
            'text': 'Hello world'
        }
        
        with patch('src.translation.model_router.SmartModelRouter.translate_chunk_async') as mock_translate:
            mock_translate.return_value = {'translation': 'Xin chào thế giới'}
            
            result = await translator._translate_one_chunk_worker(
                chunk, [], []
            )
            
            assert result['status'] == 'success'
            assert result['translation'] == 'Xin chào thế giới'
            assert result['chunk_id'] == 1
    
    @pytest.mark.asyncio
    async def test_translate_chunk_failure(self, translator):
        """Test chunk translation failure."""
        chunk = {
            'global_id': 1,
            'text': 'Hello world'
        }
        
        with patch('src.translation.model_router.SmartModelRouter.translate_chunk_async') as mock_translate:
            mock_translate.side_effect = Exception("API Error")
            
            result = await translator._translate_one_chunk_worker(
                chunk, [], []
            )
            
            assert result['status'] == 'failed'
            assert result['error'] is not None
```

### 7.3 Coverage Requirements

| Metric | Minimum | Target |
|--------|---------|--------|
| Statements | 80% | 90% |
| Branches | 75% | 85% |
| Functions | 80% | 90% |
| Lines | 80% | 90% |

---

## 8. SOLID Principles

### 8.1 Single Responsibility (SRP)

Each class/module should have ONE responsibility:

```python
# ✅ GOOD: Single responsibility
class ProgressManager:
    """Manages translation progress."""
    def save_chunk_result(self, chunk_id: int, translation: str):
        """Save a chunk translation."""
        pass

class StyleManager:
    """Manages style profile."""
    def build_style_instructions(self) -> str:
        """Build style instructions from profile."""
        pass

# ❌ BAD: Multiple responsibilities
class TranslationManager:
    """Manages translation, progress, and style."""
    def translate(self): pass
    def save_progress(self): pass
    def load_style(self): pass
```

### 8.2 Dependency Inversion (DIP)

Depend on abstractions, not concretions:

```python
# ✅ GOOD: Depend on interface
class Translator:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    async def translate(self, text: str) -> str:
        return await self.api_client.call(text)

# ❌ BAD: Depend on concrete implementation
class Translator:
    def __init__(self):
        self.api_client = GeminiAPIClient()  # Hard dependency
```

---

## 9. Security Best Practices

### 9.1 API Key Management

```python
# ✅ GOOD: Load from environment or config
import os
from typing import List

def load_api_keys() -> List[str]:
    """Load API keys from environment or config."""
    keys = []
    
    # Try environment first
    env_key = os.getenv('GEMINI_API_KEY')
    if env_key:
        keys.append(env_key)
    
    # Fallback to config file
    if not keys:
        keys = load_from_config()
    
    return keys

# ❌ BAD: Hardcoded keys
API_KEYS = ["AIzaSy..."]  # NEVER do this
```

### 9.2 Input Validation

```python
from typing import Dict, Any

def validate_chunk(chunk: Dict[str, Any]) -> bool:
    """Validate chunk structure."""
    required_fields = ['global_id', 'text']
    
    for field in required_fields:
        if field not in chunk:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(chunk['text'], str):
        raise TypeError("chunk['text'] must be a string")
    
    if not chunk['text'].strip():
        raise ValueError("chunk['text'] cannot be empty")
    
    return True
```

### 9.3 File Path Security

```python
from pathlib import Path

def safe_file_path(user_input: str, base_dir: Path) -> Path:
    """Safely resolve file path, preventing directory traversal."""
    user_path = Path(user_input)
    
    # Resolve to absolute path
    resolved = (base_dir / user_path).resolve()
    
    # Ensure it's within base_dir
    try:
        resolved.relative_to(base_dir.resolve())
    except ValueError:
        raise ValueError("Path outside allowed directory")
    
    return resolved
```

---

## 10. Documentation Standards

### 10.1 Docstrings

```python
def translate_chunk(
    chunk_text: str,
    context: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Translate a chunk of text using Gemini API.
    
    Args:
        chunk_text: The text to translate
        context: Optional context chunks for better translation
        metadata: Optional metadata (glossary, style, etc.)
    
    Returns:
        Dictionary containing:
            - 'translation': Translated text
            - 'status': 'success' or 'failed'
            - 'chunk_id': Chunk identifier
            - 'error': Error message if failed
    
    Raises:
        ValueError: If chunk_text is empty
        APIError: If API call fails
    
    Example:
        >>> result = await translate_chunk("Hello", context=["Previous text"])
        >>> print(result['translation'])
        'Xin chào'
    """
    pass
```

### 10.2 Code Comments

```python
# ❌ BAD: Obvious comment
counter += 1  # Increment counter

# ✅ GOOD: Explains why
# Use ceiling to ensure at least 1 page even for 0 items
page_count = math.ceil(total / page_size) or 1

# ✅ GOOD: Explains complex logic
# Retry with exponential backoff to handle rate limits
# Start with 1s delay, double each retry (max 3 retries)
```

---

## 11. Git Workflow

### 11.1 Branch Strategy

**MANDATORY: Create feature branch before implementing ANY issue.**

```bash
git checkout develop && git pull
git checkout -b feature/issue-{number}-{description}
# ... implement ...
git commit -m "feat(scope): description"
git push origin feature/issue-{number}-{description}
```

### 11.2 Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/issue-{n}-{desc}` | `feature/issue-123-fix-marker-validation` |
| Bug fix | `fix/issue-{n}-{desc}` | `fix/issue-456-chunk-merge-error` |
| Hotfix | `hotfix/{desc}` | `hotfix/security-patch` |

### 11.3 Commit Messages (Conventional Commits)

```bash
<type>(<scope>): <subject>

# Types: feat, fix, refactor, chore, docs, test, perf
# Examples:
git commit -m "feat(translation): add marker-based validation"
git commit -m "fix(chunker): handle empty chunks correctly"
git commit -m "refactor(prompt): simplify marker preservation logic"
```

### 11.4 Protected Branches

| Branch | Direct Commits | Status |
|--------|----------------|--------|
| `main` | **NEVER** | Production |
| `develop` | **NEVER** | Integration |
| `feature/*` | YES | Working branch |

---

## 12. AI Agent Workflow

### 12.0 TDD-First Principle (ABSOLUTE REQUIREMENT)

**TEST-DRIVEN DEVELOPMENT IS NON-NEGOTIABLE. NO EXCEPTIONS. EVER.**

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  CRITICAL: TDD IS MANDATORY FOR ALL WORK               │
│                                                             │
│  This applies to:                                           │
│  • Every feature implementation                             │
│  • Every bug fix                                            │
│  • Every refactoring                                        │
│  • Every code change, no matter how small                   │
│                                                             │
│  NO CODE SHALL BE WRITTEN WITHOUT A FAILING TEST FIRST      │
└─────────────────────────────────────────────────────────────┘
```

#### TDD Cycle - MUST Follow Strictly

```
┌─────────────────────────────────────────────────────────────┐
│                    STRICT TDD CYCLE                         │
│                                                             │
│    ┌─────────┐                                              │
│    │   RED   │  1. Write a failing test FIRST               │
│    │         │     - Test MUST fail before implementation   │
│    │         │     - Verify test fails for right reason     │
│    └────┬────┘                                              │
│         │                                                   │
│         ▼                                                   │
│    ┌─────────┐                                              │
│    │  GREEN  │  2. Write MINIMUM code to pass               │
│    │         │     - Only enough code to make test pass     │
│    │         │     - No extra features or "improvements"    │
│    └────┬────┘                                              │
│         │                                                   │
│         ▼                                                   │
│    ┌─────────┐                                              │
│    │REFACTOR │  3. Improve code quality                     │
│    │         │     - Clean up while tests stay green        │
│    │         │     - No new functionality in this phase     │
│    └────┬────┘                                              │
│         │                                                   │
│         └──────────► REPEAT for next requirement            │
└─────────────────────────────────────────────────────────────┘
```

### 12.0.1 Zero-Impact Implementation (ABSOLUTE REQUIREMENT)

**IMPLEMENTATIONS MUST NEVER BREAK EXISTING FUNCTIONALITY. NO EXCEPTIONS.**

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  CRITICAL: PROTECT CURRENT STATE AT ALL COSTS          │
│                                                             │
│  Every implementation MUST:                                 │
│  • Pass ALL existing tests before AND after changes         │
│  • Not modify existing behavior unless explicitly required  │
│  • Be backward compatible by default                        │
│  • Preserve all existing functionality                      │
│                                                             │
│  IF YOUR CHANGE BREAKS EXISTING TESTS → YOUR CHANGE IS WRONG│
└─────────────────────────────────────────────────────────────┘
```

#### Pre-Implementation State Verification

**BEFORE writing any code, you MUST:**

1. Run FULL test suite → All tests MUST pass
2. Run type checking → No type errors
3. Run linting → No lint errors
4. Run build → Build succeeds
5. Document current state (snapshot)

#### Post-Implementation Verification

**AFTER every implementation, you MUST:**

1. Run FULL test suite → All tests MUST still pass
2. Run type checking → No new type errors
3. Run linting → No new lint errors
4. Run build → Build still succeeds
5. Compare with pre-implementation snapshot
6. Verify no unintended side effects

### 12.1 Pre-Implementation: Codebase Exploration (MANDATORY)

**Before ANY implementation work begins, agents MUST explore and understand the codebase.**

#### Exploration Checklist

| Step | Action | Purpose |
|------|--------|---------|
| 1 | Read `CLAUDE.md` | Understand coding standards |
| 2 | Read `README.md` and `README_v1.8.stable.md` | Understand project overview |
| 3 | Read `PROJECT_CONTEXT.md` | Understand project context |
| 4 | Explore relevant source files | Understand existing patterns |
| 5 | Identify dependencies | Map out what the feature will interact with |
| 6 | Review similar features | Understand how similar features are implemented |

### 12.2 Task Planning: Breaking Down Milestones (MANDATORY)

**When creating issues/tasks, tasks MUST be as small as possible.**

#### Task Sizing Rules

| Rule | Description |
|------|-------------|
| **Single Responsibility** | Each task does ONE thing only |
| **Atomic Changes** | Task can be completed in a single PR |
| **Clear Scope** | No ambiguity about what's included/excluded |
| **Testable** | Task has clear acceptance criteria |
| **Time-Bounded** | Ideally completable in 1-4 hours |

### 12.3 Implementation Process

| Step | Action |
|------|--------|
| 0 | **Explore and understand codebase** (MANDATORY) |
| 1 | **Run pre-implementation checks** (tests, types, lint, build) |
| 2 | Create feature branch |
| 3 | **Write FAILING tests FIRST** (TDD RED phase - MANDATORY) |
| 4 | **Verify tests FAIL** for the right reasons |
| 5 | **Write MINIMUM code** to pass tests (TDD GREEN phase) |
| 6 | **Refactor** while keeping tests green (TDD REFACTOR phase) |
| 7 | **Run ALL existing tests** - must ALL pass |
| 8 | Run quality gates (typecheck, lint, test, build) |
| 9 | **Verify no impact** to existing functionality |
| 10 | Commit and create PR |
| 11-13 | Review cycles (minimum 3 reviews) |

**CRITICAL:** Steps 3-4 (TDD) and Steps 7-9 (Impact Verification) are NON-NEGOTIABLE.

### 12.4 Quality Gates: NEVER Skip (MANDATORY)

**Quality gates MUST pass before ANY commit, regardless of task type.**

Every commit MUST pass:
1. Type checking (mypy or pyright)
2. Linting (Ruff)
3. Tests (pytest)
4. Build verification (if applicable)

---

## 13. Project-Specific Patterns

### 13.1 Translation Workflow

```python
# Standard translation workflow pattern
async def translate_workflow(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Standard translation workflow."""
    # 1. Pre-process chunks (add markers if enabled)
    processed_chunks = preprocess_chunks(chunks)
    
    # 2. Translate in parallel
    results = await translate_all_chunks(processed_chunks)
    
    # 3. Validate results (marker-based or similarity-based)
    validated_results = validate_translations(results, chunks)
    
    # 4. Merge chunks
    merged_content = merge_chunks(validated_results)
    
    # 5. Format and save
    formatted = format_output(merged_content)
    save_output(formatted)
    
    return results
```

### 13.2 Chunk Management Pattern

```python
# Chunk management pattern
class ChunkManager:
    """Manages chunk lifecycle."""
    
    def create_chunk(self, text: str, chunk_id: int) -> Dict[str, Any]:
        """Create a chunk with optional markers."""
        chunk = {
            'global_id': chunk_id,
            'text_original': text,
            'tokens': self._count_tokens(text)
        }
        
        if self.use_markers:
            chunk['text'] = self._wrap_with_markers(text, chunk_id)
        else:
            chunk['text'] = text
        
        return chunk
    
    def _wrap_with_markers(self, text: str, chunk_id: int) -> str:
        """Wrap text with chunk markers."""
        return f"[CHUNK:{chunk_id}:START]\n{text}\n[CHUNK:{chunk_id}:END]"
```

### 13.3 Error Recovery Pattern

```python
# Error recovery pattern for translation
async def translate_with_recovery(
    chunk: Dict[str, Any],
    max_retries: int = 3
) -> Dict[str, Any]:
    """Translate with automatic retry and recovery."""
    for attempt in range(max_retries):
        try:
            result = await translate_chunk(chunk)
            if result['status'] == 'success':
                return result
        except google.api_core.exceptions.ResourceExhausted:
            # Rate limit - wait and retry
            await asyncio.sleep(60 * (attempt + 1))
            continue
        except Exception as e:
            logger.error(f"Translation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return {
                    'status': 'failed',
                    'error': str(e),
                    'chunk_id': chunk['global_id']
                }
    
    return {'status': 'failed', 'error': 'Max retries exceeded'}
```

---

## Summary Checklist

### Before Committing

- [ ] All quality gates pass (typecheck, lint, test, build)
- [ ] No hardcoded API keys or secrets
- [ ] Error handling in place
- [ ] Tests cover new functionality
- [ ] Type hints added to all functions
- [ ] Docstrings added for public functions
- [ ] No breaking changes to existing functionality

### Code Review Checklist

- [ ] Follows naming conventions (snake_case)
- [ ] Input validation present
- [ ] Error handling implemented
- [ ] Type hints present
- [ ] Async/await used for I/O operations
- [ ] Security best practices followed
- [ ] Documentation updated if needed
- [ ] All existing tests still pass

---

**End of Document**

*This document provides coding standards specific to the Novel Translator project. All developers and AI agents must follow these standards.*
