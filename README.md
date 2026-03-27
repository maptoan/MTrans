# MTranslator 🤖📖 (v9.4)

**MTranslator** là một công cụ dịch thuật tiểu thuyết/tài liệu tự động, được xây dựng bằng Python, với mục tiêu tạo ra các bản dịch chất lượng cao, có hồn và giữ được văn phong của tác giả gốc.

Khác với các công cụ dịch máy thông thường, dự án này áp dụng một phương pháp tiếp cận tinh vi: **phân tích các yếu tố văn học** của tác phẩm (như văn phong, thuật ngữ, mối quan hệ nhân vật) để cung cấp ngữ cảnh chi tiết cho mô hình AI. Quá trình này mô phỏng lại cách làm việc của một dịch giả chuyên nghiệp, đảm bảo bản dịch cuối cùng không chỉ đúng về mặt ngôn ngữ mà còn hay về mặt văn học.

---

**Current Version:** v9.4 (Workspace Reorg Safety Baseline + Path Contract)

## Tính năng nổi bật ✨

* **master.html & EPUB/PDF thống nhất (v9.0)**: Pipeline TXT/EPUB/PDF → dịch → `master.html` (giữ layout/heading) → export EPUB/PDF; Quality profile (fast_low_cost | balanced_default | max_quality).
* **EPUB Layout-Preserving (v9.x)**: Khi **input là file EPUB** (text-based) và bật `preprocessing.epub.preserve_layout`, pipeline giữ cấu trúc từng chương (file-per-chapter) và copy CSS/ảnh/font từ EPUB gốc; output gồm **EPUB dịch** (`{novel_name}_translated.epub`) tại thư mục `output.epub_reinject.epub_output_dir` và tùy chọn `master.html`.
* **RPD-block & Key State chuẩn hóa (v9.1)**: APIKeyManager là nguồn sự thật; key hết quota/ngày (RPD) bị block tới ngày hôm sau; SmartKeyDistributor dùng `_state` (APIKeyManager) cho blocked/usable.
* **Free-tier rate limit (2026-03)**: Cấu hình ưu tiên performance (5 RPM/key, 12s delay) cho Gemini free tier; tránh key_management ghi đè.
* **OCR không treo sau Cleanup (2026-03)**: AI Soát lỗi chính tả có phase timeout (mặc định 1h) và giới hạn chờ key/chunk; Cleanup đã có sẵn phase timeout và giới hạn chờ key.
* **Specialized Non-Fiction Support (v7.2)**: Support chuyên biệt cho tài liệu Học thuật, Kỹ thuật, Y khoa với adaptive prompts ưu tiên độ chính xác thuật ngữ.
* **Strict CJK Filtering (v7.2)**: Chế độ "Zero Tolerance" với ký tự Trung Quốc sót lại, tự động sửa lỗi cục bộ hoặc Transliteration Fallback.
* **Zombie Key Detection (v7.2)**: Tự động phát hiện và loại bỏ các "Zombie Keys" (lỗi liên tục) khỏi pool để đảm bảo stability.
* **Example-Driven Prompts (v7.1)**: Refactoring toàn bộ PromptBuilder theo triết lý "Show, Don't Tell" với Example Matrix, giúp AI nắm bắt văn phong nhanh hơn.
* **Pool Health Monitoring (v7.1)**: Hệ thống theo dõi sức khỏe Key Pool thời gian thực, cảnh báo sớm khi cạn kiệt tài nguyên.
* **NotebookLM Workflow (v7.1)**: Quy trình trích xuất metadata chuẩn hóa với các prompt chuyên biệt cho NotebookLM.
* **Hyper-Optimized Performance (v7.0)**: Tăng tốc độ xử lý Glossary/Relation lên tới **100x** nhờ thuật toán Lazy Regex & Substring Pre-check.
* **Robust Key Management (v7.0)**: Fix lỗi crash khi hết quota, đảm bảo hệ thống tự động xoay key hoặc chờ đợi một cách an toàn tuyệt đối.
* **Smart Failover & Key Rotation (v6.1)**: Khi gặp lỗi 429/Quota, hệ thống tự động chuyển sang key khác ngay lập tức thay vì chờ đợi. Cơ chế này áp dụng cho cả Translation và QA Editor Pass.

