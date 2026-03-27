# Project: Novel Translator - [NOVEL_NAME]
# Date: [YYYY-MM-DD]
# Pipeline: Trifecta v7.0 (Auto-Healing)

## 🎯 Task Overview
**Novel:** [Tên tiểu thuyết]
**Input:** [Đường dẫn file gốc]
**Target:** [Ngôn ngữ đích: Vietnamese]
**Purpose:** [Draft/Release/Review]

## 📋 Plan

### Phase 1: Preparation
- [ ] Verify input file exists and is readable
- [ ] Check/update glossary.csv
- [ ] Check/update style_profile.json
- [ ] Validate API keys availability

### Phase 2: Translation
- [ ] Run preprocessor (chunking)
- [ ] Execute translation pipeline
- [ ] Monitor for CJK residual characters
- [ ] Check dialogue quote consistency

### Phase 3: QA & Post-processing
- [ ] Run Batch QA (if enabled)
- [ ] Verify no CJK characters remain
- [ ] Merge chunks
- [ ] Generate output (TXT/EPUB/DOCX)

### Phase 4: Verification
- [ ] Compare output length vs expected
- [ ] Spot-check translation quality
- [ ] Verify glossary terms applied
- [ ] Check formatting consistency

## 📊 Translation Metrics (Target)
| Metric | Target | Actual |
|--------|--------|--------|
| CJK残留 | 0 | - |
| Dialogue quotes | ~match original | - |
| Chunk success rate | 100% | - |
| Processing time | <10 min | - |

## 🔍 Quality Checklist
- [ ] No CJK characters in output
- [ ] Glossary terms applied correctly
- [ ] Style profile (tone/register) followed
- [ ] Chapter structure preserved
- [ ] No placeholder text [CHUNK_X] remains

## 📝 Notes
### Decisions:
- 

### Trade-offs:
- 

### API Key Usage:
- Keys available: [N]
- Estimated cost: [approximate]

## 📊 Progress Log
| Time | Action | Result |
|------|--------|--------|
| HH:MM | Started | - |
| HH:MM | Phase 1 complete | OK |
| HH:MM | Translation started | - |
| HH:MM | Chunk N/M complete | OK |
| HH:MM | QA pass | OK |
| HH:MM | Output generated | OK |

## 📖 Review Section (Fill after completion)
### Quality Assessment:
- CJK residual: [count]
- Dialogue consistency: [%]
- Style compliance: [Y/N]

### Issues Found:
1. 
2. 

### Lessons Learned:
1. 
2. 

### Next Steps (if any):
- [ ] Re-translate with updated metadata
- [ ] Manual review required
- [ ] Update glossary

---
*Template from workflow_orchestration.md | Novel Translator v8.2*
