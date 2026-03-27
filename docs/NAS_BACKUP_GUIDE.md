# Hướng Dẫn Tự Động Sao Lưu Trên Synology NAS

Tài liệu này hướng dẫn cách thiết lập kịch bản tự động sao lưu dự án **Novel Translator** bằng công cụ **Task Scheduler** có sẵn trên Synology DSM.

## 1. Chuẩn bị

1. Đảm bảo bạn đã có file script: `scripts/nas_backup.py`.
2. Xác định đường dẫn tuyệt đối của thư mục dự án trên NAS (ví dụ: `/volume1/docker/novel-translator`).
   - Bạn có thể xem đường dẫn này trong ứng dụng **File Station** (Chuột phải vào thư mục -> Properties).

## 2. Lựa chọn phương thức sao lưu

Bạn có thể chọn một trong hai cách dưới đây tùy theo sở thích:

### Cách A: Sử dụng Shell Script (`.sh`) - **Đơn giản & Trực tiếp**

Dùng lệnh gốc của Linux/NAS, chạy cực nhanh.

- **File:** `scripts/nas_backup.sh`
- **Lệnh chạy:** `bash scripts/nas_backup.sh`

### Cách B: Sử dụng Python Script (`.py`) - **Thông minh & Linh hoạt**

Dễ dàng tùy chỉnh logic loại trừ thư mục sâu hoặc kiểm tra kích thước file phức tạp.

- **File:** `scripts/nas_backup.py`
- **Lệnh chạy:** `python3 scripts/nas_backup.py`

---

## 3. Thiết lập trên NAS DSM

### Bước 1: Cấp quyền thực thi (Quan trọng)

Trước khi chạy trên NAS, bạn cần cấp quyền thực thi cho file script. Hãy mở **Terminal** (SSH) hoặc dùng Task Scheduler chạy lệnh này một lần duy nhất:

```bash
chmod +x /volume3/docker/novel-translator/scripts/nas_backup.sh
```

### Bước 2: Tạo Task trong Task Scheduler

1. Truy cập **Control Panel** -> **Task Scheduler**.
2. **Create** -> **Scheduled Task** -> **User-defined script`.
3. Trong tab **Task Settings**, tại ô **Run Command**, nhập lệnh (chọn 1 trong 2):

**Nếu dùng Shell (Khuyên dùng cho NAS):**

```bash
cd /volume3/docker/novel-translator
bash scripts/nas_backup.sh
```

**Nếu dùng Python:**

```bash
cd /volume3/docker/novel-translator
python3 scripts/nas_backup.py
```

---

## 4. Tại sao ban đầu dùng Python thay vì Shell?

1. **Tính đa nền tảng:** Python chạy giống hệt nhau trên Windows và Linux.
2. **Logic phức tạp:** Python xử lý các điều kiện loại trừ (ví dụ: bỏ `data/progress` nhưng giữ `data/cache`) minh bạch và dễ đọc hơn các câu lệnh `find` hay `exclude` phức tạp của Shell.
3. **Xử lý lỗi:** Python cung cấp các khối `try-except` để báo cáo lỗi chi tiết hơn.

Tuy nhiên, trên môi trường thuần NAS như Synology, bản `.sh` là sự lựa chọn **gọn nhẹ và tối ưu nhất**.

---

## 5. Kiểm tra kết quả

1. Sau khi lưu Task, bạn có thể chạy thử ngay bằng cách chọn Task đó và nhấn **Run**.
2. Kiểm tra thư mục `backup/` trong dự án của bạn.
3. Bạn sẽ thấy file nén có định dạng: `novel-translator_v8.1.2_stable_YYYYMMDD_HHMMSS.zip`.

## 6. Ưu điểm của kịch bản này

- **Tiết kiệm dung lượng**: Tự động loại bỏ thư mục `venv`, các cache AI và các file log tạm thời.
- **An toàn**: Không nén đè các file cũ, mỗi bản backup đều có timestamp riêng.
- **Nhẹ**: Chỉ nén source code và dữ liệu cấu hình quan trọng.

---
**Người soạn:** Antigravity Agent
**Phiên bản:** v1.0
