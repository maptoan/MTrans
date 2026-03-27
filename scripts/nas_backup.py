#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Novel Translator - NAS Backup Script (v8.1.2)
Tác giả: Antigravity Agent
Công dụng: Tự động nén và sao lưu source code dự án, loại bỏ các file rác và venv.
"""

import datetime
import os
import sys
import zipfile

# === CẤU HÌNH ===
VERSION = "v8.1.2"
# Lấy đường dẫn gốc của dự án (thư mục cha của thư mục chứa script này)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(PROJECT_DIR, "backup")
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
FILENAME = f"novel-translator_{VERSION}_stable_{TIMESTAMP}.zip"

# Danh sách các thư mục/file cần loại bỏ để giảm dung lượng backup
EXCLUDE_DIRS = {
    'venv', '.git', '.vscode', '.Antigravity', '.gemini', '.antigravitykit',
    '.pytest_cache', '.ruff_cache', '__pycache__',
    'backups', 'backup', 'build', 'dist', 'logs', 'logs_test',
    'ocr_app', 'node_modules'
}

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"[*] Đã tạo thư mục backup: {BACKUP_DIR}")

    zip_path = os.path.join(BACKUP_DIR, FILENAME)
    print(f"[*] Bắt đầu sao lưu v7.2 stable vào: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            count = 0
            for root, dirs, files in os.walk(PROJECT_DIR):
                # Tính đường dẫn tương đối từ PROJECT_DIR
                rel_path = os.path.relpath(root, PROJECT_DIR)

                # Loại bỏ các thư mục không cần thiết ở top-level
                parts = rel_path.split(os.sep)
                if any(p in EXCLUDE_DIRS for p in parts):
                    continue

                # Loại bỏ toàn bộ dữ liệu runtime trong thư mục 'data'
                # để backup chỉ chứa codebase + docs theo policy hiện tại.
                if parts[0] == 'data':
                    continue

                for file in files:
                    # Loại bỏ các file nén cũ, file binary rác
                    if file.endswith('.zip') or file.endswith('.pyc') or file == '.DS_Store':
                        continue

                    # Giới hạn kích thước file (tránh nén nhầm các file binary cực lớn > 50MB)
                    file_full_path = os.path.join(root, file)
                    if os.path.getsize(file_full_path) > 50 * 1024 * 1024:
                        print(f"[!] Bỏ qua file quá lớn: {file}")
                        continue

                    archive_name = os.path.join(rel_path, file) if rel_path != '.' else file
                    z.write(file_full_path, archive_name)
                    count += 1

        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"[+] Sao lưu thành công! Tổng cộng {count} files.")
        print(f"[+] Kích thước: {size_mb:.2f} MB")

    except Exception as e:
        print(f"[!] Lỗi khi tạo backup: {str(e)}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        sys.exit(1)

if __name__ == "__main__":
    create_backup()
