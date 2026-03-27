#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
File utilities cho metadata extraction và file operations.

Các chức năng chính:
- Đảm bảo thư mục tồn tại
- Load/Save text, JSON, CSV files
- File operations (exists, size, backup, delete)
"""

import json
import logging
import os
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger("NovelTranslator")


def ensure_dir_exists(directory: str) -> None:
    """
    Tạo thư mục nếu chưa tồn tại.

    Args:
        directory: Đường dẫn thư mục cần tạo

    Returns:
        None

    Note:
        Sử dụng `exist_ok=True` để không raise error nếu thư mục đã tồn tại.
    """
    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Ensured directory exists: {directory}")


def load_text_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    Load nội dung file text.

    Args:
        file_path: Đường dẫn file cần đọc
        encoding: Mã hóa file (mặc định: 'utf-8')

    Returns:
        Nội dung file dưới dạng string

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        UnicodeDecodeError: Nếu không thể decode file với encoding đã cho
        IOError: Nếu có lỗi khi đọc file

    Example:
        >>> content = load_text_file("data/input/novel.txt")
        >>> print(len(content))
        12345
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
        logger.debug(f"Loaded text file: {file_path}")
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error when loading {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading text file {file_path}: {e}", exc_info=True)
        raise


def save_text_file(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Lưu nội dung vào file text.

    Tự động tạo thư mục cha nếu chưa tồn tại.

    Args:
        file_path: Đường dẫn file cần lưu
        content: Nội dung cần lưu (string)
        encoding: Mã hóa file (mặc định: 'utf-8')

    Returns:
        None

    Raises:
        IOError: Nếu có lỗi khi ghi file
        PermissionError: Nếu không có quyền ghi file

    Example:
        >>> save_text_file("data/output/result.txt", "Hello world")
    """
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Chỉ tạo nếu có thư mục (không phải file ở root)
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Saved text file: {file_path}")
    except PermissionError as e:
        logger.error(f"Permission denied when saving {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving text file {file_path}: {e}", exc_info=True)
        raise


def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """
    Lưu data vào file JSON với formatting đẹp.

    Tự động tạo thư mục cha nếu chưa tồn tại.
    Sử dụng `ensure_ascii=False` để hỗ trợ Unicode.

    Args:
        data: Dictionary chứa data cần lưu
        file_path: Đường dẫn file JSON cần lưu

    Returns:
        None

    Raises:
        TypeError: Nếu data không thể serialize thành JSON
        IOError: Nếu có lỗi khi ghi file
        PermissionError: Nếu không có quyền ghi file

    Example:
        >>> data = {"name": "Novel", "chapters": 10}
        >>> save_json_file(data, "data/metadata/novel.json")
    """
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Chỉ tạo nếu có thư mục
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved JSON file: {file_path}")
    except TypeError as e:
        logger.error(f"Data cannot be serialized to JSON: {e}")
        raise
    except PermissionError as e:
        logger.error(f"Permission denied when saving {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}", exc_info=True)
        raise


def save_csv_file(data: pd.DataFrame, file_path: str) -> None:
    """
    Lưu DataFrame vào file CSV.

    Tự động tạo thư mục cha nếu chưa tồn tại.
    Không lưu index (index=False).

    Args:
        data: pandas DataFrame cần lưu
        file_path: Đường dẫn file CSV cần lưu

    Returns:
        None

    Raises:
        ValueError: Nếu DataFrame rỗng hoặc không hợp lệ
        IOError: Nếu có lỗi khi ghi file
        PermissionError: Nếu không có quyền ghi file

    Example:
        >>> df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2]})
        >>> save_csv_file(df, "data/metadata/glossary.csv")
    """
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Chỉ tạo nếu có thư mục
            os.makedirs(dir_path, exist_ok=True)

        data.to_csv(file_path, index=False, encoding="utf-8")
        logger.debug(f"Saved CSV file: {file_path}")
    except ValueError as e:
        logger.error(f"Invalid DataFrame when saving {file_path}: {e}")
        raise
    except PermissionError as e:
        logger.error(f"Permission denied when saving {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving CSV file {file_path}: {e}", exc_info=True)
        raise


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load data từ file JSON.

    Args:
        file_path: Đường dẫn file JSON cần đọc

    Returns:
        Dictionary chứa data từ file JSON

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        json.JSONDecodeError: Nếu file không phải JSON hợp lệ
        IOError: Nếu có lỗi khi đọc file

    Example:
        >>> data = load_json_file("data/metadata/style_profile.json")
        >>> print(data.get("tone"))
        'formal'
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Loaded JSON file: {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"JSON file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}", exc_info=True)
        raise


