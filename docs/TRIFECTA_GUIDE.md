# 🚀 TRIFECTA PIPELINE (v10.0 - Portable Edition)

Bộ công cụ tự động hóa quy trình **Lập kế hoạch -> Thực thi -> Kiểm định (Plan -> Code -> Verify)** dành cho bất kỳ dự án nào.

---

## 🛠️ Cấu trúc dự án Trifecta Chuẩn

Một dự án sử dụng Trifecta nên có cấu trúc như sau:
```text
Project-Root/
├── .agent/
│   ├── rules/          # Quy tắc của Agent (GEMINI.md)
│   ├── scripts/        # Checklist.py (Kiểm định)
│   └── tasks/          # Các file task .md
├── data/
│   ├── cache/          # File trung gian (Refinement context)
│   └── reports/        # Kết quả chạy Trifecta
├── scripts/
│   ├── trifecta-run.ps1 # Engine lõi (đã đổi tên từ trifecta-core.ps1)
│   └── trifecta-setup.ps1 # Script khởi tạo môi trường
└── docs/               # Tài liệu hướng dẫn
```

---

## 🚀 Cách triển khai vào Dự án Mới

1.  **Sử dụng script setup:**
    ```powershell
    # Từ dự án hiện tại, copy file setup sang dự án mới hoặc chạy trực tiếp:
    .\scripts\trifecta-setup.ps1 -ProjectDir "D:\Duong\Dan\Den\Du-An-Moi"
    ```

2.  **Cấu hình Checklist (Tùy chọn):**
    Copy file `checklist.py` và các script kiểm định vào thư mục `.agent/scripts/` để Trifecta có thể tự động kiểm tra code.

---

## ⚡ Cách sử dụng Pipeline

### 1. Tạo file Task
Lưu yêu cầu công việc vào một file Markdown tại thư mục `.agent/tasks/my-feature.md`.

### 2. Chạy Pipeline
Mở Terminal tại thư mục gốc của dự án và chạy các lệnh sau:

```powershell
# Chạy mặc định (3 lượt thử, chế độ quét toàn diện - full scan)
.\scripts\trifecta-run.ps1 -TaskFile .agent\tasks\my-feature.md

# Chạy nhanh (Bỏ qua kiểm định, không tự động commit)
.\scripts\trifecta-run.ps1 -TaskFile .agent\tasks\my-feature.md -Mode fast -NoCommit

# Chạy với tối đa 5 lần tự động sửa lỗi
.\scripts\trifecta-run.ps1 -TaskFile .agent\tasks\my-feature.md -MaxRetries 5
```

---

## 🧠 Cơ chế Tự phục hồi (Self-Healing)

Nếu quy trình kiểm định (`checklist.py`) báo lỗi (P0-P5 thất bại), Trifecta sẽ:
1.  Trích xuất thông tin lỗi từ log.
2.  Tạo file ngữ cảnh sửa lỗi tại `data/cache/refinement_context.md` bao gồm: **Lỗi hiện tại + Yêu cầu gốc**.
3.  Gửi dữ liệu này ngược lại cho Gemini/OpenCode để yêu cầu thực hiện sửa lỗi.
4.  Lặp lại quy trình tối đa `MaxRetries` lần cho đến khi thành công hoặc hết lượt thử.

---

## 📈 Ưu điểm của phiên bản v10.0
- **Unicode Support:** Tự động thiết lập `chcp 65001` và UTF-8 cho PowerShell, hiển thị tiếng Việt hoàn hảo.
- **Auto-Commit:** Tự động tạo Git commit kèm theo thông tin số lượt thử (Attempts) khi hoàn thành.
- **Flexible Modes:** Hỗ trợ các chế độ `lite` (nhanh), `full` (đầy đủ), `fast` (bỏ qua kiểm định) phù hợp cho từng mục đích sử dụng.
