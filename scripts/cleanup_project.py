#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script dọn dẹp dự án - xóa các file thừa không cần thiết
"""

import os
import shutil
import sys
from pathlib import Path

# Thêm src vào path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from utils.logger import setup_main_logger

logger = setup_main_logger("ProjectCleanup")

class ProjectCleanup:
    """Dọn dẹp dự án"""
    
    def __init__(self):
        """Khởi tạo cleanup"""
        self.project_root = PROJECT_ROOT
        self.files_to_delete = []
        self.dirs_to_delete = []
        self.backup_files = []
        
    def analyze_files(self):
        """Phân tích các file cần xóa"""
        
        # 1. Files backup cũ không cần thiết
        backup_patterns = [
            "*.backup",
            "*.bak", 
            "*.old",
            "*.orig",
            "*_backup.*",
            "*_old.*",
            "*_temp.*"
        ]
        
        # 2. Files test cũ
        test_files = [
            "test_pronoun_checker.py",
            "test_full_workflow_tdttt.py",
            "new 1.txt"
        ]
        
        # 3. Files log cũ (giữ lại 7 ngày gần nhất)
        log_files = self._get_old_log_files()
        
        # 4. Files markdown báo cáo cũ
        old_reports = [
            "ANALYSIS_CONSISTENCY_ISSUES.md",
            "CONSISTENCY_IMPROVEMENTS_SUMMARY.md", 
            "CONTEXT_EXTRACTION_GUIDE.md",
            "2_TIER_CONTEXT_SYSTEM_SUMMARY.md",
            "PROMPT_COMPATIBILITY_ANALYSIS.md",
            "PROMPT_OPTIMIZATION_ANALYSIS.md",
            "PROMPT_OPTIMIZATION_COMPLETE.md",
            "STYLE_PROMPT_OPTIMIZATION_ANALYSIS.md",
            "STYLE_PROMPT_OPTIMIZATION_COMPLETE.md",
            "COMPREHENSIVE_COMPATIBILITY_ANALYSIS.md",
            "COMPATIBILITY_REPORT.md",
            "METADATA_EXTRACTION_GUIDE.md",
            "METADATA_EXTRACTION_MODULE_SUMMARY.md",
            "INTEGRATION_WORKFLOW_DIAGRAM.md",
            "FINAL_INTEGRATION_SUMMARY.md",
            "API_INTEGRATION_SUMMARY.md",
            "RESTRUCTURE_REPORT.md",
            "MANUAL_WORKFLOW_IMPROVEMENTS.md",
            "METADATA_DEPENDENCY_ANALYSIS.md",
            "METADATA_QUALITY_ASSESSMENT.md",
            "MODEL_OPTIMIZATION_RESULTS.md",
            "PRONOUN_METADATA_EXTRACTION_REPORT.md",
            "PRONOUN_SYSTEM_ANALYSIS.md",
            "HYBRID_PRONOUN_SYSTEM_REPORT.md",
            "FINAL_PRONOUN_SYSTEM_RECOMMENDATION.md",
            "GEMINI_MODEL_OPTIMIZATION_ANALYSIS.md",
            "QUOTA_OPTIMIZATION_ANALYSIS.md",
            "QUOTA_OPTIMIZATION_FINAL_REPORT.md",
            "SEQUENTIAL_VS_PARALLEL_FINAL_REPORT.md"
        ]
        
        # 5. Files batch cũ không dùng
        old_batch_files = [
            "3_residual_cleanup.bat",
            "4_simple_cleanup.bat", 
            "5_flash_cleanup.bat",
            "6_extract_pronoun_metadata.bat",
            "6_extract_pronoun_simple.bat",
            "run_backup.bat"
        ]
        
        # 6. Thư mục temp và cache cũ
        temp_dirs = [
            "temp",
            "data/cache"
        ]
        
        # 7. Files trong src/src (duplicate)
        duplicate_src = ["src/src"]
        
        # 8. Files trong docs cũ
        old_docs = [
            "docs/ANALYSIS_CONSISTENCY_ISSUES.md",
            "docs/CONSISTENCY_IMPROVEMENTS_SUMMARY.md",
            "docs/CONTEXT_EXTRACTION_GUIDE.md",
            "docs/2_TIER_CONTEXT_SYSTEM_SUMMARY.md",
            "docs/PROMPT_COMPATIBILITY_ANALYSIS.md",
            "docs/PROMPT_OPTIMIZATION_ANALYSIS.md",
            "docs/PROMPT_OPTIMIZATION_COMPLETE.md",
            "docs/STYLE_PROMPT_OPTIMIZATION_ANALYSIS.md",
            "docs/STYLE_PROMPT_OPTIMIZATION_COMPLETE.md",
            "docs/COMPREHENSIVE_COMPATIBILITY_ANALYSIS.md",
            "docs/COMPATIBILITY_REPORT.md",
            "docs/METADATA_EXTRACTION_GUIDE.md",
            "docs/METADATA_EXTRACTION_MODULE_SUMMARY.md",
            "docs/INTEGRATION_WORKFLOW_DIAGRAM.md",
            "docs/FINAL_INTEGRATION_SUMMARY.md",
            "docs/API_INTEGRATION_SUMMARY.md",
            "docs/RESTRUCTURE_REPORT.md"
        ]
        
        # Tổng hợp danh sách
        self.files_to_delete.extend(test_files)
        self.files_to_delete.extend(log_files)
        self.files_to_delete.extend(old_reports)
        self.files_to_delete.extend(old_batch_files)
        self.files_to_delete.extend(old_docs)
        
        self.dirs_to_delete.extend(temp_dirs)
        self.dirs_to_delete.extend(duplicate_src)
        
        # Files cần backup trước khi xóa
        self.backup_files.extend([
            "CHARACTER_MAPPING_SOLUTION.md",
            "PRONOUN_SYSTEM_INTEGRATION_COMPLETE.md"
        ])
        
        logger.info("Phân tích hoàn thành:")
        logger.info(f"  - Files cần xóa: {len(self.files_to_delete)}")
        logger.info(f"  - Dirs cần xóa: {len(self.dirs_to_delete)}")
        logger.info(f"  - Files cần backup: {len(self.backup_files)}")
    
    def _get_old_log_files(self):
        """Lấy danh sách log files cũ"""
        log_dir = self.project_root / "logs"
        if not log_dir.exists():
            return []
        
        log_files = []
        for log_file in log_dir.glob("*.log*"):
            # Giữ lại 7 ngày gần nhất
            if log_file.stat().st_mtime < (os.path.getmtime(self.project_root) - 7 * 24 * 3600):
                log_files.append(str(log_file.relative_to(self.project_root)))
        
        return log_files
    
    def backup_important_files(self):
        """Backup các file quan trọng"""
        backup_dir = self.project_root / "backups/cleanup_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in self.backup_files:
            src = self.project_root / file_path
            if src.exists():
                dst = backup_dir / src.name
                shutil.copy2(src, dst)
                logger.info(f"Đã backup: {file_path} -> {dst}")
    
    def delete_files(self, dry_run=True):
        """Xóa các file không cần thiết"""
        deleted_count = 0
        
        for file_path in self.files_to_delete:
            path = self.project_root / file_path
            if path.exists():
                if dry_run:
                    logger.info(f"[DRY RUN] Sẽ xóa file: {file_path}")
                else:
                    try:
                        path.unlink()
                        logger.info(f"Đã xóa file: {file_path}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Lỗi xóa file {file_path}: {e}")
            else:
                logger.debug(f"File không tồn tại: {file_path}")
        
        for dir_path in self.dirs_to_delete:
            path = self.project_root / dir_path
            if path.exists():
                if dry_run:
                    logger.info(f"[DRY RUN] Sẽ xóa thư mục: {dir_path}")
                else:
                    try:
                        shutil.rmtree(path)
                        logger.info(f"Đã xóa thư mục: {dir_path}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Lỗi xóa thư mục {dir_path}: {e}")
            else:
                logger.debug(f"Thư mục không tồn tại: {dir_path}")
        
        return deleted_count
    
    def cleanup_pycache(self):
        """Dọn dẹp __pycache__"""
        pycache_dirs = []
        for root, dirs, files in os.walk(self.project_root):
            for dir_name in dirs:
                if dir_name == "__pycache__":
                    pycache_dirs.append(os.path.join(root, dir_name))
        
        for pycache_dir in pycache_dirs:
            try:
                shutil.rmtree(pycache_dir)
                logger.info(f"Đã xóa __pycache__: {pycache_dir}")
            except Exception as e:
                logger.error(f"Lỗi xóa __pycache__ {pycache_dir}: {e}")
    
    def generate_cleanup_report(self):
        """Tạo báo cáo dọn dẹp"""
        report = f"""
