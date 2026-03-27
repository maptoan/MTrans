# 📘 Hướng dẫn Tạo Metadata bằng NotebookLM (Tối ưu hóa)

> **Phiên bản Tinh Gọn**: Đã được rà soát bởi tổ chuyên gia. Tập trung vào các **Ví dụ Mẫu (Golden Examples)** thay vì các quy tắc phức tạp, giúp NotebookLM dễ "bắt chước" và ít bị lỗi format hơn.

## 🚀 Quy trình
1.  Truy cập [NotebookLM](https://notebooklm.google.com/).
2.  Tạo Notebook & Upload sách.
3.  Copy & Paste lần lượt các Prompt dưới đây.
4.  Copy kết quả vào file tương ứng trong `Data/metadata/<Tên_Truyện>/`.

---

## 🎨 PROMPT 1: Style Profile (JSON)

**Copy đoạn này:**

```text
Bạn là một chuyên gia phân tích văn học. Hãy đọc toàn bộ tác phẩm và trích xuất "Hồ sơ phong cách" (Style Profile) dưới dạng JSON.

YÊU CẦU:
1. Trả về đúng 1 khối JSON (code block).
2. Nội dung phải cô đọng, sâu sắc.

TEMPLATE JSON (Hãy điền thông tin thực tế):
```json
{
  "novel_info": {
    "title": "Tên truyện (Tiếng Việt)",
    "author": "Tên tác giả",
    "genre": "Thể loại chính (Tiên hiệp/Đô thị/Lịch sử...)",
    "estimated_length": "Độ dài ước tính"
  },
  "world_setting": {
    "description": "Mô tả bối cảnh thế giới, thời đại, hệ thống xã hội (50-100 từ)",
    "power_system": "Hệ thống cấp bậc tu luyện/sức mạnh (nếu có)"
  },
  "writing_style": {
    "tone": "Tông giọng (Hài hước/Bi tráng/Trầm lắng...)",
    "vocabulary": "Mức độ từ vựng (Bình dân/Cổ trang/Hàn lâm)",
    "dialogue_ratio": "Tỷ lệ hội thoại ước tính (VD: 40%)"
  },
  "translation_guidelines": {
    "preserve": ["Quy tắc 1 (VD: Giữ nguyên Hán Việt tên chiêu thức)", "Quy tắc 2..."],
    "adapt": ["Quy tắc 1 (VD: Thuần Việt hóa đại từ nhân xưng)", "Quy tắc 2..."]
  },
  "glossary_guide": {
    "technical_terms": ["Thuật ngữ 1", "Thuật ngữ 2"],
    "notes": "Lưu ý đặc biệt về cách dịch danh từ riêng"
  }
}
```
```

---

## 📖 PROMPT 2: Glossary (CSV)

**Copy đoạn này:**

```text
Bạn là chuyên gia thuật ngữ. Hãy trích xuất danh sách các thực thể (Nhân vật, Địa danh, Pháp bảo, Chiêu thức) để tạo Glossary.

QUY TẮC QUAN TRỌNG:
1. **Output thuần CSV**: Có Header, dùng dấu phẩy ngăn cách.
2. **Xử lý dấu phẩy**: Nếu nội dung có dấu phẩy hoặc chấm phẩy (cột Alternative, Notes...), BẮT BUỘC bao quanh bằng dấu ngoặc kép `"`.
3. **Chiến lược**: Chỉ xuất **50 dòng** quan trọng nhất trước. Sau đó hỏi tôi "Tiếp tục?".

HEADER:
Type,Original_Term_Pinyin,Original_Term_CN,Translated_Term_VI,Alternative_Translations,Translation_Rule,Context_Usage,Frequency,Notes

VÍ DỤ MẪU (Hãy làm theo format này):
Type,Original_Term_Pinyin,Original_Term_CN,Translated_Term_VI,Alternative_Translations,Translation_Rule,Context_Usage,Frequency,Notes
Character,Cui Xiao Xuan,崔小玄,Thôi Tiểu Huyền,"Tiểu Huyền; Trư Đầu",transliterate,"Universal; Khi bị trêu",High,"Nam chính, tính cách tinh nghịch."
Place,Qian Cui Shan,千翠山,Thiên Thúy Sơn,"",translate_meaning,Universal,High,"Ngọn núi nơi nhân vật chính sống."
Item,Zhu Xian Jian,诛仙剑,Tru Tiên Kiếm,"Kiếm gãy",translate_meaning,Combat,Medium,"Thanh kiếm thượng cổ hung dữ."

Hãy bắt đầu với Bảng 1 (Top 50 quan trọng nhất), sau đó, chờ tôi xác nhận "OK" rồi tiếp tục gửi từng phần tối thiểu 50 từ thuật ngữ cho tới hết.
```

---

## 🕸️ PROMPT 3: Character Relations (CSV)

**Copy đoạn này:**

```text
Hãy phân tích mạng lưới quan hệ nhân vật để xác định cách xưng hô (đại từ nhân xưng).

QUY TẮC QUAN TRỌNG:
1. **Output thuần CSV**: Có Header đầy đủ.
2. **Dấu ngoặc kép**: BẮT BUỘC dùng `"` cho các cột có chứa nhiều thông tin (Type, Context, Notes).
3. **Chiến lược**: Chỉ xuất **30 quan hệ** cốt lõi nhất trước. Sau đó hỏi tôi "Tiếp tục?".

HEADER:
Speaker_ID,Listener_ID,Relationship_Type,Context,Environment,Power_Dynamic,Emotional_State,Speaker_Pronoun,Listener_Term,Notes

VÍ DỤ MẪU (Hãy làm theo format này):
Speaker_ID,Listener_ID,Relationship_Type,Context,Environment,Power_Dynamic,Emotional_State,Speaker_Pronoun,Listener_Term,Notes
Cui Xiao Xuan,Cheng Shui Ruo,"romantic+same_sect","Mặc định","informal","equal","neutral","Ta","Nàng","Quan hệ yêu đương."
Cui Xiao Xuan,Cui Cai Ting,"master-disciple","Trang trọng","formal","inferior","respectful","Đệ tử","Sư phụ","Khi báo cáo công việc."
Cheng Shui Ruo,Cui Xiao Xuan,"romantic","Khi giận dỗi","private","equal","angry","Ta","Ngươi","Khi nam chính làm sai."

Hãy bắt đầu với Bảng 1 (Top 30 quan hệ cốt lõi).
```
