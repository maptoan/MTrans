# Documentation Index - MTranslator

**Phiên bản hiện tại:** v9.4 STABLE  
**Cập nhật lần cuối:** 2026-03-27

---

## 📚 Core Documentation

### **Getting Started**

- **[README.md](./README.md)** - Main README với overview và quick start
- **[CHANGELOG.md](./CHANGELOG.md)** - Changelog với tất cả các thay đổi
- **[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)** - Context tổng quan về dự án
- **[PROJECT_HANDOVER.md](./PROJECT_HANDOVER.md)** - Tài liệu bàn giao dự án
- **[CONVERSATION_HISTORY.md](./CONVERSATION_HISTORY.md)** - Lịch sử phát triển và các session

---

## 🛠️ Setup & Configuration

### **Installation & Setup**

- **[VENV_SETUP_GUIDE.md](./VENV_SETUP_GUIDE.md)** - Hướng dẫn setup virtual environment
- **[requirements.txt](./requirements.txt)** - Python dependencies
- **[requirements-ocr.txt](./requirements-ocr.txt)** - OCR-specific dependencies

### **Configuration**

- **[config/config.yaml](./config/config.yaml)** - Main configuration file
- **[CLAUDE.md](./CLAUDE.md)** - Coding standards và best practices
- **[CODING_STANDARDS_CHECKLIST.md](./CODING_STANDARDS_CHECKLIST.md)** - Checklist tuân thủ coding standards

---

## 📖 Guides & References

### **User Guides**

- **[ACCOUNT_DEDUPLICATION_GUIDE.md](./docs/ACCOUNT_DEDUPLICATION_GUIDE.md)** - Hướng dẫn deduplicate API keys
- **[FORMAT_NORMALIZATION_GUIDE.md](./FORMAT_NORMALIZATION_GUIDE.md)** - Hướng dẫn format normalization

### **Technical References**

- **[ALGORITHM_DOCUMENTATION.md](./ALGORITHM_DOCUMENTATION.md)** - API Key Management & Chunking Optimization Algorithm
- **[PROMPT_REFERENCE_GUIDE.md](./PROMPT_REFERENCE_GUIDE.md)** - Prompt reference guide
- **[PROMPT_QUICK_REFERENCE.md](./PROMPT_QUICK_REFERENCE.md)** - Quick reference cho prompts
- **[WORKFLOW_DOCUMENTATION.md](./WORKFLOW_DOCUMENTATION.md)** - Tài liệu workflow chi tiết
- **[API_WORKER_ORCHESTRATION.md](./docs/API_WORKER_ORCHESTRATION.md)** - Giải thuật điều phối API và Worker động (High Availability)

---

## 📁 Archive Documentation

Các tài liệu lịch sử đã được phân loại vào `docs/archive/`:

### **1. Completed Reports (`docs/archive/completed/`)**

*Báo cáo hoàn tất các giai đoạn phát triển chính.*

- API Key Optimization Phases
- Context Optimization Phases
- Prompt Optimization
- SDK Migration
- TOKEN Optimization Implementation
- Workflow Integration & Optimization Phases 1-3
- Implementation Plan V5.0

### **2. Fix Reports (`docs/archive/fixes/`)**

*Tài liệu chi tiết về việc sửa các lỗi kỹ thuật.*

- Account Deduplication Fix
- API Quota & Rate Limiting Fixes
- Gemini API Communication Fix
- Worker Reduction & Missing Imports Fix
- Attribute Initialization Fixes
- Paragraph & Marker Validation Fixes
- Periodic Flush Implementation

### **3. Analysis Reports (`docs/archive/analysis/`)**

*Phân tích kỹ thuật và thảo luận chuyên gia.*

- Async Cleanup Warning Analysis
- Batch vs Immediate Save Analysis
- Chunk Compression & Merging Analysis
- Token Usage Optimization Discussion
- Workflow Optimization Discussion

### **4. Audit Reports (`docs/archive/audits/`)**

*Các báo cáo kiểm tra tuân thủ coding standards.*

- Workflow Coding Standards Audit
- Comprehensive Coding Standards Audit
- Migration Audit Report

### **5. Reviews & Expert Discussions (`docs/archive/reviews/`)**

*Ý kiến phản biện và thảo luận chuyên sâu.*

- Context Optimization Critique & Expert Discussion
- Periodic Flush Expert Review
- API Key Management Discussion

---

## 🔗 Quick Links

### **For Developers:**

- [CLAUDE.md](./CLAUDE.md) - Coding standards
- [CODING_STANDARDS_CHECKLIST.md](./CODING_STANDARDS_CHECKLIST.md) - Checklist
- [WORKFLOW_DOCUMENTATION.md](./WORKFLOW_DOCUMENTATION.md) - Workflow details

### **For Users:**

- [README.md](./README.md) - Quick start
- [VENV_SETUP_GUIDE.md](./VENV_SETUP_GUIDE.md) - Setup guide

---

## 📝 Notes

- **Archive Location:** `docs/archive/` - Chứa các tài liệu lịch sử đã archive.
- **Current Status:** Dự án đang ở baseline `v9.4` với chuẩn hóa runtime path contract và workspace reorg safety.
- **Source of Truth:** Khi có khác biệt, ưu tiên đọc theo thứ tự: `README.md` → `PROJECT_CONTEXT.md` → `WORKFLOW_DOCUMENTATION.md` → `CHANGELOG.md`.

---

**Last Updated:** 2026-03-27
