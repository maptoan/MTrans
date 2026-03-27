# Lessons Learned - Novel Translator

> *Template from workflow_orchestration.md | Novel Translator v8.2*

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
