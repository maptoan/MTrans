# Coding Standards Compliance Checklist

**Version:** 1.0  
**Last Updated:** 2026-01-08  
**Based on:** CLAUDE.md

---

## Pre-Implementation Checklist

### Codebase Exploration (MANDATORY)
- [ ] Read `CLAUDE.md` - Understand coding standards
- [ ] Read `README.md` and `README_v1.8.stable.md` - Understand project overview
- [ ] Read `PROJECT_CONTEXT.md` - Understand project context
- [ ] Explore relevant source files - Understand existing patterns
- [ ] Identify dependencies - Map out what the feature will interact with
- [ ] Review similar features - Understand how similar features are implemented

### Pre-Implementation State Verification
- [ ] Run FULL test suite → All tests MUST pass
- [ ] Run type checking (mypy) → No type errors
- [ ] Run linting (Ruff) → No lint errors
- [ ] Run build → Build succeeds
- [ ] Document current state (snapshot)

---

## Implementation Checklist

### TDD Compliance (MANDATORY)
- [ ] **Test file exists** for the feature/fix
- [ ] **Test is written** that describes expected behavior
- [ ] **Test FAILS** (red phase confirmed)
- [ ] **Failure reason** is correct (not syntax error, etc.)
- [ ] Write minimum implementation to pass
- [ ] All tests pass (green phase)
- [ ] Refactor if needed (tests still green)

### Code Quality

#### Type Hints (MANDATORY)
- [ ] All function parameters have type hints
- [ ] All return types are annotated
- [ ] Optional parameters use `Optional[T]` or `T | None`
- [ ] Complex types use `Dict[str, Any]`, `List[T]`, etc.
- [ ] No `Any` types without justification

#### Naming Conventions
- [ ] Files use `snake_case`
- [ ] Functions use `snake_case`
- [ ] Variables use `snake_case`
- [ ] Constants use `SCREAMING_SNAKE_CASE`
- [ ] Classes use `PascalCase`
- [ ] Private methods use `_leading_underscore`

#### Error Handling
- [ ] All async functions have try-except blocks
- [ ] Specific exceptions are caught (not bare `except:`)
- [ ] Errors are logged with appropriate level
- [ ] Error messages are descriptive
- [ ] Retry logic is implemented for transient errors

#### Documentation
- [ ] All public functions have docstrings
- [ ] Docstrings include Args, Returns, Raises sections
- [ ] Complex logic has inline comments explaining "why"
- [ ] No obvious comments (explaining "what" is obvious)

#### Async/Await
- [ ] I/O operations use `async/await`
- [ ] API calls are async
- [ ] File operations are async (if applicable)
- [ ] Proper use of `asyncio.gather()` for parallel operations
- [ ] Semaphores used for rate limiting

---

## Post-Implementation Checklist

### Zero-Impact Verification (MANDATORY)
- [ ] Run FULL test suite → All tests MUST still pass
- [ ] Run type checking → No new type errors
- [ ] Run linting → No new lint errors
- [ ] Run build → Build still succeeds
- [ ] Compare with pre-implementation snapshot
- [ ] Verify no unintended side effects

### Quality Gates (MANDATORY)
- [ ] Type checking passes (mypy or pyright)
- [ ] Linting passes (Ruff)
- [ ] All tests pass (pytest)
- [ ] Build verification (if applicable)
- [ ] No hardcoded secrets or API keys
- [ ] Input validation present
- [ ] Error handling implemented

### Code Review Preparation
- [ ] Follows naming conventions
- [ ] Type hints present
- [ ] Docstrings added
- [ ] Error handling in place
- [ ] Security best practices followed
- [ ] No breaking changes to existing functionality
- [ ] Documentation updated if needed

---

## File-Specific Checklists

### For New Files
- [ ] File uses `snake_case` naming
- [ ] File has proper imports (stdlib, third-party, local)
- [ ] File has module-level docstring
- [ ] All public functions have docstrings
- [ ] Type hints on all functions
- [ ] Error handling implemented

### For Modified Files
- [ ] Existing tests still pass
- [ ] New functionality has tests
- [ ] Type hints added/updated
- [ ] Docstrings updated
- [ ] No breaking changes
- [ ] Backward compatibility maintained