* **Metadata Smart Unwrap (v6.1)**: Tự động bóc tách (unwrap) cấu trúc JSON lồng khi AI trả về format không chuẩn, đảm bảo trích xuất metadata thành công.
* **Clean Console Logging (v6.1)**: Thanh tiến độ `tqdm` cập nhật in-place, loại bỏ log bị lặp đôi, console sạch sẽ chuyên nghiệp.
* **AI Metadata Generation (Phase 8)**: Tự động trích xuất metadata (glossary, character relations, style profile) từ tài liệu gốc bằng AI, hỗ trợ đa thể loại (Novel, Technical Doc, Medical, Academic Paper). Tiết kiệm ~60% API calls nhờ Unified Extraction.
* **Dynamic Work Stealing (Phase 7)**: Kiến trúc Queue động giúp tận dụng 100% tài nguyên API keys, giảm thời gian dịch xuống mức tối thiểu.
* **Mandatory QA Editor Pipeline (v6.0)**: Mỗi chunk dịch đều được biên tập chuyên sâu qua phase QA Editor độc lập, nâng cao sự phân hóa vai trò Draft/Editor.
* **Smart Role Addressing & Relations (v6.0)**: Tự động quét nhân vật và áp dụng đúng quy tắc xưng hô từ `character_relations.csv` trong công đoạn biên tập.
* **AutoFix Compliance Recovery (v5.5)**: Tự động sửa lỗi glossary sau validation, giảm tỉ lệ chunk bị fail.
* **Optimized CJK Handling (v5.5)**: Phát hiện và dịch triệt để các ký tự Trung/Nhật/Hàn bị sót bằng Smart QA Editor.
* **Smart Chunk Balancing (v5.4)**: Tự động cân bằng chunks để tối ưu API usage (~30% reduction).
* **Strict Merge Mode (v5.3)**: Việc ghép file chỉ diễn ra khi 100% chunks dịch thành công, đảm bảo output hoàn chỉnh.
* **Modular Workflow (v5.3)**: Translation workflow được tách thành 3 phases độc lập (prepare, execute, finalize) cho dễ maintain.
* **Quote-Preservation Fix (v5.1.2)**: Bộ tách câu thông minh bảo toàn dấu ngoặc kép trong hội thoại, kết hợp với cơ chế tự động khôi phục dấu ngoặc bị mất.
* **Adaptive Worker Scaling (v5.1)**: Tự động điều chỉnh số lượng luồng worker bằng chính xác số lượng API key khả dụng, tối đa hóa tốc độ xử lý.
* **Strict Key Enforcement (v5.1)**: Cơ chế "Chặn & Chờ" thông minh - tự động ngủ đông nếu thời gian chờ ngắn, hoặc dừng ngay nếu quota bị chặn lâu.
* **Global Round Robin Fallback (v5.1)**: Tự động quét và chuyển key tức thì khi gặp lỗi 429, đảm bảo hệ thống hoạt động liên tục thay vì chết chùm.
* **Safe Validation Strategy (v5.1)**: Cơ chế kiểm tra lỗi thông minh, phân biệt lỗi nghiêm trọng và cảnh báo (như abrupt ending) để tối ưu hóa quota.
* **User-Friendly Error Handling (v5.1)**: Thông báo lỗi rõ ràng, dễ hiểu khi hết tài nguyên, thay vì các thông báo kỹ thuật khó hiểu.