# BÁO CÁO DỌN DẸP DỰ ÁN

## 📊 THỐNG KÊ

### Files đã xóa:
- Tổng số files: {len(self.files_to_delete)}
- Files test cũ: {len([f for f in self.files_to_delete if 'test' in f])}
- Files log cũ: {len([f for f in self.files_to_delete if '.log' in f])}
- Files báo cáo cũ: {len([f for f in self.files_to_delete if f.endswith('.md')])}
- Files batch cũ: {len([f for f in self.files_to_delete if f.endswith('.bat')])}

### Thư mục đã xóa:
- Tổng số thư mục: {len(self.dirs_to_delete)}
- Thư mục temp: {len([d for d in self.dirs_to_delete if 'temp' in d])}
- Thư mục cache: {len([d for d in self.dirs_to_delete if 'cache' in d])}

### Files đã backup:
- Tổng số files backup: {len(self.backup_files)}

## 🎯 KẾT QUẢ

Dự án đã được dọn dẹp thành công, loại bỏ các file thừa không cần thiết
mà vẫn giữ lại các file quan trọng và cần thiết cho hoạt động.

## 📁 CẤU TRÚC SAU KHI DỌN DẸP

Dự án giờ đây có cấu trúc gọn gàng hơn với:
- Các file core cần thiết
- Metadata files quan trọng
- Scripts hoạt động
- Logs gần đây (7 ngày)
- Backup files quan trọng

