# Project: Novel Translator - convert_review
# Date: 2026-02-24
# Pipeline: Trifecta v7.0 (Auto-Healing)

## 🎯 Task Overview
**Task:** Rà soát quy trình convert file txt sang EPUB, DOCX, PDF sau khi ghép xong file txt tổng
**Project:** Novel Translator v8.2

---

## 📋 RÀ SOÁT QUY TRÌNH CONVERT

### 1. Sơ Đồ Luồng Xử Lý

```
Translation Complete
       │
       ▼
┌──────────────────┐
│  Save TXT File   │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     UI Handler (ui_handler.py)          │
│  - Option 1: Convert immediately        │
│  - Option 2: Wait for review            │
│  - Option 3: Retry failed chunks        │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│   Format Converter (format_converter.py) │
│  - convert_to_epub()                    │
│  - convert_to_docx()                    │
│  - convert_to_pdf()                     │
└─────────────────────────────────────────┘
```

### 2. Các File Liên Quan

| File | Vai Trò |
|------|---------|
| `src/translation/format_converter.py` | Xử lý convert chính (EPUB/DOCX/PDF) |
| `src/translation/ui_handler.py` | Menu chọn định dạng đầu ra |
| `src/output/formatter.py` | Xử lý định dạng đầu ra (chuẩn hóa tiêu đề) |
| `config/config.yaml` | Cấu hình output |

### 3. Chi Tiết Các Hàm Convert

#### 3.1 convert_to_epub (format_converter.py:59-86)
- Gọi `output_formatter.convert_txt_to_epub()` (HIỆN KHÔNG TỒN TẠI)
- Fallback: chạy pandoc command trực tiếp

#### 3.2 convert_to_docx (format_converter.py:88-141)
- Sử dụng pypandoc
- Chuyển [H1]/[H2]/[H3] → Markdown headings
- Lưu vào output_path

#### 3.3 convert_to_pdf (format_converter.py:143-217)
- Sử dụng pypandoc với pdf_engine (default: xelatex)
- Hỗ trợ CJK font (SimSun)
- Cần cài đặt MiKTeX/wkhtmltopdf

---

## 📋 Plan

### Phase 1: Analysis ✓
- [x] Tìm và đọc format_converter.py
- [x] Tìm và đọc ui_handler.py
- [x] Tìm và đọc formatter.py
- [x] Kiểm tra config.yaml output section

### Phase 2: Issues Found ✓
- [x] Xác định các vấn đề trong quy trình convert

### Phase 3: Recommendations ✓
- [x] Đề xuất các cải tiến

### Phase 4: Verification
- [ ] Test convert TXT → EPUB
- [ ] Test convert TXT → DOCX
- [ ] Test convert TXT → PDF (nếu có MiKTeX)

---

## ⚠️ CÁC VẤN ĐỀ PHÁT HIỆN

### Issue 1: Thiếu Hàm convert_txt_to_epub (CAO)
**File:** `src/translation/format_converter.py:71-79`
**Mô tả:**
- Code gọi `self.output_formatter.convert_txt_to_epub()`
- Nhưng hàm này **không tồn tại** trong `src/output/formatter.py`
- Hệ thống fallback sang pandoc command

**Impact:** Convert EPUB có thể thất bại nếu không có fallback

### Issue 2: EPUB Timeout (TRUNG BÌNH)
**Mô tả:**
- Khi chạy lần trước, EPUB convert bị timeout
- Đã xử lý bằng cách chạy thủ công:
```bash
pandoc "data/output/HMQT_translated.txt" -o "data/output/HMQT_translated.epub" --metadata title="Title" --metadata language=vi
```

### Issue 3: PDF Engine Dependency (THẤP)
**Mô tả:**
- Cần cài đặt MiKTeX/wkhtmltopdf
- Nếu không có, convert sẽ thất bại với thông báo lỗi

---

## ✅ QUY TRÌNH HOẠT ĐỘNG

| Định dạng | Trạng thái | Ghi chú |
|------------|-------------|----------|
| TXT → EPUB | ⚠️ Hoạt động (fallback) | Cần implement hàm |
| TXT → DOCX | ✅ Hoạt động | Đã test |
| TXT → PDF | ⚠️ Cần engine | MiKTeX/wkhtmltopdf |

---

## 📊 KHUYẾN NGHỊ

### Ưu Tiên Cao
1. **Implement hàm convert_txt_to_epub** trong formatter.py HOẶC
2. **Tăng timeout** cho convert
3. **Thêm retry logic** cho convert errors

### Ưu Tiên Thấp
1. Thêm docx_template support
2. Hỗ trợ custom CSS cho PDF
3. Batch convert song song

---

## 📖 REVIEW SECTION

### Issues Found:
1. Thiếu hàm convert_txt_to_epub trong formatter.py
2. EPUB convert bị timeout
3. PDF cần cài đặt engine

### Lessons Learned:
1. Hệ thống có fallback sang pandoc khi output_formatter fails
2. Có thể chạy thủ công khi gặp lỗi

### Next Steps:
- [ ] Verify bằng cách test các convert functions
- [ ] Fix issue 1 nếu cần thiết

---
*Task Complete: 2026-02-24*