* **Quy trình tự động toàn diện**: Từ việc làm sạch văn bản, phân tách chương, cho đến dịch và định dạng đầu ra.
* **Phân tích văn học sâu**: Tự động xác định văn phong, trích xuất bảng thuật ngữ (tên nhân vật, địa danh) và phân tích tương tác nhân vật để đảm bảo tính nhất quán.
* **Dịch thuật theo ngữ cảnh**: Xây dựng các "chỉ dẫn" (prompts) thông minh và chi tiết để hướng dẫn AI tạo ra bản dịch chất lượng cao nhất.
* **OCR Module (Mới)**: Nhận dạng văn bản từ PDF scan và hình ảnh với hỗ trợ AI cleanup và spell check thông minh.
* **Giao diện người dùng trực quan**: Cung cấp giao diện đồ họa (`gui.py`) để người dùng dễ dàng tương tác.
* **Bảo mật và Hiệu năng**: Quản lý API Key thông minh, hỗ trợ đa SDK.
* **Tối ưu chi phí với Gemini Context Caching**: Tiết kiệm 75-90% input tokens bằng cách cache các chỉ dẫn và metadata tĩnh.
* **Smart Chapter Chunking (Phase 5)**: Tự động gom nhóm ngữ cảnh thông minh (Intro + Chapter 1) để đảm bảo mạch truyện liền mạch.
* **Adaptive Rate Limiting (Phase 4)**: Sử dụng thuật toán Token Bucket để tối đa hóa throughput mà không gặp lỗi 429.
* **Cài đặt đơn giản**: Tự động kiểm tra và cài đặt các thư viện cần thiết thông qua tệp `run.bat` trên Windows.

---

## Luồng hoạt động ⚙️

Chương trình hoạt động theo một quy trình được thiết kế cẩn thận:

1.  **Tiền xử lý Thủ công (NotebookLM)**: Người dùng sử dụng Google NotebookLM để phân tích và tạo ra các tệp dữ liệu ngữ cảnh (văn phong, thuật ngữ, nhân vật).
2.  **OCR (Nếu cần)**: Đối với PDF scan hoặc hình ảnh, module OCR nhận dạng văn bản, rồi AI cleanup và spell check (có phase timeout và giới hạn chờ key, tránh treo khi hết quota).
3.  **Khởi tạo Tài nguyên (InitializationService)**: Hệ thống tự động thiết lập API keys, tải metadata và tạo context cache bất đồng bộ trước khi dịch.
4.  **Phân tách Chương (SmartChunker)**: Tệp tiểu thuyết được làm sạch và chia thành các đoạn văn bản (chunks) một cách thông minh, giữ nguyên cấu trúc đoạn.
5.  **Điều phối Dịch thuật (ExecutionManager)**: Tự động quản lý luồng dịch song song, gán key cho workers và xử lý retry thông minh.
6.  **Xây dựng Prompt & Dịch (Gemini API)**: Kết hợp ngữ cảnh từ metadata và chunks để tạo ra bản dịch chất lượng cao thông qua Google Gemini.
7.  **Định dạng đầu ra (OutputFormatter)**: Hợp nhất các bản dịch và định dạng lại thành các tệp hoàn chỉnh (TXT, DOCX, EPUB). Nếu input là EPUB và bật *preserve layout*, chương trình xuất thêm **EPUB dịch giữ cấu trúc** (từng chương + CSS/ảnh gốc) tại thư mục cấu hình.

---

## 🏗️ Cấu trúc Dự án

```
MTranslator/
├── main.py                    # Entry point chính
├── gui.py                     # GUI interface
├── requirements.txt           # Python dependencies
├── run.bat                    # Trình khởi chạy tự động cho Windows
├── config/
│   └── config.yaml            # Tệp cấu hình chính
├── src/
│   ├── translation/           # Core translation logic
│   ├── preprocessing/         # File parsing, OCR, chunking
│   ├── managers/              # Metadata managers (style, glossary, relations, progress)
│   ├── services/               # API services (Gemini API, key management)
│   ├── output/                 # Output formatting
│   └── utils/                  # Utilities
├── docs/                       # Documentation
│   └── archive/                # Archived documentation
└── data/
    ├── input/                  # Input files
    ├── output/                 # Output files
    ├── progress/               # Progress tracking
    └── metadata/               # Metadata files (style, glossary, relations)
```

