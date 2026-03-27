#!/bin/bash
# Novel Translator - NAS Backup Script (Shell Version)
# Tác giả: Antigravity Agent

set -euo pipefail

# === CẤU HÌNH ===
VERSION="v9.4"
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
BACKUP_DIR="$PROJECT_DIR/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="novel-translator_${VERSION}_stable_${TIMESTAMP}.zip"

# Thư mục chứa backup
mkdir -p "$BACKUP_DIR"

echo "[*] Bắt đầu sao lưu vào: $BACKUP_DIR/$FILENAME"

# Di chuyển vào PROJECT_DIR để cấu hình path trong zip đẹp hơn
cd "$PROJECT_DIR"

# Sử dụng zip với danh sách loại trừ (exclude)
# -r: đệ quy
# -q: chạy ngầm (quiet)
zip -rq "$BACKUP_DIR/$FILENAME" . \
    -x "venv/*" \
    -x ".git/*" \
    -x ".vscode/*" \
    -x ".Antigravity/*" \
    -x ".gemini/*" \
    -x ".antigravitykit/*" \
    -x ".pytest_cache/*" \
    -x ".ruff_cache/*" \
    -x "**/__pycache__/*" \
    -x "backups/*" \
    -x "backup/*" \
    -x "build/*" \
    -x "dist/*" \
    -x "logs/*" \
    -x "logs_test/*" \
    -x ".cursor/*" \
    -x ".agent/*" \
    -x "node_modules/*" \
    -x "data/*" \
    -x "*.zip" \
    -x "*.pyc" \
    -x ".DS_Store"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_DIR/$FILENAME" | cut -f1)
    echo "[+] Sao lưu thành công! Kích thước: $SIZE"
else
    echo "[!] Lỗi trong quá trình sao lưu."
    exit 1
fi