### For Test Files
- [ ] Test file follows `test_*.py` or `*_test.py` naming
- [ ] Tests use pytest fixtures
- [ ] Tests use `@pytest.mark.asyncio` for async tests
- [ ] Tests have descriptive names
- [ ] Tests cover happy path and error cases
- [ ] Tests are isolated (no shared state)

---

## Security Checklist

### API Key Management
- [ ] No hardcoded API keys in code
- [ ] API keys loaded from environment or config
- [ ] API keys validated before use
- [ ] API keys not logged or exposed

### Input Validation
- [ ] All user inputs are validated
- [ ] File paths are sanitized
- [ ] No directory traversal vulnerabilities
- [ ] Type checking for all inputs

### Error Messages
- [ ] Error messages don't expose sensitive information
- [ ] Stack traces not shown to end users
- [ ] Logging doesn't include secrets

---

## Project-Specific Patterns

### Translation Workflow
- [ ] Chunks are preprocessed correctly
- [ ] Markers are added if enabled
- [ ] Translation uses async/await
- [ ] Results are validated (marker-based or similarity-based)
- [ ] Chunks are merged correctly
- [ ] Output is formatted and saved

### Chunk Management
- [ ] Chunks have proper structure (`global_id`, `text`, `text_original`)
- [ ] Markers are wrapped correctly if enabled
- [ ] Token counting is accurate
- [ ] Chunks are saved to progress manager

### Error Recovery
- [ ] Retry logic implemented for transient errors
- [ ] Rate limit handling (exponential backoff)
- [ ] Failed chunks are tracked
- [ ] Recovery mechanism for failed translations

---

## Git Workflow Checklist

### Before Creating Branch
- [ ] Understand the requirement
- [ ] Explore codebase
- [ ] Run pre-implementation checks

### Branch Creation
- [ ] Branch name follows convention: `feature/issue-{n}-{desc}` or `fix/issue-{n}-{desc}`
- [ ] Branch created from `develop` (or appropriate base)
- [ ] Branch is up to date with base

### Before Committing
- [ ] All quality gates pass
- [ ] Tests written and passing
- [ ] Type hints added
- [ ] Docstrings added
- [ ] No hardcoded secrets
- [ ] Error handling in place

### Commit Message
- [ ] Follows Conventional Commits: `<type>(<scope>): <subject>`
- [ ] Type is one of: feat, fix, refactor, chore, docs, test, perf
- [ ] Scope is appropriate (e.g., translation, chunker, ocr)
- [ ] Subject is clear and concise

### Before Creating PR
- [ ] All quality gates pass
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Code reviewed by self (self-review)
- [ ] Documentation updated if needed

---

## Review Checklist (For Reviewers)

### Code Quality
- [ ] Follows naming conventions
- [ ] Type hints present and correct
- [ ] Docstrings complete
- [ ] Error handling appropriate
- [ ] No obvious bugs or issues

### Architecture
- [ ] Follows SOLID principles
- [ ] No unnecessary dependencies
- [ ] Proper separation of concerns
- [ ] Reusable code where appropriate

### Testing
- [ ] Tests cover new functionality
- [ ] Tests are meaningful (not just coverage)
- [ ] Edge cases are tested
- [ ] Error cases are tested

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Error messages don't expose sensitive info
- [ ] File operations are safe

### Performance
- [ ] Async/await used for I/O
- [ ] No unnecessary blocking operations
- [ ] Efficient algorithms used
- [ ] Memory usage is reasonable

---

## Quick Reference

### Common Commands

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
ruff check src/

# Format code
ruff format src/

# Run all quality gates
pytest && mypy src/ && ruff check src/
```

### Common Patterns

```python
# Type hints
def function(param: str, optional: Optional[int] = None) -> Dict[str, Any]:
    pass

# Async function
async def async_function(param: str) -> str:
    pass

# Error handling
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return None
```

---

## Notes

- This checklist should be used for EVERY code change
- Mark items as complete only after verification
- If an item doesn't apply, note why
- When in doubt, refer to `CLAUDE.md` for detailed standards

---

**End of Checklist**