---
**Ngày dọn dẹp:** {os.popen('date /t').read().strip()}
**Trạng thái:** ✅ Hoàn thành
"""
        
        with open(self.project_root / "CLEANUP_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info("Đã tạo báo cáo dọn dẹp: CLEANUP_REPORT.md")

def main():
    """Hàm main"""
    print("🧹 Bắt đầu dọn dẹp dự án...")
    print("=" * 50)
    
    cleanup = ProjectCleanup()
    
    # Phân tích files
    print("📊 Đang phân tích files...")
    cleanup.analyze_files()
    
    # Backup files quan trọng
    print("💾 Đang backup files quan trọng...")
    cleanup.backup_important_files()
    
    # Dry run trước
    print("🔍 Đang chạy dry run...")
    cleanup.delete_files(dry_run=True)
    
    # Hỏi xác nhận
    print("\n⚠️  XÁC NHẬN XÓA FILES:")
    print(f"  - {len(cleanup.files_to_delete)} files")
    print(f"  - {len(cleanup.dirs_to_delete)} thư mục")
    
    confirm = input("\nBạn có chắc chắn muốn xóa? (y/N): ").strip().lower()
    
    if confirm == 'y':
        print("🗑️  Đang xóa files...")
        deleted_count = cleanup.delete_files(dry_run=False)
        
        print("🧹 Đang dọn dẹp __pycache__...")
        cleanup.cleanup_pycache()
        
        print("📝 Đang tạo báo cáo...")
        cleanup.generate_cleanup_report()
        
        print(f"✅ Hoàn thành! Đã xóa {deleted_count} items")
    else:
        print("❌ Hủy bỏ dọn dẹp")

if __name__ == "__main__":
    main()
