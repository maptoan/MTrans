# 📚 HƯỚNG DẪN THAM KHẢO CÁC MẪU PROMPT

## 🎯 **Mục đích tài liệu**
Tài liệu này giải thích các mẫu prompt được sử dụng trong hệ thống dịch thuật, bao gồm vai trò, ý nghĩa và cách áp dụng từng prompt.

---

## 📋 **MỤC LỤC**
1. [Prompt chính dịch thuật](#1-prompt-chính-dịch-thuật)
2. [Prompt contextual retry](#2-prompt-contextual-retry)
3. [Prompt micro translation](#3-prompt-micro-translation)
4. [Rào chắn CJK](#4-rào-chắn-cjk)
5. [Nguyên tắc văn học](#5-nguyên-tắc-văn-học)
6. [Checklist chất lượng](#6-checklist-chất-lượng)

---

## 1. **PROMPT CHÍNH DỊCH THUẬT** (Main Prompt)

### **Vị trí:** `src/translation/prompt_builder.py` - `build_main_prompt()`

### **Vai trò:**
Đây là prompt CHÍNH và QUAN TRỌNG NHẤT, được sử dụng để dịch từng chunk văn bản. Prompt này kết hợp 9 lớp hướng dẫn thành một siêu prompt toàn diện.

### **Cấu trúc gồm 9 phần:**

#### **1.1. Nguyên tắc văn học** (`_build_literary_guidelines()`)
```python
"""
[NGUYÊN TẮC VĂN HỌC BẮT BUỘC]

1. NHỊP ĐIỆU CÂU VĂN:
   - Xen kẽ câu dài (20-35 từ) và câu ngắn (5-15 từ)
   - Tránh 3 câu dài liên tiếp
   - Phân bố: 40% câu ngắn, 40% trung bình, 20% câu dài

2. TỐI ƯU CẤU TRÚC CÂU:
   - Giới hạn: Mỗi câu tối đa 2 mệnh đề phụ
   - Nếu >3 mệnh đề → BẮT BUỘC tách thành 2-3 câu

3. TRÁNH LẶP TỪ/CỤM TỪ:
   - Không lặp từ >2 lần trong cùng đoạn
   - Thay thế bằng từ đồng nghĩa hoặc đại từ

4. ĐA DẠNG HỘI THOẠI:
   - Tránh "X nói:" >2 lần/cảnh
   - Xen kẽ: hành động, biểu cảm, động từ đa dạng

5. PHÂN ĐOẠN HỢP LÝ:
   - Đoạn >8 dòng → xem xét chia nhỏ
   - Thêm câu chuyển tiếp tự nhiên

6. LOẠI BỎ DƯ THỪA:
   - Cắt từ không cần: "bèn", "liền", "rồi"
   - Gộp câu ngắn có nội dung liên quan

7. BỘ LỌC TỪ DƯ THỪA TỰ ĐỘNG:
   - Quét từ xuất hiện >3 lần/đoạn
   - Chỉ giữ lần đầu khi cần nhấn mạnh

8. TỐI ƯU CHUỖI HÀNH ĐỘNG:
   - Hành động >2 bước → chia thành 2-3 câu
   - Mỗi câu tập trung 1-2 hành động chính

9. ĐIỀU CHỈNH GIỌNG ĐIỆU:
   - Cảm xúc mạnh → ngắn gọn, có lực
   - Hành động nhanh → ngắn, mạnh mẽ
   - Suy tư → chậm rãi hơn
"""
```

**Ý nghĩa:** Đảm bảo bản dịch có nhịp điệu tự nhiên, tránh lặp từ, và đa dạng hóa cách diễn đạt.

#### **1.2. Bộ từ điển thay thế động từ** (`_build_verb_variation_guide()`)
```python
"""
[BỘ TỪ ĐIỂN THAY THẾ ĐỘNG TỪ]

THAY CHO "nói": đáp, giải thích, buột miệng, thì thầm, gằn giọng, trả lời, lên tiếng, bật ra
THAY CHO "đi": bước, tiến, lướt, sải, rảo, di chuyển, bước đi, tiến lên
THAY CHO "nhìn": liếc, ngắm, nhìn chằm chằm, dán mắt, ngó, lướt mắt, đảo mắt, nheo mắt
THAY CHO "nghĩ": suy ngẫm, trầm ngâm, trăn trở, cân nhắc, băn khoăn, suy nghĩ
THAY CHO "cầm": nắm, túm, vịn, giữ, ôm, bưng
THAY CHO "ngồi": vào chỗ, ngồi xuống, ngồi phịch, ngồi thụp
"""
```

**Ý nghĩa:** Cung cấp từ đồng nghĩa để đa dạng hóa văn phong, tránh lặp từ.

#### **1.3. Hướng dẫn văn phong** (`style_manager.build_style_instructions()`)
Load từ file `config/metadata/style_profile.json`, chứa:
- Hướng dẫn về văn phong dịch
- Đặc điểm ngôn ngữ
- Sắc thái diễn đạt

**Ý nghĩa:** Duy trì phong cách dịch nhất quán trong toàn bộ tác phẩm.

#### **1.4. Mệnh lệnh biên tập** (`_build_editing_commands()`)
```python
"""
[MỆNH LỆNH BIÊN TẬP - THỰC HIỆN TUẦN TỰ]

BƯỚC 1: RÀ SOÁT TIÊU ĐỀ
- Tìm cụm có dạng tiêu đề (ngắn, độc lập, không có dấu chấm)
- BẮT BUỘC bọc trong [H1]...[/H1]

BƯỚC 2: LỌC TỪ DƯ THỪA
- Quét các từ "rồi", "bèn", "liền", "đã", "là" xuất hiện >3 lần
- Xem xét loại bỏ các lần không cần thiết

BƯỚC 3: TỐI ƯU CÂU DÀI
- Quét câu >35 từ hoặc >2 mệnh đề phụ
- Tách thành 2-3 câu ngắn hơn

BƯỚC 4: TỐI ƯU CHUỖI HÀNH ĐỘNG
- Tìm câu mô tả >2 hành động
- Chia thành 2-3 câu với nhịp rõ ràng

BƯỚC 5: ĐA DẠNG HÓA HỘI THOẠI
- Tìm "X nói/hỏi/đáp:"
- Nếu >2 lần trong cùng cảnh → thay đổi
- Dùng: hành động, biểu cảm, động từ khác

BƯỚC 6: KIỂM TRA LẶP TỪ
- Quét từ/cụm xuất hiện >2 lần trong 5 câu
- Thay thế lần 2, 3... bằng từ đồng nghĩa

BƯỚC 7: PHÂN ĐOẠN HỢP LÝ
- Tìm đoạn >150 từ
- Tách tại điểm chuyển đổi tự nhiên
- Thêm câu chuyển tiếp nếu cần

BƯỚC 8: ĐIỀU CHỈNH NHỊP ĐIỆU
- Đảm bảo không >3 câu dài liên tiếp
- Chèn câu ngắn để tạo nhịp nghỉ

BƯỚC 9: ĐIỀU CHỈNH GIỌNG ĐIỆU
- Cảm xúc mạnh → ngắn, súc tích
- Hành động nhanh → ngắn, có lực
"""
```

**Ý nghĩa:** Hướng dẫn AI tuần tự qua 9 bước biên tập để đảm bảo chất lượng.

#### **1.5. Glossary và quan hệ nhân vật**
```python
"""
[NGỮ CẢNH KỸ THUẬT]

[BẢNG THUẬT NGỮ]
{term} → {translation}
...

[QUAN HỆ NHÂN VẬT]
{character1} {relation} {character2}
...
"""
```

**Ý nghĩa:** Đảm bảo dịch nhất quán về thuật ngữ và mối quan hệ nhân vật.

#### **1.6. Ngữ cảnh từ đoạn trước**
```python
"""
[NGỮ CẢNH TRƯỚC ĐÓ]
{context_text}

PHÂN TÍCH NGỮ CẢNH:
- Tốc độ tường thuật: {pace}
- Độ dài câu trung bình: ~{avg_length} từ
- Giọng điệu: Quan sát và duy trì phong cách tương tự

LƯU Ý:
- Đảm bảo liền mạch với đoạn trên về văn phong
- Tránh lặp lại từ/cụm từ/cấu trúc đã dùng
- Duy trì sự HÒA HỢP về tốc độ và giọng điệu
"""
```

**Ý nghĩa:** Giữ tính liền mạch với đoạn trước, tránh thay đổi văn phong đột ngột.

#### **1.7. Rào chắn CJK**
```python
"""
[RÀO CHẮN CHỐNG SÓT KÝ TỰ TIẾNG TRUNG]

QUY TẮC TUYỆT ĐỐI:
- Mọi ký tự CJK trong đoạn văn PHẢI được dịch sang tiếng Việt
- KHÔNG để lại bất kỳ ký tự CJK nào trong bản dịch cuối cùng
- Nếu phát hiện còn CJK → TỰ ĐỘNG viết lại câu đó
"""
```

**Ý nghĩa:** Ngăn chặn việc sót ký tự tiếng Trung trong bản dịch.

#### **1.8. Quy trình thực hiện**
```python
"""
[ĐOẠN VĂN BẢN CẦN DỊCH]
{chunk_text}

QUY TRÌNH THỰC HIỆN:
1. Đọc kỹ đoạn văn và ngữ cảnh trước
2. Dịch sang tiếng Việt
3. Thực hiện TUẦN TỰ tất cả bước biên tập (Bước 1-9)
4. Kiểm tra theo [KIỂM TRA CHẤT LƯỢNG]
5. THỰC HIỆN "RÀ SOÁT CJK"
6. Thực hiện [KIỂM TRA HẬU KỲ]
7. Nếu chưa đạt → quay lại chỉnh sửa

CHỈ TRẢ VỀ: Bản dịch tiếng Việt hoàn chỉnh
"""
```

**Ý nghĩa:** Hướng dẫn AI quy trình dịch và biên tập từng bước.

#### **1.9. Checklist chất lượng** (`_build_quality_checklist()`)
```python
"""
[KIỂM TRA CHẤT LƯỢNG CUỐI CÙNG]

☑ Không có câu >35 từ hoặc >3 mệnh đề
☑ Phân bố độ dài câu cân đối
☑ Không có từ lặp >2 lần trong 5 câu
☑ Các từ "rồi", "bèn" không >3 lần/đoạn
☑ Không >3 câu dài liên tiếp
☑ Hội thoại đa dạng (không "X nói:" >2 lần/cảnh)
☑ Đoạn văn <150 từ/đoạn
☑ Có câu chuyển tiếp tự nhiên
☑ Tiêu đề đã bọc [H1]...[/H1]
☑ TUYỆT ĐỐI KHÔNG còn ký tự CJK
"""
```

**Ý nghĩa:** Kiểm tra checklist cuối cùng trước khi trả về bản dịch.

#### **1.10. Kiểm tra hậu kỳ** (`_build_post_processing_check()`)
```python
"""
[KIỂM TRA HẬU KỲ - BƯỚC CUỐI CÙNG]

Đọc lại TOÀN BỘ như độc giả thông thường:

1. KIỂM TRA ĐỘC LẬP: Đọc thành tiếng - có vấp váp không?
2. KIỂM TRA CẢM XÚC: Câu cảm xúc có đủ sức, đủ mạnh không?
3. KIỂM TRA LIỀN MẠCH: Chuyển đoạn có tự nhiên không?
4. KIỂM TRA HÌNH ẢNH: Mô tả có rõ ràng, sinh động không?
5. KIỂM TRA NHỊP ĐIỆU: Đọc có êm tai không?

CHỈ TRẢ VỀ KHI ĐÃ HOÀN TOÀN HÀI LÒNG.
"""
```

**Ý nghĩa:** Đảm bảo bản dịch đọc tự nhiên như văn học thật.

---

## 2. **PROMPT CONTEXTUAL RETRY** (Retry với ngữ cảnh)

### **Vị trí:** `src/translation/translator.py` - `_build_contextual_translation_prompt()`

### **Vai trò:**
Dùng để dịch lại các câu có từ sót CJK, dịch theo NGỮ CẢNH (contextual) thay vì từng từ riêng lẻ.

### **Cấu trúc:**
```python
"""
HƯỚNG DẪN:
Bạn là chuyên gia dịch Trung-Việt. Dịch lại CÁC CÂU GỐC có chứa ký tự CJK sang tiếng Việt tự nhiên.
KHÔNG để sót bất kỳ ký tự CJK nào. Chỉ trả về JSON mảng các đối tượng {original, translation}.

GHI CHÚ:
- Giữ nghĩa và sắc thái; viết tự nhiên, chuẩn văn phong
- Nếu câu gốc có CJK → BẮT BUỘC dịch hết
- Tuyệt đối KHÔNG in thêm text ngoài JSON

VÍ DỤ:
[
  {"original": "千萬不用客气", "translation": "ngàn vạn lần đừng khách sáo"},
  {"original": "魁梧", "translation": "vạm vỡ/khôi ngô (tuỳ ngữ cảnh)"},
  {"original": "魑魅魍魉", "translation": "yêu ma quỷ quái"}
]

DỮ LIỆU CẦN DỊCH:
[
  {"original": "{sentence_with_cjk}"}
]

ĐỊNH DẠNG TRẢ VỀ: JSON array với phần tử {"original": string, "translation": string}
"""
```

### **Khi nào sử dụng:**
- Khi phát hiện còn từ sót CJK trong bản dịch
- Yêu cầu AI dịch lại toàn bộ câu (không phải từng từ riêng)
- Đảm bảo dịch theo ngữ cảnh (contextual)

### **Ưu điểm:**
- Dịch theo ngữ cảnh → chính xác hơn
- Yêu cầu trả về JSON → dễ parse
- Có ví dụ → AI hiểu rõ format

---

## 3. **PROMPT MICRO TRANSLATION** (Dịch vi mô)

### **Vị trí:** `src/translation/prompt_builder.py` - `build_micro_translation_prompt()`

### **Vai trò:**
Dùng để dịch các từ/cụm từ đơn lẻ (fallback khi contextual retry thất bại).

### **Cấu trúc:**
```python
"""
Bạn là công cụ dịch thuật Trung-Việt. Dịch các thuật ngữ sau.
QUY TẮC: Mỗi dòng theo định dạng 'Từ gốc | Bản dịch'

{term1} | 
{term2} | 
...
"""
```

### **Khi nào sử dụng:**
- Khi contextual retry thất bại
- Fallback cho từ sót còn lại
- Đơn giản, nhanh

### **Nhược điểm:**
- Không có ngữ cảnh → có thể thiếu chính xác
- Dịch từng từ → mất sắc thái văn chương

---

## 4. **RÀO CHẮN CJK**

### **Vị trí:** `src/translation/prompt_builder.py` - `build_main_prompt()`

### **Vai trò:**
Ngăn chặn việc sót ký tự tiếng Trung trong bản dịch cuối cùng.

### **Cấu trúc:**
```python
"""
[RÀO CHẮN CHỐNG SÓT KÝ TỰ TIẾNG TRUNG]

QUY TẮC TUYỆT ĐỐI:
- Mọi ký tự CJK (汉/漢/かな/カナ/かな/カタカナ/한글) PHẢI được dịch sang tiếng Việt
- KHÔNG để lại bất kỳ ký tự CJK nào trong bản dịch cuối cùng
- Kể cả từ đơn, cụm đơn lẻ hay chữ lồng trong câu
- Nếu phát hiện còn CJK → TỰ ĐỘNG viết lại câu đó
- Đầu ra chỉ gồm tiếng Việt thuần

Ví dụ:
- Trước: "千萬不用客气" → Sau: "ngàn vạn lần đừng khách sáo"
- Trước: "魁梧" → Sau: "khôi ngô, vạm vỡ"
"""
```

### **Ý nghĩa:**
- Đảm bảo không còn ký tự Trung trong bản dịch
- Yêu cầu AI tự kiểm tra và sửa nếu sót
- Có ví dụ minh họa → dễ hiểu

---

## 5. **NGUYÊN TẮC VĂN HỌC** (Literary Guidelines)

### **Vị trí:** `src/translation/prompt_builder.py` - `_build_literary_guidelines()`

### **Vai trò:**
Hướng dẫn AI biên tập bản dịch theo tiêu chuẩn văn học, đảm bảo:
- Nhịp điệu tự nhiên
- Tránh lặp từ
- Đa dạng hóa cách diễn đạt
- Phân đoạn hợp lý
- Giọng điệu phù hợp

### **9 nguyên tắc chính:**
1. **NHỊP ĐIỆU CÂU VĂN** - Xen kẽ câu ngắn/dài
2. **TỐI ƯU CẤU TRÚC CÂU** - Tối đa 2 mệnh đề/câu
3. **TRÁNH LẶP TỪ** - Không lặp >2 lần
4. **ĐA DẠNG HỘI THOẠI** - Tránh "X nói:" >2 lần/cảnh
5. **PHÂN ĐOẠN HỢP LÝ** - Chia đoạn dài
6. **LOẠI BỎ DƯ THỪA** - Cắt từ không cần
7. **BỘ LỌC TỪ DƯ THỪA** - Quét từ lặp >3 lần
8. **TỐI ƯU CHUỖI HÀNH ĐỘNG** - Chia hành động >2 bước
9. **ĐIỀU CHỈNH GIỌNG ĐIỆU** - Phù hợp cảm xúc

### **Ví dụ đi kèm:**
Mỗi nguyên tắc có ví dụ TỐT và XẤU để AI hiểu rõ.

---

## 6. **CHECKLIST CHẤT LƯỢNG**

### **Vị trí:** `src/translation/prompt_builder.py` - `_build_quality_checklist()`

### **Vai trò:**
Checklist kiểm tra chất lượng cuối cùng trước khi trả về bản dịch.

### **Các tiêu chí:**
```python
"""
☑ Không có câu >35 từ hoặc >3 mệnh đề
☑ Phân bố độ dài câu cân đối (40%/40%/20%)
☑ Không có từ/cụm lặp >2 lần trong 5 câu
☑ Các từ "rồi", "bèn", "liền" không >3 lần/đoạn
☑ Không >3 câu dài liên tiếp
☑ Hội thoại đa dạng (không "X nói:" >2 lần/cảnh)
☑ Đoạn văn <150 từ/đoạn
☑ Có câu chuyển tiếp tự nhiên
☑ Tiêu đề đã bọc [H1]...[/H1]
☑ TUYỆT ĐỐI KHÔNG còn ký tự CJK
☑ Ngữ cảnh liền mạch với đoạn trước
☑ Câu mở đầu đoạn ngắn gọn và hấp dẫn
☑ Giọng điệu phù hợp
☑ Chuỗi hành động đã được tách rõ ràng
"""
```

### **Quy tắc:**
- NẾU BẤT KỲ MỤC NÀO CHƯA ĐẠT → QUAY LẠI CHỈNH SỬA
- Chỉ trả về khi đã vượt qua TẤT CẢ tiêu chí

---

## 📊 **TỔNG KẾT**

### **Các loại prompt:**
1. **Main Prompt** - Dịch chunk chính (9 lớp hướng dẫn)
2. **Contextual Retry** - Dịch lại theo câu (có ngữ cảnh)
3. **Micro Translation** - Dịch từng từ (fallback)
4. **CJK Guardrail** - Rào chắn chống sót ký tự Trung
5. **Literary Guidelines** - Nguyên tắc văn học (9 quy tắc)
6. **Quality Checklist** - Checklist kiểm tra cuối (14 tiêu chí)

### **Luồng sử dụng:**
```
Main Prompt (dịch chunk)
    ↓
Có từ sót CJK?
    ↓ CÓ
Contextual Retry (dịch lại theo câu)
    ↓ Vẫn còn?
Micro Translation (dịch từng từ)
    ↓
Quality Checklist
```

### **Đặc điểm nổi bật:**
- **Main Prompt** rất dài và chi tiết (9 lớp)
- **Contextual Retry** ngắn gọn, yêu cầu JSON
- **Micro Translation** cực đơn giản (fallback)
- **CJK Guardrail** tuyệt đối không cho phép sót
- **Literary Guidelines** có ví dụ minh họa
- **Quality Checklist** kiểm tra 14 tiêu chí

### **Lưu ý quan trọng:**
1. Main Prompt là MẠNH NHẤT vì có 9 lớp hướng dẫn
2. Contextual Retry CHÍNH XÁC hơn Micro vì có ngữ cảnh
3. Micro Translation chỉ dùng khi BẮT BUỘC (fallback)
4. CJK Guardrail là TUYỆT ĐỐI (không cho phép ngoại lệ)
5. Quality Checklist là CỬA ẢI CUỐI CÙNG trước khi trả về

---

## 🔍 **FILE LIÊN QUAN**

- `src/translation/prompt_builder.py` - Xây dựng Main Prompt
- `src/translation/translator.py` - Xây dựng Contextual Retry
- `src/managers/style_manager.py` - Văn phong
- `src/managers/glossary_manager.py` - Thuật ngữ
- `src/managers/relation_manager.py` - Quan hệ nhân vật
- `config/metadata/style_profile.json` - Profile văn phong

---

**📝 Tài liệu được tạo: 2025-10-28**  
**📌 Phiên bản: v1.7.stable**