---

## Hướng dẫn Cài đặt và Sử dụng 🚀

Mục tiêu của phần này: sau khi fork repo, bạn có thể chạy bản dịch đầu tiên trong vài bước ngắn.

### 1) Chuẩn bị môi trường

- Yêu cầu: Python `3.11+` (khuyến nghị), kết nối Internet, Gemini API key.
- Clone/fork repo về máy.

**Windows (nhanh nhất):**
1. Chạy `run.bat` một lần để tạo môi trường và cài thư viện.
2. Nếu cửa sổ tự đóng sau khi cài xong, đó là bình thường.

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Chuẩn bị dữ liệu đầu vào

Đặt tệp nguồn vào `data/input/` (hỗ trợ `.txt`, `.epub`, `.docx`, `.pdf`).

Ví dụ:
- `data/input/my_novel.txt`

### 3) Chuẩn bị metadata (khuyến nghị mạnh)

Để chất lượng dịch tốt và nhất quán, tạo 3 file metadata rồi đặt vào thư mục riêng theo tên tác phẩm, ví dụ:

- `data/metadata/My Novel/style_profile.json`
- `data/metadata/My Novel/glossary.csv`
- `data/metadata/My Novel/character_relations.csv`

Bạn có thể dùng prompt mẫu trong `prompts/` để tạo metadata bằng NotebookLM/Gemini.

### 4) Cấu hình tối thiểu trong `config/config.yaml`

Chỉ cần kiểm tra 3 nhóm sau trước khi chạy:

1. `api_keys`: điền danh sách Gemini API key.
2. `input.novel_path`: trỏ đúng file trong `data/input/`.
3. `metadata.*_path`: trỏ đúng 3 file metadata.

Ví dụ tối thiểu:

```yaml
api_keys:
  - "YOUR_GEMINI_API_KEY"

input:
  novel_path: "data/input/my_novel.txt"

metadata:
  style_profile_path: "data/metadata/My Novel/style_profile.json"
  glossary_path: "data/metadata/My Novel/glossary.csv"
  character_relations_path: "data/metadata/My Novel/character_relations.csv"
```

### 5) Chạy chương trình

**Windows:**
- Chạy `run.bat` (sau lần đầu cài, script sẽ vào luồng chạy chính).

**macOS/Linux:**
```bash
python main.py
```

Kết quả dịch sẽ xuất ra thư mục cấu hình trong `output.output_path` (mặc định là `data/output/`).

### 6) Cách chạy nhanh để kiểm thử sau khi fork

Checklist ngắn:
- [ ] Đã có ít nhất 1 API key hợp lệ trong `config/config.yaml`
- [ ] `input.novel_path` trỏ đúng file
- [ ] 3 file metadata tồn tại và đúng đường dẫn
- [ ] Chạy `python main.py` (hoặc `run.bat`)
- [ ] Kiểm tra thư mục `data/output/` và log console

---

### ⚙️ Các khóa cấu hình quan trọng

| Mục | Dùng để làm gì |
| :--- | :--- |
| `api_keys` | Danh sách key dùng để xoay vòng khi dịch |
| `input.novel_path` | File đầu vào cần dịch |
| `metadata.style_profile_path` | Giữ văn phong đầu ra |
| `metadata.glossary_path` | Giữ nhất quán thuật ngữ |
| `metadata.character_relations_path` | Giữ xưng hô/quan hệ nhân vật |
| `preprocessing.epub.preserve_layout` | Giữ layout khi dịch EPUB text-based |
| `translation.qa_editor.*` | Cấu hình hậu kiểm chất lượng bản dịch |
| `performance.*` | Tốc độ gọi API / nhịp gửi request |
| `output.*` | Vị trí và định dạng file kết quả |

---

### 🗂️ Runtime Data Policy (an toàn khi cải tổ workspace)

- `data/input/`, `data/progress/`, `data/metadata/`, `data/cache/` là **runtime contract** của chương trình.
- Artifacts nặng/đầu ra trung gian nên để ngoài lifecycle repo:
  - `backup/*`
  - `data/output/*`
  - `data/reports/*`
