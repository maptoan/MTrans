# Project: Novel Translator Web UI
# Date: 2026-02-25
# Task: Xây dựng giao diện Web (React + MUI) và API Bridge (FastAPI).

## 📋 Plan

### Phase 1: Backend API Bridge (FastAPI)
- [ ] **Khởi tạo `src/api/`:** Tạo Server FastAPI để điều khiển `NovelTranslator`.
- [ ] **Endpoints:**
    - `GET /config`: Đọc cấu hình hiện tại.
    - `POST /config`: Cập nhật cấu hình.
    - `GET /files`: Duyệt file trong thư mục input/metadata.
    - `WS /ws/progress`: WebSocket để stream log và % hoàn thành.
    - `POST /start`, `POST /stop`: Điều khiển tiến trình.

### Phase 2: Frontend Scaffolding (React + MUI)
- [ ] **Scaffold:** Sử dụng Vite để khởi tạo dự án React (TypeScript).
- [ ] **Setup MUI:** Cài đặt `@mui/material`, `@emotion/react`, `@mui/icons-material`.
- [ ] **Layout:** Xây dựng khung giao diện Responsive (Sidebar, Header, Main Content).

### Phase 3: Component Implementation
- [ ] **ConfigForm:** Linh hoạt cho phép sửa API Keys, Model, Paths.
- [ ] **ProgressDashboard:** Thanh tiến trình (LinearProgress) và thông tin Worker.
- [ ] **LogViewer:** Hiển thị tracklog với màu sắc theo icon (giống hiện tại).

### Phase 4: Integration & Optimization
- [ ] Kết nối Frontend với Backend qua API và WebSocket.
- [ ] Tối ưu Re-render để đảm bảo mượt mà khi log đổ về liên tục.

### Phase 5: Verification
- [ ] Chạy thử quy trình dịch hoàn chỉnh qua Web UI.