def load_csv_file(file_path: str) -> pd.DataFrame:
    """
    Load data từ file CSV.

    Args:
        file_path: Đường dẫn file CSV cần đọc

    Returns:
        pandas DataFrame chứa data từ file CSV

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        pd.errors.EmptyDataError: Nếu file CSV rỗng
        pd.errors.ParserError: Nếu file CSV không hợp lệ
        IOError: Nếu có lỗi khi đọc file

    Example:
        >>> df = load_csv_file("data/metadata/glossary.csv")
        >>> print(df.columns.tolist())
        ['Original_Term', 'Translated_Term_VI']
    """
    try:
        data = pd.read_csv(file_path, encoding="utf-8")
        logger.debug(f"Loaded CSV file: {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        raise
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file is empty: {file_path}")
        return pd.DataFrame()  # Trả về DataFrame rỗng thay vì raise
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading CSV file {file_path}: {e}", exc_info=True)
        raise


def file_exists(file_path: str) -> bool:
    """
    Kiểm tra file có tồn tại không.

    Args:
        file_path: Đường dẫn file cần kiểm tra

    Returns:
        True nếu file tồn tại, False nếu không

    Example:
        >>> if file_exists("data/input/novel.txt"):
        ...     content = load_text_file("data/input/novel.txt")
    """
    return os.path.exists(file_path)


def get_file_size(file_path: str) -> int:
    """
    Lấy kích thước file tính bằng bytes.

    Args:
        file_path: Đường dẫn file cần kiểm tra

    Returns:
        Kích thước file tính bằng bytes. Trả về 0 nếu file không tồn tại hoặc có lỗi.

    Example:
        >>> size = get_file_size("data/input/novel.txt")
        >>> print(f"File size: {size / 1024:.2f} KB")
    """
    try:
        return os.path.getsize(file_path)
    except FileNotFoundError:
        logger.warning(f"File not found when getting size: {file_path}")
        return 0
    except Exception as e:
        logger.error(f"Error getting file size {file_path}: {e}", exc_info=True)
        return 0


def backup_file(file_path: str, backup_suffix: str = ".backup") -> str:
    """
    Backup file bằng cách đổi tên file gốc.

    Args:
        file_path: Đường dẫn file cần backup
        backup_suffix: Suffix thêm vào tên file backup (mặc định: '.backup')

    Returns:
        Đường dẫn file backup đã được tạo

    Raises:
        FileNotFoundError: Nếu file gốc không tồn tại
        OSError: Nếu không thể đổi tên file (ví dụ: file backup đã tồn tại)

    Example:
        >>> backup_path = backup_file("data/config.yaml")
        >>> # File gốc đã được đổi tên thành "data/config.yaml.backup"
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File to backup not found: {file_path}")

        backup_path = f"{file_path}{backup_suffix}"
        os.rename(file_path, backup_path)
        logger.debug(f"Backed up file: {file_path} -> {backup_path}")
        return backup_path
    except FileNotFoundError:
        logger.error(f"File not found when backing up: {file_path}")
        raise
    except OSError as e:
        logger.error(f"OS error when backing up {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error backing up file {file_path}: {e}", exc_info=True)
        raise


def delete_file(file_path: str) -> None:
    """
    Xóa file từ filesystem.

    Args:
        file_path: Đường dẫn file cần xóa

    Returns:
        None

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        PermissionError: Nếu không có quyền xóa file
        OSError: Nếu có lỗi hệ thống khi xóa file

    Example:
        >>> delete_file("data/temp/cache.txt")
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found when deleting: {file_path}")
            return  # Không raise error nếu file không tồn tại (idempotent)

        os.remove(file_path)
        logger.debug(f"Deleted file: {file_path}")
    except PermissionError as e:
        logger.error(f"Permission denied when deleting {file_path}: {e}")
        raise
    except OSError as e:
        logger.error(f"OS error when deleting {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}", exc_info=True)
        raise
