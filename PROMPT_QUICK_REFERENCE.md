# 🚀 PROMPT QUICK REFERENCE

## 📋 **Bảng tóm tắt các mẫu prompt**

### **1. MAIN PROMPT** (Prompt chính dịch thuật)
**Vai trò:** Dịch từng chunk với 9 lớp hướng dẫn  
**Vị trí:** `src/translation/prompt_builder.py`  
**Khi nào dùng:** Dịch chunk văn bản chính  
**Đặc điểm:** Dài, chi tiết, 9 phần (literary + verb guide + style + editing + glossary + context + CJK guard + task + checklist)

---

### **2. CONTEXTUAL RETRY** (Dịch lại theo ngữ cảnh)
**Vai trò:** Dịch lại câu có từ sót CJK  
**Vị trí:** `src/translation/translator.py`  
**Khi nào dùng:** Khi phát hiện còn từ sót CJK  
**Đặc điểm:** Ngắn gọn, yêu cầu JSON format `{original, translation}`  
**Ưu điểm:** Dịch theo ngữ cảnh → chính xác hơn

---

### **3. MICRO TRANSLATION** (Dịch vi mô)
**Vai trò:** Dịch từng từ đơn lẻ (fallback)  
**Vị trí:** `src/translation/prompt_builder.py`  
**Khi nào dùng:** Khi contextual retry thất bại  
**Đặc điểm:** Cực đơn giản, format `Từ gốc | Bản dịch`  
**Nhược điểm:** Không có ngữ cảnh → kém chính xác

---

### **4. CJK GUARDRAIL** (Rào chắn chống sót)
**Vai trò:** Ngăn chặn việc sót ký tự tiếng Trung  
**Vị trí:** Trong Main Prompt  
**Khi nào dùng:** Luôn luôn (tuyệt đối)  
**Đặc điểm:** Không cho phép ngoại lệ, có ví dụ minh họa

---

### **5. LITERARY GUIDELINES** (Nguyên tắc văn học)
**Vai trò:** Hướng dẫn biên tập theo tiêu chuẩn văn học  
**Vị trí:** Trong Main Prompt  
**Khi nào dùng:** Luôn luôn (tất cả chunks)  
**Đặc điểm:** 9 nguyên tắc + ví dụ TỐT/XẤU  
**Nội dung:** Nhịp điệu, cấu trúc, tránh lặp, đa dạng hội thoại, phân đoạn, loại bỏ dư thừa, bộ lọc từ, chuỗi hành động, giọng điệu

---

### **6. QUALITY CHECKLIST** (Checklist chất lượng)
**Vai trò:** Kiểm tra cuối cùng trước khi trả về  
**Vị trí:** Trong Main Prompt  
**Khi nào dùng:** Luôn luôn (bước cuối)  
**Đặc điểm:** 14 tiêu chí, có/không checkbox  
**Quy tắc:** Chỉ trả về khi ĐẠT TẤT CẢ

---

## 🔄 **Luồng sử dụng**

```
Main Prompt (dịch chunk)
    ↓
Còn từ sót CJK?
    ↓ CÓ
Contextual Retry
    ↓ Vẫn còn?
Micro Translation (fallback)
    ↓
Quality Checklist
    ↓
Trả về bản dịch
```

---

## ⚠️ **Lưu ý quan trọng**

1. **Main Prompt** là mạnh nhất vì có 9 lớp hướng dẫn
2. **Contextual Retry** chính xác hơn vì có ngữ cảnh
3. **Micro Translation** chỉ dùng khi bắt buộc (fallback)
4. **CJK Guardrail** là tuyệt đối (không cho phép ngoại lệ)
5. **Quality Checklist** là cửa ải cuối cùng (14 tiêu chí)

---

## 📁 **Files liên quan**

- `src/translation/prompt_builder.py` - Main Prompt
- `src/translation/translator.py` - Contextual Retry
- `config/metadata/style_profile.json` - Văn phong
- `config/metadata/glossary.csv` - Thuật ngữ
- `config/metadata/character_relations.csv` - Quan hệ

---

**📝 Tài liệu tóm tắt - v1.7.stable**
