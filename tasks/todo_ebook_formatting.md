# Project: Novel Translator - Ebook Formatting Optimization
# Date: 2026-02-25
# Pipeline: v8.2 (Ebook Formatting Analysis)

## 🎯 Task Overview
**Task:** Rà soát và tối ưu workflow định dạng ebook (EPUB/DOCX/PDF)
**Target:** Giảm trùng lặp, tăng hiệu suất, nhất quán styles

## 📋 Plan

### Phase 1: Analysis ✅
- [x] Phân tích format_converter.py
- [x] Phân tích formatter.py 
- [x] Phân tích ui_handler callback flow
- [x] Xác định trùng lặp

### Phase 2: Identify Issues
- [x] Tìm duplicate logic giữa format_converter và formatter
- [x] Kiểm tra CSS/styles consistency
- [x] Đo I/O operations

## 🔴 Issues Identified

### Issue 1: Duplicate DOCX Conversion (CAO)
| Location | Method | Tool |
|----------|--------|------|
| format_converter.py:88 | convert_to_docx | pandoc |
| formatter.py:320 | save_as_docx | python-docx |

**Problem:** 
- 2 cách convert DOCX khác nhau!
- ui_handler gọi format_converter.convert_to_docx (dùng pandoc)
- formatter.save() gọi save_as_docx (dùng python-docx)
- Không nhất quán

### Issue 2: Multiple I/O in format_converter (TRUNG BÌNH)
- convert_to_docx: đọc file (line 114)
- convert_to_pdf: đọc file (line 169) 
- convert_to_epub: gọi output_formatter (đọc file lần nữa)
- **Total: 3 lần đọc file**

### Issue 3: Styles Not Fully Utilized (THẤP)
- EPUB: dùng epub_css ✅
- PDF: dùng pdf_css (nếu có) ⚠️
- DOCX: dùng docx_template (nếu có) ⚠️

## 📝 Analysis Summary

**Current Flow:**
```
translator.save() → formatter.save() → save_as_txt()
                                     → save_as_docx() [python-docx]
                                     → convert_txt_to_epub() [pypandoc]
                                     → convert_txt_to_pdf() [pypandoc]

ui_handler → format_converter.convert_to_docx() [pandoc - DUPLICATE]
           → format_converter.convert_to_pdf() [pypandoc]
           → format_converter.convert_to_epub() [formatter]
```

### Recommendations:
1. **Chọn 1 method DOCX**: Hoặc pandoc hoặc python-docx, không cần cả 2
2. **Unified I/O**: Đọc content 1 lần, truyền cho các function
3. **Styles consolidation**: Đảm bảo tất cả formats đều dùng styles

## 📊 Progress Log
| Time | Action | Result |
|------|--------|--------|
| 2026-02-25 | Analysis | Found 3 issues |

---
*Template from workflow_orchestration.md*
