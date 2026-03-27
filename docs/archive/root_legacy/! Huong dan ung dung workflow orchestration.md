# Hướng Dẫn Sử Dụng Workflow Orchestration Cho Novel Translator

## Mục Lục
1. [Giới Thiệu](#giới-thiệu)
2. [Cài Đặt & Chuẩn Bị](#cài-đặt--chuẩn-bị)
3. [Sử Dụng Script Khởi Tạo Session](#sử-dụng-script-khởi-tạo-session)
4. [Workflow Hoàn Chỉnh](#workflow-hoàn-chỉnh)
5. [Sử Dụng Với AI Agent](#sử-dụng-với-ai-agent)
6. [Templates](#templates)
7. [Câu Lệnh Nhanh](#câu-lệnh-nhanh)

---

## 1. Giới Thiệu

### Workflow Orchestration Là Gì?
Workflow Orchestration là bộ quy tắc để tổ chức và quản lý phiên làm việc hiệu quả:

| Nguyên Tắc | Mô Tả |
|------------|-------|
| **Plan First** | Lập kế hoạch trước mọi task phi trivial |
| **Verify Before Done** | Xác minh trước khi mark complete |
| **Self-Improvement** | Ghi nhận lessons sau mỗi correction |
| **Subagent Strategy** | Dùng subagent để giữ context sạch |
| **Demand Elegance** | Tìm giải pháp elegant, tránh hacky fix |
| **Autonomous Bug Fixing** | Fix bug ngay, không cần hỏi |

### Mục Đích
- Giảm context overflow khi giao tiếp với AI
- Đảm bảo quality trước khi complete
- Ghi nhận lessons để tránh lặp lại mistakes
- Tăng hiệu quả khi làm việc với AI agent

---

## 2. Cài Đặt & Chuẩn Bị

### Yêu Cầu
- Python 3.10+
- Project Novel Translator đã cài đặt

### Cấu Trúc Files
```
project/
├── tasks/
│   ├── todo_template.md          # Template cho task planning
│   ├── lessons_template.md       # Template cho lessons
│   ├── todo_[PROJECT]_[DATE].md # Task file (auto-generated)
│   └── lessons.md                # Lessons file (auto-created)
├── scripts/
│   └── init_session.py           # Script khởi tạo session
├── workflow_orchestration.md     # File gốc
├── AGENTS.md                    # Project context
└── config/
    └── config.yaml               # Config
```

### Kiểm Tra Files
```bash
ls -la tasks/
ls -la scripts/init_session.py
```

---

## 3. Sử Dụng Script Khởi Tạo Session

### 3.1. Các Chế Độ

```bash
# Chế độ tương tác (menu)
python scripts/init_session.py

# Quick start task mới
python scripts/init_session.py --task HMQT

# Tạo/freshen lessons.md
python scripts/init_session.py --init

# Show workflow summary
python scripts/init_session.py --review

# Show recent lessons
python scripts/init_session.py --lessons
```

### 3.2. Quick Start

```bash
# Bước 1: Khởi tạo task mới
python scripts/init_session.py --task HMQT
```

Output:
```
[OK] Session initialized!

Files created:
  - tasks\todo_HMQT_20260224_2156.md

Next steps:
  1. Edit todo_HMQT_*.md with your plan
  2. Run: python main.py
  3. After completion: update tasks/lessons.md
```

### 3.3. Xem Workflow Checklist

```bash
python scripts/init_session.py --review
```

Output:
```
[CHECKLIST] WORKFLOW:

Before Session:
  [OK] Check AGENTS.md for updates
  [OK] Review recent lessons (tasks/lessons.md)
  [OK] Verify config.yaml settings

During Session:
  [OK] Plan first (tasks/todo_*.md)
  [OK] Verify at each step
  [OK] Update todo.md progress

After Session:
  [OK] Verify final output
  [OK] Update lessons.md with new learnings
  [OK] Summary to user
```

---

## 4. Workflow Hoàn Chỉnh

### 4.1. Trước Phiên Làm Việc

```bash
# Bước 1: Xem context hiện tại
python scripts/init_session.py --review

# Bước 2: Xem lessons gần đây
python scripts/init_session.py --lessons

# Bước 3: Xem AGENTS.md
cat AGENTS.md
```

### 4.2. Bắt Đầu Task Mới

```bash
# Tạo todo file cho task
python scripts/init_session.py --task HMQT

# Edit todo file để lập kế hoạn
# Xem mẫu: tasks/todo_template.md
```

### 4.3. Trong Phiên Làm Việc

1. **Theo dõi progress trong todo.md**
2. **Verify sau mỗi bước quan trọng**
3. **Ghi nhận issues vào lessons.md nếu có**

### 4.4. Kết Thúc Phiên

1. **Verify output cuối cùng**
2. **Update lessons.md** với các learnings mới
3. **Summary cho user**

---

## 5. Sử Dụng Với AI Agent

### 5.1. OpenCode

```markdown
Task: [Mô tả task]

Project: Novel Translator v8.2
Pipeline: Trifecta v7.0

Hãy tuân thủ workflow_orchestration.md:
1. Plan first - tạo tasks/todo_[date].md
2. Verify trước khi done
3. Update tasks/lessons.md nếu có correction

Context:
- Config: config/config.yaml (77 API keys)
- AGENTS.md: xem project context
- Tasks: tasks/todo_*.md, tasks/lessons.md
```

### 5.2. Gemini CLI

```markdown
# Task
[Mô tả task]

# Constraints
- Follow workflow_orchestration.md
- Plan: tasks/todo.md
- Verify before complete
- Document lessons: tasks/lessons.md

# Project Context
- Novel Translator v8.2
- Pipeline: Trifecta v7.0
- Active keys: 77
```

### 5.3. Cursor/Claude Code

```markdown
## Context
- Project: Novel Translator
- Version: v8.2
- Pipeline: Trifecta v7.0

## Task
[Mô tả]

## Workflow Requirements
1. Plan First: Write to `tasks/todo_[date].md`
2. Verify: Test before marking complete
3. Learn: Update `tasks/lessons.md` for corrections

## Quick Ref
- AGENTS.md: Project context
- Lessons: tasks/lessons.md
- Config: config/config.yaml
```

### 5.4. Khi Fix Bug

```markdown
Bug: [Mô tả lỗi]
Error: [error log]

Hãy:
1. Tự động fix (không cần hỏi)
2. Point at logs/errors
3. Sau khi fix -> update tasks/lessons.md nếu cần
```

---

## 6. Templates

### 6.1. Todo Template (tasks/todo_template.md)

```markdown
# Project: Novel Translator - [NOVEL_NAME]
# Date: [YYYY-MM-DD]
# Pipeline: Trifecta v7.0

## Task Overview
- Novel: [Tên]
- Input: [Đường dẫn]
- Target: Vietnamese
- Purpose: [Draft/Release/Review]

## Plan
### Phase 1: Preparation
- [ ] Verify input file
- [ ] Check glossary.csv
- [ ] Check style_profile.json
- [ ] Validate API keys

### Phase 2: Translation
- [ ] Run preprocessor
- [ ] Execute pipeline
- [ ] Monitor CJK residual

### Phase 3: QA & Post-processing
- [ ] Run Batch QA
- [ ] Verify output
- [ ] Generate final files

### Phase 4: Verification
- [ ] Compare length
- [ ] Spot-check quality
- [ ] Verify glossary

## Review
### Quality Assessment
- CJK residual: [count]
- Dialogue consistency: [%]

### Issues Found
1. ...

### Lessons Learned
1. ...
```

### 6.2. Lessons Template (tasks/lessons_template.md)

```markdown
# Lessons Learned - Novel Translator

## Session: [YYYY-MM-DD]

### Issue: [Title]
**Context:** What was being done?

**What happened:** 
- Error: [type]
- Message: [error]

**Root cause:** 
- [ ] API key exhausted
- [ ] Rate limit
- [ ] CJK residual
- [ ] Glossary not applied
- [ ] Other

**Fix applied:**
[Specific fix]

**Rule to prevent:**
[Rule to avoid recurrence]
```

---

## 7. Câu Lệnh Nhanh

### Translation Commands
```bash
# Chạy dịch
python main.py

# Init session mới
python scripts/init_session.py --task [PROJECT]

# Xem workflow
python scripts/init_session.py --review

# Xem lessons
python scripts/init_session.py --lessons

# Init lessons file
python scripts/init_session.py --init
```

### Quick Reference

| Action | Command |
|--------|---------|
| New task | `python scripts/init_session.py --task NAME` |
| View workflow | `python scripts/init_session.py --review` |
| View lessons | `python scripts/init_session.py --lessons` |
| Init lessons | `python scripts/init_session.py --init` |
| Run translation | `python main.py` |
| Check context | `cat AGENTS.md` |

---

## 8. Best Practices

### Trước Mỗi Phiên
- [ ] Chạy `python scripts/init_session.py --review`
- [ ] Đọc AGENTS.md nếu có cập nhật
- [ ] Xem lessons gần đây

### Trong Phiên
- [ ] Tạo todo.md cho task lớn
- [ ] Verify sau mỗi bước quan trọng
- [ ] Không mark complete nếu chưa verify

### Sau Mỗi Phiên
- [ ] Update lessons.md với learnings mới
- [ ] Verify output cuối cùng
- [ ] Summary cho user

---

## 9. Tích Hợp Với AI Agent

Khi giao task cho AI, luôn bao gồm:

```markdown
Hãy tuân thủ workflow_orchestration.md:
1. Plan first vào tasks/todo.md
2. Verify trước khi done  
3. Update tasks/lessons.md nếu có correction

Context:
- AGENTS.md: Project context
- Tasks: tasks/todo_*.md, tasks/lessons.md
- Config: config/config.yaml
```

---

## 10. Troubleshooting

### Lỗi Thường Gặp

| Lỗi | Giải Pháp |
|------|-----------|
| Unicode error trong script | Đảm bảo terminal hỗ trợ UTF-8 |
| Không tìm thấy tasks/ | Chạy `python scripts/init_session.py --init` |
| Quên plan | Dùng `python scripts/init_session.py --task NAME` |

### Tăng Hiệu Quả
- Dùng `--task` để quick start
- Review lessons trước khi bắt đầu task tương tự
- Update lessons.md ngay sau khi fix issue

---

## Liên Kết

- **Workflow Orchestration:** `workflow_orchestration.md`
- **Project Context:** `AGENTS.md`
- **Config:** `config/config.yaml`
- **Templates:** `tasks/todo_template.md`, `tasks/lessons_template.md`

---

*Document version: 1.0*
*Last updated: 2026-02-24*
*Project: Novel Translator v8.2*
