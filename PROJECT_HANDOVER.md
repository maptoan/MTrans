**Ngày bàn giao:** 2026-02-12
**Trạng thái:** Tối ưu hóa hiệu năng & Sửa lỗi cấu trúc EPUB (v8.1.2)
**Version:** 8.1.2

---

## 📋 Tổng Quan Dự Án

### **Mục Tiêu**

Hệ thống dịch thuật tự động sử dụng Google Gemini API để dịch tiểu thuyết và tài liệu từ tiếng Trung/Anh sang tiếng Việt, hỗ trợ đa dạng thể loại (Văn học, Kỹ thuật, Y khoa, Học thuật) với độ chính xác cao.

### **Tính Năng Chính (v8.1.2)**

1. ✅ **High-Throughput Engine (v8.0):**
    * **Chunk Upsizing:** Sử dụng chunks **20,000 tokens** để tối ưu số lượng request.
    * **3-Tier Quality Gate:** Hệ thống kiểm duyệt 3 tầng (Structural, Content Coverage, CJK Residuals).
    * **Sub-chunk Fallback:** Tự động chia nhỏ và dịch lại tuần tự (with context) nếu chunk lớn bị lỗi chất lượng.
    * **QA Conditional Gating:** Tiết kiệm quota bằng cách skip QA cho các đoạn text "sạch".

2. ✅ **API Orchestration (v8.1.2):**
    * **Smart Key Management:** Tài liệu hóa chi tiết cơ chế phân loại Pool và Zero-Wait Replacement.
    * **Worker-Key Affinity:** Tối ưu hóa caching phía server bằng cách gắn kết cố định key-worker.
    * **Adaptive Scaling:** Tự động điều chỉnh số lượng worker dựa trên sức khỏe hệ thống (success rate).

3. ✅ **Structural Consistency:**
    * **Sequential Parsing (v8.1.2):** Cố định thứ tự đọc chương cho EPUB (sử dụng spine order), loại bỏ hoàn toàn lỗi xáo trộn chương.
    * **Metadata Compliance:** Tự động sửa lỗi thuật ngữ ngay sau khi dịch.

4. ✅ **UX & Automation:**
    * **Vietnamese Docs Rule:** Mọi tài liệu kỹ thuật đều được viết bằng tiếng Việt để dễ quản lý.
    * **Zero-Touch Startup:** Khởi động nhanh vào chế độ dịch, không cần tương tác thủ công.

---

## 🏗️ Cấu Trúc Dự Án (Snapshot v6.0)

```
novel-translator/
├── main.py                    # Entry point
├── config/config.yaml         # Configuration
├── src/
│   ├── translation/          # Core Logic (Translator, PromptBuilder, ModelRouter)
│   ├── preprocessing/        # Input (OCR, Parser, Chunker)
│   ├── managers/             # Metadata (Style, Glossary, Relation, Progress)
│   ├── services/             # API (Gemini Adapter, Key Manager)
│   ├── output/               # Output (Formatter - DOCX/EPUB)
│   └── utils/                # Helpers (CSV AI Fixer, Errors, Token Counter)
├── scripts/                  # Helper Scripts (e.g. diagnose_api_keys.py)
├── data/                     # Input/Output Data
└── docs/                     # Documentation (PROJECT_CONTEXT.md là Source of Truth)
```

---

## 📚 Tài Liệu Tham Khảo (Source of Truth)

Để đảm bảo thông tin luôn cập nhật, vui lòng tham khảo các tài liệu sống sau đây:

1. **`PROJECT_CONTEXT.md`**: Tài liệu ngữ cảnh toàn diện nhất, chứa chi tiết kỹ thuật, cấu trúc và hướng dẫn.
2. **`CHANGELOG.md`**: Lịch sử thay đổi và tính năng mới theo từng phiên bản.
3. **`WORKFLOW_DOCUMENTATION.md`**: Chi tiết các luồng xử lý (Workflow).

---

## 🚀 Hướng Dẫn Nhanh (Quick Start)

### 1. Cài đặt môi trường

```bash
# Windows
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

### 2. Cấu hình

Sửa file `config/config.yaml`:

* `api_keys`: Thêm danh sách Google Gemini API keys.
* `input`: Đường dẫn file cần dịch (`novel_path`).
* `translation`: Chọn model (`gemini-2.5-flash`), bật/tắt QA editor.

### 3. Diagnose (Kiểm tra API Keys)

Trước khi chạy, nên kiểm tra API keys:

```bash
python scripts/diagnose_api_keys.py
```

### 4. Chạy dịch thuật

```bash
python main.py
```

---

## ⚠️ Lưu Ý Bàn Giao (Handover Notes)

1. **Dependencies:** Dự án sử dụng `google-genai` (SDK mới) là chính, `google-generativeai` (SDK cũ) là fallback. Đảm bảo môi trường Python 3.11+.
2. **API Quota (v8.0):** Hệ thống được cấu hình cho **60 API keys** với giới hạn **20 RPD** mỗi key. Nếu bạn có ít key hơn, hãy điều chỉnh `max_parallel_workers` trong `config.yaml` (~70% số key).
3. **Chunk Size:** Kích thước chunk 20K tokens rất hiệu quả cho Gemini Flash nhưng yêu cầu RAM ổn định khi xử lý batch lớn.
4. **Data Persistence:** Tiến độ được lưu trong `data/progress/`. Nếu chương trình bị gián đoạn, chỉ cần chạy lại `main.py` để tiếp tục (Resume).
5. **Narrative Pronouns (v8.1):** Hệ thống tự động suy luận giới tính nhân vật từ `character_relations.csv` → phân biệt "hắn" (nam) và "nàng" (nữ) trong trần thuật. Nếu thêm nhân vật mới, cần đảm bảo có đủ `Listener_Term` để engine inference đúng giới tính.
6. **Classical Addressing (v8.1):** Khi `style_profile.json` có genre "tiên hiệp/cổ trang", hệ thống tự động inject rule dùng Tỷ/Muội/Huynh/Đệ thay cho Chị/Em/Anh.

---
**Người bàn giao:** Antigravity Agent
**Phiên bản bàn giao:** v8.1
