# 📘 Hướng dẫn Tạo Metadata cho Sách Non-Fiction (NotebookLM)

> **Lưu ý**: Bộ prompt này được thiết kế theo hướng **MODULAR**. Hãy chọn block phù hợp với loại sách của bạn (Narrative/General hoặc Technical).

## 🚀 Quy trình
1.  Truy cập [NotebookLM](https://notebooklm.google.com/).
2.  Tạo Notebook & Upload sách Non-Fiction.
3.  Chọn Prompt phù hợp dưới đây.

---

## 🎨 PROMPT 1: Style Profile (Chọn 1 trong 2)

### 🅰️ Option A: Dành cho Sách Kể Chuyện / Đại Chúng
*(Hồi ký, Lịch sử, Kinh tế thường thức, Self-help, Business)*

**Copy đoạn này:**
```text
Bạn là biên tập viên sách Non-Fiction đại chúng. Hãy phân tích tác phẩm và trích xuất "Hồ sơ phong cách" JSON.

YÊU CẦU:
1. Tập trung vào "Giọng văn" (Voice) và "Thông điệp cốt lõi".
2. Trả về 1 khối JSON duy nhất.

TEMPLATE JSON:
```json
{
  "book_info": {
    "title": "Tên sách",
    "genre": "Thể loại (VD: Hồi ký / Self-help)",
    "target_audience": "Độc giả mục tiêu (VD: Người khởi nghiệp)"
  },
  "narrative_style": {
    "tone": "Tông giọng (VD: Truyền cảm hứng, Hài hước, Chiêm nghiệm)",
    "storytelling": "Cách kể chuyện (VD: Dùng nhiều giai thoại cá nhân / Phân tích dữ liệu)"
  },
  "core_message": {
    "thesis": "Luận điểm chính (50 từ)",
    "key_takeaways": ["Bài học 1", "Bài học 2"]
  },
  "translation_guidelines": {
    "cultural_adaptation": ["Cách xử lý các tham chiếu văn hóa"],
    "pronouns": ["Cách xưng hô tác giả-độc giả (VD: Tôi-Bạn / Chúng ta)"]
  }
}
```
```

### 🅱️ Option B: Dành cho Sách Kỹ Thuật / Học Thuật
*(Sách Lập trình, Y khoa, Tài liệu kỹ thuật, Giáo trình)*

**Copy đoạn này:**
```text
Bạn là chuyên gia dịch thuật kỹ thuật (Technical Translator). Hãy trích xuất "Hồ sơ phong cách" JSON.

YÊU CẦU:
1. Tập trung vào "Độ chính xác" (Precision) và "Quy ước định dạng".
2. Trả về 1 khối JSON duy nhất.

TEMPLATE JSON:
```json
{
  "doc_info": {
    "title": "Tên tài liệu",
    "field": "Lĩnh vực (VD: Python Programming / Cardiology)",
    "difficulty": "Trình độ (Basic / Advanced)"
  },
  "technical_style": {
    "terminology_strictness": "Mức độ tuân thủ thuật ngữ (High/Absolute)",
    "sentence_structure": "Cấu trúc câu (Passive voice / Imperative instructions)"
  },
  "formatting_rules": {
    "code_blocks": "Quy tắc xử lý Code (VD: Giữ nguyên comment tiếng Anh?)",
    "variables": "Quy tắc xử lý tên biến/hàm (VD: Không dịch snake_case)"
  },
  "translation_guidelines": {
    "acronyms": "Quy tắc viết tắt (VD: Giữ nguyên API, JSON)",
    "notes": "Lưu ý khác"
  }
}
```
```

---

## 📖 PROMPT 2: Glossary (Chung cho cả 2)

**Copy đoạn này:**

```text
Bạn là chuyên gia thuật ngữ. Hãy trích xuất danh sách **Technical Terms** (Thuật ngữ chuyên ngành), **Acronyms** (Từ viết tắt), và **Proper Nouns** (Tên riêng/Tổ chức).

QUY TẮC:
1. **Output thuần CSV**.
2. **Technical/Code**: Những từ khóa kỹ thuật (như `function`, `class`, `loop` hoặc thuật ngữ kinh tế `ROI`, `EBITDA`) BẮT BUỘC liệt kê quy tắc dịch (dịch nghĩa hay giữ nguyên).

HEADER:
Type,Original_Term,Translated_Term_VI,Domain,Context_Rule,Notes

VÍ DỤ MẪU:
Type,Original_Term,Translated_Term_VI,Domain,Context_Rule,Notes
Code,string,chuỗi ký tự,Programming,translate_meaning,"Trong bối cảnh lập trình."
Acronym,API,API,Tech,keep_original,"Không dịch."
Concept,Opportunity Cost,Chi phí cơ hội,Economics,translate_meaning,"Thuật ngữ chuẩn."
Organization,WHO,WHO (Tổ chức Y tế Thế giới),Medical,keep_and_annotate,"Giữ viết tắt, chú thích lần đầu."

Hãy xuất 50 thuật ngữ quan trọng nhất.
```

---

## 🏛️ PROMPT 3: Key Figures & References (Tùy chọn)

> Dùng cho sách Lịch sử, Hồi ký hoặc sách trích dẫn nhiều người nổi tiếng.

**Copy đoạn này:**

```text
Trích xuất danh sách Nhân vật và Tác giả được trích dẫn.

HEADER:
Name_Original,Name_VI,Role,Pronoun_Guide,Notes

VÍ DỤ:
Name_Original,Name_VI,Role,Pronoun_Guide,Notes
Steve Jobs,Steve Jobs,Founder Apple,Transliterate,"Giữ nguyên tên."
Sun Tzu,Tôn Tử,Strategist,Hán Việt,"Dùng danh xưng Tôn Tử."
```
