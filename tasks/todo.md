# Project: Novel Translator - Workflow Optimization
# Date: 2026-02-25
# Pipeline: v8.2 (Analysis & Optimization)

## 🎯 Task Overview
**Task:** Rà soát và tối ưu workflow từ bước ghép chunk → xuất file
**Target:** Tối đa hiệu suất, giảm bottleneck

## 📋 Plan

### Phase 1: Analysis (Current Workflow)
- [ ] Phân tích _merge_all_chunks trong translator.py
- [ ] Phân tích formatter.save() trong formatter.py
- [ ] Phân tích ui_handler.show_user_options()
- [ ] Xác định các bước trùng lặp

### Phase 2: Identify Issues
- [ ] Tìm các đoạn code xử lý trùng lặp
- [ ] Đo hiệu suất các bước chuẩn hóa
- [ ] Kiểm tra I/O operations

### Phase 3: Optimization
- [ ] Loại bỏ xử lý trùng lặp
- [ ] Tối ưu memory usage
- [ ] Cải thiện tốc độ

### Phase 4: Verification
- [ ] Chạy test import
- [ ] Verify workflow hoạt động đúng
- [ ] Update lessons.md nếu có correction

## 📊 Current Workflow Analysis
| Bước | File | Vấn đề tiềm năng |
|------|------|------------------|
| 1. Merge chunks | translator.py:1722 | Nhiều bước validation |
| 2. Chuẩn hóa | formatter.py:433 | Split/join nhiều lần |
| 3. Lưu TXT | formatter.py:309 | OK |
| 4. Tạo DOCX | formatter.py:320 | Đọc lại file TXT |
| 5. Tạo EPUB | formatter.py:530 | Tiền xử lý markdown |

## 🔴 Issues Identified

### Issue 1: Redundant Title Standardization (CAO)
- **Vị trí**: translator.py:1722 → formatter.py:433-455
- **Vấn đề**: 
  - `_merge_all_chunks` merge chunks với ParagraphPreserver (không có title standardization)
  - `formatter.save()` thực hiện title standardization lần nữa (lines 446-456)
- **Tác động**: Xử lý trùng lặp, chậm hơn

### Issue 2: Multiple File I/O (TRUNG BÌNH)
- **Vị trí**: formatter.py
- **Vấn đề**:
  - Lưu TXT (line 465)
  - Đọc lại TXT cho DOCX (line 475)
  - Đọc lại TXT cho EPUB trong convert_txt_to_epub (line 547)
- **Tác động**: I/O overhead

### Issue 3: Redundant Paragraph Normalization (THẤP)
- **Vị trí**: translator.py:2500 + formatter.py:459
- **Vấn đề**:
  - `ParagraphPreserver.merge_chunks_with_paragraph_preservation` normalize paragraphs
  - `formatter._normalize_paragraphs` normalize AGAIN
- **Tác động**: Nhỏ, nhưng không cần thiết

### Issue 4: DOCX Re-standardization (TRUNG BÌNH)
- **Vấn đề**: Lines 446-456 đã chuẩn hóa, rồi lines 479-482 chuẩn hóa LẠI lần nữa cho DOCX
- **Tác động**: Duplicate processing

## 📝 Notes
### Decisions:
- KHÔNG nên merge title standardization vào _merge_all_chunks vì:
  1. Separation of concerns: translator chỉ merge, formatter xử lý output
  2. Có thể có use case không cần standardization
- Cần tối ưu I/O: Giữ content trong memory thay vì đọc lại file

### Trade-offs:
- Giữ nguyên architecture để tránh breaking changes
- Tối ưu nhưng không refactor lớn

## 📊 Progress Log
| Time | Action | Result |
|------|--------|--------|
| 2026-02-25 | Started analysis | - |
| 2026-02-25 | Identified 4 issues | See above |
| 2026-02-25 | Optimized formatter.py | Add preprocessed_content param |
| 2026-02-25 | Verified imports | OK |

## ✅ Optimization Complete (2026-02-25)

### Changes Made:
1. **formatter.py save()**: Thêm parameter `preprocessed_content` để tránh xử lý trùng lặp
2. **formatter.py convert_txt_to_epub()**: Thêm optional `content` parameter
3. **formatter.py convert_txt_to_pdf()**: Thêm optional `content` parameter

### Benefits:
- Giảm 2 lần đọc file (DOCX, EPUB/PDF)
- Tránh xử lý title standardization trùng lặp
- Memory efficient hơn với preprocessed_content

### Note:
- Backward compatible: các function vẫn hoạt động nếu không truyền content
- Separation of concerns được giữ nguyên

---
*Template from workflow_orchestration.md | Novel Translator v8.2*
