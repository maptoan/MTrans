# 🧠 AGENTS CENTRAL MEMORY (BỘ NHỚ TRUNG TÂM)

## 📌 Project Context (Bối cảnh dự án)
- **Tên dự án:** MTranslator (Trình dịch tiểu thuyết)
- **Mục tiêu:** Dịch tiểu thuyết song song, hỗ trợ OCR, dọn dẹp CJK và tối ưu hóa metadata.
- **Công nghệ chính:** Python, Gemini API (Multi-key), PowerShell (Trifecta Pipeline).

## 🛠️ Tool Interaction Rules (Quy tắc phối hợp)
1. **Gemini CLI:** Giữ vai trò Brain (Lập kế hoạch & Quản lý Task).
2. **OpenCode:** Giữ vai trò Worker (Thực thi mã nguồn & Fix bugs).
3. **Antigravity (Checklist):** Giữ vai trò Auditor (Kiểm định chất lượng & Báo cáo lỗi).

## 📜 Global Standards (Tiêu chuẩn chung)
- **Ngôn ngữ:** Mã nguồn & Comment dùng tiếng Anh. Tài liệu & Giải thích dùng tiếng Việt.
- **Workflow:** Quy trình Trifecta v7.0 (Auto-healing).
- **Quality:** Phải đạt 100% Checklist mới được phép commit.

## 🔄 Active Status (Trang thai hien tai)
- **Last Task:** Handover 2026-03-28 — Structured IR chunking tuân `max_effective_tokens` + benchmark ScienceOfRunning.pdf.
- **Current Pipeline:** v9.5 docs baseline + chunk IR cap (preprocessing).
- **Active Issues:** Full pytest vẫn có fail sẵn (async/legacy); chunk subset OK.
- **Phien ban hien tai:** v9.5 (docs) + Unreleased chunk IR fix

## 🧠 Shared Memory (Ghi nho cho cac Agent)
- [2026-03-28] **Chia chunk IR**: Không để mảnh quá dài; markdown sau OCR chỉ hợp PDF quét; PDF nhiều cột/chữ trong ảnh cần xử lý riêng (OCR/xuất file).
- [2026-03-19] **v9.2 Stable**: Unified layout (Tables/Headings/Images) & Quality Audit for English sources.
- [2026-02-26] **v8.3 Stable**: Workflow optimization, enable final_cleanup_pass, residual_cleanup.py fix.
- [2026-02-24] **Documentation Sync**: Cap nhat dong bo PROJECT_CONTEXT.md, CHANGELOG.md len v8.2.
- [2026-02-24] **ALGORITHM_DOCUMENTATION.md**: Tạo tài liệu giải thuật quản lý API Keys & Chunking tối ưu.
- [2026-02-18] **Unicode Fix**: PowerShell 5.1 cần thiết lập `$OutputEncoding`, `[Console]::InputEncoding`, `[Console]::OutputEncoding` và lệnh `chcp 65001` để hiển thị tiếng Việt chuẩn. File script nên lưu ở định dạng UTF-8 with BOM.
- [2026-02-18] **Context Overflow**: Khi gửi toàn bộ codebase vào prompt sửa lỗi, Gemini thường bị overload context hoặc tập trung sai chỗ. => Giải pháp: Chỉ gửi phần diff hoặc error log cụ thể (Context Differential).
- [2026-02-18] **Parallel Execution**: Chạy tuần tự các check tốn quá nhiều thời gian. => Giải pháp: Chạy song song P1-P5 giúp giảm 40% thời gian verify.
- [2026-02-18] **Gatekeeper Pattern**: Nếu Security check (P0) fail thì không nên chạy tiếp các check khác để tiết kiệm resource.
- [2026-02-17] Đã nâng cấp thành công cơ chế Self-healing (3 retries).
- [2026-02-17] Đã chuẩn hóa toàn bộ import bằng Ruff.
- [2026-02-17] Thiết lập AGENTS.md làm trung tâm điều phối thông tin.