- Chương trình vẫn tự tạo lại thư mục runtime rỗng khi cần; không phụ thuộc vào việc track dữ liệu output trong git.
- Resolve path nội bộ đã được chuẩn hóa theo project root để tránh lệch khi chạy khác CWD.

---

## 💡 Gỡ lỗi (Troubleshooting)

* **Lỗi `ValueError: API key... not set`**: Bạn chưa điền API keys vào `config/config.yaml` hoặc danh sách keys rỗng.
* **Lỗi `FileNotFoundError`**: Đường dẫn đến tệp tiểu thuyết hoặc tệp metadata trong `config.yaml` không chính xác. Hãy kiểm tra lại.
* **Lỗi `ImportError: Neither SDK is available`**: Cần cài đặt `google-genai` hoặc `google-generativeai`. Chạy `pip install google-genai` hoặc `pip install google-generativeai`.
* **429 / RPD / "You exceeded your current quota"**: Key hết quota (RPD) bị block tới ngày hôm sau; hệ thống tự chuyển sang key khác. Nếu workflow OCR "kẹt" sau bước Cleanup, đảm bảo bản mới (phase timeout cho Spell check) và kiểm tra `ocr.ai_spell_check.phase_timeout_seconds`.
* **Warning về async cleanup**: Không nghiêm trọng, có thể bỏ qua.
* **Chương trình tự thoát sau khi cài đặt thư viện**: Hành vi đúng. Chạy lại `run.bat` hoặc `python main.py` để bắt đầu dịch.

---

## 🗺️ Lộ trình Phát triển (Roadmap)

* [x] **Google GenAI SDK Support**: Hỗ trợ SDK mới với auto-detection
* [x] **Periodic Flush**: Batch save với periodic flush để cân bằng performance và safety
* [x] **Error Handling**: Robust error handling với automatic retry
* [x] **API Key Management**: Intelligent key management với free tier filtering
* [x] **Gemini Context Caching**: Tối ưu 75-90% input tokens (Flash/Pro)
* [ ] **Giao diện Người dùng Đồ họa (GUI)**: Xây dựng giao diện đơn giản với Tkinter hoặc Streamlit.
* [ ] **Giao diện Review**: Tạo một công cụ để so sánh song ngữ (side-by-side) và chỉnh sửa bản dịch.
* [x] **OCR phase timeout**: Phase timeout và giới hạn chờ key cho AI Cleanup & Spell check (tránh treo khi hết key)
* [ ] **Async cleanup warning**: Fix warning async cleanup trong OCR Reader (không ảnh hưởng chức năng)
* [ ] **Fine-tuning**: Tích hợp khả năng fine-tuning một model cho văn phong của một tác giả cụ thể.

---

## 📚 Documentation

Xem [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) để có danh sách đầy đủ các tài liệu.

### **Quick Links:**
- [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) - Ngữ cảnh dự án (cấu trúc, tính năng, workflow)
- [VENV_SETUP_GUIDE.md](./VENV_SETUP_GUIDE.md) - Hướng dẫn setup venv với Google GenAI SDK
- [WORKFLOW_DOCUMENTATION.md](./WORKFLOW_DOCUMENTATION.md) - Tài liệu workflow chi tiết
- [CONVERSATION_HISTORY.md](./CONVERSATION_HISTORY.md) - Lịch sử phát triển
- [CHANGELOG.md](./CHANGELOG.md) - Changelog với tất cả các thay đổi

---

## Đóng góp

Nếu bạn có ý tưởng cải thiện hoặc phát hiện lỗi, vui lòng tạo một "Issue" trên trang GitHub của dự án. Mọi sự đóng góp đều được chào đón!

## Giấy phép

Dự án này được cấp phép theo Giấy phép MIT. Xem tệp `LICENSE` để biết thêm chi tiết.

---

**Version:** v9.4  
**Last Updated:** 2026-03-27