# Hướng Dẫn Setup Virtual Environment cho Google GenAI SDK

**Ngày cập nhật:** 2025-01-09  
**Mục đích:** Hướng dẫn setup venv để sử dụng Google GenAI SDK mới

---

## 📋 Tổng Quan

Project này hỗ trợ cả 2 SDKs:
- **SDK Mới (Khuyến nghị):** `google-genai` - Package: `google-genai`
- **SDK Cũ (Fallback):** `google-generativeai` - Package: `google-generativeai`

---

## 🔧 Setup Virtual Environment

### **Bước 1: Kích hoạt Virtual Environment**

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### **Bước 2: Cài Đặt Dependencies**

**Cài đặt tất cả packages (bao gồm cả 2 SDKs):**
```bash
pip install -r requirements.txt
```

**Hoặc cài đặt SDK mới riêng (khuyến nghị):**
```bash
pip install google-genai>=0.2.0
```

**Hoặc cài đặt SDK cũ (fallback):**
```bash
pip install google-generativeai
```

---

## ✅ Verification

Sau khi kích hoạt venv, script `Activate.ps1` sẽ tự động kiểm tra và hiển thị:

```
✓ Google GenAI SDK (mới) đã được cài đặt (google-genai)
✓ Google GenerativeAI SDK (cũ) đã được cài đặt (google-generativeai)
→ Sẽ sử dụng Google GenAI SDK (mới) - google-genai
```

**Nếu chưa cài đặt:**
```
⚠ Google GenAI SDK (mới) chưa được cài đặt (google-genai)
  → Cài đặt: pip install google-genai
```

---

## 🔍 Kiểm Tra Thủ Công

**Kiểm tra SDK mới:**
```python
python -c "from google import genai; print('SDK mới available')"
```

**Kiểm tra SDK cũ:**
```python
python -c "import google.generativeai; print('SDK cũ available')"
```

---

## ⚙️ Configuration

SDK được sử dụng được config trong `config/config.yaml`:

```yaml
translation:
  use_new_sdk: true  # true: SDK mới, false: SDK cũ
```

**Lưu ý:**
- Nếu `use_new_sdk: true` nhưng SDK mới chưa được cài đặt → sẽ fallback về SDK cũ
- Nếu cả 2 SDK đều chưa được cài đặt → sẽ raise `ImportError`

---

## 📝 Requirements.txt

File `requirements.txt` đã được cập nhật để bao gồm cả 2 SDKs:

```
# SDK mới (khuyến nghị)
google-genai>=0.2.0

# SDK cũ (fallback)
google-generativeai
```

---

## 🎯 Kết Luận

**Đã cập nhật:**
- ✅ `requirements.txt` - Thêm `google-genai>=0.2.0`
- ✅ `venv/Scripts/Activate.ps1` - Thêm verification và thông báo

**Sau khi kích hoạt venv:**
- Script sẽ tự động kiểm tra SDK availability
- Hiển thị thông báo rõ ràng về SDK đang sử dụng
- Hướng dẫn cài đặt nếu thiếu

---

**Người cập nhật:** AI Assistant  
**Ngày:** 2025-01-09
